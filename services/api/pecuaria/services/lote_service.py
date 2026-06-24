import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.base_service import BaseService
from core.exceptions import BusinessRuleError
from core.cadastros.propriedades.models import AreaRural, TipoArea
from pecuaria.animal.models import LoteAnimal as LoteBovino
from pecuaria.schemas.lote_schema import LoteBovinoCreate

class LoteBovinoService(BaseService[LoteBovino]):
    def __init__(self, tenant_id: uuid.UUID):
        # NOTE: Ideally this expects session as well in __init__(self, model, session, tenant_id)
        # but let's see how it was called in router
        super().__init__(LoteBovino, None, tenant_id) # Session is passed in the methods there?

    async def _obter_area_piquete(
        self,
        db: AsyncSession,
        *,
        area_id: uuid.UUID,
        unidade_produtiva_id: uuid.UUID,
    ) -> AreaRural:
        """Busca o piquete canônico validando tenant, unidade, tipo e ativo."""
        stmt = select(AreaRural).where(
            AreaRural.id == area_id,
            AreaRural.tenant_id == self.tenant_id,
            AreaRural.unidade_produtiva_id == unidade_produtiva_id,
            AreaRural.tipo == TipoArea.PIQUETE.value,
            AreaRural.ativo == True,
        )
        area = (await db.execute(stmt)).scalars().first()
        if not area:
            raise BusinessRuleError(
                "O piquete selecionado não existe, está inativo ou não pertence a esta fazenda."
            )
        return area


    async def create_lote(self, db: AsyncSession, *, obj_in: LoteBovinoCreate) -> LoteBovino:
        obj_data = obj_in.model_dump(exclude_none=True)
        piquete_id = obj_data.pop("piquete_id", None)
        area_id = obj_data.pop("area_id", None) or piquete_id

        if area_id is not None:
            await self._obter_area_piquete(
                db,
                area_id=area_id,
                unidade_produtiva_id=obj_data["unidade_produtiva_id"],
            )
            obj_data["area_id"] = area_id

        # 3. Persiste Lote Principal
        db_lote = LoteBovino(**obj_data, tenant_id=self.tenant_id)
        db.add(db_lote)
        await db.flush()
        await db.refresh(db_lote)
        
        return db_lote
