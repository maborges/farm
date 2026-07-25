import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_service import BaseService
from core.exceptions import EntityNotFoundError
from .models import TipoServico
from .schemas import TipoServicoCreate, TipoServicoUpdate


class TipoServicoService(BaseService[TipoServico]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(TipoServico, session, tenant_id)

    async def listar(
        self,
        q: Optional[str] = None,
        ativo: Optional[bool] = None,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[TipoServico]:
        stmt = select(TipoServico).where(TipoServico.tenant_id == self.tenant_id)
        if q:
            stmt = stmt.where(TipoServico.nome.ilike(f"%{q}%"))
        if ativo is not None:
            stmt = stmt.where(TipoServico.ativo == ativo)
        stmt = stmt.order_by(TipoServico.nome.asc())
        if skip:
            stmt = stmt.offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar(self, data: TipoServicoCreate) -> TipoServico:
        obj = TipoServico(tenant_id=self.tenant_id, **data.model_dump())
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def obter(self, tipo_servico_id: uuid.UUID) -> TipoServico:
        stmt = select(TipoServico).where(
            TipoServico.id == tipo_servico_id, TipoServico.tenant_id == self.tenant_id
        )
        obj = (await self.session.execute(stmt)).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Tipo de serviço não encontrado")
        return obj

    async def atualizar(self, tipo_servico_id: uuid.UUID, data: TipoServicoUpdate) -> TipoServico:
        obj = await self.obter(tipo_servico_id)
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(obj, k, v)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def desativar(self, tipo_servico_id: uuid.UUID) -> None:
        obj = await self.obter(tipo_servico_id)
        obj.ativo = False
