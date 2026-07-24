import uuid
from typing import Optional
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_service import BaseService
from core.exceptions import EntityNotFoundError, BusinessRuleError
from .models import Marca, ModeloProduto, CategoriaProduto, Produto, ProdutoAgricola, ProdutoEstoque, ProdutoEPI, ProdutoCultura, SoloParametroCultura


# Categorias-sistema (tenant_id NULL) semeadas na migration 20260723f,
# equivalentes ao TipoProduto legado — usadas só para derivar Produto.tipo
# automaticamente a partir da categoria escolhida no formulário (tipo deixou
# de ser um campo editável; ver CLAUDE.md / brainstorm de unificação).
CATEGORIA_SISTEMA_PARA_TIPO: dict[uuid.UUID, str] = {
    uuid.UUID("11111111-ca70-0000-0000-000000000001"): "SEMENTE",
    uuid.UUID("11111111-ca70-0000-0000-000000000002"): "DEFENSIVO",
    uuid.UUID("11111111-ca70-0000-0000-000000000003"): "FERTILIZANTE",
    uuid.UUID("11111111-ca70-0000-0000-000000000004"): "INOCULANTE",
    uuid.UUID("11111111-ca70-0000-0000-000000000005"): "ADJUVANTE",
    uuid.UUID("11111111-ca70-0000-0000-000000000006"): "RACAO",
    uuid.UUID("11111111-ca70-0000-0000-000000000007"): "MEDICAMENTO",
    uuid.UUID("11111111-ca70-0000-0000-000000000008"): "VACINA",
    uuid.UUID("11111111-ca70-0000-0000-000000000009"): "MINERAL",
    uuid.UUID("11111111-ca70-0000-0000-000000000010"): "PECA",
    uuid.UUID("11111111-ca70-0000-0000-000000000011"): "LUBRIFICANTE",
    uuid.UUID("11111111-ca70-0000-0000-000000000012"): "COMBUSTIVEL",
    uuid.UUID("11111111-ca70-0000-0000-000000000013"): "MATERIAL_GERAL",
    uuid.UUID("11111111-ca70-0000-0000-000000000014"): "EPI",
    uuid.UUID("11111111-ca70-0000-0000-000000000015"): "SERVICO",
}


_PRODUTO_LOADS = [
    selectinload(Produto.marca_rel),
    selectinload(Produto.modelo_rel),
    selectinload(Produto.categoria),
    selectinload(Produto.detalhe_agricola),
    selectinload(Produto.detalhe_estoque),
    selectinload(Produto.detalhe_epi),
]


class ProdutoService(BaseService[Produto]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        super().__init__(Produto, session, tenant_id)

    # ── Marcas ────────────────────────────────────────────────────────────────

    async def listar_marcas(self, ativo: Optional[bool] = None) -> list[Marca]:
        stmt = select(Marca).where(
            or_(Marca.tenant_id.is_(None), Marca.tenant_id == self.tenant_id)
        ).order_by(Marca.nome)
        if ativo is not None:
            stmt = stmt.where(Marca.ativo == ativo)
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_marca(self, data) -> Marca:
        obj = Marca(tenant_id=self.tenant_id, sistema=False, **data.model_dump())
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def _get_marca(self, marca_id: uuid.UUID, editavel: bool = False) -> Marca:
        conds = [Marca.id == marca_id, Marca.tenant_id == self.tenant_id]
        if editavel:
            conds.append(Marca.sistema == False)
        obj = (await self.session.execute(select(Marca).where(*conds))).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Marca não encontrada" + (" ou não editável" if editavel else ""))
        return obj

    async def atualizar_marca(self, marca_id: uuid.UUID, data) -> Marca:
        obj = await self._get_marca(marca_id, editavel=True)
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(obj, k, v)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def remover_marca(self, marca_id: uuid.UUID) -> None:
        obj = await self._get_marca(marca_id, editavel=True)
        if (await self.session.execute(select(ModeloProduto).where(ModeloProduto.marca_id == marca_id))).scalar_one_or_none():
            raise BusinessRuleError("Não é possível excluir marca com modelos vinculados. Desative os modelos primeiro.")
        obj.ativo = False

    # ── Modelos ───────────────────────────────────────────────────────────────

    async def listar_modelos(
        self, marca_id: Optional[uuid.UUID] = None,
        tipo_produto: Optional[str] = None, ativo: Optional[bool] = None,
    ) -> list[ModeloProduto]:
        stmt = (
            select(ModeloProduto)
            .where(or_(ModeloProduto.tenant_id.is_(None), ModeloProduto.tenant_id == self.tenant_id))
            .options(selectinload(ModeloProduto.marca))
            .order_by(ModeloProduto.nome)
        )
        if marca_id:
            stmt = stmt.where(ModeloProduto.marca_id == marca_id)
        if tipo_produto:
            stmt = stmt.where(
                (ModeloProduto.tipo_produto == tipo_produto) | (ModeloProduto.tipo_produto.is_(None))
            )
        if ativo is not None:
            stmt = stmt.where(ModeloProduto.ativo == ativo)
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_modelo(self, data) -> ModeloProduto:
        marca = (await self.session.execute(
            select(Marca).where(Marca.id == data.marca_id, or_(Marca.tenant_id.is_(None), Marca.tenant_id == self.tenant_id))
        )).scalar_one_or_none()
        if not marca:
            raise EntityNotFoundError("Marca não encontrada")
        obj = ModeloProduto(tenant_id=self.tenant_id, sistema=False, **data.model_dump())
        self.session.add(obj)
        await self.session.flush()
        res = (await self.session.execute(
            select(ModeloProduto).where(ModeloProduto.id == obj.id).options(selectinload(ModeloProduto.marca))
        )).scalar_one()
        return res

    async def _get_modelo(self, modelo_id: uuid.UUID, editavel: bool = False) -> ModeloProduto:
        conds = [ModeloProduto.id == modelo_id, ModeloProduto.tenant_id == self.tenant_id]
        if editavel:
            conds.append(ModeloProduto.sistema == False)
        obj = (await self.session.execute(
            select(ModeloProduto).where(*conds).options(selectinload(ModeloProduto.marca))
        )).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Modelo não encontrado" + (" ou não editável" if editavel else ""))
        return obj

    async def atualizar_modelo(self, modelo_id: uuid.UUID, data) -> ModeloProduto:
        obj = await self._get_modelo(modelo_id, editavel=True)
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(obj, k, v)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def remover_modelo(self, modelo_id: uuid.UUID) -> None:
        obj = await self._get_modelo(modelo_id, editavel=True)
        obj.ativo = False

    # ── Categorias ────────────────────────────────────────────────────────────

    async def listar_categorias(self, parent_id: Optional[uuid.UUID] = None, ativo: Optional[bool] = None) -> list[CategoriaProduto]:
        stmt = (
            select(CategoriaProduto)
            .where(or_(CategoriaProduto.tenant_id.is_(None), CategoriaProduto.tenant_id == self.tenant_id))
            .order_by(CategoriaProduto.ordem, CategoriaProduto.nome)
        )
        if parent_id is not None:
            stmt = stmt.where(CategoriaProduto.parent_id == parent_id)
        if ativo is not None:
            stmt = stmt.where(CategoriaProduto.ativo == ativo)
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_categoria(self, data) -> CategoriaProduto:
        obj = CategoriaProduto(tenant_id=self.tenant_id, sistema=False, **data.model_dump())
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def _get_categoria(self, cat_id: uuid.UUID, editavel: bool = False) -> CategoriaProduto:
        conds = [CategoriaProduto.id == cat_id, CategoriaProduto.tenant_id == self.tenant_id]
        if editavel:
            conds.append(CategoriaProduto.sistema == False)
        obj = (await self.session.execute(select(CategoriaProduto).where(*conds))).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Categoria não encontrada" + (" ou não editável" if editavel else ""))
        return obj

    async def atualizar_categoria(self, cat_id: uuid.UUID, data) -> CategoriaProduto:
        obj = await self._get_categoria(cat_id, editavel=True)
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(obj, k, v)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def remover_categoria(self, cat_id: uuid.UUID) -> None:
        obj = await self._get_categoria(cat_id, editavel=True)
        obj.ativo = False

    # ── Produtos ──────────────────────────────────────────────────────────────

    async def listar_produtos(
        self, tipo: Optional[str] = None, categoria_id: Optional[uuid.UUID] = None,
        marca_id: Optional[uuid.UUID] = None, ativo: Optional[bool] = None, q: Optional[str] = None,
        incluir_sistema: bool = False,
    ) -> list[Produto]:
        stmt = select(Produto).options(*_PRODUTO_LOADS).order_by(Produto.nome)
        if incluir_sistema:
            stmt = stmt.where(or_(Produto.tenant_id.is_(None), Produto.tenant_id == self.tenant_id))
        else:
            stmt = stmt.where(Produto.tenant_id == self.tenant_id)
        if tipo:
            stmt = stmt.where(Produto.tipo == tipo)
        if categoria_id:
            stmt = stmt.where(Produto.categoria_id == categoria_id)
        if marca_id:
            stmt = stmt.where(Produto.marca_id == marca_id)
        if ativo is not None:
            stmt = stmt.where(Produto.ativo == ativo)
        if q:
            stmt = stmt.where(or_(Produto.nome.ilike(f"%{q}%"), Produto.codigo_interno.ilike(f"%{q}%")))
        return list((await self.session.execute(stmt)).scalars().all())

    async def _derivar_tipo_de_categoria(self, categoria_id: Optional[uuid.UUID]) -> str:
        """Sobe a árvore de categoria até achar uma categoria-sistema
        conhecida e retorna o TipoProduto equivalente. `tipo` não é mais
        escolhido pelo usuário — é só um espelho de compatibilidade para
        código legado que ainda filtra/agrupa por ele."""
        atual_id = categoria_id
        visitados = set()
        for _ in range(10):
            if atual_id is None or atual_id in visitados:
                break
            if atual_id in CATEGORIA_SISTEMA_PARA_TIPO:
                return CATEGORIA_SISTEMA_PARA_TIPO[atual_id]
            visitados.add(atual_id)
            categoria = (await self.session.execute(
                select(CategoriaProduto.parent_id).where(CategoriaProduto.id == atual_id)
            )).scalar_one_or_none()
            atual_id = categoria
        return "OUTRO"

    async def criar_produto(self, data) -> Produto:
        payload = data.model_dump(exclude={"detalhe_agricola", "detalhe_estoque", "detalhe_epi"})
        # Guardrail: campos operacionais deixam de ser escritos pelo catálogo.
        payload.pop("estoque_minimo", None)
        payload.pop("preco_ultima_compra", None)
        if payload.get("produto_referencia_id"):
            referencia = (await self.session.execute(
                select(Produto).where(Produto.id == payload["produto_referencia_id"], Produto.tenant_id.is_(None))
            )).scalar_one_or_none()
            if not referencia:
                raise EntityNotFoundError("Produto padrão de referência não encontrado")
        if not payload.get("tipo"):
            payload["tipo"] = await self._derivar_tipo_de_categoria(payload.get("categoria_id"))
        produto = Produto(tenant_id=self.tenant_id, **payload)
        if data.detalhe_agricola:
            produto.detalhe_agricola = ProdutoAgricola(**data.detalhe_agricola.model_dump())
        if data.detalhe_estoque:
            produto.detalhe_estoque = ProdutoEstoque(**data.detalhe_estoque.model_dump())
        if data.detalhe_epi:
            produto.detalhe_epi = ProdutoEPI(**data.detalhe_epi.model_dump())
        self.session.add(produto)
        await self.session.flush()
        res = (await self.session.execute(
            select(Produto).where(Produto.id == produto.id).options(*_PRODUTO_LOADS)
        )).scalar_one()
        return res

    async def _get_produto(self, produto_id: uuid.UUID) -> Produto:
        obj = (await self.session.execute(
            select(Produto).where(
                Produto.id == produto_id,
                or_(Produto.tenant_id.is_(None), Produto.tenant_id == self.tenant_id),
            ).options(*_PRODUTO_LOADS)
        )).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Produto não encontrado")
        return obj

    async def atualizar_produto(self, produto_id: uuid.UUID, data) -> Produto:
        obj = (await self.session.execute(
            select(Produto).where(Produto.id == produto_id, Produto.tenant_id == self.tenant_id).options(*_PRODUTO_LOADS)
        )).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Produto não encontrado")
        payload = data.model_dump(exclude_none=True, exclude={"estoque_minimo", "preco_ultima_compra", "detalhe_agricola", "detalhe_estoque", "detalhe_epi", "tipo"})
        for k, v in payload.items():
            setattr(obj, k, v)
        if "categoria_id" in payload:
            obj.tipo = await self._derivar_tipo_de_categoria(payload["categoria_id"])

        if data.detalhe_agricola is not None:
            if obj.detalhe_agricola:
                for ak, av in data.detalhe_agricola.model_dump(exclude_none=True).items():
                    setattr(obj.detalhe_agricola, ak, av)
            else:
                obj.detalhe_agricola = ProdutoAgricola(**data.detalhe_agricola.model_dump(exclude_none=True))

        if data.detalhe_estoque is not None:
            if obj.detalhe_estoque:
                for ek, ev in data.detalhe_estoque.model_dump(exclude_none=True).items():
                    setattr(obj.detalhe_estoque, ek, ev)
            else:
                obj.detalhe_estoque = ProdutoEstoque(**data.detalhe_estoque.model_dump(exclude_none=True))

        if data.detalhe_epi is not None:
            if obj.detalhe_epi:
                for pk, pv in data.detalhe_epi.model_dump(exclude_none=True).items():
                    setattr(obj.detalhe_epi, pk, pv)
            else:
                obj.detalhe_epi = ProdutoEPI(**data.detalhe_epi.model_dump(exclude_none=True))

        await self.session.flush()
        res = (await self.session.execute(
            select(Produto).where(Produto.id == produto_id).options(*_PRODUTO_LOADS)
        )).scalar_one()
        return res

    async def _produto_em_uso(self, produto_id: uuid.UUID) -> bool:
        """Verifica se o produto já foi usado em algum fluxo operacional
        (compras, estoque, requisições, manutenção, manejo). Se sim, não pode
        ser excluído de vez — só desativado."""
        from operacional.models.compras import SolicitacaoItem, ItemPedidoCompra, ItemDevolucao, CotacaoItem
        from operacional.models.estoque import LoteEstoque, ItemRequisicao, ReservaEstoque, EstoqueMovimento
        from operacional.models.frota import ItemOrdemServico
        from agricola.operacoes.models import InsumoOperacao
        from pecuaria.models.manejo import ManejoLote
        from pecuaria.animal.models import EventoAnimal

        tabelas_produto_id = [
            SolicitacaoItem, ItemPedidoCompra, ItemDevolucao, CotacaoItem,
            LoteEstoque, ItemRequisicao, ReservaEstoque, EstoqueMovimento,
            ItemOrdemServico, InsumoOperacao, ManejoLote, EventoAnimal,
        ]
        for modelo in tabelas_produto_id:
            existe = (await self.session.execute(
                select(modelo.id).where(modelo.produto_id == produto_id).limit(1)
            )).scalar_one_or_none()
            if existe:
                return True
        return False

    async def remover_produto(self, produto_id: uuid.UUID) -> None:
        obj = (await self.session.execute(
            select(Produto).where(Produto.id == produto_id, Produto.tenant_id == self.tenant_id)
        )).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Produto não encontrado")

        if await self._produto_em_uso(produto_id):
            obj.ativo = False
            return

        for detalhe in (obj.detalhe_agricola, obj.detalhe_estoque, obj.detalhe_epi):
            if detalhe:
                await self.session.delete(detalhe)
        await self.session.flush()
        await self.session.delete(obj)

    # ── Culturas ──────────────────────────────────────────────────────────────

    async def listar_culturas(self, grupo: Optional[str] = None, ativa: Optional[bool] = None, q: Optional[str] = None) -> list[ProdutoCultura]:
        stmt = select(ProdutoCultura).where(
            or_(ProdutoCultura.tenant_id.is_(None), ProdutoCultura.tenant_id == self.tenant_id)
        ).order_by(ProdutoCultura.nome)
        if grupo:
            stmt = stmt.where(ProdutoCultura.grupo == grupo)
        if ativa is not None:
            stmt = stmt.where(ProdutoCultura.ativa == ativa)
        if q:
            stmt = stmt.where(or_(ProdutoCultura.nome.ilike(f"%{q}%"), ProdutoCultura.nome_cientifico.ilike(f"%{q}%")))
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_cultura(self, data) -> ProdutoCultura:
        obj = ProdutoCultura(tenant_id=self.tenant_id, sistema=False, **data.model_dump())
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def _get_cultura(self, cultura_id: uuid.UUID, editavel: bool = False) -> ProdutoCultura:
        conds = [ProdutoCultura.id == cultura_id, ProdutoCultura.tenant_id == self.tenant_id]
        if editavel:
            conds.append(ProdutoCultura.sistema == False)
        obj = (await self.session.execute(select(ProdutoCultura).where(*conds))).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Cultura não encontrada" + (" ou não editável" if editavel else ""))
        return obj

    async def atualizar_cultura(self, cultura_id: uuid.UUID, data) -> ProdutoCultura:
        obj = await self._get_cultura(cultura_id, editavel=True)
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(obj, k, v)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def remover_cultura(self, cultura_id: uuid.UUID) -> None:
        obj = await self._get_cultura(cultura_id, editavel=True)
        obj.ativa = False

    # ── Solo Parâmetros ───────────────────────────────────────────────────────

    async def listar_parametros_solo(self, cultura_id: uuid.UUID) -> list[SoloParametroCultura]:
        stmt = select(SoloParametroCultura).where(
            SoloParametroCultura.cultura_id == cultura_id,
            or_(SoloParametroCultura.tenant_id.is_(None), SoloParametroCultura.tenant_id == self.tenant_id),
        ).order_by(SoloParametroCultura.parametro, SoloParametroCultura.faixa_min)
        return list((await self.session.execute(stmt)).scalars().all())

    async def criar_parametro_solo(self, cultura_id: uuid.UUID, data) -> SoloParametroCultura:
        if not await self.session.get(ProdutoCultura, cultura_id):
            raise EntityNotFoundError("Cultura não encontrada")
        obj = SoloParametroCultura(cultura_id=cultura_id, tenant_id=self.tenant_id, **data.model_dump())
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def _get_parametro_solo(self, param_id: uuid.UUID, cultura_id: uuid.UUID) -> SoloParametroCultura:
        obj = (await self.session.execute(
            select(SoloParametroCultura).where(
                SoloParametroCultura.id == param_id,
                SoloParametroCultura.cultura_id == cultura_id,
                SoloParametroCultura.tenant_id == self.tenant_id,
            )
        )).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Parâmetro não encontrado ou não editável")
        return obj

    async def atualizar_parametro_solo(self, param_id: uuid.UUID, cultura_id: uuid.UUID, data) -> SoloParametroCultura:
        obj = await self._get_parametro_solo(param_id, cultura_id)
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(obj, k, v)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def remover_parametro_solo(self, param_id: uuid.UUID, cultura_id: uuid.UUID) -> None:
        obj = await self._get_parametro_solo(param_id, cultura_id)
        await self.session.delete(obj)
