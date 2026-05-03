from uuid import UUID
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.base_service import BaseService
from core.exceptions import BusinessRuleError, EntityNotFoundError
from operacional.models.estoque import (
    Deposito, EstoqueMovimento, SaldoEstoque,
    LoteEstoque, RequisicaoMaterial, ItemRequisicao, ReservaEstoque,
)
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
    ReservaCreate, ReservaCancelarRequest, ReservaConsumirRequest,
    AuditoriaMovimentacaoResponse,
)
from operacional.services.estoque_ledger import registrar_ledger_estoque
from financeiro.models.lancamento import LancamentoFinanceiro


class EstoqueService(BaseService[SaldoEstoque]):
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(SaldoEstoque, session, tenant_id)

    async def _get_produto(self, produto_id: UUID) -> ProdutoCatalogo | None:
        stmt = select(ProdutoCatalogo).where(
            ProdutoCatalogo.id == produto_id,
            ProdutoCatalogo.tenant_id == self.tenant_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    # ── Categorias ────────────────────────────────────────────────────────

    # ── Depósitos ─────────────────────────────────────────────────────────

    async def criar_deposito(self, data: DepositoCreate) -> Deposito:
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

        prod_stmt = select(ProdutoCatalogo).where(ProdutoCatalogo.tenant_id == self.tenant_id, ProdutoCatalogo.ativo == True)
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

        result = [SaldoResponse(
            id=s.id,
            deposito_id=s.deposito_id,
            produto_id=s.produto_id,
            produto_nome=produtos.get(s.produto_id).nome if produtos.get(s.produto_id) else "N/A",
            deposito_nome=depositos.get(s.deposito_id).nome if depositos.get(s.deposito_id) else "N/A",
            quantidade_atual=s.quantidade_atual,
            quantidade_reservada=s.quantidade_reservada,
            quantidade_disponivel=max(0.0, s.quantidade_atual - s.quantidade_reservada),
            preco_medio=produtos.get(s.produto_id).preco_medio if produtos.get(s.produto_id) else 0.0,
            unidade_medida=produtos.get(s.produto_id).unidade_medida if produtos.get(s.produto_id) else "",
            estoque_minimo=s.estoque_minimo,
            abaixo_minimo=max(0.0, s.quantidade_atual - s.quantidade_reservada) <= (s.estoque_minimo or 0) if s.estoque_minimo is not None else False,
            ultima_atualizacao=s.ultima_atualizacao,
        ) for s in saldos if s.deposito_id in depositos and s.produto_id in produtos]
        return result

    async def atualizar_estoque_minimo(self, saldo_id: UUID, estoque_minimo: float) -> SaldoEstoque:
        stmt = select(SaldoEstoque).where(SaldoEstoque.id == saldo_id)
        saldo = (await self.session.execute(stmt)).scalars().first()
        if not saldo:
            raise EntityNotFoundError("Saldo não encontrado.")
        saldo.estoque_minimo = estoque_minimo
        self.session.add(saldo)
        await self.session.flush()
        
        # Verificar se já está abaixo do novo mínimo
        await self._verificar_e_notificar_estoque_baixo(saldo)
        
        return saldo

    async def listar_alertas_reposicao(self) -> list[AlertaEstoqueItem]:
        saldos = await self.listar_saldos()
        alertas = []
        for s in saldos:
            if s.abaixo_minimo:
                minimo = s.estoque_minimo or 0
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
        if saldo.estoque_minimo is not None:
            disponivel = max(0.0, saldo.quantidade_atual - saldo.quantidade_reservada)
            if disponivel <= saldo.estoque_minimo:
                from notificacoes.service import NotificacaoService
                from notificacoes.schemas import NotificacaoCreate
                from core.models.cadastros.produto import ProdutoCatalogo
                
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
            status="ATIVO",
        )
        self.session.add(lote)
        await self.session.flush()
        await self.session.refresh(lote)
        return lote

    async def atualizar_lote(self, lote_id: UUID, data: LoteUpdate) -> LoteEstoque:
        stmt = select(LoteEstoque).where(LoteEstoque.id == lote_id)
        lote = (await self.session.execute(stmt)).scalars().first()
        if not lote:
            raise EntityNotFoundError(f"Lote {lote_id} não encontrado.")
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
        return list((await self.session.execute(stmt)).scalars().all())

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
    ) -> EstoqueMovimento:
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
            observacoes=motivo,
        )

    async def _descontar_lote(self, lote_id: UUID, quantidade: float) -> LoteEstoque:
        """Desconta quantidade de um lote e atualiza status se esgotado."""
        stmt = select(LoteEstoque).where(LoteEstoque.id == lote_id)
        lote = (await self.session.execute(stmt)).scalars().first()
        if not lote:
            raise EntityNotFoundError(f"Lote {lote_id} não encontrado.")
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
        stmt = select(Deposito).where(
            Deposito.id == data.deposito_id, Deposito.tenant_id == self.tenant_id
        )
        dep = (await self.session.execute(stmt)).scalars().first()
        if not dep:
            raise EntityNotFoundError("Depósito não encontrado.")

        saldo = await self._get_ou_criar_saldo(data.deposito_id, data.produto_id)
        qtd_antes = saldo.quantidade_atual
        saldo.quantidade_atual += data.quantidade

        # Atualiza preço médio ponderado
        prod = await self._get_produto(data.produto_id)
        if data.custo_unitario and data.custo_unitario > 0:
            if qtd_antes > 0:
                prod.preco_medio = round(
                    (qtd_antes * prod.preco_medio + data.quantidade * data.custo_unitario)
                    / saldo.quantidade_atual, 4
                )
            else:
                prod.preco_medio = data.custo_unitario
            self.session.add(prod)

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
            custo_unitario=data.custo_unitario or prod.preco_medio,
            motivo=data.motivo or "Entrada manual",
            origem_id=data.origem_id,
            origem_tipo=data.origem_tipo or "MANUAL",
            lote_id=data.lote_id,
        )
        await self.session.flush()
        await self.session.refresh(mov)
        await self._verificar_e_notificar_estoque_baixo(saldo)
        return mov

    async def registrar_saida_insumo(
        self,
        produto_id: UUID,
        quantidade: float,
        unidade_produtiva_id: UUID,
        origem_id: UUID,
        origem_tipo: str = "OPERACAO_AGRICOLA",
        motivo: str = "Uso em operação agrícola",
        deposito_id: UUID | None = None,
    ) -> EstoqueMovimento:
        if deposito_id:
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
        mov = await self._registrar_movimento(
            deposito_id=saldo_sel.deposito_id,
            produto_id=produto_id,
            tipo="SAIDA",
            quantidade=quantidade,
            custo_unitario=prod.preco_medio if prod else None,
            motivo=motivo,
            origem_id=origem_id,
            origem_tipo=origem_tipo,
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
    ) -> EstoqueMovimento:
        """Busca o produto pelo nome e registra a saída."""
        stmt = select(ProdutoCatalogo).where(
            ProdutoCatalogo.tenant_id == self.tenant_id,
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
            motivo=motivo
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

    async def registrar_saida(self, data: SaidaEstoqueRequest) -> EstoqueMovimento:
        if data.deposito_id:
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
            custo_unit = prod.preco_medio if prod else 0.0
            mov = await self._registrar_movimento(
                deposito_id=data.deposito_id, produto_id=data.produto_id,
                tipo="SAIDA", quantidade=data.quantidade,
                custo_unitario=custo_unit or None,
                motivo=data.motivo, origem_id=data.origem_id,
                origem_tipo=data.origem_tipo or "MANUAL",
                lote_id=data.lote_id,
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
                custo_unit = prod.preco_medio if prod else 0.0
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
        mov = await self._registrar_movimento(
            deposito_id=data.deposito_id,
            produto_id=data.produto_id,
            tipo="AJUSTE",
            quantidade=diff,
            motivo=data.motivo,
            origem_tipo="AJUSTE",
        )
        await self.session.flush()
        await self.session.refresh(mov)
        await self._verificar_e_notificar_estoque_baixo(saldo)
        return mov

    async def registrar_transferencia(self, data: TransferenciaEstoqueRequest) -> list[EstoqueMovimento]:
        stmt = select(SaldoEstoque).where(
            SaldoEstoque.produto_id == data.produto_id,
            SaldoEstoque.deposito_id == data.deposito_origem_id,
        )
        saldo_orig = (await self.session.execute(stmt)).scalars().first()
        if not saldo_orig or saldo_orig.quantidade_atual < data.quantidade:
            raise BusinessRuleError("Saldo insuficiente no depósito de origem.")

        saldo_orig.quantidade_atual -= data.quantidade
        saldo_dest = await self._get_ou_criar_saldo(data.deposito_destino_id, data.produto_id)
        saldo_dest.quantidade_atual += data.quantidade

        prod = await self._get_produto(data.produto_id)
        motivo = data.motivo or "Transferência entre depósitos"
        transferencia_id = uuid.uuid4()
        mov_saida = await self._registrar_movimento(
            deposito_id=data.deposito_origem_id, produto_id=data.produto_id,
            tipo="TRANSFERENCIA", quantidade=-data.quantidade,
            custo_unitario=prod.preco_medio if prod else None,
            motivo=motivo, origem_id=transferencia_id, origem_tipo="TRANSFERENCIA",
        )
        mov_entrada = await self._registrar_movimento(
            deposito_id=data.deposito_destino_id, produto_id=data.produto_id,
            tipo="TRANSFERENCIA", quantidade=data.quantidade,
            custo_unitario=prod.preco_medio if prod else None,
            motivo=motivo, origem_id=transferencia_id, origem_tipo="TRANSFERENCIA",
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
        result = []
        for mov, p_nome, d_nome in rows:
            mov_dict = {c.name: getattr(mov, c.name) for c in mov.__table__.columns}
            mov_dict["produto_nome"] = p_nome
            mov_dict["deposito_nome"] = d_nome
            # Mapeia campos legados para o schema MovimentacaoResponse
            mov_dict["data_movimentacao"] = mov.data_movimento
            mov_dict["motivo"] = mov.observacoes
            result.append(mov_dict)
        return result

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
        mov_dict["data_movimentacao"] = mov.data_movimento
        mov_dict["motivo"] = mov.observacoes
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

    async def criar_requisicao(self, data: RequisicaoCreate, solicitante_id: UUID) -> RequisicaoMaterial:
        req = RequisicaoMaterial(
            tenant_id=self.tenant_id,
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
        return req

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
        return list((await self.session.execute(stmt)).scalars().all())

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
            )
            await self.registrar_saida(saida)
            item.quantidade_entregue = qtd
            item.lote_id = upd.lote_id

        req.status = "ENTREGUE"
        await self.session.flush()
        await self.session.refresh(req)
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
        return req

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
                produto_id=s.produto_id,
                produto_nome=s.produto_nome,
                deposito_nome=s.deposito_nome,
                quantidade_atual=s.quantidade_atual,
                estoque_minimo=prods[s.produto_id].estoque_minimo if s.produto_id in prods else 0.0,
                unidade_medida=s.unidade_medida,
                deficit=round(
                    (prods[s.produto_id].estoque_minimo if s.produto_id in prods else 0.0) - s.quantidade_atual, 4
                ),
            )
            for s in saldos if s.abaixo_minimo
        ]
