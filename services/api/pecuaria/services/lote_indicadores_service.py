from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import uuid

from sqlalchemy import and_, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.models import CostAllocation
from campo.models import TarefaCampo
from core.cadastros.propriedades.models import AreaRural
from core.exceptions import EntityNotFoundError
from financeiro.models.lancamento import LancamentoFinanceiro
from operacional.models.estoque import EstoqueMovimento
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.models.manejo import ManejoLote
from pecuaria.schemas.lote_indicadores_schema import LoteIndicadoresResponse
from pecuaria.services import cotacao_arroba_service
from pecuaria.services.arroba_utils import (
    EntradaEconomicaArroba,
    calcular_metricas_economicas_arroba,
    calcular_ua_por_peso,
    normalizar_rendimento_carcaca,
)
from pecuaria.services.gmd_utils import calcular_gmd

ORIGENS_NUTRICAO = ("PECUARIA_NUTRICAO", "NUTRICAO", "CONFINAMENTO")
CATEGORIAS_NUTRICAO = ("NUTRICAO", "CONFINAMENTO", "OPERACOES")
TIPOS_MANEJO_SANITARIO = ("VACINACAO", "MEDICACAO", "CASTRACAO")
CATEGORIAS_COST_EXCLUIDAS = ("SANITARIO", "NUTRICAO", "CONFINAMENTO")


@dataclass(frozen=True)
class _DadosZootecnicosLote:
    modo_gestao: str
    quantidade_animais: int
    peso_total_kg: float
    peso_medio_kg: float
    peso_inicial_total_kg: float | None
    custo_aquisicao_total: float
    gmd_medio: float | None
    ultima_pesagem: date | None


@dataclass(frozen=True)
class _CustosLote:
    sanitario: float
    nutricao: float
    outros: float


class LoteIndicadoresService:
    """Consolida indicadores zootécnicos, sanitários e financeiros por lote."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def resumir(self, lote_id: uuid.UUID) -> LoteIndicadoresResponse:
        """Calcula todos os indicadores zootécnicos e econômicos de um lote.

        Args:
            lote_id: Identificador do lote no tenant atual.

        Returns:
            LoteIndicadoresResponse completo com modo híbrido e valor de mercado.

        Raises:
            EntityNotFoundError: Se o lote não existir no tenant.
        """
        lote = await self._buscar_lote(lote_id)
        zootecnico = await self._resolver_dados_zootecnicos(lote)
        custos = await self._buscar_custos_lote(lote.id)
        area_ha = await self._buscar_area_piquete_ha(lote.area_id)
        cotacao = await cotacao_arroba_service.obter_cotacao_boi_gordo_referencia(self.session)
        return self._montar_resposta(lote, zootecnico, custos, area_ha, cotacao)

    async def _buscar_lote(self, lote_id: uuid.UUID) -> LoteAnimal:
        lote = await self.session.scalar(
            select(LoteAnimal).where(
                LoteAnimal.id == lote_id, LoteAnimal.tenant_id == self.tenant_id
            )
        )
        if not lote:
            raise EntityNotFoundError(f"Lote {lote_id} não encontrado")
        return lote

    async def _resolver_dados_zootecnicos(self, lote: LoteAnimal) -> _DadosZootecnicosLote:
        resumo_ind = await self._resumir_animais_individuais(lote.id)
        qtd_ind = resumo_ind[0]
        if qtd_ind > 0 or lote.modo_gestao == "INDIVIDUAL":
            return await self._montar_zootecnico_individual(lote, resumo_ind)
        return await self._montar_zootecnico_por_lote(lote)

    async def _resumir_animais_individuais(
        self, lote_id: uuid.UUID
    ) -> tuple[int, float, int, float]:
        stmt = select(
            func.count(Animal.id),
            func.coalesce(func.sum(Animal.peso_atual_kg), 0),
            func.count(Animal.peso_atual_kg),
            func.coalesce(func.sum(Animal.valor_aquisicao), 0),
        ).where(
            Animal.tenant_id == self.tenant_id,
            Animal.lote_id == lote_id,
            Animal.status == "ATIVO",
        )
        row = (await self.session.execute(stmt)).one()
        return int(row[0] or 0), float(row[1] or 0), int(row[2] or 0), float(row[3] or 0)

    async def _montar_zootecnico_individual(
        self, lote: LoteAnimal, resumo: tuple[int, float, int, float]
    ) -> _DadosZootecnicosLote:
        qtd, peso_total, qtd_com_peso, aqui_ind = resumo
        peso_medio = peso_total / qtd_com_peso if qtd_com_peso else 0.0
        aquisicao = aqui_ind if aqui_ind > 0 else float(lote.valor_aquisicao_total or 0.0)
        peso_inicial = await self._buscar_peso_inicial_individual(lote, qtd_com_peso)
        return _DadosZootecnicosLote(
            modo_gestao="INDIVIDUAL",
            quantidade_animais=qtd,
            peso_total_kg=peso_total,
            peso_medio_kg=peso_medio,
            peso_inicial_total_kg=peso_inicial,
            custo_aquisicao_total=aquisicao,
            gmd_medio=await self._calcular_gmd_medio(lote.id),
            ultima_pesagem=await self._buscar_ultima_pesagem(lote.id),
        )

    async def _montar_zootecnico_por_lote(self, lote: LoteAnimal) -> _DadosZootecnicosLote:
        qtd = int(lote.quantidade_cabecas or 0)
        peso_medio = float(lote.peso_medio_kg or 0.0)
        peso_total = round(qtd * peso_medio, 2)
        peso_inicial = (
            float(lote.peso_inicial_medio_kg) * qtd
            if lote.peso_inicial_medio_kg is not None
            else None
        )
        gmd, ultima_pesagem = await self._buscar_pesagem_coletiva(lote)
        return _DadosZootecnicosLote(
            modo_gestao="POR_LOTE",
            quantidade_animais=qtd,
            peso_total_kg=peso_total,
            peso_medio_kg=peso_medio,
            peso_inicial_total_kg=peso_inicial,
            custo_aquisicao_total=float(lote.valor_aquisicao_total or 0.0),
            gmd_medio=gmd,
            ultima_pesagem=ultima_pesagem,
        )

    async def _buscar_peso_inicial_individual(
        self, lote: LoteAnimal, qtd_com_peso: int
    ) -> float | None:
        if lote.peso_inicial_medio_kg is not None and qtd_com_peso > 0:
            return float(lote.peso_inicial_medio_kg) * qtd_com_peso
        return None

    async def _buscar_pesagem_coletiva(
        self, lote: LoteAnimal
    ) -> tuple[float | None, date | None]:
        stmt = (
            select(ManejoLote.data_evento, ManejoLote.quantidade_cabecas, ManejoLote.peso_total_kg)
            .where(
                ManejoLote.tenant_id == self.tenant_id,
                ManejoLote.lote_id == lote.id,
                ManejoLote.tipo_evento == "PESAGEM",
            )
            .order_by(ManejoLote.data_evento.asc(), ManejoLote.created_at.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        if not rows:
            return None, None
        pontos = self._extrair_pontos_pesagem_coletiva(rows, lote.quantidade_cabecas)
        ultima = rows[-1][0]
        gmds = self._calcular_gmds_coletivos(pontos)
        return (round(sum(gmds) / len(gmds), 3) if gmds else None), ultima

    @staticmethod
    def _extrair_pontos_pesagem_coletiva(
        rows: list[tuple], cabecas_fallback: int
    ) -> list[tuple[date, float]]:
        pontos: list[tuple[date, float]] = []
        for data_ev, qtd, peso_total in rows:
            divisor = int(qtd or cabecas_fallback or 0)
            if divisor > 0 and peso_total is not None and float(peso_total) > 0:
                pontos.append((data_ev, float(peso_total) / divisor))
        return pontos

    @staticmethod
    def _calcular_gmds_coletivos(pontos: list[tuple[date, float]]) -> list[float]:
        gmds: list[float] = []
        for idx in range(1, len(pontos)):
            dias = (pontos[idx][0] - pontos[idx - 1][0]).days
            gmd = calcular_gmd(pontos[idx][1], pontos[idx - 1][1], dias)
            if gmd is not None:
                gmds.append(gmd)
        return gmds

    async def _calcular_gmd_medio(self, lote_id: uuid.UUID) -> float | None:
        stmt = (
            select(EventoAnimal.animal_id, EventoAnimal.data_evento, EventoAnimal.peso_kg)
            .join(Animal, and_(Animal.id == EventoAnimal.animal_id, Animal.tenant_id == self.tenant_id))
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
        return round(sum(gm_ds) / len(gm_ds), 3) if gm_ds else None

    async def _buscar_ultima_pesagem(self, lote_id: uuid.UUID) -> date | None:
        stmt = (
            select(func.max(EventoAnimal.data_evento))
            .join(Animal, and_(Animal.id == EventoAnimal.animal_id, Animal.tenant_id == self.tenant_id))
            .where(
                EventoAnimal.tenant_id == self.tenant_id,
                Animal.lote_id == lote_id,
                Animal.status == "ATIVO",
                EventoAnimal.tipo == "PESAGEM",
            )
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def _buscar_custos_lote(self, lote_id: uuid.UUID) -> _CustosLote:
        return _CustosLote(
            sanitario=await self._buscar_custo_sanitario_total(lote_id),
            nutricao=await self._buscar_custo_nutricao_total(lote_id),
            outros=await self._buscar_custo_outros_total(lote_id),
        )

    async def _buscar_custo_sanitario_total(self, lote_id: uuid.UUID) -> float:
        stmt_ca = (
            select(func.coalesce(func.sum(CostAllocation.amount), 0))
            .join(TarefaCampo, and_(TarefaCampo.id == CostAllocation.source_id, TarefaCampo.tenant_id == self.tenant_id))
            .join(EstoqueMovimento, and_(EstoqueMovimento.id == CostAllocation.inventory_movement_id, EstoqueMovimento.tenant_id == self.tenant_id))
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
        stmt_manejo = select(func.coalesce(func.sum(ManejoLote.custo_total), 0)).where(
            ManejoLote.tenant_id == self.tenant_id,
            ManejoLote.lote_id == lote_id,
            ManejoLote.tipo_evento.in_(TIPOS_MANEJO_SANITARIO),
            ManejoLote.custo_total.is_not(None),
        )
        custo_ca = float((await self.session.execute(stmt_ca)).scalar_one() or 0)
        custo_manejo = float((await self.session.execute(stmt_manejo)).scalar_one() or 0)
        return custo_ca + custo_manejo

    async def _buscar_custo_nutricao_total(self, lote_id: uuid.UUID) -> float:
        fin_stmt = select(func.coalesce(func.sum(LancamentoFinanceiro.valor), 0)).where(
            LancamentoFinanceiro.tenant_id == self.tenant_id,
            LancamentoFinanceiro.tipo == "CUSTO",
            LancamentoFinanceiro.origem_id == lote_id,
            self._filtro_lancamento_nutricao(),
        )
        ca_stmt = select(func.coalesce(func.sum(CostAllocation.amount), 0)).where(
            CostAllocation.tenant_id == self.tenant_id,
            CostAllocation.source_id == lote_id,
            CostAllocation.cost_category.in_(("NUTRICAO", "CONFINAMENTO")),
        )
        custo_fin = float((await self.session.execute(fin_stmt)).scalar_one() or 0)
        custo_ca = float((await self.session.execute(ca_stmt)).scalar_one() or 0)
        return custo_fin + custo_ca

    async def _buscar_custo_outros_total(self, lote_id: uuid.UUID) -> float:
        fin_stmt = select(func.coalesce(func.sum(LancamentoFinanceiro.valor), 0)).where(
            LancamentoFinanceiro.tenant_id == self.tenant_id,
            LancamentoFinanceiro.tipo == "CUSTO",
            LancamentoFinanceiro.origem_id == lote_id,
            not_(self._filtro_lancamento_nutricao()),
        )
        ca_stmt = select(func.coalesce(func.sum(CostAllocation.amount), 0)).where(
            CostAllocation.tenant_id == self.tenant_id,
            CostAllocation.source_id == lote_id,
            CostAllocation.cost_category.not_in(CATEGORIAS_COST_EXCLUIDAS),
        )
        custo_fin = float((await self.session.execute(fin_stmt)).scalar_one() or 0)
        custo_ca = float((await self.session.execute(ca_stmt)).scalar_one() or 0)
        return custo_fin + custo_ca

    @staticmethod
    def _filtro_lancamento_nutricao():
        return or_(
            func.coalesce(LancamentoFinanceiro.origem, "").in_(ORIGENS_NUTRICAO),
            func.coalesce(LancamentoFinanceiro.categoria, "").in_(CATEGORIAS_NUTRICAO),
        )

    async def _buscar_area_piquete_ha(self, piquete_id: uuid.UUID | None) -> float:
        if piquete_id is None:
            return 0.0
        stmt = select(func.coalesce(AreaRural.area_hectares, AreaRural.area_hectares_manual)).where(
            AreaRural.id == piquete_id,
            AreaRural.tenant_id == self.tenant_id,
        )
        return float((await self.session.execute(stmt)).scalar_one_or_none() or 0)

    def _montar_resposta(
        self,
        lote: LoteAnimal,
        zootecnico: _DadosZootecnicosLote,
        custos: _CustosLote,
        area_piquete_ha: float,
        cotacao_publica: tuple[float | None, str | None],
    ) -> LoteIndicadoresResponse:
        rendimento = normalizar_rendimento_carcaca(lote.rendimento_carcaca_pct)
        cotacao_valor, fonte_cotacao = cotacao_arroba_service.resolver_cotacao_lote(
            lote.cotacao_arroba_override, cotacao_publica
        )
        metricas = calcular_metricas_economicas_arroba(
            EntradaEconomicaArroba(
                peso_vivo_kg=zootecnico.peso_total_kg,
                peso_inicial_kg=zootecnico.peso_inicial_total_kg,
                rendimento_carcaca_pct=rendimento,
                quantidade_animais=zootecnico.quantidade_animais,
                custo_aquisicao=zootecnico.custo_aquisicao_total,
                custo_sanitario=custos.sanitario,
                custo_nutricao=custos.nutricao,
                custo_outros=custos.outros,
                cotacao_arroba=cotacao_valor,
            )
        )
        qtd = zootecnico.quantidade_animais
        peso_total = zootecnico.peso_total_kg
        ua_total = calcular_ua_por_peso(peso_total, qtd)
        return LoteIndicadoresResponse(
            lote_id=lote.id,
            nome_lote=lote.identificacao,
            modo_gestao=zootecnico.modo_gestao,
            rendimento_carcaca_pct=rendimento,
            quantidade_animais=qtd,
            peso_total_kg=round(peso_total, 2),
            peso_medio_kg=round(zootecnico.peso_medio_kg, 2),
            arrobas_totais=metricas.arrobas_totais,
            arrobas_produzidas=metricas.arrobas_produzidas,
            gmd_medio_kg_dia=zootecnico.gmd_medio,
            ultima_pesagem=zootecnico.ultima_pesagem,
            custo_sanitario_total=round(custos.sanitario, 2),
            custo_sanitario_por_cabeca=round(custos.sanitario / qtd, 4) if qtd else 0.0,
            custo_sanitario_por_kg=round(custos.sanitario / peso_total, 4) if peso_total else 0.0,
            custo_sanitario_por_arroba=metricas.custo_sanitario_por_arroba,
            custo_aquisicao_total=round(zootecnico.custo_aquisicao_total, 2),
            area_piquete_ha=round(area_piquete_ha, 2),
            lotacao_ua_ha=round(ua_total / area_piquete_ha, 2) if area_piquete_ha > 0 else 0.0,
            arrobas_por_hectare=round(metricas.arrobas_totais / area_piquete_ha, 2) if area_piquete_ha > 0 else 0.0,
            custo_nutricao_total=round(custos.nutricao, 2),
            custo_outros_total=round(custos.outros, 2),
            custo_total_operacional=metricas.custo_total_operacional,
            custo_total_por_arroba=metricas.custo_total_por_arroba,
            custo_por_arroba_produzida=metricas.custo_por_arroba_produzida,
            custo_break_even_por_arroba=metricas.custo_break_even_por_arroba,
            cotacao_arroba_referencia=cotacao_valor,
            fonte_cotacao=fonte_cotacao,
            valor_mercado_estimado=metricas.valor_mercado_estimado,
            margem_bruta_estimada=metricas.margem_bruta_estimada,
            margem_estimada_por_cabeca=metricas.margem_estimada_por_cabeca,
        )

    def _extrair_gmds(self, rows: list[tuple[uuid.UUID, date, float | None]]) -> list[float]:
        gm_ds: list[float] = []
        ultimo_animal: uuid.UUID | None = None
        peso_anterior: float | None = None
        data_anterior: date | None = None
        for animal_id, data_evento, peso_kg in rows:
            if animal_id != ultimo_animal:
                ultimo_animal, peso_anterior, data_anterior = animal_id, None, None
            if data_anterior and peso_anterior is not None and peso_kg is not None:
                dias = (data_evento - data_anterior).days
                gmd = calcular_gmd(peso_kg, peso_anterior, dias)
                if gmd is not None:
                    gm_ds.append(gmd)
            peso_anterior = float(peso_kg) if peso_kg is not None else peso_anterior
            data_anterior = data_evento
        return gm_ds
