from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.models import CostAllocation
from campo.models import TarefaCampo
from core.cadastros.propriedades.models import AreaRural
from core.exceptions import EntityNotFoundError
from financeiro.models.lancamento import LancamentoFinanceiro
from operacional.models.estoque import EstoqueMovimento
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.schemas.lote_indicadores_schema import LoteIndicadoresResponse
from pecuaria.services.gmd_utils import calcular_gmd


class LoteIndicadoresService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def resumir(self, lote_id: uuid.UUID) -> LoteIndicadoresResponse:
        lote = await self._buscar_lote(lote_id)
        quantidade_animais = await self._contar_animais_ativos(lote_id)
        peso_total, quantidade_com_peso = await self._somar_pesos(lote_id)
        gmd_medio = await self._calcular_gmd_medio(lote_id)
        ultima_pesagem = await self._buscar_ultima_pesagem(lote_id)
        custo_total = await self._buscar_custo_sanitario_total(lote_id)
        custo_aquisicao_total = await self._buscar_custo_aquisicao_total(lote_id)
        area_piquete_ha = await self._buscar_area_piquete_ha(lote.area_id)
        custo_nutricao_total = await self._buscar_custo_nutricao_total(lote_id)
        return self._montar_resposta(
            lote,
            quantidade_animais,
            peso_total,
            quantidade_com_peso,
            gmd_medio,
            ultima_pesagem,
            custo_total,
            custo_aquisicao_total,
            area_piquete_ha,
            custo_nutricao_total,
        )

    async def _buscar_lote(self, lote_id: uuid.UUID) -> LoteAnimal:
        lote = await self.session.scalar(
            select(LoteAnimal).where(
                LoteAnimal.id == lote_id, LoteAnimal.tenant_id == self.tenant_id
            )
        )
        if not lote:
            raise EntityNotFoundError(f"Lote {lote_id} não encontrado")
        return lote

    async def _contar_animais_ativos(self, lote_id: uuid.UUID) -> int:
        stmt = select(func.count(Animal.id)).where(
            Animal.tenant_id == self.tenant_id,
            Animal.lote_id == lote_id,
            Animal.status == "ATIVO",
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _somar_pesos(self, lote_id: uuid.UUID) -> tuple[float, int]:
        stmt = select(
            func.coalesce(func.sum(Animal.peso_atual_kg), 0),
            func.count(Animal.peso_atual_kg),
        ).where(
            Animal.tenant_id == self.tenant_id,
            Animal.lote_id == lote_id,
            Animal.status == "ATIVO",
        )
        row = (await self.session.execute(stmt)).one()
        return float(row[0] or 0), int(row[1] or 0)

    async def _calcular_gmd_medio(self, lote_id: uuid.UUID) -> float | None:
        stmt = (
            select(EventoAnimal.animal_id, EventoAnimal.data_evento, EventoAnimal.peso_kg)
            .join(
                Animal,
                and_(Animal.id == EventoAnimal.animal_id, Animal.tenant_id == self.tenant_id),
            )
            .where(
                EventoAnimal.tenant_id == self.tenant_id,
                Animal.lote_id == lote_id,
                Animal.status == "ATIVO",
                EventoAnimal.tipo == "PESAGEM",
            )
            .order_by(EventoAnimal.animal_id, EventoAnimal.data_evento)
        )
        rows = (await self.session.execute(stmt)).all()
        gm_ds = self._extrair_gmds(rows)
        if not gm_ds:
            return None
        return round(sum(gm_ds) / len(gm_ds), 3)

    async def _buscar_ultima_pesagem(self, lote_id: uuid.UUID) -> date | None:
        stmt = (
            select(func.max(EventoAnimal.data_evento))
            .join(
                Animal,
                and_(Animal.id == EventoAnimal.animal_id, Animal.tenant_id == self.tenant_id),
            )
            .where(
                EventoAnimal.tenant_id == self.tenant_id,
                Animal.lote_id == lote_id,
                Animal.status == "ATIVO",
                EventoAnimal.tipo == "PESAGEM",
            )
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def _buscar_custo_sanitario_total(self, lote_id: uuid.UUID) -> float:
        stmt = (
            select(func.coalesce(func.sum(CostAllocation.amount), 0))
            .join(
                TarefaCampo,
                and_(
                    TarefaCampo.id == CostAllocation.source_id,
                    TarefaCampo.tenant_id == self.tenant_id,
                ),
            )
            .join(
                EstoqueMovimento,
                and_(
                    EstoqueMovimento.id == CostAllocation.inventory_movement_id,
                    EstoqueMovimento.tenant_id == self.tenant_id,
                ),
            )
            .where(
                CostAllocation.tenant_id == self.tenant_id,
                CostAllocation.source == "PECUARIA_VACINACAO",
                CostAllocation.cost_category == "SANITARIO",
                TarefaCampo.lote_id == lote_id,
                TarefaCampo.module == "pecuaria",
                TarefaCampo.type == "VACINACAO",
                TarefaCampo.status_execucao == "CONCLUIDA",
                EstoqueMovimento.origem == "PECUARIA_VACINACAO",
            )
        )
        return float((await self.session.execute(stmt)).scalar_one() or 0)

    async def _buscar_custo_aquisicao_total(self, lote_id: uuid.UUID) -> float:
        stmt = select(func.coalesce(func.sum(Animal.valor_aquisicao), 0)).where(
            Animal.tenant_id == self.tenant_id,
            Animal.lote_id == lote_id,
            Animal.status == "ATIVO",
            Animal.valor_aquisicao.is_not(None),
        )
        return float((await self.session.execute(stmt)).scalar_one() or 0)

    async def _buscar_area_piquete_ha(self, piquete_id: uuid.UUID | None) -> float:
        """Retorna a área em hectares do piquete atual do lote."""
        if piquete_id is None:
            return 0.0
        stmt = select(func.coalesce(AreaRural.area_hectares, AreaRural.area_hectares_manual)).where(
            AreaRural.id == piquete_id,
            AreaRural.tenant_id == self.tenant_id,
        )
        return float((await self.session.execute(stmt)).scalar_one_or_none() or 0)

    async def _buscar_custo_nutricao_total(self, lote_id: uuid.UUID) -> float:
        """Soma custos de nutrição/confinamento e lançamentos financeiros vinculados ao lote."""
        fin_stmt = select(func.coalesce(func.sum(LancamentoFinanceiro.valor), 0)).where(
            LancamentoFinanceiro.tenant_id == self.tenant_id,
            LancamentoFinanceiro.tipo == "CUSTO",
            LancamentoFinanceiro.origem_id == lote_id,
        )
        custo_fin = float((await self.session.execute(fin_stmt)).scalar_one() or 0)
        ca_stmt = select(func.coalesce(func.sum(CostAllocation.amount), 0)).where(
            CostAllocation.tenant_id == self.tenant_id,
            CostAllocation.source_id == lote_id,
            CostAllocation.cost_category.in_(("NUTRICAO", "CONFINAMENTO")),
        )
        custo_ca = float((await self.session.execute(ca_stmt)).scalar_one() or 0)
        return custo_fin + custo_ca

    def _montar_resposta(
        self,
        lote: LoteAnimal,
        quantidade_animais: int,
        peso_total: float,
        quantidade_com_peso: int,
        gmd_medio: float | None,
        ultima_pesagem: date | None,
        custo_total: float,
        custo_aquisicao_total: float,
        area_piquete_ha: float = 0.0,
        custo_nutricao_total: float = 0.0,
    ) -> LoteIndicadoresResponse:
        peso_medio = peso_total / quantidade_com_peso if quantidade_com_peso else 0.0
        custo_por_cabeca = round(custo_total / quantidade_animais, 4) if quantidade_animais else 0.0
        custo_por_kg = round(custo_total / peso_total, 4) if peso_total else 0.0
        custo_por_arroba = round(custo_por_kg * 15, 4)
        ua_total = (peso_total / 450.0) if peso_total > 0 else (quantidade_animais * 0.5)
        lotacao_ua_ha = round(ua_total / area_piquete_ha, 2) if area_piquete_ha > 0 else 0.0
        arrobas_totais = peso_total / 30.0 if peso_total > 0 else 0.0
        arrobas_por_hectare = round(arrobas_totais / area_piquete_ha, 2) if area_piquete_ha > 0 else 0.0
        custo_operacional = float(custo_total) + float(custo_nutricao_total)
        custo_total_por_arroba = round((custo_operacional / peso_total) * 15, 4) if peso_total > 0 else 0.0
        return LoteIndicadoresResponse(
            lote_id=lote.id,
            nome_lote=lote.identificacao,
            quantidade_animais=quantidade_animais,
            peso_total_kg=float(peso_total),
            peso_medio_kg=float(peso_medio),
            gmd_medio_kg_dia=gmd_medio,
            ultima_pesagem=ultima_pesagem,
            custo_sanitario_total=float(custo_total),
            custo_sanitario_por_cabeca=float(custo_por_cabeca),
            custo_sanitario_por_kg=float(custo_por_kg),
            custo_sanitario_por_arroba=float(custo_por_arroba),
            custo_aquisicao_total=float(custo_aquisicao_total),
            area_piquete_ha=round(area_piquete_ha, 2),
            lotacao_ua_ha=lotacao_ua_ha,
            arrobas_por_hectare=arrobas_por_hectare,
            custo_nutricao_total=round(float(custo_nutricao_total), 2),
            custo_total_operacional=round(custo_operacional, 2),
            custo_total_por_arroba=custo_total_por_arroba,
        )

    def _extrair_gmds(self, rows: list[tuple[uuid.UUID, date, float | None]]) -> list[float]:
        gm_ds: list[float] = []
        ultimo_animal: uuid.UUID | None = None
        peso_anterior: float | None = None
        data_anterior: date | None = None
        for animal_id, data_evento, peso_kg in rows:
            if animal_id != ultimo_animal:
                ultimo_animal = animal_id
                peso_anterior = None
                data_anterior = None
            if data_anterior and peso_anterior is not None and peso_kg is not None:
                dias = (data_evento - data_anterior).days
                gmd = calcular_gmd(peso_kg, peso_anterior, dias)
                if gmd is not None:
                    gm_ds.append(gmd)
            peso_anterior = float(peso_kg) if peso_kg is not None else peso_anterior
            data_anterior = data_evento
        return gm_ds
