from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_service import BaseService
from imoveis.models.irrigacao import SistemaIrrigacao


class IrrigacaoService(BaseService[SistemaIrrigacao]):
    """CRUD de sistemas de irrigação (OPERATIONS-GAP-01 §21.34)."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(SistemaIrrigacao, session, tenant_id)

    async def listar_por_imovel(self, imovel_id: uuid.UUID | None = None) -> list[SistemaIrrigacao]:
        stmt = select(SistemaIrrigacao).where(SistemaIrrigacao.tenant_id == self.tenant_id)
        if imovel_id:
            stmt = stmt.where(SistemaIrrigacao.imovel_id == imovel_id)
        stmt = stmt.order_by(SistemaIrrigacao.nome)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
