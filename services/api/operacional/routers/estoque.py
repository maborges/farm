from core.dependencies import require_tenant_permission
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from core.dependencies import get_session, get_current_tenant, require_limit, require_module
from core.models.tenant import Tenant
from operacional.services.estoque_service import EstoqueService
from core.dependencies import get_current_user
from core.models.auth import Usuario
from operacional.schemas.estoque import (
    DepositoCreate, DepositoUpdate, DepositoResponse,
    SaldoResponse,
    EntradaEstoqueRequest, SaidaEstoqueRequest,
    AjusteEstoqueRequest, AjusteMovimentoRequest, TransferenciaEstoqueRequest,
    MovimentacaoResponse, AlertaEstoqueItem, AuditoriaMovimentacaoResponse,
    SaldoMinimoUpdateRequest, SaldoMaximoUpdateRequest,
    LoteCreate, LoteUpdate, LoteResponse,
    RequisicaoCreate, RequisicaoAprovarRequest, RequisicaoEntregarRequest, RequisicaoResponse,
    ConfirmarRetiradaRequest, ConfirmarDevolucaoRequest,
    ReservaCreate, ReservaCancelarRequest, ReservaConsumirRequest, ReservaResponse,
    EstoqueLocalizacaoCreate, EstoqueLocalizacaoUpdate, EstoqueLocalizacaoResponse,
)

router = APIRouter(prefix="/estoque", tags=["Operacional — Estoque"], dependencies=[Depends(require_module("O2_ESTOQUE"))])


def _svc(session: AsyncSession, tenant: Tenant) -> EstoqueService:
    return EstoqueService(session, tenant.id)


# ── Lotes ─────────────────────────────────────────────────────────────────────

@router.get("/lotes", response_model=List[LoteResponse])
async def listar_lotes(
    produto_id: Optional[uuid.UUID] = Query(None),
    deposito_id: Optional[uuid.UUID] = Query(None),
    vencendo_em_dias: Optional[int] = Query(None, description="Lotes vencendo nos próximos N dias"),
    apenas_ativos: bool = Query(True),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).listar_lotes(produto_id, deposito_id, vencendo_em_dias, apenas_ativos)


@router.post(
    "/lotes",
    response_model=LoteResponse,
    status_code=201,
    dependencies=[Depends(require_tenant_permission("operacional:*")), Depends(require_limit("storage_limite_mb"))],  # ← Valida limite de storage!
)
async def criar_lote(
    data: LoteCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.criar_lote(data)
    await session.commit()
    return result


@router.patch("/lotes/{lote_id}", response_model=LoteResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def atualizar_lote(
    lote_id: uuid.UUID,
    data: LoteUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.atualizar_lote(lote_id, data)
    await session.commit()
    return result


@router.get("/lotes/alertas-validade", response_model=List[LoteResponse])
async def alertas_validade(
    dias: int = Query(30, description="Alertar lotes vencendo em X dias"),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).listar_lotes(vencendo_em_dias=dias)


# ── Depósitos ─────────────────────────────────────────────────────────────────

@router.get("/depositos", response_model=List[DepositoResponse])
async def listar_depositos(
    unidade_produtiva_id: Optional[uuid.UUID] = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).listar_depositos(unidade_produtiva_id)


@router.post("/depositos", response_model=DepositoResponse, status_code=201,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def criar_deposito(
    data: DepositoCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.criar_deposito(data)
    await session.commit()
    return result


@router.patch("/depositos/{deposito_id}", response_model=DepositoResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def atualizar_deposito(
    deposito_id: uuid.UUID,
    data: DepositoUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.atualizar_deposito(deposito_id, data)
    await session.commit()
    return result


# ── Saldos ────────────────────────────────────────────────────────────────────

@router.get("/alertas-reposicao", response_model=List[AlertaEstoqueItem])
async def listar_alertas_reposicao(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).listar_alertas_reposicao()


@router.patch("/saldos/{saldo_id}/minimo", response_model=SaldoResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def atualizar_estoque_minimo(
    saldo_id: uuid.UUID,
    data: SaldoMinimoUpdateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    return await svc.atualizar_estoque_minimo(saldo_id, data.estoque_minimo)


@router.patch("/saldos/{saldo_id}/maximo", response_model=SaldoResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def atualizar_estoque_maximo(
    saldo_id: uuid.UUID,
    data: SaldoMaximoUpdateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    return await svc.atualizar_estoque_maximo(saldo_id, data.estoque_maximo)


# ── Localização física ───────────────────────────────────────────────────────

@router.get("/localizacoes", response_model=List[EstoqueLocalizacaoResponse])
async def listar_localizacoes(
    produto_id: Optional[uuid.UUID] = Query(None),
    deposito_id: Optional[uuid.UUID] = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).listar_localizacoes(produto_id, deposito_id)


@router.post("/localizacoes", response_model=EstoqueLocalizacaoResponse, status_code=201,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def criar_localizacao(
    data: EstoqueLocalizacaoCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.criar_localizacao(data)
    await session.commit()
    return result


@router.patch("/localizacoes/{localizacao_id}", response_model=EstoqueLocalizacaoResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def atualizar_localizacao(
    localizacao_id: uuid.UUID,
    data: EstoqueLocalizacaoUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.atualizar_localizacao(localizacao_id, data)
    await session.commit()
    return result


@router.delete("/localizacoes/{localizacao_id}", status_code=204,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def remover_localizacao(
    localizacao_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    await svc.remover_localizacao(localizacao_id)
    await session.commit()


@router.get("/saldos", response_model=List[SaldoResponse])
async def listar_saldos(
    unidade_produtiva_id: Optional[uuid.UUID] = Query(None),
    produto_id: Optional[uuid.UUID] = Query(None),
    deposito_id: Optional[uuid.UUID] = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).listar_saldos(unidade_produtiva_id, produto_id, deposito_id)


@router.get("/alertas", response_model=List[AlertaEstoqueItem])
async def alertas_estoque_minimo(
    unidade_produtiva_id: Optional[uuid.UUID] = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).alertas_estoque_minimo(unidade_produtiva_id)


# ── Movimentações ─────────────────────────────────────────────────────────────

@router.get("/movimentacoes", response_model=List[MovimentacaoResponse])
async def listar_movimentacoes(
    produto_id: Optional[uuid.UUID] = Query(None),
    deposito_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).listar_movimentacoes(produto_id, deposito_id, limit)


@router.get("/movimentacoes/{movimentacao_id}", response_model=MovimentacaoResponse)
async def obter_movimentacao(
    movimentacao_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).obter_movimentacao(movimentacao_id)


@router.post("/movimentacoes/{movimentacao_id}/ajustar", response_model=MovimentacaoResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def ajustar_movimentacao(
    movimentacao_id: uuid.UUID,
    data: AjusteMovimentoRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).ajustar_movimentacao(movimentacao_id, data)


@router.get("/movimentacoes/{movimentacao_id}/auditoria", response_model=AuditoriaMovimentacaoResponse)
async def obter_auditoria_movimentacao(
    movimentacao_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).get_auditoria_movimentacao(movimentacao_id)


@router.post("/movimentacoes/entrada", response_model=MovimentacaoResponse, status_code=201,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def registrar_entrada(
    data: EntradaEstoqueRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.registrar_entrada(data)
    await session.commit()
    return result


@router.post("/movimentacoes/saida", response_model=MovimentacaoResponse, status_code=201,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def registrar_saida(
    data: SaidaEstoqueRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.registrar_saida(data)
    await session.commit()
    return result


@router.post("/movimentacoes/ajuste", response_model=MovimentacaoResponse, status_code=201,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def registrar_ajuste(
    data: AjusteEstoqueRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.registrar_ajuste(data)
    await session.commit()
    return result


@router.post("/movimentacoes/transferencia", response_model=List[MovimentacaoResponse], status_code=201,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def registrar_transferencia(
    data: TransferenciaEstoqueRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.registrar_transferencia(data)
    await session.commit()
    return result


# ── Requisições de Material ────────────────────────────────────────────────────

@router.post("/requisicoes", response_model=RequisicaoResponse, status_code=201,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def criar_requisicao(
    data: RequisicaoCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    usuario: Usuario = Depends(get_current_user),
):
    svc = _svc(session, tenant)
    result = await svc.criar_requisicao(data, usuario.id)
    await session.commit()
    # commit() expira a relação `itens` (lazy="noload"); repopular para a resposta.
    return await svc._carregar_itens_requisicao(result)


@router.get("/requisicoes", response_model=List[RequisicaoResponse])
async def listar_requisicoes(
    unidade_produtiva_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).listar_requisicoes(unidade_produtiva_id, status)


@router.patch("/requisicoes/{req_id}/aprovar", response_model=RequisicaoResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def aprovar_requisicao(
    req_id: uuid.UUID,
    data: RequisicaoAprovarRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    usuario: Usuario = Depends(get_current_user),
):
    svc = _svc(session, tenant)
    result = await svc.aprovar_requisicao(req_id, data, usuario.id)
    await session.commit()
    return await svc._carregar_itens_requisicao(result)


@router.patch("/requisicoes/{req_id}/separar", response_model=RequisicaoResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def separar_requisicao(
    req_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.atualizar_status_requisicao(req_id, "SEPARANDO")
    await session.commit()
    return await svc._carregar_itens_requisicao(result)


@router.patch("/requisicoes/{req_id}/entregar", response_model=RequisicaoResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def entregar_requisicao(
    req_id: uuid.UUID,
    data: RequisicaoEntregarRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.entregar_requisicao(req_id, data)
    await session.commit()
    return await svc._carregar_itens_requisicao(result)


@router.post("/requisicoes/{req_id}/confirmar-retirada", response_model=RequisicaoResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def confirmar_retirada_requisicao(
    req_id: uuid.UUID,
    data: ConfirmarRetiradaRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Confirma a retirada física do material (reautenticação por e-mail+senha),
    baixando o estoque pela quantidade conferida por quem retira."""
    svc = _svc(session, tenant)
    result = await svc.confirmar_retirada_requisicao(req_id, data)
    await session.commit()
    return await svc._carregar_itens_requisicao(result)


@router.post("/requisicoes/{req_id}/confirmar-devolucao", response_model=RequisicaoResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def confirmar_devolucao_requisicao(
    req_id: uuid.UUID,
    data: ConfirmarDevolucaoRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Confirma devolução de sobra de insumo (reautenticação por e-mail+senha),
    estornando ao estoque."""
    svc = _svc(session, tenant)
    result = await svc.confirmar_devolucao_requisicao(req_id, data)
    await session.commit()
    return result


@router.patch("/requisicoes/{req_id}/recusar", response_model=RequisicaoResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def recusar_requisicao(
    req_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.atualizar_status_requisicao(req_id, "RECUSADA")
    await session.commit()
    return await svc._carregar_itens_requisicao(result)


# ── Reservas de Estoque ────────────────────────────────────────────────────────

@router.get("/reservas", response_model=List[ReservaResponse])
async def listar_reservas(
    produto_id: Optional[uuid.UUID] = Query(None),
    deposito_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query("ATIVA", description="ATIVA | CONSUMIDA | CANCELADA | (vazio=todos)"),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).listar_reservas(produto_id, deposito_id, status or None)


@router.post("/reservas", response_model=ReservaResponse, status_code=201,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def criar_reserva(
    data: ReservaCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    usuario: Usuario = Depends(get_current_user),
):
    svc = _svc(session, tenant)
    result = await svc.criar_reserva(data, usuario.id)
    await session.commit()
    return result


@router.patch("/reservas/{reserva_id}/cancelar", response_model=ReservaResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def cancelar_reserva(
    reserva_id: uuid.UUID,
    data: ReservaCancelarRequest = ReservaCancelarRequest(),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.cancelar_reserva(reserva_id)
    await session.commit()
    return result


@router.patch("/reservas/{reserva_id}/consumir", response_model=ReservaResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def consumir_reserva(
    reserva_id: uuid.UUID,
    data: ReservaConsumirRequest = ReservaConsumirRequest(),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    result = await svc.consumir_reserva(reserva_id, data)
    await session.commit()
    return result
