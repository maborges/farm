from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.models import CostAllocation
from campo.models import TarefaCampo
from core.cadastros.propriedades.models import AreaRural
from operacional.models.estoque import EstoqueMovimento
from pecuaria.animal.models import Animal, LoteAnimal
from pecuaria.schemas.dashboard_resumo_schema import PecuariaDashboardResumoExecutivoResponse


class PecuariaDashboardResumoService:
    _TIPOS_VACINACAO = ("VACINACAO", "VACINACAO_LOTE")
    _STATUS_ABERTOS = ("PENDENTE", "EM_EXECUCAO")

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID | None = None):
        self.session = session
        self.tenant_id = tenant_id
        self.unidade_produtiva_id = unidade_produtiva_id

    async def resumir(self) -> PecuariaDashboardResumoExecutivoResponse:
        animais_ativos = await self._contar_animais_ativos()
        lotes_ativos = await self._contar_lotes_ativos()
        piquetes_ativos = await self._contar_piquetes_ativos()
        peso_total_kg, quantidade_animais_com_peso = await self._somar_pesos()
        manejos_pendentes = await self._contar_manejos_pendentes()
        vacinacoes_pendentes = await self._contar_vacinacoes_pendentes()
        custo_sanitario_acumulado = await self._somar_custo_sanitario()
        area_pastagem_ha = await self._somar_area_pastagem()

        peso_medio_kg = (peso_total_kg / quantidade_animais_com_peso) if quantidade_animais_com_peso else 0.0
        ua_total = (peso_total_kg / 450.0) if peso_total_kg > 0 else (animais_ativos * 0.5)
        lotacao_ua_ha = round(ua_total / area_pastagem_ha, 2) if area_pastagem_ha > 0 else 0.0
        arrobas_totais = round(peso_total_kg / 30.0, 2) if peso_total_kg > 0 else 0.0
        arrobas_por_hectare = round(arrobas_totais / area_pastagem_ha, 2) if area_pastagem_ha > 0 else 0.0
        custo_total_por_arroba = round((custo_sanitario_acumulado / peso_total_kg) * 15, 2) if peso_total_kg > 0 else 0.0
        return PecuariaDashboardResumoExecutivoResponse(
            animais_ativos=animais_ativos,
            lotes_ativos=lotes_ativos,
            piquetes_ativos=piquetes_ativos,
            peso_total_kg=float(peso_total_kg),
            peso_medio_kg=float(peso_medio_kg),
            manejos_pendentes=manejos_pendentes,
            vacinacoes_pendentes=vacinacoes_pendentes,
            custo_sanitario_acumulado=float(custo_sanitario_acumulado),
            area_pastagem_ha=round(area_pastagem_ha, 2),
            lotacao_ua_ha=lotacao_ua_ha,
            arrobas_totais=arrobas_totais,
            arrobas_por_hectare=arrobas_por_hectare,
            custo_total_por_arroba=custo_total_por_arroba,
        )

    def _aplicar_contexto_unidade(self, stmt, model):
        if self.unidade_produtiva_id is not None:
            stmt = stmt.where(model.unidade_produtiva_id == self.unidade_produtiva_id)
        return stmt

    async def _contar_animais_ativos(self) -> int:
        stmt = select(func.count(Animal.id)).where(
            Animal.tenant_id == self.tenant_id,
            Animal.status == "ATIVO",
        )
        stmt = self._aplicar_contexto_unidade(stmt, Animal)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _contar_lotes_ativos(self) -> int:
        stmt = select(func.count(LoteAnimal.id)).where(
            LoteAnimal.tenant_id == self.tenant_id,
            LoteAnimal.ativo.is_(True),
        )
        stmt = self._aplicar_contexto_unidade(stmt, LoteAnimal)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _contar_piquetes_ativos(self) -> int:
        stmt = select(func.count(AreaRural.id)).where(
            AreaRural.tenant_id == self.tenant_id,
            AreaRural.ativo.is_(True),
            AreaRural.tipo == "PIQUETE",
        )
        stmt = self._aplicar_contexto_unidade(stmt, AreaRural)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _somar_pesos(self) -> tuple[float, int]:
        stmt = select(
            func.coalesce(func.sum(Animal.peso_atual_kg), 0),
            func.count(Animal.peso_atual_kg),
        ).where(
            Animal.tenant_id == self.tenant_id,
            Animal.status == "ATIVO",
            Animal.peso_atual_kg.is_not(None),
        )
        stmt = self._aplicar_contexto_unidade(stmt, Animal)
        row = (await self.session.execute(stmt)).one()
        return float(row[0] or 0), int(row[1] or 0)

    async def _contar_manejos_pendentes(self) -> int:
        stmt = select(func.count(TarefaCampo.id)).where(
            TarefaCampo.tenant_id == self.tenant_id,
            TarefaCampo.module == "pecuaria",
            TarefaCampo.status_execucao.in_(self._STATUS_ABERTOS),
        )
        if self.unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == self.unidade_produtiva_id)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _contar_vacinacoes_pendentes(self) -> int:
        stmt = select(func.count(TarefaCampo.id)).where(
            TarefaCampo.tenant_id == self.tenant_id,
            TarefaCampo.module == "pecuaria",
            TarefaCampo.type.in_(self._TIPOS_VACINACAO),
            TarefaCampo.status_execucao.in_(self._STATUS_ABERTOS),
        )
        if self.unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == self.unidade_produtiva_id)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def _somar_custo_sanitario(self) -> float:
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
                TarefaCampo.module == "pecuaria",
                TarefaCampo.type.in_(self._TIPOS_VACINACAO),
                TarefaCampo.status_execucao == "CONCLUIDA",
                EstoqueMovimento.origem == "PECUARIA_VACINACAO",
            )
        )
        if self.unidade_produtiva_id is not None:
            stmt = stmt.where(TarefaCampo.unidade_produtiva_id == self.unidade_produtiva_id)
        return float((await self.session.execute(stmt)).scalar_one() or 0)

    async def _somar_area_pastagem(self) -> float:
        """Soma a área em hectares dos piquetes ativos no contexto."""
        stmt = select(func.coalesce(func.sum(AreaRural.area_hectares), 0)).where(
            AreaRural.tenant_id == self.tenant_id,
            AreaRural.ativo.is_(True),
            AreaRural.tipo == "PIQUETE",
        )
        stmt = self._aplicar_contexto_unidade(stmt, AreaRural)
        return float((await self.session.execute(stmt)).scalar_one() or 0)

