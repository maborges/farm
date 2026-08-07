from core.dependencies import require_tenant_permission
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import uuid
from datetime import datetime, date, timezone
from loguru import logger

from core.dependencies import get_session, get_current_tenant, get_current_user_claims, require_module
from core.exceptions import BusinessRuleError, TenantViolationError, EntityNotFoundError
from core.models.tenant import Tenant
from operacional.models.compras import (
    PedidoCompra, ItemPedidoCompra, CotacaoFornecedor,
    RecebimentoParcial, ItemRecebimento, DevolucaoFornecedor, ItemDevolucao,
    SolicitacaoCompra, CotacaoCompra
)
from operacional.schemas.compras import (
    RecebimentoCreate, RecebimentoResponse, EstornoRecebimentoRequest,
    DevolucaoCreate, DevolucaoStatusUpdate, DevolucaoResponse,
    SolicitacaoCompraCreate, SolicitacaoCompraResponse, SolicitacaoCompraStatusUpdate,
    SolicitacaoItemCreate,
    SolicitacaoItemUpdate,
    CotacaoSolicitacaoCreate, CotacaoSolicitacaoResponse, CotacaoItemUpdate, CotacaoUpdate,
    AlocacaoRequest,
    PedidoCompraResponse, PedidoCompraStatusUpdate, CondicoesPagamentoUpdate, AdiantamentoUpdate,
    PrecoHistoricoResponse, MelhorFornecedorResponse, PrecoIdealResponse,
    FornecedorConsistenciaResponse, EconomiaAnalyticsResponse,
    EconomiaSerieTemporalResponse, EconomiaCategoriaResponse,
    EconomiaUsuarioResponse, EconomiaFornecedorResponse
)
from core.cadastros.models import ProdutoCatalogo as Produto
from operacional.services.estoque_service import EstoqueService
from operacional.services.estoque_ledger import registrar_ledger_estoque
from operacional.services.fornecedores_service import salvar_fornecedor_legado
from operacional.schemas.estoque import EntradaEstoqueRequest, LoteCreate
from operacional.models.estoque import LoteEstoque, SaldoEstoque
from pydantic import BaseModel, Field
from operacional.services.compras_service import ComprasService

router = APIRouter(prefix="/compras", tags=["Operacional — Compras"], dependencies=[Depends(require_module("O3_COMPRAS"))])

# --- SCHEMAS ---
class FornecedorCreate(BaseModel):
    nome_fantasia: str
    cnpj_cpf: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    condicoes_pagamento: Optional[str] = None
    prazo_entrega_dias: Optional[int] = None
    avaliacao: Optional[float] = None

class FornecedorResponse(BaseModel):
    id: uuid.UUID
    pessoa_id: uuid.UUID
    nome_fantasia: str
    cnpj_cpf: Optional[str]
    email: Optional[str]
    telefone: Optional[str]
    condicoes_pagamento: Optional[str]
    prazo_entrega_dias: Optional[int]
    avaliacao: Optional[float]
    class Config: from_attributes = True

# --- ENDPOINTS ---

@router.get("/fornecedores", response_model=List[FornecedorResponse])
async def list_fornecedores(
    q: Optional[str] = None,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ComprasService(session, tenant.id)
    resultado = await svc.listar_fornecedores(q)
    await session.commit()
    return resultado


@router.post("/fornecedores", response_model=FornecedorResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def create_fornecedor(
    data: FornecedorCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    forn, _created = await salvar_fornecedor_legado(
        session,
        tenant.id,
        **data.model_dump(),
    )
    await session.commit()
    svc = ComprasService(session, tenant.id)
    return await svc._montar_fornecedor_response(forn)


@router.get("/fornecedores/consistencia", response_model=List[FornecedorConsistenciaResponse])
async def get_consistencia_fornecedores(
    item_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Retorna a análise de consistência de preços por fornecedor para um item."""
    svc = ComprasService(session, tenant.id)
    return await svc.obter_consistencia_fornecedores(item_id)


@router.get("/fornecedores/{fornecedor_id}", response_model=FornecedorResponse)
async def get_fornecedor(
    fornecedor_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ComprasService(session, tenant.id)
    forn = await svc.obter_fornecedor(fornecedor_id)
    if not forn:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    return forn


@router.put("/fornecedores/{fornecedor_id}", response_model=FornecedorResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def update_fornecedor(
    fornecedor_id: uuid.UUID,
    data: FornecedorCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ComprasService(session, tenant.id)
    forn = await svc.obter_fornecedor_orm(fornecedor_id)
    if not forn:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    forn, _created = await salvar_fornecedor_legado(
        session,
        tenant.id,
        fornecedor=forn,
        **data.model_dump(),
    )

    session.add(forn)
    await session.commit()
    return await svc._montar_fornecedor_response(forn)


@router.get("/pedidos", response_model=List[PedidoCompraResponse])
async def list_pedidos(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ComprasService(session, tenant.id)
    return await svc.listar_pedidos()


@router.get("/pedidos/{pedido_id}", response_model=PedidoCompraResponse)
async def get_pedido(
    pedido_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(PedidoCompra).where(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant.id)
    ped = (await session.execute(stmt)).scalar_one_or_none()
    if not ped:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    svc = ComprasService(session, tenant.id)
    return await svc._enriquecer_pedido(ped)


@router.patch("/pedidos/{pedido_id}/status", response_model=PedidoCompraResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def update_pedido_status(
    pedido_id: uuid.UUID,
    data: PedidoCompraStatusUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ComprasService(session, tenant.id)
    pedido = await svc.atualizar_status_pedido(pedido_id, data.status)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    await session.commit()
    await session.refresh(pedido)
    return await svc._enriquecer_pedido(pedido)


@router.post("/pedidos/{pedido_id}/enviar", response_model=PedidoCompraResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def enviar_pedido_fornecedor(
    pedido_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ComprasService(session, tenant.id)
    pedido = await svc.enviar_pedido_fornecedor(pedido_id)
    await session.commit()
    return await svc._enriquecer_pedido(pedido)


@router.patch("/pedidos/{pedido_id}/condicoes-pagamento", response_model=PedidoCompraResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def update_condicoes_pagamento(
    pedido_id: uuid.UUID,
    data: CondicoesPagamentoUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ComprasService(session, tenant.id)
    pedido = await svc.atualizar_condicoes_pagamento(pedido_id, data.condicoes_pagamento)
    await session.commit()
    await session.refresh(pedido)
    return pedido


@router.patch("/pedidos/{pedido_id}/adiantamento", response_model=PedidoCompraResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def update_adiantamento(
    pedido_id: uuid.UUID,
    data: AdiantamentoUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ComprasService(session, tenant.id)
    pedido = await svc.atualizar_adiantamento(pedido_id, data.valor_adiantamento)
    await session.commit()
    await session.refresh(pedido)
    return pedido


@router.get("/pedidos/{pedido_id}/pdf")
async def get_pedido_pdf(
    pedido_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Gera e retorna o PDF operacional do pedido de compra."""
    svc = ComprasService(session, tenant.id)
    pdf_content = await svc.gerar_pdf_pedido(pedido_id)

    if not pdf_content:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")

    pedido = await session.get(PedidoCompra, pedido_id)
    nome_arquivo = pedido.numero if pedido and pedido.numero else str(pedido_id)

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={nome_arquivo}.pdf"
        }
    )


@router.patch("/pedidos/{pedido_id}/receber", status_code=200,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def receber_pedido(
    pedido_id: uuid.UUID,
    data: RecebimentoCreate | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    svc = ComprasService(session, tenant.id)
    try:
        pedido = await svc.receber_pedido(pedido_id, data=data, recebido_por_id=claims.get("sub"))
    except BusinessRuleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    await session.commit()
    return {"message": "Pedido marcado como recebido", "pedido_id": str(pedido.id), "status": pedido.status}


@router.post("/pedidos/{pedido_id}/estornar-recebimento", response_model=PedidoCompraResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def estornar_recebimento_pedido(
    pedido_id: uuid.UUID,
    data: EstornoRecebimentoRequest,
    tenant: Tenant = Depends(get_current_tenant),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Desfaz um recebimento feito por engano — só permitido enquanto o
    estoque recebido ainda não foi consumido."""
    svc = ComprasService(session, tenant.id)
    try:
        pedido = await svc.estornar_recebimento(pedido_id, motivo=data.motivo, usuario_id=claims.get("sub"))
    except BusinessRuleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await session.commit()
    await session.refresh(pedido)
    return await svc._enriquecer_pedido(pedido)


async def atualizar_status_devolucao(
    dev_id: uuid.UUID,
    data: DevolucaoStatusUpdate,
    tenant: Tenant,
    session: AsyncSession,

    _permission: None = Depends(require_tenant_permission("operacional:compras:list"))):
    svc = ComprasService(session, tenant.id)
    if data.status == "CONCLUIDA":
        devolucao = await svc.concluir_devolucao(dev_id)
        if not devolucao:
            raise BusinessRuleError("Devolução não encontrada")
        return devolucao

    devolucao = await session.get(DevolucaoFornecedor, dev_id)
    if not devolucao or devolucao.tenant_id != tenant.id:
        raise BusinessRuleError("Devolução não encontrada")

    devolucao.status = data.status
    session.add(devolucao)
    await session.flush()
    return devolucao


@router.get("/historico-precos")
async def historico_precos(
    limit: int = 100,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    from core.cadastros.produtos.models import Produto
    stmt = (
        select(
            ItemPedidoCompra.produto_id,
            Produto.nome.label("nome_produto"),
            func.coalesce(ItemPedidoCompra.preco_real_unitario, ItemPedidoCompra.preco_estimado_unitario).label("preco_unitario"),
            ItemPedidoCompra.quantidade_recebida,
            PedidoCompra.updated_at.label("data_recebimento"),
            PedidoCompra.id.label("pedido_id"),
            PedidoCompra.fornecedor_nome.label("nome_fornecedor"),
        )
        .join(PedidoCompra, ItemPedidoCompra.pedido_id == PedidoCompra.id)
        .join(Produto, ItemPedidoCompra.produto_id == Produto.id)
        .where(
            PedidoCompra.tenant_id == tenant.id,
            PedidoCompra.status == "RECEBIDO",
        )
        .order_by(PedidoCompra.updated_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        {
            "produto_id": str(row.produto_id),
            "nome_produto": row.nome_produto,
            "preco_real_unitario": row.preco_unitario,
            "quantidade_recebida": row.quantidade_recebida,
            "data_recebimento": row.data_recebimento.isoformat() if row.data_recebimento else None,
            "pedido_id": str(row.pedido_id),
            "nome_fornecedor": row.nome_fornecedor,
        }
        for row in rows
    ]


@router.get("/precos/historico", response_model=PrecoHistoricoResponse)
async def get_precos_historico_item(
    item_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Retorna o histórico detalhado de preços para um item específico."""
    svc = ComprasService(session, tenant.id)
    return await svc.get_historico_precos(item_id)


@router.get("/precos/melhor-fornecedor", response_model=Optional[MelhorFornecedorResponse])
async def get_melhor_fornecedor_item(
    item_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Retorna a recomendação do melhor fornecedor para um item."""
    svc = ComprasService(session, tenant.id)
    return await svc.obter_melhor_fornecedor(item_id)


@router.get("/precos/preco-ideal", response_model=Optional[PrecoIdealResponse])
async def get_preco_ideal_item(
    item_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Retorna a sugestão de faixa de preço ideal para um item."""
    svc = ComprasService(session, tenant.id)
    return await svc.obter_preco_ideal(item_id)



# --- SOLICITAÇÕES DE COMPRA (Step 147-150) ---

@router.post("/solicitacoes", response_model=SolicitacaoCompraResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def create_solicitacao_compra(
    data: SolicitacaoCompraCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    claims: dict = Depends(get_current_user_claims),
):
    svc = ComprasService(session, tenant.id)
    solicitacao = await svc.criar_solicitacao(data, solicitante_id=claims.get("sub"))
    await session.commit()
    await session.refresh(solicitacao)
    # refresh() expira a relação `itens` (lazy="noload"); repopular para a resposta.
    solicitacao.itens = await svc._enriquecer_itens_solicitacao(solicitacao.id)
    return solicitacao


@router.get("/solicitacoes", response_model=List[SolicitacaoCompraResponse])
async def list_solicitacoes_compra(
    status: Optional[str] = None,
    item_id: Optional[uuid.UUID] = None,
    deposito_id: Optional[uuid.UUID] = None,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ComprasService(session, tenant.id)
    return await svc.listar_solicitacoes(status=status, produto_id=item_id, deposito_id=deposito_id)


@router.patch("/solicitacoes/{id}/status", response_model=SolicitacaoCompraResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def update_solicitacao_status(
    id: uuid.UUID,
    data: SolicitacaoCompraStatusUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ComprasService(session, tenant.id)
    solicitacao = await svc.atualizar_status(id, data.status)
    if not solicitacao: raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    await session.commit()
    await session.refresh(solicitacao)
    solicitacao.itens = await svc._enriquecer_itens_solicitacao(solicitacao.id)
    return solicitacao


@router.post("/solicitacoes/{id}/itens", response_model=SolicitacaoCompraResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def adicionar_item_solicitacao(
    id: uuid.UUID,
    data: SolicitacaoItemCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Adiciona um item a uma solicitação já existente."""
    svc = ComprasService(session, tenant.id)
    try:
        solicitacao = await svc.adicionar_item_solicitacao(id, data)
        await session.commit()
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await session.refresh(solicitacao)
    solicitacao.itens = await svc._enriquecer_itens_solicitacao(solicitacao.id)
    return solicitacao


@router.patch("/solicitacoes/{id}/itens/{item_id}", response_model=SolicitacaoCompraResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def atualizar_item_solicitacao(
    id: uuid.UUID,
    item_id: uuid.UUID,
    data: SolicitacaoItemUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Atualiza a quantidade de um item de uma solicitação já existente."""
    svc = ComprasService(session, tenant.id)
    try:
        solicitacao = await svc.atualizar_item_solicitacao(id, item_id, data)
        await session.commit()
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await session.refresh(solicitacao)
    solicitacao.itens = await svc._enriquecer_itens_solicitacao(solicitacao.id)
    return solicitacao


@router.delete("/solicitacoes/{id}/itens/{item_id}", response_model=SolicitacaoCompraResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def remover_item_solicitacao(
    id: uuid.UUID,
    item_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Remove um item de uma solicitação já existente."""
    svc = ComprasService(session, tenant.id)
    try:
        solicitacao = await svc.remover_item_solicitacao(id, item_id)
        await session.commit()
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await session.refresh(solicitacao)
    solicitacao.itens = await svc._enriquecer_itens_solicitacao(solicitacao.id)
    return solicitacao


@router.post("/solicitacoes/{id}/cotacoes", response_model=CotacaoSolicitacaoResponse, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def create_cotacao_solicitacao(
    id: uuid.UUID,
    data: CotacaoSolicitacaoCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ComprasService(session, tenant.id)
    try:
        cotacao = await svc.criar_cotacao(id, data)
        if not cotacao: raise HTTPException(status_code=404, detail="Solicitação não encontrada")
        await session.commit()
        await session.refresh(cotacao)
        cotacao.itens = await svc._enriquecer_itens_cotacao(cotacao.id)
        return cotacao
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/solicitacoes/{id}/alocar", response_model=SolicitacaoCompraResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def alocar_itens_solicitacao(
    id: uuid.UUID,
    data: AlocacaoRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Aloca quantidades de itens da solicitação a cotações/fornecedores
    específicos — pode ser chamado várias vezes até completar os itens."""
    svc = ComprasService(session, tenant.id)
    try:
        await svc.alocar_itens(id, data.itens)
        await session.commit()
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=str(e))

    solicitacao = await session.get(SolicitacaoCompra, id)
    solicitacao.itens = await svc._enriquecer_itens_solicitacao(id)
    return solicitacao


@router.post("/solicitacoes/{id}/gerar-pedidos", response_model=List[PedidoCompraResponse],
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def gerar_pedidos_solicitacao(
    id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Converte as alocações pendentes em pedidos de compra — 1 pedido por
    fornecedor com itens alocados; pode gerar vários pedidos de uma vez."""
    svc = ComprasService(session, tenant.id)
    try:
        pedidos = await svc.gerar_pedidos_de_alocacoes(id)
        await session.commit()
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=str(e))

    resultado = []
    for pedido in pedidos:
        await session.refresh(pedido)
        resultado.append(await svc._enriquecer_pedido(pedido))
    return resultado


@router.post("/solicitacoes/{id}/encerrar", response_model=SolicitacaoCompraResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def encerrar_solicitacao_compra(
    id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    claims: dict = Depends(get_current_user_claims),
):
    """Encerra a solicitação — só quem a criou pode fazer isso, mesmo com
    itens ainda pendentes/parciais (ele decide se o parcial já atende)."""
    svc = ComprasService(session, tenant.id)
    try:
        solicitacao = await svc.encerrar_solicitacao(id, usuario_id=claims.get("sub"))
        await session.commit()
    except TenantViolationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return solicitacao


@router.get("/solicitacoes/{id}/cotacoes", response_model=List[CotacaoSolicitacaoResponse])
async def list_cotacoes_solicitacao(
    id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ComprasService(session, tenant.id)
    return await svc.listar_cotacoes(id)


@router.patch("/solicitacoes/{id}/cotacoes/{cotacao_id}", response_model=CotacaoSolicitacaoResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def atualizar_cotacao(
    id: uuid.UUID,
    cotacao_id: uuid.UUID,
    data: CotacaoUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Corrige condições de pagamento / prazo de entrega de uma cotação —
    só permitido enquanto RECEBIDA."""
    svc = ComprasService(session, tenant.id)
    try:
        cotacao = await svc.atualizar_cotacao(id, cotacao_id, data.condicoes_pagamento, data.prazo_entrega_dias)
        await session.commit()
        return cotacao
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.patch("/solicitacoes/{id}/cotacoes/{cotacao_id}/itens/{item_id}", response_model=CotacaoSolicitacaoResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def atualizar_item_cotacao(
    id: uuid.UUID,
    cotacao_id: uuid.UUID,
    item_id: uuid.UUID,
    data: CotacaoItemUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Corrige o valor unitário de um item de uma cotação (ex: erro de
    digitação) — só permitido enquanto a cotação está RECEBIDA."""
    svc = ComprasService(session, tenant.id)
    try:
        cotacao = await svc.atualizar_item_cotacao(id, cotacao_id, item_id, data.valor_unitario, data.quantidade_atendida)
        await session.commit()
        return cotacao
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/analytics/economia", response_model=EconomiaAnalyticsResponse)
async def get_economia_analytics(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Retorna dados analíticos sobre economia (savings) gerada pelo sistema (Step 163)."""
    svc = ComprasService(session, tenant.id)
    return await svc.obter_economia_analytics()


@router.get("/analytics/economia/serie-temporal", response_model=EconomiaSerieTemporalResponse)
async def get_serie_temporal_economia(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Retorna a evolução mensal da economia gerada (Step 164)."""
    svc = ComprasService(session, tenant.id)
    items = await svc.obter_serie_temporal_economia()
    return {"items": items}

@router.get("/analytics/economia/por-categoria", response_model=EconomiaCategoriaResponse)
async def get_economia_por_categoria(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Retorna o breakdown de economia por categoria (Step 165)."""
    svc = ComprasService(session, tenant.id)
    items = await svc.obter_economia_por_categoria()
    return {"items": items}


@router.get("/analytics/economia/por-fornecedor", response_model=EconomiaFornecedorResponse)
async def get_economia_por_fornecedor(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Retorna o ranking de economia gerada por fornecedor (Step 167)."""
    svc = ComprasService(session, tenant.id)
    items = await svc.obter_economia_por_fornecedor()
    return {"items": items}


@router.get("/analytics/economia/por-usuario", response_model=EconomiaUsuarioResponse)
async def get_economia_por_usuario(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Retorna o ranking de economia gerada por comprador (Step 166)."""
    svc = ComprasService(session, tenant.id)
    items = await svc.obter_economia_por_usuario()
    return {"items": items}


@router.get("/solicitacoes/{id}/cotacoes/export.pdf")
async def get_comparativo_cotacoes_pdf(
    id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Gera e retorna o PDF comparativo de cotações para uma solicitação."""
    svc = ComprasService(session, tenant.id)
    pdf_content = await svc.gerar_pdf_comparativo(id)
    
    if not pdf_content:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada ou sem cotações.")
        
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=comparativo_solicitacao_{id}.pdf"
        }
    )


@router.patch("/solicitacoes/{solicitacao_id}/cotacoes/{cotacao_id}/aprovar", response_model=PedidoCompraResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))]
)
async def aprovar_cotacao_solicitacao(
    solicitacao_id: uuid.UUID,
    cotacao_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Aprova uma cotação e gera o pedido de compra correspondente."""
    svc = ComprasService(session, tenant.id)
    try:
        pedido = await svc.aprovar_cotacao(solicitacao_id, cotacao_id)
        if not pedido:
            raise HTTPException(status_code=404, detail="Cotação ou solicitação não encontrada")
        
        await session.commit()
        await session.refresh(pedido)
        return await svc._enriquecer_pedido(pedido)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=str(e))
