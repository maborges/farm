from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.services.sequencial_service import SequencialService
from imoveis.models.manutencao_benfeitoria import OrdemServicoBenfeitoria, PlanoManutencaoBenfeitoria
from imoveis.schemas.manutencao_benfeitoria import (
    OrdemServicoBenfeitoriaCreate,
    PlanoManutencaoBenfeitoriaCreate,
)


class ManutencaoBenfeitoriaService:
    """OPERATIONS-GAP-01 §21.33 — workflow de manutenção para infraestrutura fixa.

    Módulo paralelo ao de frota (`operacional/models/frota.py`), não uma
    generalização dele — os models de frota são acoplados a `equipamento_id`
    em várias services de negócio (dashboard, custo consolidado), retrofitar
    uma FK alternativa ali teria blast radius alto. Aqui é um workflow
    simplificado (sem horímetro/km) dedicado só a `Benfeitoria`.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def criar_plano(self, data: PlanoManutencaoBenfeitoriaCreate) -> PlanoManutencaoBenfeitoria:
        plano = PlanoManutencaoBenfeitoria(tenant_id=self.tenant_id, **data.model_dump())
        self.session.add(plano)
        await self.session.commit()
        await self.session.refresh(plano)
        return plano

    async def listar_planos(self, benfeitoria_id: uuid.UUID | None = None) -> list[PlanoManutencaoBenfeitoria]:
        stmt = select(PlanoManutencaoBenfeitoria).where(PlanoManutencaoBenfeitoria.tenant_id == self.tenant_id)
        if benfeitoria_id:
            stmt = stmt.where(PlanoManutencaoBenfeitoria.benfeitoria_id == benfeitoria_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def abrir_os(self, data: OrdemServicoBenfeitoriaCreate, *, usuario_id: uuid.UUID | None = None) -> OrdemServicoBenfeitoria:
        numero_os = await SequencialService(self.session, self.tenant_id).proximo_numero("manutencao_benfeitoria_os")
        os_ = OrdemServicoBenfeitoria(
            tenant_id=self.tenant_id,
            numero_os=numero_os,
            status="ABERTA",
            aberta_por_id=usuario_id,
            **data.model_dump(),
        )
        self.session.add(os_)
        await self.session.commit()
        await self.session.refresh(os_)
        return os_

    async def _get_or_fail(self, os_id: uuid.UUID) -> OrdemServicoBenfeitoria:
        stmt = select(OrdemServicoBenfeitoria).where(
            OrdemServicoBenfeitoria.id == os_id, OrdemServicoBenfeitoria.tenant_id == self.tenant_id,
        )
        os_ = (await self.session.execute(stmt)).scalars().first()
        if not os_:
            raise EntityNotFoundError("Ordem de serviço de manutenção não encontrada")
        return os_

    async def concluir_os(
        self, os_id: uuid.UUID, *, custo_total: float, usuario_id: uuid.UUID | None = None,
    ) -> OrdemServicoBenfeitoria:
        os_ = await self._get_or_fail(os_id)
        if os_.status in ("CONCLUIDA", "CANCELADA"):
            raise BusinessRuleError(f"Ordem de serviço já está {os_.status}, não pode ser concluída novamente.")

        os_.status = "CONCLUIDA"
        os_.custo_total = custo_total
        os_.data_conclusao = datetime.now(timezone.utc)
        os_.encerrada_por_id = usuario_id

        if os_.plano_manutencao_id:
            plano = await self.session.get(PlanoManutencaoBenfeitoria, os_.plano_manutencao_id)
            if plano:
                plano.ultimo_registro_data = os_.data_conclusao

        await self.session.commit()
        await self.session.refresh(os_)
        return os_

    async def cancelar_os(self, os_id: uuid.UUID) -> OrdemServicoBenfeitoria:
        os_ = await self._get_or_fail(os_id)
        if os_.status in ("CONCLUIDA", "CANCELADA"):
            raise BusinessRuleError(f"Ordem de serviço já está {os_.status}, não pode ser cancelada.")
        os_.status = "CANCELADA"
        await self.session.commit()
        await self.session.refresh(os_)
        return os_

    async def listar_os(
        self, *, benfeitoria_id: uuid.UUID | None = None, status: str | None = None,
    ) -> list[OrdemServicoBenfeitoria]:
        stmt = select(OrdemServicoBenfeitoria).where(OrdemServicoBenfeitoria.tenant_id == self.tenant_id)
        if benfeitoria_id:
            stmt = stmt.where(OrdemServicoBenfeitoria.benfeitoria_id == benfeitoria_id)
        if status:
            stmt = stmt.where(OrdemServicoBenfeitoria.status == status)
        stmt = stmt.order_by(OrdemServicoBenfeitoria.data_abertura.desc())
        return list((await self.session.execute(stmt)).scalars().all())
