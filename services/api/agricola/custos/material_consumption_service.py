"""Apropriação econômica idempotente do consumo canônico de materiais."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.constants import REQUISICAO_CONSUMO
from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from core.exceptions import BusinessRuleError, EntityNotFoundError
from operacional.models.estoque import EstoqueMovimento, RequisicaoItemEvento


class MaterialConsumptionCostService:
    """Cria o CostAllocation oficial para um evento CONSUMO."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def process(self, event_id: UUID) -> CostAllocation:
        """Apropria um consumo ou retorna sua apropriação idempotente."""
        event = await self._load_event(event_id)
        existing = await self._existing(event.id)
        if existing is not None:
            self._validate_existing(existing, event)
            return existing
        execution, production_unit_id = await self._load_execution(event)
        movement = await self._load_delivery_movement(event)
        amount, unit_cost, quantity = self._calculate(event, movement)
        allocation = self._build_allocation(
            event,
            execution,
            production_unit_id,
            amount,
            unit_cost,
            quantity,
        )
        return await self._insert_idempotently(allocation, event)

    async def _load_event(self, event_id: UUID) -> RequisicaoItemEvento:
        event = (
            await self.session.execute(
                select(RequisicaoItemEvento).where(
                    RequisicaoItemEvento.tenant_id == self.tenant_id,
                    RequisicaoItemEvento.id == event_id,
                )
            )
        ).scalars().one_or_none()
        if event is None:
            raise EntityNotFoundError("Evento de consumo não encontrado no tenant atual.")
        if event.tipo_evento != "CONSUMO":
            raise BusinessRuleError("Somente eventos CONSUMO geram custo de material.")
        if event.provenance != "CANONICAL":
            raise BusinessRuleError("Evento legado não pode gerar apropriação econômica nova.")
        return event

    async def _existing(self, event_id: UUID) -> CostAllocation | None:
        return (
            await self.session.execute(
                select(CostAllocation).where(
                    CostAllocation.tenant_id == self.tenant_id,
                    CostAllocation.requisicao_item_evento_id == event_id,
                )
            )
        ).scalars().one_or_none()

    async def _load_execution(
        self, event: RequisicaoItemEvento
    ) -> tuple[OperacaoExecucao, UUID]:
        if event.operacao_execucao_id is None:
            raise BusinessRuleError("Consumo sem OperacaoExecucao não pode ser apropriado.")
        row = (
            await self.session.execute(
                select(OperacaoExecucao, OperacaoAgricola)
                .join(OperacaoAgricola, OperacaoAgricola.id == OperacaoExecucao.operacao_id)
                .where(
                    OperacaoExecucao.tenant_id == self.tenant_id,
                    OperacaoExecucao.id == event.operacao_execucao_id,
                    OperacaoAgricola.tenant_id == self.tenant_id,
                    OperacaoAgricola.id == event.operacao_agricola_id,
                )
            )
        ).first()
        if row is None:
            raise BusinessRuleError("Consumo não pertence à OperacaoAgricola informada.")
        execution, operation = row
        production_unit_id = execution.production_unit_id or operation.production_unit_id
        if production_unit_id is None:
            raise BusinessRuleError("Consumo sem ProductionUnit não pode ser apropriado.")
        return execution, production_unit_id

    async def _load_delivery_movement(self, event: RequisicaoItemEvento) -> EstoqueMovimento:
        if event.evento_entrega_id is None:
            raise BusinessRuleError("Consumo sem entrega de origem não pode ser apropriado.")
        movement = (
            await self.session.execute(
                select(EstoqueMovimento).where(
                    EstoqueMovimento.tenant_id == self.tenant_id,
                    EstoqueMovimento.requisicao_item_evento_id == event.evento_entrega_id,
                    EstoqueMovimento.tipo_movimento == "SAIDA",
                )
            )
        ).scalars().one_or_none()
        if movement is None or movement.custo_unitario is None:
            raise BusinessRuleError("Entrega de origem não possui custo unitário canônico.")
        return movement

    @staticmethod
    def _calculate(
        event: RequisicaoItemEvento, movement: EstoqueMovimento
    ) -> tuple[Decimal, Decimal, Decimal]:
        quantity = Decimal(str(event.quantidade))
        unit_cost = Decimal(str(movement.custo_unitario))
        amount = (quantity * unit_cost).quantize(Decimal("0.01"))
        if quantity <= 0 or unit_cost <= 0 or amount <= 0:
            raise BusinessRuleError("Consumo precisa possuir quantidade e custo positivos.")
        return amount, unit_cost, quantity

    @staticmethod
    def _build_allocation(
        event: RequisicaoItemEvento,
        execution: OperacaoExecucao,
        production_unit_id: UUID,
        amount: Decimal,
        unit_cost: Decimal,
        quantity: Decimal,
    ) -> CostAllocation:
        return CostAllocation(
            tenant_id=event.tenant_id,
            production_unit_id=production_unit_id,
            source=REQUISICAO_CONSUMO,
            source_id=event.id,
            requisicao_item_evento_id=event.id,
            operation_execution_id=execution.id,
            cost_category="INSUMO",
            amount=amount,
            allocation_date=event.ocorrido_em.date() if event.ocorrido_em else date.today(),
            allocation_method="DIRECT",
            allocation_basis=quantity,
            currency="BRL",
        )

    async def _insert_idempotently(
        self, allocation: CostAllocation, event: RequisicaoItemEvento
    ) -> CostAllocation:
        try:
            async with self.session.begin_nested():
                self.session.add(allocation)
                await self.session.flush()
        except IntegrityError:
            existing = await self._existing(event.id)
            if existing is None:
                raise
            self._validate_existing(existing, event)
            return existing
        return allocation

    @staticmethod
    def _validate_existing(allocation: CostAllocation, event: RequisicaoItemEvento) -> None:
        if (
            allocation.source_id != event.id
            or allocation.requisicao_item_evento_id != event.id
        ):
            raise BusinessRuleError(
                "CostAllocation existente não corresponde ao evento de consumo."
            )
