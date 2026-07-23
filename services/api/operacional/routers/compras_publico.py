"""Rotas públicas (sem JWT/tenant) para o fornecedor confirmar ou recusar
um pedido de compra recebido por e-mail, via token + senha de confirmação."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session
from operacional.schemas.compras import ConfirmacaoAceiteRequest, PedidoConfirmacaoPublicaResponse
from operacional.services.compras_service import obter_confirmacao_publica, responder_confirmacao_publica

router = APIRouter(prefix="/compras-publico", tags=["Operacional — Compras (Público)"])


@router.get("/pedidos/confirmar/{token}", response_model=PedidoConfirmacaoPublicaResponse)
async def obter_confirmacao(token: str, session: AsyncSession = Depends(get_session)):
    return await obter_confirmacao_publica(session, token)


@router.post("/pedidos/confirmar/{token}", response_model=PedidoConfirmacaoPublicaResponse)
async def responder_confirmacao(
    token: str,
    data: ConfirmacaoAceiteRequest,
    session: AsyncSession = Depends(get_session),
):
    return await responder_confirmacao_publica(session, token, data.senha, data.aceito)
