from __future__ import annotations

import uuid

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.base_service import BaseService
from core.cadastros.propriedades.models import AreaRural, TipoArea
from core.exceptions import BusinessRuleError, EntityNotFoundError
from pecuaria.animal.models import Animal, LoteAnimal as LoteBovino
from pecuaria.schemas.lote_schema import LoteBovinoCreate, LoteBovinoUpdate

CAMPOS_ATUALIZAVEIS_LOTE = frozenset({
    "identificacao",
    "modo_gestao",
    "categoria",
    "raca",
    "quantidade_cabecas",
    "peso_medio_kg",
    "peso_inicial_medio_kg",
    "rendimento_carcaca_pct",
    "valor_aquisicao_total",
    "cotacao_arroba_override",
    "ativo",
})


class LoteBovinoService(BaseService[LoteBovino]):
    """Serviço de gestão de lotes bovinos com suporte ao modo híbrido."""

    def __init__(self, tenant_id: uuid.UUID):
        super().__init__(LoteBovino, None, tenant_id)

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
            AreaRural.ativo == True,  # noqa: E712
        )
        area = (await db.execute(stmt)).scalars().first()
        if not area:
            raise BusinessRuleError(
                "O piquete selecionado não existe, está inativo ou não pertence a esta fazenda."
            )
        return area

    async def _buscar_lote(self, db: AsyncSession, lote_id: uuid.UUID) -> LoteBovino:
        """Busca lote por ID respeitando isolamento multi-tenant.

        Args:
            db: Sessão assíncrona ativa.
            lote_id: Identificador do lote.

        Returns:
            Registro LoteBovino encontrado.

        Raises:
            EntityNotFoundError: Se o lote não existir no tenant.
        """
        lote = await db.scalar(
            select(LoteBovino).where(
                LoteBovino.id == lote_id,
                LoteBovino.tenant_id == self.tenant_id,
            )
        )
        if not lote:
            raise EntityNotFoundError(f"Lote {lote_id} não encontrado neste tenant.")
        return lote

    async def _contar_animais_ativos(self, db: AsyncSession, lote_id: uuid.UUID) -> int:
        """Conta cabeças individuais ativas vinculadas ao lote."""
        stmt = select(func.count(Animal.id)).where(
            Animal.tenant_id == self.tenant_id,
            Animal.lote_id == lote_id,
            Animal.status == "ATIVO",
        )
        return int((await db.execute(stmt)).scalar_one() or 0)

    async def _validar_transicao_modo(
        self, db: AsyncSession, lote: LoteBovino, novo_modo: str | None
    ) -> None:
        """Impede retorno para POR_LOTE quando já existem animais individuais ativos."""
        if novo_modo != "POR_LOTE" or lote.modo_gestao == "POR_LOTE":
            return
        if await self._contar_animais_ativos(db, lote.id) > 0:
            raise BusinessRuleError(
                "Não é possível alterar para POR_LOTE enquanto houver animais individuais ativos."
            )

    async def _aplicar_atualizacao_piquete(
        self, db: AsyncSession, lote: LoteBovino, updates: dict
    ) -> None:
        """Atualiza area_id validando o piquete dentro do tenant e fazenda."""
        if "piquete_id" not in updates:
            return
        piquete_id = updates.pop("piquete_id")
        if piquete_id is None:
            lote.area_id = None
            return
        await self._obter_area_piquete(
            db, area_id=piquete_id, unidade_produtiva_id=lote.unidade_produtiva_id
        )
        lote.area_id = piquete_id

    async def create_lote(self, db: AsyncSession, *, obj_in: LoteBovinoCreate) -> LoteBovino:
        """Cria um novo lote pecuário com parâmetros híbridos e econômicos.

        Args:
            db: Sessão assíncrona ativa.
            obj_in: Payload validado de criação do lote.

        Returns:
            Instância persistida de LoteBovino.

        Raises:
            BusinessRuleError: Se o piquete informado for inválido.
        """
        obj_data = obj_in.model_dump(exclude_none=True)
        piquete_id = obj_data.pop("piquete_id", None)
        area_id = obj_data.pop("area_id", None) or piquete_id

        if area_id is not None:
            await self._obter_area_piquete(
                db, area_id=area_id, unidade_produtiva_id=obj_data["unidade_produtiva_id"]
            )
            obj_data["area_id"] = area_id

        if obj_data.get("peso_inicial_medio_kg") is None and obj_data.get("peso_medio_kg", 0) > 0:
            obj_data["peso_inicial_medio_kg"] = float(obj_data["peso_medio_kg"])

        db_lote = LoteBovino(**obj_data, tenant_id=self.tenant_id)
        db.add(db_lote)
        await db.flush()
        await db.refresh(db_lote)
        return db_lote

    async def update_lote(
        self, db: AsyncSession, lote_id: uuid.UUID, obj_in: LoteBovinoUpdate
    ) -> LoteBovino:
        """Atualiza parâmetros de gestão, piquete e econômicos de um lote.

        Args:
            db: Sessão assíncrona ativa.
            lote_id: Identificador do lote a atualizar.
            obj_in: Campos opcionais de atualização.

        Returns:
            LoteBovino atualizado após flush e refresh.

        Raises:
            EntityNotFoundError: Se o lote não existir no tenant.
            BusinessRuleError: Em piquete inválido ou transição proibida de modo.
        """
        lote = await self._buscar_lote(db, lote_id)
        updates = obj_in.model_dump(exclude_unset=True)
        await self._validar_transicao_modo(db, lote, updates.get("modo_gestao"))
        await self._aplicar_atualizacao_piquete(db, lote, updates)
        for campo, valor in updates.items():
            if campo in CAMPOS_ATUALIZAVEIS_LOTE:
                setattr(lote, campo, valor)
        await db.flush()
        await db.refresh(lote)
        return lote
