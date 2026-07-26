import uuid
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from core.exceptions import EntityNotFoundError, BusinessRuleError
from agricola.alertas.service import (
    AlertasAgricolasService,
    WorkflowGovernanceEvent,
)
from agricola.caderno.models import CadernoCampoEntrada, CadernoCampoFoto
from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from agricola.safras.models import Safra
from agricola.tarefas.models import SafraTarefa, SafraTarefaNecessidade
from agricola.tarefas.schemas import (
    TarefaCreate,
    TarefaUpdate,
    PlanejarOperacaoRequest,
    SafraTarefaNecessidadeCreate,
    SafraTarefaNecessidadeUpdate,
)
from core.services.audit_service import _serialize, write_audit_log
from financeiro.models.despesa import Despesa
from operacional.models.estoque import EstoqueMovimento

STATUS_TAREFA_ATIVA = {"PENDENTE_APROVACAO", "APROVADA", "EM_EXECUCAO", "CONCLUIDA"}

# SafraTarefa.tipo usa uma taxonomia mais granular (ex: origem de análise de solo,
# que discrimina N/P/K) do que OperacaoAgricola.tipo (validado contra
# DEFAULT_TIPO_FASES). Mapeia para o tipo canônico ao gerar a ordem de serviço.
TAREFA_TIPO_PARA_OPERACAO_TIPO: dict[str, str] = {
    "ADUBACAO_NITROGENIO": "ADUBAÇÃO",
    "ADUBACAO_FOSFORO": "ADUBAÇÃO",
    "ADUBACAO_POTASSIO": "ADUBAÇÃO",
    "CALAGEM": "CALAGEM",
    "GRADAGEM": "PREPARO_SOLO",
    "PLANTIO": "PLANTIO",
    "PULVERIZACAO": "PULVERIZAÇÃO",
    "IRRIGACAO": "IRRIGAÇÃO",
    "COLHEITA": "COLHEITA",
    "OUTRO": "OUTROS",
}

# OperacaoAgricola.tipo (canônico) -> TarefaCampo.type (vocabulário do app/PWA de
# campo, ver TIPO_LABEL em apps/web .../campo/tarefas/page.tsx). Usado ao espelhar
# a OS gerada em campo_tarefas para o operador executar.
OPERACAO_TIPO_PARA_CAMPO_TYPE: dict[str, str] = {
    "ADUBAÇÃO": "APLICACAO_FERTILIZANTE",
    "PULVERIZAÇÃO": "APLICACAO_DEFENSIVO",
    "COLHEITA": "COLHEITA_REGISTRO",
    "PLANTIO": "PLANTIO_REGISTRO",
    "PREPARO_SOLO": "PREPARO_SOLO",
    "IRRIGAÇÃO": "IRRIGACAO_EVENTO",
    "CALAGEM": "PREPARO_SOLO",
    "OPERAÇÃO_MECANIZADA": "OPERACAO_MECANIZADA",
    "OUTROS": "OUTROS_AGRICOLA",
}

TRANSICOES = {
    "PENDENTE_APROVACAO": ["APROVADA", "CANCELADA"],
    "APROVADA":           ["EM_EXECUCAO", "CANCELADA"],
    "EM_EXECUCAO":        ["CONCLUIDA", "CANCELADA"],
    "CONCLUIDA":          [],
    "CANCELADA":          [],
    "INVALIDADA":         [],
}

TASK_DELETE_BLOCKED_MESSAGE = (
    "Esta tarefa já gerou registros operacionais e não pode ser excluída. "
    "Utilize cancelamento ou invalidação."
)


@dataclass
class TaskDeleteEvaluation:
    allowed: bool
    blockers: list[str]


class TarefaService:
    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
    ):
        self.session = session
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.ip_address = ip_address

    async def _get(self, tarefa_id: uuid.UUID) -> SafraTarefa:
        stmt = select(SafraTarefa).where(
            SafraTarefa.id == tarefa_id,
            SafraTarefa.tenant_id == self.tenant_id,
        )
        t = (await self.session.execute(stmt)).scalars().first()
        if not t:
            raise EntityNotFoundError(f"Tarefa {tarefa_id} não encontrada.")
        return t

    async def listar(self, safra_id: uuid.UUID, status: str | None = None, talhao_id: uuid.UUID | None = None) -> list[SafraTarefa]:
        stmt = select(SafraTarefa).where(
            SafraTarefa.tenant_id == self.tenant_id,
            SafraTarefa.safra_id == safra_id,
        ).order_by(SafraTarefa.created_at.desc())
        if status:
            stmt = stmt.where(SafraTarefa.status == status)
        if talhao_id:
            stmt = stmt.where(SafraTarefa.talhao_id == talhao_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar(self, safra_id: uuid.UUID, dados: TarefaCreate, user_id: uuid.UUID | None = None) -> SafraTarefa:
        # Idempotência: para tarefas originadas de análise de solo, evita duplicar
        # a mesma recomendação (tenant + analise_solo_id + safra + talhão + tipo)
        # quando já existe uma tarefa ativa equivalente.
        if dados.origem == "SOLO" and dados.analise_solo_id is not None:
            existente = await self._tarefa_solo_ativa_existente(
                analise_solo_id=dados.analise_solo_id,
                safra_id=safra_id,
                talhao_id=dados.talhao_id,
                tipo=dados.tipo,
            )
            if existente:
                return existente

        # Tarefas automáticas (SOLO/TEMPLATE) herdam a fase atual da safra quando
        # o chamador não informa `fase` explicitamente. Tarefas MANUAL preservam
        # a escolha do usuário (inclusive "sem fase") e não sofrem esse preenchimento.
        fase = dados.fase
        if fase is None and dados.origem != "MANUAL":
            fase = await self._fase_atual_safra(safra_id)

        # Tarefas manuais nascem APROVADAS; automáticas (SOLO/TEMPLATE) nascem PENDENTE_APROVACAO
        status_inicial = "APROVADA" if dados.origem == "MANUAL" else "PENDENTE_APROVACAO"
        tarefa = SafraTarefa(
            tenant_id=self.tenant_id,
            safra_id=safra_id,
            talhao_id=dados.talhao_id,
            production_unit_id=dados.production_unit_id,
            cultivo_area_id=dados.cultivo_area_id,
            analise_solo_id=dados.analise_solo_id,
            grupo_geracao_id=dados.grupo_geracao_id,
            origem=dados.origem,
            tipo=dados.tipo,
            fase=fase,
            criticidade=dados.criticidade,
            descricao=dados.descricao,
            obs=dados.obs,
            prioridade=dados.prioridade,
            status=status_inicial,
            dose_estimada_kg_ha=dados.dose_estimada_kg_ha,
            quantidade_total_estimada_kg=dados.quantidade_total_estimada_kg,
            area_ha=dados.area_ha,
            custo_estimado=dados.custo_estimado,
            data_prevista=dados.data_prevista,
            created_by=user_id,
        )
        self.session.add(tarefa)
        await self.session.flush()
        return tarefa

    async def _fase_atual_safra(self, safra_id: uuid.UUID) -> str | None:
        stmt = select(Safra.status).where(
            Safra.id == safra_id,
            Safra.tenant_id == self.tenant_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _tarefa_solo_ativa_existente(
        self,
        analise_solo_id: uuid.UUID,
        safra_id: uuid.UUID,
        talhao_id: uuid.UUID | None,
        tipo: str,
    ) -> SafraTarefa | None:
        stmt = select(SafraTarefa).where(
            SafraTarefa.tenant_id == self.tenant_id,
            SafraTarefa.analise_solo_id == analise_solo_id,
            SafraTarefa.safra_id == safra_id,
            SafraTarefa.talhao_id == talhao_id,
            SafraTarefa.tipo == tipo,
            SafraTarefa.status.in_(STATUS_TAREFA_ATIVA),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _write_audit(self, action: str, before: SafraTarefa | None, after: SafraTarefa | None) -> None:
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            action=action,
            resource=SafraTarefa.__tablename__,
            resource_id=(after or before).id if (after or before) else None,
            payload_before=_serialize(before),
            payload_after=_serialize(after),
            ip_address=self.ip_address,
        )

    async def _related_operacao_ids(self, tarefa: SafraTarefa) -> list[uuid.UUID]:
        clauses = [OperacaoAgricola.tarefa_id == tarefa.id]
        if tarefa.operacao_id:
            clauses.append(OperacaoAgricola.id == tarefa.operacao_id)
        stmt = select(OperacaoAgricola.id).where(
            OperacaoAgricola.tenant_id == self.tenant_id,
            or_(*clauses),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _related_caderno_entry_ids(
        self,
        tarefa: SafraTarefa,
        operacao_ids: list[uuid.UUID],
    ) -> list[uuid.UUID]:
        clauses = []
        if operacao_ids:
            clauses.append(CadernoCampoEntrada.operacao_id.in_(operacao_ids))
        clauses.append(CadernoCampoEntrada.payload_operacional["task_id"].as_string() == str(tarefa.id))
        stmt = select(CadernoCampoEntrada.id).where(
            CadernoCampoEntrada.tenant_id == self.tenant_id,
            CadernoCampoEntrada.excluida.is_(False),
            or_(*clauses),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _avaliar_exclusao_tarefa(self, tarefa: SafraTarefa) -> TaskDeleteEvaluation:
        blockers: list[str] = []

        if tarefa.status != "PENDENTE_APROVACAO":
            blockers.append(f"status:{tarefa.status}")

        if tarefa.concluida_em is not None:
            blockers.append("conclusao")

        operacao_ids = await self._related_operacao_ids(tarefa)
        if tarefa.operacao_id is not None or operacao_ids:
            blockers.append("operacao_agricola")

        caderno_entry_ids = await self._related_caderno_entry_ids(tarefa, operacao_ids)
        if caderno_entry_ids:
            blockers.append("caderno")

        if caderno_entry_ids:
            fotos_count = (
                await self.session.execute(
                    select(func.count(CadernoCampoFoto.id)).where(
                        CadernoCampoFoto.entrada_id.in_(caderno_entry_ids)
                    )
                )
            ).scalar_one()
            if fotos_count:
                blockers.append("evidencia")

        if operacao_ids:
            execucao_ids = list(
                (
                    await self.session.execute(
                        select(OperacaoExecucao.id).where(
                            OperacaoExecucao.tenant_id == self.tenant_id,
                            OperacaoExecucao.operacao_id.in_(operacao_ids),
                        )
                    )
                ).scalars().all()
            )
            if execucao_ids:
                estoque_count = (
                    await self.session.execute(
                        select(func.count(EstoqueMovimento.id)).where(
                            EstoqueMovimento.tenant_id == self.tenant_id,
                            EstoqueMovimento.operacao_execucao_id.in_(execucao_ids),
                        )
                    )
                ).scalar_one()
                if estoque_count:
                    blockers.append("estoque")

                allocation_count = (
                    await self.session.execute(
                        select(func.count(CostAllocation.id)).where(
                            CostAllocation.tenant_id == self.tenant_id,
                            or_(
                                CostAllocation.operation_execution_id.in_(execucao_ids),
                                CostAllocation.source_id.in_(operacao_ids),
                            ),
                        )
                    )
                ).scalar_one()
                if allocation_count:
                    blockers.append("financeiro")

            despesa_count = (
                await self.session.execute(
                    select(func.count(Despesa.id)).where(
                        Despesa.tenant_id == self.tenant_id,
                        Despesa.origem_tipo == "OPERACAO_AGRICOLA",
                        Despesa.origem_id.in_(operacao_ids),
                        Despesa.ativo.is_(True),
                    )
                )
            ).scalar_one()
            if despesa_count:
                blockers.append("financeiro")

        return TaskDeleteEvaluation(allowed=len(blockers) == 0, blockers=sorted(set(blockers)))

    async def pode_excluir_tarefa(self, tarefa_id: uuid.UUID) -> bool:
        tarefa = await self._get(tarefa_id)
        return (await self._avaliar_exclusao_tarefa(tarefa)).allowed

    async def excluir(self, tarefa_id: uuid.UUID) -> None:
        tarefa = await self._get(tarefa_id)
        avaliacao = await self._avaliar_exclusao_tarefa(tarefa)
        if not avaliacao.allowed:
            raise BusinessRuleError(TASK_DELETE_BLOCKED_MESSAGE)

        payload_before = _serialize(tarefa)
        await self.session.delete(tarefa)
        await self.session.flush()
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            action="delete",
            resource=SafraTarefa.__tablename__,
            resource_id=tarefa.id,
            payload_before=payload_before,
            payload_after=None,
            ip_address=self.ip_address,
        )

    async def atualizar(self, tarefa_id: uuid.UUID, dados: TarefaUpdate) -> SafraTarefa:
        tarefa = await self._get(tarefa_id)
        if tarefa.status in {"CANCELADA", "INVALIDADA", "CONCLUIDA"}:
            raise BusinessRuleError("Não é permitido editar tarefa já concluída, cancelada ou invalidada.")
        payload_before = _serialize(tarefa)
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(tarefa, campo, valor)
        tarefa.updated_at = datetime.utcnow()
        await self.session.flush()
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            action="update",
            resource=SafraTarefa.__tablename__,
            resource_id=tarefa.id,
            payload_before=payload_before,
            payload_after=_serialize(tarefa),
            ip_address=self.ip_address,
        )
        return tarefa

    async def aprovar(self, tarefa_id: uuid.UUID, aprovador_id: uuid.UUID) -> SafraTarefa:
        tarefa = await self._get(tarefa_id)
        if "APROVADA" not in TRANSICOES.get(tarefa.status, []):
            raise BusinessRuleError(f"Tarefa com status '{tarefa.status}' não pode ser aprovada.")
        payload_before = _serialize(tarefa)
        tarefa.status = "APROVADA"
        tarefa.aprovado_por = aprovador_id
        tarefa.aprovado_em = datetime.utcnow()
        tarefa.updated_at = datetime.utcnow()
        await self.session.flush()
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=self.user_id or aprovador_id,
            action="approve",
            resource=SafraTarefa.__tablename__,
            resource_id=tarefa.id,
            payload_before=payload_before,
            payload_after=_serialize(tarefa),
            ip_address=self.ip_address,
        )
        return tarefa

    async def rejeitar(self, tarefa_id: uuid.UUID, motivo: str | None = None, user_id: uuid.UUID | None = None) -> SafraTarefa:
        tarefa = await self._get(tarefa_id)
        if "CANCELADA" not in TRANSICOES.get(tarefa.status, []):
            raise BusinessRuleError(f"Tarefa com status '{tarefa.status}' não pode ser cancelada.")
        motivo_limpo = (motivo or "").strip()
        if not motivo_limpo:
            raise BusinessRuleError("Motivo de cancelamento é obrigatório.")
        payload_before = _serialize(tarefa)
        tarefa.status = "CANCELADA"
        tarefa.motivo_cancelamento = motivo_limpo
        tarefa.cancelado_por = user_id
        tarefa.cancelado_em = datetime.utcnow()
        tarefa.updated_at = datetime.utcnow()
        await self.session.flush()
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=user_id or self.user_id,
            action="cancel",
            resource=SafraTarefa.__tablename__,
            resource_id=tarefa.id,
            payload_before=payload_before,
            payload_after=_serialize(tarefa),
            ip_address=self.ip_address,
        )
        return tarefa

    async def invalidar(self, tarefa_id: uuid.UUID, motivo: str, user_id: uuid.UUID | None = None) -> SafraTarefa:
        tarefa = await self._get(tarefa_id)
        motivo_limpo = (motivo or "").strip()
        if not motivo_limpo:
            raise BusinessRuleError("Motivo de invalidação é obrigatório.")

        avaliacao = await self._avaliar_exclusao_tarefa(tarefa)
        if avaliacao.allowed:
            raise BusinessRuleError("Tarefa sem fatos operacionais deve ser cancelada ou excluída, não invalidada.")
        if tarefa.status in {"CANCELADA", "INVALIDADA"}:
            raise BusinessRuleError(f"Tarefa com status '{tarefa.status}' não pode ser invalidada.")

        payload_before = _serialize(tarefa)
        tarefa.status = "INVALIDADA"
        tarefa.invalidado_por = user_id
        tarefa.invalidado_em = datetime.utcnow()
        tarefa.motivo_invalidacao = motivo_limpo
        tarefa.updated_at = datetime.utcnow()
        await self.session.flush()
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=user_id or self.user_id,
            action="invalidate",
            resource=SafraTarefa.__tablename__,
            resource_id=tarefa.id,
            payload_before=payload_before,
            payload_after=_serialize(tarefa),
            ip_address=self.ip_address,
        )

        operacao_ids = await self._related_operacao_ids(tarefa)
        if tarefa.operacao_id and tarefa.operacao_id not in operacao_ids:
            operacao_ids.append(tarefa.operacao_id)

        from agricola.caderno.service import CadernoCampoService

        caderno_svc = CadernoCampoService(self.session, self.tenant_id)
        await caderno_svc.propagar_invalidacao_origem_operacional(
            tarefa_id=tarefa.id,
            motivo=motivo_limpo,
            usuario_id=user_id or self.user_id,
            operacao_ids=operacao_ids,
            ip_address=self.ip_address,
        )
        return tarefa

    async def iniciar(self, tarefa_id: uuid.UUID) -> SafraTarefa:
        tarefa = await self._get(tarefa_id)
        if "EM_EXECUCAO" not in TRANSICOES.get(tarefa.status, []):
            raise BusinessRuleError(f"Tarefa com status '{tarefa.status}' não pode ser iniciada.")
        tarefa.status = "EM_EXECUCAO"
        tarefa.updated_at = datetime.utcnow()
        await self.session.flush()
        return tarefa

    async def concluir(self, tarefa_id: uuid.UUID) -> SafraTarefa:
        tarefa = await self._get(tarefa_id)
        if "CONCLUIDA" not in TRANSICOES.get(tarefa.status, []):
            raise BusinessRuleError(f"Tarefa com status '{tarefa.status}' não pode ser concluída.")
        tarefa.status = "CONCLUIDA"
        tarefa.concluida_em = datetime.utcnow()
        tarefa.updated_at = datetime.utcnow()
        await self._validar_conclusao_manual_leve(tarefa)
        await self.session.flush()
        return tarefa

    async def concluir_via_operacao(self, tarefa_id: uuid.UUID, operacao_id: uuid.UUID) -> SafraTarefa:
        tarefa = await self._get(tarefa_id)
        if tarefa.status in {"CANCELADA", "INVALIDADA"}:
            raise BusinessRuleError(f"Tarefa com status '{tarefa.status}' não pode ser concluída via operação.")
        tarefa.status = "CONCLUIDA"
        tarefa.operacao_id = operacao_id
        tarefa.concluida_em = datetime.utcnow()
        tarefa.updated_at = datetime.utcnow()
        await self.session.flush()
        return tarefa

    async def get(self, tarefa_id: uuid.UUID) -> SafraTarefa:
        return await self._get(tarefa_id)

    async def _validar_conclusao_manual_leve(self, tarefa: SafraTarefa) -> None:
        alertas_svc = AlertasAgricolasService(self.session, self.tenant_id)
        regra = alertas_svc.classificar_origem_tarefa(tarefa.tipo)

        if regra.origem == "ADMINISTRATIVA" or regra.origem == "FINANCEIRA_COMERCIAL":
            return

        justificativa = (tarefa.obs or "").strip()
        evidencia_minima = tarefa.operacao_id is not None or bool(justificativa)

        if regra.origem == "AGRICOLA_OPERACIONAL":
            if tarefa.operacao_id is not None:
                return

            if justificativa:
                finding = alertas_svc.build_finding(
                    codigo="TAREFA_OPERACIONAL_FECHADA_SEM_OPERACAO_COM_JUSTIFICATIVA",
                    titulo="Tarefa operacional concluída sem operação, com justificativa",
                    severidade="WARNING_LEVE",
                    origem="safra_tarefas",
                    total=1,
                    mensagem=(
                        "Tarefa operacional foi concluída manualmente sem operação vinculada, "
                        "mas possui justificativa operacional registrada em observações."
                    ),
                    amostras=[str(tarefa.id)],
                    meta={
                        "tarefa_id": str(tarefa.id),
                        "tipo_tarefa": tarefa.tipo,
                        "classificacao_origem": regra.origem,
                        "justificativa": justificativa,
                    },
                )
                await alertas_svc.registrar_ocorrencia_governanca(
                    WorkflowGovernanceEvent(
                        finding=finding,
                        resource_id=str(tarefa.id),
                        action="manual_close_just",
                        notify=False,
                        audit=True,
                        origem_id=f"tarefa:{tarefa.id}:manual_closure_with_justification",
                    )
                )
                return

            finding = alertas_svc.build_finding(
                codigo="TAREFA_OPERACIONAL_FECHADA_SEM_OPERACAO_SEM_JUSTIFICATIVA",
                titulo="Tarefa operacional concluída sem operação",
                severidade="INCONSISTENCIA_MODERADA",
                origem="safra_tarefas",
                total=1,
                mensagem=(
                    "Tarefa operacional foi concluída manualmente sem operação vinculada e sem "
                    "justificativa operacional em observações."
                ),
                amostras=[str(tarefa.id)],
                meta={
                    "tarefa_id": str(tarefa.id),
                    "tipo_tarefa": tarefa.tipo,
                    "classificacao_origem": regra.origem,
                },
            )
            await alertas_svc.registrar_ocorrencia_governanca(
                WorkflowGovernanceEvent(
                    finding=finding,
                    resource_id=str(tarefa.id),
                    action="manual_close_warn",
                    notify=True,
                    audit=True,
                    origem_id=f"tarefa:{tarefa.id}:manual_closure_without_operation",
                )
            )
            return

        if regra.warning_sem_evidencia and not evidencia_minima:
            if regra.origem == "INSPECAO_MONITORAMENTO":
                finding = alertas_svc.build_finding(
                    codigo="TAREFA_INSPECAO_SEM_EVIDENCIA",
                    titulo="Tarefa de inspeção/monitoramento sem evidência mínima",
                    severidade="WARNING_LEVE",
                    origem="safra_tarefas",
                    total=1,
                    mensagem=(
                        "Tarefa de inspeção/monitoramento foi concluída sem operação, "
                        "apontamento, checklist explícito ou justificativa operacional."
                    ),
                    amostras=[str(tarefa.id)],
                    meta={"tarefa_id": str(tarefa.id), "tipo_tarefa": tarefa.tipo, "classificacao_origem": regra.origem},
                )
                await alertas_svc.registrar_ocorrencia_governanca(
                    WorkflowGovernanceEvent(
                        finding=finding,
                        resource_id=str(tarefa.id),
                        action="inspect_warn",
                        notify=True,
                        audit=True,
                        origem_id=f"tarefa:{tarefa.id}:inspection_without_evidence",
                    )
                )
            elif regra.origem == "MANUTENCAO_FROTA":
                finding = alertas_svc.build_finding(
                    codigo="TAREFA_MANUTENCAO_SEM_EVIDENCIA",
                    titulo="Tarefa de manutenção/frota sem evidência mínima",
                    severidade="INCONSISTENCIA_MODERADA",
                    origem="safra_tarefas",
                    total=1,
                    mensagem=(
                        "Tarefa de manutenção/frota foi concluída sem evidência mínima "
                        "registrada em OS, jornada, checklist ou justificativa operacional."
                    ),
                    amostras=[str(tarefa.id)],
                    meta={"tarefa_id": str(tarefa.id), "tipo_tarefa": tarefa.tipo, "classificacao_origem": regra.origem},
                )
                await alertas_svc.registrar_ocorrencia_governanca(
                    WorkflowGovernanceEvent(
                        finding=finding,
                        resource_id=str(tarefa.id),
                        action="maint_warn",
                        notify=True,
                        audit=True,
                        origem_id=f"tarefa:{tarefa.id}:maintenance_without_evidence",
                    )
                )

    async def gerar_operacao_planejada(self, tarefa_id: uuid.UUID, dados: PlanejarOperacaoRequest) -> OperacaoAgricola:
        # Lock a linha da tarefa para evitar corrida em cliques duplicados: dois
        # requests concorrentes gerariam duas OS/TarefaCampo para a mesma tarefa
        # se ambos passassem pelo SELECT "op_existente" antes do primeiro commitar.
        stmt_lock = select(SafraTarefa).where(
            SafraTarefa.id == tarefa_id,
            SafraTarefa.tenant_id == self.tenant_id,
        ).with_for_update()
        tarefa = (await self.session.execute(stmt_lock)).scalars().first()
        if not tarefa:
            raise EntityNotFoundError(f"Tarefa {tarefa_id} não encontrada.")
        if tarefa.status != "APROVADA":
            raise BusinessRuleError(
                f"Tarefa com status '{tarefa.status}' não pode gerar operação planejada. "
                "É necessário aprovar a tarefa antes de planejar logisticamente."
            )
        if tarefa.talhao_id is None:
            raise BusinessRuleError(
                "Esta tarefa não está vinculada a um talhão específico. "
                "Edite a tarefa e defina o talhão antes de gerar a ordem de serviço."
            )

        from agricola.operacoes.models import OperacaoAgricola
        from agricola.operacoes.service import OperacaoService
        from agricola.operacoes.schemas import OperacaoAgricolaCreate, InsumoOperacaoCreate
        from core.cadastros.propriedades.models import AreaRural

        # TarefaCampo/AreaRural usam o modelo LEGADO de fazenda (unidades_produtivas),
        # diferente de OperacaoAgricola.production_unit_id (modelo novo production_units)
        # — não são o mesmo espaço de UUIDs, não confundir os dois ao popular a ponte.
        talhao = await self.session.get(AreaRural, tarefa.talhao_id)
        unidade_produtiva_legado_id = talhao.unidade_produtiva_id if talhao else None

        stmt = select(OperacaoAgricola).where(
            OperacaoAgricola.tenant_id == self.tenant_id,
            OperacaoAgricola.tarefa_id == tarefa.id,
            OperacaoAgricola.status == "PLANEJADA"
        )
        op_existente = (await self.session.execute(stmt)).scalars().first()
        if op_existente:
            from campo.models import TarefaCampo
            campo_stmt = select(TarefaCampo).where(
                TarefaCampo.tenant_id == self.tenant_id,
                TarefaCampo.operacao_agricola_id == op_existente.id,
            )
            campo_existente = (await self.session.execute(campo_stmt)).scalars().first()
            if not campo_existente:
                from campo.service import TarefaProgramadaService
                campo_svc = TarefaProgramadaService(self.session, self.tenant_id, self.user_id)
                await campo_svc.criar_vinculada_operacao(
                    safra_tarefa_id=tarefa.id,
                    operacao_agricola_id=op_existente.id,
                    titulo=tarefa.descricao or f"{op_existente.tipo} — {tarefa.tipo}",
                    type=OPERACAO_TIPO_PARA_CAMPO_TYPE.get(op_existente.tipo, "OUTROS_AGRICOLA"),
                    data_programada=dados.data_prevista,
                    unidade_produtiva_id=unidade_produtiva_legado_id,
                    area_rural_id=tarefa.talhao_id,
                    operador_id=dados.operador_id,
                    prioridade="ALTA" if tarefa.criticidade == "CRITICA" else "NORMAL",
                )
            return op_existente

        insumos_create = []
        for ins in dados.insumos:
            insumos_create.append(InsumoOperacaoCreate(
                produto_id=ins.produto_id,
                dose_por_ha=ins.dose_por_ha,
                unidade=ins.unidade,
                area_aplicada=tarefa.area_ha,
            ))

        op_create = OperacaoAgricolaCreate(
            safra_id=tarefa.safra_id,
            talhao_id=tarefa.talhao_id,
            cultivo_id=None,
            production_unit_id=tarefa.production_unit_id,
            tarefa_id=tarefa.id,
            tipo=TAREFA_TIPO_PARA_OPERACAO_TIPO.get(tarefa.tipo, tarefa.tipo),
            descricao=tarefa.descricao or f"Operação planejada a partir da tarefa {tarefa.tipo}",
            fase_safra=None,  # auto-preenche com a fase ATUAL da safra (tarefa.fase é a fase no momento da criação, pode estar desatualizada)
            data_prevista=dados.data_prevista,
            data_realizada=dados.data_prevista,
            area_aplicada_ha=tarefa.area_ha or 1.0,
            maquina_id=dados.maquina_id,
            implemento=dados.implemento,
            operador_id=dados.operador_id,
            status="PLANEJADA",
            insumos=insumos_create,
        )

        op_svc = OperacaoService(self.session, self.tenant_id)
        operacao = await op_svc.criar(op_create)

        from campo.service import TarefaProgramadaService
        campo_svc = TarefaProgramadaService(self.session, self.tenant_id, self.user_id)
        await campo_svc.criar_vinculada_operacao(
            safra_tarefa_id=tarefa.id,
            operacao_agricola_id=operacao.id,
            titulo=tarefa.descricao or f"{operacao.tipo} — {tarefa.tipo}",
            type=OPERACAO_TIPO_PARA_CAMPO_TYPE.get(operacao.tipo, "OUTROS_AGRICOLA"),
            data_programada=dados.data_prevista,
            unidade_produtiva_id=unidade_produtiva_legado_id,
            area_rural_id=tarefa.talhao_id,
            operador_id=dados.operador_id,
            prioridade="ALTA" if tarefa.criticidade == "CRITICA" else "NORMAL",
        )
        return operacao

    # ------------------------------------------------------------------
    # Necessidade agronômica estruturada (Fase 2 do PLANO-OPERACIONAL-01)
    # ------------------------------------------------------------------

    async def adicionar_necessidade(
        self, tarefa_id: uuid.UUID, dados: SafraTarefaNecessidadeCreate
    ) -> SafraTarefaNecessidade:
        await self._get(tarefa_id)  # valida existência + tenant
        necessidade = SafraTarefaNecessidade(
            tenant_id=self.tenant_id,
            safra_tarefa_id=tarefa_id,
            categoria=dados.categoria,
            tipo_aplicacao=dados.tipo_aplicacao,
            unidade_referencia=dados.unidade_referencia,
            dose_tecnica=dados.dose_tecnica,
            quantidade_tecnica=dados.quantidade_tecnica,
            area_referencia_ha=dados.area_referencia_ha,
            origem_calculo=dados.origem_calculo,
            parametros_calculo=dados.parametros_calculo,
        )
        self.session.add(necessidade)
        await self.session.flush()
        return necessidade

    async def listar_necessidades(self, tarefa_id: uuid.UUID) -> list[SafraTarefaNecessidade]:
        await self._get(tarefa_id)
        stmt = select(SafraTarefaNecessidade).where(
            SafraTarefaNecessidade.tenant_id == self.tenant_id,
            SafraTarefaNecessidade.safra_tarefa_id == tarefa_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _get_necessidade_or_fail(
        self, tarefa_id: uuid.UUID, necessidade_id: uuid.UUID
    ) -> SafraTarefaNecessidade:
        stmt = select(SafraTarefaNecessidade).where(
            SafraTarefaNecessidade.id == necessidade_id,
            SafraTarefaNecessidade.safra_tarefa_id == tarefa_id,
            SafraTarefaNecessidade.tenant_id == self.tenant_id,
        )
        necessidade = (await self.session.execute(stmt)).scalars().first()
        if not necessidade:
            raise EntityNotFoundError(f"Necessidade {necessidade_id} não encontrada nesta tarefa.")
        return necessidade

    async def atualizar_necessidade(
        self, tarefa_id: uuid.UUID, necessidade_id: uuid.UUID, dados: SafraTarefaNecessidadeUpdate
    ) -> SafraTarefaNecessidade:
        necessidade = await self._get_necessidade_or_fail(tarefa_id, necessidade_id)
        for campo, valor in dados.model_dump(exclude_unset=True).items():
            setattr(necessidade, campo, valor)
        self.session.add(necessidade)
        await self.session.flush()
        return necessidade

    async def remover_necessidade(self, tarefa_id: uuid.UUID, necessidade_id: uuid.UUID) -> None:
        necessidade = await self._get_necessidade_or_fail(tarefa_id, necessidade_id)
        await self.session.delete(necessidade)
        await self.session.flush()
