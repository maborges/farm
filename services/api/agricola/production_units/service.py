from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.production_units.models import ProductionUnit, StatusConsorcioArea
from agricola.production_units.schemas import ProductionUnitCreate, ProductionUnitUpdate
from core.base_service import BaseService
from core.cadastros.propriedades.models import AreaRural
from agricola.cultivos.models import Cultivo, CultivoArea
from core.exceptions import EntityNotFoundError, BusinessRuleError


class ProductionUnitService(BaseService[ProductionUnit]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(ProductionUnit, session, tenant_id)

    async def listar_por_safra(self, safra_id: uuid.UUID) -> list[dict]:
        stmt = (
            select(ProductionUnit, Cultivo.cultura, AreaRural.nome)
            .outerjoin(Cultivo, Cultivo.id == ProductionUnit.cultivo_id)
            .outerjoin(AreaRural, AreaRural.id == ProductionUnit.area_id)
            .where(
                and_(
                    ProductionUnit.tenant_id == self.tenant_id,
                    ProductionUnit.safra_id == safra_id,
                )
            )
            .order_by(Cultivo.cultura, AreaRural.nome)
        )
        rows = (await self.session.execute(stmt)).all()
        result = []
        for pu, cultura, area_nome in rows:
            d = {c.key: getattr(pu, c.key) for c in ProductionUnit.__table__.columns}
            d["cultivo_nome"] = cultura
            d["area_nome"] = area_nome
            result.append(d)
        return result

    async def criar(self, safra_id: uuid.UUID, data: ProductionUnitCreate) -> dict:
        existente_stmt = select(ProductionUnit.id).where(
            and_(
                ProductionUnit.tenant_id == self.tenant_id,
                ProductionUnit.safra_id == safra_id,
                ProductionUnit.area_id == data.area_id,
            )
        )
        existente = (await self.session.execute(existente_stmt)).scalar_one_or_none()
        if existente:
            raise BusinessRuleError("Esta área já faz parte das unidades operacionais da safra.")

        cultivo_area_id = await self._resolver_cultivo_area_id(
            cultivo_id=data.cultivo_id,
            area_id=data.area_id,
            area_ha=data.area_ha,
            cultivo_area_id=data.cultivo_area_id,
        )

        obj = ProductionUnit(
            tenant_id=self.tenant_id,
            safra_id=safra_id,
            cultivo_id=data.cultivo_id,
            area_id=data.area_id,
            cultivo_area_id=cultivo_area_id,
            percentual_participacao=float(data.percentual_participacao),
            area_ha=float(data.area_ha),
            data_inicio=data.data_inicio,
            data_fim=data.data_fim,
            status="ATIVA",
        )
        self.session.add(obj)
        await self.session.flush()
        return await self._enrich(obj)

    async def obter(self, pu_id: uuid.UUID) -> dict:
        pu = await self._get_or_fail_tenant(pu_id)
        return await self._enrich(pu)

    async def atualizar(self, pu_id: uuid.UUID, data: ProductionUnitUpdate) -> dict:
        pu = await self._get_or_fail_tenant(pu_id)
        updates = data.model_dump(exclude_none=True)
        if "status" in updates and updates["status"] not in ("ATIVA", "ENCERRADA"):
            raise BusinessRuleError("Status deve ser ATIVA ou ENCERRADA.")
        for k, v in updates.items():
            setattr(pu, k, float(v) if isinstance(v, Decimal) else v)
        await self.session.flush()
        return await self._enrich(pu)

    async def encerrar(self, pu_id: uuid.UUID) -> dict:
        pu = await self._get_or_fail_tenant(pu_id)
        if pu.status == "ENCERRADA":
            raise BusinessRuleError("Production Unit já está encerrada.")
        pu.status = "ENCERRADA"
        await self.session.flush()
        return await self._enrich(pu)

    async def status_consorcio(self, safra_id: uuid.UUID) -> list[dict]:
        stmt = (
            select(StatusConsorcioArea, AreaRural.nome)
            .join(AreaRural, AreaRural.id == StatusConsorcioArea.area_id)
            .where(
                and_(
                    StatusConsorcioArea.tenant_id == self.tenant_id,
                    StatusConsorcioArea.safra_id == safra_id,
                )
            )
        )
        rows = (await self.session.execute(stmt)).all()
        result = []
        for sc, area_nome in rows:
            d = {c.key: getattr(sc, c.key) for c in StatusConsorcioArea.__table__.columns}
            d["area_nome"] = area_nome
            result.append(d)
        return result

    async def sincronizar_de_cultivo_area(
        self, cultivo_area: CultivoArea, safra_id: uuid.UUID
    ) -> ProductionUnit:
        """
        Cria ou atualiza a ProductionUnit correspondente a um CultivoArea, mantendo
        os dois vínculos (talhão × cultivo) em sincronia.

        Idempotente por (tenant, safra, cultivo, área): reaproveita a PU existente
        (mesmo que ENCERRADA, reativando-a) em vez de duplicar. `percentual_participacao`
        nunca é sobrescrito automaticamente — só é definido como 100% na criação inicial;
        ajustes manuais (ex: consórcio) feitos na tela de Production Units são preservados
        em sincronizações futuras.
        """
        stmt = select(ProductionUnit).where(
            and_(
                ProductionUnit.tenant_id == self.tenant_id,
                ProductionUnit.safra_id == safra_id,
                ProductionUnit.cultivo_id == cultivo_area.cultivo_id,
                ProductionUnit.area_id == cultivo_area.area_id,
            )
        )
        pu = (await self.session.execute(stmt)).scalar_one_or_none()
        if pu:
            pu.cultivo_area_id = cultivo_area.id
            pu.area_ha = float(cultivo_area.area_ha)
            if pu.status == "ENCERRADA":
                pu.status = "ATIVA"
            await self.session.flush()
            return pu

        pu = ProductionUnit(
            tenant_id=self.tenant_id,
            safra_id=safra_id,
            cultivo_id=cultivo_area.cultivo_id,
            area_id=cultivo_area.area_id,
            cultivo_area_id=cultivo_area.id,
            percentual_participacao=100.0,
            area_ha=float(cultivo_area.area_ha),
            status="ATIVA",
        )
        self.session.add(pu)
        await self.session.flush()
        return pu

    async def encerrar_por_cultivo_area(
        self, safra_id: uuid.UUID, cultivo_id: uuid.UUID, area_id: uuid.UUID
    ) -> None:
        """
        Encerra (nunca deleta) a ProductionUnit correspondente quando o CultivoArea
        que a originou é removido — preserva o histórico de CostAllocation/DRE já
        lançado contra essa unidade. Silencioso se não houver PU ativa para o combo
        (ex: sincronização nunca rodou antes, ou já estava encerrada).
        """
        stmt = select(ProductionUnit).where(
            and_(
                ProductionUnit.tenant_id == self.tenant_id,
                ProductionUnit.safra_id == safra_id,
                ProductionUnit.cultivo_id == cultivo_id,
                ProductionUnit.area_id == area_id,
                ProductionUnit.status == "ATIVA",
            )
        )
        pu = (await self.session.execute(stmt)).scalar_one_or_none()
        if pu:
            pu.status = "ENCERRADA"
            await self.session.flush()

    async def _get_or_fail_tenant(self, pu_id: uuid.UUID) -> ProductionUnit:
        stmt = select(ProductionUnit).where(
            and_(ProductionUnit.id == pu_id, ProductionUnit.tenant_id == self.tenant_id)
        )
        pu = (await self.session.execute(stmt)).scalar_one_or_none()
        if not pu:
            raise EntityNotFoundError(f"ProductionUnit {pu_id} não encontrada.")
        return pu

    async def _resolver_cultivo_area_id(
        self,
        *,
        cultivo_id: uuid.UUID,
        area_id: uuid.UUID,
        area_ha: Decimal,
        cultivo_area_id: uuid.UUID | None,
    ) -> uuid.UUID | None:
        """
        Resolve o vínculo CultivoArea usado como origem da unidade operacional.

        A unidade operacional nasce do par (cultivo, área). Se a origem for
        inequívoca, reaproveitamos o registro de cultivo_areas correspondente.
        """
        if cultivo_area_id is not None:
            stmt = select(CultivoArea.id).where(
                and_(
                    CultivoArea.id == cultivo_area_id,
                    CultivoArea.tenant_id == self.tenant_id,
                    CultivoArea.cultivo_id == cultivo_id,
                    CultivoArea.area_id == area_id,
                )
            )
            existente = (await self.session.execute(stmt)).scalar_one_or_none()
            if not existente:
                raise BusinessRuleError(
                    "O cultivo_area_id informado não corresponde ao cultivo e à área selecionados."
                )
            return cultivo_area_id

        stmt = (
            select(CultivoArea.id)
            .where(
                and_(
                    CultivoArea.tenant_id == self.tenant_id,
                    CultivoArea.cultivo_id == cultivo_id,
                    CultivoArea.area_id == area_id,
                )
            )
            .order_by(CultivoArea.created_at.asc(), CultivoArea.id.asc())
        )
        cultivo_area_id_resolvido = (await self.session.execute(stmt)).scalars().first()
        if cultivo_area_id_resolvido:
            return cultivo_area_id_resolvido

        cultivo_area = CultivoArea(
            tenant_id=self.tenant_id,
            cultivo_id=cultivo_id,
            area_id=area_id,
            area_ha=float(area_ha),
        )
        self.session.add(cultivo_area)
        await self.session.flush()
        return cultivo_area.id

    async def _enrich(self, pu: ProductionUnit) -> dict:
        cultura = (
            await self.session.execute(select(Cultivo.cultura).where(Cultivo.id == pu.cultivo_id))
        ).scalar_one_or_none()
        area_nome = (
            await self.session.execute(select(AreaRural.nome).where(AreaRural.id == pu.area_id))
        ).scalar_one_or_none()
        d = {c.key: getattr(pu, c.key) for c in ProductionUnit.__table__.columns}
        d["cultivo_nome"] = cultura
        d["area_nome"] = area_nome
        return d
