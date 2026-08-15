from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.cadastros.models import ProdutoCatalogo
from core.operational_context import validate_deposito_context
from operacional.models.contagem_estoque import ContagemEstoque, ContagemEstoqueItem
from operacional.schemas.contagem_estoque import (
    ContagemAbrirRequest,
    ContagemEstoqueItemResponse,
    ContagemEstoqueResponse,
)
from operacional.schemas.estoque import AjusteEstoqueRequest
from operacional.services.estoque_service import EstoqueService


class ContagemEstoqueService:
    """OPERATIONS-GAP-01 §21.30 — sessão de contagem física de estoque.

    Reaproveita `EstoqueService.listar_saldos`/`registrar_ajuste` em vez de
    duplicar lógica de saldo; esta classe só orquestra o agrupamento
    (cabeçalho + itens) e o estado ABERTA→CONCLUIDA/CANCELADA.
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.estoque_service = EstoqueService(session, tenant_id)

    async def abrir_contagem(self, data: ContagemAbrirRequest, *, usuario_id: uuid.UUID | None = None) -> ContagemEstoque:
        await validate_deposito_context(self.session, tenant_id=self.tenant_id, deposito_id=data.deposito_id)

        contagem = ContagemEstoque(
            tenant_id=self.tenant_id,
            deposito_id=data.deposito_id,
            status="ABERTA",
            aberta_por=usuario_id,
            observacoes=data.observacoes,
        )
        self.session.add(contagem)
        await self.session.flush()

        saldos = await self.estoque_service.listar_saldos(deposito_id=data.deposito_id, limit=10000)
        for saldo in saldos:
            self.session.add(
                ContagemEstoqueItem(
                    tenant_id=self.tenant_id,
                    contagem_id=contagem.id,
                    produto_id=saldo.produto_id,
                    quantidade_sistema=saldo.quantidade_atual,
                )
            )
        await self.session.commit()
        await self.session.refresh(contagem)
        return contagem

    async def _get_or_fail(self, contagem_id: uuid.UUID) -> ContagemEstoque:
        stmt = select(ContagemEstoque).where(
            ContagemEstoque.id == contagem_id, ContagemEstoque.tenant_id == self.tenant_id,
        )
        contagem = (await self.session.execute(stmt)).scalars().first()
        if not contagem:
            raise EntityNotFoundError("Contagem de estoque não encontrada")
        return contagem

    async def _get_item_or_fail(self, contagem_id: uuid.UUID, produto_id: uuid.UUID) -> ContagemEstoqueItem:
        stmt = select(ContagemEstoqueItem).where(
            ContagemEstoqueItem.contagem_id == contagem_id,
            ContagemEstoqueItem.produto_id == produto_id,
            ContagemEstoqueItem.tenant_id == self.tenant_id,
        )
        item = (await self.session.execute(stmt)).scalars().first()
        if not item:
            raise EntityNotFoundError("Item de contagem não encontrado (produto sem saldo no depósito na abertura)")
        return item

    async def registrar_contagem_item(
        self, contagem_id: uuid.UUID, produto_id: uuid.UUID, quantidade_contada: float,
    ) -> ContagemEstoqueItem:
        contagem = await self._get_or_fail(contagem_id)
        if contagem.status != "ABERTA":
            raise BusinessRuleError("Só é possível registrar itens em contagens ABERTAS")

        item = await self._get_item_or_fail(contagem_id, produto_id)
        item.quantidade_contada = quantidade_contada
        item.contado_em = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def concluir_contagem(self, contagem_id: uuid.UUID, *, usuario_id: uuid.UUID | None = None) -> ContagemEstoque:
        contagem = await self._get_or_fail(contagem_id)
        if contagem.status != "ABERTA":
            raise BusinessRuleError("Só é possível concluir contagens ABERTAS")

        stmt = select(ContagemEstoqueItem).where(ContagemEstoqueItem.contagem_id == contagem_id)
        itens = (await self.session.execute(stmt)).scalars().all()

        for item in itens:
            if item.quantidade_contada is None:
                continue
            if float(item.quantidade_contada) == float(item.quantidade_sistema):
                continue
            mov = await self.estoque_service.registrar_ajuste(
                AjusteEstoqueRequest(
                    deposito_id=contagem.deposito_id,
                    produto_id=item.produto_id,
                    quantidade_nova=float(item.quantidade_contada),
                    motivo=f"Contagem de inventário {contagem.id}",
                    categoria_ajuste="CONTAGEM_INVENTARIO",
                )
            )
            item.movimento_ajuste_id = mov.id

        contagem.status = "CONCLUIDA"
        contagem.concluida_por = usuario_id
        contagem.concluida_em = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(contagem)
        return contagem

    async def cancelar_contagem(self, contagem_id: uuid.UUID) -> ContagemEstoque:
        contagem = await self._get_or_fail(contagem_id)
        if contagem.status != "ABERTA":
            raise BusinessRuleError("Só é possível cancelar contagens ABERTAS")
        contagem.status = "CANCELADA"
        await self.session.commit()
        await self.session.refresh(contagem)
        return contagem

    async def listar_contagens(self, *, deposito_id: uuid.UUID | None = None, status: str | None = None) -> list[ContagemEstoque]:
        stmt = select(ContagemEstoque).where(ContagemEstoque.tenant_id == self.tenant_id)
        if deposito_id:
            stmt = stmt.where(ContagemEstoque.deposito_id == deposito_id)
        if status:
            stmt = stmt.where(ContagemEstoque.status == status)
        stmt = stmt.order_by(ContagemEstoque.aberta_em.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def detalhar_contagem(self, contagem_id: uuid.UUID) -> ContagemEstoqueResponse:
        contagem = await self._get_or_fail(contagem_id)
        stmt = select(ContagemEstoqueItem).where(ContagemEstoqueItem.contagem_id == contagem_id)
        itens = (await self.session.execute(stmt)).scalars().all()

        produto_ids = [item.produto_id for item in itens]
        produtos = {}
        if produto_ids:
            prod_stmt = select(ProdutoCatalogo).where(ProdutoCatalogo.id.in_(produto_ids))
            produtos = {p.id: p for p in (await self.session.execute(prod_stmt)).scalars().all()}

        itens_response = [
            ContagemEstoqueItemResponse(
                id=item.id,
                contagem_id=item.contagem_id,
                produto_id=item.produto_id,
                produto_nome=produtos.get(item.produto_id).nome if produtos.get(item.produto_id) else None,
                quantidade_sistema=item.quantidade_sistema,
                quantidade_contada=item.quantidade_contada,
                divergencia=(
                    float(item.quantidade_contada) - float(item.quantidade_sistema)
                    if item.quantidade_contada is not None else None
                ),
                contado_em=item.contado_em,
                movimento_ajuste_id=item.movimento_ajuste_id,
            )
            for item in itens
        ]
        return ContagemEstoqueResponse(
            id=contagem.id,
            deposito_id=contagem.deposito_id,
            status=contagem.status,
            aberta_por=contagem.aberta_por,
            aberta_em=contagem.aberta_em,
            concluida_por=contagem.concluida_por,
            concluida_em=contagem.concluida_em,
            observacoes=contagem.observacoes,
            itens=itens_response,
        )
