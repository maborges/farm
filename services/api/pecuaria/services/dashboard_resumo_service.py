from __future__ import annotations

from dataclasses import dataclass
import uuid

from sqlalchemy import and_, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.models import CostAllocation
from campo.models import TarefaCampo
from core.cadastros.propriedades.models import AreaRural
from financeiro.models.lancamento import LancamentoFinanceiro
from operacional.models.estoque import EstoqueMovimento
from pecuaria.animal.models import Animal, LoteAnimal
from pecuaria.models.manejo import ManejoLote
from pecuaria.schemas.dashboard_resumo_schema import PecuariaDashboardResumoExecutivoResponse
from pecuaria.services import cotacao_arroba_service
from pecuaria.services.arroba_utils import (
    calcular_arrobas_carcaca,
    calcular_ua_por_peso,
    normalizar_rendimento_carcaca,
)
from pecuaria.services.lote_indicadores_service import (
    CATEGORIAS_COST_EXCLUIDAS,
    CATEGORIAS_NUTRICAO,
    ORIGENS_NUTRICAO,
    TIPOS_MANEJO_SANITARIO,
)


@dataclass(frozen=True)
class _RebanhoAgregado:
    animais_ativos: int
    lotes_ativos: int
    peso_total_kg: float
    peso_medio_kg: float
    arrobas_totais: float
    ua_total: float
    custo_aquisicao: float
    valor_mercado_estimado: float | None


@dataclass(frozen=True)
class _CustosRebanho:
    sanitario: float
    nutricao: float
    outros: float


class PecuariaDashboardResumoService:
    """Consolida indicadores operacionais e econômicos híbridos da fazenda/grupo."""

    _TIPOS_VACINACAO = ("VACINACAO", "VACINACAO_LOTE")
    _STATUS_ABERTOS = ("PENDENTE", "EM_EXECUCAO")

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID | None = None,
    ):
        self.session = session
        self.tenant_id = tenant_id
        self.unidade_produtiva_id = unidade_produtiva_id

    async def resumir(self) -> PecuariaDashboardResumoExecutivoResponse:
        """Agrega rebanho híbrido, lotação, custos reais e valor de mercado.

        Returns:
            PecuariaDashboardResumoExecutivoResponse consolidado para o contexto.
        """
        cotacao_pub = await cotacao_arroba_service.resolver_cotacao_boi_gordo_contexto(
            self.session,
            tenant_id=self.tenant_id,
            unidade_produtiva_id=self.unidade_produtiva_id,
        )
        lotes = await self._buscar_lotes_ativos()
        cotacoes_por_unidade = await self._resolver_cotacoes_unidades(lotes, cotacao_pub)
        rebanho = await self._agregar_rebanho_hibrido(lotes, cotacao_pub, cotacoes_por_unidade)
        custos = await self._buscar_custos_rebanho([lote.id for lote in lotes])
        area_pastagem_ha = await self._somar_area_pastagem()
        piquetes_ativos = await self._contar_piquetes_ativos()
        manejos_pendentes = await self._contar_manejos_pendentes()
        vacinacoes_pendentes = await self._contar_vacinacoes_pendentes()
        return self._montar_resposta(
            rebanho, custos, area_pastagem_ha, piquetes_ativos, manejos_pendentes, vacinacoes_pendentes, cotacao_pub
        )

    def _aplicar_contexto_unidade(self, stmt, model):
        if self.unidade_produtiva_id is not None:
            stmt = stmt.where(model.unidade_produtiva_id == self.unidade_produtiva_id)
        return stmt

    async def _buscar_lotes_ativos(self) -> list[LoteAnimal]:
        stmt = select(LoteAnimal).where(
            LoteAnimal.tenant_id == self.tenant_id,
            LoteAnimal.ativo.is_(True),
        )
        stmt = self._aplicar_contexto_unidade(stmt, LoteAnimal)
        return list((await self.session.execute(stmt)).scalars().all())

    async def _agrupar_animais_por_lote(self) -> dict[uuid.UUID | None, tuple[int, float, int, float]]:
        stmt = (
            select(
                Animal.lote_id,
                func.count(Animal.id),
                func.coalesce(func.sum(Animal.peso_atual_kg), 0),
                func.count(Animal.peso_atual_kg),
                func.coalesce(func.sum(Animal.valor_aquisicao), 0),
            )
            .where(Animal.tenant_id == self.tenant_id, Animal.status == "ATIVO")
            .group_by(Animal.lote_id)
        )
        stmt = self._aplicar_contexto_unidade(stmt, Animal)
        rows = (await self.session.execute(stmt)).all()
        return {
            row[0]: (int(row[1] or 0), float(row[2] or 0), int(row[3] or 0), float(row[4] or 0))
            for row in rows
        }

    async def _resolver_cotacoes_unidades(
        self,
        lotes: list[LoteAnimal],
        cotacao_padrao: tuple[float | None, str | None],
    ) -> dict[uuid.UUID, tuple[float | None, str | None]]:
        if self.unidade_produtiva_id is not None:
            return {}
        unidades = {lote.unidade_produtiva_id for lote in lotes if lote.unidade_produtiva_id is not None}
        if not unidades:
            return {}
        mapa: dict[uuid.UUID, tuple[float | None, str | None]] = {}
        for uid in unidades:
            mapa[uid] = await cotacao_arroba_service.resolver_cotacao_boi_gordo_contexto(
                self.session, tenant_id=self.tenant_id, unidade_produtiva_id=uid
            )
        return mapa

    async def _agregar_rebanho_hibrido(
        self,
        lotes: list[LoteAnimal],
        cotacao_pub: tuple[float | None, str | None],
        cotacoes_por_unidade: dict[uuid.UUID, tuple[float | None, str | None]] | None = None,
    ) -> _RebanhoAgregado:
        por_lote = await self._agrupar_animais_por_lote()
        totais = {"cab": 0, "peso": 0.0, "com_peso": 0, "arrobas": 0.0, "aqui": 0.0, "mercado": 0.0, "tem_mercado": False}
        lotes_ativos_ids = {lote.id for lote in lotes}
        mapa_unid = cotacoes_por_unidade or {}

        for lote in lotes:
            cot_lote = mapa_unid.get(lote.unidade_produtiva_id, cotacao_pub) if lote.unidade_produtiva_id else cotacao_pub
            self._acumular_lote(totais, lote, por_lote.get(lote.id), cot_lote)
        for lote_id, grupo in por_lote.items():
            if lote_id is None or lote_id not in lotes_ativos_ids:
                self._acumular_avulsos(totais, grupo, cotacao_pub)

        peso_medio = (totais["peso"] / totais["com_peso"]) if totais["com_peso"] else 0.0
        return _RebanhoAgregado(
            animais_ativos=totais["cab"],
            lotes_ativos=len(lotes),
            peso_total_kg=round(totais["peso"], 2),
            peso_medio_kg=round(peso_medio, 2),
            arrobas_totais=totais["arrobas"],
            ua_total=calcular_ua_por_peso(totais["peso"], totais["cab"]),
            custo_aquisicao=round(totais["aqui"], 2),
            valor_mercado_estimado=round(totais["mercado"], 2) if totais["tem_mercado"] else None,
        )

    @staticmethod
    def _acumular_lote(
        totais: dict,
        lote: LoteAnimal,
        ind: tuple[int, float, int, float] | None,
        cotacao_pub: tuple[float | None, str | None],
    ) -> None:
        ind_qtd, ind_peso, ind_com_peso, ind_aqui = ind or (0, 0.0, 0, 0.0)
        if ind_qtd > 0 or lote.modo_gestao == "INDIVIDUAL":
            cab, peso, com_peso = ind_qtd, ind_peso, ind_com_peso
            aqui = ind_aqui if ind_aqui > 0 else float(lote.valor_aquisicao_total or 0.0)
        else:
            cab = int(lote.quantidade_cabecas or 0)
            peso_med = float(lote.peso_medio_kg or 0.0)
            peso = cab * peso_med
            com_peso = cab if peso_med > 0 else 0
            aqui = float(lote.valor_aquisicao_total or 0.0)

        rend = normalizar_rendimento_carcaca(lote.rendimento_carcaca_pct)
        arrobas = calcular_arrobas_carcaca(peso, rend)
        cotacao_val, _ = cotacao_arroba_service.resolver_cotacao_lote(lote.cotacao_arroba_override, cotacao_pub)
        totais["cab"] += cab
        totais["peso"] += peso
        totais["com_peso"] += com_peso
        totais["arrobas"] += arrobas
        totais["aqui"] += aqui
        if arrobas > 0 and cotacao_val is not None and cotacao_val > 0:
            totais["mercado"] += arrobas * cotacao_val
            totais["tem_mercado"] = True

    @staticmethod
    def _acumular_avulsos(
        totais: dict,
        grupo: tuple[int, float, int, float],
        cotacao_pub: tuple[float | None, str | None],
    ) -> None:
        cab, peso, com_peso, aqui = grupo
        arrobas = calcular_arrobas_carcaca(peso)
        totais["cab"] += cab
        totais["peso"] += peso
        totais["com_peso"] += com_peso
        totais["arrobas"] += arrobas
        totais["aqui"] += aqui
        if arrobas > 0 and cotacao_pub[0] is not None and cotacao_pub[0] > 0:
            totais["mercado"] += arrobas * cotacao_pub[0]
            totais["tem_mercado"] = True

    async def _contar_piquetes_ativos(self) -> int:
        stmt = select(func.count(AreaRural.id)).where(
            AreaRural.tenant_id == self.tenant_id,
            AreaRural.ativo.is_(True),
            AreaRural.tipo == "PIQUETE",
        )
        stmt = self._aplicar_contexto_unidade(stmt, AreaRural)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

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

    async def _buscar_custos_rebanho(self, lote_ids: list[uuid.UUID]) -> _CustosRebanho:
        sanitario = await self._somar_custo_sanitario()
        nutricao = await self._somar_custo_nutricao(lote_ids)
        outros = await self._somar_custo_outros(lote_ids)
        return _CustosRebanho(sanitario=sanitario, nutricao=nutricao, outros=outros)

    async def _somar_custo_sanitario(self) -> float:
        stmt_ca = (
            select(func.coalesce(func.sum(CostAllocation.amount), 0))
            .join(TarefaCampo, and_(TarefaCampo.id == CostAllocation.source_id, TarefaCampo.tenant_id == self.tenant_id))
            .join(EstoqueMovimento, and_(EstoqueMovimento.id == CostAllocation.inventory_movement_id, EstoqueMovimento.tenant_id == self.tenant_id))
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
            stmt_ca = stmt_ca.where(TarefaCampo.unidade_produtiva_id == self.unidade_produtiva_id)

        stmt_manejo = (
            select(func.coalesce(func.sum(ManejoLote.custo_total), 0))
            .join(LoteAnimal, and_(LoteAnimal.id == ManejoLote.lote_id, LoteAnimal.tenant_id == self.tenant_id))
            .where(
                ManejoLote.tenant_id == self.tenant_id,
                ManejoLote.tipo_evento.in_(TIPOS_MANEJO_SANITARIO),
                ManejoLote.custo_total.is_not(None),
            )
        )
        if self.unidade_produtiva_id is not None:
            stmt_manejo = stmt_manejo.where(LoteAnimal.unidade_produtiva_id == self.unidade_produtiva_id)

        return float((await self.session.execute(stmt_ca)).scalar_one() or 0) + float(
            (await self.session.execute(stmt_manejo)).scalar_one() or 0
        )

    async def _somar_custo_nutricao(self, lote_ids: list[uuid.UUID]) -> float:
        if not lote_ids:
            return 0.0
        fin_stmt = select(func.coalesce(func.sum(LancamentoFinanceiro.valor), 0)).where(
            LancamentoFinanceiro.tenant_id == self.tenant_id,
            LancamentoFinanceiro.tipo == "CUSTO",
            LancamentoFinanceiro.origem_id.in_(lote_ids),
            self._filtro_lancamento_nutricao(),
        )
        ca_stmt = select(func.coalesce(func.sum(CostAllocation.amount), 0)).where(
            CostAllocation.tenant_id == self.tenant_id,
            CostAllocation.source_id.in_(lote_ids),
            CostAllocation.cost_category.in_(("NUTRICAO", "CONFINAMENTO")),
        )
        return float((await self.session.execute(fin_stmt)).scalar_one() or 0) + float(
            (await self.session.execute(ca_stmt)).scalar_one() or 0
        )

    async def _somar_custo_outros(self, lote_ids: list[uuid.UUID]) -> float:
        if not lote_ids:
            return 0.0
        fin_stmt = select(func.coalesce(func.sum(LancamentoFinanceiro.valor), 0)).where(
            LancamentoFinanceiro.tenant_id == self.tenant_id,
            LancamentoFinanceiro.tipo == "CUSTO",
            LancamentoFinanceiro.origem_id.in_(lote_ids),
            not_(self._filtro_lancamento_nutricao()),
        )
        ca_stmt = select(func.coalesce(func.sum(CostAllocation.amount), 0)).where(
            CostAllocation.tenant_id == self.tenant_id,
            CostAllocation.source_id.in_(lote_ids),
            CostAllocation.cost_category.not_in(CATEGORIAS_COST_EXCLUIDAS),
        )
        return float((await self.session.execute(fin_stmt)).scalar_one() or 0) + float(
            (await self.session.execute(ca_stmt)).scalar_one() or 0
        )

    @staticmethod
    def _filtro_lancamento_nutricao():
        return or_(
            func.coalesce(LancamentoFinanceiro.origem, "").in_(ORIGENS_NUTRICAO),
            func.coalesce(LancamentoFinanceiro.categoria, "").in_(CATEGORIAS_NUTRICAO),
        )

    async def _somar_area_pastagem(self) -> float:
        stmt = select(
            func.coalesce(func.sum(func.coalesce(AreaRural.area_hectares, AreaRural.area_hectares_manual, 0)), 0)
        ).where(
            AreaRural.tenant_id == self.tenant_id,
            AreaRural.ativo.is_(True),
            AreaRural.tipo == "PIQUETE",
        )
        stmt = self._aplicar_contexto_unidade(stmt, AreaRural)
        return float((await self.session.execute(stmt)).scalar_one() or 0)

    @staticmethod
    def _montar_resposta(
        rebanho: _RebanhoAgregado,
        custos: _CustosRebanho,
        area_pastagem_ha: float,
        piquetes_ativos: int,
        manejos_pendentes: int,
        vacinacoes_pendentes: int,
        cotacao_pub: tuple[float | None, str | None],
    ) -> PecuariaDashboardResumoExecutivoResponse:
        operacional = round(custos.sanitario + custos.nutricao + custos.outros, 2)
        arrobas_exatas = rebanho.arrobas_totais
        investido = rebanho.custo_aquisicao + operacional
        custo_arroba = round(operacional / arrobas_exatas, 2) if arrobas_exatas > 0 else 0.0
        break_even = round(investido / arrobas_exatas, 2) if arrobas_exatas > 0 else 0.0
        margem = (
            round(rebanho.valor_mercado_estimado - investido, 2)
            if rebanho.valor_mercado_estimado is not None
            else None
        )
        return PecuariaDashboardResumoExecutivoResponse(
            animais_ativos=rebanho.animais_ativos,
            lotes_ativos=rebanho.lotes_ativos,
            piquetes_ativos=piquetes_ativos,
            peso_total_kg=rebanho.peso_total_kg,
            peso_medio_kg=rebanho.peso_medio_kg,
            ua_total=rebanho.ua_total,
            manejos_pendentes=manejos_pendentes,
            vacinacoes_pendentes=vacinacoes_pendentes,
            custo_sanitario_acumulado=round(custos.sanitario, 2),
            custo_aquisicao_acumulado=rebanho.custo_aquisicao,
            custo_nutricao_acumulado=round(custos.nutricao, 2),
            custo_outros_acumulado=round(custos.outros, 2),
            custo_operacional_acumulado=operacional,
            area_pastagem_ha=round(area_pastagem_ha, 2),
            lotacao_ua_ha=round(rebanho.ua_total / area_pastagem_ha, 2) if area_pastagem_ha > 0 else 0.0,
            arrobas_totais=round(arrobas_exatas, 2),
            arrobas_por_hectare=round(arrobas_exatas / area_pastagem_ha, 2) if area_pastagem_ha > 0 else 0.0,
            custo_total_por_arroba=custo_arroba,
            custo_break_even_por_arroba=break_even,
            cotacao_arroba_referencia=cotacao_pub[0],
            fonte_cotacao=cotacao_pub[1],
            valor_mercado_estimado=rebanho.valor_mercado_estimado,
            margem_bruta_estimada=margem,
        )
