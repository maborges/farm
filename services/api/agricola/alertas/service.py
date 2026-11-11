"""
Serviço de alertas agrícolas.
Verifica condições críticas nas safras e dispara notificações via NotificacaoService.

Condições verificadas:
1. Checklist obrigatório pendente na fase atual
2. Safra parada na mesma fase há N dias sem operações registradas
3. Safra em DESENVOLVIMENTO sem registro fenológico recente (> 14 dias)
4. Inconsistências de governança do workflow operacional
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from agricola.safras.models import Safra
from agricola.checklist.models import SafraChecklistItem
from agricola.safras.models import SafraFaseHistorico
from agricola.fenologia.models import SafraFenologiaRegistro
from agricola.tarefas.models import SafraTarefa
from core.services.audit_service import write_audit_log
from financeiro.models.despesa import Despesa
from financeiro.models.lancamento import LancamentoFinanceiro
from notificacoes.service import NotificacaoService
from notificacoes.schemas import NotificacaoCreate
from operacional.models.apontamento import ApontamentoUso
from operacional.models.compras import DevolucaoFornecedor, ItemDevolucao, ItemRecebimento, PedidoCompra, RecebimentoParcial
from operacional.models.estoque import EstoqueMovimento
from core.exceptions import BusinessRuleError
from core.services.analytics_taxonomy import classificar_tipo_relatorio, normalizar_severidade

DIAS_FASE_PARADA = 10       # alerta se safra ficou X dias na mesma fase sem avançar
DIAS_FENOLOGIA_VENCIDA = 14  # alerta se não há registro fenológico há X dias em DESENVOLVIMENTO
WORKFLOW_GOVERNANCE_RESOURCE = "operational_workflow_governance"
WORKFLOW_GOVERNANCE_ORIGIN = "workflow_governance"

TIPOS_TAREFA_OPERACIONAL = {
    "CALAGEM",
    "ADUBACAO_FOSFORO",
    "ADUBACAO_POTASSIO",
    "ADUBACAO_NITROGENIO",
    "GRADAGEM",
    "PLANTIO",
    "PULVERIZACAO",
    "IRRIGACAO",
    "COLHEITA",
}
TIPOS_DESPESA_AUTOMATICA = {
    "OPERACAO_AGRICOLA",
    "ORDEM_SERVICO",
    "ABASTECIMENTO",
    "COMPRA",
    "RH_DIARIA",
    "RH_EMPREITADA",
}
SEVERITY_NOTIFICATION_LEVEL = {
    "WARNING_LEVE": "INFO",
    "INCONSISTENCIA_MODERADA": "WARNING",
    "RISCO_ECONOMICO": "WARNING",
    "RISCO_CRITICO": "DANGER",
    "ATENCAO": "WARNING",
    "PRIORIDADE_CRITICA": "DANGER",
}
WORKFLOW_ENFORCEMENT_WARNING_ONLY = "WARNING_ONLY"
WORKFLOW_ENFORCEMENT_BLOCK_CRITICAL = "BLOCK_CRITICAL"
WORKFLOW_ENFORCEMENT_BLOCK_ECONOMIC_AND_CRITICAL = "BLOCK_ECONOMIC_AND_CRITICAL"
WORKFLOW_ENFORCEMENT_MODE = WORKFLOW_ENFORCEMENT_WARNING_ONLY
WORKFLOW_ENFORCEMENT_BLOCKED_SEVERITIES = {
    WORKFLOW_ENFORCEMENT_WARNING_ONLY: set(),
    WORKFLOW_ENFORCEMENT_BLOCK_CRITICAL: {"RISCO_CRITICO", "PRIORIDADE_CRITICA"},
    WORKFLOW_ENFORCEMENT_BLOCK_ECONOMIC_AND_CRITICAL: {"RISCO_ECONOMICO", "RISCO_CRITICO", "PRIORIDADE_CRITICA"},
}


@dataclass(slots=True)
class WorkflowGovernanceFinding:
    codigo: str
    titulo: str
    severidade: str
    origem: str
    total: int
    mensagem: str
    amostras: list[str]
    meta: dict

    def to_payload(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class WorkflowGovernanceEvent:
    finding: WorkflowGovernanceFinding
    resource_id: str | None = None
    action: str = "warning"
    notify: bool = True
    audit: bool = True
    origem_id: str | None = None


@dataclass(slots=True)
class WorkflowGovernanceReportItem:
    codigo: str
    titulo: str
    severidade: str
    tipo_inconsistencia: str
    origem: str
    origem_tipo: str | None
    origem_id: str | None
    total: int
    mensagem: str
    sugestao_correcao: str
    amostras: list[str]
    meta: dict


@dataclass(slots=True)
class WorkflowGovernanceReport:
    tenant_id: UUID
    gerado_em: datetime
    total_inconsistencias: int
    por_severidade: dict[str, int]
    por_tipo: dict[str, int]
    itens: list[WorkflowGovernanceReportItem]


@dataclass(slots=True)
class WorkflowOriginRule:
    origem: str
    exige_operacao: bool = False
    exige_execucao: bool = False
    exige_apontamento: bool = False
    exige_cost_allocation: bool = False
    exige_origem_rastreavel: bool = False
    permite_fechamento_sem_custo: bool = True
    permite_fechamento_com_justificativa: bool = False
    warning_sem_evidencia: str | None = None


TIPOS_TAREFA_ADMINISTRATIVA = {"ADMINISTRATIVA", "FINANCEIRA", "COMERCIAL"}
TIPOS_TAREFA_INSPECAO = {"INSPECAO", "MONITORAMENTO", "CHECKLIST"}
TIPOS_TAREFA_MANUTENCAO = {"MANUTENCAO", "MANUTENCAO_FROTA", "FROTA", "OFICINA"}
TIPOS_OPERACAO_INSPECAO = {"INSPECAO", "MONITORAMENTO"}


class AlertasAgricolasService:
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.notif_svc = NotificacaoService(session, tenant_id)

    async def verificar_todas(self, fazenda_ids: list[UUID] | None = None) -> int:
        """Verifica todas as condições de alerta e dispara notificações. Retorna total de alertas gerados."""
        total = 0
        total += await self._verificar_checklist_pendente()
        total += await self._verificar_fase_parada()
        total += await self._verificar_fenologia_vencida()
        total += await self.verificar_governanca_operacional()
        total += await self.verificar_reconciliacao_economica()
        return total

    async def _safras_ativas(self) -> list[Safra]:
        stmt = select(Safra).where(
            Safra.tenant_id == self.tenant_id,
            Safra.status.notin_(["ENCERRADA", "CANCELADA"]),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _verificar_checklist_pendente(self) -> int:
        """Alerta quando há itens obrigatórios não concluídos na fase atual."""
        safras = await self._safras_ativas()
        total = 0
        if not safras:
            return 0

        stmt = (
            select(
                SafraChecklistItem.safra_id,
                func.count(SafraChecklistItem.id).label("total"),
            )
            .where(
                SafraChecklistItem.tenant_id == self.tenant_id,
                SafraChecklistItem.safra_id.in_([safra.id for safra in safras]),
                SafraChecklistItem.obrigatorio == True,
                SafraChecklistItem.concluido == False,
            )
            .group_by(SafraChecklistItem.safra_id)
        )
        pendentes_por_safra = {
            safra_id: total
            for safra_id, total in (await self.session.execute(stmt)).all()
        }
        for safra in safras:
            pendentes = pendentes_por_safra.get(safra.id, 0)
            if pendentes > 0:
                await self.notif_svc.criar_e_push(NotificacaoCreate(
                    tipo="ALERTA_AGRICOLA",
                    titulo="Checklist obrigatório pendente",
                    mensagem=(
                        f"Safra {safra.cultura} {safra.ano_safra} possui {pendentes} "
                        f"atividade(s) obrigatória(s) pendente(s) na fase {safra.status}."
                    ),
                ))
                total += 1
        return total

    async def _verificar_fase_parada(self) -> int:
        """Alerta quando uma safra está na mesma fase há mais de DIAS_FASE_PARADA dias."""
        safras = await self._safras_ativas()
        total = 0
        limite = date.today() - timedelta(days=DIAS_FASE_PARADA)
        if not safras:
            return 0

        stmt = (
            select(
                SafraFaseHistorico.safra_id,
                func.max(SafraFaseHistorico.created_at).label("ultima_data"),
            )
            .where(
                SafraFaseHistorico.tenant_id == self.tenant_id,
                SafraFaseHistorico.safra_id.in_([safra.id for safra in safras]),
            )
            .group_by(SafraFaseHistorico.safra_id)
        )
        ultimo_por_safra: dict[UUID, date] = {}
        for safra_id, ultima_data in (await self.session.execute(stmt)).all():
            if isinstance(ultima_data, datetime):
                ultimo_por_safra[safra_id] = ultima_data.date()
            elif isinstance(ultima_data, date):
                ultimo_por_safra[safra_id] = ultima_data

        for safra in safras:
            ultima_data = ultimo_por_safra.get(safra.id)
            if ultima_data and ultima_data < limite:
                dias = (date.today() - ultima_data).days
                await self.notif_svc.criar_e_push(NotificacaoCreate(
                    tipo="ALERTA_AGRICOLA",
                    titulo="Safra parada na mesma fase",
                    mensagem=(
                        f"Safra {safra.cultura} {safra.ano_safra} está na fase "
                        f"{safra.status} há {dias} dias sem avançar."
                    ),
                ))
                total += 1
        return total

    async def _verificar_fenologia_vencida(self) -> int:
        """Alerta quando não há registro fenológico recente em safras em DESENVOLVIMENTO."""
        stmt = select(Safra).where(
            Safra.tenant_id == self.tenant_id,
            Safra.status == "DESENVOLVIMENTO",
        )
        safras = list((await self.session.execute(stmt)).scalars().all())
        total = 0
        limite = date.today() - timedelta(days=DIAS_FENOLOGIA_VENCIDA)
        if not safras:
            return 0

        stmt_fen = (
            select(
                SafraFenologiaRegistro.safra_id,
                func.max(SafraFenologiaRegistro.data_observacao).label("ultima_data"),
            )
            .where(
                SafraFenologiaRegistro.tenant_id == self.tenant_id,
                SafraFenologiaRegistro.safra_id.in_([safra.id for safra in safras]),
            )
            .group_by(SafraFenologiaRegistro.safra_id)
        )
        ultimo_por_safra = {
            safra_id: ultima_data
            for safra_id, ultima_data in (await self.session.execute(stmt_fen)).all()
            if isinstance(ultima_data, date)
        }

        for safra in safras:
            ultimo = ultimo_por_safra.get(safra.id)
            if not ultimo or ultimo < limite:
                dias = (date.today() - ultimo).days if ultimo else "?"
                await self.notif_svc.criar_e_push(NotificacaoCreate(
                    tipo="ALERTA_AGRICOLA",
                    titulo="Sem registro fenológico recente",
                    mensagem=(
                        f"Safra {safra.cultura} {safra.ano_safra} está em DESENVOLVIMENTO "
                        f"sem registro fenológico há {dias} dias."
                    ),
                ))
                total += 1
        return total

    async def verificar_governanca_operacional(self) -> int:
        findings = await self.detectar_inconsistencias_operacionais()
        if not findings:
            await self._registrar_scan_governanca([])
            logger.info(
                "workflow_governance_scan",
                tenant_id=str(self.tenant_id),
                findings=0,
            )
            return 0

        for finding in findings:
            await self.registrar_ocorrencia_governanca(
                WorkflowGovernanceEvent(
                    finding=finding,
                    resource_id=finding.amostras[0] if finding.amostras else None,
                    action="scan_finding",
                    notify=True,
                    audit=False,
                    origem_id=finding.codigo,
                )
            )

        await self._registrar_scan_governanca(findings)
        return len(findings)

    async def verificar_reconciliacao_economica(self) -> int:
        findings = await self.detectar_inconsistencias_reconciliacao_economica()
        if not findings:
            await self._registrar_scan_reconciliacao([])
            logger.info(
                "workflow_economic_reconciliation_scan",
                tenant_id=str(self.tenant_id),
                findings=0,
            )
            return 0

        for finding in findings:
            await self.registrar_ocorrencia_governanca(
                WorkflowGovernanceEvent(
                    finding=finding,
                    resource_id=finding.amostras[0] if finding.amostras else None,
                    action="reconcile_finding",
                    notify=True,
                    audit=False,
                    origem_id=finding.codigo,
                )
            )

        await self._registrar_scan_reconciliacao(findings)
        return len(findings)

    async def gerar_relatorio_governanca(self) -> WorkflowGovernanceReport:
        findings = [
            *await self.detectar_inconsistencias_operacionais(),
            *await self.detectar_inconsistencias_reconciliacao_economica(),
        ]

        devolucoes = await self._detectar_devolucao_sem_movimento_original()
        if devolucoes is not None:
            findings.append(devolucoes)

        itens = [self._finding_para_relatorio(finding) for finding in findings]
        por_severidade = Counter(item.severidade for item in itens)
        por_tipo = Counter(item.tipo_inconsistencia for item in itens)

        return WorkflowGovernanceReport(
            tenant_id=self.tenant_id,
            gerado_em=datetime.now(timezone.utc),
            total_inconsistencias=len(itens),
            por_severidade=dict(sorted(por_severidade.items())),
            por_tipo=dict(sorted(por_tipo.items())),
            itens=itens,
        )

    async def detectar_inconsistencias_operacionais(self) -> list[WorkflowGovernanceFinding]:
        findings: list[WorkflowGovernanceFinding] = []

        findings.extend(
            [
                finding
                for finding in [
                    await self._detectar_tarefa_concluida_sem_operacao(),
                    await self._detectar_operacao_sem_execucao(),
                    await self._detectar_operacao_com_custo_sem_allocation(),
                    await self._detectar_apontamento_com_custo_sem_contexto(),
                    await self._detectar_pedido_recebido_sem_movimento_ou_lote(),
                    await self._detectar_despesa_automatica_sem_origem(),
                    await self._detectar_allocations_duplicadas(),
                ]
                if finding is not None
            ]
        )
        return findings

    async def detectar_inconsistencias_reconciliacao_economica(self) -> list[WorkflowGovernanceFinding]:
        findings: list[WorkflowGovernanceFinding] = []

        findings.extend(
            [
                finding
                for finding in [
                    await self._detectar_allocation_sem_reflexo_economico(),
                    await self._detectar_cost_allocation_sem_origem_rastreavel(),
                    await self._detectar_despesa_automatica_duplicada_mesma_origem(),
                    await self._detectar_movimento_com_custo_sem_allocation(),
                    await self._detectar_divergencia_valor_operacional_apropriado(),
                ]
                if finding is not None
            ]
        )
        return findings

    async def _registrar_scan_governanca(self, findings: list[WorkflowGovernanceFinding]) -> None:
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=None,
            action="scan",
            resource=WORKFLOW_GOVERNANCE_RESOURCE,
            resource_id=None,
            payload_before=None,
            payload_after={
                "findings": [finding.to_payload() for finding in findings],
                "total_findings": len(findings),
            },
            ip_address=None,
        )
        await self.session.commit()

    async def _registrar_scan_reconciliacao(self, findings: list[WorkflowGovernanceFinding]) -> None:
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=None,
            action="reconcile",
            resource=WORKFLOW_GOVERNANCE_RESOURCE,
            resource_id=None,
            payload_before=None,
            payload_after={
                "findings": [finding.to_payload() for finding in findings],
                "total_findings": len(findings),
            },
            ip_address=None,
        )
        await self.session.commit()

    def classificar_origem_tarefa(self, tipo_tarefa: str | None) -> WorkflowOriginRule:
        tipo = (tipo_tarefa or "").strip().upper()
        if tipo in TIPOS_TAREFA_OPERACIONAL:
            return WorkflowOriginRule(
                origem="AGRICOLA_OPERACIONAL",
                exige_operacao=True,
                exige_execucao=True,
                exige_cost_allocation=True,
                permite_fechamento_sem_custo=False,
                permite_fechamento_com_justificativa=True,
                warning_sem_evidencia="INCONSISTENCIA_MODERADA",
            )
        if tipo in TIPOS_TAREFA_ADMINISTRATIVA:
            return WorkflowOriginRule(
                origem="ADMINISTRATIVA",
                permite_fechamento_sem_custo=True,
                permite_fechamento_com_justificativa=True,
            )
        if tipo in TIPOS_TAREFA_INSPECAO:
            return WorkflowOriginRule(
                origem="INSPECAO_MONITORAMENTO",
                exige_apontamento=True,
                permite_fechamento_sem_custo=True,
                permite_fechamento_com_justificativa=True,
                warning_sem_evidencia="WARNING_LEVE",
            )
        if tipo in TIPOS_TAREFA_MANUTENCAO:
            return WorkflowOriginRule(
                origem="MANUTENCAO_FROTA",
                exige_apontamento=True,
                exige_origem_rastreavel=True,
                permite_fechamento_sem_custo=False,
                permite_fechamento_com_justificativa=True,
                warning_sem_evidencia="INCONSISTENCIA_MODERADA",
            )
        return WorkflowOriginRule(
            origem="FINANCEIRA_COMERCIAL",
            permite_fechamento_sem_custo=True,
            permite_fechamento_com_justificativa=True,
        )

    def classificar_origem_operacao(self, tipo_operacao: str | None) -> WorkflowOriginRule:
        tipo = (tipo_operacao or "").strip().upper()
        if tipo in TIPOS_OPERACAO_INSPECAO:
            return WorkflowOriginRule(
                origem="INSPECAO_MONITORAMENTO",
                exige_execucao=True,
                permite_fechamento_sem_custo=True,
                permite_fechamento_com_justificativa=True,
                warning_sem_evidencia="WARNING_LEVE",
            )
        return WorkflowOriginRule(
            origem="AGRICOLA_OPERACIONAL",
            exige_execucao=True,
            exige_cost_allocation=True,
            permite_fechamento_sem_custo=False,
            permite_fechamento_com_justificativa=False,
            warning_sem_evidencia="INCONSISTENCIA_MODERADA",
        )

    def classificar_origem_despesa(self, origem_tipo: str | None) -> WorkflowOriginRule:
        origem = (origem_tipo or "").strip().upper()
        if origem in {"OPERACAO_AGRICOLA", "ABASTECIMENTO", "ORDEM_SERVICO", "COMPRA"}:
            return WorkflowOriginRule(
                origem="AGRICOLA_OPERACIONAL" if origem == "OPERACAO_AGRICOLA" else "MANUTENCAO_FROTA",
                exige_origem_rastreavel=True,
            )
        if origem in {"RH_DIARIA", "RH_EMPREITADA"}:
            return WorkflowOriginRule(
                origem="RH_OPERACIONAL",
                exige_origem_rastreavel=True,
            )
        if origem == "FIN_RATEIO":
            return WorkflowOriginRule(
                origem="RATEIO_FINANCEIRO",
                exige_origem_rastreavel=True,
                permite_fechamento_sem_custo=True,
            )
        if origem in {"AJUSTE", "REQUISICAO", "TRANSFERENCIA", "MANUAL"}:
            return WorkflowOriginRule(
                origem="ESTOQUE_MANUAL",
                exige_origem_rastreavel=False,
            )
        return WorkflowOriginRule(
            origem="FINANCEIRA_COMERCIAL",
            exige_origem_rastreavel=False,
        )

    async def validar_despesa_origem_leve(
        self,
        despesa: Despesa,
        *,
        origem_id_override: str | None = None,
        allow_block: bool = False,
    ) -> None:
        regra = self.classificar_origem_despesa(despesa.origem_tipo)
        if not regra.exige_origem_rastreavel:
            return
        if despesa.origem_tipo and despesa.origem_id is not None:
            return

        finding = self.build_finding(
            codigo="DESPESA_AUTOMATICA_SEM_ORIGEM_NOVO_FLUXO",
            titulo="Despesa automática sem origem rastreável",
            severidade="RISCO_CRITICO",
            origem="fin_despesas",
            total=1,
            mensagem=(
                "Despesa automática foi gerada sem origem rastreável completa "
                "(origem_tipo/origem_id)."
            ),
            amostras=[str(despesa.id)] if getattr(despesa, "id", None) else [],
            meta={
                "despesa_id": str(despesa.id) if getattr(despesa, "id", None) else None,
                "origem_tipo": despesa.origem_tipo,
                "classificacao_origem": regra.origem,
            },
        )
        await self.registrar_e_aplicar_enforcement(
            WorkflowGovernanceEvent(
                finding=finding,
                resource_id=str(despesa.id) if getattr(despesa, "id", None) else None,
                action="auto_exp_origin",
                notify=True,
                audit=True,
                origem_id=origem_id_override or f"despesa:{despesa.id}:missing_origin",
            ),
            allow_block=allow_block,
            error_message=(
                "Nao e possivel registrar despesa automatica sem origem rastreavel. "
                "Revise origem_tipo e origem_id do fluxo operacional."
            ),
        )

    async def validar_cost_allocation_unica_origem(
        self,
        allocation: CostAllocation,
        *,
        allow_block: bool = False,
        origem_id_override: str | None = None,
        include_pending: bool = False,
    ) -> None:
        origin_key = allocation.operation_execution_id or allocation.inventory_movement_id or allocation.fin_rateio_id or allocation.source_id
        if origin_key is None:
            return

        if allocation.source == "OPERATION_EXECUTION":
            filtro_origem = CostAllocation.operation_execution_id == origin_key
        elif allocation.source == "INVENTORY_MOVEMENT":
            filtro_origem = CostAllocation.inventory_movement_id == origin_key
        elif allocation.source == "FIN_RATEIO":
            filtro_origem = CostAllocation.fin_rateio_id == origin_key
        else:
            filtro_origem = CostAllocation.source_id == origin_key

        existentes_pendentes = 0
        if include_pending:
            for obj in self.session.new:
                if not isinstance(obj, CostAllocation):
                    continue
                if obj is allocation:
                    continue
                if obj.tenant_id != self.tenant_id:
                    continue
                if obj.source != allocation.source or obj.production_unit_id != allocation.production_unit_id:
                    continue
                obj_origin_key = obj.operation_execution_id or obj.inventory_movement_id or obj.fin_rateio_id or obj.source_id
                if obj_origin_key == origin_key:
                    existentes_pendentes += 1

        stmt = select(func.count(CostAllocation.id)).where(
            CostAllocation.tenant_id == self.tenant_id,
            CostAllocation.source == allocation.source,
            CostAllocation.production_unit_id == allocation.production_unit_id,
            filtro_origem,
        )
        existentes = existentes_pendentes + int((await self.session.execute(stmt)).scalar_one() or 0)
        if existentes == 0:
            return

        finding = self.build_finding(
            codigo="ALLOCATION_POTENCIALMENTE_DUPLICADA",
            titulo="Cost allocation duplicada para a mesma origem",
            severidade="RISCO_CRITICO",
            origem="cost_allocations",
            total=existentes,
            mensagem=(
                "Nao e possivel registrar cost allocation duplicada para a mesma origem "
                "e unidade produtiva."
            ),
            amostras=[f"{allocation.source}:{origin_key}:{allocation.production_unit_id}"],
            meta={
                "source": allocation.source,
                "source_id": str(origin_key),
                "production_unit_id": str(allocation.production_unit_id) if allocation.production_unit_id else None,
                "existentes": existentes,
            },
        )
        await self.registrar_e_aplicar_enforcement(
            WorkflowGovernanceEvent(
                finding=finding,
                resource_id=str(origin_key),
                action="alloc_dup",
                notify=True,
                audit=True,
                origem_id=origem_id_override or f"allocation:{origin_key}:duplicate",
            ),
            allow_block=allow_block,
            error_message=(
                "Nao e possivel registrar cost allocation duplicada para a mesma origem. "
                "Revise a origem operacional e evite duplicidade de apropriação."
            ),
        )

    async def validar_despesa_automatica_unica_origem(
        self,
        despesa: Despesa,
        *,
        allow_block: bool = False,
        origem_id_override: str | None = None,
    ) -> None:
        if despesa.origem_tipo not in TIPOS_DESPESA_AUTOMATICA or despesa.origem_id is None:
            return

        stmt = (
            select(func.count(Despesa.id))
            .where(
                Despesa.tenant_id == self.tenant_id,
                Despesa.origem_tipo == despesa.origem_tipo,
                Despesa.origem_id == despesa.origem_id,
                Despesa.ativo == True,
                Despesa.id != despesa.id,
            )
        )
        if despesa.grupo_parcela_id is not None:
            stmt = stmt.where(
                or_(
                    Despesa.grupo_parcela_id.is_(None),
                    Despesa.grupo_parcela_id != despesa.grupo_parcela_id,
                )
            )

        existentes = int((await self.session.execute(stmt)).scalar_one() or 0)
        if existentes == 0:
            return

        finding = self.build_finding(
            codigo="DESPESA_AUTOMATICA_DUPLICADA_MESMA_ORIGEM",
            titulo="Despesa automática duplicada para a mesma origem",
            severidade="RISCO_CRITICO",
            origem="fin_despesas",
            total=existentes,
            mensagem=(
                "Nao e possivel registrar despesa automatica duplicada para a mesma origem."
            ),
            amostras=[f"{despesa.origem_tipo}:{despesa.origem_id}"],
            meta={
                "origem_tipo": despesa.origem_tipo,
                "origem_id": str(despesa.origem_id),
                "grupo_parcela_id": str(despesa.grupo_parcela_id) if despesa.grupo_parcela_id else None,
                "existentes": existentes,
            },
        )
        await self.registrar_e_aplicar_enforcement(
            WorkflowGovernanceEvent(
                finding=finding,
                resource_id=str(despesa.id) if getattr(despesa, "id", None) else None,
                action="exp_dup",
                notify=True,
                audit=True,
                origem_id=origem_id_override or f"despesa:{despesa.id}:duplicate",
            ),
            allow_block=allow_block,
            error_message=(
                "Nao e possivel registrar despesa automatica duplicada para a mesma origem. "
                "Revise o fluxo financeiro e remova o lançamento duplicado."
            ),
        )

    def get_workflow_enforcement_mode(self) -> str:
        mode = (WORKFLOW_ENFORCEMENT_MODE or WORKFLOW_ENFORCEMENT_WARNING_ONLY).strip().upper()
        if mode not in WORKFLOW_ENFORCEMENT_BLOCKED_SEVERITIES:
            return WORKFLOW_ENFORCEMENT_WARNING_ONLY
        return mode

    def deve_bloquear_severidade(self, severidade: str) -> bool:
        blocked = WORKFLOW_ENFORCEMENT_BLOCKED_SEVERITIES.get(self.get_workflow_enforcement_mode(), set())
        if severidade in blocked:
            return True
        return normalizar_severidade(severidade) in blocked

    async def registrar_e_aplicar_enforcement(
        self,
        event: WorkflowGovernanceEvent,
        *,
        allow_block: bool,
        error_message: str | None = None,
    ) -> None:
        await self.registrar_ocorrencia_governanca(event)
        if not allow_block:
            return
        if not self.deve_bloquear_severidade(event.finding.severidade):
            return
        raise BusinessRuleError(error_message or event.finding.mensagem)

    async def registrar_ocorrencia_governanca(self, event: WorkflowGovernanceEvent) -> None:
        finding = event.finding
        logger.warning(
            "workflow_governance_inconsistency",
            tenant_id=str(self.tenant_id),
            codigo=finding.codigo,
            severidade=finding.severidade,
            total=finding.total,
            origem=finding.origem,
            amostras=finding.amostras,
            resource_id=event.resource_id,
            action=event.action,
        )

        if event.notify:
            await self.notif_svc.criar_sem_duplicar(
                NotificacaoCreate(
                    tipo="WORKFLOW_OPERACIONAL",
                    titulo=finding.titulo,
                    mensagem=finding.mensagem,
                    nivel=SEVERITY_NOTIFICATION_LEVEL.get(finding.severidade, "WARNING"),
                    origem=WORKFLOW_GOVERNANCE_ORIGIN,
                    origem_id=event.origem_id or finding.codigo,
                    meta={
                        "codigo": finding.codigo,
                        "severidade": finding.severidade,
                        "total": finding.total,
                        "origem": finding.origem,
                        "amostras": finding.amostras,
                        "resource_id": event.resource_id,
                        "action": event.action,
                        **finding.meta,
                    },
                )
            )

        if event.audit:
            resource_uuid = None
            if event.resource_id:
                try:
                    resource_uuid = UUID(event.resource_id)
                except ValueError:
                    resource_uuid = None
            await write_audit_log(
                self.session,
                tenant_id=self.tenant_id,
                user_id=None,
                action=event.action,
                resource=WORKFLOW_GOVERNANCE_RESOURCE,
                resource_id=resource_uuid,
                payload_before=None,
                payload_after=finding.to_payload(),
                ip_address=None,
            )
            await self.session.flush()

    def build_finding(
        self,
        *,
        codigo: str,
        titulo: str,
        severidade: str,
        origem: str,
        total: int,
        mensagem: str,
        amostras: list[str] | None = None,
        meta: dict | None = None,
    ) -> WorkflowGovernanceFinding:
        return WorkflowGovernanceFinding(
            codigo=codigo,
            titulo=titulo,
            severidade=severidade,
            origem=origem,
            total=total,
            mensagem=mensagem,
            amostras=amostras or [],
            meta=meta or {},
        )

    async def _detectar_tarefa_concluida_sem_operacao(self) -> WorkflowGovernanceFinding | None:
        stmt = (
            select(SafraTarefa.id, SafraTarefa.tipo)
            .where(
                SafraTarefa.tenant_id == self.tenant_id,
                SafraTarefa.status == "CONCLUIDA",
                SafraTarefa.operacao_id.is_(None),
                SafraTarefa.tipo.in_(TIPOS_TAREFA_OPERACIONAL),
            )
            .order_by(SafraTarefa.updated_at.desc())
        )
        rows = list((await self.session.execute(stmt)).all())
        if not rows:
            return None
        return self._build_finding(
            codigo="TAREFA_CONCLUIDA_SEM_OPERACAO",
            titulo="Tarefa operacional concluída sem operação",
            severidade="INCONSISTENCIA_MODERADA",
            origem="safra_tarefas",
            rows=rows,
            mensagem=(
                f"{len(rows)} tarefa(s) operacional(is) foram concluídas sem operação vinculada. "
                "O fechamento permanece permitido, mas precisa de saneamento."
            ),
            meta={"tipos_tarefa": sorted({row.tipo for row in rows if row.tipo})},
        )

    async def _detectar_operacao_sem_execucao(self) -> WorkflowGovernanceFinding | None:
        stmt = (
            select(OperacaoAgricola.id, OperacaoAgricola.tipo)
            .outerjoin(OperacaoExecucao, OperacaoExecucao.operacao_id == OperacaoAgricola.id)
            .where(
                OperacaoAgricola.tenant_id == self.tenant_id,
                OperacaoAgricola.status == "REALIZADA",
                OperacaoExecucao.id.is_(None),
            )
            .order_by(OperacaoAgricola.updated_at.desc())
        )
        rows = list((await self.session.execute(stmt)).all())
        if not rows:
            return None
        return self._build_finding(
            codigo="OPERACAO_REALIZADA_SEM_EXECUCAO",
            titulo="Operação realizada sem execução",
            severidade="INCONSISTENCIA_MODERADA",
            origem="operacoes_agricolas",
            rows=rows,
            mensagem=(
                f"{len(rows)} operação(ões) marcada(s) como realizada(s) não possuem "
                "registro em operações_execucoes."
            ),
            meta={"tipos_operacao": sorted({row.tipo for row in rows if row.tipo})},
        )

    async def _detectar_operacao_com_custo_sem_allocation(self) -> WorkflowGovernanceFinding | None:
        stmt = (
            select(OperacaoAgricola.id, OperacaoAgricola.tipo)
            .outerjoin(OperacaoExecucao, OperacaoExecucao.operacao_id == OperacaoAgricola.id)
            .outerjoin(CostAllocation, CostAllocation.operation_execution_id == OperacaoExecucao.id)
            .where(
                OperacaoAgricola.tenant_id == self.tenant_id,
                OperacaoAgricola.status == "REALIZADA",
                OperacaoAgricola.production_unit_id.is_not(None),
                OperacaoAgricola.custo_total.is_not(None),
                OperacaoAgricola.custo_total > 0,
            )
            .group_by(OperacaoAgricola.id, OperacaoAgricola.tipo)
            .having(func.count(CostAllocation.id) == 0)
            .order_by(OperacaoAgricola.updated_at.desc())
        )
        rows = list((await self.session.execute(stmt)).all())
        if not rows:
            return None
        return self._build_finding(
            codigo="OPERACAO_COM_CUSTO_SEM_ALLOCATION",
            titulo="Operação com custo sem apropriação",
            severidade="RISCO_ECONOMICO",
            origem="operacoes_agricolas",
            rows=rows,
            mensagem=(
                f"{len(rows)} operação(ões) com custo e production_unit definida ainda não geraram "
                "CostAllocation rastreável."
            ),
            meta={"tipos_operacao": sorted({row.tipo for row in rows if row.tipo})},
        )

    async def _detectar_apontamento_com_custo_sem_contexto(self) -> WorkflowGovernanceFinding | None:
        stmt = (
            select(ApontamentoUso.id)
            .where(
                ApontamentoUso.tenant_id == self.tenant_id,
                ApontamentoUso.custo_total.is_not(None),
                ApontamentoUso.custo_total > 0,
                ApontamentoUso.operacao_id.is_(None),
                ApontamentoUso.jornada_id.is_(None),
                or_(
                    ApontamentoUso.safra_id.is_(None),
                    ApontamentoUso.production_unit_id.is_(None),
                ),
            )
            .order_by(ApontamentoUso.created_at.desc())
        )
        rows = list((await self.session.execute(stmt)).all())
        if not rows:
            return None
        return self._build_finding(
            codigo="APONTAMENTO_COM_CUSTO_SEM_CONTEXTO",
            titulo="Apontamento com custo sem contexto operacional",
            severidade="RISCO_ECONOMICO",
            origem="frota_apontamentos_uso",
            rows=rows,
            mensagem=(
                f"{len(rows)} apontamento(s) possuem custo, mas sem operação/jornada e sem "
                "contexto operacional completo."
            ),
            meta={},
        )

    async def _detectar_pedido_recebido_sem_movimento_ou_lote(self) -> WorkflowGovernanceFinding | None:
        stmt = (
            select(PedidoCompra.id)
            .outerjoin(
                EstoqueMovimento,
                and_(
                    EstoqueMovimento.tenant_id == self.tenant_id,
                    EstoqueMovimento.origem == "COMPRA",
                    EstoqueMovimento.origem_id == PedidoCompra.id,
                ),
            )
            .outerjoin(RecebimentoParcial, RecebimentoParcial.pedido_id == PedidoCompra.id)
            .outerjoin(ItemRecebimento, ItemRecebimento.recebimento_id == RecebimentoParcial.id)
            .where(
                PedidoCompra.tenant_id == self.tenant_id,
                PedidoCompra.status == "RECEBIDO",
            )
            .group_by(PedidoCompra.id)
            .having(
                or_(
                    func.count(EstoqueMovimento.id) == 0,
                    func.count(ItemRecebimento.lote_id) == 0,
                )
            )
            .order_by(func.max(PedidoCompra.updated_at).desc())
        )
        rows = list((await self.session.execute(stmt)).all())
        if not rows:
            return None
        return self._build_finding(
            codigo="PEDIDO_RECEBIDO_SEM_MOVIMENTO_OU_LOTE",
            titulo="Pedido recebido sem movimento ou lote completo",
            severidade="RISCO_CRITICO",
            origem="compras_pedidos",
            rows=rows,
            mensagem=(
                f"{len(rows)} pedido(s) recebidos não possuem trilha completa de estoque "
                "e/ou lote para valuation."
            ),
            meta={},
        )

    async def _detectar_despesa_automatica_sem_origem(self) -> WorkflowGovernanceFinding | None:
        stmt = (
            select(Despesa.id, Despesa.origem_tipo)
            .where(
                Despesa.tenant_id == self.tenant_id,
                Despesa.origem_tipo.in_(TIPOS_DESPESA_AUTOMATICA),
                Despesa.origem_id.is_(None),
            )
            .order_by(Despesa.updated_at.desc())
        )
        rows = list((await self.session.execute(stmt)).all())
        if not rows:
            return None
        return self._build_finding(
            codigo="DESPESA_AUTOMATICA_SEM_ORIGEM",
            titulo="Despesa automática sem origem rastreável",
            severidade="RISCO_CRITICO",
            origem="fin_despesas",
            rows=rows,
            mensagem=(
                f"{len(rows)} despesa(s) automática(s) estão sem origem_id, comprometendo "
                "a rastreabilidade econômica."
            ),
            meta={"origens": sorted({row.origem_tipo for row in rows if row.origem_tipo})},
        )

    async def _detectar_allocations_duplicadas(self) -> WorkflowGovernanceFinding | None:
        stmt = (
            select(
                CostAllocation.source,
                CostAllocation.source_id,
                CostAllocation.production_unit_id,
                func.count(CostAllocation.id).label("duplicidades"),
            )
            .where(CostAllocation.tenant_id == self.tenant_id)
            .group_by(
                CostAllocation.source,
                CostAllocation.source_id,
                CostAllocation.production_unit_id,
            )
            .having(
                CostAllocation.source_id.is_not(None),
                func.count(CostAllocation.id) > 1,
            )
            .order_by(func.count(CostAllocation.id).desc())
        )
        rows = list((await self.session.execute(stmt)).all())
        if not rows:
            return None
        return WorkflowGovernanceFinding(
            codigo="ALLOCATION_POTENCIALMENTE_DUPLICADA",
            titulo="Cost allocation potencialmente duplicada",
            severidade="RISCO_CRITICO",
            origem="cost_allocations",
            total=len(rows),
            mensagem=(
                f"{len(rows)} combinação(ões) de source/source_id/production_unit aparecem "
                "mais de uma vez em cost_allocations."
            ),
            amostras=[
                f"{row.source}:{row.source_id}:{row.production_unit_id}"
                for row in rows[:10]
            ],
            meta={
                "maior_duplicidade": max(int(row.duplicidades or 0) for row in rows),
            },
        )

    async def _detectar_allocation_sem_reflexo_economico(self) -> WorkflowGovernanceFinding | None:
        # A reconciliação CostAllocation (OPERATION_EXECUTION) x Despesa(OPERACAO_AGRICOLA) foi
        # aposentada em SOIL-PLAN-EXEC-04I: a despesa deixou de ser criada para operações novas, e
        # CostAllocation passou a ser a única fonte de custo produtivo — a ausência de despesa é o
        # estado normal, não mais um risco. A reconciliação de estoque abaixo permanece válida.
        estoque_stmt = (
            select(
                CostAllocation.id,
                CostAllocation.source,
                CostAllocation.source_id,
                CostAllocation.amount,
                EstoqueMovimento.id.label("movimento_id"),
            )
            .join(EstoqueMovimento, CostAllocation.inventory_movement_id == EstoqueMovimento.id)
            .outerjoin(
                LancamentoFinanceiro,
                and_(
                    LancamentoFinanceiro.tenant_id == self.tenant_id,
                    LancamentoFinanceiro.origem == "ESTOQUE",
                    LancamentoFinanceiro.origem_id == EstoqueMovimento.id,
                ),
            )
            .where(
                CostAllocation.tenant_id == self.tenant_id,
                CostAllocation.source == "INVENTORY_MOVEMENT",
                CostAllocation.amount > 0,
                CostAllocation.inventory_movement_id.is_not(None),
                LancamentoFinanceiro.id.is_(None),
            )
        )

        estoque_rows = list((await self.session.execute(estoque_stmt)).all())
        if not estoque_rows:
            return None

        return self._build_finding(
            codigo="CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO",
            titulo="Custo operacional sem reflexo econômico",
            severidade="RISCO_ECONOMICO",
            origem="reconciliacao_economica",
            rows=estoque_rows,
            mensagem=(
                f"{len(estoque_rows)} apropriação(ões) econômicas de estoque não encontraram "
                "reflexo financeiro compatível em lançamento."
            ),
            meta={
                "estoques_sem_lancamento": len(estoque_rows),
            },
        )

    async def _detectar_cost_allocation_sem_origem_rastreavel(self) -> WorkflowGovernanceFinding | None:
        stmt = (
            select(
                CostAllocation.id,
                CostAllocation.source,
                CostAllocation.source_id,
                CostAllocation.production_unit_id,
                CostAllocation.amount,
            )
            .where(
                CostAllocation.tenant_id == self.tenant_id,
                CostAllocation.source == "MANUAL",
                CostAllocation.source_id.is_(None),
                CostAllocation.amount > 0,
            )
            .order_by(CostAllocation.created_at.desc())
        )
        rows = list((await self.session.execute(stmt)).all())
        if not rows:
            return None
        return self._build_finding(
            codigo="COST_ALLOCATION_SEM_ORIGEM_RASTREAVEL",
            titulo="Cost allocation sem origem rastreável",
            severidade="INCONSISTENCIA_MODERADA",
            origem="cost_allocations",
            rows=rows,
            mensagem=(
                f"{len(rows)} cost allocation(s) manuais não possuem origem_id rastreável."
            ),
            meta={
                "origens": sorted({row.source for row in rows if row.source}),
            },
        )

    async def _detectar_despesa_automatica_duplicada_mesma_origem(self) -> WorkflowGovernanceFinding | None:
        stmt = (
            select(
                Despesa.origem_tipo,
                Despesa.origem_id,
                func.count(Despesa.id).label("duplicidades"),
                func.count(func.distinct(func.coalesce(Despesa.grupo_parcela_id, Despesa.id))).label("grupos_distintos"),
                func.sum(Despesa.valor_total).label("valor_total"),
            )
            .where(
                Despesa.tenant_id == self.tenant_id,
                Despesa.origem_tipo.in_(TIPOS_DESPESA_AUTOMATICA),
                Despesa.origem_id.is_not(None),
            )
            .group_by(Despesa.origem_tipo, Despesa.origem_id)
            .having(func.count(func.distinct(func.coalesce(Despesa.grupo_parcela_id, Despesa.id))) > 1)
            .order_by(func.count(Despesa.id).desc())
        )
        rows = list((await self.session.execute(stmt)).all())
        if not rows:
            return None
        return self._build_finding(
            codigo="DESPESA_AUTOMATICA_DUPLICADA_MESMA_ORIGEM",
            titulo="Despesa automática duplicada para a mesma origem",
            severidade="RISCO_CRITICO",
            origem="fin_despesas",
            rows=rows,
            mensagem=(
                f"{len(rows)} origem(ns) automática(s) de despesa foram lançadas mais de uma vez."
            ),
            meta={
                "maior_duplicidade": max(int(row.duplicidades or 0) for row in rows),
                "grupos_distintos": max(int(getattr(row, "grupos_distintos", 0) or 0) for row in rows),
                "origens": [f"{row.origem_tipo}:{row.origem_id}" for row in rows[:10]],
            },
        )

    async def _detectar_movimento_com_custo_sem_allocation(self) -> WorkflowGovernanceFinding | None:
        stmt = (
            select(
                EstoqueMovimento.id,
                EstoqueMovimento.origem,
                EstoqueMovimento.origem_id,
                EstoqueMovimento.custo_total,
                func.count(CostAllocation.id).label("allocations"),
                func.count(LancamentoFinanceiro.id).label("lancamentos"),
            )
            .outerjoin(
                CostAllocation,
                and_(
                    CostAllocation.tenant_id == self.tenant_id,
                    CostAllocation.inventory_movement_id == EstoqueMovimento.id,
                ),
            )
            .outerjoin(
                LancamentoFinanceiro,
                and_(
                    LancamentoFinanceiro.tenant_id == self.tenant_id,
                    LancamentoFinanceiro.origem == "ESTOQUE",
                    LancamentoFinanceiro.origem_id == EstoqueMovimento.id,
                ),
            )
            .where(
                EstoqueMovimento.tenant_id == self.tenant_id,
                EstoqueMovimento.custo_total.is_not(None),
                EstoqueMovimento.custo_total > 0,
                EstoqueMovimento.origem.in_(["COMPRA", "ORDEM_SERVICO", "OPERACAO_EXECUCAO"]),
            )
            .group_by(
                EstoqueMovimento.id,
                EstoqueMovimento.origem,
                EstoqueMovimento.origem_id,
                EstoqueMovimento.custo_total,
            )
            .having(
                and_(
                    func.count(CostAllocation.id) == 0,
                    func.count(LancamentoFinanceiro.id) > 0,
                )
            )
            .order_by(EstoqueMovimento.created_at.desc())
        )
        rows = list((await self.session.execute(stmt)).all())
        if not rows:
            return None
        return self._build_finding(
            codigo="MOVIMENTO_COM_CUSTO_SEM_ALLOCATION",
            titulo="Movimento de estoque com custo sem apropriação",
            severidade="RISCO_ECONOMICO",
            origem="estoque_movimentos",
            rows=rows,
            mensagem=(
                f"{len(rows)} movimento(s) de estoque possuem custo e reflexo financeiro, mas sem apropriação de custo (rateio)."
            ),
            meta={
                "origens": sorted({row.origem for row in rows if row.origem}),
            },
        )

    async def _detectar_divergencia_valor_operacional_apropriado(self) -> WorkflowGovernanceFinding | None:
        op_stmt = (
            select(
                OperacaoAgricola.id.label("operacao_id"),
                OperacaoAgricola.tipo.label("operacao_tipo"),
                OperacaoAgricola.descricao.label("operacao_descricao"),
                OperacaoAgricola.data_realizada.label("operacao_data"),
                OperacaoAgricola.custo_total.label("valor_operacional"),
                func.coalesce(func.sum(CostAllocation.amount), 0).label("valor_apropriado"),
                (OperacaoAgricola.custo_total - func.coalesce(func.sum(CostAllocation.amount), 0)).label("diferenca"),
            )
            .join(OperacaoExecucao, OperacaoExecucao.operacao_id == OperacaoAgricola.id)
            .outerjoin(
                CostAllocation,
                and_(
                    CostAllocation.tenant_id == self.tenant_id,
                    CostAllocation.source == "OPERATION_EXECUTION",
                    CostAllocation.operation_execution_id == OperacaoExecucao.id,
                ),
            )
            .where(
                OperacaoAgricola.tenant_id == self.tenant_id,
                OperacaoAgricola.custo_total.is_not(None),
                OperacaoAgricola.custo_total > 0,
                OperacaoAgricola.status == "REALIZADA",
            )
            .group_by(
                OperacaoAgricola.id,
                OperacaoAgricola.tipo,
                OperacaoAgricola.descricao,
                OperacaoAgricola.data_realizada,
                OperacaoAgricola.custo_total,
            )
            .having(func.abs(func.coalesce(func.sum(CostAllocation.amount), 0) - OperacaoAgricola.custo_total) > 0.01)
        )

        mov_stmt = (
            select(
                EstoqueMovimento.id.label("movimento_id"),
                EstoqueMovimento.tipo_movimento.label("movimento_tipo"),
                EstoqueMovimento.numero_lote.label("movimento_numero_lote"),
                EstoqueMovimento.data_movimento.label("movimento_data"),
                EstoqueMovimento.custo_total.label("valor_operacional"),
                func.coalesce(func.sum(CostAllocation.amount), 0).label("valor_apropriado"),
                (EstoqueMovimento.custo_total - func.coalesce(func.sum(CostAllocation.amount), 0)).label("diferenca"),
            )
            .outerjoin(
                CostAllocation,
                and_(
                    CostAllocation.tenant_id == self.tenant_id,
                    CostAllocation.inventory_movement_id == EstoqueMovimento.id,
                    or_(
                        CostAllocation.source == "INVENTORY_MOVEMENT",
                        and_(
                            CostAllocation.source == "OPERATION_EXECUTION",
                            EstoqueMovimento.origem == "OPERACAO_EXECUCAO",
                            CostAllocation.operation_execution_id == EstoqueMovimento.operacao_execucao_id,
                            CostAllocation.production_unit_id == EstoqueMovimento.production_unit_id,
                        ),
                    ),
                ),
            )
            .where(
                EstoqueMovimento.tenant_id == self.tenant_id,
                EstoqueMovimento.custo_total.is_not(None),
                EstoqueMovimento.custo_total > 0,
                EstoqueMovimento.origem.in_(["COMPRA", "ORDEM_SERVICO", "OPERACAO_EXECUCAO"]),
            )
            .group_by(
                EstoqueMovimento.id,
                EstoqueMovimento.tipo_movimento,
                EstoqueMovimento.numero_lote,
                EstoqueMovimento.data_movimento,
                EstoqueMovimento.custo_total,
            )
            .having(func.abs(func.coalesce(func.sum(CostAllocation.amount), 0) - EstoqueMovimento.custo_total) > 0.01)
        )

        op_rows = list((await self.session.execute(op_stmt)).all())
        mov_rows = list((await self.session.execute(mov_stmt)).all())
        if not op_rows and not mov_rows:
            return None

        maiores_diferencas = [
            abs(float(row.diferenca or 0))
            for row in [*op_rows, *mov_rows]
        ]
        maior_diferenca = max(maiores_diferencas) if maiores_diferencas else 0.0
        if maior_diferenca <= 1.0:
            severidade = "WARNING_LEVE"
        elif maior_diferenca <= 5.0:
            severidade = "INCONSISTENCIA_MODERADA"
        else:
            severidade = "RISCO_ECONOMICO"

        amostras = [
            f"OS {row.operacao_tipo} — {row.operacao_descricao} ({row.operacao_data.strftime('%d/%m/%Y')}) · diferença R$ {abs(float(row.diferenca or 0)):.2f}"
            for row in op_rows[:5]
        ] + [
            f"Movimento {row.movimento_tipo}"
            f"{' — lote ' + row.movimento_numero_lote if row.movimento_numero_lote else ''}"
            f" ({row.movimento_data.strftime('%d/%m/%Y')}) · diferença R$ {abs(float(row.diferenca or 0)):.2f}"
            for row in mov_rows[:5]
        ]

        return self.build_finding(
            codigo="DIVERGENCIA_VALOR_OPERACIONAL_APROPRIADO",
            titulo="Divergência entre custo operacional e valor apropriado",
            severidade=severidade,
            origem="reconciliacao_economica",
            total=len(op_rows) + len(mov_rows),
            mensagem=(
                f"{len(op_rows) + len(mov_rows)} registro(s) apresentam diferença relevante entre custo operacional e valor apropriado."
            ),
            amostras=amostras,
            meta={
                "operacoes_divergentes": len(op_rows),
                "movimentos_divergentes": len(mov_rows),
                "maior_diferenca": round(maior_diferenca, 2),
                "operacao_ids": [str(row.operacao_id) for row in op_rows[:10]],
                "movimento_ids": [str(row.movimento_id) for row in mov_rows[:10]],
            },
        )

    def _build_finding(
        self,
        *,
        codigo: str,
        titulo: str,
        severidade: str,
        origem: str,
        rows: list,
        mensagem: str,
        meta: dict,
    ) -> WorkflowGovernanceFinding:
        return self.build_finding(
            codigo=codigo,
            titulo=titulo,
            severidade=severidade,
            origem=origem,
            total=len(rows),
            mensagem=mensagem,
            amostras=[str(self._extract_identifier(row)) for row in rows[:10]],
            meta=meta,
        )

    def _extract_identifier(self, row: object) -> str:
        if hasattr(row, "id"):
            return str(row.id)
        if isinstance(row, tuple) and row:
            return str(row[0])
        if hasattr(row, "_mapping"):
            mapping = row._mapping
            for key in ("id", "source", "source_id"):
                if key in mapping:
                    return str(mapping[key])
            for key, value in mapping.items():
                if key == "id" or key.endswith("_id"):
                    return str(value)
            if mapping:
                return str(next(iter(mapping.values())))
        return str(row)

    def _classificar_tipo_relatorio(self, codigo: str) -> str:
        return classificar_tipo_relatorio(codigo)

    def _sugerir_correcao_relatorio(self, finding: WorkflowGovernanceFinding) -> str:
        sugestoes = {
            "TAREFA_CONCLUIDA_SEM_OPERACAO": "Vincular operação agrícola ou registrar justificativa operacional no fechamento.",
            "OPERACAO_REALIZADA_SEM_EXECUCAO": "Criar OperacaoExecucao correspondente para o novo fluxo.",
            "OPERACAO_COM_CUSTO_SEM_ALLOCATION": "Gerar CostAllocation para a execução ou revisar ProductionUnit.",
            "APONTAMENTO_COM_CUSTO_SEM_CONTEXTO": "Associar operação, jornada ou contextos mínimos antes do fechamento.",
            "PEDIDO_RECEBIDO_SEM_MOVIMENTO_OU_LOTE": "Materializar lote, movimento e saldo antes de manter o pedido como RECEBIDO.",
            "DESPESA_AUTOMATICA_SEM_ORIGEM": "Preencher origem_tipo e origem_id no lançamento automático.",
            "ALLOCATION_POTENCIALMENTE_DUPLICADA": "Eliminar lançamentos duplicados e manter apenas uma apropriação por origem.",
            "CUSTO_OPERACIONAL_SEM_REFLEXO_ECONOMICO": "Gerar reflexo financeiro ou reclassificar a apropriação econômica.",
            "COST_ALLOCATION_SEM_ORIGEM_RASTREAVEL": "Resolver a origem operacional antes de manter o rateio manual.",
            "DESPESA_AUTOMATICA_DUPLICADA_MESMA_ORIGEM": "Remover a duplicidade e consolidar o lançamento automático.",
            "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION": "Criar CostAllocation para o movimento com custo ou registrar justificativa.",
            "DIVERGENCIA_VALOR_OPERACIONAL_APROPRIADO": "Reconciliar o valor operacional com a soma das apropriações.",
            "DEVOLUCAO_SEM_MOVIMENTO_ORIGINAL": "Vincular o movimento de entrada original antes de concluir a devolução.",
        }
        return sugestoes.get(
            finding.codigo,
            "Revisar a origem operacional e corrigir a rastreabilidade antes do saneamento.",
        )

    def _extrair_detalhes_origem_relatorio(self, finding: WorkflowGovernanceFinding) -> tuple[str | None, str | None]:
        if finding.codigo == "ALLOCATION_POTENCIALMENTE_DUPLICADA" and finding.amostras:
            parts = finding.amostras[0].split(":")
            if len(parts) >= 3:
                return parts[0], parts[1]
        if finding.codigo == "DESPESA_AUTOMATICA_DUPLICADA_MESMA_ORIGEM" and finding.amostras:
            parts = finding.amostras[0].split(":")
            if len(parts) >= 2:
                return parts[0], parts[1]
        if finding.codigo == "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION" and finding.amostras:
            return "INVENTORY_MOVEMENT", finding.amostras[0]
        if finding.codigo in {"TAREFA_CONCLUIDA_SEM_OPERACAO", "OPERACAO_REALIZADA_SEM_EXECUCAO", "OPERACAO_COM_CUSTO_SEM_ALLOCATION"} and finding.amostras:
            return self._classificar_tipo_relatorio(finding.codigo), finding.amostras[0]
        if finding.codigo in {"PEDIDO_RECEBIDO_SEM_MOVIMENTO_OU_LOTE", "DEVOLUCAO_SEM_MOVIMENTO_ORIGINAL"} and finding.amostras:
            return "COMPRA", finding.amostras[0]
        if finding.codigo in {"DESPESA_AUTOMATICA_SEM_ORIGEM", "COST_ALLOCATION_SEM_ORIGEM_RASTREAVEL"} and finding.amostras:
            return self._classificar_tipo_relatorio(finding.codigo), finding.amostras[0]
        return None, None

    def _finding_para_relatorio(self, finding: WorkflowGovernanceFinding) -> WorkflowGovernanceReportItem:
        origem_tipo, origem_id = self._extrair_detalhes_origem_relatorio(finding)
        return WorkflowGovernanceReportItem(
            codigo=finding.codigo,
            titulo=finding.titulo,
            severidade=finding.severidade,
            tipo_inconsistencia=self._classificar_tipo_relatorio(finding.codigo),
            origem=finding.origem,
            origem_tipo=origem_tipo,
            origem_id=origem_id,
            total=finding.total,
            mensagem=finding.mensagem,
            sugestao_correcao=self._sugerir_correcao_relatorio(finding),
            amostras=list(finding.amostras),
            meta=dict(finding.meta),
        )

    async def _detectar_devolucao_sem_movimento_original(self) -> WorkflowGovernanceFinding | None:
        stmt = (
            select(DevolucaoFornecedor.id, DevolucaoFornecedor.pedido_id)
            .where(
                DevolucaoFornecedor.tenant_id == self.tenant_id,
                DevolucaoFornecedor.status.in_(["ABERTA", "ENVIADA", "CONCLUIDA"]),
            )
        )
        devolucoes = list((await self.session.execute(stmt)).all())
        if not devolucoes:
            return None

        devolucao_rows = [
            (row.id, row.pedido_id) if hasattr(row, "id") else (row[0], row[1])
            for row in devolucoes
        ]
        problematics: list[tuple[str, str | None]] = []
        itens_stmt = select(ItemDevolucao).where(ItemDevolucao.devolucao_id.in_([row_id for row_id, _ in devolucao_rows]))
        itens = list((await self.session.execute(itens_stmt)).scalars().all())
        itens_por_devolucao: dict[UUID, list[ItemDevolucao]] = defaultdict(list)
        for item in itens:
            itens_por_devolucao[item.devolucao_id].append(item)

        pedido_ids = [pedido_id for _, pedido_id in devolucao_rows if pedido_id is not None]
        chaves_movimento = {
            (pedido_id, item.produto_id, item.deposito_origem_id, item.lote_id)
            for row_id, pedido_id in devolucao_rows
            for item in itens_por_devolucao.get(row_id, [])
            if pedido_id is not None and item.lote_id is not None
        }
        movimentos_encontrados: set[tuple[UUID | str | None, UUID | str | None, UUID | str | None, UUID | str | None]] = set()
        if pedido_ids and chaves_movimento:
            mov_stmt = select(
                EstoqueMovimento.origem_id,
                EstoqueMovimento.produto_id,
                EstoqueMovimento.deposito_id,
                EstoqueMovimento.lote_id,
            ).where(
                EstoqueMovimento.tenant_id == self.tenant_id,
                EstoqueMovimento.origem == "COMPRA",
                EstoqueMovimento.origem_id.in_(pedido_ids),
            )
            movimentos_encontrados = {
                (origem_id, produto_id, deposito_id, lote_id)
                for origem_id, produto_id, deposito_id, lote_id in (await self.session.execute(mov_stmt)).all()
            }

        for row_id, pedido_id in devolucao_rows:
            itens_row = itens_por_devolucao.get(row_id, [])
            if not itens_row:
                continue

            has_issue = False
            for item in itens_row:
                if item.lote_id is None:
                    has_issue = True
                    break
                if pedido_id is None or (
                    pedido_id,
                    item.produto_id,
                    item.deposito_origem_id,
                    item.lote_id,
                ) not in movimentos_encontrados:
                    has_issue = True
                    break

            if has_issue:
                problematics.append((str(row_id), str(pedido_id) if pedido_id else None))

        if not problematics:
            return None

        return WorkflowGovernanceFinding(
            codigo="DEVOLUCAO_SEM_MOVIMENTO_ORIGINAL",
            titulo="Devolução sem movimento original rastreável",
            severidade="RISCO_CRITICO",
            origem="compras_devolucoes",
            total=len(problematics),
            mensagem=(
                f"{len(problematics)} devolução(ões) não possuem movimento original rastreável para saneamento."
            ),
            amostras=[row_id for row_id, _ in problematics[:10]],
            meta={
                "pedidos": [pedido_id for _, pedido_id in problematics[:10] if pedido_id],
            },
        )
