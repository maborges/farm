import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, func, union_all, literal_column, cast, Numeric
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from agricola.alertas.service import AlertasAgricolasService, WorkflowGovernanceEvent
from core.exceptions import BusinessRuleError
from operacional.models.compras import (
    SolicitacaoCompra,
    CotacaoCompra,
    PedidoCompra,
    ItemPedidoCompra,
    RecebimentoParcial,
    ItemRecebimento,
    DevolucaoFornecedor,
    ItemDevolucao,
)
from operacional.schemas.compras import (
    SolicitacaoCompraCreate,
    CotacaoSolicitacaoCreate,
    RecebimentoCreate,
)
from operacional.services.estoque_service import EstoqueService
from operacional.schemas.estoque import EntradaEstoqueRequest, LoteCreate, AjusteMovimentoRequest
from operacional.models.estoque import EstoqueMovimento, LoteEstoque, SaldoEstoque
from operacional.services.estoque_ledger import registrar_ledger_estoque

class ComprasService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    def _resolver_custo_recebimento(self, pedido: PedidoCompra) -> float:
        """
        Guardrail de valuation:
        recebimento compra usa o valor do pedido como custo operacional,
        sem consultar nem reescrever `Produto.preco_medio`.
        """
        return float(pedido.valor_unitario)

    async def _get_or_create_item_pedido_principal(self, pedido: PedidoCompra) -> ItemPedidoCompra:
        stmt = (
            select(ItemPedidoCompra)
            .where(ItemPedidoCompra.pedido_id == pedido.id)
            .order_by(ItemPedidoCompra.id.asc())
            .limit(1)
        )
        item = (await self.session.execute(stmt)).scalar_one_or_none()
        if item is not None:
            return item

        item = ItemPedidoCompra(
            id=uuid.uuid4(),
            pedido_id=pedido.id,
            produto_id=pedido.item_id,
            quantidade_solicitada=pedido.quantidade,
            preco_estimado_unitario=pedido.valor_unitario,
            quantidade_recebida=0.0,
            preco_real_unitario=pedido.valor_unitario,
            status_item="PENDENTE",
        )
        self.session.add(item)
        await self.session.flush()
        return item

    def _build_recebimento_fallback(self, pedido: PedidoCompra, item_pedido: ItemPedidoCompra) -> RecebimentoCreate:
        return RecebimentoCreate(
            numero_nf=None,
            chave_nfe=None,
            observacoes="Recebimento materializado por compatibilidade no fluxo legado.",
            itens=[
                {
                    "item_pedido_id": item_pedido.id,
                    "quantidade_recebida": pedido.quantidade,
                    "preco_real_unitario": self._resolver_custo_recebimento(pedido),
                    "numero_lote_fornecedor": None,
                    "lote_id": None,
                }
            ],
        )

    def _gerar_numero_lote_recebimento(
        self,
        pedido: PedidoCompra,
        recebimento: RecebimentoCreate,
        item_recebido,
    ) -> str:
        base_nf = (recebimento.numero_nf or "").strip()
        lote_fornecedor = (getattr(item_recebido, "numero_lote_fornecedor", None) or "").strip()
        if base_nf and lote_fornecedor:
            return f"{base_nf}:{lote_fornecedor}"[:100]
        if base_nf:
            return base_nf[:100]
        if lote_fornecedor:
            return f"COMPRA-{str(pedido.id)[:8]}:{lote_fornecedor}"[:100]
        return f"COMPRA-{str(pedido.id)[:8]}"

    async def _registrar_evento_recebimento_critico(
        self,
        *,
        pedido: PedidoCompra,
        codigo: str,
        titulo: str,
        mensagem: str,
        meta: dict | None = None,
    ) -> None:
        alertas_svc = AlertasAgricolasService(self.session, self.tenant_id)
        finding = alertas_svc.build_finding(
            codigo=codigo,
            titulo=titulo,
            severidade="RISCO_CRITICO",
            origem="compras_recebimentos",
            total=1,
            mensagem=mensagem,
            amostras=[str(pedido.id)],
            meta={"pedido_id": str(pedido.id), **(meta or {})},
        )
        await alertas_svc.registrar_e_aplicar_enforcement(
            WorkflowGovernanceEvent(
                finding=finding,
                resource_id=str(pedido.id),
                action="recv_critical",
                notify=True,
                audit=True,
                origem_id=f"pedido:{pedido.id}:{codigo.lower()}",
            ),
            allow_block=True,
            error_message=mensagem,
        )

    async def _registrar_evento_reversao_critica(
        self,
        *,
        devolucao: DevolucaoFornecedor,
        codigo: str,
        titulo: str,
        mensagem: str,
        meta: dict | None = None,
    ) -> None:
        alertas_svc = AlertasAgricolasService(self.session, self.tenant_id)
        finding = alertas_svc.build_finding(
            codigo=codigo,
            titulo=titulo,
            severidade="RISCO_CRITICO",
            origem="compras_devolucoes",
            total=1,
            mensagem=mensagem,
            amostras=[str(devolucao.id)],
            meta={"devolucao_id": str(devolucao.id), **(meta or {})},
        )
        await alertas_svc.registrar_e_aplicar_enforcement(
            WorkflowGovernanceEvent(
                finding=finding,
                resource_id=str(devolucao.id),
                action="rev_critical",
                notify=True,
                audit=True,
                origem_id=f"devolucao:{devolucao.id}:{codigo.lower()}",
            ),
            allow_block=True,
            error_message=mensagem,
        )

    async def _materializar_item_recebimento(
        self,
        *,
        pedido: PedidoCompra,
        recebimento: RecebimentoCreate,
        item_pedido: ItemPedidoCompra,
        item_recebido,
    ) -> tuple[uuid.UUID | None, EstoqueMovimento | None]:
        quantidade = float(item_recebido.quantidade_recebida or 0.0)
        custo_unitario = float(item_recebido.preco_real_unitario or 0.0) or self._resolver_custo_recebimento(pedido)
        if quantidade <= 0 or custo_unitario <= 0:
            await self._registrar_evento_recebimento_critico(
                pedido=pedido,
                codigo="RECEBIMENTO_COMPRA_SEM_VALUATION_NOVO_FLUXO",
                titulo="Recebimento com itens sem valuation operacional",
                mensagem=(
                    "Nao e possivel materializar o recebimento sem quantidade e custo unitario validos. "
                    "Revise os itens recebidos ou o valor do pedido."
                ),
                meta={
                    "item_pedido_id": str(item_pedido.id),
                    "quantidade_recebida": quantidade,
                    "custo_unitario": custo_unitario,
                },
            )
            return None, None

        estoque_svc = EstoqueService(self.session, self.tenant_id)
        lote_id = item_recebido.lote_id
        lote = None
        if lote_id is not None:
            lote = await self.session.get(LoteEstoque, lote_id)
        else:
            lote = await estoque_svc.criar_lote(
                LoteCreate(
                    produto_id=pedido.item_id,
                    deposito_id=pedido.deposito_id,
                    numero_lote=self._gerar_numero_lote_recebimento(pedido, recebimento, item_recebido),
                    quantidade_inicial=quantidade,
                    custo_unitario=custo_unitario,
                    nota_fiscal_ref=recebimento.numero_nf,
                )
            )
            lote.quantidade_atual = 0.0
            self.session.add(lote)
            await self.session.flush()
            lote_id = lote.id

        try:
            movimento = await estoque_svc.registrar_entrada(
                EntradaEstoqueRequest(
                    deposito_id=pedido.deposito_id,
                    produto_id=pedido.item_id,
                    quantidade=quantidade,
                    custo_unitario=custo_unitario,
                    motivo=f"Recebimento de Pedido {pedido.id}",
                    origem_id=pedido.id,
                    origem_tipo="COMPRA",
                    lote_id=lote_id,
                )
            )
        except BusinessRuleError as exc:
            await self._registrar_evento_recebimento_critico(
                pedido=pedido,
                codigo="PEDIDO_RECEBIDO_SEM_MATERIALIZACAO_ESTOQUE_NOVO_FLUXO",
                titulo="Pedido recebido sem materializacao completa de estoque",
                mensagem=(
                    "Nao e possivel marcar o pedido como recebido sem lote, movimento e saldo validos. "
                    "Revise produto, deposito e lote do recebimento."
                ),
                meta={
                    "item_pedido_id": str(item_pedido.id),
                    "lote_id": str(lote_id) if lote_id else None,
                    "erro": str(exc),
                },
            )
            return lote_id, None

        saldo = (
            await self.session.execute(
                select(SaldoEstoque).where(
                    SaldoEstoque.deposito_id == pedido.deposito_id,
                    SaldoEstoque.produto_id == pedido.item_id,
                )
            )
        ).scalar_one_or_none()
        if lote_id is None or movimento is None or saldo is None:
            await self._registrar_evento_recebimento_critico(
                pedido=pedido,
                codigo="PEDIDO_RECEBIDO_SEM_LOTE_MOVIMENTO_SALDO_NOVO_FLUXO",
                titulo="Pedido recebido sem materializacao completa de valuation",
                mensagem=(
                    "Nao e possivel marcar o pedido como recebido sem lote, movimento e saldo consistentes. "
                    "Revise a materializacao do recebimento."
                ),
                meta={
                    "item_pedido_id": str(item_pedido.id),
                    "lote_id": str(lote_id) if lote_id else None,
                    "movimento_id": str(movimento.id) if movimento else None,
                    "saldo_encontrado": saldo is not None,
                },
            )
            return lote_id, movimento

        return lote_id, movimento

    async def _buscar_movimento_recebimento_compra(
        self,
        *,
        pedido_id: uuid.UUID | None,
        produto_id: uuid.UUID,
        deposito_id: uuid.UUID,
        lote_id: uuid.UUID | None,
    ) -> EstoqueMovimento | None:
        stmt = (
            select(EstoqueMovimento)
            .where(
                EstoqueMovimento.tenant_id == self.tenant_id,
                EstoqueMovimento.origem == "COMPRA",
                EstoqueMovimento.produto_id == produto_id,
                EstoqueMovimento.deposito_id == deposito_id,
            )
            .order_by(EstoqueMovimento.created_at.asc())
        )
        if pedido_id is not None:
            stmt = stmt.where(EstoqueMovimento.origem_id == pedido_id)
        if lote_id is not None:
            stmt = stmt.where(EstoqueMovimento.lote_id == lote_id)
        stmt = stmt.limit(1)
        return (await self.session.execute(stmt)).scalars().first()

    async def _pedido_tem_reversao_operacional(self, pedido_id: uuid.UUID) -> bool:
        original_stmt = select(EstoqueMovimento.id).where(
            EstoqueMovimento.tenant_id == self.tenant_id,
            EstoqueMovimento.origem == "COMPRA",
            EstoqueMovimento.origem_id == pedido_id,
        )
        originals = list((await self.session.execute(original_stmt)).scalars().all())
        if not originals:
            return False
        reversao_stmt = select(func.count(EstoqueMovimento.id)).where(
            EstoqueMovimento.tenant_id == self.tenant_id,
            EstoqueMovimento.origem == "AJUSTE",
            EstoqueMovimento.ajuste_de.in_(originals),
        )
        return (await self.session.execute(reversao_stmt)).scalar_one() > 0

    async def concluir_devolucao(self, devolucao_id: uuid.UUID) -> DevolucaoFornecedor | None:
        devolucao = await self.session.get(DevolucaoFornecedor, devolucao_id)
        if not devolucao or devolucao.tenant_id != self.tenant_id:
            return None

        if devolucao.status == "CONCLUIDA":
            return devolucao

        alertas_svc = AlertasAgricolasService(self.session, self.tenant_id)
        permite_warning_only = not alertas_svc.deve_bloquear_severidade("RISCO_CRITICO")
        itens = list(
            (
                await self.session.execute(
                    select(ItemDevolucao).where(
                        ItemDevolucao.devolucao_id == devolucao.id,
                    )
                )
            ).scalars().all()
        )
        if not itens:
                await self._registrar_evento_reversao_critica(
                    devolucao=devolucao,
                    codigo="DEVOLUCAO_SEM_ITENS",
                    titulo="Devolução sem itens rastreáveis",
                    mensagem=(
                        "Nao e possivel concluir a devolucao sem itens vinculados. "
                        "Revise o recebimento original e inclua o lote afetado."
                    ),
                )
                if permite_warning_only:
                    devolucao.status = "CONCLUIDA"
                    self.session.add(devolucao)
                    await self.session.flush()
                    return devolucao
                return devolucao

        estoque_svc = EstoqueService(self.session, self.tenant_id)
        reversoes_preparadas: list[dict] = []
        pedido_referencia_id = devolucao.pedido_id
        for item in itens:
            if item.lote_id is None:
                await self._registrar_evento_reversao_critica(
                    devolucao=devolucao,
                    codigo="DEVOLUCAO_SEM_LOTE_ORIGINAL",
                    titulo="Devolução sem lote original",
                    mensagem=(
                        "Nao e possivel concluir a devolucao sem o lote original. "
                        "Revise o item devolvido e associe o lote rastreavel."
                    ),
                    meta={"item_devolucao_id": str(item.id), "produto_id": str(item.produto_id)},
                )
                if permite_warning_only:
                    devolucao.status = "CONCLUIDA"
                    self.session.add(devolucao)
                    await self.session.flush()
                    return devolucao
                return devolucao

            original_mov = await self._buscar_movimento_recebimento_compra(
                pedido_id=pedido_referencia_id,
                produto_id=item.produto_id,
                deposito_id=item.deposito_origem_id,
                lote_id=item.lote_id,
            )
            if original_mov is None:
                finding = alertas_svc.build_finding(
                    codigo="DEVOLUCAO_SEM_MOVIMENTO_ORIGINAL",
                    titulo="Devolução sem movimento original rastreável",
                    severidade="RISCO_CRITICO",
                    origem="compras_devolucoes",
                    total=1,
                    mensagem=(
                        "Nao e possivel concluir a devolucao sem o movimento original rastreavel. "
                        "Revise lote, produto e deposito."
                    ),
                    amostras=[str(devolucao.id)],
                    meta={"item_devolucao_id": str(item.id), "lote_id": str(item.lote_id)},
                )
                await alertas_svc.registrar_e_aplicar_enforcement(
                    WorkflowGovernanceEvent(
                        finding=finding,
                        resource_id=str(devolucao.id),
                        action="rev_missing_origin",
                        notify=True,
                        audit=True,
                        origem_id=f"devolucao:{devolucao.id}:missing_origin",
                    ),
                    allow_block=True,
                    error_message=(
                        "Nao e possivel concluir a devolucao sem o movimento original rastreavel. "
                        "Revise lote, produto e deposito."
                    ),
                )

            lote = await self.session.get(LoteEstoque, item.lote_id)
            custo_unitario = float(item.custo_unitario or 0.0) or float(original_mov.custo_unitario or 0.0) or float(
                lote.custo_unitario if lote else 0.0
            )
            if custo_unitario <= 0:
                await self._registrar_evento_reversao_critica(
                    devolucao=devolucao,
                    codigo="DEVOLUCAO_SEM_VALUATION",
                    titulo="Devolução sem valuation rastreável",
                    mensagem=(
                        "Nao e possivel concluir a devolucao sem custo unitario rastreavel. "
                        "Revise o custo do lote ou do recebimento original."
                    ),
                    meta={"item_devolucao_id": str(item.id), "lote_id": str(item.lote_id)},
                )
                if permite_warning_only:
                    devolucao.status = "CONCLUIDA"
                    self.session.add(devolucao)
                    await self.session.flush()
                    return devolucao
                return devolucao

            reversoes_preparadas.append(
                {
                    "item": item,
                    "original_mov": original_mov,
                    "lote": lote,
                    "custo_unitario": custo_unitario,
                }
            )

        for preparo in reversoes_preparadas:
            item = preparo["item"]
            original_mov = preparo["original_mov"]
            lote = preparo["lote"]
            custo_unitario = preparo["custo_unitario"]

            movimento = await registrar_ledger_estoque(
                self.session,
                tenant_id=self.tenant_id,
                produto_id=item.produto_id,
                deposito_id=item.deposito_origem_id,
                lote_id=item.lote_id,
                tipo_movimento="AJUSTE",
                quantidade=float(item.quantidade),
                custo_unitario=custo_unitario,
                origem="AJUSTE",
                origem_id=devolucao.id,
                ajuste_de=original_mov.id if original_mov else None,
                observacoes=f"Devolucao fornecedor {devolucao.id}",
            )

            saldo = await estoque_svc._get_ou_criar_saldo(item.deposito_origem_id, item.produto_id)
            saldo.quantidade_atual += float(item.quantidade)

            if lote:
                lote.quantidade_atual += float(item.quantidade)
                if lote.status == "ESGOTADO" and lote.quantidade_atual > 0:
                    lote.status = "ATIVO"

            item.quantidade = float(item.quantidade)
            self.session.add(item)
            logger.info(
                "devolucao_materializada",
                tenant_id=str(self.tenant_id),
                devolucao_id=str(devolucao.id),
                movimento_id=str(movimento.id),
                lote_id=str(item.lote_id),
            )

        devolucao.status = "CONCLUIDA"
        self.session.add(devolucao)
        await self.session.flush()
        return devolucao

    async def criar_solicitacao(self, data: SolicitacaoCompraCreate) -> SolicitacaoCompra:
        """Cria uma nova solicitação de compra interna."""
        obj = SolicitacaoCompra(
            tenant_id=self.tenant_id,
            produto_id=data.item_id,
            deposito_id=data.deposito_id,
            quantidade_solicitada=data.quantidade_solicitada,
            unidade=data.unidade,
            origem=data.origem,
            origem_id=data.origem_id,
            status="ABERTA"
        )
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def listar_solicitacoes(
        self, 
        status: Optional[str] = None,
        produto_id: Optional[uuid.UUID] = None,
        deposito_id: Optional[uuid.UUID] = None
    ) -> List[SolicitacaoCompra]:
        """Lista solicitações de compra com filtros e dados enriquecidos."""
        from core.cadastros.produtos.models import Produto
        from operacional.models.estoque import Deposito
        
        stmt = (
            select(
                SolicitacaoCompra,
                Produto.nome.label("produto_nome"),
                Deposito.nome.label("deposito_nome")
            )
            .join(Produto, SolicitacaoCompra.produto_id == Produto.id)
            .join(Deposito, SolicitacaoCompra.deposito_id == Deposito.id)
            .where(SolicitacaoCompra.tenant_id == self.tenant_id)
        )
        
        if status:
            stmt = stmt.where(SolicitacaoCompra.status == status)
        if produto_id:
            stmt = stmt.where(SolicitacaoCompra.produto_id == produto_id)
        if deposito_id:
            stmt = stmt.where(SolicitacaoCompra.deposito_id == deposito_id)
            
        stmt = stmt.order_by(SolicitacaoCompra.created_at.desc())
        
        result = await self.session.execute(stmt)
        items = []
        for row in result.all():
            sol, p_nome, d_nome = row
            sol.produto_nome = p_nome
            sol.deposito_nome = d_nome
            items.append(sol)
            
        return items

    async def atualizar_status(self, solicitacao_id: uuid.UUID, novo_status: str) -> SolicitacaoCompra:
        """Atualiza o status de uma solicitação de compra."""
        stmt = select(SolicitacaoCompra).where(
            SolicitacaoCompra.id == solicitacao_id,
            SolicitacaoCompra.tenant_id == self.tenant_id
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        
        if not obj:
            return None
            
        obj.status = novo_status
        await self.session.flush()
        
        # Recarregar com nomes para o retorno
        from core.cadastros.produtos.models import Produto
        from operacional.models.estoque import Deposito
        
        enrich_stmt = (
            select(Produto.nome, Deposito.nome)
            .join(Deposito, Deposito.id == obj.deposito_id)
            .where(Produto.id == obj.produto_id)
        )
        enrich_res = (await self.session.execute(enrich_stmt)).first()
        if enrich_res:
            obj.produto_nome, obj.deposito_nome = enrich_res
            
        return obj

    async def criar_cotacao(self, solicitacao_id: uuid.UUID, data: CotacaoSolicitacaoCreate) -> CotacaoCompra:
        """Cria uma cotação para uma solicitação aprovada."""
        from core.exceptions import BusinessRuleError
        
        # Verificar se a solicitação existe e está aprovada
        solicitacao = await self.session.get(SolicitacaoCompra, solicitacao_id)
        if not solicitacao or solicitacao.tenant_id != self.tenant_id:
            return None
        
        if solicitacao.status != "APROVADA":
            raise BusinessRuleError("Cotações só podem ser registradas para solicitações APROVADAS.")

        # Guardrail: cotação usa histórico compatível; `Produto.preco_medio` não é fonte de verdade.
        stats = await self.get_historico_precos(solicitacao.produto_id)
        preco_medio = stats.get("preco_medio", 0)
        
        acima_media = False
        percentual = 0.0
        mensagem = None
        
        if preco_medio > 0 and data.valor_unitario > (preco_medio * 1.15):
            acima_media = True
            percentual = round(((data.valor_unitario / preco_medio) - 1) * 100, 2)
            mensagem = f"Cotação {percentual}% acima da média histórica (R$ {preco_medio:,.2f})"

        cotacao = CotacaoCompra(
            tenant_id=self.tenant_id,
            solicitacao_id=solicitacao_id,
            fornecedor_nome=data.fornecedor_nome,
            fornecedor_contato=data.fornecedor_contato,
            valor_unitario=data.valor_unitario,
            valor_total=round(data.valor_unitario * solicitacao.quantidade_solicitada, 2),
            prazo_entrega_dias=data.prazo_entrega_dias,
            status="RECEBIDA",
            acima_media=acima_media,
            percentual_acima_media=percentual if acima_media else None,
            mensagem_alerta=mensagem
        )
        
        self.session.add(cotacao)
        await self.session.flush()
        return cotacao

    async def listar_cotacoes(self, solicitacao_id: uuid.UUID) -> List[CotacaoCompra]:
        """Lista cotações vinculadas a uma solicitação."""
        stmt = (
            select(CotacaoCompra)
            .where(
                CotacaoCompra.solicitacao_id == solicitacao_id,
                CotacaoCompra.tenant_id == self.tenant_id
            )
            .order_by(CotacaoCompra.valor_total.asc())
        )
        
        result = await self.session.execute(stmt)
        cotacoes = list(result.scalars().all())
        
        solicitacao = await self.session.get(SolicitacaoCompra, solicitacao_id)
        
        # Enriquecer com Score de Compra (Step 159)
        for cot in cotacoes:
            # Passar produto_id da solicitação para o cálculo do score
            res_score = await self.calcular_score_compra(cot, solicitacao.produto_id if solicitacao else None)
            cot.score_compra = res_score["score"]
            cot.classificacao_score = res_score["classificacao"]
            cot.motivos_score = res_score["motivos"]
            
        # Step 160: Ranking Comparativo
        # Ordenação: Score DESC -> Valor ASC -> Prazo ASC
        cotacoes.sort(key=lambda x: (
            -x.score_compra,
            x.valor_total,
            x.prazo_entrega_dias if x.prazo_entrega_dias is not None else 999
        ))
        
        for i, cot in enumerate(cotacoes):
            cot.posicao_ranking = i + 1
            cot.melhor_opcao = (i == 0)
            
            # Step 161: Gerar Explicação Textual
            expl = await self.gerar_explicacao_compra(cot)
            cot.explicacao_compra = expl["explicacao"]
            cot.pontos_fortes = expl["pontos_fortes"]
            cot.pontos_atencao = expl["pontos_atencao"]
            
        return cotacoes

    async def aprovar_cotacao(self, solicitacao_id: uuid.UUID, cotacao_id: uuid.UUID) -> Optional[PedidoCompra]:
        """Aprova uma cotação, recusa as outras e gera o pedido de compra."""
        from core.exceptions import BusinessRuleError

        # 1. Validar cotação e solicitação
        stmt_cot = select(CotacaoCompra).where(
            CotacaoCompra.id == cotacao_id,
            CotacaoCompra.tenant_id == self.tenant_id,
            CotacaoCompra.solicitacao_id == solicitacao_id
        )
        cotacao = (await self.session.execute(stmt_cot)).scalar_one_or_none()
        if not cotacao:
            return None

        solicitacao = await self.session.get(SolicitacaoCompra, solicitacao_id)
        if not solicitacao or solicitacao.status != "APROVADA":
            raise BusinessRuleError("A solicitação deve estar em status APROVADA.")

        # 2. Marcar cotação como APROVADA e outras como RECUSADA
        cotacao.status = "APROVADA"
        
        stmt_recusar = (
            select(CotacaoCompra)
            .where(
                CotacaoCompra.solicitacao_id == solicitacao_id,
                CotacaoCompra.id != cotacao_id
            )
        )
        outras = (await self.session.execute(stmt_recusar)).scalars().all()
        for o in outras:
            o.status = "RECUSADA"

        # 3. Calcular Economia (Savings) - Step 163
        # Savings = (Pior Preço - Preço Escolhido) * Quantidade
        todas_cotacoes = [cotacao.valor_unitario] + [o.valor_unitario for o in outras]
        pior_preco_unitario = max(todas_cotacoes)
        
        economia_unitaria = pior_preco_unitario - cotacao.valor_unitario
        economia_absoluta = economia_unitaria * solicitacao.quantidade_solicitada
        economia_percentual = (economia_unitaria / pior_preco_unitario * 100) if pior_preco_unitario > 0 else 0.0

        # 4. Criar Pedido de Compra
        pedido = PedidoCompra(
            tenant_id=self.tenant_id,
            solicitacao_id=solicitacao_id,
            cotacao_id=cotacao_id,
            fornecedor_nome=cotacao.fornecedor_nome,
            fornecedor_contato=cotacao.fornecedor_contato,
            item_id=solicitacao.produto_id,
            deposito_id=solicitacao.deposito_id,
            quantidade=solicitacao.quantidade_solicitada,
            unidade=solicitacao.unidade,
            valor_unitario=cotacao.valor_unitario,
            valor_total=cotacao.valor_total,
            status="ABERTO",
            economia_absoluta=economia_absoluta,
            economia_percentual=economia_percentual
        )
        
        self.session.add(pedido)
        await self.session.flush()
        return pedido

    async def listar_pedidos(self) -> List[PedidoCompra]:
        """Lista todos os pedidos de compra com dados enriquecidos."""
        from core.cadastros.produtos.models import Produto
        from operacional.models.estoque import Deposito
        
        stmt = (
            select(
                PedidoCompra,
                Produto.nome.label("item_nome"),
                Deposito.nome.label("deposito_nome")
            )
            .join(Produto, PedidoCompra.item_id == Produto.id)
            .join(Deposito, PedidoCompra.deposito_id == Deposito.id)
            .where(PedidoCompra.tenant_id == self.tenant_id)
            .order_by(PedidoCompra.created_at.desc())
        )
        
        result = await self.session.execute(stmt)
        items = []
        for row in result.all():
            ped, i_nome, d_nome = row
            ped.item_nome = i_nome
            ped.deposito_nome = d_nome
            items.append(ped)
            
        return items

    async def receber_pedido(
        self,
        pedido_id: uuid.UUID,
        data: RecebimentoCreate | None = None,
        recebido_por_id: uuid.UUID | None = None,
    ) -> PedidoCompra:
        """Marca o pedido como recebido e materializa recebimento + estoque."""
        # 1. Buscar pedido
        pedido = await self.session.get(PedidoCompra, pedido_id)
        if not pedido or pedido.tenant_id != self.tenant_id:
            return None

        if pedido.status == "RECEBIDO":
            return await self._enriquecer_pedido(pedido)  # Já recebido, idempotente

        item_pedido = await self._get_or_create_item_pedido_principal(pedido)
        recebimento_data = data or self._build_recebimento_fallback(pedido, item_pedido)

        # 2. Verificar se já existe movimentação para este pedido (idempotência extra)
        stmt_check = select(EstoqueMovimento).where(
            EstoqueMovimento.origem == "COMPRA",
            EstoqueMovimento.origem_id == pedido.id,
            EstoqueMovimento.tenant_id == self.tenant_id
        )
        existing_mov = (await self.session.execute(stmt_check)).scalar_one_or_none()

        recebimento = RecebimentoParcial(
            pedido_id=pedido.id,
            data_recebimento=datetime.now(timezone.utc),
            numero_nf=recebimento_data.numero_nf,
            chave_nfe=recebimento_data.chave_nfe,
            recebido_por_id=recebido_por_id,
            observacoes=recebimento_data.observacoes,
        )
        self.session.add(recebimento)
        await self.session.flush()

        if not existing_mov:
            for item_data in recebimento_data.itens:
                item_model = item_data if hasattr(item_data, "item_pedido_id") else type("ItemRecebimentoCompat", (), item_data)()
                item_alvo = item_pedido
                if getattr(item_model, "item_pedido_id", None):
                    item_alvo = await self.session.get(ItemPedidoCompra, item_model.item_pedido_id) or item_pedido

                lote_id, movimento = await self._materializar_item_recebimento(
                    pedido=pedido,
                    recebimento=recebimento_data,
                    item_pedido=item_alvo,
                    item_recebido=item_model,
                )

                item_recebimento = ItemRecebimento(
                    recebimento_id=recebimento.id,
                    item_pedido_id=item_alvo.id,
                    quantidade_recebida=float(item_model.quantidade_recebida),
                    preco_real_unitario=float(item_model.preco_real_unitario or 0.0) or self._resolver_custo_recebimento(pedido),
                    numero_lote_fornecedor=getattr(item_model, "numero_lote_fornecedor", None),
                    lote_id=lote_id,
                )
                self.session.add(item_recebimento)

                item_alvo.quantidade_recebida = float(item_alvo.quantidade_recebida or 0.0) + float(item_model.quantidade_recebida)
                item_alvo.preco_real_unitario = item_recebimento.preco_real_unitario
                item_alvo.status_item = "COMPLETO" if item_alvo.quantidade_recebida >= float(item_alvo.quantidade_solicitada or 0.0) else "PARCIAL"
                self.session.add(item_alvo)

                if movimento is not None:
                    logger.info(f"Entrada de estoque gerada para pedido {pedido.id}", movimento_id=str(movimento.id))

        # 4. Atualizar pedido
        pedido.status = "RECEBIDO"
        self.session.add(pedido)
        await self.session.flush()
        
        return await self._enriquecer_pedido(pedido)

    async def atualizar_status_pedido(self, pedido_id: uuid.UUID, novo_status: str) -> PedidoCompra:
        """Atualiza o status de um pedido de compra, com lógica especial para RECEBIDO."""
        if novo_status == "RECEBIDO":
            return await self.receber_pedido(pedido_id)
            
        pedido = await self.session.get(PedidoCompra, pedido_id)
        if not pedido or pedido.tenant_id != self.tenant_id:
            return None

        if novo_status == "CANCELADO" and pedido.status == "RECEBIDO":
            alertas_svc = AlertasAgricolasService(self.session, self.tenant_id)
            reversao_existe = await self._pedido_tem_reversao_operacional(pedido.id)
            if not reversao_existe:
                finding = alertas_svc.build_finding(
                    codigo="PEDIDO_RECEBIDO_CANCELADO_SEM_REVERSAO",
                    titulo="Pedido recebido cancelado sem reversão operacional",
                    severidade="RISCO_CRITICO",
                    origem="compras_pedidos",
                    total=1,
                    mensagem=(
                        "Nao e possivel cancelar um pedido ja recebido sem reversao operacional rastreavel. "
                        "Registre devolucao ou ajuste antes do cancelamento."
                    ),
                    amostras=[str(pedido.id)],
                    meta={"pedido_id": str(pedido.id), "status_atual": pedido.status},
                )
                await alertas_svc.registrar_e_aplicar_enforcement(
                    WorkflowGovernanceEvent(
                        finding=finding,
                        resource_id=str(pedido.id),
                        action="cancel_recv",
                        notify=True,
                        audit=True,
                        origem_id=f"pedido:{pedido.id}:cancel_without_reversal",
                    ),
                    allow_block=True,
                    error_message=(
                        "Nao e possivel cancelar pedido recebido sem reversao operacional. "
                        "Registre uma devolucao ou ajuste rastreavel antes do cancelamento."
                    ),
                )

        pedido.status = novo_status
        self.session.add(pedido)
        await self.session.flush()
        return await self._enriquecer_pedido(pedido)

    async def _enriquecer_pedido(self, pedido: PedidoCompra) -> PedidoCompra:
        """Adiciona nomes de item e depósito ao objeto do pedido."""
        from core.cadastros.produtos.models import Produto
        from operacional.models.estoque import Deposito
        
        p = await self.session.get(Produto, pedido.item_id)
        d = await self.session.get(Deposito, pedido.deposito_id)
        pedido.item_nome = p.nome if p else "N/A"
        pedido.deposito_nome = d.nome if d else "N/A"
        return pedido

    async def gerar_pdf_pedido(self, pedido_id: uuid.UUID) -> bytes:
        """Gera um PDF operacional do pedido de compra."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        import io

        # 1. Buscar dados
        pedido = await self.session.get(PedidoCompra, pedido_id)
        if not pedido or pedido.tenant_id != self.tenant_id:
            return None
            
        await self._enriquecer_pedido(pedido)
        
        # 2. Criar PDF em memória
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        styles = getSampleStyleSheet()
        
        # Estilos customizados
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.black,
            alignment=1, # Center
            spaceAfter=20
        )
        
        elements = []
        
        # Cabeçalho
        elements.append(Paragraph("PEDIDO DE COMPRA", title_style))
        elements.append(Spacer(1, 12))
        
        # Tabela de Dados Gerais
        data_geral = [
            ["ID do Pedido:", str(pedido.id)],
            ["Data do Pedido:", pedido.created_at.strftime("%d/%m/%Y %H:%M")],
            ["Status:", pedido.status]
        ]
        t_geral = Table(data_geral, colWidths=[100, 300])
        t_geral.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ('TEXTCOLOR', (0,0), (0,-1), colors.grey),
        ]))
        elements.append(t_geral)
        elements.append(Spacer(1, 20))
        
        # Dados do Fornecedor
        elements.append(Paragraph("<b>DADOS DO FORNECEDOR</b>", styles['Normal']))
        data_forn = [
            ["Fornecedor:", pedido.fornecedor_nome],
            ["Contato:", pedido.fornecedor_contato or "N/A"]
        ]
        t_forn = Table(data_forn, colWidths=[100, 300])
        t_forn.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
        ]))
        elements.append(t_forn)
        elements.append(Spacer(1, 20))
        
        # Itens do Pedido
        elements.append(Paragraph("<b>ITENS E ENTREGA</b>", styles['Normal']))
        header_itens = ["Item", "Qtd", "Un", "Vlr Unit", "Total"]
        row_itens = [
            pedido.item_nome,
            str(pedido.quantidade),
            pedido.unidade,
            f"R$ {pedido.valor_unitario:,.2f}",
            f"R$ {pedido.valor_total:,.2f}"
        ]
        
        t_itens = Table([header_itens, row_itens], colWidths=[180, 50, 40, 80, 80])
        t_itens.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
        ]))
        elements.append(t_itens)
        elements.append(Spacer(1, 20))
        
        # Local de Entrega
        elements.append(Paragraph(f"<b>Local de Entrega:</b> {pedido.deposito_nome}", styles['Normal']))
        
        doc.build(elements)
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content

    async def gerar_pdf_comparativo(self, solicitacao_id: uuid.UUID) -> Optional[bytes]:
        """Gera um PDF comparativo de cotações para uma solicitação (Step 162)."""
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        import io

        # 1. Buscar dados
        solicitacao = await self.session.get(SolicitacaoCompra, solicitacao_id)
        if not solicitacao or solicitacao.tenant_id != self.tenant_id:
            return None
            
        # Enriquecer solicitação com nomes legíveis
        from core.cadastros.produtos.models import Produto
        from operacional.models.estoque import Deposito
        p = await self.session.get(Produto, solicitacao.produto_id)
        d = await self.session.get(Deposito, solicitacao.deposito_id)
        item_nome = p.nome if p else "N/A"
        deposito_nome = d.nome if d else "N/A"
        
        cotacoes = await self.listar_cotacoes(solicitacao_id)
        
        # 2. Criar PDF em memória
        buffer = io.BytesIO()
        # Usar landscape para caber melhor a tabela comparativa
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
        styles = getSampleStyleSheet()
        
        # Estilos customizados
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.black,
            alignment=1, # Center
            spaceAfter=20
        )
        
        elements = []
        
        # Cabeçalho
        elements.append(Paragraph("MAPA COMPARATIVO DE COTAÇÕES", title_style))
        elements.append(Spacer(1, 12))
        
        # Dados da Solicitação
        data_sol = [
            [Paragraph(f"<b>Item:</b> {item_nome}", styles['Normal']), Paragraph(f"<b>Qtd:</b> {solicitacao.quantidade_solicitada} {solicitacao.unidade}", styles['Normal'])],
            [Paragraph(f"<b>Depósito:</b> {deposito_nome}", styles['Normal']), Paragraph(f"<b>Status:</b> {solicitacao.status}", styles['Normal'])]
        ]
        t_sol = Table(data_sol, colWidths=[400, 300])
        elements.append(t_sol)
        elements.append(Spacer(1, 20))
        
        # Tabela Comparativa
        header_table = ["Ranking", "Fornecedor", "Valor Unit", "Valor Total", "Prazo", "Score", "Classificação", "Melhor Opção"]
        rows = []
        for cot in cotacoes:
            rows.append([
                f"#{cot.posicao_ranking}",
                cot.fornecedor_nome,
                f"R$ {cot.valor_unitario:,.2f}",
                f"R$ {cot.valor_total:,.2f}",
                f"{cot.prazo_entrega_dias} dias" if cot.prazo_entrega_dias else "N/A",
                f"{cot.score_compra:.1f}",
                cot.classificacao_score,
                "SIM" if cot.melhor_opcao else ""
            ])
            
        t_comp = Table([header_table] + rows, colWidths=[60, 180, 80, 80, 60, 60, 100, 80])
        
        # Estilização da Tabela
        table_style_list = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#10b981")), # Verde Esmeralda (Marca Agro)
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]
        
        # Colorir linhas baseadas na classificação
        for i, cot in enumerate(cotacoes):
            if cot.melhor_opcao:
                table_style_list.append(('BACKGROUND', (0, i+1), (-1, i+1), colors.HexColor("#d1fae5")))
            elif cot.classificacao_score == "RUIM":
                 table_style_list.append(('TEXTCOLOR', (6, i+1), (6, i+1), colors.red))
                 
        t_comp.setStyle(TableStyle(table_style_list))
        elements.append(t_comp)
        elements.append(Spacer(1, 30))
        
        # Recomendação do Assistente (da melhor opção)
        melhor = next((c for c in cotacoes if c.melhor_opcao), None)
        if melhor:
            elements.append(Paragraph("<b>ANÁLISE E RECOMENDAÇÃO DO ASSISTENTE</b>", styles['Heading3']))
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(melhor.explicacao_compra, styles['Normal']))
            
            if melhor.pontos_fortes:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph("<b>Pontos Fortes:</b>", styles['Normal']))
                for p in melhor.pontos_fortes:
                    elements.append(Paragraph(f"• {p}", styles['Normal']))
            
            if melhor.pontos_atencao:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph("<b>Pontos de Atenção:</b>", styles['Normal']))
                for p in melhor.pontos_atencao:
                    elements.append(Paragraph(f"• {p}", styles['Normal']))
        
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    async def get_historico_precos(self, item_id: uuid.UUID) -> dict:
        """Retorna o histórico de preços de um item e estatísticas básicas."""
        # 1. Query para Cotações
        stmt_cot = (
            select(
                CotacaoCompra.fornecedor_nome,
                CotacaoCompra.valor_unitario,
                CotacaoCompra.created_at.label("data"),
                literal_column("'COTACAO'").label("origem")
            )
            .join(SolicitacaoCompra, CotacaoCompra.solicitacao_id == SolicitacaoCompra.id)
            .where(
                SolicitacaoCompra.produto_id == item_id,
                CotacaoCompra.tenant_id == self.tenant_id
            )
        )
        
        # 2. Query para Pedidos
        stmt_ped = (
            select(
                PedidoCompra.fornecedor_nome,
                PedidoCompra.valor_unitario,
                PedidoCompra.created_at.label("data"),
                literal_column("'PEDIDO'").label("origem")
            )
            .where(
                PedidoCompra.item_id == item_id,
                PedidoCompra.tenant_id == self.tenant_id
            )
        )
        
        # Unir ambas
        u = union_all(stmt_cot, stmt_ped).alias("historico_uniao")
        stmt_final = select(
            u.c.fornecedor_nome, 
            u.c.valor_unitario, 
            u.c.data, 
            u.c.origem
        ).order_by(u.c.data.asc())
        
        res = await self.session.execute(stmt_final)
        historico = []
        precos = []
        for row in res.all():
            historico.append({
                "fornecedor_nome": row.fornecedor_nome,
                "valor_unitario": row.valor_unitario,
                "data": row.data,
                "origem": row.origem
            })
            precos.append(row.valor_unitario)
            
        # 3. Agregações
        stats = {
            "menor_preco": min(precos) if precos else 0.0,
            "maior_preco": max(precos) if precos else 0.0,
            "preco_medio": sum(precos) / len(precos) if precos else 0.0,
            "historico": historico
        }
        
        return stats

    async def obter_melhor_fornecedor(self, item_id: uuid.UUID) -> Optional[dict]:
        """Calcula e sugere o melhor fornecedor para um item baseado no histórico."""
        stats = await self.get_historico_precos(item_id)
        historico = stats.get("historico", [])
        
        if not historico:
            return None
            
        # Agrupar por fornecedor
        fornecedores = {}
        for h in historico:
            f_nome = h["fornecedor_nome"]
            if f_nome not in fornecedores:
                fornecedores[f_nome] = {
                    "precos": [],
                    "datas": [],
                    "qtd": 0
                }
            fornecedores[f_nome]["precos"].append(h["valor_unitario"])
            fornecedores[f_nome]["datas"].append(h["data"])
            fornecedores[f_nome]["qtd"] += 1

        # Processar métricas por fornecedor
        processed = []
        for nome, data in fornecedores.items():
            avg = sum(data["precos"]) / len(data["precos"])
            last = data["precos"][-1] # Histórico agora vem ordenado por data asc
            last_date = data["datas"][-1]
            
            processed.append({
                "fornecedor_nome": nome,
                "preco_medio": avg,
                "ultimo_preco": last,
                "qtd_compras": data["qtd"],
                "data_ultima": last_date
            })

        if not processed:
            return None

        # Ignorar fornecedores com apenas 1 registro (se houver outros com mais)
        multi_registro = [p for p in processed if p["qtd_compras"] > 1]
        pool = multi_registro if multi_registro else processed

        # Calcular Scores
        min_avg = min(p["preco_medio"] for p in pool)
        max_qtd = max(p["qtd_compras"] for p in pool)
        
        # O último fornecedor geral (mais recente de todos)
        ultimo_geral_nome = historico[-1]["fornecedor_nome"]

        results = []
        for p in pool:
            # Score Preço (0.50): Menor preço médio = 1.0
            score_preco = (min_avg / p["preco_medio"]) * 0.50
            
            # Score Frequência (0.30): Mais compras = 1.0
            score_freq = (p["qtd_compras"] / max_qtd) * 0.30
            
            # Score Recência (0.20): Se foi o último = 1.0
            score_recencia = (1.0 if p["fornecedor_nome"] == ultimo_geral_nome else 0.2) * 0.20
            
            p["score"] = round(score_preco + score_freq + score_recencia, 2)
            results.append(p)

        # Ordenar por score desc
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[0] if results else None

    async def obter_preco_ideal(self, item_id: uuid.UUID) -> Optional[dict]:
        """Calcula a faixa de preço ideal sugerida para um item."""
        stats = await self.get_historico_precos(item_id)
        historico = stats.get("historico", [])
        
        if len(historico) < 2:
            return None
            
        preco_medio = stats["preco_medio"]
        menor_preco = stats["menor_preco"]
        
        return {
            "preco_minimo_referencia": menor_preco,
            "preco_ideal": preco_medio,
            "preco_maximo_recommended": preco_medio * 1.10,
            "base_calculo": "Histórico interno dos últimos registros"
        }

    async def obter_consistencia_fornecedores(self, item_id: uuid.UUID) -> List[dict]:
        """Analisa a estabilidade de preços por fornecedor para um item."""
        import statistics
        
        stats = await self.get_historico_precos(item_id)
        historico = stats.get("historico", [])
        
        # Agrupar por fornecedor
        fornecedores_precos = {}
        for h in historico:
            nome = h["fornecedor_nome"]
            if nome not in fornecedores_precos:
                fornecedores_precos[nome] = []
            fornecedores_precos[nome].append(h["valor_unitario"])
            
        results = []
        for nome, precos in fornecedores_precos.items():
            if len(precos) < 2:
                continue
                
            media = statistics.mean(precos)
            desvio = statistics.stdev(precos)
            variacao = (desvio / media) * 100 if media > 0 else 0
            
            if variacao <= 10:
                classificacao = "ESTAVEL"
            elif variacao <= 25:
                classificacao = "MODERADO"
            else:
                classificacao = "INSTAVEL"
                
            results.append({
                "fornecedor_nome": nome,
                "preco_medio": media,
                "desvio_padrao": desvio,
                "variacao_percentual": variacao,
                "classificacao": classificacao
            })
            
        return results

    async def calcular_score_compra(self, cotacao: CotacaoCompra, item_id: Optional[uuid.UUID] = None) -> dict:
        """
        Calcula o score de 0 a 100 para uma cotação baseado em múltiplos critérios.
        Retorna score, classificação e lista de motivos.
        """
        score = 0.0
        motivos = []
        
        # Tentar obter item_id se não fornecido
        if not item_id:
            try:
                # Tenta buscar via solicitação se o objeto tiver
                if hasattr(cotacao, 'solicitacao'):
                    item_id = cotacao.solicitacao.produto_id
                else:
                    # Busca pontual se necessário
                    sol = await self.session.get(SolicitacaoCompra, cotacao.solicitacao_id)
                    if sol:
                        item_id = sol.produto_id
            except Exception:
                pass

        # 1. Preço (Max 40)
        try:
            if not item_id:
                raise ValueError("ID do item não identificado")

            ideal = await self.obter_preco_ideal(item_id)
            if ideal and ideal.get("preco_ideal"):
                p_ideal = ideal["preco_ideal"]
                p_max = ideal.get("preco_maximo_recommended", p_ideal * 1.10)
                
                if cotacao.valor_unitario <= p_ideal:
                    score += 40
                    motivos.append("Preço excelente (abaixo ou igual à meta ideal)")
                elif cotacao.valor_unitario <= p_max:
                    score += 20
                    motivos.append("Preço dentro da faixa aceitável")
                else:
                    motivos.append("Preço acima do máximo recomendado")
            else:
                if not cotacao.acima_media:
                    score += 40
                    motivos.append("Preço competitivo (abaixo da média histórica)")
                else:
                    score += 10
                    motivos.append("Preço acima da média histórica")
        except Exception as e:
            print(f"DEBUG: Erro Preço: {e}")
            score += 20
            motivos.append("Base de comparação de preço indisponível")

        # 2. Consistência do Fornecedor (Max 30)
        try:
            if not item_id:
                raise ValueError("ID do item não identificado")
            consistencias = await self.obter_consistencia_fornecedores(item_id)
            f_cons = next((f for f in consistencias if f["fornecedor_nome"] == cotacao.fornecedor_nome), None)
            
            if f_cons:
                if f_cons["classificacao"] == "ESTAVEL":
                    score += 30
                    motivos.append("Fornecedor com preços historicamente estáveis")
                elif f_cons["classificacao"] == "MODERADO":
                    score += 15
                    motivos.append("Fornecedor com variação de preço moderada")
                else:
                    motivos.append("Fornecedor com alta instabilidade de preços")
            else:
                score += 15
                motivos.append("Histórico de consistência do fornecedor insuficiente")
        except Exception as e:
            score += 15

        # 3. Prazo de Entrega (Max 20)
        prazo = cotacao.prazo_entrega_dias
        if prazo is not None:
            if prazo <= 3:
                score += 20
                motivos.append("Entrega rápida (até 3 dias)")
            elif prazo <= 7:
                score += 10
                motivos.append("Prazo de entrega adequado")
            else:
                motivos.append("Prazo de entrega longo (> 7 dias)")
        else:
            score += 10
            motivos.append("Prazo de entrega não informado")

        # 4. Histórico/Recorrência (Max 10)
        try:
            if not item_id:
                raise ValueError("ID do item não identificado")
            melhor = await self.obter_melhor_fornecedor(item_id)
            if melhor and melhor.get("fornecedor_nome") == cotacao.fornecedor_nome:
                score += 10
                motivos.append("Fornecedor recomendado pelo histórico de compras")
            else:
                score += 5
                motivos.append("Fornecedor com histórico secundário")
        except Exception as e:
            score += 5

        # Classificação Final
        if score >= 80:
            classificacao = "BOA"
        elif score >= 50:
            classificacao = "ATENCAO"
        else:
            classificacao = "RUIM"
            
        return {
            "score": score,
            "classificacao": classificacao,
            "motivos": motivos
        }

    async def gerar_explicacao_compra(self, cotacao: CotacaoCompra) -> dict:
        """
        Gera uma explicação textual determinística para a cotação (Step 161).
        """
        fortes = []
        atencao = []
        
        # Analisar motivos existentes para categorizar em pontos fortes e de atenção
        motivos = getattr(cotacao, 'motivos_score', [])
        for m in motivos:
            m_lower = m.lower()
            if any(key in m_lower for key in ["competitivo", "estáveis", "rápida", "recomendado", "adequado", "estável", "excelente", "ideal"]):
                fortes.append(m)
            elif any(key in m_lower for key in ["acima", "instabilidade", "longo", "insuficiente", "não informado", "indisponível"]):
                atencao.append(m)

        classificacao = getattr(cotacao, 'classificacao_score', 'ATENCAO')
        nome = cotacao.fornecedor_nome

        if classificacao == "BOA":
            explicacao = f"O fornecedor {nome} é a melhor escolha técnica. Apresenta um histórico sólido de estabilidade e preços competitivos para este item."
        elif classificacao == "ATENCAO":
            explicacao = f"A proposta de {nome} é aceitável, mas requer atenção a detalhes como variação histórica ou prazo de entrega."
        else:
            explicacao = f"Não recomendamos a compra com {nome} no momento devido a preços fora da realidade de mercado ou histórico instável."

        return {
            "explicacao": explicacao,
            "pontos_fortes": fortes,
            "pontos_atencao": atencao
        }

    async def obter_economia_analytics(self) -> dict:
        """Calcula agregados de economia gerada pelo sistema (Step 163)."""
        from sqlalchemy import func
        from core.cadastros.produtos.models import Produto
        
        # Agregados Gerais
        stmt = (
            select(
                func.sum(PedidoCompra.economia_absoluta).label("total_absoluto"),
                func.avg(cast(PedidoCompra.economia_percentual, Numeric)).label("avg_percentual"),
                func.count(PedidoCompra.id).label("total_pedidos")
            )
            .where(
                PedidoCompra.tenant_id == self.tenant_id,
                PedidoCompra.economia_absoluta > 0
            )
        )
        
        exec_res = await self.session.execute(stmt)
        result = exec_res.one_or_none()
        
        # Melhor Decisão (Maior Economia Absoluta)
        stmt_best = (
            select(
                Produto.nome,
                PedidoCompra.economia_absoluta
            )
            .join(Produto, PedidoCompra.item_id == Produto.id)
            .where(PedidoCompra.tenant_id == self.tenant_id)
            .order_by(PedidoCompra.economia_absoluta.desc())
            .limit(1)
        )
        exec_best = await self.session.execute(stmt_best)
        best = exec_best.one_or_none()
        
        return {
            "economia_total": float(result.total_absoluto or 0.0) if result else 0.0,
            "economia_media_percentual": float(result.avg_percentual or 0.0) if result else 0.0,
            "total_pedidos": int(result.total_pedidos or 0) if result else 0,
            "melhor_decisao": {
                "item": best[0] if best else "N/A",
                "economia": float(best[1] or 0.0) if best else 0.0
            }
        }

    async def obter_serie_temporal_economia(self) -> List[dict]:
        """Calcula a evolução mensal da economia gerada (Step 164)."""
        from sqlalchemy import func
        
        # Agrupamento por mês (YYYY-MM) usando to_char do PostgreSQL
        periodo_col = func.to_char(PedidoCompra.created_at, 'YYYY-MM')
        
        stmt = (
            select(
                periodo_col.label("periodo"),
                func.sum(PedidoCompra.economia_absoluta).label("total_mes")
            )
            .where(
                PedidoCompra.tenant_id == self.tenant_id,
                PedidoCompra.economia_absoluta > 0
            )
            .group_by(periodo_col)
            .order_by(periodo_col.asc())
        )
        
        res = await self.session.execute(stmt)
        return [
            {"periodo": row.periodo, "economia_total": float(row.total_mes or 0.0)}
            for row in res.all()
        ]

    async def obter_economia_por_categoria(self) -> List[dict]:
        """Calcula o breakdown de economia por categoria de insumo (Step 165)."""
        from core.cadastros.produtos.models import Produto
        from sqlalchemy import func, case, text
        
        # Mapeamento simplificado de TipoProduto -> Categoria Macro (INSUMOS vs OPERACOES)
        tipo_insumos = ["SEMENTE", "DEFENSIVO", "FERTILIZANTE", "INOCULANTE", "ADJUVANTE", "RACAO", "MEDICAMENTO", "VACINA", "MINERAL"]
        tipo_operacoes = ["PECA", "LUBRIFICANTE", "COMBUSTIVEL", "MATERIAL_GERAL", "SERVICO"]
        
        categoria_macro = case(
            (Produto.tipo.in_(tipo_insumos), "INSUMOS"),
            (Produto.tipo.in_(tipo_operacoes), "OPERACOES"),
            else_="OUTROS"
        ).label("categoria_macro")

        # Total economizado pelo tenant para cálculo de percentual
        stmt_total = select(func.sum(PedidoCompra.economia_absoluta)).where(PedidoCompra.tenant_id == self.tenant_id)
        total_geral = (await self.session.execute(stmt_total)).scalar() or 0.0
        
        if total_geral == 0:
            return []

        stmt = (
            select(
                categoria_macro,
                func.sum(PedidoCompra.economia_absoluta).label("total_cat")
            )
            .join(Produto, PedidoCompra.item_id == Produto.id)
            .where(
                PedidoCompra.tenant_id == self.tenant_id,
                PedidoCompra.economia_absoluta > 0
            )
            .group_by(text("categoria_macro"))
            .order_by(func.sum(PedidoCompra.economia_absoluta).desc())
        )
        
        res = await self.session.execute(stmt)
        return [
            {
                "categoria": row.categoria_macro,
                "economia_total": float(row.total_cat or 0.0),
                "percentual": round((float(row.total_cat or 0.0) / total_geral) * 100, 1)
            }
            for row in res.all()
        ]

    async def obter_economia_por_fornecedor(self) -> list[dict]:
        """Calcula economia gerada agrupada por fornecedor (Step 167)."""
        stmt_total = select(func.sum(PedidoCompra.economia_absoluta)).where(
            PedidoCompra.tenant_id == self.tenant_id,
            PedidoCompra.economia_absoluta > 0
        )
        total_geral = (await self.session.execute(stmt_total)).scalar() or 0.0

        if total_geral == 0:
            return []

        stmt = (
            select(
                PedidoCompra.fornecedor_nome,
                func.sum(PedidoCompra.economia_absoluta).label("economia_total"),
                func.count(PedidoCompra.id).label("total_pedidos")
            )
            .where(
                PedidoCompra.tenant_id == self.tenant_id,
                PedidoCompra.economia_absoluta > 0,
                PedidoCompra.fornecedor_nome.isnot(None)
            )
            .group_by(PedidoCompra.fornecedor_nome)
            .order_by(func.sum(PedidoCompra.economia_absoluta).desc())
        )

        res = await self.session.execute(stmt)
        return [
            {
                "fornecedor_nome": row.fornecedor_nome,
                "economia_total": float(row.economia_total or 0.0),
                "economia_percentual": round((float(row.economia_total or 0.0) / float(total_geral)) * 100, 1),
                "total_pedidos": row.total_pedidos,
            }
            for row in res.all()
        ]

    async def obter_economia_por_usuario(self) -> list[dict]:
        """Calcula economia gerada por cada comprador (Step 166)."""
        from core.models.auth import Usuario

        # Total geral do tenant para cálculo de percentual
        stmt_total = select(func.sum(PedidoCompra.economia_absoluta)).where(
            PedidoCompra.tenant_id == self.tenant_id,
            PedidoCompra.economia_absoluta > 0
        )
        total_geral = (await self.session.execute(stmt_total)).scalar() or 0.0

        if total_geral == 0:
            return []

        stmt = (
            select(
                PedidoCompra.usuario_solicitante_id,
                func.coalesce(Usuario.nome_completo, Usuario.username, "Sem Responsável").label("usuario_nome"),
                func.sum(PedidoCompra.economia_absoluta).label("economia_total"),
                func.count(PedidoCompra.id).label("total_pedidos")
            )
            .outerjoin(Usuario, PedidoCompra.usuario_solicitante_id == Usuario.id)
            .where(
                PedidoCompra.tenant_id == self.tenant_id,
                PedidoCompra.economia_absoluta > 0
            )
            .group_by(PedidoCompra.usuario_solicitante_id, Usuario.nome_completo, Usuario.username)
            .order_by(func.sum(PedidoCompra.economia_absoluta).desc())
        )

        res = await self.session.execute(stmt)
        return [
            {
                "usuario_id": row.usuario_solicitante_id,
                "usuario_nome": row.usuario_nome,
                "economia_total": float(row.economia_total or 0.0),
                "economia_percentual": round((float(row.economia_total or 0.0) / float(total_geral)) * 100, 1),
                "total_pedidos": row.total_pedidos,
            }
            for row in res.all()
        ]
