from __future__ import annotations

from datetime import date

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.logistica_reversa_embalagens.models import DevolucaoEmbalagem, StatusDevolucaoEmbalagem


async def marcar_devolucoes_vencidas(session: AsyncSession) -> int:
    """Job automático: marca como VENCIDO toda devolução de embalagem cujo prazo passou.

    Critério: status == PENDENTE AND prazo_limite < hoje.
    Retorna o número de devoluções marcadas.
    """
    hoje = date.today()

    result = await session.execute(
        select(DevolucaoEmbalagem).where(
            DevolucaoEmbalagem.status == StatusDevolucaoEmbalagem.PENDENTE.value,
            DevolucaoEmbalagem.prazo_limite < hoje,
        )
    )
    devolucoes = result.scalars().all()

    count = 0
    for devolucao in devolucoes:
        devolucao.status = StatusDevolucaoEmbalagem.VENCIDO.value
        count += 1

    if count:
        await session.commit()
        logger.info(f"marcar_devolucoes_vencidas: {count} devolução(ões) marcada(s) como VENCIDO.")

    return count
