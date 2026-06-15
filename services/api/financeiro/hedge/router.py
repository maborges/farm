"""
Router — Hedge / Exposição Física × Financeira

Prefixo: /hedge
Módulo: F4_HEDGING (NÃO usa EXT_IA)

Endpoints:
  POST /hedge/contratos              — Cria instrumento futuro
  GET  /hedge/contratos              — Lista instrumentos
  POST /hedge/registros              — Registra operação de hedge
  GET  /hedge/registros              — Lista operações
  GET  /hedge/posicao                — Posição consolidada (projeção calculada)
  GET  /hedge/exposicao              — Exposição física × financeira completa
  GET  /hedge/exposicao/consolidado  — Visão multi-safra/multi-commodity
  GET  /hedge/exposicao/historico    — Série temporal MTM (ENTERPRISE)
"""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import Modulos
from core.dependencies import (
    get_session_with_tenant,
    get_tenant_id,
    get_user_id,
    require_module,
    require_tenant_permission,
    require_tier,
)
from core.constants import PlanTier
from core.exceptions import EntityNotFoundError, BusinessRuleError

from .schemas import (
    ContratoFuturoCreate,
    ContratoFuturoResponse,
    HedgeRegistroCreate,
    HedgeRegistroResponse,
    HedgePosicaoResponse,
    HedgeExposicaoResponse,
    HedgePositionSnapshotResponse,
    ReprocessarMtMRequest,
    ReprocessarMtMResponse,
    ExposicaoConsolidadaResponse,
    ExposicaoHistoricoItem,
)
from .service import HedgeService, HedgeExposureService
from .snapshot_service import HedgeSnapshotService

router = APIRouter(
    prefix="/hedge",
    tags=["Financeiro — Hedge"],
    dependencies=[Depends(require_module(Modulos.FINANCEIRO_HEDGING))],
)


# ==============================================================================
# ContratoFuturo
# ==============================================================================

@router.post(
    "/contratos",
    response_model=ContratoFuturoResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Cria instrumento de hedge (contrato futuro)",
)
async def criar_contrato(
    data: ContratoFuturoCreate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: Optional[uuid.UUID] = Depends(get_user_id),
):
    """Registra um novo contrato futuro de commodity para proteção de preço.

    Regras:
    - quantidade deve ser > 0.
    - preco_contratado, se informado, deve ser > 0.
    - status inicia em ABERTO.
    """
    svc = HedgeService(session, tenant_id)
    try:
        contrato = await svc.criar_contrato(data, user_id=user_id)
        await session.commit()
        await session.refresh(contrato)
        return contrato
    except BusinessRuleError as exc:
        raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))


@router.get(
    "/contratos",
    response_model=list[ContratoFuturoResponse],
    summary="Lista instrumentos de hedge",
)
async def listar_contratos(
    safra_id: Optional[uuid.UUID] = Query(None),
    commodity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Lista contratos futuros do tenant com filtros opcionais."""
    svc = HedgeService(session, tenant_id)
    return await svc.listar_contratos(
        safra_id=safra_id, commodity=commodity, status=status
    )


# ==============================================================================
# HedgeRegistro
# ==============================================================================

@router.post(
    "/registros",
    response_model=HedgeRegistroResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Registra operação de hedge",
)
async def criar_registro(
    data: HedgeRegistroCreate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: Optional[uuid.UUID] = Depends(get_user_id),
):
    """Registra uma operação de hedge vinculada a um contrato futuro.

    Regras:
    - O contrato referenciado deve pertencer ao mesmo tenant.
    - Não é permitido registrar operação em contrato ENCERRADO ou LIQUIDADO.
    - quantidade deve ser > 0 e preco deve ser > 0.
    """
    svc = HedgeService(session, tenant_id)
    try:
        registro = await svc.criar_registro(data, user_id=user_id)
        await session.commit()
        await session.refresh(registro)
        return registro
    except EntityNotFoundError as exc:
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, str(exc))
    except BusinessRuleError as exc:
        raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))


@router.get(
    "/registros",
    response_model=list[HedgeRegistroResponse],
    summary="Lista operações de hedge",
)
async def listar_registros(
    contrato_futuro_id: Optional[uuid.UUID] = Query(None),
    safra_id: Optional[uuid.UUID] = Query(None),
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Lista operações de hedge do tenant com filtros opcionais."""
    svc = HedgeService(session, tenant_id)
    return await svc.listar_registros(
        contrato_futuro_id=contrato_futuro_id,
        safra_id=safra_id,
    )


# ==============================================================================
# Posição e Exposição (projeções calculadas)
# ==============================================================================

@router.get(
    "/posicao",
    response_model=HedgePosicaoResponse,
    summary="Posição consolidada de hedge (projeção calculada)",
)
async def calcular_posicao(
    safra_id: Optional[uuid.UUID] = Query(None),
    commodity: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Retorna a posição de hedge consolidada.

    NÃO existe tabela hedge_positions.
    A posição é calculada em tempo real a partir dos ContratosFuturos abertos.
    """
    svc = HedgeService(session, tenant_id)
    return await svc.calcular_posicao(safra_id=safra_id, commodity=commodity)


@router.get(
    "/exposicao",
    response_model=HedgeExposicaoResponse,
    summary="Exposição física × financeira completa",
)
async def calcular_exposicao(
    safra_id: Optional[uuid.UUID] = Query(None),
    commodity: Optional[str] = Query(None, description="Filtro por commodity/cultura (ex: SOJA, MILHO)"),
    unidade_produtiva_id: Optional[uuid.UUID] = Query(None, description="Filtro por Unidade Produtiva"),
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Calcula a exposição física × financeira completa do tenant.

    Fórmula:
        exposicao_bruta      = Σ (produtividade_meta_sc_ha × area_ha) + estoque_fisico
        compromissos_fisicos = Σ comercializações confirmadas/entregues/finalizadas
        protecao_financeira  = Σ contratos futuros ABERTOS
        exposicao_aberta     = (exposicao_bruta - compromissos) - protecao
        percentual_cobertura = protecao / (exposicao_bruta - compromissos) × 100
        classificacao_risco  = DESCOBERTO (<70%) | EQUILIBRADO (70–110%) | SOBREPROTEGIDO (>110%)

    Dados vêm de Cultivo, SaldoEstoque, ComercializacaoCommodity e ContratoFuturo.
    Nenhuma tabela nova criada — funcionalidade 100% analítica.
    """
    svc = HedgeExposureService(session, tenant_id)
    return await svc.calcular_exposicao(
        safra_id=safra_id,
        commodity=commodity,
        unidade_produtiva_id=unidade_produtiva_id,
    )


@router.get(
    "/exposicao/consolidado",
    response_model=ExposicaoConsolidadaResponse,
    summary="Exposição consolidada multi-safra e multi-commodity",
)
async def calcular_exposicao_consolidada(
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Retorna visão consolidada de exposição agrupada por safra e commodity.

    Agrega todas as safras e commodities do tenant, exibindo subtotais por grupo
    e totais globais com classificação de risco unificada.

    Não existe tabela de consolidação — calculado em tempo real a partir
    de Cultivo, ComercializacaoCommodity e ContratoFuturo.
    """
    svc = HedgeExposureService(session, tenant_id)
    return await svc.calcular_consolidado()


@router.get(
    "/exposicao/historico",
    response_model=list[ExposicaoHistoricoItem],
    summary="Série temporal de cobertura (ENTERPRISE)",
    dependencies=[Depends(require_tier(PlanTier.ENTERPRISE))],
)
async def calcular_exposicao_historico(
    safra_id: Optional[uuid.UUID] = Query(None),
    commodity_id: Optional[uuid.UUID] = Query(None),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    limit: int = Query(90, ge=1, le=365),
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Retorna a série temporal da posição de cobertura baseada nos snapshots MTM.

    Utiliza os dados de hedge_position_snapshots_v2 já persistidos para
    construir a evolução histórica. Nenhum dado novo é calculado.

    Disponível apenas no tier ENTERPRISE.
    """
    svc = HedgeSnapshotService(session)
    snapshots = await svc.listar_snapshots(
        tenant_id=tenant_id,
        safra_id=safra_id,
        commodity_id=commodity_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=limit,
    )
    return [
        ExposicaoHistoricoItem(
            data_referencia=str(s.data_referencia),
            quantidade_aberta_sc=float(s.quantidade_aberta),
            pnl_nao_realizado=float(s.pnl_nao_realizado),
            preco_medio_mercado=float(s.preco_mercado) if s.preco_mercado else None,
        )
        for s in snapshots
    ]


# ==============================================================================
# Snapshots de Posição (Mark-to-Market)
# ==============================================================================

@router.get(
    "/snapshots",
    response_model=list[HedgePositionSnapshotResponse],
    summary="Lista snapshots consolidados de MTM (apenas leitura)",
)
async def listar_snapshots(
    safra_id: Optional[uuid.UUID] = Query(None),
    commodity_id: Optional[uuid.UUID] = Query(None),
    contrato_futuro_id: Optional[uuid.UUID] = Query(None),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Lista snapshots de Mark-to-Market de forma paginada e com filtros.
    
    Apenas para leitura consolidada. O snapshot não é recalculado por este endpoint.
    """
    svc = HedgeSnapshotService(session)
    return await svc.listar_snapshots(
        tenant_id=tenant_id,
        safra_id=safra_id,
        commodity_id=commodity_id,
        contrato_futuro_id=contrato_futuro_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=limit,
        offset=offset
    )

@router.post(
    "/snapshots/reprocessar",
    response_model=ReprocessarMtMResponse,
    summary="Reprocessa os snapshots de MTM retroativamente",
    dependencies=[Depends(require_tenant_permission("financeiro:*"))],
)
async def reprocessar_snapshots(
    data: ReprocessarMtMRequest,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user_id: Optional[uuid.UUID] = Depends(get_user_id),
):
    """
    Reprocessa o MTM retroativamente para um intervalo de datas e contratos aplicáveis.
    
    Regras:
    - Exige permissão financeiro:* (admin/owner).
    - Intervalo máximo de 31 dias.
    - O motivo é obrigatório para auditoria.
    """
    svc = HedgeSnapshotService(session)
    try:
        resultado = await svc.reprocessar_snapshots(
            tenant_id=tenant_id,
            user_id=user_id,
            data_inicio=data.data_inicio,
            data_fim=data.data_fim,
            safra_id=data.safra_id,
            commodity_id=data.commodity_id,
            contrato_futuro_id=data.contrato_futuro_id,
            motivo=data.motivo
        )
        await session.commit()
        return resultado
    except ValueError as exc:
        raise HTTPException(http_status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
