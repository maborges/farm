import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from core.dependencies import get_session

get_db = get_session
from certificacoes_esg.models import PassaporteRastreabilidade, StatusPassaporte
from certificacoes_esg.schemas import PassaportePublicoResponse, IntegridadeResponse
from certificacoes_esg.service import CertificacoesESGPublicService

router = APIRouter()

@router.get(
    "/passaportes/{public_token}",
    response_model=PassaportePublicoResponse,
    summary="Busca dados públicos de um Passaporte de Rastreabilidade",
)
async def get_passaporte_publico(
    public_token: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> Any:
    """
    Retorna os dados públicos de um passaporte publicado.
    Acesso não autenticado (anônimo).
    """
    # Buscar passaporte
    stmt = (
        select(PassaporteRastreabilidade)
        .options(
            selectinload(PassaporteRastreabilidade.eventos),
            selectinload(PassaporteRastreabilidade.evidencias),
        )
        .where(PassaporteRastreabilidade.public_token == public_token)
    )
    result = await db.execute(stmt)
    passaporte = result.scalars().first()

    if not passaporte:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passaporte não encontrado ou token inválido.",
        )

    # Validar regras de exposição
    if passaporte.status != StatusPassaporte.PUBLICADO:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passaporte não encontrado ou token inválido.",
        )
    
    if not passaporte.publico:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passaporte não encontrado ou token inválido.",
        )

    if not passaporte.snapshot_hash:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passaporte não encontrado ou token inválido.",
        )

    # O retorno mapeará para PassaportePublicoResponse que removerá o tenant_id
    return passaporte


@router.get(
    "/passaportes/{public_token}/verify",
    response_model=IntegridadeResponse,
    summary="Verifica a integridade criptográfica de um Passaporte de Rastreabilidade",
)
async def verify_passaporte_integridade(
    public_token: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> Any:
    """
    Endpoint público para validar se o snapshot_json do passaporte
    corresponde exatamente ao snapshot_hash armazenado (SHA-256).
    """
    service = CertificacoesESGPublicService(session=db)
    result = await service.verificar_integridade_passaporte(public_token)
    return result
