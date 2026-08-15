from __future__ import annotations

from datetime import date

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.receituario_agronomico.models import ReceituarioAgronomico, StatusReceituario


async def marcar_receituarios_vencidos(session: AsyncSession) -> int:
    """Job automático: marca como VENCIDO todo receituário emitido cuja validade passou.

    Critério: status == EMITIDO AND data_validade < hoje.
    Retorna o número de receituários marcados.
    """
    hoje = date.today()

    result = await session.execute(
        select(ReceituarioAgronomico).where(
            ReceituarioAgronomico.status == StatusReceituario.EMITIDO.value,
            ReceituarioAgronomico.data_validade < hoje,
        )
    )
    receituarios = result.scalars().all()

    count = 0
    for receituario in receituarios:
        receituario.status = StatusReceituario.VENCIDO.value
        count += 1

    if count:
        await session.commit()
        logger.info(f"marcar_receituarios_vencidos: {count} receituário(s) marcado(s) como VENCIDO.")

    return count
