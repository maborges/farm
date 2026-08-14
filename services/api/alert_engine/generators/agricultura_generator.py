from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select

from agricola.a1_planejamento.models import ItemOrcamentoSafra
from agricola.cultivos.models import Cultivo
from agricola.custos.service import CustosService
from agricola.operacoes.models import OperacaoAgricola
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from alert_engine.models import AlertStatus, Category, Domain, Priority, Severity, TriggerType
from alert_engine.schemas import OperationalAlertCreate
from alert_engine.service import AlertLifecycleService
from core.cadastros.propriedades.models import AreaRural

from ._support import has_active_alert, set_rls_context
from .base import BaseAlertGenerator
from .context import AlertGeneratorContext
from .registry import register_alert_generator
from .result import AlertGeneratorResult


@dataclass(slots=True)
class _SafraContext:
    safra_id: UUID
    unidade_produtiva_id: UUID | None
    ano_safra: str
    cultura: str | None
    status: str
    created_at: datetime


@dataclass(slots=True)
class _TalhaoContext:
    safra_id: UUID
    talhao_id: UUID
    unidade_produtiva_id: UUID | None
    talhao_nome: str
    ano_safra: str
    cultura: str | None
    safra_status: str
    created_at: datetime


@dataclass(slots=True)
class _OperacaoContext:
    operacao_id: UUID
    safra_id: UUID
    unidade_produtiva_id: UUID | None
    talhao_id: UUID
    tipo: str
    status: str
    data_prevista: date
    descricao: str


@register_alert_generator
class AgriculturaAlertGenerator(BaseAlertGenerator):
    """Generates canonical alerts for agricultural operational signals."""

    generator_name = "agricultura"
    domain = Domain.AGRICULTURE
    category = Category.OPERACIONAL
    execution_modes = ("scheduled", "hybrid")

    async def run(self, context: AlertGeneratorContext) -> AlertGeneratorResult:
        """Execute agricultural rules from canonical context.

        Cada item é processado dentro de um SAVEPOINT (`begin_nested`), não
        `session.rollback()` da transação inteira — `session.rollback()`
        após falha de flush não deixa a sessão de fato reutilizável nesse
        stack (SQLAlchemy async + asyncpg), confirmado ao vivo em produção.
        Mesmo padrão aplicado em campo_generator.py e pecuaria_generator.py —
        ver memória do projeto project_tres_sistemas_alertas_mapeados.
        """
        from loguru import logger

        await set_rls_context(self.session, context.tenant_id)
        counters = {
            "safras_sem_movimentacao": 0,
            "operacoes_atrasadas": 0,
            "talhoes_sem_atualizacao": 0,
            "custos_acima_previstos": 0,
        }
        result = AlertGeneratorResult(
            generator_name=self.generator_name,
            metadata={"rule_counters": counters},
        )
        dias_sem_movimentacao = self._metadata_int(context, "dias_sem_movimentacao", 30)
        dias_tolerancia_atraso = self._metadata_int(context, "dias_tolerancia_atraso", 0)
        dias_sem_atualizacao_talhao = self._metadata_int(
            context,
            "dias_sem_atualizacao_talhao",
            45,
        )
        limite_desvio_percentual = self._metadata_float(
            context,
            "limite_desvio_percentual",
            15.0,
        )

        async def _processar(itens, item_id_fn, avaliar, contador_key):
            for item in itens:
                try:
                    async with self.session.begin_nested():
                        created = await avaliar(item)
                    result.created += created
                    result.updated += 1 - created if created in {0, 1} else 0
                    counters[contador_key] += created
                except Exception:  # pragma: no cover - defensive isolation
                    logger.bind(
                        component="agricultura_alert_generator",
                        tenant_id=str(context.tenant_id),
                        item_id=str(item_id_fn(item)),
                        contador=contador_key,
                    ).exception("agricultura_alert_generator_item_failed")
                    result.errors += 1

        await _processar(
            await self._listar_safras_ativas(context.tenant_id, context.unidade_produtiva_id),
            lambda safra: safra.safra_id,
            lambda safra: self._avaliar_safra_sem_movimentacao(safra, dias_sem_movimentacao),
            "safras_sem_movimentacao",
        )
        await _processar(
            await self._listar_operacoes_atrasadas(
                context.tenant_id, context.unidade_produtiva_id, dias_tolerancia_atraso
            ),
            lambda operacao: operacao.operacao_id,
            lambda operacao: self._avaliar_operacao_atrasada(operacao, dias_tolerancia_atraso),
            "operacoes_atrasadas",
        )
        await _processar(
            await self._listar_talhoes_ativos(context.tenant_id, context.unidade_produtiva_id),
            lambda talhao: talhao.talhao_id,
            lambda talhao: self._avaliar_talhao_sem_atualizacao(
                talhao, dias_sem_atualizacao_talhao
            ),
            "talhoes_sem_atualizacao",
        )
        await _processar(
            await self._listar_safras_com_orcamento(
                context.tenant_id, context.unidade_produtiva_id
            ),
            lambda safra_id: safra_id,
            lambda safra_id: self._avaliar_custo_acima_previsto(
                context.tenant_id, safra_id, limite_desvio_percentual
            ),
            "custos_acima_previstos",
        )
        result.metadata = {"rule_counters": counters}
        return result

    async def _listar_safras_ativas(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> list[_SafraContext]:
        stmt = (
            select(
                Safra.id,
                Safra.ano_safra,
                Safra.cultura,
                Safra.status,
                Safra.created_at,
                AreaRural.unidade_produtiva_id,
            )
            .join(ProductionUnit, ProductionUnit.safra_id == Safra.id)
            .join(AreaRural, AreaRural.id == ProductionUnit.area_id)
            .where(
                Safra.tenant_id == tenant_id,
                ProductionUnit.tenant_id == tenant_id,
                AreaRural.tenant_id == tenant_id,
                ProductionUnit.status == "ATIVA",
                Safra.status.notin_(("ENCERRADA", "CANCELADA")),
            )
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(AreaRural.unidade_produtiva_id == unidade_produtiva_id)
        rows = (await self.session.execute(stmt.order_by(Safra.created_at.asc()))).all()
        unicos: dict[UUID, _SafraContext] = {}
        for row in rows:
            unicos.setdefault(
                row.id,
                _SafraContext(
                    safra_id=row.id,
                    unidade_produtiva_id=row.unidade_produtiva_id,
                    ano_safra=row.ano_safra,
                    cultura=row.cultura,
                    status=row.status,
                    created_at=row.created_at,
                ),
            )
        return list(unicos.values())

    async def _listar_operacoes_atrasadas(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        dias_tolerancia_atraso: int,
    ) -> list[_OperacaoContext]:
        status_ok = ("CONCLUIDA", "CANCELADA", "REALIZADA")
        stmt = (
            select(
                OperacaoAgricola.id,
                OperacaoAgricola.safra_id,
                OperacaoAgricola.production_unit_id,
                OperacaoAgricola.talhao_id,
                OperacaoAgricola.tipo,
                OperacaoAgricola.status,
                OperacaoAgricola.data_prevista,
                OperacaoAgricola.descricao,
                AreaRural.unidade_produtiva_id,
            )
            .join(AreaRural, AreaRural.id == OperacaoAgricola.talhao_id)
            .where(
                OperacaoAgricola.tenant_id == tenant_id,
                AreaRural.tenant_id == tenant_id,
                OperacaoAgricola.data_prevista.is_not(None),
                OperacaoAgricola.status.notin_(status_ok),
                OperacaoAgricola.data_prevista
                < date.today() - timedelta(days=dias_tolerancia_atraso),
            )
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(AreaRural.unidade_produtiva_id == unidade_produtiva_id)
        rows = (
            await self.session.execute(stmt.order_by(OperacaoAgricola.data_prevista.asc()))
        ).all()
        return [
            _OperacaoContext(
                operacao_id=row.id,
                safra_id=row.safra_id,
                unidade_produtiva_id=row.unidade_produtiva_id,
                talhao_id=row.talhao_id,
                tipo=row.tipo,
                status=row.status,
                data_prevista=row.data_prevista,
                descricao=row.descricao,
            )
            for row in rows
        ]

    async def _listar_talhoes_ativos(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> list[_TalhaoContext]:
        stmt = (
            select(
                ProductionUnit.safra_id,
                ProductionUnit.area_id,
                ProductionUnit.created_at,
                AreaRural.nome,
                AreaRural.unidade_produtiva_id,
                Safra.ano_safra,
                Safra.cultura,
                Safra.status,
            )
            .join(AreaRural, AreaRural.id == ProductionUnit.area_id)
            .join(Cultivo, Cultivo.id == ProductionUnit.cultivo_id)
            .join(Safra, Safra.id == ProductionUnit.safra_id)
            .where(
                ProductionUnit.tenant_id == tenant_id,
                AreaRural.tenant_id == tenant_id,
                Cultivo.tenant_id == tenant_id,
                Safra.tenant_id == tenant_id,
                ProductionUnit.status == "ATIVA",
                AreaRural.ativo.is_(True),
                AreaRural.tipo == "TALHAO",
                Safra.status.notin_(("ENCERRADA", "CANCELADA")),
            )
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(AreaRural.unidade_produtiva_id == unidade_produtiva_id)
        rows = (await self.session.execute(stmt.order_by(AreaRural.nome.asc()))).all()
        unicos: dict[UUID, _TalhaoContext] = {}
        for row in rows:
            unicos.setdefault(
                row.area_id,
                _TalhaoContext(
                    safra_id=row.safra_id,
                    talhao_id=row.area_id,
                    unidade_produtiva_id=row.unidade_produtiva_id,
                    talhao_nome=row.nome,
                    ano_safra=row.ano_safra,
                    cultura=row.cultura,
                    safra_status=row.status,
                    created_at=row.created_at,
                ),
            )
        return list(unicos.values())

    async def _listar_safras_com_orcamento(
        self,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
    ) -> list[UUID]:
        stmt = (
            select(ItemOrcamentoSafra.safra_id)
            .where(ItemOrcamentoSafra.tenant_id == tenant_id)
            .group_by(ItemOrcamentoSafra.safra_id)
            .order_by(ItemOrcamentoSafra.safra_id.asc())
        )
        if unidade_produtiva_id is not None:
            stmt = (
                stmt.join(
                    ProductionUnit,
                    ProductionUnit.safra_id == ItemOrcamentoSafra.safra_id,
                )
                .join(
                    AreaRural,
                    AreaRural.id == ProductionUnit.area_id,
                )
                .where(
                    ProductionUnit.tenant_id == tenant_id,
                    AreaRural.unidade_produtiva_id == unidade_produtiva_id,
                )
            )
        rows = await self.session.execute(stmt)
        return list(dict.fromkeys(row[0] for row in rows.all()))

    async def _avaliar_safra_sem_movimentacao(
        self,
        safra: _SafraContext,
        dias_sem_movimentacao: int,
    ) -> int:
        ultima_movimentacao = await self._ultima_movimentacao_safra(safra.safra_id)
        referencia = ultima_movimentacao or safra.created_at.date()
        dias = (date.today() - referencia).days
        if dias <= dias_sem_movimentacao:
            return 0
        return await self._persistir_alerta(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=safra.unidade_produtiva_id,
            category=Category.OPERACIONAL,
            severity=Severity.WARNING,
            priority=Priority.HIGH,
            title="Safra sem movimentação recente",
            message=(
                f"A safra {safra.ano_safra} ({safra.cultura or 'sem cultura'}) está sem "
                f"movimentação operacional há {dias} dias."
            ),
            source_type="AGRICULTURA_SAFRA_SEM_MOVIMENTACAO",
            source_id=str(safra.safra_id),
            dedupe_key=f"agricultura:safra_sem_movimentacao:{safra.safra_id}",
            entity_type="safra",
            entity_id=safra.safra_id,
            metadata={
                "safra_id": str(safra.safra_id),
                "ano_safra": safra.ano_safra,
                "cultura": safra.cultura,
                "status_safra": safra.status,
                "ultima_movimentacao": referencia.isoformat(),
                "dias_sem_movimentacao": dias,
            },
        )

    async def _avaliar_operacao_atrasada(
        self,
        operacao: _OperacaoContext,
        dias_tolerancia_atraso: int,
    ) -> int:
        atraso = (date.today() - operacao.data_prevista).days
        severity = Severity.CRITICAL if atraso > 7 else Severity.WARNING
        priority = Priority.URGENT if atraso > 7 else Priority.HIGH
        return await self._persistir_alerta(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=operacao.unidade_produtiva_id,
            category=Category.OPERACIONAL,
            severity=severity,
            priority=priority,
            title="Operação agrícola atrasada",
            message=(
                f"A operação '{operacao.tipo}' da safra {operacao.safra_id} está atrasada "
                f"desde {operacao.data_prevista.isoformat()}."
            ),
            source_type="AGRICULTURA_OPERACAO_ATRASADA",
            source_id=str(operacao.operacao_id),
            dedupe_key=f"agricultura:operacao_atrasada:{operacao.operacao_id}",
            entity_type="operacao_agricola",
            entity_id=operacao.operacao_id,
            metadata={
                "operacao_id": str(operacao.operacao_id),
                "safra_id": str(operacao.safra_id),
                "talhao_id": str(operacao.talhao_id),
                "tipo": operacao.tipo,
                "status": operacao.status,
                "data_prevista": operacao.data_prevista.isoformat(),
                "dias_atraso": atraso,
            },
        )

    async def _avaliar_talhao_sem_atualizacao(
        self,
        talhao: _TalhaoContext,
        dias_sem_atualizacao_talhao: int,
    ) -> int:
        ultima_atualizacao = await self._ultima_movimentacao_talhao(talhao.talhao_id)
        referencia = ultima_atualizacao or talhao.created_at.date()
        dias = (date.today() - referencia).days
        if dias <= dias_sem_atualizacao_talhao:
            return 0
        severity = Severity.INFO if dias <= dias_sem_atualizacao_talhao + 15 else Severity.WARNING
        priority = Priority.NORMAL if severity == Severity.INFO else Priority.HIGH
        return await self._persistir_alerta(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=talhao.unidade_produtiva_id,
            category=Category.OPERACIONAL,
            severity=severity,
            priority=priority,
            title="Talhão sem atualização operacional recente",
            message=(
                f"O talhão '{talhao.talhao_nome}' da safra {talhao.ano_safra} está sem "
                f"atualização operacional há {dias} dias."
            ),
            source_type="AGRICULTURA_TALHAO_SEM_ATUALIZACAO",
            source_id=str(talhao.talhao_id),
            dedupe_key=f"agricultura:talhao_sem_atualizacao:{talhao.safra_id}:{talhao.talhao_id}",
            entity_type="talhao",
            entity_id=talhao.talhao_id,
            metadata={
                "safra_id": str(talhao.safra_id),
                "talhao_id": str(talhao.talhao_id),
                "talhao_nome": talhao.talhao_nome,
                "ano_safra": talhao.ano_safra,
                "status_safra": talhao.safra_status,
                "ultima_atualizacao": referencia.isoformat(),
                "dias_sem_atualizacao": dias,
            },
        )

    async def _avaliar_custo_acima_previsto(
        self,
        tenant_id: UUID,
        safra_id: UUID,
        limite_desvio_percentual: float,
    ) -> int:
        resumo = await CustosService(self.session, tenant_id).get_resumo_safra(safra_id)
        if resumo.orcamento_previsto_total is None:
            return 0
        desvio = float(resumo.desvio_orcamento_pct or 0.0)
        if desvio <= limite_desvio_percentual:
            return 0
        severity = Severity.CRITICAL if desvio >= limite_desvio_percentual * 2 else Severity.WARNING
        priority = Priority.URGENT if severity == Severity.CRITICAL else Priority.HIGH
        return await self._persistir_alerta(
            tenant_id=tenant_id,
            unidade_produtiva_id=None,
            category=Category.ECONOMICO,
            severity=severity,
            priority=priority,
            title="Custo agrícola acima do previsto",
            message=(
                f"A safra {safra_id} está com desvio de {desvio:.2f}% sobre o orçamento "
                f"previsto."
            ),
            source_type="AGRICULTURA_CUSTO_ACIMA_PREVISTO",
            source_id=str(safra_id),
            dedupe_key=f"agricultura:custo_acima_previsto:{safra_id}",
            entity_type="safra",
            entity_id=safra_id,
            metadata={
                "safra_id": str(safra_id),
                "orcamento_previsto_total": float(resumo.orcamento_previsto_total or 0.0),
                "custo_total_realizado": float(resumo.custo_total_realizado),
                "desvio_orcamento_pct": desvio,
                "limite_desvio_percentual": limite_desvio_percentual,
            },
        )

    async def _ultima_movimentacao_safra(self, safra_id: UUID) -> date | None:
        stmt = select(func.max(OperacaoAgricola.data_realizada)).where(
            OperacaoAgricola.tenant_id == self.tenant_id,
            OperacaoAgricola.safra_id == safra_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _ultima_movimentacao_talhao(self, talhao_id: UUID) -> date | None:
        stmt = select(func.max(OperacaoAgricola.data_realizada)).where(
            OperacaoAgricola.tenant_id == self.tenant_id,
            OperacaoAgricola.talhao_id == talhao_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _persistir_alerta(
        self,
        *,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        category: Category,
        severity: Severity,
        priority: Priority,
        title: str,
        message: str,
        source_type: str,
        source_id: str,
        dedupe_key: str,
        entity_type: str,
        entity_id: UUID,
        metadata: dict[str, object],
    ) -> int:
        was_update = await has_active_alert(self.session, tenant_id, dedupe_key)
        payload = OperationalAlertCreate(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain=Domain.AGRICULTURE,
            category=category,
            title=title,
            message=message,
            severity=severity,
            priority=priority,
            status=AlertStatus.OPEN,
            trigger_type=TriggerType.SCHEDULE,
            source_type=source_type,
            source_id=source_id,
            entity_type=entity_type,
            entity_id=entity_id,
            source_event_ids=[],
            source_indicator_ids=[],
            dedupe_key=dedupe_key,
            context=metadata,
        )
        await AlertLifecycleService(self.session, tenant_id).create_or_update_alert(payload)
        return 0 if was_update else 1

    @staticmethod
    def _metadata_int(context: AlertGeneratorContext, key: str, default: int) -> int:
        value = context.metadata.get(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _metadata_float(context: AlertGeneratorContext, key: str, default: float) -> float:
        value = context.metadata.get(key, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
