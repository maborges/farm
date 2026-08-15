from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.operational_cost_service import OperationalCostAllocationService, OperationalCostInput
from agricola.operacoes.models import OperacaoAgricola
from agricola.production_units.models import ProductionUnit
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.operational_context import (
    validate_area_in_tenant,
    validate_pessoa_tenant,
    validate_production_unit_context,
    validate_safra_area_link,
    validate_safra_in_tenant,
)
from operacional.models.apontamento import ApontamentoMaoObra
from operacional.schemas.apontamento import ApontamentoMaoObraCreate
from rh.models import ColaboradorRH


@dataclass(frozen=True)
class _ApontamentoMaoObraContexto:
    unidade_produtiva_id: uuid.UUID | None
    safra_id: uuid.UUID | None
    production_unit_id: uuid.UUID | None
    talhao_id: uuid.UUID | None
    operacao_id: uuid.UUID | None


class ApontamentoMaoObraService:
    """OPERATIONS-GAP-01 §21.14: elo estruturado entre execução real de mão de
    obra manual (sem equipamento) e OperacaoAgricola/CostAllocation — mesmo
    papel que FrotaApontamentoService cumpre para máquinas."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def listar(
        self,
        *,
        pessoa_id: uuid.UUID | None = None,
        safra_id: uuid.UUID | None = None,
        production_unit_id: uuid.UUID | None = None,
        talhao_id: uuid.UUID | None = None,
        operacao_id: uuid.UUID | None = None,
        data_inicio: datetime | None = None,
        data_fim: datetime | None = None,
    ) -> list[ApontamentoMaoObra]:
        stmt = select(ApontamentoMaoObra).where(ApontamentoMaoObra.tenant_id == self.tenant_id)
        if pessoa_id is not None:
            stmt = stmt.where(ApontamentoMaoObra.pessoa_id == pessoa_id)
        if safra_id is not None:
            stmt = stmt.where(ApontamentoMaoObra.safra_id == safra_id)
        if production_unit_id is not None:
            stmt = stmt.where(ApontamentoMaoObra.production_unit_id == production_unit_id)
        if talhao_id is not None:
            stmt = stmt.where(ApontamentoMaoObra.talhao_id == talhao_id)
        if operacao_id is not None:
            stmt = stmt.where(ApontamentoMaoObra.operacao_id == operacao_id)
        if data_inicio is not None:
            stmt = stmt.where(ApontamentoMaoObra.data >= data_inicio)
        if data_fim is not None:
            stmt = stmt.where(ApontamentoMaoObra.data <= data_fim)
        stmt = stmt.order_by(ApontamentoMaoObra.data.desc(), ApontamentoMaoObra.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar(self, dados: ApontamentoMaoObraCreate) -> ApontamentoMaoObra:
        await validate_pessoa_tenant(self.session, tenant_id=self.tenant_id, pessoa_id=dados.pessoa_id)
        contexto = await self._resolver_contexto(dados)
        custo_hora = dados.custo_hora_snapshot
        if custo_hora is None:
            custo_hora = await self._resolver_custo_hora(dados.pessoa_id)

        apontamento = ApontamentoMaoObra(
            tenant_id=self.tenant_id,
            pessoa_id=dados.pessoa_id,
            data=dados.data,
            turno=dados.turno,
            horas_trabalhadas=dados.horas_trabalhadas,
            quantidade_pessoas=dados.quantidade_pessoas,
            unidade_produtiva_id=contexto.unidade_produtiva_id,
            safra_id=contexto.safra_id,
            production_unit_id=contexto.production_unit_id,
            talhao_id=contexto.talhao_id,
            operacao_id=contexto.operacao_id,
            tipo_operacao=dados.tipo_operacao,
            custo_hora_snapshot=custo_hora,
            observacoes=dados.observacoes,
        )
        if custo_hora is not None:
            apontamento.custo_total = round(
                float(custo_hora) * float(dados.horas_trabalhadas) * dados.quantidade_pessoas, 2
            )
        self.session.add(apontamento)
        await self.session.flush()

        await self._registrar_allocacao_economica(apontamento)
        return apontamento

    async def remover(self, apontamento_id: uuid.UUID) -> None:
        apontamento = await self._obter(apontamento_id)
        await self.session.delete(apontamento)

    async def _obter(self, apontamento_id: uuid.UUID) -> ApontamentoMaoObra:
        stmt = select(ApontamentoMaoObra).where(
            ApontamentoMaoObra.id == apontamento_id,
            ApontamentoMaoObra.tenant_id == self.tenant_id,
        )
        apontamento = (await self.session.execute(stmt)).scalar_one_or_none()
        if apontamento is None:
            raise EntityNotFoundError("Apontamento de mão de obra não encontrado.")
        return apontamento

    async def _resolver_custo_hora(self, pessoa_id: uuid.UUID) -> float | None:
        stmt = select(ColaboradorRH.valor_hora).where(
            ColaboradorRH.tenant_id == self.tenant_id,
            ColaboradorRH.pessoa_id == pessoa_id,
            ColaboradorRH.ativo.is_(True),
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def _resolver_contexto(self, dados: ApontamentoMaoObraCreate) -> _ApontamentoMaoObraContexto:
        operacao = None
        if dados.operacao_id is not None:
            operacao = await self._obter_operacao(dados.operacao_id)

        safra_id = dados.safra_id or (operacao.safra_id if operacao else None)
        talhao_id = dados.talhao_id or (operacao.talhao_id if operacao else None)
        unidade_produtiva_id = dados.unidade_produtiva_id

        if operacao is not None:
            if safra_id is not None and operacao.safra_id != safra_id:
                raise BusinessRuleError("Operação agrícola incompatível com a safra do apontamento.")
            if talhao_id is not None and operacao.talhao_id != talhao_id:
                raise BusinessRuleError("Operação agrícola incompatível com o talhão do apontamento.")

        if talhao_id is not None:
            area = await validate_area_in_tenant(self.session, tenant_id=self.tenant_id, area_id=talhao_id)
            if unidade_produtiva_id is None:
                unidade_produtiva_id = area.unidade_produtiva_id
            elif area.unidade_produtiva_id and area.unidade_produtiva_id != unidade_produtiva_id:
                raise BusinessRuleError("Talhão não pertence à unidade produtiva informada.")
            if safra_id is not None:
                await validate_safra_area_link(
                    self.session, tenant_id=self.tenant_id, safra_id=safra_id, area_id=talhao_id,
                )
        if safra_id is not None:
            await validate_safra_in_tenant(self.session, tenant_id=self.tenant_id, safra_id=safra_id)

        production_unit_id = dados.production_unit_id
        if production_unit_id is not None:
            if safra_id is None or talhao_id is None:
                raise BusinessRuleError("ProductionUnit exige safra e talhão informados.")
            await validate_production_unit_context(
                self.session, tenant_id=self.tenant_id,
                production_unit_id=production_unit_id, safra_id=safra_id, area_id=talhao_id,
            )
        elif safra_id is not None and talhao_id is not None:
            production_unit_id = await self._resolver_production_unit_id(safra_id=safra_id, talhao_id=talhao_id)

        return _ApontamentoMaoObraContexto(
            unidade_produtiva_id=unidade_produtiva_id,
            safra_id=safra_id,
            production_unit_id=production_unit_id,
            talhao_id=talhao_id,
            operacao_id=operacao.id if operacao else None,
        )

    async def _resolver_production_unit_id(self, *, safra_id: uuid.UUID, talhao_id: uuid.UUID) -> uuid.UUID | None:
        stmt = (
            select(ProductionUnit.id)
            .where(
                ProductionUnit.tenant_id == self.tenant_id,
                ProductionUnit.safra_id == safra_id,
                ProductionUnit.area_id == talhao_id,
            )
            .order_by((ProductionUnit.status == "ATIVA").desc(), ProductionUnit.created_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _obter_operacao(self, operacao_id: uuid.UUID) -> OperacaoAgricola:
        stmt = select(OperacaoAgricola).where(
            OperacaoAgricola.id == operacao_id,
            OperacaoAgricola.tenant_id == self.tenant_id,
        )
        operacao = (await self.session.execute(stmt)).scalar_one_or_none()
        if operacao is None:
            raise EntityNotFoundError("Operação agrícola não encontrada para o tenant informado.")
        return operacao

    async def _registrar_allocacao_economica(self, apontamento: ApontamentoMaoObra) -> None:
        if apontamento.custo_total is None or apontamento.custo_total <= 0:
            return
        await OperationalCostAllocationService(self.session, self.tenant_id).process(
            OperationalCostInput(
                tenant_id=self.tenant_id,
                unidade_produtiva_id=apontamento.unidade_produtiva_id,
                safra_id=apontamento.safra_id,
                talhao_id=apontamento.talhao_id,
                production_unit_id=apontamento.production_unit_id,
                origem_tipo="APONTAMENTO_MAO_OBRA",
                origem_id=apontamento.id,
                categoria="DIARIA",
                valor=float(apontamento.custo_total),
                quantidade=float(apontamento.horas_trabalhadas) or None,
                unidade="HORA",
                data_competencia=apontamento.data.date() if isinstance(apontamento.data, datetime) else date.today(),
                descricao="Apontamento operacional de mão de obra manual",
            )
        )
