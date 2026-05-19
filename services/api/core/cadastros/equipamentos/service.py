import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_service import BaseService
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.models.unidade_produtiva import UnidadeProdutiva
from .alocacao_service import criar_equipamento_alocacao
from .models import Equipamento, EquipamentoAlocacao
from .schemas import EquipamentoCreate, EquipamentoUpdate


class EquipamentoService(BaseService[Equipamento]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(Equipamento, session, tenant_id)

    async def _validar_unidade_produtiva(self, unidade_produtiva_id: uuid.UUID | None) -> None:
        if unidade_produtiva_id is None:
            return
        unidade = (
            await self.session.execute(
                select(UnidadeProdutiva.id).where(
                    UnidadeProdutiva.id == unidade_produtiva_id,
                    UnidadeProdutiva.tenant_id == self.tenant_id,
                    UnidadeProdutiva.ativo == True,
                )
            )
        ).scalar_one_or_none()
        if unidade is None:
            raise BusinessRuleError("Unidade produtiva do equipamento não localizada ou inacessível.")

    async def listar(
        self,
        tipo: Optional[str] = None,
        status: Optional[str] = None,
        unidade_produtiva_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[Equipamento]:
        stmt = select(Equipamento).where(Equipamento.tenant_id == self.tenant_id)
        if tipo:
            stmt = stmt.where(Equipamento.tipo == tipo)
        if status:
            stmt = stmt.where(Equipamento.status == status)
        if unidade_produtiva_id:
            agora = datetime.now(timezone.utc)
            allocated_ids = (
                select(EquipamentoAlocacao.equipamento_id)
                .where(
                    EquipamentoAlocacao.tenant_id == self.tenant_id,
                    EquipamentoAlocacao.unidade_produtiva_id == unidade_produtiva_id,
                    EquipamentoAlocacao.status == "ATIVA",
                    EquipamentoAlocacao.data_inicio <= agora,
                    (EquipamentoAlocacao.data_fim.is_(None) | (EquipamentoAlocacao.data_fim >= agora)),
                )
            )
            stmt = stmt.where((Equipamento.unidade_produtiva_id == unidade_produtiva_id) | (Equipamento.id.in_(allocated_ids)))
        stmt = stmt.order_by(Equipamento.nome.asc())
        if skip:
            stmt = stmt.offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar(self, data: EquipamentoCreate) -> Equipamento:
        await self._validar_unidade_produtiva(data.unidade_produtiva_id)
        eq = Equipamento(tenant_id=self.tenant_id, **data.model_dump())
        self.session.add(eq)
        await self.session.flush()
        if eq.unidade_produtiva_id:
            await criar_equipamento_alocacao(
                self.session,
                tenant_id=self.tenant_id,
                equipamento_id=eq.id,
                unidade_produtiva_id=eq.unidade_produtiva_id,
                principal=True,
                observacao="Alocação inicial criada a partir do vínculo legado do equipamento.",
            )
        await self.session.refresh(eq)
        return eq

    async def obter(self, eq_id: uuid.UUID) -> Equipamento:
        stmt = select(Equipamento).where(Equipamento.id == eq_id, Equipamento.tenant_id == self.tenant_id)
        obj = (await self.session.execute(stmt)).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Equipamento não encontrado")
        return obj

    async def atualizar(self, eq_id: uuid.UUID, data: EquipamentoUpdate) -> Equipamento:
        obj = await self.obter(eq_id)
        updates = data.model_dump(exclude_none=True)
        if "unidade_produtiva_id" in updates:
            await self._validar_unidade_produtiva(updates["unidade_produtiva_id"])
        for k, v in updates.items():
            setattr(obj, k, v)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def desativar(self, eq_id: uuid.UUID) -> None:
        obj = await self.obter(eq_id)
        obj.status = "INATIVO"
