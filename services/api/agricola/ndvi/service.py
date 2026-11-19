from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.ndvi.models import ImagemNDVI
from agricola.ndvi.schemas import (
    NDVIAlertaResumo,
    NDVICreate,
    NDVIResumoPropriedadeResponse,
    NDVITalhaoResumo,
)
from core.base_service import BaseService
from core.cadastros.propriedades.models import AreaRural, TIPOS_AREA_PRODUTIVA
from core.exceptions import EntityNotFoundError

_DEFAULT_LIST_LIMIT = 500


def _classificar_ndvi(indice: float | None) -> str:
    """Classifica o índice NDVI em faixas agronômicas legíveis."""
    if indice is None:
        return "Sem dados"
    if indice >= 0.6:
        return "Excelente"
    if indice >= 0.4:
        return "Moderado"
    if indice >= 0.2:
        return "Atenção"
    if indice >= 0.0:
        return "Crítico"
    return "Água / Nuvem"


def _calcular_variacao_e_tendencia(
    indice_atual: float | None,
    indice_anterior: float | None,
) -> tuple[float | None, Literal["SUBINDO", "CAINDO", "ESTAVEL"] | None]:
    """Calcula a variação percentual e tendência entre as duas capturas mais recentes."""
    if indice_atual is None or indice_anterior is None:
        return None, None
    delta = indice_atual - indice_anterior
    tendencia: Literal["SUBINDO", "CAINDO", "ESTAVEL"] = (
        "SUBINDO" if delta > 0.02 else "CAINDO" if delta < -0.02 else "ESTAVEL"
    )
    variacao_pct = round((delta / abs(indice_anterior)) * 100, 1) if indice_anterior != 0 else None
    return variacao_pct, tendencia


def _alerta_estresse(resumo: NDVITalhaoResumo) -> NDVIAlertaResumo | None:
    """Gera alerta quando o NDVI atual indica estresse vegetativo ou solo exposto."""
    indice = resumo.indice_atual
    if indice is None or indice >= 0.45:
        return None
    is_critico = indice < 0.2
    return NDVIAlertaResumo(
        talhao_id=resumo.talhao_id,
        talhao_nome=resumo.talhao_nome,
        tipo="ESTRESSE_HIDRICO",
        severidade="CRITICO" if is_critico else "ATENCAO",
        titulo="Solo exposto / estresse severo" if is_critico else "Vigor abaixo do ideal",
        detalhe=f"NDVI atual em {indice:.3f} ({resumo.classificacao}).",
        indice_atual=indice,
    )


def _alerta_queda(resumo: NDVITalhaoResumo) -> NDVIAlertaResumo | None:
    """Gera alerta quando há queda expressiva em relação à captura anterior."""
    variacao = resumo.variacao_pct
    if variacao is None or variacao > -5.0:
        return None
    is_critico = variacao <= -10.0
    return NDVIAlertaResumo(
        talhao_id=resumo.talhao_id,
        talhao_nome=resumo.talhao_nome,
        tipo="QUEDA_VIGOR",
        severidade="CRITICO" if is_critico else "ATENCAO",
        titulo=f"Queda de {abs(variacao):.1f}%",
        detalhe=f"Vigor caiu de {resumo.indice_anterior:.3f} para {resumo.indice_atual:.3f}.",
        indice_atual=resumo.indice_atual,
        variacao_pct=variacao,
    )


def _alerta_nuvem(resumo: NDVITalhaoResumo) -> NDVIAlertaResumo | None:
    """Gera alerta quando a última captura apresenta alta cobertura de nuvens."""
    nuvens = resumo.cobertura_nuvens_pct
    if nuvens is None or nuvens < 30.0:
        return None
    return NDVIAlertaResumo(
        talhao_id=resumo.talhao_id,
        talhao_nome=resumo.talhao_nome,
        tipo="NUVEM_ALTA",
        severidade="ATENCAO",
        titulo=f"Nuvem {nuvens:.0f}%",
        detalhe="Alta cobertura de nuvens na última captura; recomenda-se nova leitura.",
        cobertura_nuvens_pct=nuvens,
    )


def _gerar_alertas_talhao(resumo: NDVITalhaoResumo) -> list[NDVIAlertaResumo]:
    """Coleta todos os alertas agronômicos aplicáveis ao resumo do talhão."""
    candidatos = (_alerta_estresse(resumo), _alerta_queda(resumo), _alerta_nuvem(resumo))
    return [alerta for alerta in candidatos if alerta is not None]


def _extrair_area_hectares(area: Any) -> float | None:
    """Retorna área em hectares priorizando polígono calculado com fallback manual."""
    valor = area.area_hectares if area.area_hectares is not None else area.area_hectares_manual
    return float(valor) if valor is not None else None


def _media_ou_none(valores: list[float], casas: int = 3) -> float | None:
    """Retorna a média aritmética arredondada ou None quando a lista estiver vazia."""
    return round(sum(valores) / len(valores), casas) if valores else None


def _montar_resumo_talhao(area: Any, imgs: list[ImagemNDVI]) -> NDVITalhaoResumo:
    """Agrega as imagens ordenadas de uma área produtiva em resumo consolidado."""
    ordenadas = sorted(imgs, key=lambda img: (img.data_captura, img.created_at))
    com_indice = [img for img in ordenadas if img.indice_medio is not None]
    indice_atual = float(com_indice[-1].indice_medio) if com_indice else None
    indice_anterior = float(com_indice[-2].indice_medio) if len(com_indice) >= 2 else None
    variacao_pct, tendencia = _calcular_variacao_e_tendencia(indice_atual, indice_anterior)
    ultima = ordenadas[-1] if ordenadas else None
    return NDVITalhaoResumo(
        talhao_id=area.id,
        talhao_nome=area.nome,
        tipo_area=area.tipo,
        area_hectares=_extrair_area_hectares(area),
        unidade_produtiva_id=area.unidade_produtiva_id,
        total_imagens=len(ordenadas),
        indice_atual=indice_atual,
        indice_anterior=indice_anterior,
        variacao_pct=variacao_pct,
        cobertura_nuvens_pct=(
            float(ultima.cobertura_nuvens_pct)
            if ultima and ultima.cobertura_nuvens_pct is not None
            else None
        ),
        ultima_captura=ultima.data_captura if ultima else None,
        tendencia=tendencia,
        classificacao=_classificar_ndvi(indice_atual),
        satelite=ultima.satelite if ultima else None,
    )


class NDVIService(BaseService[ImagemNDVI]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(ImagemNDVI, session, tenant_id)

    async def _buscar_areas_produtivas(self, unidade_produtiva_id: UUID | None) -> list[Any]:
        """Busca áreas produtivas ativas do tenant, filtrando por propriedade se informada.

        Args:
            unidade_produtiva_id: UUID opcional da propriedade.

        Returns:
            Lista de linhas de áreas produtivas ordenadas por nome.
        """
        tipos_produtivos = [t.value for t in TIPOS_AREA_PRODUTIVA]
        stmt = (
            select(
                AreaRural.id,
                AreaRural.nome,
                AreaRural.tipo,
                AreaRural.area_hectares,
                AreaRural.area_hectares_manual,
                AreaRural.unidade_produtiva_id,
            )
            .where(
                AreaRural.tenant_id == self.tenant_id,
                AreaRural.ativo == True,  # noqa: E712
                AreaRural.tipo.in_(tipos_produtivos),
            )
            .order_by(AreaRural.nome.asc())
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(AreaRural.unidade_produtiva_id == unidade_produtiva_id)
        return list((await self.session.execute(stmt)).all())

    async def _buscar_imagens_por_areas(
        self,
        area_ids: list[UUID],
        periodo_dias: int | None,
    ) -> dict[UUID, list[ImagemNDVI]]:
        """Carrega imagens NDVI das áreas solicitadas com filtro opcional por período.

        Args:
            area_ids: Lista de IDs de áreas rurais.
            periodo_dias: Quantidade opcional de dias retroativos.

        Returns:
            Dicionário mapeando talhao_id para suas imagens NDVI.
        """
        if not area_ids:
            return {}
        stmt = select(ImagemNDVI).where(
            ImagemNDVI.tenant_id == self.tenant_id,
            ImagemNDVI.talhao_id.in_(area_ids),
        )
        if periodo_dias is not None:
            data_corte = date.today() - timedelta(days=periodo_dias)
            stmt = stmt.where(ImagemNDVI.data_captura >= data_corte)
        stmt = stmt.order_by(ImagemNDVI.data_captura.asc(), ImagemNDVI.created_at.asc())
        imagens = list((await self.session.execute(stmt)).scalars().all())
        agrupado: dict[UUID, list[ImagemNDVI]] = defaultdict(list)
        for img in imagens:
            agrupado[img.talhao_id].append(img)
        return agrupado

    async def registrar_manual(self, data: NDVICreate) -> ImagemNDVI:
        """Registra manualmente uma leitura NDVI após validar o talhão no tenant.

        Args:
            data: Payload validado de registro NDVI.

        Returns:
            Instância persistida de ImagemNDVI.

        Raises:
            EntityNotFoundError: Se o talhão não existir ou não estiver ativo no tenant.
        """
        stmt = select(AreaRural.id).where(
            AreaRural.id == data.talhao_id,
            AreaRural.tenant_id == self.tenant_id,
            AreaRural.ativo == True,  # noqa: E712
        )
        area_existente = (await self.session.execute(stmt)).scalar_one_or_none()
        if area_existente is None:
            raise EntityNotFoundError(
                f"Área produtiva {data.talhao_id} não encontrada ou inativa neste tenant."
            )
        return await self.create(data)

    async def listar_imagens(
        self,
        talhao_id: UUID | None = None,
        periodo_dias: int | None = None,
    ) -> list[ImagemNDVI]:
        """Lista registros NDVI do tenant com ordenação cronológica decrescente.

        Args:
            talhao_id: Filtro opcional por área rural.
            periodo_dias: Janela opcional de dias a partir da data atual.

        Returns:
            Lista de ImagemNDVI pertencentes ao tenant.
        """
        stmt = select(ImagemNDVI).where(ImagemNDVI.tenant_id == self.tenant_id)
        if talhao_id is not None:
            stmt = stmt.where(ImagemNDVI.talhao_id == talhao_id)
        if periodo_dias is not None:
            data_corte = date.today() - timedelta(days=periodo_dias)
            stmt = stmt.where(ImagemNDVI.data_captura >= data_corte)
        stmt = stmt.order_by(
            ImagemNDVI.data_captura.desc(),
            ImagemNDVI.created_at.desc(),
        ).limit(_DEFAULT_LIST_LIMIT)
        return list((await self.session.execute(stmt)).scalars().all())

    async def excluir_registro(self, imagem_id: UUID) -> None:
        """Exclui um registro NDVI pertencente ao tenant.

        Args:
            imagem_id: Identificador do registro ImagemNDVI.

        Raises:
            EntityNotFoundError: Quando o registro não existe no tenant atual.
        """
        await self.hard_delete(imagem_id)

    async def obter_resumo_propriedade(
        self,
        unidade_produtiva_id: UUID | None = None,
        periodo_dias: int | None = None,
    ) -> NDVIResumoPropriedadeResponse:
        """Consolida KPIs, histórico resumido por área e alertas reais de NDVI.

        Args:
            unidade_produtiva_id: Filtro opcional por propriedade ativa.
            periodo_dias: Janela opcional de dias para filtrar capturas.

        Returns:
            NDVIResumoPropriedadeResponse com visão real da propriedade.
        """
        areas = await self._buscar_areas_produtivas(unidade_produtiva_id)
        area_ids = [area.id for area in areas]
        imagens_por_area = await self._buscar_imagens_por_areas(area_ids, periodo_dias)
        talhoes = [_montar_resumo_talhao(area, imagens_por_area.get(area.id, [])) for area in areas]

        indices = [t.indice_atual for t in talhoes if t.indice_atual is not None]
        variacoes = [t.variacao_pct for t in talhoes if t.variacao_pct is not None]
        media_ndvi = _media_ou_none(indices, 3)
        alertas = [alerta for t in talhoes for alerta in _gerar_alertas_talhao(t)]
        alertas.sort(key=lambda a: 0 if a.severidade == "CRITICO" else 1)

        return NDVIResumoPropriedadeResponse(
            unidade_produtiva_id=unidade_produtiva_id,
            periodo_dias=periodo_dias,
            total_areas_produtivas=len(talhoes),
            areas_monitoradas=sum(1 for t in talhoes if t.total_imagens > 0),
            total_registros=sum(t.total_imagens for t in talhoes),
            media_ndvi_propriedade=media_ndvi,
            variacao_media_pct=_media_ou_none(variacoes, 1),
            classificacao_geral=_classificar_ndvi(media_ndvi),
            sincronizacao_automatica_disponivel=False,
            talhoes=talhoes,
            alertas=alertas,
        )

    async def get_serie_temporal(self, talhao_id: UUID) -> dict:
        """Retorna série temporal NDVI ordenada no formato esperado por NdviTalhao.

        Args:
            talhao_id: ID da área produtiva (talhão/piquete).

        Returns:
            Dicionário com total_imagens, indice_atual, tendencia e dados.
        """
        imagens = sorted(await self.list_all(talhao_id=talhao_id), key=lambda img: img.data_captura)
        dados = [
            {
                "data": img.data_captura.isoformat(),
                "indice_medio": float(img.indice_medio) if img.indice_medio is not None else None,
                "cobertura_nuvens_pct": (
                    float(img.cobertura_nuvens_pct)
                    if img.cobertura_nuvens_pct is not None
                    else None
                ),
            }
            for img in imagens
        ]

        com_indice = [d["indice_medio"] for d in dados if d["indice_medio"] is not None]
        indice_atual = com_indice[-1] if com_indice else None
        indice_anterior = com_indice[-2] if len(com_indice) >= 2 else None
        _, tendencia = _calcular_variacao_e_tendencia(indice_atual, indice_anterior)

        return {
            "talhao_id": str(talhao_id),
            "total_imagens": len(dados),
            "indice_atual": indice_atual,
            "tendencia": tendencia,
            "dados": dados,
        }
