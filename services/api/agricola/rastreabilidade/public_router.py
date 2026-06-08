from fastapi import APIRouter, HTTPException, Response

from core.database import async_session_maker
from agricola.rastreabilidade.service import RastreabilidadeService, LoteComercialService

router = APIRouter(prefix="/public", tags=["Rastreabilidade Pública"])


@router.get("/track/{codigo_lote}")
async def track_lote_publico(codigo_lote: str):
    """Endpoint público para rastreamento de lote via QR code. Sem autenticação."""
    async with async_session_maker() as session:
        lote = await RastreabilidadeService.buscar_por_codigo(session, codigo_lote)

    if not lote:
        raise HTTPException(status_code=404, detail="Lote não encontrado.")

    return {
        "codigo_lote": lote.codigo_lote,
        "produto": lote.produto,
        "variedade": lote.variedade,
        "quantidade_total": float(lote.quantidade_total or 0),
        "unidade": lote.unidade,
        "status": lote.status,
        "certificacoes": lote.certificacoes or [],
        "data_geracao": lote.data_geracao.isoformat() if lote.data_geracao else None,
        "qr_code_url": lote.qr_code_url,
    }


@router.get("/rastreabilidade/{token}")
async def obter_rastreabilidade_publica(token: str, response: Response):
    """Endpoint público que retorna o snapshot imutável do passaporte do lote."""
    response.headers["X-Robots-Tag"] = "noindex, nofollow"

    async with async_session_maker() as session:
        lote = await LoteComercialService.buscar_por_token(session, token)

    if not lote or lote.status != "ATIVO" or not lote.snapshot_json:
        raise HTTPException(status_code=404, detail="Lote comercial não encontrado ou não publicado.")

    return lote.snapshot_json
