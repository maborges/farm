from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.cultivos.models import Cultivo
from agricola.custos.allocation_service import registrar_cost_allocation
from agricola.custos.models import CostAllocation
from agricola.production_units.models import ProductionUnit
from core.cadastros.propriedades.models import AreaRural
from financeiro.models.despesa import Despesa
from financeiro.models.plano_conta import PlanoConta


@dataclass(slots=True, frozen=True)
class OperationalCostInput:
    """Contrato canônico de entrada econômica operacional."""

    tenant_id: UUID
    origem_tipo: str
    origem_id: UUID
    categoria: str
    valor: float
    data_competencia: date
    descricao: str
    unidade_produtiva_id: UUID | None = None
    safra_id: UUID | None = None
    talhao_id: UUID | None = None
    production_unit_id: UUID | None = None
    operacao_id: UUID | None = None
    subcategoria: str | None = None
    quantidade: float | None = None
    unidade: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    criar_despesa: bool = False
    despesa_valor: float | None = None


@dataclass(slots=True, frozen=True)
class OperationalCostResult:
    """Resultado de apropriação econômica operacional."""

    allocation: CostAllocation | None
    despesa: Despesa | None
    production_unit_id: UUID | None


class OperationalCostAllocationService:
    """Camada canônica para apropriação de custos operacionais."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def process(self, data: OperationalCostInput) -> OperationalCostResult:
        """Cria ou atualiza a apropriação canônica e a despesa vinculada."""
        production_unit_id = await self._resolver_production_unit_id(data)
        allocation = await self._upsert_allocation(data, production_unit_id)
        despesa = await self._upsert_despesa(data)
        return OperationalCostResult(
            allocation=allocation,
            despesa=despesa,
            production_unit_id=production_unit_id,
        )

    async def _upsert_allocation(
        self,
        data: OperationalCostInput,
        production_unit_id: UUID | None,
    ) -> CostAllocation | None:
        """Garante CostAllocation idempotente quando há contexto agrícola válido."""
        if production_unit_id is None or data.valor <= 0:
            return None
        source = self._mapear_source(data)
        cost_category = self._mapear_cost_category(data)
        allocation = await self._buscar_allocation(source, data.origem_id, production_unit_id)
        if allocation is None:
            allocation = await registrar_cost_allocation(
                self.session,
                tenant_id=self.tenant_id,
                production_unit_id=production_unit_id,
                source=source,
                source_id=data.origem_id,
                amount=round(float(data.valor), 2),
                allocation_date=data.data_competencia,
                cost_category=cost_category,
                allocation_method="DIRECT",
                allocation_basis=data.quantidade,
            )
            await self.session.flush()
            return allocation
        allocation.amount = round(float(data.valor), 2)
        allocation.cost_category = cost_category
        allocation.allocation_date = data.data_competencia
        allocation.allocation_basis = data.quantidade
        self.session.add(allocation)
        await self.session.flush()
        return allocation

    async def _upsert_despesa(self, data: OperationalCostInput) -> Despesa | None:
        """Cria ou atualiza despesa automática quando aplicável."""
        valor = round(float(data.despesa_valor or data.valor), 2)
        if not data.criar_despesa or valor <= 0 or data.unidade_produtiva_id is None:
            return None
        plano_id = await self._resolver_plano_conta_id(data.categoria)
        if plano_id is None:
            return None
        despesa = await self._buscar_despesa(data.origem_tipo, data.origem_id)
        if despesa is None:
            despesa = Despesa(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                unidade_produtiva_id=data.unidade_produtiva_id,
                plano_conta_id=plano_id,
                cultivo_id=await self._resolver_cultivo_id(data.safra_id),
                descricao=data.descricao[:255],
                valor_total=valor,
                valor_pago=valor,
                data_emissao=data.data_competencia,
                data_vencimento=data.data_competencia,
                data_pagamento=data.data_competencia,
                competencia=data.data_competencia,
                status="PAGO",
                origem_id=data.origem_id,
                origem_tipo=data.origem_tipo,
                ativo=True,
            )
        else:
            despesa.unidade_produtiva_id = data.unidade_produtiva_id
            despesa.plano_conta_id = plano_id
            despesa.cultivo_id = await self._resolver_cultivo_id(data.safra_id)
            despesa.descricao = data.descricao[:255]
            despesa.valor_total = valor
            despesa.valor_pago = valor
            despesa.data_emissao = data.data_competencia
            despesa.data_vencimento = data.data_competencia
            despesa.data_pagamento = data.data_competencia
            despesa.competencia = data.data_competencia
            despesa.status = "PAGO"
        self.session.add(despesa)
        await self.session.flush()
        return despesa

    async def _resolver_production_unit_id(self, data: OperationalCostInput) -> UUID | None:
        """Resolve a ProductionUnit pelo contexto agrícola disponível."""
        if data.production_unit_id is not None:
            return await self._validar_production_unit(data.production_unit_id)
        if data.safra_id is None:
            return None
        if data.talhao_id is not None:
            return await self._buscar_pu_por_safra_talhao(data.safra_id, data.talhao_id)
        if data.unidade_produtiva_id is None:
            return None
        return await self._buscar_pu_unica_por_safra_up(data.safra_id, data.unidade_produtiva_id)

    async def _validar_production_unit(self, production_unit_id: UUID) -> UUID | None:
        """Confirma que a ProductionUnit pertence ao tenant atual."""
        stmt = select(ProductionUnit.id).where(
            ProductionUnit.tenant_id == self.tenant_id,
            ProductionUnit.id == production_unit_id,
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def _buscar_pu_por_safra_talhao(self, safra_id: UUID, talhao_id: UUID) -> UUID | None:
        """Localiza ProductionUnit pelo par safra/talhão."""
        stmt = (
            select(ProductionUnit.id)
            .where(
                ProductionUnit.tenant_id == self.tenant_id,
                ProductionUnit.safra_id == safra_id,
                ProductionUnit.area_id == talhao_id,
                ProductionUnit.status != "CANCELADA",
            )
            .order_by((ProductionUnit.status == "ATIVA").desc(), ProductionUnit.created_at.desc())
        )
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def _buscar_pu_unica_por_safra_up(
        self,
        safra_id: UUID,
        unidade_produtiva_id: UUID,
    ) -> UUID | None:
        """Resolve a PU quando a safra possui um único contexto elegível na fazenda."""
        stmt = (
            select(ProductionUnit.id)
            .join(AreaRural, AreaRural.id == ProductionUnit.area_id)
            .where(
                ProductionUnit.tenant_id == self.tenant_id,
                ProductionUnit.safra_id == safra_id,
                ProductionUnit.status != "CANCELADA",
                AreaRural.unidade_produtiva_id == unidade_produtiva_id,
            )
        )
        production_units = (await self.session.execute(stmt)).scalars().all()
        return production_units[0] if len(production_units) == 1 else None

    async def _buscar_allocation(
        self,
        source: str,
        origem_id: UUID,
        production_unit_id: UUID,
    ) -> CostAllocation | None:
        """Busca CostAllocation já existente para a origem canônica."""
        stmt = (
            select(CostAllocation)
            .where(
                CostAllocation.tenant_id == self.tenant_id,
                CostAllocation.source == source,
                CostAllocation.source_id == origem_id,
                CostAllocation.production_unit_id == production_unit_id,
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _buscar_despesa(self, origem_tipo: str, origem_id: UUID) -> Despesa | None:
        """Busca despesa ativa já vinculada à origem operacional."""
        stmt = (
            select(Despesa)
            .where(
                Despesa.tenant_id == self.tenant_id,
                Despesa.origem_tipo == origem_tipo,
                Despesa.origem_id == origem_id,
                Despesa.ativo == True,
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _resolver_plano_conta_id(self, categoria: str) -> UUID | None:
        """Escolhe o plano de conta mais aderente à categoria operacional."""
        stmt = (
            select(PlanoConta.id)
            .where(
                PlanoConta.tenant_id == self.tenant_id,
                PlanoConta.natureza == "ANALITICA",
                PlanoConta.ativo == True,
            )
        )
        categoria_normalizada = categoria.strip().upper()
        if categoria_normalizada == "COMBUSTIVEL":
            stmt = stmt.where(PlanoConta.nome.ilike("%Combust%"))
        else:
            stmt = stmt.where(PlanoConta.categoria_rfb == "CUSTEIO")
        plano_id = (await self.session.execute(stmt.limit(1))).scalar_one_or_none()
        if plano_id is not None or categoria_normalizada == "COMBUSTIVEL":
            return plano_id
        fallback = select(PlanoConta.id).where(
            PlanoConta.tenant_id == self.tenant_id,
            PlanoConta.natureza == "ANALITICA",
            PlanoConta.ativo == True,
        )
        return (await self.session.execute(fallback.limit(1))).scalar_one_or_none()

    async def _resolver_cultivo_id(self, safra_id: UUID | None) -> UUID | None:
        """Resolve cultivo associado à safra para reaproveitar rastreabilidade financeira."""
        if safra_id is None:
            return None
        stmt = (
            select(Cultivo.id)
            .where(Cultivo.tenant_id == self.tenant_id, Cultivo.safra_id == safra_id)
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    def _mapear_source(self, data: OperationalCostInput) -> str:
        """Normaliza a origem econômica para a taxonomia canônica."""
        origem = data.origem_tipo.strip().upper()
        categoria = data.categoria.strip().upper()
        if origem == "ABASTECIMENTO":
            return "FROTA_COMBUSTIVEL"
        if origem == "ORDEM_SERVICO" and categoria == "PECAS":
            return "FROTA_PECAS"
        if origem == "ORDEM_SERVICO":
            return "FROTA_MANUTENCAO"
        if origem == "RH_DIARIA":
            return "RH_DIARIA"
        if origem == "RH_EMPREITADA":
            return "RH_EMPREITADA"
        if origem == "APONTAMENTO_FROTA":
            return "FROTA_APONTAMENTO"
        return origem[:32]

    def _mapear_cost_category(self, data: OperationalCostInput) -> str:
        """Converte categorias operacionais detalhadas para a taxonomia persistida."""
        categoria = data.categoria.strip().upper()
        mapping = {
            "COMBUSTIVEL": "INSUMO",
            "PECAS": "INSUMO",
            "MANUTENCAO": "SERVICO",
            "DIARIA": "MAO_OBRA",
            "EMPREITADA": "MAO_OBRA",
            "MAQUINA": "MAQUINARIO",
        }
        return mapping.get(categoria, "OUTROS")
