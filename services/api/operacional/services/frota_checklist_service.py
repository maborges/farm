from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.cadastros.equipamentos.alocacao_service import get_equipamento_unidade_operacional
from core.cadastros.equipamentos.models import Equipamento
from core.operational_context import validate_operador_context
from core.exceptions import BusinessRuleError, EntityNotFoundError
from operacional.models.checklist import (
    ChecklistOperacional,
    ChecklistOperacionalItem,
    ChecklistOperacionalResposta,
)
from operacional.models.frota import OrdemServico
from operacional.schemas.frota_checklist import (
    ChecklistOperacionalCreate,
    ChecklistOperacionalPreenchimentoCreate,
    ChecklistOperacionalPreenchimentoResponse,
)


class FrotaChecklistService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def criar_checklist(self, dados: ChecklistOperacionalCreate) -> ChecklistOperacional:
        checklist = ChecklistOperacional(
            tenant_id=self.tenant_id,
            nome=dados.nome.strip(),
            tipo_equipamento=dados.tipo_equipamento.strip() if dados.tipo_equipamento else None,
            tipo_jornada=dados.tipo_jornada,
            exige_antes_operacao=dados.exige_antes_operacao,
            bloqueia_falha_critica=dados.bloqueia_falha_critica,
            ativo=True,
        )
        for item in dados.itens:
            checklist.itens.append(
                ChecklistOperacionalItem(
                    tenant_id=self.tenant_id,
                    categoria=item.categoria,
                    descricao=item.descricao.strip(),
                    obrigatorio=item.obrigatorio,
                    ordem=item.ordem,
                    ativo=True,
                )
            )
        self.session.add(checklist)
        await self.session.flush()
        return checklist

    async def listar_checklists(
        self,
        tipo_equipamento: str | None = None,
        tipo_jornada: str | None = None,
        ativo: bool = True,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[ChecklistOperacional]:
        stmt = (
            select(ChecklistOperacional)
            .options(selectinload(ChecklistOperacional.itens))
            .where(ChecklistOperacional.tenant_id == self.tenant_id)
        )
        if tipo_equipamento is not None:
            stmt = stmt.where(
                or_(
                    ChecklistOperacional.tipo_equipamento == tipo_equipamento,
                    ChecklistOperacional.tipo_equipamento.is_(None),
                )
            )
        if tipo_jornada is not None:
            stmt = stmt.where(ChecklistOperacional.tipo_jornada == tipo_jornada)
        if ativo is not None:
            stmt = stmt.where(ChecklistOperacional.ativo == ativo)
        stmt = stmt.order_by(ChecklistOperacional.tipo_equipamento.desc(), ChecklistOperacional.created_at.desc())
        if skip:
            stmt = stmt.offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list((await self.session.execute(stmt)).scalars().unique().all())

    async def registrar_respostas(
        self,
        dados: ChecklistOperacionalPreenchimentoCreate,
    ) -> ChecklistOperacionalPreenchimentoResponse:
        equipamento = await self._obter_equipamento(dados.equipamento_id)
        checklist = await self._resolver_checklist(
            equipamento=equipamento,
            tipo_jornada=dados.tipo_jornada,
            checklist_id=dados.checklist_id,
            exigir=True,
        )
        if checklist is None:
            raise BusinessRuleError("Checklist operacional não encontrado para o equipamento.")

        unidade_produtiva_id = dados.unidade_produtiva_id
        contexto = await get_equipamento_unidade_operacional(
            self.session,
            tenant_id=self.tenant_id,
            equipamento_id=equipamento.id,
            expected_unidade_produtiva_id=unidade_produtiva_id,
        )
        unidade_produtiva_id = contexto.unidade_produtiva_id

        responsaveis = {
            pessoa_id
            for pessoa_id in (dados.operador_id, dados.executado_por_id, dados.reportado_por_id)
            if pessoa_id is not None
        }
        for pessoa_id in responsaveis:
            await validate_operador_context(
                self.session,
                tenant_id=self.tenant_id,
                operador_id=pessoa_id,
                unidade_produtiva_id=unidade_produtiva_id,
            )
        executado_por_id = dados.executado_por_id or dados.operador_id
        reportado_por_id = dados.reportado_por_id or dados.operador_id

        self._validar_respostas_obrigatorias(checklist, dados)
        itens_por_id = {item.id: item for item in checklist.itens if item.ativo}

        respostas: list[ChecklistOperacionalResposta] = []
        resposta_critica: ChecklistOperacionalResposta | None = None
        for resposta_in in dados.respostas:
            item = itens_por_id.get(resposta_in.item_id)
            if item is None:
                raise BusinessRuleError("Item de checklist inválido para o checklist informado.")
            falha = resposta_in.falha or resposta_in.status == "NAO_CONFORME"
            criticidade = resposta_in.criticidade if falha else None
            resposta = ChecklistOperacionalResposta(
                tenant_id=self.tenant_id,
                checklist_id=checklist.id,
                item_id=item.id,
                equipamento_id=equipamento.id,
                jornada_id=dados.jornada_id,
                operador_id=dados.operador_id,
                executado_por_id=executado_por_id,
                reportado_por_id=reportado_por_id,
                unidade_produtiva_id=unidade_produtiva_id,
                safra_id=dados.safra_id,
                tipo_jornada=dados.tipo_jornada,
                status=resposta_in.status,
                falha=falha,
                criticidade=criticidade,
                observacao=resposta_in.observacao,
                alerta_operacional=falha and criticidade in {"ALTA", "CRITICA"},
            )
            self.session.add(resposta)
            respostas.append(resposta)
            if criticidade == "CRITICA" and resposta_critica is None:
                resposta_critica = resposta

        await self.session.flush()

        os_gerada_id = None
        if dados.gerar_os or resposta_critica is not None:
            origem = resposta_critica or next((item for item in respostas if item.falha), None)
            if origem is not None:
                os_gerada_id = await self._gerar_os_checklist(equipamento, checklist, origem, dados.tipo_jornada)
                for resposta in respostas:
                    if resposta.falha:
                        resposta.os_gerada_id = os_gerada_id

        bloqueou = False
        if resposta_critica is not None and checklist.bloqueia_falha_critica:
            bloqueou = True
            equipamento.bloqueado_operacional = True
            equipamento.motivo_bloqueio_operacional = "Falha crítica registrada em checklist operacional."
            equipamento.bloqueado_operacional_em = datetime.now(timezone.utc)
            await self.session.flush()

        return ChecklistOperacionalPreenchimentoResponse(
            checklist_id=checklist.id,
            equipamento_id=equipamento.id,
            bloqueou_operacao=bloqueou,
            os_gerada_id=os_gerada_id,
            respostas=respostas,
        )

    async def validar_checklist_obrigatorio_abertura(
        self,
        equipamento: Equipamento,
        preenchimento: ChecklistOperacionalPreenchimentoCreate | None,
    ) -> ChecklistOperacionalPreenchimentoResponse | None:
        checklist = await self._resolver_checklist(
            equipamento=equipamento,
            tipo_jornada="ABERTURA",
            checklist_id=preenchimento.checklist_id if preenchimento else None,
            exigir=False,
        )
        if checklist is None:
            return None
        if checklist.exige_antes_operacao and preenchimento is None:
            raise BusinessRuleError("Checklist de abertura obrigatório antes da operação.")
        if preenchimento is None:
            return None
        responsaveis = {
            pessoa_id
            for pessoa_id in (
                preenchimento.operador_id,
                preenchimento.executado_por_id,
                preenchimento.reportado_por_id,
            )
            if pessoa_id is not None
        }
        for pessoa_id in responsaveis:
            await validate_operador_context(
                self.session,
                tenant_id=self.tenant_id,
                operador_id=pessoa_id,
                unidade_produtiva_id=equipamento.unidade_produtiva_id,
            )
        resposta = await self.registrar_respostas(preenchimento)
        if resposta.bloqueou_operacao:
            await self.session.commit()
            raise BusinessRuleError("Falha crítica no checklist bloqueou a abertura da jornada.")
        return resposta

    async def _obter_equipamento(self, equipamento_id: uuid.UUID) -> Equipamento:
        stmt = select(Equipamento).where(
            Equipamento.id == equipamento_id,
            Equipamento.tenant_id == self.tenant_id,
        )
        equipamento = (await self.session.execute(stmt)).scalar_one_or_none()
        if equipamento is None:
            raise EntityNotFoundError("Equipamento não encontrado para o tenant informado.")
        return equipamento

    async def _resolver_checklist(
        self,
        equipamento: Equipamento,
        tipo_jornada: str,
        checklist_id: uuid.UUID | None,
        exigir: bool,
    ) -> ChecklistOperacional | None:
        stmt = (
            select(ChecklistOperacional)
            .options(selectinload(ChecklistOperacional.itens))
            .where(
                ChecklistOperacional.tenant_id == self.tenant_id,
                ChecklistOperacional.tipo_jornada == tipo_jornada,
                ChecklistOperacional.ativo == True,
            )
        )
        if checklist_id:
            stmt = stmt.where(ChecklistOperacional.id == checklist_id)
        else:
            stmt = stmt.where(
                or_(
                    ChecklistOperacional.tipo_equipamento == equipamento.tipo,
                    ChecklistOperacional.tipo_equipamento.is_(None),
                )
            )
            stmt = stmt.order_by(ChecklistOperacional.tipo_equipamento.desc(), ChecklistOperacional.created_at.desc())
        checklist = (await self.session.execute(stmt)).scalars().unique().first()
        if checklist is None:
            if exigir:
                raise BusinessRuleError("Checklist operacional não encontrado.")
            return None
        if checklist.tipo_equipamento and checklist.tipo_equipamento != equipamento.tipo:
            raise BusinessRuleError("Checklist incompatível com o tipo do equipamento.")
        return checklist

    @staticmethod
    def _validar_respostas_obrigatorias(
        checklist: ChecklistOperacional,
        dados: ChecklistOperacionalPreenchimentoCreate,
    ) -> None:
        respondidos = {item.item_id for item in dados.respostas}
        obrigatorios = {item.id for item in checklist.itens if item.ativo and item.obrigatorio}
        faltantes = obrigatorios - respondidos
        if faltantes:
            raise BusinessRuleError("Checklist obrigatório incompleto.")

    async def _gerar_os_checklist(
        self,
        equipamento: Equipamento,
        checklist: ChecklistOperacional,
        resposta: ChecklistOperacionalResposta,
        tipo_jornada: str,
    ) -> uuid.UUID:
        numero_os = f"CHK-{uuid.uuid4().hex[:12]}"
        tipo = "CORRETIVA" if resposta.criticidade in {"ALTA", "CRITICA"} else "PREVENTIVA"
        os = OrdemServico(
            tenant_id=self.tenant_id,
            numero_os=numero_os,
            equipamento_id=equipamento.id,
            tipo=tipo,
            descricao_problema=(
                f"Checklist {checklist.nome} ({tipo_jornada}) apontou falha "
                f"{resposta.criticidade or 'BAIXA'}: {resposta.observacao or 'sem observacao'}"
            )[:500],
            horimetro_na_abertura=equipamento.horimetro_atual or 0.0,
            km_na_abertura=equipamento.km_atual,
            checklist_aplicado=checklist.nome,
            origem_checklist_resposta_id=resposta.id,
        )
        self.session.add(os)
        await self.session.flush()
        resposta.os_gerada_id = os.id
        return os.id
