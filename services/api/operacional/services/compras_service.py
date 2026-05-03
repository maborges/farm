import uuid
from typing import List, Optional
from sqlalchemy import select, func, union_all, literal_column
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from operacional.models.compras import SolicitacaoCompra, CotacaoCompra, PedidoCompra
from operacional.schemas.compras import SolicitacaoCompraCreate, CotacaoSolicitacaoCreate
from operacional.services.estoque_service import EstoqueService
from operacional.schemas.estoque import EntradaEstoqueRequest
from operacional.models.estoque import EstoqueMovimento

class ComprasService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

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

        # Lógica de Inteligência: Alerta de preço acima da média
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
        return list(result.scalars().all())

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

        # 3. Criar Pedido de Compra
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
            status="ABERTO"
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

    async def receber_pedido(self, pedido_id: uuid.UUID) -> PedidoCompra:
        """Marca o pedido como recebido e gera entrada automática no estoque."""
        from core.exceptions import BusinessRuleError

        # 1. Buscar pedido
        pedido = await self.session.get(PedidoCompra, pedido_id)
        if not pedido or pedido.tenant_id != self.tenant_id:
            return None

        if pedido.status == "RECEBIDO":
            return pedido # Já recebido, idempotente

        # 2. Verificar se já existe movimentação para este pedido (idempotência extra)
        stmt_check = select(EstoqueMovimento).where(
            EstoqueMovimento.origem == "COMPRA",
            EstoqueMovimento.origem_id == pedido.id,
            EstoqueMovimento.tenant_id == self.tenant_id
        )
        existing_mov = (await self.session.execute(stmt_check)).scalar_one_or_none()
        
        if not existing_mov:
            # 3. Gerar entrada no estoque
            estoque_svc = EstoqueService(self.session, self.tenant_id)
            entrada_req = EntradaEstoqueRequest(
                deposito_id=pedido.deposito_id,
                produto_id=pedido.item_id,
                quantidade=pedido.quantidade,
                custo_unitario=pedido.valor_unitario,
                motivo=f"Recebimento de Pedido {pedido.id}",
                origem_id=pedido.id,
                origem_tipo="COMPRA"
            )
            await estoque_svc.registrar_entrada(entrada_req)
            logger.info(f"Entrada de estoque gerada para pedido {pedido.id}")

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
        
        # Rodapé
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("-" * 50, styles['Normal']))
        elements.append(Paragraph("Documento Operacional Gerado pelo AgroSaaS", styles['Normal']))
        
        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()
        
        return pdf

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
        ).order_by(u.c.data.desc())
        
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
