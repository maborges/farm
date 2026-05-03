from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid
from datetime import datetime, date, timezone
from loguru import logger

from core.dependencies import get_session, get_current_tenant, get_current_user_claims, require_module
from core.exceptions import BusinessRuleError
from core.models.tenant import Tenant
from operacional.models.compras import (
    Fornecedor, PedidoCompra, ItemPedidoCompra, CotacaoFornecedor,
    RecebimentoParcial, ItemRecebimento, DevolucaoFornecedor, ItemDevolucao,
    SolicitacaoCompra, CotacaoCompra
)
from operacional.schemas.compras import (
    RecebimentoCreate, RecebimentoResponse,
    DevolucaoCreate, DevolucaoStatusUpdate, DevolucaoResponse,
    SolicitacaoCompraCreate, SolicitacaoCompraResponse, SolicitacaoCompraStatusUpdate,
    CotacaoSolicitacaoCreate, CotacaoSolicitacaoResponse,
    PedidoCompraResponse, PedidoCompraStatusUpdate,
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
    pessoa_id: Optional[uuid.UUID] = None
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
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Fornecedor).where(Fornecedor.tenant_id == tenant.id)
    res = await session.execute(stmt)
    return res.scalars().all()


@router.post("/fornecedores", response_model=FornecedorResponse, status_code=status.HTTP_201_CREATED)
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
    await session.refresh(forn)
    return forn


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
    stmt = select(Fornecedor).where(Fornecedor.id == fornecedor_id, Fornecedor.tenant_id == tenant.id)
    forn = (await session.execute(stmt)).scalar_one_or_none()
    if not forn:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    return forn


@router.put("/fornecedores/{fornecedor_id}", response_model=FornecedorResponse)
async def update_fornecedor(
    fornecedor_id: uuid.UUID,
    data: FornecedorCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Fornecedor).where(Fornecedor.id == fornecedor_id, Fornecedor.tenant_id == tenant.id)
    forn = (await session.execute(stmt)).scalar_one_or_none()
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
    await session.refresh(forn)
    return forn


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
    from core.cadastros.produtos.models import Produto
    from operacional.models.estoque import Deposito
    
    stmt = (
        select(PedidoCompra, Produto.nome.label("item_nome"), Deposito.nome.label("deposito_nome"))
        .join(Produto, PedidoCompra.item_id == Produto.id)
        .join(Deposito, PedidoCompra.deposito_id == Deposito.id)
        .where(PedidoCompra.id == pedido_id, PedidoCompra.tenant_id == tenant.id)
    )
    res = (await session.execute(stmt)).first()
    if not res:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    ped, i_nome, d_nome = res
    ped.item_nome = i_nome
    ped.deposito_nome = d_nome
    return ped


@router.patch("/pedidos/{pedido_id}/status", response_model=PedidoCompraResponse)
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
        
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=pedido_{pedido_id}.pdf"
        }
    )


@router.patch("/pedidos/{pedido_id}/receber", status_code=200)
async def receber_pedido(
    pedido_id: uuid.UUID,
    # Reaproveitando o esquema simplificado se necessário
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    # Endpoint simplificado para o Step 150/151
    pedido = await session.get(PedidoCompra, pedido_id)
    if not pedido or pedido.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    pedido.status = "RECEBIDO"
    await session.commit()
    return {"message": "Pedido marcado como recebido"}


@router.get("/historico-precos")
async def historico_precos(
    limit: int = 100,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    from core.cadastros.produtos.models import Produto
    stmt = (
        select(
            PedidoCompra.item_id,
            Produto.nome.label("nome_produto"),
            PedidoCompra.valor_unitario,
            PedidoCompra.quantidade.label("quantidade_recebida"),
            PedidoCompra.updated_at.label("data_recebimento"),
            PedidoCompra.id.label("pedido_id"),
            PedidoCompra.fornecedor_nome.label("nome_fornecedor"),
        )
        .join(Produto, PedidoCompra.item_id == Produto.id)
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
            "produto_id": str(row.item_id),
            "nome_produto": row.nome_produto,
            "preco_real_unitario": row.valor_unitario,
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

@router.post("/solicitacoes", response_model=SolicitacaoCompraResponse, status_code=status.HTTP_201_CREATED)
async def create_solicitacao_compra(
    data: SolicitacaoCompraCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ComprasService(session, tenant.id)
    solicitacao = await svc.criar_solicitacao(data)
    await session.commit()
    await session.refresh(solicitacao)
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


@router.patch("/solicitacoes/{id}/status", response_model=SolicitacaoCompraResponse)
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
    return solicitacao


@router.post("/solicitacoes/{id}/cotacoes", response_model=CotacaoSolicitacaoResponse, status_code=status.HTTP_201_CREATED)
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
        return cotacao
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/solicitacoes/{id}/cotacoes", response_model=List[CotacaoSolicitacaoResponse])
async def list_cotacoes_solicitacao(
    id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    svc = ComprasService(session, tenant.id)
    return await svc.listar_cotacoes(id)


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


@router.patch("/solicitacoes/{solicitacao_id}/cotacoes/{cotacao_id}/aprovar", response_model=PedidoCompraResponse)
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
        
        # Enriquecer para o response
        from core.cadastros.produtos.models import Produto
        from operacional.models.estoque import Deposito
        
        p = await session.get(Produto, pedido.item_id)
        d = await session.get(Deposito, pedido.deposito_id)
        pedido.item_nome = p.nome if p else None
        pedido.deposito_nome = d.nome if d else None
        
        return pedido
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=str(e))
