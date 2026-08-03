from uuid import UUID
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from loguru import logger

from core.base_service import BaseService
from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.services.sequencial_service import SequencialService
from core.models.auth import Usuario
from core.models.unidade_produtiva import UnidadeProdutiva
from core.cadastros.propriedades.models import AreaRural
from agricola.cultivos.models import Cultivo, CultivoArea
from agricola.operacoes.models import OperacaoAgricola
from agricola.safras.models import Safra
from agricola.tarefas.models import SafraTarefa
from core.operational_context import (
    validate_deposito_context,
    validate_lote_context,
    validate_safra_in_tenant,
)
from operacional.models.estoque import (
    Deposito, EstoqueMovimento, SaldoEstoque,
    LoteEstoque, RequisicaoMaterial, ItemRequisicao, ReservaEstoque, EstoqueLocalizacao,
    RequisicaoConfirmacao,
)
from operacional.models.compras import Fornecedor, PedidoCompra
from core.cadastros.models import ProdutoCatalogo
from operacional.schemas.estoque import (
    DepositoCreate, DepositoUpdate,
    EntradaEstoqueRequest,
    SaidaEstoqueRequest,
    AjusteEstoqueRequest,
    AjusteMovimentoRequest,
    TransferenciaEstoqueRequest,
    SaldoResponse,
    AlertaEstoqueItem,
    LoteCreate, LoteUpdate,
    RequisicaoCreate, RequisicaoAprovarRequest, RequisicaoEntregarRequest,
    ConfirmarRetiradaRequest, ConfirmarDevolucaoRequest, ItemEntregaUpdate,
    ReservaCreate, ReservaCancelarRequest, ReservaConsumirRequest,
    AuditoriaMovimentacaoResponse,
    EstoqueLocalizacaoCreate, EstoqueLocalizacaoUpdate, EstoqueLocalizacaoResponse,
)
from operacional.services.estoque_ledger import registrar_ledger_estoque
from financeiro.models.lancamento import LancamentoFinanceiro


class EstoqueService(BaseService[SaldoEstoque]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(SaldoEstoque, session, tenant_id)

    async def _get_produto(self, produto_id: UUID) -> ProdutoCatalogo | None:
        stmt = select(ProdutoCatalogo).where(
            ProdutoCatalogo.id == produto_id,
            or_(ProdutoCatalogo.tenant_id.is_(None), ProdutoCatalogo.tenant_id == self.tenant_id),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _get_produto_or_fail(self, produto_id: UUID) -> ProdutoCatalogo:
        produto = await self._get_produto(produto_id)
        if not produto:
            logger.warning(
                "multi_up_tenant_mismatch",
                resource="produto_estoque",
                tenant_id=str(self.tenant_id),
                produto_id=str(produto_id),
            )
            raise BusinessRuleError("Produto não localizado ou inacessível para o tenant.")
        return produto

    async def _resolver_custo_unitario_contextual(
        self,
        produto_id: UUID,
        deposito_id: UUID | None = None,
        lote_id: UUID | None = None,
    ) -> float | None:
        """
        Resolve custo operacional sem usar Produto.preco_medio como fonte primária.

        Ordem de preferência:
        1. lote explícito informado
        2. média ponderada dos lotes ativos do contexto
        3. custo médio dos movimentos já registrados no contexto
        4. snapshot legado do produto
        """
        if lote_id is not None:
            lote = await validate_lote_context(self.session, tenant_id=self.tenant_id, lote_id=lote_id)
            if lote and lote.custo_unitario is not None and float(lote.custo_unitario) > 0:
                return float(lote.custo_unitario)

        lotes_stmt = (
            select(LoteEstoque)
            .join(Deposito, Deposito.id == LoteEstoque.deposito_id)
            .where(
                LoteEstoque.produto_id == produto_id,
                LoteEstoque.status == "ATIVO",
                LoteEstoque.quantidade_atual > 0,
                Deposito.tenant_id == self.tenant_id,
            )
        )
        if deposito_id is not None:
            lotes_stmt = lotes_stmt.where(LoteEstoque.deposito_id == deposito_id)

        lotes = list((await self.session.execute(lotes_stmt)).scalars().all())
        quantidade_total = sum(float(l.quantidade_atual or 0.0) for l in lotes)
        if quantidade_total > 0:
            custo_total = sum(
                float(l.quantidade_atual or 0.0) * float(l.custo_unitario or 0.0)
                for l in lotes
            )
            if custo_total > 0:
                return round(custo_total / quantidade_total, 4)

        mov_stmt = select(func.avg(EstoqueMovimento.custo_unitario)).where(
            EstoqueMovimento.tenant_id == self.tenant_id,
            EstoqueMovimento.produto_id == produto_id,
            EstoqueMovimento.custo_unitario.is_not(None),
        )
        if deposito_id is not None:
            mov_stmt = mov_stmt.where(EstoqueMovimento.deposito_id == deposito_id)
        mov_avg = (await self.session.execute(mov_stmt)).scalar_one_or_none()
        if mov_avg is not None and float(mov_avg) > 0:
            return float(mov_avg)

        produto = await self._get_produto(produto_id)
        if produto and produto.preco_medio is not None and float(produto.preco_medio) > 0:
            return float(produto.preco_medio)
        return None

    async def _resolver_estoque_minimo_contextual(
        self,
        saldo: SaldoEstoque,
        produto: ProdutoCatalogo | None = None,
    ) -> float | None:
        """
        Resolve o estoque mínimo operacional com prioridade para o contexto do saldo.

        Ordem de preferência:
        1. SaldoEstoque.estoque_minimo
        2. snapshot legado em ProdutoCatalogo.estoque_minimo
        """
        if saldo.estoque_minimo is not None:
            return float(saldo.estoque_minimo)

        if produto and produto.estoque_minimo is not None and float(produto.estoque_minimo) > 0:
            return float(produto.estoque_minimo)

        return None

    async def _validar_unidade_produtiva(self, unidade_produtiva_id: UUID) -> None:
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
            logger.warning(
                "multi_up_context_invalid",
                reason="estoque_unidade_produtiva_tenant_mismatch",
                tenant_id=str(self.tenant_id),
                unidade_produtiva_id=str(unidade_produtiva_id),
            )
            raise BusinessRuleError("Unidade produtiva não localizada ou inacessível para o tenant.")

    # ── Categorias ────────────────────────────────────────────────────────

    # ── Depósitos ─────────────────────────────────────────────────────────

    async def criar_deposito(self, data: DepositoCreate) -> Deposito:
        await self._validar_unidade_produtiva(data.unidade_produtiva_id)
        dep = Deposito(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=data.unidade_produtiva_id,
            nome=data.nome,
            tipo=data.tipo,
            localizacao_desc=data.localizacao_desc,
        )
        self.session.add(dep)
        await self.session.flush()
        await self.session.refresh(dep)
        return dep

    async def atualizar_deposito(self, deposito_id: UUID, data: DepositoUpdate) -> Deposito:
        stmt = select(Deposito).where(
            Deposito.id == deposito_id, Deposito.tenant_id == self.tenant_id
        )
        dep = (await self.session.execute(stmt)).scalars().first()
        if not dep:
            raise EntityNotFoundError(f"Depósito {deposito_id} não encontrado.")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(dep, field, value)
        self.session.add(dep)
        await self.session.flush()
        await self.session.refresh(dep)
        return dep

    async def listar_depositos(self, unidade_produtiva_id: UUID | None = None) -> list[Deposito]:
        stmt = select(Deposito).where(Deposito.tenant_id == self.tenant_id)
        if unidade_produtiva_id:
            stmt = stmt.where(Deposito.unidade_produtiva_id == unidade_produtiva_id)
        return list((await self.session.execute(stmt)).scalars().all())

    # ── Saldos ────────────────────────────────────────────────────────────

    async def _get_ou_criar_saldo(self, deposito_id: UUID, produto_id: UUID) -> SaldoEstoque:
        await validate_deposito_context(self.session, tenant_id=self.tenant_id, deposito_id=deposito_id)
        await self._get_produto_or_fail(produto_id)
        stmt = select(SaldoEstoque).where(
            SaldoEstoque.deposito_id == deposito_id,
            SaldoEstoque.produto_id == produto_id,
        )
        saldo = (await self.session.execute(stmt)).scalars().first()
        if not saldo:
            saldo = SaldoEstoque(deposito_id=deposito_id, produto_id=produto_id, quantidade_atual=0.0)
            self.session.add(saldo)
            await self.session.flush()
        return saldo

    async def listar_saldos(
        self, 
        unidade_produtiva_id: UUID | None = None,
        produto_id: UUID | None = None,
        deposito_id: UUID | None = None
    ) -> list[SaldoResponse]:
        dep_stmt = select(Deposito).where(Deposito.tenant_id == self.tenant_id, Deposito.ativo == True)
        if unidade_produtiva_id:
            dep_stmt = dep_stmt.where(Deposito.unidade_produtiva_id == unidade_produtiva_id)
        if deposito_id:
            dep_stmt = dep_stmt.where(Deposito.id == deposito_id)
            
        depositos = {d.id: d for d in (await self.session.execute(dep_stmt)).scalars().all()}

        prod_stmt = select(ProdutoCatalogo).where(
            or_(ProdutoCatalogo.tenant_id.is_(None), ProdutoCatalogo.tenant_id == self.tenant_id),
            ProdutoCatalogo.ativo == True,
        )
        if produto_id:
            prod_stmt = prod_stmt.where(ProdutoCatalogo.id == produto_id)
        produtos = {p.id: p for p in (await self.session.execute(prod_stmt)).scalars().all()}

        if not depositos:
            return []

        saldo_stmt = select(SaldoEstoque).where(
            SaldoEstoque.deposito_id.in_(list(depositos.keys()))
        )
        if produto_id:
            saldo_stmt = saldo_stmt.where(SaldoEstoque.produto_id == produto_id)
            
        saldos = (await self.session.execute(saldo_stmt)).scalars().all()

        result = []
        for s in saldos:
            produto = produtos.get(s.produto_id)
            estoque_minimo = await self._resolver_estoque_minimo_contextual(s, produto)
            disponivel = max(0.0, s.quantidade_atual - s.quantidade_reservada)
            result.append(
                SaldoResponse(
                    id=s.id,
                    deposito_id=s.deposito_id,
                    produto_id=s.produto_id,
                    produto_nome=produto.nome if produto else "N/A",
                    deposito_nome=depositos.get(s.deposito_id).nome if depositos.get(s.deposito_id) else "N/A",
                    quantidade_atual=s.quantidade_atual,
                    quantidade_reservada=s.quantidade_reservada,
                    quantidade_disponivel=disponivel,
                    preco_medio=float(s.custo_medio) if s.custo_medio is not None else (produto.preco_medio if produto else 0.0),
                    unidade_medida=produto.unidade_medida if produto else "",
                    estoque_minimo=estoque_minimo,
                    estoque_maximo=s.estoque_maximo,
                    abaixo_minimo=estoque_minimo is not None and disponivel <= estoque_minimo,
                    acima_maximo=s.estoque_maximo is not None and disponivel > s.estoque_maximo,
                    ultima_atualizacao=s.ultima_atualizacao,
                )
            )
        return result

    async def atualizar_estoque_minimo(self, saldo_id: UUID, estoque_minimo: float) -> SaldoEstoque:
        stmt = select(SaldoEstoque).where(SaldoEstoque.id == saldo_id)
        saldo = (await self.session.execute(stmt)).scalars().first()
        if not saldo:
            raise EntityNotFoundError("Saldo não encontrado.")
        await validate_deposito_context(self.session, tenant_id=self.tenant_id, deposito_id=saldo.deposito_id)
        saldo.estoque_minimo = estoque_minimo
        self.session.add(saldo)
        await self.session.flush()

        # Verificar se já está abaixo do novo mínimo
        await self._verificar_e_notificar_estoque_baixo(saldo)

        return saldo

    async def atualizar_estoque_maximo(self, saldo_id: UUID, estoque_maximo: float) -> SaldoEstoque:
        stmt = select(SaldoEstoque).where(SaldoEstoque.id == saldo_id)
        saldo = (await self.session.execute(stmt)).scalars().first()
        if not saldo:
            raise EntityNotFoundError("Saldo não encontrado.")
        await validate_deposito_context(self.session, tenant_id=self.tenant_id, deposito_id=saldo.deposito_id)
        saldo.estoque_maximo = estoque_maximo
        self.session.add(saldo)
        await self.session.flush()
        return saldo

    # ── Localização física ───────────────────────────────────────────────────

    async def listar_localizacoes(
        self, produto_id: UUID | None = None, deposito_id: UUID | None = None,
    ) -> list[EstoqueLocalizacaoResponse]:
        stmt = select(EstoqueLocalizacao).where(EstoqueLocalizacao.tenant_id == self.tenant_id)
        if produto_id:
            stmt = stmt.where(EstoqueLocalizacao.produto_id == produto_id)
        if deposito_id:
            stmt = stmt.where(EstoqueLocalizacao.deposito_id == deposito_id)
        locs = (await self.session.execute(stmt)).scalars().all()
        if not locs:
            return []

        produtos = {p.id: p for p in (await self.session.execute(
            select(ProdutoCatalogo).where(ProdutoCatalogo.id.in_({l.produto_id for l in locs}))
        )).scalars().all()}
        depositos = {d.id: d for d in (await self.session.execute(
            select(Deposito).where(Deposito.id.in_({l.deposito_id for l in locs}))
        )).scalars().all()}

        return [
            EstoqueLocalizacaoResponse(
                id=l.id, deposito_id=l.deposito_id, produto_id=l.produto_id,
                produto_nome=produtos.get(l.produto_id).nome if produtos.get(l.produto_id) else None,
                deposito_nome=depositos.get(l.deposito_id).nome if depositos.get(l.deposito_id) else None,
                corredor=l.corredor, prateleira=l.prateleira, posicao=l.posicao,
                codigo_localizacao=l.codigo_localizacao, observacao_livre=l.observacao_livre,
                quantidade=l.quantidade,
            )
            for l in locs
        ]

    async def criar_localizacao(self, data: EstoqueLocalizacaoCreate) -> EstoqueLocalizacao:
        await validate_deposito_context(self.session, tenant_id=self.tenant_id, deposito_id=data.deposito_id)
        await self._get_produto_or_fail(data.produto_id)
        obj = EstoqueLocalizacao(tenant_id=self.tenant_id, **data.model_dump())
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def _get_localizacao(self, localizacao_id: UUID) -> EstoqueLocalizacao:
        obj = (await self.session.execute(
            select(EstoqueLocalizacao).where(
                EstoqueLocalizacao.id == localizacao_id, EstoqueLocalizacao.tenant_id == self.tenant_id
            )
        )).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Localização não encontrada.")
        return obj

    async def atualizar_localizacao(self, localizacao_id: UUID, data: EstoqueLocalizacaoUpdate) -> EstoqueLocalizacao:
        obj = await self._get_localizacao(localizacao_id)
        for k, v in data.model_dump(exclude_none=True).items():
            setattr(obj, k, v)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def remover_localizacao(self, localizacao_id: UUID) -> None:
        obj = await self._get_localizacao(localizacao_id)
        await self.session.delete(obj)

    async def listar_alertas_reposicao(self) -> list[AlertaEstoqueItem]:
        saldos = await self.listar_saldos()
        alertas = []
        for s in saldos:
            minimo = s.estoque_minimo or 0
            if minimo > 0 and s.abaixo_minimo:
                # Regra: repor até 20% acima do mínimo para dar margem operacional
                sugerido = (minimo * 1.2) - s.quantidade_atual
                alertas.append(AlertaEstoqueItem(
                    id=s.id,
                    produto_id=s.produto_id,
                    deposito_id=s.deposito_id,
                    produto_nome=s.produto_nome,
                    deposito_nome=s.deposito_nome,
                    quantidade_atual=s.quantidade_atual,
                    estoque_minimo=minimo,
                    unidade_medida=s.unidade_medida,
                    quantidade_sugerida=round(max(0, sugerido), 2)
                ))
        return alertas

    async def _verificar_e_notificar_estoque_baixo(self, saldo: SaldoEstoque):
        from core.cadastros.models import ProdutoCatalogo

        produto = await self._get_produto(saldo.produto_id)
        estoque_minimo = await self._resolver_estoque_minimo_contextual(saldo, produto)
        if estoque_minimo is not None:
            disponivel = max(0.0, saldo.quantidade_atual - saldo.quantidade_reservada)
            if disponivel <= estoque_minimo:
                from notificacoes.service import NotificacaoService
                from notificacoes.schemas import NotificacaoCreate

                # Buscar nomes para a mensagem
                dep_stmt = select(Deposito.nome).where(Deposito.id == saldo.deposito_id)
                prod_stmt = select(ProdutoCatalogo.nome).where(ProdutoCatalogo.id == saldo.produto_id)

                dep_nome = (await self.session.execute(dep_stmt)).scalar() or "N/A"
                prod_nome = (await self.session.execute(prod_stmt)).scalar() or "N/A"

                notif_svc = NotificacaoService(self.session, self.tenant_id)
                await notif_svc.criar_e_push(NotificacaoCreate(
                    tipo="ESTOQUE_REPOSICAO",
                    titulo="Estoque Baixo",
                    mensagem=f"O item {prod_nome} atingiu o nível crítico no depósito {dep_nome}. Saldo: {disponivel:.2f}",
                    nivel="WARNING",
                    origem="estoque_saldo",
                    origem_id=str(saldo.id)
                ))

    # ── Lotes ─────────────────────────────────────────────────────────────

    async def criar_lote(self, data: LoteCreate) -> LoteEstoque:
        await validate_deposito_context(self.session, tenant_id=self.tenant_id, deposito_id=data.deposito_id)
        await self._get_produto_or_fail(data.produto_id)
        lote = LoteEstoque(
            produto_id=data.produto_id,
            deposito_id=data.deposito_id,
            numero_lote=data.numero_lote,
            data_fabricacao=data.data_fabricacao,
            data_validade=data.data_validade,
            quantidade_inicial=data.quantidade_inicial,
            quantidade_atual=data.quantidade_inicial,
            custo_unitario=data.custo_unitario,
            nota_fiscal_ref=data.nota_fiscal_ref,
            qualidade_laudo_id=data.qualidade_laudo_id,
            qualidade_status=data.qualidade_status,
            peso_desconto_qualidade_kg=data.peso_desconto_qualidade_kg,
            metadata_json=data.metadata_json,
            status="ATIVO",
        )
        self.session.add(lote)
        await self.session.flush()
        await self.session.refresh(lote)
        return lote

    async def atualizar_lote(self, lote_id: UUID, data: LoteUpdate) -> LoteEstoque:
        lote = await validate_lote_context(self.session, tenant_id=self.tenant_id, lote_id=lote_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(lote, field, value)
        self.session.add(lote)
        await self.session.flush()
        await self.session.refresh(lote)
        return lote

    async def listar_lotes(
        self,
        produto_id: UUID | None = None,
        deposito_id: UUID | None = None,
        vencendo_em_dias: int | None = None,
        apenas_ativos: bool = True,
    ) -> list[LoteEstoque]:
        # Garante acesso apenas a depósitos do tenant
        dep_stmt = select(Deposito.id).where(Deposito.tenant_id == self.tenant_id)
        dep_ids = set((await self.session.execute(dep_stmt)).scalars().all())

        stmt = select(LoteEstoque).where(LoteEstoque.deposito_id.in_(dep_ids))
        if produto_id:
            stmt = stmt.where(LoteEstoque.produto_id == produto_id)
        if deposito_id:
            stmt = stmt.where(LoteEstoque.deposito_id == deposito_id)
        if apenas_ativos:
            stmt = stmt.where(LoteEstoque.status == "ATIVO")
        if vencendo_em_dias is not None:
            from datetime import timedelta
            limite = date.today() + timedelta(days=vencendo_em_dias)
            stmt = stmt.where(
                LoteEstoque.data_validade != None,
                LoteEstoque.data_validade <= limite,
            )
        stmt = stmt.order_by(LoteEstoque.data_validade.asc().nullslast())
        lotes = list((await self.session.execute(stmt)).scalars().all())

        # Marca lotes ESGOTADOS que foram zerados por estorno de recebimento
        # (AJUSTE com ajuste_de preenchido), para diferenciar de esgotamento
        # por consumo normal na UI.
        ids_esgotados = [l.id for l in lotes if l.status == "ESGOTADO"]
        lotes_estornados: set = set()
        if ids_esgotados:
            stmt_estorno = select(EstoqueMovimento.lote_id).where(
                EstoqueMovimento.lote_id.in_(ids_esgotados),
                EstoqueMovimento.origem == "AJUSTE",
                EstoqueMovimento.ajuste_de.isnot(None),
            ).distinct()
            lotes_estornados = {row[0] for row in (await self.session.execute(stmt_estorno)).all()}
        for lote in lotes:
            lote.esgotado_por_estorno = lote.id in lotes_estornados

        return lotes

    async def _atualizar_status_lotes_vencidos(self) -> None:
        """Marca automaticamente lotes vencidos."""
        stmt = select(LoteEstoque).where(
            LoteEstoque.status == "ATIVO",
            LoteEstoque.data_validade != None,
            LoteEstoque.data_validade < date.today(),
        )
        lotes = (await self.session.execute(stmt)).scalars().all()
        for lote in lotes:
            lote.status = "VENCIDO"

    # ── Movimentações ─────────────────────────────────────────────────────

    async def _registrar_movimento(
        self,
        deposito_id: UUID,
        produto_id: UUID,
        tipo: str,
        quantidade: float,
        custo_unitario: float | None = None,
        motivo: str | None = None,
        origem_id: UUID | None = None,
        origem_tipo: str | None = None,
        lote_id: UUID | None = None,
        production_unit_id: UUID | None = None,
        fornecedor_id: UUID | None = None,
        custo_medio_anterior: float | None = None,
        custo_medio_resultante: float | None = None,
    ) -> EstoqueMovimento:
        await validate_deposito_context(self.session, tenant_id=self.tenant_id, deposito_id=deposito_id)
        await self._get_produto_or_fail(produto_id)
        if lote_id:
            await validate_lote_context(
                self.session,
                tenant_id=self.tenant_id,
                lote_id=lote_id,
                produto_id=produto_id,
                deposito_id=deposito_id,
            )
        return await registrar_ledger_estoque(
            self.session,
            tenant_id=self.tenant_id,
            produto_id=produto_id,
            deposito_id=deposito_id,
            lote_id=lote_id,
            tipo_movimento=tipo,
            quantidade=quantidade,
            custo_unitario=custo_unitario,
            origem=origem_tipo or "MANUAL",
            origem_id=origem_id,
            production_unit_id=production_unit_id,
            fornecedor_id=fornecedor_id,
            observacoes=motivo,
            custo_medio_anterior=custo_medio_anterior,
            custo_medio_resultante=custo_medio_resultante,
        )

    async def _descontar_lote(self, lote_id: UUID, quantidade: float) -> LoteEstoque:
        """Desconta quantidade de um lote e atualiza status se esgotado."""
        lote = await validate_lote_context(self.session, tenant_id=self.tenant_id, lote_id=lote_id)
        if lote.quantidade_atual < quantidade:
            raise BusinessRuleError(
                f"Saldo insuficiente no lote {lote.numero_lote}. "
                f"Disponível: {lote.quantidade_atual}, solicitado: {quantidade}"
            )
        lote.quantidade_atual -= quantidade
        if lote.quantidade_atual <= 0:
            lote.status = "ESGOTADO"
        return lote

    async def registrar_entrada(self, data: EntradaEstoqueRequest) -> EstoqueMovimento:
        await validate_deposito_context(self.session, tenant_id=self.tenant_id, deposito_id=data.deposito_id)
        await self._get_produto_or_fail(data.produto_id)
        stmt_fornecedor = select(Fornecedor).where(
            Fornecedor.id == data.fornecedor_id, Fornecedor.tenant_id == self.tenant_id
        )
        fornecedor = (await self.session.execute(stmt_fornecedor)).scalars().first()
        if not fornecedor:
            raise BusinessRuleError("Fornecedor informado não encontrado.")
        if data.lote_id:
            await validate_lote_context(
                self.session,
                tenant_id=self.tenant_id,
                lote_id=data.lote_id,
                produto_id=data.produto_id,
                deposito_id=data.deposito_id,
            )

        saldo = await self._get_ou_criar_saldo(data.deposito_id, data.produto_id)
        qtd_antes = float(saldo.quantidade_atual)
        custo_medio_antes = float(saldo.custo_medio) if saldo.custo_medio is not None else None

        custo_unitario = (
            data.custo_unitario
            if data.custo_unitario and data.custo_unitario > 0
            else await self._resolver_custo_unitario_contextual(
                data.produto_id,
                deposito_id=data.deposito_id,
                lote_id=data.lote_id,
            )
        )

        # CMPM (Custo Médio Ponderado Móvel/Kardex): só entrada recalcula o
        # custo médio. Se não havia saldo/custo anterior, o custo médio novo
        # é o próprio custo da entrada (equivale a "resetar" naturalmente).
        if qtd_antes <= 0 or custo_medio_antes is None:
            custo_medio_novo = custo_unitario
        else:
            custo_medio_novo = (
                (qtd_antes * custo_medio_antes) + (data.quantidade * custo_unitario)
            ) / (qtd_antes + data.quantidade)
        saldo.custo_medio = custo_medio_novo
        saldo.quantidade_atual += data.quantidade

        # Atualiza saldo do lote se informado
        if data.lote_id:
            stmt_lote = select(LoteEstoque).where(LoteEstoque.id == data.lote_id)
            lote = (await self.session.execute(stmt_lote)).scalars().first()
            if lote:
                lote.quantidade_atual += data.quantidade

        mov = await self._registrar_movimento(
            deposito_id=data.deposito_id,
            produto_id=data.produto_id,
            tipo="ENTRADA",
            quantidade=data.quantidade,
            custo_unitario=custo_unitario,
            motivo=data.motivo or "Entrada manual",
            origem_id=data.origem_id,
            origem_tipo=data.origem_tipo or "MANUAL",
            lote_id=data.lote_id,
            fornecedor_id=data.fornecedor_id,
            custo_medio_anterior=custo_medio_antes,
            custo_medio_resultante=custo_medio_novo,
        )
        await self.session.flush()
        await self.session.refresh(mov)
        await self._verificar_e_notificar_estoque_baixo(saldo)
        return mov

    async def registrar_saldo_inicial_implantacao(
        self,
        *,
        produto_id: UUID,
        deposito_id: UUID,
        quantidade: float,
        origem_id: UUID,
        observacao: str | None = None,
        custo_unitario: float | None = None,
        unidade_produtiva_id: UUID | None = None,
        numero_lote_legado: str | None = None,
        validade_legado: date | None = None,
    ) -> EstoqueMovimento:
        if quantidade <= 0:
            raise BusinessRuleError("Saldo inicial exige quantidade maior que zero.")
        if unidade_produtiva_id is not None:
            await validate_deposito_context(
                self.session,
                tenant_id=self.tenant_id,
                deposito_id=deposito_id,
                expected_unidade_produtiva_id=unidade_produtiva_id,
            )
        else:
            await validate_deposito_context(self.session, tenant_id=self.tenant_id, deposito_id=deposito_id)
        await self._get_produto_or_fail(produto_id)

        stmt_dup = select(EstoqueMovimento.id).where(
            EstoqueMovimento.tenant_id == self.tenant_id,
            EstoqueMovimento.produto_id == produto_id,
            EstoqueMovimento.deposito_id == deposito_id,
            EstoqueMovimento.tipo_movimento == "SALDO_INICIAL",
        ).limit(1)
        if (await self.session.execute(stmt_dup)).scalar_one_or_none():
            raise BusinessRuleError("Ja existe SALDO_INICIAL para este produto e deposito.")

        saldo = await self._get_ou_criar_saldo(deposito_id, produto_id)
        saldo.quantidade_atual += quantidade

        observacao_parts = [observacao] if observacao else []
        if numero_lote_legado:
            observacao_parts.append(f"Lote legado: {numero_lote_legado}")
        if validade_legado:
            observacao_parts.append(f"Validade legado: {validade_legado.isoformat()}")
        observacao_final = " | ".join(part for part in observacao_parts if part) or "Saldo inicial por implantacao assistida"

        try:
            mov = await registrar_ledger_estoque(
                self.session,
                tenant_id=self.tenant_id,
                produto_id=produto_id,
                deposito_id=deposito_id,
                tipo_movimento="SALDO_INICIAL",
                quantidade=quantidade,
                custo_unitario=custo_unitario,
                origem="IMPLANTACAO",
                origem_id=origem_id,
                observacoes=observacao_final,
                numero_lote_legado=numero_lote_legado,
            )
            await self.session.flush()
            await self.session.refresh(mov)
            return mov
        except IntegrityError as exc:
            raise BusinessRuleError("Nao foi possivel gravar SALDO_INICIAL. Verifique duplicidade da implantacao.") from exc

    async def registrar_saida_insumo(
        self,
        produto_id: UUID,
        quantidade: float,
        unidade_produtiva_id: UUID,
        origem_id: UUID,
        origem_tipo: str = "OPERACAO_AGRICOLA",
        motivo: str = "Uso em operação agrícola",
        deposito_id: UUID | None = None,
        production_unit_id: UUID | None = None,
    ) -> EstoqueMovimento:
        await self._validar_unidade_produtiva(unidade_produtiva_id)
        await self._get_produto_or_fail(produto_id)
        if deposito_id:
            await validate_deposito_context(
                self.session,
                tenant_id=self.tenant_id,
                deposito_id=deposito_id,
                expected_unidade_produtiva_id=unidade_produtiva_id,
            )
            stmt_saldo = select(SaldoEstoque).where(
                SaldoEstoque.produto_id == produto_id,
                SaldoEstoque.deposito_id == deposito_id,
            )
            saldos = list((await self.session.execute(stmt_saldo)).scalars().all())
        else:
            stmt_deps = select(Deposito.id).where(
                Deposito.tenant_id == self.tenant_id,
                Deposito.unidade_produtiva_id == unidade_produtiva_id,
                Deposito.ativo == True,
            )
            dep_ids = (await self.session.execute(stmt_deps)).scalars().all()
            if not dep_ids:
                raise BusinessRuleError(f"Nenhum depósito ativo na fazenda {unidade_produtiva_id}.")
            stmt_saldo = select(SaldoEstoque).where(
                SaldoEstoque.produto_id == produto_id,
                SaldoEstoque.deposito_id.in_(dep_ids),
            ).order_by(SaldoEstoque.quantidade_atual.desc())
            saldos = list((await self.session.execute(stmt_saldo)).scalars().all())

        if not saldos:
            raise BusinessRuleError(f"Produto {produto_id} sem saldo nos depósitos.")

        saldo_sel = next((s for s in saldos if s.quantidade_atual >= quantidade), None)
        if not saldo_sel:
            total = sum(s.quantidade_atual for s in saldos)
            raise BusinessRuleError(f"Saldo insuficiente. Necessário: {quantidade}, disponível: {total}")

        saldo_sel.quantidade_atual -= quantidade
        prod = await self._get_produto(produto_id)
        custo_unitario = await self._resolver_custo_unitario_contextual(
            produto_id,
            deposito_id=saldo_sel.deposito_id,
        )
        mov = await self._registrar_movimento(
            deposito_id=saldo_sel.deposito_id,
            produto_id=produto_id,
            tipo="SAIDA",
            quantidade=quantidade,
            custo_unitario=custo_unitario,
            motivo=motivo,
            origem_id=origem_id,
            origem_tipo=origem_tipo,
            production_unit_id=production_unit_id,
        )
        await self.session.flush()
        await self.session.refresh(mov)
        await self._verificar_e_notificar_estoque_baixo(saldo_sel)
        return mov

    async def registrar_saida_insumo_por_nome(
        self,
        nome_insumo: str,
        quantidade: float,
        unidade_produtiva_id: UUID,
        origem_id: UUID,
        origem_tipo: str = "OPERACAO_AGRICOLA",
        motivo: str = "Uso em operação agrícola",
        production_unit_id: UUID | None = None,
    ) -> EstoqueMovimento:
        """Busca o produto pelo nome e registra a saída."""
        stmt = select(ProdutoCatalogo).where(
            or_(ProdutoCatalogo.tenant_id.is_(None), ProdutoCatalogo.tenant_id == self.tenant_id),
            ProdutoCatalogo.nome.ilike(f"%{nome_insumo}%"),
            ProdutoCatalogo.ativo == True
        ).limit(1)
        prod = (await self.session.execute(stmt)).scalars().first()
        
        if not prod:
            raise EntityNotFoundError(f"Produto de estoque '{nome_insumo}' não encontrado para baixa.")

        return await self.registrar_saida_insumo(
            produto_id=prod.id,
            quantidade=quantidade,
            unidade_produtiva_id=unidade_produtiva_id,
            origem_id=origem_id,
            origem_tipo=origem_tipo,
            motivo=motivo,
            production_unit_id=production_unit_id,
        )

    async def _criar_lancamento_insumo(
        self,
        safra_id: UUID,
        nome_produto: str,
        custo_unitario: float,
        quantidade: float,
        movimentacao_id: UUID | None = None,
    ) -> None:
        valor = custo_unitario * quantidade
        if valor <= 0:
            return

        # Compatibilidade legada. Não usar LancamentoFinanceiro de estoque como
        # fonte canônica de DRE operacional nova; novos fluxos devem apropriar
        # custo em CostAllocation pela porta operacional oficial.
        # Idempotência: não duplicar se já existe lançamento para este movimento
        if movimentacao_id is not None:
            stmt_dup = select(LancamentoFinanceiro.id).where(
                LancamentoFinanceiro.tenant_id == self.tenant_id,
                LancamentoFinanceiro.origem == "ESTOQUE",
                LancamentoFinanceiro.origem_id == movimentacao_id,
            ).limit(1)
            if (await self.session.execute(stmt_dup)).first():
                return

        lancamento = LancamentoFinanceiro(
            tenant_id=self.tenant_id,
            safra_id=safra_id,
            descricao=f"Uso de insumo: {nome_produto}",
            valor=valor,
            data=date.today(),
            tipo="CUSTO",
            categoria="INSUMOS",
            origem="ESTOQUE",
            origem_id=movimentacao_id,
        )
        self.session.add(lancamento)

    async def _resolver_safra_contexto_requisicao(self, requisicao: RequisicaoMaterial) -> UUID | None:
        origem_tipo = (requisicao.origem_tipo or "").upper()
        origem_id = requisicao.origem_id

        if origem_id is not None and origem_tipo in {"ORDEM_SERVICO", "OPERACAO_AGRICOLA"}:
            stmt_operacao = (
                select(OperacaoAgricola.safra_id)
                .where(
                    OperacaoAgricola.id == origem_id,
                    OperacaoAgricola.tenant_id == self.tenant_id,
                )
                .limit(1)
            )
            safra_id = (await self.session.execute(stmt_operacao)).scalar_one_or_none()
            if safra_id is not None:
                return safra_id

            stmt_tarefa = (
                select(SafraTarefa.safra_id)
                .where(
                    SafraTarefa.tenant_id == self.tenant_id,
                    or_(
                        SafraTarefa.id == origem_id,
                        SafraTarefa.operacao_id == origem_id,
                    ),
                )
                .limit(1)
            )
            safra_id = (await self.session.execute(stmt_tarefa)).scalar_one_or_none()
            if safra_id is not None:
                return safra_id

        stmt_safra = (
            select(Safra.id)
            .join(Cultivo, Cultivo.safra_id == Safra.id)
            .join(CultivoArea, CultivoArea.cultivo_id == Cultivo.id)
            .join(AreaRural, AreaRural.id == CultivoArea.area_id)
            .where(
                Safra.tenant_id == self.tenant_id,
                AreaRural.unidade_produtiva_id == requisicao.unidade_produtiva_id,
                Safra.status.notin_(["ENCERRADA", "CANCELADA"]),
            )
            .order_by(Safra.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt_safra)).scalar_one_or_none()

    async def registrar_saida(self, data: SaidaEstoqueRequest) -> EstoqueMovimento:
        await self._get_produto_or_fail(data.produto_id)
        if data.safra_id:
            await validate_safra_in_tenant(self.session, tenant_id=self.tenant_id, safra_id=data.safra_id)
        if data.deposito_id:
            await validate_deposito_context(self.session, tenant_id=self.tenant_id, deposito_id=data.deposito_id)
            if data.lote_id:
                await validate_lote_context(
                    self.session,
                    tenant_id=self.tenant_id,
                    lote_id=data.lote_id,
                    produto_id=data.produto_id,
                    deposito_id=data.deposito_id,
                )
            stmt = select(SaldoEstoque).where(
                SaldoEstoque.produto_id == data.produto_id,
                SaldoEstoque.deposito_id == data.deposito_id,
            )
            saldo = (await self.session.execute(stmt)).scalars().first()
            if not saldo:
                raise BusinessRuleError("Saldo não encontrado para o depósito selecionado.")
            disponivel = saldo.quantidade_atual - saldo.quantidade_reservada
            if disponivel < data.quantidade:
                raise BusinessRuleError(
                    f"Saldo disponível insuficiente. Disponível: {disponivel:.3f}, Necessário: {data.quantidade:.3f}"
                )
            saldo.quantidade_atual -= data.quantidade
            if data.lote_id:
                await self._descontar_lote(data.lote_id, data.quantidade)
            prod = await self._get_produto(data.produto_id)
            custo_unit = await self._resolver_custo_unitario_contextual(
                data.produto_id,
                deposito_id=data.deposito_id,
                lote_id=data.lote_id,
            )
            # Saída consome ao custo médio vigente — não recalcula o CMPM.
            custo_medio_atual = float(saldo.custo_medio) if saldo.custo_medio is not None else None
            mov = await self._registrar_movimento(
                deposito_id=data.deposito_id, produto_id=data.produto_id,
                tipo="SAIDA", quantidade=data.quantidade,
                custo_unitario=custo_unit,
                motivo=data.motivo, origem_id=data.origem_id,
                origem_tipo=data.origem_tipo or "MANUAL",
                lote_id=data.lote_id,
                custo_medio_anterior=custo_medio_atual,
                custo_medio_resultante=custo_medio_atual,
            )
            if data.safra_id and custo_unit and custo_unit > 0:
                await self._criar_lancamento_insumo(
                    safra_id=data.safra_id,
                    nome_produto=prod.nome if prod else str(data.produto_id),
                    custo_unitario=custo_unit,
                    quantidade=data.quantidade,
                    movimentacao_id=mov.id,
                )
            await self.session.flush()
            await self.session.refresh(mov)
            await self._verificar_e_notificar_estoque_baixo(saldo)
            return mov
        elif data.unidade_produtiva_id:
            mov = await self.registrar_saida_insumo(
                produto_id=data.produto_id, quantidade=data.quantidade,
                unidade_produtiva_id=data.unidade_produtiva_id,
                origem_id=data.origem_id or uuid.uuid4(),
                origem_tipo=data.origem_tipo or "MANUAL",
                motivo=data.motivo or "Saída manual",
            )
            if data.safra_id:
                prod = await self._get_produto(data.produto_id)
                custo_unit = float(mov.custo_unitario or 0.0)
                if custo_unit and custo_unit > 0:
                    await self._criar_lancamento_insumo(
                        safra_id=data.safra_id,
                        nome_produto=prod.nome if prod else str(data.produto_id),
                        custo_unitario=custo_unit,
                        quantidade=data.quantidade,
                        movimentacao_id=mov.id,
                    )
            return mov
        raise BusinessRuleError("Informe deposito_id ou unidade_produtiva_id.")

    async def registrar_ajuste(self, data: AjusteEstoqueRequest) -> EstoqueMovimento:
        saldo = await self._get_ou_criar_saldo(data.deposito_id, data.produto_id)
        diff = data.quantidade_nova - saldo.quantidade_atual
        saldo.quantidade_atual = data.quantidade_nova
        # Ajuste de inventário não tem custo próprio (só corrige contagem) —
        # custo médio permanece o mesmo, seja o ajuste positivo ou negativo.
        custo_medio_atual = float(saldo.custo_medio) if saldo.custo_medio is not None else None
        mov = await self._registrar_movimento(
            deposito_id=data.deposito_id,
            produto_id=data.produto_id,
            tipo="AJUSTE",
            quantidade=diff,
            motivo=data.motivo,
            origem_tipo="AJUSTE",
            custo_medio_anterior=custo_medio_atual,
            custo_medio_resultante=custo_medio_atual,
        )
        await self.session.flush()
        await self.session.refresh(mov)
        await self._verificar_e_notificar_estoque_baixo(saldo)
        return mov

    async def registrar_transferencia(self, data: TransferenciaEstoqueRequest) -> list[EstoqueMovimento]:
        dep_origem = await validate_deposito_context(
            self.session,
            tenant_id=self.tenant_id,
            deposito_id=data.deposito_origem_id,
        )
        dep_destino = await validate_deposito_context(
            self.session,
            tenant_id=self.tenant_id,
            deposito_id=data.deposito_destino_id,
        )
        await self._get_produto_or_fail(data.produto_id)
        if dep_origem.unidade_produtiva_id != dep_destino.unidade_produtiva_id:
            logger.info(
                "multi_up_stock_transfer_between_units",
                tenant_id=str(self.tenant_id),
                deposito_origem_id=str(data.deposito_origem_id),
                deposito_destino_id=str(data.deposito_destino_id),
                unidade_origem_id=str(dep_origem.unidade_produtiva_id),
                unidade_destino_id=str(dep_destino.unidade_produtiva_id),
            )
        stmt = select(SaldoEstoque).where(
            SaldoEstoque.produto_id == data.produto_id,
            SaldoEstoque.deposito_id == data.deposito_origem_id,
        )
        saldo_orig = (await self.session.execute(stmt)).scalars().first()
        if not saldo_orig or saldo_orig.quantidade_atual < data.quantidade:
            raise BusinessRuleError("Saldo insuficiente no depósito de origem.")

        # Origem: saída — custo médio não muda.
        custo_medio_orig = float(saldo_orig.custo_medio) if saldo_orig.custo_medio is not None else None
        saldo_orig.quantidade_atual -= data.quantidade

        saldo_dest = await self._get_ou_criar_saldo(data.deposito_destino_id, data.produto_id)
        qtd_antes_dest = float(saldo_dest.quantidade_atual)
        custo_medio_antes_dest = float(saldo_dest.custo_medio) if saldo_dest.custo_medio is not None else None

        motivo = data.motivo or "Transferência entre depósitos"
        transferencia_id = uuid.uuid4()
        custo_unitario = await self._resolver_custo_unitario_contextual(
            data.produto_id,
            deposito_id=data.deposito_origem_id,
        )

        # Destino: entrada carregando o custo da origem — recalcula o CMPM do depósito destino.
        if qtd_antes_dest <= 0 or custo_medio_antes_dest is None:
            custo_medio_novo_dest = custo_unitario
        else:
            custo_medio_novo_dest = (
                (qtd_antes_dest * custo_medio_antes_dest) + (data.quantidade * (custo_unitario or 0.0))
            ) / (qtd_antes_dest + data.quantidade)
        saldo_dest.custo_medio = custo_medio_novo_dest
        saldo_dest.quantidade_atual += data.quantidade

        mov_saida = await self._registrar_movimento(
            deposito_id=data.deposito_origem_id, produto_id=data.produto_id,
            tipo="TRANSFERENCIA", quantidade=-data.quantidade,
            custo_unitario=custo_unitario,
            motivo=motivo, origem_id=transferencia_id, origem_tipo="TRANSFERENCIA",
            custo_medio_anterior=custo_medio_orig,
            custo_medio_resultante=custo_medio_orig,
        )
        mov_entrada = await self._registrar_movimento(
            deposito_id=data.deposito_destino_id, produto_id=data.produto_id,
            tipo="TRANSFERENCIA", quantidade=data.quantidade,
            custo_unitario=custo_unitario,
            motivo=motivo, origem_id=transferencia_id, origem_tipo="TRANSFERENCIA",
            custo_medio_anterior=custo_medio_antes_dest,
            custo_medio_resultante=custo_medio_novo_dest,
        )
        await self.session.flush()
        await self.session.refresh(mov_saida)
        await self.session.refresh(mov_entrada)
        await self._verificar_e_notificar_estoque_baixo(saldo_orig)
        await self._verificar_e_notificar_estoque_baixo(saldo_dest)
        return [mov_saida, mov_entrada]

    async def listar_movimentacoes(
        self,
        produto_id: UUID | None = None,
        deposito_id: UUID | None = None,
        limit: int = 100,
    ) -> list[dict]:
        stmt = (
            select(
                EstoqueMovimento,
                ProdutoCatalogo.nome.label("produto_nome"),
                Deposito.nome.label("deposito_nome"),
            )
            .join(ProdutoCatalogo, EstoqueMovimento.produto_id == ProdutoCatalogo.id)
            .outerjoin(Deposito, EstoqueMovimento.deposito_id == Deposito.id)
            .where(EstoqueMovimento.tenant_id == self.tenant_id)
            .order_by(EstoqueMovimento.data_movimento.desc())
            .limit(limit)
        )

        if produto_id:
            stmt = stmt.where(EstoqueMovimento.produto_id == produto_id)
        if deposito_id:
            stmt = stmt.where(EstoqueMovimento.deposito_id == deposito_id)

        rows = (await self.session.execute(stmt)).all()
        numeros_pedido = await self._mapear_numeros_pedido_compra([mov for mov, _, _ in rows])
        result = []
        for mov, p_nome, d_nome in rows:
            mov_dict = {c.name: getattr(mov, c.name) for c in mov.__table__.columns}
            mov_dict["produto_nome"] = p_nome
            mov_dict["deposito_nome"] = d_nome
            # Mapeia campos legados para o schema MovimentacaoResponse
            mov_dict["tipo"] = mov.tipo_movimento
            mov_dict["origem_tipo"] = mov.origem
            mov_dict["data_movimentacao"] = mov.data_movimento
            mov_dict["motivo"] = self._formatar_motivo_movimento(mov, numeros_pedido)
            result.append(mov_dict)
        return result

    async def _mapear_numeros_pedido_compra(self, movimentos: list[EstoqueMovimento]) -> dict[UUID, str]:
        pedido_ids = {
            mov.origem_id
            for mov in movimentos
            if self._movimento_referencia_pedido_compra(mov) and mov.origem_id is not None
        }
        if not pedido_ids:
            return {}

        rows = (
            await self.session.execute(
                select(PedidoCompra.id, PedidoCompra.numero).where(
                    PedidoCompra.tenant_id == self.tenant_id,
                    PedidoCompra.id.in_(pedido_ids),
                )
            )
        ).all()
        return {pedido_id: numero for pedido_id, numero in rows if numero}

    def _formatar_motivo_movimento(
        self,
        mov: EstoqueMovimento,
        numeros_pedido: dict[UUID, str],
    ) -> str | None:
        if mov.origem == "COMPRA" and mov.origem_id in numeros_pedido:
            return f"Recebimento de Pedido {numeros_pedido[mov.origem_id]}"
        if mov.origem == "AJUSTE" and mov.origem_id in numeros_pedido and mov.observacoes:
            return mov.observacoes.replace(str(mov.origem_id), numeros_pedido[mov.origem_id])
        return mov.observacoes

    def _movimento_referencia_pedido_compra(self, mov: EstoqueMovimento) -> bool:
        return mov.origem == "COMPRA" or (
            mov.origem == "AJUSTE"
            and bool(mov.ajuste_de)
            and bool(mov.observacoes)
            and "Estorno de recebimento" in mov.observacoes
        )

    async def obter_movimentacao(self, movimentacao_id: UUID) -> dict:
        stmt = (
            select(
                EstoqueMovimento,
                ProdutoCatalogo.nome.label("produto_nome"),
                Deposito.nome.label("deposito_nome"),
            )
            .join(ProdutoCatalogo, EstoqueMovimento.produto_id == ProdutoCatalogo.id)
            .outerjoin(Deposito, EstoqueMovimento.deposito_id == Deposito.id)
            .where(
                EstoqueMovimento.id == movimentacao_id,
                EstoqueMovimento.tenant_id == self.tenant_id,
            )
        )

        result = (await self.session.execute(stmt)).first()
        if not result:
            raise EntityNotFoundError(f"Movimentação {movimentacao_id} não encontrada.")

        mov, p_nome, d_nome = result
        mov_dict = {c.name: getattr(mov, c.name) for c in mov.__table__.columns}
        mov_dict["produto_nome"] = p_nome
        mov_dict["deposito_nome"] = d_nome
        mov_dict["tipo"] = mov.tipo_movimento
        mov_dict["origem_tipo"] = mov.origem
        mov_dict["data_movimentacao"] = mov.data_movimento
        numeros_pedido = await self._mapear_numeros_pedido_compra([mov])
        mov_dict["motivo"] = self._formatar_motivo_movimento(mov, numeros_pedido)
        return mov_dict

    async def ajustar_movimentacao(self, movimentacao_id: UUID, data: AjusteMovimentoRequest) -> EstoqueMovimento:
        # 1. Buscar movimentação original
        stmt = select(EstoqueMovimento).where(
            EstoqueMovimento.id == movimentacao_id,
            EstoqueMovimento.tenant_id == self.tenant_id
        )
        original = (await self.session.execute(stmt)).scalars().first()
        if not original:
            raise EntityNotFoundError(f"Movimentação {movimentacao_id} não encontrada.")

        # 2. Registrar o ajuste no estoque via ledger
        mov = await registrar_ledger_estoque(
            self.session,
            tenant_id=self.tenant_id,
            produto_id=original.produto_id,
            deposito_id=original.deposito_id,
            lote_id=original.lote_id,
            tipo_movimento=data.tipo_ajuste,
            quantidade=data.quantidade,
            custo_unitario=original.custo_unitario,
            origem="AJUSTE",
            ajuste_de=original.id,
            observacoes=data.motivo,
        )

        # 3. Atualizar saldo real (SaldoEstoque)
        saldo = await self._get_ou_criar_saldo(original.deposito_id, original.produto_id)
        # registrar_ledger_estoque normaliza a quantidade dependendo do tipo (SAIDA fica negativo)
        real_qty = float(mov.quantidade)
        
        if data.tipo_ajuste == "SAIDA":
            disponivel = saldo.quantidade_atual - saldo.quantidade_reservada
            if disponivel < data.quantidade:
                raise BusinessRuleError(
                    f"Saldo insuficiente para ajuste de saída. Disponível: {disponivel:.3f}, Necessário: {data.quantidade:.3f}"
                )
        
        saldo.quantidade_atual += real_qty
        await self._verificar_e_notificar_estoque_baixo(saldo)

        # 4. Atualizar saldo do lote se existir
        if original.lote_id:
            stmt_lote = select(LoteEstoque).where(LoteEstoque.id == original.lote_id)
            lote = (await self.session.execute(stmt_lote)).scalars().first()
            if lote:
                lote.quantidade_atual += real_qty
                if lote.quantidade_atual <= 0:
                    lote.status = "ESGOTADO"
                elif lote.status == "ESGOTADO" and lote.quantidade_atual > 0:
                    lote.status = "ATIVO"

        # 5. Ajuste Financeiro (se SAIDA e houver safra_id vinculada à original)
        if data.tipo_ajuste == "SAIDA":
            stmt_lanc = select(LancamentoFinanceiro.safra_id).where(
                LancamentoFinanceiro.tenant_id == self.tenant_id,
                LancamentoFinanceiro.origem == "ESTOQUE",
                LancamentoFinanceiro.origem_id == original.id
            ).limit(1)
            safra_id = (await self.session.execute(stmt_lanc)).scalar_one_or_none()
            
            if safra_id:
                prod = await self._get_produto(original.produto_id)
                await self._criar_lancamento_insumo(
                    safra_id=safra_id,
                    nome_produto=f"Ajuste de estoque: {prod.nome if prod else 'Produto'}",
                    custo_unitario=float(original.custo_unitario or 0),
                    quantidade=data.quantidade,
                    movimentacao_id=mov.id
                )

        await self.session.flush()
        await self.session.refresh(mov)
        return mov

    async def get_auditoria_movimentacao(self, movimentacao_id: UUID) -> dict:
        # 1. Buscar movimentação original
        original = await self.obter_movimentacao(movimentacao_id)
        
        # 2. Buscar ajustes vinculados
        stmt_ajustes = select(EstoqueMovimento).where(
            EstoqueMovimento.ajuste_de == movimentacao_id,
            EstoqueMovimento.tenant_id == self.tenant_id
        ).order_by(EstoqueMovimento.created_at.asc())
        ajustes_db = (await self.session.execute(stmt_ajustes)).scalars().all()
        
        ajustes_list = []
        for a in ajustes_db:
            # Buscar lançamento financeiro se existir
            stmt_lanc = select(LancamentoFinanceiro).where(
                LancamentoFinanceiro.tenant_id == self.tenant_id,
                LancamentoFinanceiro.origem == "ESTOQUE",
                LancamentoFinanceiro.origem_id == a.id
            ).limit(1)
            lanc = (await self.session.execute(stmt_lanc)).scalars().first()
            
            ajuste_item = {
                "id": a.id,
                "tipo": a.tipo,
                "quantidade": a.quantidade,
                "motivo": a.observacoes,
                "created_at": a.created_at,
                "lancamento_financeiro": lanc if lanc else None
            }
            ajustes_list.append(ajuste_item)
            
        return {
            "movimentacao_original": original,
            "ajustes": ajustes_list
        }

    # ── Requisições de Material ────────────────────────────────────────────

    async def _enriquecer_nomes_requisicao(self, req: RequisicaoMaterial) -> RequisicaoMaterial:
        usuario_ids = [uid for uid in (req.solicitante_id, req.aprovador_id) if uid]
        if usuario_ids:
            stmt_u = select(Usuario.id, Usuario.nome_completo).where(Usuario.id.in_(usuario_ids))
            nomes = dict((await self.session.execute(stmt_u)).all())
            req.solicitante_nome = nomes.get(req.solicitante_id)
            req.aprovador_nome = nomes.get(req.aprovador_id) if req.aprovador_id else None
        return req

    async def _carregar_itens_requisicao(self, req: RequisicaoMaterial) -> RequisicaoMaterial:
        """`RequisicaoMaterial.itens` é lazy='noload' — precisa ser carregado
        explicitamente para a resposta da API não vir sempre com itens=[]."""
        stmt = select(ItemRequisicao).where(ItemRequisicao.requisicao_id == req.id)
        itens = list((await self.session.execute(stmt)).scalars().all())
        produto_ids = {item.produto_id for item in itens}
        produtos: dict[uuid.UUID, ProdutoCatalogo] = {}
        if produto_ids:
            stmt_p = select(ProdutoCatalogo).where(ProdutoCatalogo.id.in_(produto_ids))
            produtos = {p.id: p for p in (await self.session.execute(stmt_p)).scalars().all()}
        for item in itens:
            produto = produtos.get(item.produto_id)
            item.produto_nome = produto.nome if produto else None
            item.unidade_medida = produto.unidade_medida if produto else None
        req.itens = itens
        await self._enriquecer_nomes_requisicao(req)
        return req

    async def criar_requisicao(self, data: RequisicaoCreate, solicitante_id: UUID) -> RequisicaoMaterial:
        numero = await SequencialService(self.session, self.tenant_id).proximo_numero("estoque_requisicao")
        req = RequisicaoMaterial(
            tenant_id=self.tenant_id,
            numero=numero,
            unidade_produtiva_id=data.unidade_produtiva_id,
            solicitante_id=solicitante_id,
            data_necessidade=data.data_necessidade,
            origem_tipo=data.origem_tipo,
            origem_id=data.origem_id,
            observacoes=data.observacoes,
            status="PENDENTE",
        )
        self.session.add(req)
        await self.session.flush()
        for item_data in data.itens:
            item = ItemRequisicao(
                requisicao_id=req.id,
                produto_id=item_data.produto_id,
                deposito_id=item_data.deposito_id,
                quantidade_solicitada=item_data.quantidade_solicitada,
                observacoes=item_data.observacoes,
            )
            self.session.add(item)
        await self.session.flush()
        await self.session.refresh(req)
        return await self._carregar_itens_requisicao(req)

    async def criar_requisicao_a_partir_de_operacao(
        self,
        operacao: OperacaoAgricola,
        *,
        unidade_produtiva_id: UUID,
        solicitante_id: UUID,
        data_necessidade: date | None = None,
    ) -> RequisicaoMaterial | None:
        """Auto-gera a requisição de material (picking list) ao confirmar uma OS
        (gerar_operacao_planejada). Idempotente: não duplica se já existir uma
        requisição para esta operação. Pode haver mais de uma requisição por OS
        (complementos), então esta função só cobre a geração inicial."""
        stmt_existente = select(RequisicaoMaterial).where(
            RequisicaoMaterial.tenant_id == self.tenant_id,
            RequisicaoMaterial.operacao_agricola_id == operacao.id,
        )
        if (await self.session.execute(stmt_existente)).scalars().first():
            return None

        from agricola.operacoes.models import InsumoOperacao
        stmt_insumos = select(InsumoOperacao).where(InsumoOperacao.operacao_id == operacao.id)
        insumos = list((await self.session.execute(stmt_insumos)).scalars().all())
        if not insumos:
            return None

        numero = await SequencialService(self.session, self.tenant_id).proximo_numero("estoque_requisicao")
        req = RequisicaoMaterial(
            tenant_id=self.tenant_id,
            numero=numero,
            unidade_produtiva_id=unidade_produtiva_id,
            solicitante_id=solicitante_id,
            data_necessidade=data_necessidade,
            origem_tipo="ORDEM_SERVICO",
            origem_id=operacao.id,
            operacao_agricola_id=operacao.id,
            observacoes=f"Gerada automaticamente ao confirmar a OS {operacao.id} ({operacao.tipo}).",
            status="PENDENTE",
        )
        self.session.add(req)
        await self.session.flush()

        for insumo in insumos:
            item = ItemRequisicao(
                requisicao_id=req.id,
                produto_id=insumo.produto_id,
                quantidade_solicitada=float(insumo.quantidade_total or 0.0),
                observacoes=f"Insumo planejado da OS — dose {insumo.dose_por_ha} {insumo.unidade}/ha",
            )
            self.session.add(item)

        await self.session.flush()
        await self.session.refresh(req)
        return await self._carregar_itens_requisicao(req)

    async def listar_requisicoes_por_operacao(self, operacao_agricola_id: UUID) -> list[RequisicaoMaterial]:
        """Requisições (pode ser mais de uma — inicial + complementos) vinculadas
        a uma OS, para o app de campo mostrar o que precisa retirar/devolver."""
        stmt = select(RequisicaoMaterial).where(
            RequisicaoMaterial.tenant_id == self.tenant_id,
            RequisicaoMaterial.operacao_agricola_id == operacao_agricola_id,
        ).order_by(RequisicaoMaterial.data_solicitacao.asc())
        requisicoes = list((await self.session.execute(stmt)).scalars().all())
        for req in requisicoes:
            await self._carregar_itens_requisicao(req)
        return requisicoes

    async def listar_requisicoes(
        self,
        unidade_produtiva_id: UUID | None = None,
        status: str | None = None,
        solicitante_id: UUID | None = None,
    ) -> list[RequisicaoMaterial]:
        stmt = select(RequisicaoMaterial).where(RequisicaoMaterial.tenant_id == self.tenant_id)
        if unidade_produtiva_id:
            stmt = stmt.where(RequisicaoMaterial.unidade_produtiva_id == unidade_produtiva_id)
        if status:
            stmt = stmt.where(RequisicaoMaterial.status == status)
        if solicitante_id:
            stmt = stmt.where(RequisicaoMaterial.solicitante_id == solicitante_id)
        stmt = stmt.order_by(RequisicaoMaterial.data_solicitacao.desc())
        requisicoes = list((await self.session.execute(stmt)).scalars().all())
        for req in requisicoes:
            await self._carregar_itens_requisicao(req)
        return requisicoes

    async def aprovar_requisicao(
        self, req_id: UUID, data: RequisicaoAprovarRequest, aprovador_id: UUID
    ) -> RequisicaoMaterial:
        stmt = select(RequisicaoMaterial).where(
            RequisicaoMaterial.id == req_id, RequisicaoMaterial.tenant_id == self.tenant_id
        )
        req = (await self.session.execute(stmt)).scalars().first()
        if not req:
            raise EntityNotFoundError(f"Requisição {req_id} não encontrada.")
        if req.status != "PENDENTE":
            raise BusinessRuleError(f"Requisição não pode ser aprovada no status '{req.status}'.")

        item_map = {i.item_id: i for i in data.itens}
        stmt_itens = select(ItemRequisicao).where(ItemRequisicao.requisicao_id == req_id)
        itens = (await self.session.execute(stmt_itens)).scalars().all()
        for item in itens:
            if item.id in item_map:
                upd = item_map[item.id]
                item.quantidade_aprovada = upd.quantidade_aprovada
                if upd.deposito_id:
                    item.deposito_id = upd.deposito_id

        req.aprovador_id = aprovador_id
        req.status = "APROVADA"
        await self.session.flush()
        await self.session.refresh(req)
        req.itens = list(itens)
        await self._enriquecer_nomes_requisicao(req)
        return req

    async def entregar_requisicao(
        self, req_id: UUID, data: RequisicaoEntregarRequest
    ) -> RequisicaoMaterial:
        stmt = select(RequisicaoMaterial).where(
            RequisicaoMaterial.id == req_id, RequisicaoMaterial.tenant_id == self.tenant_id
        )
        req = (await self.session.execute(stmt)).scalars().first()
        if not req:
            raise EntityNotFoundError(f"Requisição {req_id} não encontrada.")
        if req.status not in ("APROVADA", "SEPARANDO"):
            raise BusinessRuleError(f"Requisição não pode ser entregue no status '{req.status}'.")

        safra_id = await self._resolver_safra_contexto_requisicao(req)
        item_map = {i.item_id: i for i in data.itens}
        stmt_itens = select(ItemRequisicao).where(ItemRequisicao.requisicao_id == req_id)
        itens = (await self.session.execute(stmt_itens)).scalars().all()
        for item in itens:
            if item.id not in item_map:
                continue
            upd = item_map[item.id]
            qtd = upd.quantidade_entregue
            if qtd <= 0:
                continue
            if not item.deposito_id:
                raise BusinessRuleError(f"Item {item.id} sem depósito definido para entrega.")
            # Baixa de estoque
            saida = SaidaEstoqueRequest(
                deposito_id=item.deposito_id,
                produto_id=item.produto_id,
                quantidade=qtd,
                motivo=f"Requisição {req_id}",
                origem_id=req_id,
                origem_tipo="REQUISICAO",
                lote_id=upd.lote_id,
                safra_id=safra_id,
            )
            await self.registrar_saida(saida)
            item.quantidade_entregue = qtd
            item.lote_id = upd.lote_id

        req.status = "ENTREGUE"
        await self.session.flush()
        await self.session.refresh(req)
        req.itens = list(itens)
        await self._enriquecer_nomes_requisicao(req)
        return req

    async def _verificar_credencial_step_up(self, email: str, senha: str) -> Usuario:
        """Reautentica por e-mail+senha (pode ser pessoa diferente do usuário
        logado — quem efetivamente retira/devolve o material). Valida que o
        usuário resolvido pertence a este tenant."""
        from core.models.auth import TenantUsuario
        from core.services.auth_service import AuthService

        stmt = select(Usuario).where(func.lower(Usuario.email) == email.strip().lower())
        usuario = (await self.session.execute(stmt)).scalars().first()
        if not usuario or not usuario.ativo or not usuario.senha_hash:
            raise BusinessRuleError("Credenciais inválidas.")

        vinculo = (await self.session.execute(select(TenantUsuario).where(
            TenantUsuario.tenant_id == self.tenant_id,
            TenantUsuario.usuario_id == usuario.id,
            TenantUsuario.status == "ATIVO",
        ))).scalars().first()
        if not vinculo:
            raise BusinessRuleError("Credenciais inválidas.")

        if not AuthService(self.session).verify_password(senha, usuario.senha_hash):
            raise BusinessRuleError("Credenciais inválidas.")

        return usuario

    async def confirmar_retirada_requisicao(
        self, req_id: UUID, data: ConfirmarRetiradaRequest
    ) -> RequisicaoMaterial:
        """Confirma a retirada física do material com reautenticação (e-mail+senha)."""
        usuario = await self._verificar_credencial_step_up(data.email, data.senha)
        return await self._confirmar_retirada_interno(
            req_id, data.itens, usuario=usuario, metodo="SENHA", email_informado=data.email,
        )

    async def confirmar_retirada_requisicao_dispositivo(
        self, req_id: UUID, device_user_id: UUID, itens: list,
    ) -> RequisicaoMaterial:
        """Confirma retirada via app de campo, já reautenticado por PIN do
        dispositivo (ver `campo.service.DispositivoService.verificar_pin`)."""
        usuario = await self.session.get(Usuario, device_user_id)
        if not usuario:
            raise EntityNotFoundError(f"Usuário {device_user_id} não encontrado.")
        return await self._confirmar_retirada_interno(
            req_id, itens, usuario=usuario, metodo="TOKEN_DISPOSITIVO", email_informado=None,
        )

    async def _confirmar_retirada_interno(
        self, req_id: UUID, itens: list, *, usuario: Usuario, metodo: str, email_informado: str | None,
    ) -> RequisicaoMaterial:
        """A quantidade CONFERIDA por quem retira é a que efetivamente baixa do
        estoque — pode diferir do solicitado/aprovado."""
        entrega_itens = [
            ItemEntregaUpdate(item_id=item.item_id, quantidade_entregue=item.quantidade_conferida, lote_id=None)
            for item in itens
        ]
        requisicao = await self.entregar_requisicao(req_id, RequisicaoEntregarRequest(itens=entrega_itens))

        self.session.add(RequisicaoConfirmacao(
            tenant_id=self.tenant_id,
            requisicao_id=req_id,
            tipo="RETIRADA",
            usuario_id=usuario.id,
            metodo=metodo,
            email_informado=email_informado,
        ))
        await self.session.flush()
        return requisicao

    async def confirmar_devolucao_requisicao(
        self, req_id: UUID, data: ConfirmarDevolucaoRequest
    ) -> RequisicaoMaterial:
        """Confirma devolução de sobra de insumo com reautenticação (e-mail+senha)."""
        usuario = await self._verificar_credencial_step_up(data.email, data.senha)
        return await self._confirmar_devolucao_interno(
            req_id, data.itens, usuario=usuario, metodo="SENHA", email_informado=data.email,
        )

    async def confirmar_devolucao_requisicao_dispositivo(
        self, req_id: UUID, device_user_id: UUID, itens: list,
    ) -> RequisicaoMaterial:
        """Confirma devolução via app de campo, já reautenticado por PIN do
        dispositivo (ver `campo.service.DispositivoService.verificar_pin`)."""
        usuario = await self.session.get(Usuario, device_user_id)
        if not usuario:
            raise EntityNotFoundError(f"Usuário {device_user_id} não encontrado.")
        return await self._confirmar_devolucao_interno(
            req_id, itens, usuario=usuario, metodo="TOKEN_DISPOSITIVO", email_informado=None,
        )

    async def _confirmar_devolucao_interno(
        self, req_id: UUID, itens_devolvidos: list, *, usuario: Usuario, metodo: str, email_informado: str | None,
    ) -> RequisicaoMaterial:
        """Estorna ao estoque (ledger DEVOLUCAO) — mesmo padrão de estorno já
        usado em `_reverter_movimentos_estoque_operacao` (agricola/operacoes/service.py)."""
        stmt = select(RequisicaoMaterial).where(
            RequisicaoMaterial.id == req_id, RequisicaoMaterial.tenant_id == self.tenant_id
        )
        req = (await self.session.execute(stmt)).scalars().first()
        if not req:
            raise EntityNotFoundError(f"Requisição {req_id} não encontrada.")
        if req.status != "ENTREGUE":
            raise BusinessRuleError(
                f"Só é possível devolver sobra de uma requisição 'ENTREGUE' (status atual: '{req.status}')."
            )

        item_map = {i.item_id: i for i in itens_devolvidos}
        stmt_itens = select(ItemRequisicao).where(ItemRequisicao.requisicao_id == req_id)
        itens = (await self.session.execute(stmt_itens)).scalars().all()

        safra_id = await self._resolver_safra_contexto_requisicao(req)

        for item in itens:
            if item.id not in item_map:
                continue
            upd = item_map[item.id]
            qtd_ja_devolvida = float(item.quantidade_devolvida or 0.0)
            qtd_entregue = float(item.quantidade_entregue or 0.0)
            if qtd_ja_devolvida + upd.quantidade_devolvida > qtd_entregue:
                raise BusinessRuleError(
                    f"Item {item.id}: devolução ({upd.quantidade_devolvida}) excede o saldo "
                    f"retirado ainda não devolvido ({qtd_entregue - qtd_ja_devolvida})."
                )
            if not item.deposito_id:
                raise BusinessRuleError(f"Item {item.id} sem depósito definido para devolução.")

            stmt_saida_original = select(EstoqueMovimento).where(
                EstoqueMovimento.tenant_id == self.tenant_id,
                EstoqueMovimento.origem_tipo == "REQUISICAO",
                EstoqueMovimento.origem_id == req_id,
                EstoqueMovimento.produto_id == item.produto_id,
                EstoqueMovimento.tipo_movimento == "SAIDA",
            ).order_by(EstoqueMovimento.created_at.asc())
            saida_original = (await self.session.execute(stmt_saida_original)).scalars().first()
            if saida_original is None:
                raise BusinessRuleError(
                    f"Item {item.id}: nenhuma saída de estoque encontrada para esta requisição — "
                    "não é possível devolver o que não foi retirado."
                )

            custo_unit = await self._resolver_custo_unitario_contextual(
                item.produto_id, deposito_id=item.deposito_id, lote_id=item.lote_id,
            )
            stmt_saldo = select(SaldoEstoque).where(
                SaldoEstoque.produto_id == item.produto_id,
                SaldoEstoque.deposito_id == item.deposito_id,
            )
            saldo = (await self.session.execute(stmt_saldo)).scalars().first()
            if saldo:
                saldo.quantidade_atual += upd.quantidade_devolvida

            await registrar_ledger_estoque(
                self.session,
                tenant_id=self.tenant_id,
                tipo_movimento="DEVOLUCAO",
                origem="REQUISICAO",
                origem_id=req_id,
                produto_id=item.produto_id,
                deposito_id=item.deposito_id,
                lote_id=item.lote_id,
                quantidade=upd.quantidade_devolvida,
                custo_unitario=custo_unit,
                ajuste_de=saida_original.id,
                observacoes=f"Devolução de sobra — requisição {req_id}",
            )
            item.quantidade_devolvida = qtd_ja_devolvida + upd.quantidade_devolvida

        self.session.add(RequisicaoConfirmacao(
            tenant_id=self.tenant_id,
            requisicao_id=req_id,
            tipo="DEVOLUCAO",
            usuario_id=usuario.id,
            metodo=metodo,
            email_informado=email_informado,
        ))
        await self.session.flush()
        await self.session.refresh(req)
        req.itens = list(itens)
        await self._enriquecer_nomes_requisicao(req)
        return req

    async def atualizar_status_requisicao(self, req_id: UUID, novo_status: str) -> RequisicaoMaterial:
        stmt = select(RequisicaoMaterial).where(
            RequisicaoMaterial.id == req_id, RequisicaoMaterial.tenant_id == self.tenant_id
        )
        req = (await self.session.execute(stmt)).scalars().first()
        if not req:
            raise EntityNotFoundError(f"Requisição {req_id} não encontrada.")
        req.status = novo_status
        await self.session.flush()
        await self.session.refresh(req)
        return await self._carregar_itens_requisicao(req)

    # ── Reservas de Estoque ────────────────────────────────────────────────

    async def criar_reserva(self, data: ReservaCreate, usuario_id: UUID) -> ReservaEstoque:
        saldo = await self._get_ou_criar_saldo(data.deposito_id, data.produto_id)
        disponivel = saldo.quantidade_atual - saldo.quantidade_reservada
        if disponivel < data.quantidade:
            raise BusinessRuleError(
                f"Saldo disponível insuficiente para reserva. Disponível: {disponivel:.3f}, Solicitado: {data.quantidade:.3f}"
            )
        reserva = ReservaEstoque(
            tenant_id=self.tenant_id,
            produto_id=data.produto_id,
            deposito_id=data.deposito_id,
            criado_por_id=usuario_id,
            quantidade=data.quantidade,
            motivo=data.motivo,
            referencia_tipo=data.referencia_tipo,
            referencia_id=data.referencia_id,
            status="ATIVA",
        )
        saldo.quantidade_reservada += data.quantidade
        self.session.add(reserva)
        await self.session.flush()
        await self.session.refresh(reserva)
        return reserva

    async def cancelar_reserva(self, reserva_id: UUID) -> ReservaEstoque:
        reserva = await self._get_reserva(reserva_id)
        if reserva.status != "ATIVA":
            raise BusinessRuleError(f"Reserva não pode ser cancelada no status '{reserva.status}'.")
        saldo = await self._get_ou_criar_saldo(reserva.deposito_id, reserva.produto_id)
        saldo.quantidade_reservada = max(0.0, saldo.quantidade_reservada - reserva.quantidade)
        reserva.status = "CANCELADA"
        await self.session.flush()
        await self.session.refresh(reserva)
        return reserva

    async def consumir_reserva(self, reserva_id: UUID, data: ReservaConsumirRequest) -> ReservaEstoque:
        reserva = await self._get_reserva(reserva_id)
        if reserva.status != "ATIVA":
            raise BusinessRuleError(f"Reserva não pode ser consumida no status '{reserva.status}'.")
        qtd = data.quantidade or reserva.quantidade
        if qtd > reserva.quantidade:
            raise BusinessRuleError(f"Quantidade a consumir ({qtd:.3f}) excede a reserva ({reserva.quantidade:.3f}).")
        # Libera a reserva antes de registrar saída (evita conflito na checagem de disponível)
        saldo = await self._get_ou_criar_saldo(reserva.deposito_id, reserva.produto_id)
        saldo.quantidade_reservada = max(0.0, saldo.quantidade_reservada - reserva.quantidade)
        # Registra saída física
        await self.registrar_saida(SaidaEstoqueRequest(
            deposito_id=reserva.deposito_id,
            produto_id=reserva.produto_id,
            quantidade=qtd,
            motivo=data.motivo or f"Consumo de reserva: {reserva.motivo}",
            origem_id=reserva.referencia_id,
            origem_tipo=reserva.referencia_tipo or "RESERVA",
        ))
        reserva.status = "CONSUMIDA"
        await self.session.flush()
        await self.session.refresh(reserva)
        return reserva

    async def listar_reservas(
        self,
        produto_id: UUID | None = None,
        deposito_id: UUID | None = None,
        status: str | None = "ATIVA",
    ) -> list[ReservaEstoque]:
        # Filtra apenas reservas do tenant (via depósitos)
        dep_stmt = select(Deposito.id).where(Deposito.tenant_id == self.tenant_id)
        dep_ids = set((await self.session.execute(dep_stmt)).scalars().all())
        stmt = select(ReservaEstoque).where(
            ReservaEstoque.deposito_id.in_(dep_ids)
        ).order_by(ReservaEstoque.created_at.desc())
        if produto_id:
            stmt = stmt.where(ReservaEstoque.produto_id == produto_id)
        if deposito_id:
            stmt = stmt.where(ReservaEstoque.deposito_id == deposito_id)
        if status:
            stmt = stmt.where(ReservaEstoque.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def _get_reserva(self, reserva_id: UUID) -> ReservaEstoque:
        dep_stmt = select(Deposito.id).where(Deposito.tenant_id == self.tenant_id)
        dep_ids = set((await self.session.execute(dep_stmt)).scalars().all())
        stmt = select(ReservaEstoque).where(
            ReservaEstoque.id == reserva_id,
            ReservaEstoque.deposito_id.in_(dep_ids),
        )
        reserva = (await self.session.execute(stmt)).scalars().first()
        if not reserva:
            raise EntityNotFoundError(f"Reserva {reserva_id} não encontrada.")
        return reserva

    async def alertas_estoque_minimo(self, unidade_produtiva_id: UUID | None = None) -> list[AlertaEstoqueItem]:
        saldos = await self.listar_saldos(unidade_produtiva_id)

        # Busca estoque_minimo dos produtos
        prod_ids = [s.produto_id for s in saldos if s.abaixo_minimo]
        if not prod_ids:
            return []
        stmt = select(ProdutoCatalogo).where(ProdutoCatalogo.id.in_(prod_ids))
        prods = {p.id: p for p in (await self.session.execute(stmt)).scalars().all()}

        return [
            AlertaEstoqueItem(
                id=s.id,
                produto_id=s.produto_id,
                deposito_id=s.deposito_id,
                produto_nome=s.produto_nome,
                deposito_nome=s.deposito_nome,
                quantidade_atual=s.quantidade_atual,
                estoque_minimo=prods[s.produto_id].estoque_minimo if s.produto_id in prods else 0.0,
                unidade_medida=s.unidade_medida,
                quantidade_sugerida=round(
                    max(0.0, (prods[s.produto_id].estoque_minimo if s.produto_id in prods else 0.0) - s.quantidade_atual), 4
                ),
            )
            for s in saldos if s.abaixo_minimo
        ]
