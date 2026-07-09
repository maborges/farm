from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import column, func, select, table, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.models.unidade_produtiva import UnidadeProdutiva
from wizard.models import (
    ACTIVE_WIZARD_STATUSES,
    ChecklistEvidenceType,
    ChecklistItemSeverity,
    ChecklistItemStatus,
    ImplantacaoChecklistItem,
    ImplantacaoEtapa,
    ImplantacaoHistorico,
    ImplantacaoOperacional,
    ImplantacaoPendencia,
    ModoImplantacao,
    OrigemImplantacao,
    PendenciaSeverity,
    PendenciaStatus,
    PendenciaTipo,
    WizardEtapaStatus,
    WizardStageCode,
    WizardStatus,
)
from wizard.state_engine import transicionar_implantacao

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python < 3.11 compatibility
    UTC = timezone.utc  # noqa: UP017


@dataclass(frozen=True)
class WizardStageDefinition:
    codigo: str
    nome: str
    ordem: int
    obrigatoria: bool
    percentual_peso: int


@dataclass(frozen=True)
class WizardChecklistDefinition:
    codigo: str
    descricao: str
    obrigatorio: bool
    severidade: str
    evidencia_tipo: str
    etapa_codigo: str | None = None


STAGE_DEFINITIONS: tuple[WizardStageDefinition, ...] = (
    WizardStageDefinition("DIAGNOSTICO", "Diagnóstico", 1, True, 10),
    WizardStageDefinition("UNIDADE_PRODUTIVA", "Unidade Produtiva", 2, True, 15),
    WizardStageDefinition("TERRITORIO", "Território", 3, True, 10),
    WizardStageDefinition("ATIVIDADES", "Atividades", 4, True, 5),
    WizardStageDefinition("AGRICULTURA", "Agricultura", 5, True, 10),
    WizardStageDefinition("PECUARIA", "Pecuária", 6, True, 10),
    WizardStageDefinition("ESTOQUE", "Estoque", 7, True, 10),
    WizardStageDefinition("FINANCEIRO", "Financeiro", 8, True, 10),
    WizardStageDefinition("MAQUINAS", "Máquinas", 9, True, 5),
    WizardStageDefinition("EQUIPE", "Equipe", 10, False, 0),
    WizardStageDefinition("REVISAO", "Revisão", 11, True, 5),
    WizardStageDefinition("GO_LIVE", "Go-live", 12, True, 5),
    WizardStageDefinition("ESTABILIZACAO", "Estabilização", 13, True, 5),
)

CHECKLIST_DEFINITIONS: tuple[WizardChecklistDefinition, ...] = (
    WizardChecklistDefinition(
        "CHECK_UNIDADE_PRODUTIVA",
        "Existe ao menos uma Unidade Produtiva ativa para a implantação",
        True,
        ChecklistItemSeverity.CRITICO.value,
        ChecklistEvidenceType.AUTOMATICA.value,
        WizardStageCode.UNIDADE_PRODUTIVA.value,
    ),
    WizardChecklistDefinition(
        "CHECK_ESTRUTURA_TERRITORIAL",
        "Existe ao menos uma Área Rural ativa",
        True,
        ChecklistItemSeverity.ATENCAO.value,
        ChecklistEvidenceType.AUTOMATICA.value,
        WizardStageCode.TERRITORIO.value,
    ),
    WizardChecklistDefinition(
        "CHECK_AGRICULTURA_TALHAO",
        "Quando Agricultura estiver habilitada, deve existir ao menos um talhão",
        True,
        ChecklistItemSeverity.CRITICO.value,
        ChecklistEvidenceType.AUTOMATICA.value,
        WizardStageCode.AGRICULTURA.value,
    ),
    WizardChecklistDefinition(
        "CHECK_PECUARIA_PIQUETE",
        "Quando Pecuária estiver habilitada, deve existir ao menos um piquete",
        True,
        ChecklistItemSeverity.CRITICO.value,
        ChecklistEvidenceType.AUTOMATICA.value,
        WizardStageCode.PECUARIA.value,
    ),
    WizardChecklistDefinition(
        "CHECK_ESTOQUE_DEPOSITO",
        "Quando Estoque estiver habilitado, deve existir ao menos um depósito ativo",
        True,
        ChecklistItemSeverity.ATENCAO.value,
        ChecklistEvidenceType.AUTOMATICA.value,
        WizardStageCode.ESTOQUE.value,
    ),
    WizardChecklistDefinition(
        "CHECK_FINANCEIRO_PLANO_CONTA",
        "Quando Financeiro estiver habilitado, deve existir um plano de contas mínimo",
        True,
        ChecklistItemSeverity.ATENCAO.value,
        ChecklistEvidenceType.AUTOMATICA.value,
        WizardStageCode.FINANCEIRO.value,
    ),
    WizardChecklistDefinition(
        "CHECK_PRODUTO_CATALOGO",
        (
            "Quando Agricultura ou Estoque estiverem habilitados, deve existir "
            "um catálogo mínimo de produtos"
        ),
        True,
        ChecklistItemSeverity.ATENCAO.value,
        ChecklistEvidenceType.AUTOMATICA.value,
        WizardStageCode.ATIVIDADES.value,
    ),
    WizardChecklistDefinition(
        "CHECK_EQUIPAMENTO_CADASTRO",
        "Quando Frota estiver habilitada, deve existir ao menos um equipamento cadastrado",
        True,
        ChecklistItemSeverity.ATENCAO.value,
        ChecklistEvidenceType.AUTOMATICA.value,
        WizardStageCode.MAQUINAS.value,
    ),
)

OPEN_PENDENCIA_STATUSES = {
    PendenciaStatus.ABERTA.value,
    PendenciaStatus.EM_TRATAMENTO.value,
}
DONE_ETAPA_STATUSES = {
    WizardEtapaStatus.COMPLETED.value,
    WizardEtapaStatus.SKIPPED.value,
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _is_legacy_empty_uuid_error(exc: DBAPIError) -> bool:
    message = str(exc).lower()
    return "invalid input syntax for type uuid" in message and '""' in message


async def _sanitize_legacy_nullable_uuid_columns_for_model(
    session: AsyncSession,
    *,
    model: type[BaseException] | Any,
    column_names: tuple[str, ...],
) -> None:
    table_name = model.__table__.name
    schema_result = await session.execute(text("SELECT current_schema()"))
    schema_name = schema_result.scalar_one()
    for column_name in column_names:
        column_meta = await session.execute(
            text(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_schema = :schema_name
                  AND table_name = :table_name
                  AND column_name = :column_name
                """
            ),
            {
                "schema_name": schema_name,
                "table_name": table_name,
                "column_name": column_name,
            },
        )
        data_type = column_meta.scalar_one_or_none()
        if data_type not in {"text", "character varying", "character"}:
            continue
        legacy_table = table(
            table_name,
            column(column_name),
            schema=schema_name,
        )
        try:
            async with session.begin_nested():
                await session.execute(
                    update(legacy_table)
                    .values({column_name: None})
                    .where(
                        text(f"btrim(coalesce({column_name}::text, '')) = ''")
                    )
                )
        except Exception:  # noqa: S110
            pass
    await session.flush()


async def sanitize_legacy_wizard_nullable_uuid_columns(
    session: AsyncSession,
) -> None:
    await _sanitize_legacy_nullable_uuid_columns_for_model(
        session,
        model=ImplantacaoChecklistItem,
        column_names=("etapa_id", "checked_by_usuario_id"),
    )
    await _sanitize_legacy_nullable_uuid_columns_for_model(
        session,
        model=ImplantacaoPendencia,
        column_names=("etapa_id", "responsavel_usuario_id"),
    )
    await _sanitize_legacy_nullable_uuid_columns_for_model(
        session,
        model=ImplantacaoHistorico,
        column_names=("ator_usuario_id",),
    )


class HistoricoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def registrar(
        self,
        implantacao_id: uuid.UUID,
        *,
        evento: str,
        status_anterior: str | None = None,
        status_novo: str | None = None,
        etapa_anterior: str | None = None,
        etapa_nova: str | None = None,
        ator_usuario_id: uuid.UUID | None = None,
        payload_snapshot: dict[str, Any] | None = None,
    ) -> ImplantacaoHistorico:
        historico = ImplantacaoHistorico(
            implantacao_id=implantacao_id,
            evento=evento,
            status_anterior=status_anterior,
            status_novo=status_novo,
            etapa_anterior=etapa_anterior,
            etapa_nova=etapa_nova,
            ator_usuario_id=ator_usuario_id,
            payload_snapshot=payload_snapshot or {},
        )
        self.session.add(historico)
        await self.session.flush()
        return historico

    async def registrar_transicao(
        self,
        implantacao_id: uuid.UUID,
        payload: dict[str, Any],
    ) -> ImplantacaoHistorico:
        return await self.registrar(implantacao_id, **payload)


class EtapaService:
    def __init__(self, session: AsyncSession, historico_service: HistoricoService) -> None:
        self.session = session
        self.historico_service = historico_service

    async def listar_etapas(self, implantacao_id: uuid.UUID) -> list[ImplantacaoEtapa]:
        stmt = (
            select(ImplantacaoEtapa)
            .where(ImplantacaoEtapa.implantacao_id == implantacao_id)
            .order_by(ImplantacaoEtapa.ordem.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _buscar_etapa(
        self,
        implantacao_id: uuid.UUID,
        codigo_etapa: str,
    ) -> ImplantacaoEtapa | None:
        stmt = select(ImplantacaoEtapa).where(
            ImplantacaoEtapa.implantacao_id == implantacao_id,
            ImplantacaoEtapa.codigo_etapa == codigo_etapa,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def inicializar_etapas_canonicas(
        self,
        implantacao: ImplantacaoOperacional,
    ) -> list[ImplantacaoEtapa]:
        implantacao_id = implantacao.id
        existentes = {
            etapa.codigo_etapa: etapa
            for etapa in await self.listar_etapas(implantacao_id)
        }
        criadas: list[ImplantacaoEtapa] = []
        for definition in STAGE_DEFINITIONS:
            if definition.codigo in existentes:
                continue
            etapa = ImplantacaoEtapa(
                implantacao_id=implantacao_id,
                codigo_etapa=definition.codigo,
                nome=definition.nome,
                obrigatoria=definition.obrigatoria,
                ordem=definition.ordem,
                percentual_peso=definition.percentual_peso,
            )
            self.session.add(etapa)
            criadas.append(etapa)
        if criadas:
            await self.session.flush()
        return await self.listar_etapas(implantacao_id)

    async def iniciar_etapa(
        self,
        implantacao: ImplantacaoOperacional,
        codigo_etapa: str,
        *,
        ator_usuario_id: uuid.UUID | None = None,
        observacoes: str | None = None,
        now: datetime | None = None,
    ) -> ImplantacaoEtapa:
        etapa = await self._buscar_etapa(implantacao.id, codigo_etapa)
        if etapa is None:
            raise EntityNotFoundError(f"Etapa '{codigo_etapa}' não encontrada.")
        if etapa.status in DONE_ETAPA_STATUSES:
            raise BusinessRuleError("Não é permitido iniciar uma etapa já finalizada.")
        instante = now or _utcnow()
        etapa.status = WizardEtapaStatus.IN_PROGRESS.value
        etapa.started_at = etapa.started_at or instante
        etapa.blocked_at = None
        etapa.observacoes = observacoes or etapa.observacoes
        implantacao.etapa_atual = codigo_etapa
        implantacao.updated_at = instante
        self.session.add(etapa)
        self.session.add(implantacao)
        await self.session.flush()
        await self.historico_service.registrar(
            implantacao.id,
            evento="wizard.etapa.started",
            status_anterior=implantacao.status,
            status_novo=implantacao.status,
            etapa_anterior=implantacao.etapa_atual,
            etapa_nova=codigo_etapa,
            ator_usuario_id=ator_usuario_id,
            payload_snapshot={"codigo_etapa": codigo_etapa},
        )
        return etapa

    async def concluir_etapa(
        self,
        implantacao: ImplantacaoOperacional,
        codigo_etapa: str,
        *,
        ator_usuario_id: uuid.UUID | None = None,
        now: datetime | None = None,
    ) -> ImplantacaoEtapa:
        etapa = await self._buscar_etapa(implantacao.id, codigo_etapa)
        if etapa is None:
            raise EntityNotFoundError(f"Etapa '{codigo_etapa}' não encontrada.")
        instante = now or _utcnow()
        etapa.status = WizardEtapaStatus.COMPLETED.value
        etapa.started_at = etapa.started_at or instante
        etapa.completed_at = instante
        etapa.blocked_at = None
        implantacao.etapa_atual = codigo_etapa
        implantacao.updated_at = instante
        self.session.add(etapa)
        self.session.add(implantacao)
        await self.session.flush()
        await self.historico_service.registrar(
            implantacao.id,
            evento="wizard.etapa.completed",
            status_anterior=implantacao.status,
            status_novo=implantacao.status,
            etapa_anterior=implantacao.etapa_atual,
            etapa_nova=codigo_etapa,
            ator_usuario_id=ator_usuario_id,
            payload_snapshot={"codigo_etapa": codigo_etapa},
        )
        return etapa

    async def pular_etapa(
        self,
        implantacao: ImplantacaoOperacional,
        codigo_etapa: str,
        *,
        ator_usuario_id: uuid.UUID | None = None,
        motivo: str | None = None,
        now: datetime | None = None,
    ) -> ImplantacaoEtapa:
        etapa = await self._buscar_etapa(implantacao.id, codigo_etapa)
        if etapa is None:
            raise EntityNotFoundError(f"Etapa '{codigo_etapa}' não encontrada.")
        if etapa.obrigatoria:
            raise BusinessRuleError("Não é permitido pular uma etapa obrigatória.")
        instante = now or _utcnow()
        etapa.status = WizardEtapaStatus.SKIPPED.value
        etapa.started_at = etapa.started_at or instante
        etapa.skipped_at = instante
        etapa.observacoes = motivo or etapa.observacoes
        implantacao.etapa_atual = codigo_etapa
        implantacao.updated_at = instante
        self.session.add(etapa)
        self.session.add(implantacao)
        await self.session.flush()
        await self.historico_service.registrar(
            implantacao.id,
            evento="wizard.etapa.skipped",
            status_anterior=implantacao.status,
            status_novo=implantacao.status,
            etapa_anterior=implantacao.etapa_atual,
            etapa_nova=codigo_etapa,
            ator_usuario_id=ator_usuario_id,
            payload_snapshot={"codigo_etapa": codigo_etapa, "motivo": motivo},
        )
        return etapa


class ChecklistService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _sanitize_legacy_nullable_uuid_columns(self) -> None:
        await sanitize_legacy_wizard_nullable_uuid_columns(self.session)

    async def listar_itens(
        self,
        implantacao_id: uuid.UUID,
    ) -> list[ImplantacaoChecklistItem]:
        stmt = (
            select(ImplantacaoChecklistItem)
            .where(ImplantacaoChecklistItem.implantacao_id == implantacao_id)
            .order_by(ImplantacaoChecklistItem.codigo_item.asc())
        )
        try:
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except DBAPIError as exc:
            if not _is_legacy_empty_uuid_error(exc):
                raise
            await self.session.rollback()
            try:
                await self._sanitize_legacy_nullable_uuid_columns()
                result = await self.session.execute(stmt)
                return list(result.scalars().all())
            except Exception:
                return []

    async def _buscar_item(
        self,
        implantacao_id: uuid.UUID,
        codigo_item: str,
    ) -> ImplantacaoChecklistItem | None:
        stmt = select(ImplantacaoChecklistItem).where(
            ImplantacaoChecklistItem.implantacao_id == implantacao_id,
            ImplantacaoChecklistItem.codigo_item == codigo_item,
        )
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except DBAPIError as exc:
            if not _is_legacy_empty_uuid_error(exc):
                raise
            await self.session.rollback()
            try:
                await self._sanitize_legacy_nullable_uuid_columns()
                result = await self.session.execute(stmt)
                return result.scalar_one_or_none()
            except Exception:
                return None

    async def criar_checklist_base_idempotente(
        self,
        implantacao: ImplantacaoOperacional,
        etapas: list[ImplantacaoEtapa],
    ) -> list[ImplantacaoChecklistItem]:
        implantacao_id = implantacao.id
        etapas_por_codigo = {etapa.codigo_etapa: etapa for etapa in etapas}
        existentes = {
            item.codigo_item: item
            for item in await self.listar_itens(implantacao_id)
        }
        for definition in CHECKLIST_DEFINITIONS:
            if definition.codigo in existentes:
                continue
            etapa = (
                etapas_por_codigo.get(definition.etapa_codigo)
                if definition.etapa_codigo
                else None
            )
            item = ImplantacaoChecklistItem(
                implantacao_id=implantacao.id,
                etapa_id=etapa.id if etapa else None,
                codigo_item=definition.codigo,
                descricao=definition.descricao,
                obrigatorio=definition.obrigatorio,
                severidade=definition.severidade,
                evidencia_tipo=definition.evidencia_tipo,
            )
            self.session.add(item)
        await self.session.flush()
        return await self.listar_itens(implantacao_id)

    async def marcar_item_atendido(
        self,
        implantacao_id: uuid.UUID,
        codigo_item: str,
        *,
        checked_by_usuario_id: uuid.UUID | None,
        evidencia_ref_id: str | None,
        evidencia_tipo: str | None = None,
        now: datetime | None = None,
    ) -> ImplantacaoChecklistItem:
        item = await self._buscar_item(implantacao_id, codigo_item)
        if item is None:
            raise EntityNotFoundError(f"Checklist '{codigo_item}' não encontrado.")
        if item.obrigatorio and not evidencia_ref_id:
            raise BusinessRuleError(
                "Item obrigatório de checklist exige evidência antes de ser atendido."
            )
        instante = now or _utcnow()
        item.status = ChecklistItemStatus.ATENDIDO.value
        item.evidencia_ref_id = evidencia_ref_id
        item.evidencia_tipo = evidencia_tipo or item.evidencia_tipo
        item.checked_by_usuario_id = checked_by_usuario_id
        item.checked_at = instante
        item.updated_at = instante
        self.session.add(item)
        await self.session.flush()
        return item

    async def minimum_checklist_satisfied(
        self,
        implantacao_id: uuid.UUID,
    ) -> bool:
        stmt = (
            select(func.count(ImplantacaoChecklistItem.id))
            .where(
                ImplantacaoChecklistItem.implantacao_id == implantacao_id,
                ImplantacaoChecklistItem.obrigatorio.is_(True),
                ImplantacaoChecklistItem.status.not_in(
                    [
                        ChecklistItemStatus.ATENDIDO.value,
                        ChecklistItemStatus.DISPENSADO.value,
                    ]
                ),
            )
        )
        pendentes = (await self.session.execute(stmt)).scalar_one()
        return pendentes == 0


class PendenciaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def listar_pendencias(
        self,
        implantacao_id: uuid.UUID,
        *,
        status: str | None = None,
    ) -> list[ImplantacaoPendencia]:
        stmt = (
            select(ImplantacaoPendencia)
            .where(ImplantacaoPendencia.implantacao_id == implantacao_id)
            .order_by(ImplantacaoPendencia.created_at.desc())
        )
        if status is not None:
            stmt = stmt.where(ImplantacaoPendencia.status == status)
        try:
            result = await self.session.execute(stmt)
        except DBAPIError as exc:
            if not _is_legacy_empty_uuid_error(exc):
                raise
            await self.session.rollback()
            await sanitize_legacy_wizard_nullable_uuid_columns(self.session)
            result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def criar_pendencia(
        self,
        implantacao_id: uuid.UUID,
        *,
        titulo: str,
        descricao: str,
        tipo: str = PendenciaTipo.PENDENCIA.value,
        severidade: str = PendenciaSeverity.MEDIA.value,
        etapa_id: uuid.UUID | None = None,
        responsavel_usuario_id: uuid.UUID | None = None,
        due_date: date | None = None,
    ) -> ImplantacaoPendencia:
        pendencia = ImplantacaoPendencia(
            implantacao_id=implantacao_id,
            etapa_id=etapa_id,
            tipo=tipo,
            severidade=severidade,
            titulo=titulo,
            descricao=descricao,
            responsavel_usuario_id=responsavel_usuario_id,
            due_date=due_date,
        )
        self.session.add(pendencia)
        await self.session.flush()
        return pendencia

    async def buscar_pendencia_aberta_por_titulo(
        self,
        implantacao_id: uuid.UUID,
        titulo: str,
    ) -> ImplantacaoPendencia | None:
        stmt = (
            select(ImplantacaoPendencia)
            .where(
                ImplantacaoPendencia.implantacao_id == implantacao_id,
                ImplantacaoPendencia.titulo == titulo,
                ImplantacaoPendencia.status.in_(OPEN_PENDENCIA_STATUSES),
            )
            .order_by(ImplantacaoPendencia.created_at.desc())
            .limit(1)
        )
        try:
            result = await self.session.execute(stmt)
        except DBAPIError as exc:
            if not _is_legacy_empty_uuid_error(exc):
                raise
            await self.session.rollback()
            await sanitize_legacy_wizard_nullable_uuid_columns(self.session)
            result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def criar_ou_manter_pendencia(
        self,
        implantacao_id: uuid.UUID,
        *,
        titulo: str,
        descricao: str,
        tipo: str = PendenciaTipo.PENDENCIA.value,
        severidade: str = PendenciaSeverity.MEDIA.value,
        etapa_id: uuid.UUID | None = None,
        responsavel_usuario_id: uuid.UUID | None = None,
        due_date: date | None = None,
    ) -> tuple[ImplantacaoPendencia, bool]:
        existente = await self.buscar_pendencia_aberta_por_titulo(implantacao_id, titulo)
        if existente is not None:
            changed = False
            if existente.descricao != descricao:
                existente.descricao = descricao
                changed = True
            if existente.severidade != severidade:
                existente.severidade = severidade
                changed = True
            if existente.tipo != tipo:
                existente.tipo = tipo
                changed = True
            if changed:
                existente.updated_at = _utcnow()
                self.session.add(existente)
                await self.session.flush()
            return existente, False
        pendencia = await self.criar_pendencia(
            implantacao_id,
            titulo=titulo,
            descricao=descricao,
            tipo=tipo,
            severidade=severidade,
            etapa_id=etapa_id,
            responsavel_usuario_id=responsavel_usuario_id,
            due_date=due_date,
        )
        return pendencia, True

    async def resolver_pendencia(
        self,
        pendencia_id: uuid.UUID,
        *,
        descartar: bool = False,
        now: datetime | None = None,
    ) -> ImplantacaoPendencia:
        stmt = select(ImplantacaoPendencia).where(ImplantacaoPendencia.id == pendencia_id)
        pendencia = (await self.session.execute(stmt)).scalar_one_or_none()
        if pendencia is None:
            raise EntityNotFoundError(f"Pendencia '{pendencia_id}' nao encontrada.")
        instante = now or _utcnow()
        pendencia.status = (
            PendenciaStatus.DESCARTADA.value
            if descartar
            else PendenciaStatus.RESOLVIDA.value
        )
        pendencia.resolved_at = instante
        pendencia.updated_at = instante
        self.session.add(pendencia)
        await self.session.flush()
        return pendencia

    async def resolver_pendencia_por_titulo(
        self,
        implantacao_id: uuid.UUID,
        titulo: str,
        *,
        descartar: bool = False,
        now: datetime | None = None,
    ) -> ImplantacaoPendencia | None:
        pendencia = await self.buscar_pendencia_aberta_por_titulo(implantacao_id, titulo)
        if pendencia is None:
            return None
        return await self.resolver_pendencia(
            pendencia.id,
            descartar=descartar,
            now=now,
        )

    async def has_open_critical_blockers(
        self,
        implantacao_id: uuid.UUID,
    ) -> bool:
        stmt = (
            select(func.count(ImplantacaoPendencia.id))
            .where(
                ImplantacaoPendencia.implantacao_id == implantacao_id,
                ImplantacaoPendencia.severidade == PendenciaSeverity.CRITICA.value,
                ImplantacaoPendencia.status.in_(OPEN_PENDENCIA_STATUSES),
            )
        )
        count = (await self.session.execute(stmt)).scalar_one()
        return count > 0


class ImplantacaoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.historico_service = HistoricoService(session)
        self.etapa_service = EtapaService(session, self.historico_service)
        self.checklist_service = ChecklistService(session)
        self.pendencia_service = PendenciaService(session)

    async def get_active_implantacao(
        self,
        tenant_id: uuid.UUID,
    ) -> ImplantacaoOperacional | None:
        stmt = (
            select(ImplantacaoOperacional)
            .where(
                ImplantacaoOperacional.tenant_id == tenant_id,
                ImplantacaoOperacional.status.in_(ACTIVE_WIZARD_STATUSES),
            )
            .order_by(ImplantacaoOperacional.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_get_active(
        self,
        *,
        tenant_id: uuid.UUID,
        owner_usuario_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None = None,
        modo_implantacao: str = ModoImplantacao.ASSISTIDA.value,
        origem: str = OrigemImplantacao.NOVO_ASSINANTE.value,
    ) -> ImplantacaoOperacional:
        implantacao = await self.get_active_implantacao(tenant_id)
        if implantacao is None:
            implantacao = ImplantacaoOperacional(
                tenant_id=tenant_id,
                owner_usuario_id=owner_usuario_id,
                unidade_produtiva_id=unidade_produtiva_id,
                modo_implantacao=modo_implantacao,
                origem=origem,
                status=WizardStatus.NOT_STARTED.value,
                etapa_atual=WizardStageCode.DIAGNOSTICO.value,
            )
            self.session.add(implantacao)
            await self.session.flush()
            await self.historico_service.registrar(
                implantacao.id,
                evento="wizard.implantacao.created",
                status_novo=implantacao.status,
                etapa_nova=implantacao.etapa_atual,
                ator_usuario_id=owner_usuario_id,
                payload_snapshot={"tenant_id": str(tenant_id)},
            )
        elif unidade_produtiva_id and implantacao.unidade_produtiva_id is None:
            implantacao.unidade_produtiva_id = unidade_produtiva_id
            self.session.add(implantacao)
            await self.session.flush()
        await self.garantir_unidade_produtiva_contextual(
            implantacao,
            unidade_produtiva_id=unidade_produtiva_id,
        )
        await self.etapa_service.inicializar_etapas_canonicas(implantacao)
        etapas = await self.etapa_service.listar_etapas(implantacao.id)
        await self.checklist_service.criar_checklist_base_idempotente(implantacao, etapas)
        await self.recalcular_progresso_basico(implantacao.id)
        return implantacao

    async def retomar_implantacao(
        self,
        tenant_id: uuid.UUID,
        *,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> ImplantacaoOperacional:
        implantacao = await self.get_active_implantacao(tenant_id)
        if implantacao is None:
            raise EntityNotFoundError("Implantação ativa não encontrada para o tenant.")
        await self.garantir_unidade_produtiva_contextual(
            implantacao,
            unidade_produtiva_id=unidade_produtiva_id,
        )
        await self.etapa_service.inicializar_etapas_canonicas(implantacao)
        etapas = await self.etapa_service.listar_etapas(implantacao.id)
        await self.checklist_service.criar_checklist_base_idempotente(implantacao, etapas)
        await self.recalcular_progresso_basico(implantacao.id)
        return implantacao

    async def garantir_unidade_produtiva_contextual(
        self,
        implantacao: ImplantacaoOperacional,
        *,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> ImplantacaoOperacional:
        """Vincula a implantação a uma unidade ativa quando ainda estiver sem contexto.

        Prioriza o `unidade_produtiva_id` do request. Se ele não vier, usa a única
        unidade ativa do tenant quando houver exatamente uma.
        """
        if implantacao.unidade_produtiva_id is not None:
            return implantacao

        resolved_id = await self._resolver_unidade_produtiva_id(
            implantacao.tenant_id, unidade_produtiva_id
        )
        if resolved_id is None:
            return implantacao

        implantacao.unidade_produtiva_id = resolved_id
        self.session.add(implantacao)
        await self.session.flush()
        return implantacao

    async def _resolver_unidade_produtiva_id(
        self,
        tenant_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None = None,
    ) -> uuid.UUID | None:
        if unidade_produtiva_id is None:
            return None

        stmt = select(UnidadeProdutiva.id).where(
            UnidadeProdutiva.tenant_id == tenant_id,
            UnidadeProdutiva.ativo.is_(True),
            UnidadeProdutiva.id == unidade_produtiva_id,
        )
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def aplicar_transicao_estado(
        self,
        implantacao: ImplantacaoOperacional,
        novo_status: str,
        *,
        ator_usuario_id: uuid.UUID | None = None,
        payload_snapshot: dict[str, Any] | None = None,
    ) -> ImplantacaoOperacional:
        implantacao_id = implantacao.id
        minimum_checklist_satisfied = await self.checklist_service.minimum_checklist_satisfied(
            implantacao_id
        )
        has_open_critical_blockers = await self.pendencia_service.has_open_critical_blockers(
            implantacao_id
        )

        result = transicionar_implantacao(
            implantacao,
            novo_status,
            ator_usuario_id=ator_usuario_id,
            payload_snapshot=payload_snapshot,
            minimum_checklist_satisfied=minimum_checklist_satisfied,
            has_open_critical_blockers=has_open_critical_blockers,
        )
        self.session.add(implantacao)
        await self.session.flush()
        await self.historico_service.registrar_transicao(implantacao_id, result.historico)
        await self.recalcular_progresso_basico(implantacao_id)
        return implantacao

    async def recalcular_progresso_basico(
        self,
        implantacao_id: uuid.UUID,
    ) -> int:
        stmt = select(ImplantacaoOperacional).where(ImplantacaoOperacional.id == implantacao_id)
        implantacao = (await self.session.execute(stmt)).scalar_one()
        etapas = await self.etapa_service.listar_etapas(implantacao_id)
        total = sum(etapa.percentual_peso for etapa in etapas)
        concluido = sum(
            etapa.percentual_peso
            for etapa in etapas
            if etapa.status in DONE_ETAPA_STATUSES
        )
        progresso = 0 if total == 0 else int(round((concluido / total) * 100))
        implantacao.percentual_progresso = progresso
        implantacao.checklist_minimo_percentual = (
            100
            if await self.checklist_service.minimum_checklist_satisfied(implantacao_id)
            else 0
        )
        self.session.add(implantacao)
        await self.session.flush()
        return progresso

    async def cancelar_implantacao(
        self,
        implantacao: ImplantacaoOperacional,
        *,
        ator_usuario_id: uuid.UUID | None = None,
        payload_snapshot: dict[str, Any] | None = None,
    ) -> ImplantacaoOperacional:
        return await self.aplicar_transicao_estado(
            implantacao,
            WizardStatus.CANCELLED.value,
            ator_usuario_id=ator_usuario_id,
            payload_snapshot=payload_snapshot,
        )

    async def bloquear_implantacao(
        self,
        implantacao: ImplantacaoOperacional,
        *,
        ator_usuario_id: uuid.UUID | None = None,
        payload_snapshot: dict[str, Any] | None = None,
    ) -> ImplantacaoOperacional:
        return await self.aplicar_transicao_estado(
            implantacao,
            WizardStatus.BLOCKED.value,
            ator_usuario_id=ator_usuario_id,
            payload_snapshot=payload_snapshot,
        )

    async def desbloquear_implantacao(
        self,
        implantacao: ImplantacaoOperacional,
        *,
        ator_usuario_id: uuid.UUID | None = None,
        payload_snapshot: dict[str, Any] | None = None,
    ) -> ImplantacaoOperacional:
        return await self.aplicar_transicao_estado(
            implantacao,
            WizardStatus.IN_PROGRESS.value,
            ator_usuario_id=ator_usuario_id,
            payload_snapshot=payload_snapshot,
        )


__all__ = [
    "CHECKLIST_DEFINITIONS",
    "STAGE_DEFINITIONS",
    "ChecklistService",
    "EtapaService",
    "HistoricoService",
    "ImplantacaoService",
    "PendenciaService",
    "WizardChecklistDefinition",
    "WizardStageDefinition",
]
