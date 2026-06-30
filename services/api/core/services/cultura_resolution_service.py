from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.cultivos.models import Cultivo
from agricola.safras.models import Safra
from core.cadastros.produtos.models import ProdutoCultura


class CulturaResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    NOT_FOUND = "NOT_FOUND"
    MULTIPLE = "MULTIPLE"


class CulturaResolutionSource(str, Enum):
    CULTIVAR_ID = "CULTIVAR_ID"
    CULTIVO_TEXTO = "CULTIVO_TEXTO"
    SAFRA_TEXTO = "SAFRA_TEXTO"
    NOT_FOUND = "NOT_FOUND"
    MULTIPLE = "MULTIPLE"


@dataclass(frozen=True)
class CulturaResolution:
    status: CulturaResolutionStatus
    source: CulturaResolutionSource
    cultura_id: uuid.UUID | None = None
    nome: str | None = None
    nome_cientifico: str | None = None
    matched_text: str | None = None
    cultivo_id: uuid.UUID | None = None
    safra_id: uuid.UUID | None = None

    @property
    def resolved(self) -> bool:
        return self.status == CulturaResolutionStatus.RESOLVED


class CulturaResolutionService:
    """Resolve a cultura canônica a partir de contexto agrícola.

    Args:
        session: Sessão SQLAlchemy com contexto de tenant.
        tenant_id: Tenant autenticado da operação.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def resolve_by_cultivo(self, cultivo_id: uuid.UUID) -> CulturaResolution:
        """Resolve a cultura canônica a partir de um cultivo.

        Args:
            cultivo_id: Identificador do cultivo.

        Returns:
            CulturaResolution com status explícito.
        """
        cultivo = await self._buscar_cultivo(cultivo_id)
        if cultivo is None:
            return self._not_found(cultivo_id=cultivo_id)
        return await self._resolver_cultivo(cultivo)

    async def resolve_by_safra(self, safra_id: uuid.UUID) -> CulturaResolution:
        """Resolve a cultura canônica a partir de uma safra.

        Args:
            safra_id: Identificador da safra.

        Returns:
            CulturaResolution com status explícito.
        """
        cultivos = await self._listar_cultivos_da_safra(safra_id)
        cultivo_match = await self._resolver_por_cultivos(cultivos, safra_id)
        if cultivo_match is not None:
            return cultivo_match
        safra = await self._buscar_safra(safra_id)
        if safra is None:
            return self._not_found(safra_id=safra_id)
        return await self._resolver_por_texto(
            safra.cultura,
            CulturaResolutionSource.SAFRA_TEXTO,
            safra_id=safra_id,
        )

    async def _resolver_por_cultivos(
        self,
        cultivos: list[Cultivo],
        safra_id: uuid.UUID,
    ) -> CulturaResolution | None:
        por_id = await self._resolver_lista_cultivos(cultivos, True)
        if por_id is not None:
            return por_id if por_id.resolved else self._multiple(safra_id=safra_id)
        por_texto = await self._resolver_lista_cultivos(cultivos, False)
        if por_texto is not None:
            return por_texto if por_texto.resolved else self._multiple(safra_id=safra_id)
        return None

    async def _resolver_lista_cultivos(
        self,
        cultivos: list[Cultivo],
        preferir_cultivar: bool,
    ) -> CulturaResolution | None:
        resultados: list[CulturaResolution] = []
        for cultivo in cultivos:
            if preferir_cultivar:
                resultado = await self._resolver_por_cultivar(cultivo)
            else:
                resultado = await self._resolver_por_texto(
                    cultivo.cultura,
                    CulturaResolutionSource.CULTIVO_TEXTO,
                    cultivo_id=cultivo.id,
                    safra_id=cultivo.safra_id,
                )
            if resultado.resolved:
                resultados.append(resultado)
        return self._colapsar(resultados)

    async def _resolver_cultivo(self, cultivo: Cultivo) -> CulturaResolution:
        por_id = await self._resolver_por_cultivar(cultivo)
        if por_id.resolved:
            return por_id
        return await self._resolver_por_texto(
            cultivo.cultura,
            CulturaResolutionSource.CULTIVO_TEXTO,
            cultivo_id=cultivo.id,
            safra_id=cultivo.safra_id,
        )

    async def _resolver_por_cultivar(self, cultivo: Cultivo) -> CulturaResolution:
        if cultivo.cultivar_id is None:
            return self._not_found(cultivo_id=cultivo.id, safra_id=cultivo.safra_id)
        cultura = await self._buscar_cultura_por_id(cultivo.cultivar_id)
        if cultura is None:
            return self._not_found(cultivo_id=cultivo.id, safra_id=cultivo.safra_id)
        return self._resolved(
            cultura,
            CulturaResolutionSource.CULTIVAR_ID,
            cultivo_id=cultivo.id,
            safra_id=cultivo.safra_id,
        )

    async def _resolver_por_texto(
        self,
        texto: str | None,
        source: CulturaResolutionSource,
        cultivo_id: uuid.UUID | None = None,
        safra_id: uuid.UUID | None = None,
    ) -> CulturaResolution:
        if not texto or not texto.strip():
            return self._not_found(cultivo_id=cultivo_id, safra_id=safra_id)
        cultura = await self._buscar_cultura_por_nome(texto)
        if cultura is None:
            return self._not_found(cultivo_id=cultivo_id, safra_id=safra_id)
        return self._resolved(
            cultura,
            source,
            matched_text=texto,
            cultivo_id=cultivo_id,
            safra_id=safra_id,
        )

    async def _buscar_cultura_por_id(self, cultura_id: uuid.UUID) -> ProdutoCultura | None:
        stmt = select(ProdutoCultura).where(
            ProdutoCultura.id == cultura_id,
            or_(
                ProdutoCultura.tenant_id.is_(None),
                ProdutoCultura.tenant_id == self._tenant_id,
            ),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _buscar_cultura_por_nome(self, texto: str) -> ProdutoCultura | None:
        stmt = (
            select(ProdutoCultura)
            .where(
                ProdutoCultura.ativa.is_(True),
                or_(
                    ProdutoCultura.tenant_id.is_(None),
                    ProdutoCultura.tenant_id == self._tenant_id,
                ),
                ProdutoCultura.nome.ilike(texto.strip()),
            )
            .order_by(ProdutoCultura.tenant_id.is_(None), ProdutoCultura.nome)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _buscar_cultivo(self, cultivo_id: uuid.UUID) -> Cultivo | None:
        stmt = select(Cultivo).where(
            Cultivo.id == cultivo_id,
            Cultivo.tenant_id == self._tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _listar_cultivos_da_safra(self, safra_id: uuid.UUID) -> list[Cultivo]:
        stmt = (
            select(Cultivo)
            .where(
                Cultivo.safra_id == safra_id,
                Cultivo.tenant_id == self._tenant_id,
            )
            .order_by(Cultivo.created_at, Cultivo.id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _buscar_safra(self, safra_id: uuid.UUID) -> Safra | None:
        stmt = select(Safra).where(
            Safra.id == safra_id,
            Safra.tenant_id == self._tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def _colapsar(self, resultados: list[CulturaResolution]) -> CulturaResolution | None:
        if not resultados:
            return None
        chaves = {(item.cultura_id, (item.nome or "").upper()) for item in resultados}
        if len(chaves) > 1:
            return self._multiple(safra_id=resultados[0].safra_id)
        return resultados[0]

    def _resolved(
        self,
        cultura: ProdutoCultura,
        source: CulturaResolutionSource,
        matched_text: str | None = None,
        cultivo_id: uuid.UUID | None = None,
        safra_id: uuid.UUID | None = None,
    ) -> CulturaResolution:
        return CulturaResolution(
            status=CulturaResolutionStatus.RESOLVED,
            source=source,
            cultura_id=cultura.id,
            nome=cultura.nome,
            nome_cientifico=cultura.nome_cientifico,
            matched_text=matched_text,
            cultivo_id=cultivo_id,
            safra_id=safra_id,
        )

    def _not_found(
        self,
        cultivo_id: uuid.UUID | None = None,
        safra_id: uuid.UUID | None = None,
    ) -> CulturaResolution:
        return CulturaResolution(
            status=CulturaResolutionStatus.NOT_FOUND,
            source=CulturaResolutionSource.NOT_FOUND,
            cultivo_id=cultivo_id,
            safra_id=safra_id,
        )

    def _multiple(self, safra_id: uuid.UUID | None = None) -> CulturaResolution:
        return CulturaResolution(
            status=CulturaResolutionStatus.MULTIPLE,
            source=CulturaResolutionSource.MULTIPLE,
            safra_id=safra_id,
        )
