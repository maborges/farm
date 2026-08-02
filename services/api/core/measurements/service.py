from decimal import Decimal
from uuid import UUID
from typing import List, Optional

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_service import BaseService
from core.exceptions import BusinessRuleError
from core.measurements.models import UnidadeMedida, UnidadeMedidaConversao


class UnidadeMedidaService(BaseService[UnidadeMedida]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(UnidadeMedida, session, tenant_id)

    async def obter(self, id: UUID) -> Optional[UnidadeMedida]:
        """Busca por id respeitando visibilidade global + tenant (mesmo critério de listar)."""
        stmt = select(UnidadeMedida).where(
            UnidadeMedida.id == id,
            or_(
                UnidadeMedida.tenant_id.is_(None),
                UnidadeMedida.tenant_id == self.tenant_id,
            ),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def listar(
        self,
        dimensao: str | None = None,
        q: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[UnidadeMedida]:
        """Lista unidades globais (tenant_id NULL) + unidades do tenant atual."""
        stmt = select(UnidadeMedida).where(
            or_(
                UnidadeMedida.tenant_id.is_(None),
                UnidadeMedida.tenant_id == self.tenant_id,
            ),
            UnidadeMedida.ativo.is_(True),
        )
        if dimensao:
            stmt = stmt.where(UnidadeMedida.dimensao == dimensao)
        if q:
            termo = f"%{q}%"
            stmt = stmt.where(
                or_(
                    UnidadeMedida.nome.ilike(termo),
                    UnidadeMedida.codigo.ilike(termo),
                )
            )
        stmt = stmt.order_by(UnidadeMedida.nome).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def converter(
        self,
        valor: Decimal,
        unidade_origem_id: UUID,
        unidade_destino_id: UUID,
        cultura: str | None = None,
    ) -> Decimal:
        """
        Converte um valor entre duas unidades de medida.

        - Mesma dimensão: cálculo direto via fator_referencia (cada unidade
          guarda quanto vale em relação à unidade-base da dimensão).
        - Dimensões diferentes: busca um fator específico em
          unidades_medida_conversoes (ex: sacas de café -> kg, que varia
          por cultura/commodity e não é um fator universal).
        """
        origem = await self.obter(unidade_origem_id)
        destino = await self.obter(unidade_destino_id)
        if origem is None or destino is None:
            raise BusinessRuleError("Unidade de origem ou destino não encontrada.")

        if origem.id == destino.id:
            return valor

        if origem.dimensao == destino.dimensao:
            resultado = valor * Decimal(str(origem.fator_referencia)) / Decimal(str(destino.fator_referencia))
            return round(resultado, destino.casas_decimais)

        stmt = select(UnidadeMedidaConversao).where(
            and_(
                UnidadeMedidaConversao.unidade_origem_id == origem.id,
                UnidadeMedidaConversao.unidade_destino_id == destino.id,
                or_(
                    UnidadeMedidaConversao.tenant_id.is_(None),
                    UnidadeMedidaConversao.tenant_id == self.tenant_id,
                ),
            )
        )
        if cultura:
            stmt = stmt.where(
                or_(UnidadeMedidaConversao.cultura == cultura, UnidadeMedidaConversao.cultura.is_(None))
            ).order_by(UnidadeMedidaConversao.cultura.desc().nulls_last())
        else:
            stmt = stmt.where(UnidadeMedidaConversao.cultura.is_(None))

        conversao = (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

        if conversao is None:
            stmt_inversa = select(UnidadeMedidaConversao).where(
                and_(
                    UnidadeMedidaConversao.unidade_origem_id == destino.id,
                    UnidadeMedidaConversao.unidade_destino_id == origem.id,
                    or_(
                        UnidadeMedidaConversao.tenant_id.is_(None),
                        UnidadeMedidaConversao.tenant_id == self.tenant_id,
                    ),
                )
            )
            if cultura:
                stmt_inversa = stmt_inversa.where(
                    or_(UnidadeMedidaConversao.cultura == cultura, UnidadeMedidaConversao.cultura.is_(None))
                ).order_by(UnidadeMedidaConversao.cultura.desc().nulls_last())
            else:
                stmt_inversa = stmt_inversa.where(UnidadeMedidaConversao.cultura.is_(None))
            conversao_inversa = (await self.session.execute(stmt_inversa.limit(1))).scalar_one_or_none()
            if conversao_inversa is None:
                raise BusinessRuleError(
                    f"Não existe conversão cadastrada entre '{origem.codigo}' e '{destino.codigo}'."
                )
            resultado = valor / Decimal(str(conversao_inversa.fator))
            return round(resultado, destino.casas_decimais)

        resultado = valor * Decimal(str(conversao.fator))
        return round(resultado, destino.casas_decimais)
