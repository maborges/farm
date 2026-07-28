import uuid
import re
import secrets
import bcrypt
from datetime import date, timedelta
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, func, union_all, literal_column, cast, Numeric, or_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from agricola.alertas.service import AlertasAgricolasService, WorkflowGovernanceEvent
from core.config import settings
from core.exceptions import BusinessRuleError
from core.services.email_service import email_service
from core.models.tenant import Tenant
from core.services.sequencial_service import SequencialService
from operacional.models.compras import (
    SolicitacaoCompra,
    SolicitacaoItem,
    CotacaoCompra,
    CotacaoItem,
    AlocacaoItem,
    PedidoCompra,
    ItemPedidoCompra,
    RecebimentoParcial,
    ItemRecebimento,
    DevolucaoFornecedor,
    ItemDevolucao,
    PedidoConfirmacaoFornecedor,
)
from operacional.schemas.compras import (
    SolicitacaoCompraCreate,
    SolicitacaoItemCreate,
    CotacaoSolicitacaoCreate,
    RecebimentoCreate,
)
from core.cadastros.produtos.models import Produto
from financeiro.models.despesa import Despesa
from financeiro.models.plano_conta import PlanoConta
from financeiro.schemas.despesa_schema import DespesaCreate
from financeiro.services.despesa_service import DespesaService
from operacional.services.estoque_service import EstoqueService
from operacional.schemas.estoque import EntradaEstoqueRequest, LoteCreate, AjusteMovimentoRequest
from operacional.models.estoque import Deposito, EstoqueMovimento, LoteEstoque, SaldoEstoque
from operacional.models.compras import Fornecedor
from core.cadastros.pessoas.models import Pessoa, PessoaDocumento, PessoaRelacionamento, TipoRelacionamento
from operacional.services.fornecedores_service import resolve_fornecedor, obter_dados_exibicao_fornecedor
from operacional.services.estoque_ledger import registrar_ledger_estoque

class ComprasService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    def _resolver_custo_recebimento(self, item_pedido: "ItemPedidoCompra") -> float:
        """Guardrail de valuation: recebimento de compra usa o valor cotado do
        item como custo operacional, sem consultar nem reescrever `Produto.preco_medio`."""
        return float(item_pedido.preco_estimado_unitario or 0.0)

    def _parse_condicoes_pagamento_em_dias(self, condicoes_pagamento: str | None) -> int | None:
        if not condicoes_pagamento:
            return None
        match = re.search(r"(\d+)", condicoes_pagamento)
        if not match:
            return None
        dias = int(match.group(1))
        return dias if dias >= 0 else None

    async def _montar_fornecedor_response(self, fornecedor: Fornecedor) -> dict:
        dados = await obter_dados_exibicao_fornecedor(self.session, fornecedor.pessoa_id)
        return {
            "id": fornecedor.id,
            "pessoa_id": fornecedor.pessoa_id,
            "nome_fantasia": dados["nome_fantasia"],
            "razao_social": dados["razao_social"],
            "cnpj_cpf": dados["cnpj_cpf"],
            "email": dados["email"],
            "telefone": dados["telefone"],
            "condicoes_pagamento": fornecedor.condicoes_pagamento,
            "prazo_entrega_dias": fornecedor.prazo_entrega_dias,
            "avaliacao": fornecedor.avaliacao,
        }

    async def listar_fornecedores(self, q: str | None = None) -> list[dict]:
        """Lista toda Pessoa com papel FORNECEDOR — não só quem já tem linha
        em compras_fornecedores. Uma pessoa pode ser marcada como fornecedor
        direto no cadastro de Pessoas, sem nunca ter passado pela tela de
        Compras; ela precisa aparecer aqui do mesmo jeito. A linha em
        compras_fornecedores (dados comerciais: condições de pagamento etc.)
        é criada sob demanda na primeira vez que a pessoa aparece nesta lista."""
        stmt = (
            select(Pessoa)
            .join(PessoaRelacionamento, PessoaRelacionamento.pessoa_id == Pessoa.id)
            .join(TipoRelacionamento, TipoRelacionamento.id == PessoaRelacionamento.tipo_id)
            .where(
                Pessoa.tenant_id == self.tenant_id,
                Pessoa.ativo == True,
                TipoRelacionamento.codigo == "FORNECEDOR",
            )
        )
        if q:
            termo = f"%{q.strip()}%"
            doc_subq = select(PessoaDocumento.pessoa_id).where(PessoaDocumento.numero.ilike(termo))
            stmt = stmt.where(or_(Pessoa.nome_exibicao.ilike(termo), Pessoa.id.in_(doc_subq)))
        stmt = stmt.order_by(Pessoa.nome_exibicao).limit(20)
        pessoas = (await self.session.execute(stmt)).scalars().all()

        resultado = []
        for pessoa in pessoas:
            fornecedor_stmt = select(Fornecedor).where(
                Fornecedor.pessoa_id == pessoa.id, Fornecedor.tenant_id == self.tenant_id
            ).limit(1)
            fornecedor = (await self.session.execute(fornecedor_stmt)).scalar_one_or_none()
            if fornecedor is None:
                fornecedor = Fornecedor(tenant_id=self.tenant_id, pessoa_id=pessoa.id)
                self.session.add(fornecedor)
                await self.session.flush()
            resultado.append(await self._montar_fornecedor_response(fornecedor))
        return resultado

    async def obter_fornecedor_orm(self, fornecedor_id: uuid.UUID) -> Fornecedor | None:
        stmt = select(Fornecedor).where(
            Fornecedor.id == fornecedor_id, Fornecedor.tenant_id == self.tenant_id
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def obter_fornecedor(self, fornecedor_id: uuid.UUID) -> dict | None:
        fornecedor = await self.obter_fornecedor_orm(fornecedor_id)
        if not fornecedor:
            return None
        return await self._montar_fornecedor_response(fornecedor)

    async def _buscar_ultimo_recebimento(self, pedido_id: uuid.UUID) -> RecebimentoParcial | None:
        stmt = (
            select(RecebimentoParcial)
            .where(RecebimentoParcial.pedido_id == pedido_id)
            .order_by(RecebimentoParcial.data_recebimento.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _resolver_ou_criar_fornecedor_por_nome(
        self, nome: str, contato: str | None = None
    ) -> Fornecedor:
        stmt = (
            select(Fornecedor)
            .join(Pessoa, Pessoa.id == Fornecedor.pessoa_id)
            .where(Fornecedor.tenant_id == self.tenant_id, Pessoa.nome_exibicao == nome)
            .limit(1)
        )
        fornecedor = (await self.session.execute(stmt)).scalar_one_or_none()
        if fornecedor is None:
            pessoa = await resolve_fornecedor(
                self.session, self.tenant_id, nome_fantasia=nome, telefone=contato
            )
            fornecedor = Fornecedor(tenant_id=self.tenant_id, pessoa_id=pessoa.id)
            self.session.add(fornecedor)
            await self.session.flush()

        return fornecedor

    async def _resolver_fornecedor_financeiro(
        self,
        pedido: PedidoCompra,
    ) -> tuple[uuid.UUID | None, str | None, Fornecedor | None]:
        fornecedor = (
            await self.session.get(Fornecedor, pedido.fornecedor_id)
            if pedido.fornecedor_id is not None
            else None
        )
        if fornecedor is None:
            # Legado/teste: pedido sem fornecedor_id vinculado — tenta casar por nome.
            stmt = (
                select(Fornecedor)
                .join(Pessoa, Pessoa.id == Fornecedor.pessoa_id)
                .where(Fornecedor.tenant_id == self.tenant_id, Pessoa.nome_exibicao == pedido.fornecedor_nome)
                .limit(1)
            )
            fornecedor = (await self.session.execute(stmt)).scalar_one_or_none()
        if fornecedor is None:
            return None, pedido.fornecedor_nome, None

        pessoa = await self.session.get(Pessoa, fornecedor.pessoa_id)
        nome = pessoa.nome_exibicao if pessoa else pedido.fornecedor_nome
        return fornecedor.pessoa_id, nome, fornecedor

    async def _resolver_plano_conta_por_categoria(self, categoria_id: uuid.UUID | None) -> uuid.UUID | None:
        """Sobe a árvore de CategoriaProduto (produto → categoria → ... → raiz)
        até achar um PlanoConta do tenant vinculado (categoria_produto_id).
        Substitui o mapeamento fixo por Produto.tipo quando o tenant já
        configurou o vínculo categoria→plano de contas."""
        from core.cadastros.produtos.models import CategoriaProduto

        atual_id = categoria_id
        visitados = set()
        for _ in range(10):  # guardrail contra ciclo acidental na árvore
            if atual_id is None or atual_id in visitados:
                break
            visitados.add(atual_id)

            stmt = (
                select(PlanoConta.id)
                .where(
                    PlanoConta.tenant_id == self.tenant_id,
                    PlanoConta.categoria_produto_id == atual_id,
                    PlanoConta.tipo == "DESPESA",
                    PlanoConta.natureza == "ANALITICA",
                    PlanoConta.ativo == True,
                )
                .limit(1)
            )
            plano_id = (await self.session.execute(stmt)).scalar_one_or_none()
            if plano_id is not None:
                return plano_id

            categoria = await self.session.get(CategoriaProduto, atual_id)
            atual_id = categoria.parent_id if categoria else None
        return None

    async def _resolver_plano_conta_compra(self, produto: Produto) -> uuid.UUID | None:
        plano_por_categoria = await self._resolver_plano_conta_por_categoria(produto.categoria_id)
        if plano_por_categoria is not None:
            return plano_por_categoria

        # Fallback legado: mapeamento fixo por Produto.tipo, usado enquanto o
        # tenant não vincula PlanoConta.categoria_produto_id às categorias.
        codigo_por_tipo = {
            "SEMENTE": "3.01",
            "INOCULANTE": "3.01",
            "FERTILIZANTE": "3.02",
            "DEFENSIVO": "3.03",
            "ADJUVANTE": "3.03",
            "COMBUSTIVEL": "3.04",
            "LUBRIFICANTE": "3.04",
            "PECA": "3.06",
            "RACAO": "3.12",
            "MINERAL": "3.12",
            "MEDICAMENTO": "3.13",
            "VACINA": "3.13",
            "SERVICO": "3.14",
        }
        codigo = codigo_por_tipo.get((produto.tipo or "").upper())

        if codigo:
            stmt = (
                select(PlanoConta.id)
                .where(
                    PlanoConta.tenant_id == self.tenant_id,
                    PlanoConta.codigo == codigo,
                    PlanoConta.tipo == "DESPESA",
                    PlanoConta.natureza == "ANALITICA",
                    PlanoConta.ativo == True,
                )
                .limit(1)
            )
            plano_id = (await self.session.execute(stmt)).scalar_one_or_none()
            if plano_id is not None:
                return plano_id

        stmt_fallback = (
            select(PlanoConta.id)
            .where(
                PlanoConta.tenant_id == self.tenant_id,
                PlanoConta.tipo == "DESPESA",
                PlanoConta.categoria_rfb == "CUSTEIO",
                PlanoConta.natureza == "ANALITICA",
                PlanoConta.ativo == True,
            )
            .order_by(PlanoConta.codigo.asc())
            .limit(1)
        )
        return (await self.session.execute(stmt_fallback)).scalar_one_or_none()

    async def _garantir_despesa_financeira_compra(
        self,
        pedido: PedidoCompra,
        *,
        recebimento: RecebimentoParcial | None = None,
    ) -> Despesa | None:
        """Gera uma Despesa por recebimento (não por pedido), já que um pedido
        pode ter múltiplas notas fiscais/recebimentos parciais, cada um com seu
        próprio vencimento. A idempotência é chaveada por origem_id=recebimento.id."""
        recebimento = recebimento or await self._buscar_ultimo_recebimento(pedido.id)
        if recebimento is None:
            return None

        existente = (
            await self.session.execute(
                select(Despesa).where(
                    Despesa.tenant_id == self.tenant_id,
                    Despesa.origem_tipo == "COMPRA",
                    Despesa.origem_id == recebimento.id,
                    Despesa.ativo == True,
                ).limit(1)
            )
        ).scalar_one_or_none()
        if existente is not None:
            return existente

        valor_recebimento = (
            await self.session.execute(
                select(func.coalesce(func.sum(ItemRecebimento.quantidade_recebida * ItemRecebimento.preco_real_unitario), 0.0))
                .where(ItemRecebimento.recebimento_id == recebimento.id)
            )
        ).scalar_one()
        valor_recebimento = float(valor_recebimento or 0.0) or float(pedido.valor_total or 0.0)
        if valor_recebimento <= 0:
            # Recebimento sem valuation (custo unitário zerado) — nada a pagar,
            # não há Despesa para gerar. O alerta de "sem valuation" já é
            # emitido em outro fluxo (ver _registrar_evento_recebimento_critico).
            return None

        abatimento_adiantamento = 0.0
        adiantamento_restante = float(pedido.valor_adiantamento or 0.0)
        if adiantamento_restante > 0:
            abatimento_adiantamento = min(adiantamento_restante, valor_recebimento)
            valor_recebimento -= abatimento_adiantamento
            pedido.valor_adiantamento = adiantamento_restante - abatimento_adiantamento
            self.session.add(pedido)

        item_principal = await self._get_or_create_item_pedido_principal(pedido)
        deposito = await self.session.get(Deposito, item_principal.deposito_id)
        produto = await self.session.get(Produto, item_principal.produto_id)
        if not deposito or deposito.tenant_id != self.tenant_id:
            raise BusinessRuleError("Deposito do pedido indisponível para integração financeira da compra.")
        if not produto or produto.tenant_id != self.tenant_id:
            raise BusinessRuleError("Produto do pedido indisponível para integração financeira da compra.")

        plano_conta_id = await self._resolver_plano_conta_compra(produto)
        if plano_conta_id is None:
            raise BusinessRuleError("Nenhum plano de contas de despesa analítica foi encontrado para integrar a compra.")

        data_base = (
            recebimento.data_recebimento.date()
            if recebimento.data_recebimento is not None
            else date.today()
        )

        pessoa_id, fornecedor_nome, fornecedor = await self._resolver_fornecedor_financeiro(pedido)
        dias_pagamento = self._parse_condicoes_pagamento_em_dias(
            fornecedor.condicoes_pagamento if fornecedor is not None else pedido.condicoes_pagamento
        )
        data_vencimento = data_base + timedelta(days=dias_pagamento or 0)

        payload = DespesaCreate(
            unidade_produtiva_id=deposito.unidade_produtiva_id,
            plano_conta_id=plano_conta_id,
            descricao=f"Compra de {produto.nome} (NF {recebimento.numero_nf or 's/n'})",
            valor_total=valor_recebimento,
            data_emissao=data_base,
            data_vencimento=data_vencimento,
            competencia=data_base.replace(day=1),
            status="A_PAGAR",
            pessoa_id=pessoa_id,
            fornecedor=fornecedor_nome or pedido.fornecedor_nome,
            observacoes=(
                f"Despesa automática do recebimento {recebimento.id} do pedido {pedido.id}."
                + (f" Abatido adiantamento de {_formatar_moeda_brl(abatimento_adiantamento)}." if abatimento_adiantamento > 0 else "")
            ),
            numero_nf=recebimento.numero_nf,
            chave_nfe=recebimento.chave_nfe,
            nota_fiscal=recebimento.numero_nf,
            origem_id=recebimento.id,
            origem_tipo="COMPRA",
            rateios=[],
        )
        despesas = await DespesaService(self.session, self.tenant_id).create_with_rateio(payload)
        return despesas[0] if despesas else None

    async def _get_or_create_item_pedido_principal(self, pedido: PedidoCompra) -> ItemPedidoCompra:
        """Retorna o primeiro item do pedido — todo PedidoCompra criado pelo
        fluxo atual (aprovar_cotacao/gerar_pedidos_de_alocacoes) sempre grava
        ao menos 1 ItemPedidoCompra, então isso nunca deveria faltar."""
        stmt = (
            select(ItemPedidoCompra)
            .where(ItemPedidoCompra.pedido_id == pedido.id)
            .order_by(ItemPedidoCompra.id.asc())
            .limit(1)
        )
        item = (await self.session.execute(stmt)).scalar_one_or_none()
        if item is None:
            raise BusinessRuleError("Pedido sem itens — dados inconsistentes.")
        return item

    async def _build_recebimento_fallback(self, pedido: PedidoCompra, item_pedido: ItemPedidoCompra) -> RecebimentoCreate:
        """Recebimento sem corpo explícito: recebe TODOS os itens do pedido
        integralmente, ao preço cotado (custo real vem do fluxo explícito
        via RecebimentoCreate.itens quando o chamador informar valores reais)."""
        stmt = select(ItemPedidoCompra).where(ItemPedidoCompra.pedido_id == pedido.id)
        itens_pedido = (await self.session.execute(stmt)).scalars().all() or [item_pedido]

        return RecebimentoCreate(
            numero_nf=None,
            chave_nfe=None,
            observacoes="Recebimento materializado por compatibilidade no fluxo legado.",
            itens=[
                {
                    "item_pedido_id": ip.id,
                    "quantidade_recebida": ip.quantidade_solicitada,
                    "preco_real_unitario": ip.preco_estimado_unitario or self._resolver_custo_recebimento(ip),
                    "numero_lote_fornecedor": None,
                    "lote_id": None,
                }
                for ip in itens_pedido
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
        custo_unitario = float(item_recebido.preco_real_unitario or 0.0) or self._resolver_custo_recebimento(item_pedido)
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

        _, _, fornecedor = await self._resolver_fornecedor_financeiro(pedido)
        if fornecedor is None:
            await self._registrar_evento_recebimento_critico(
                pedido=pedido,
                codigo="RECEBIMENTO_COMPRA_SEM_FORNECEDOR_CADASTRADO_NOVO_FLUXO",
                titulo="Recebimento sem fornecedor cadastrado vinculado",
                mensagem=(
                    f"Nao foi encontrado cadastro de Fornecedor para '{pedido.fornecedor_nome}'. "
                    "Cadastre o fornecedor em Compras > Fornecedores antes de receber este pedido."
                ),
                meta={"item_pedido_id": str(item_pedido.id), "fornecedor_nome": pedido.fornecedor_nome},
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
                    produto_id=item_pedido.produto_id,
                    deposito_id=item_pedido.deposito_id,
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
                    deposito_id=item_pedido.deposito_id,
                    produto_id=item_pedido.produto_id,
                    fornecedor_id=fornecedor.id,
                    quantidade=quantidade,
                    custo_unitario=custo_unitario,
                    motivo=f"Recebimento de Pedido {pedido.numero or pedido.id}",
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
                    SaldoEstoque.deposito_id == item_pedido.deposito_id,
                    SaldoEstoque.produto_id == item_pedido.produto_id,
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

    async def criar_solicitacao(
        self, data: SolicitacaoCompraCreate, solicitante_id: uuid.UUID | None = None,
    ) -> SolicitacaoCompra:
        """Cria uma nova solicitação de compra interna (pode ter vários itens).

        `solicitante_id` é quem pediu — só ele poderá encerrar a solicitação
        (ver encerrar_solicitacao)."""
        numero = await SequencialService(self.session, self.tenant_id).proximo_numero("compras_solicitacao")
        primeiro = data.itens[0]
        obj = SolicitacaoCompra(
            tenant_id=self.tenant_id,
            numero=numero,
            solicitante_id=solicitante_id,
            # campos escalares deprecated, espelham o primeiro item p/ telas legadas
            produto_id=primeiro.produto_id,
            deposito_id=primeiro.deposito_id,
            quantidade_solicitada=primeiro.quantidade_solicitada,
            unidade=primeiro.unidade,
            origem=data.origem,
            origem_id=data.origem_id,
            status="ABERTA"
        )
        self.session.add(obj)
        await self.session.flush()

        for item in data.itens:
            self.session.add(SolicitacaoItem(
                solicitacao_id=obj.id,
                produto_id=item.produto_id,
                deposito_id=item.deposito_id,
                quantidade_solicitada=item.quantidade_solicitada,
                unidade=item.unidade,
            ))
        await self.session.flush()
        obj.itens = await self._enriquecer_itens_solicitacao(obj.id)
        await self._enriquecer_solicitante_nome(obj)
        return obj

    async def _enriquecer_solicitante_nome(self, obj: SolicitacaoCompra) -> SolicitacaoCompra:
        from core.models.auth import Usuario
        obj.solicitante_nome = None
        if obj.solicitante_id:
            stmt = select(Usuario.nome_completo).where(Usuario.id == obj.solicitante_id)
            obj.solicitante_nome = (await self.session.execute(stmt)).scalar_one_or_none()
        return obj

    async def _enriquecer_itens_solicitacao(self, solicitacao_id: uuid.UUID) -> List[SolicitacaoItem]:
        from core.cadastros.produtos.models import Produto
        from operacional.models.estoque import Deposito

        stmt = (
            select(SolicitacaoItem, Produto.nome, Deposito.nome)
            .join(Produto, SolicitacaoItem.produto_id == Produto.id)
            .join(Deposito, SolicitacaoItem.deposito_id == Deposito.id)
            .where(SolicitacaoItem.solicitacao_id == solicitacao_id)
        )
        result = await self.session.execute(stmt)
        itens = []
        for item, p_nome, d_nome in result.all():
            item.produto_nome = p_nome
            item.deposito_nome = d_nome
            itens.append(item)

        if not itens:
            return itens

        stmt_aloc = (
            select(AlocacaoItem.solicitacao_item_id, func.coalesce(func.sum(AlocacaoItem.quantidade_alocada), 0.0))
            .where(AlocacaoItem.solicitacao_item_id.in_([i.id for i in itens]))
            .group_by(AlocacaoItem.solicitacao_item_id)
        )
        alocado_por_item = dict((await self.session.execute(stmt_aloc)).all())
        await self._preencher_ultima_compra_itens(itens)

        for item in itens:
            item.quantidade_alocada = alocado_por_item.get(item.id, 0.0)
            if item.quantidade_alocada <= 0:
                item.status_atendimento = "PENDENTE"
            elif item.quantidade_alocada >= item.quantidade_solicitada:
                item.status_atendimento = "ATENDIDO"
            else:
                item.status_atendimento = "PARCIAL"

        return itens

    async def _preencher_ultima_compra_itens(self, itens: List[SolicitacaoItem]) -> None:
        produto_ids = {item.produto_id for item in itens}
        if not produto_ids:
            return

        ultimas = (
            select(
                ItemPedidoCompra.produto_id.label("produto_id"),
                ItemPedidoCompra.preco_estimado_unitario.label("valor_unitario"),
                PedidoCompra.created_at.label("data_compra"),
                func.row_number().over(
                    partition_by=ItemPedidoCompra.produto_id,
                    order_by=PedidoCompra.created_at.desc(),
                ).label("rn"),
            )
            .join(PedidoCompra, ItemPedidoCompra.pedido_id == PedidoCompra.id)
            .where(
                PedidoCompra.tenant_id == self.tenant_id,
                ItemPedidoCompra.produto_id.in_(produto_ids),
            )
        ).subquery()

        rows = await self.session.execute(
            select(ultimas.c.produto_id, ultimas.c.valor_unitario, ultimas.c.data_compra)
            .where(ultimas.c.rn == 1)
        )
        por_produto = {row.produto_id: row for row in rows.all()}

        for item in itens:
            row = por_produto.get(item.produto_id)
            item.valor_ultima_compra = float(row.valor_unitario) if row is not None and row.valor_unitario is not None else None
            item.data_ultima_compra = row.data_compra if row is not None else None

    async def listar_solicitacoes(
        self,
        status: Optional[str] = None,
        produto_id: Optional[uuid.UUID] = None,
        deposito_id: Optional[uuid.UUID] = None
    ) -> List[SolicitacaoCompra]:
        """Lista solicitações de compra com filtros e dados enriquecidos."""
        from core.cadastros.produtos.models import Produto
        from operacional.models.estoque import Deposito

        stmt = select(SolicitacaoCompra).where(SolicitacaoCompra.tenant_id == self.tenant_id)

        if status:
            stmt = stmt.where(SolicitacaoCompra.status == status)
        if produto_id or deposito_id:
            stmt = stmt.join(SolicitacaoItem, SolicitacaoItem.solicitacao_id == SolicitacaoCompra.id)
            if produto_id:
                stmt = stmt.where(SolicitacaoItem.produto_id == produto_id)
            if deposito_id:
                stmt = stmt.where(SolicitacaoItem.deposito_id == deposito_id)

        stmt = stmt.order_by(SolicitacaoCompra.created_at.desc()).distinct()

        result = await self.session.execute(stmt)
        solicitacoes = list(result.scalars().all())

        for sol in solicitacoes:
            sol.itens = await self._enriquecer_itens_solicitacao(sol.id)
            if sol.itens:
                sol.produto_nome = sol.itens[0].produto_nome
                sol.deposito_nome = sol.itens[0].deposito_nome
            await self._enriquecer_solicitante_nome(sol)

        return solicitacoes

    async def atualizar_status(self, solicitacao_id: uuid.UUID, novo_status: str) -> SolicitacaoCompra:
        """Atualiza o status de uma solicitação de compra."""
        from core.exceptions import BusinessRuleError

        stmt = select(SolicitacaoCompra).where(
            SolicitacaoCompra.id == solicitacao_id,
            SolicitacaoCompra.tenant_id == self.tenant_id
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()

        if not obj:
            return None

        if novo_status == "CANCELADA":
            pedidos = (
                await self.session.execute(
                    select(PedidoCompra).where(PedidoCompra.solicitacao_id == solicitacao_id)
                )
            ).scalars().all()
            if any(p.status == "RECEBIDO" for p in pedidos):
                raise BusinessRuleError(
                    "Esta solicitação já tem pedido(s) recebido(s) — não é possível cancelar. "
                    "Trate a devolução pelo próprio pedido, se necessário."
                )
            for pedido in pedidos:
                if pedido.status != "CANCELADO":
                    pedido.status = "CANCELADO"
                    self.session.add(pedido)

        obj.status = novo_status
        await self.session.flush()

        obj.itens = await self._enriquecer_itens_solicitacao(obj.id)
        if obj.itens:
            obj.produto_nome = obj.itens[0].produto_nome
            obj.deposito_nome = obj.itens[0].deposito_nome
        await self._enriquecer_solicitante_nome(obj)

        return obj

    async def adicionar_item_solicitacao(
        self, solicitacao_id: uuid.UUID, item: SolicitacaoItemCreate,
    ) -> SolicitacaoCompra:
        """Adiciona um novo item a uma solicitação já existente (ainda não encerrada/cancelada)."""
        from core.exceptions import BusinessRuleError, EntityNotFoundError

        stmt = select(SolicitacaoCompra).where(
            SolicitacaoCompra.id == solicitacao_id,
            SolicitacaoCompra.tenant_id == self.tenant_id,
        )
        obj = (await self.session.execute(stmt)).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Solicitação de compra não encontrada")
        if obj.status in ("ENCERRADA", "CANCELADA"):
            raise BusinessRuleError("Não é possível adicionar itens a uma solicitação encerrada ou cancelada")

        self.session.add(SolicitacaoItem(
            solicitacao_id=obj.id,
            produto_id=item.produto_id,
            deposito_id=item.deposito_id,
            quantidade_solicitada=item.quantidade_solicitada,
            unidade=item.unidade,
        ))
        await self.session.flush()

        obj.itens = await self._enriquecer_itens_solicitacao(obj.id)
        await self._enriquecer_solicitante_nome(obj)
        return obj

    async def _get_solicitacao_e_item(
        self, solicitacao_id: uuid.UUID, item_id: uuid.UUID,
    ) -> tuple[SolicitacaoCompra, SolicitacaoItem]:
        from core.exceptions import BusinessRuleError, EntityNotFoundError

        stmt = select(SolicitacaoCompra).where(
            SolicitacaoCompra.id == solicitacao_id,
            SolicitacaoCompra.tenant_id == self.tenant_id,
        )
        obj = (await self.session.execute(stmt)).scalar_one_or_none()
        if not obj:
            raise EntityNotFoundError("Solicitação de compra não encontrada")
        if obj.status in ("ENCERRADA", "CANCELADA"):
            raise BusinessRuleError("Não é possível alterar itens de uma solicitação encerrada ou cancelada.")

        item = (await self.session.execute(
            select(SolicitacaoItem).where(
                SolicitacaoItem.id == item_id,
                SolicitacaoItem.solicitacao_id == solicitacao_id,
            )
        )).scalar_one_or_none()
        if not item:
            raise EntityNotFoundError("Item da solicitação não encontrado")
        return obj, item

    async def atualizar_item_solicitacao(
        self, solicitacao_id: uuid.UUID, item_id: uuid.UUID, data: "SolicitacaoItemUpdate",
    ) -> SolicitacaoCompra:
        """Atualiza a quantidade de um item da solicitação (ainda não encerrada/cancelada)."""
        obj, item = await self._get_solicitacao_e_item(solicitacao_id, item_id)
        item.quantidade_solicitada = data.quantidade_solicitada
        self.session.add(item)
        await self.session.flush()

        obj.itens = await self._enriquecer_itens_solicitacao(obj.id)
        await self._enriquecer_solicitante_nome(obj)
        return obj

    async def remover_item_solicitacao(
        self, solicitacao_id: uuid.UUID, item_id: uuid.UUID,
    ) -> SolicitacaoCompra:
        """Remove um item da solicitação — bloqueado se for o último item, ou
        se já existir cotação registrada para ele (evita apagar cotação em
        cascata sem o usuário perceber)."""
        from core.exceptions import BusinessRuleError

        obj, item = await self._get_solicitacao_e_item(solicitacao_id, item_id)

        total_itens = (await self.session.execute(
            select(func.count(SolicitacaoItem.id)).where(SolicitacaoItem.solicitacao_id == solicitacao_id)
        )).scalar_one()
        if total_itens <= 1:
            raise BusinessRuleError("A solicitação precisa ter ao menos 1 item — cancele a solicitação em vez de remover o último item.")

        tem_cotacao = (await self.session.execute(
            select(func.count(CotacaoItem.id)).where(CotacaoItem.solicitacao_item_id == item_id)
        )).scalar_one()
        if tem_cotacao > 0:
            raise BusinessRuleError("Este item já tem cotação registrada — remova a cotação antes de excluir o item.")

        await self.session.delete(item)
        await self.session.flush()

        obj.itens = await self._enriquecer_itens_solicitacao(obj.id)
        await self._enriquecer_solicitante_nome(obj)
        return obj

    async def criar_cotacao(self, solicitacao_id: uuid.UUID, data: CotacaoSolicitacaoCreate) -> CotacaoCompra:
        """Cria uma cotação para uma solicitação aprovada (pode cobrir vários itens)."""
        from core.exceptions import BusinessRuleError

        # Verificar se a solicitação existe e está aprovada
        solicitacao = await self.session.get(SolicitacaoCompra, solicitacao_id)
        if not solicitacao or solicitacao.tenant_id != self.tenant_id:
            return None

        if solicitacao.status != "APROVADA":
            raise BusinessRuleError("Cotações só podem ser registradas para solicitações APROVADAS.")

        itens_solicitacao = await self._enriquecer_itens_solicitacao(solicitacao_id)
        if not itens_solicitacao:
            raise BusinessRuleError("Solicitação sem itens.")

        if data.itens:
            itens_por_id = {i.id: i for i in itens_solicitacao}
            ids_informados = [item.solicitacao_item_id for item in data.itens]
            if len(set(ids_informados)) != len(ids_informados):
                raise BusinessRuleError("Cada item da solicitação só pode aparecer uma vez na cotação.")
            if not set(ids_informados) <= set(itens_por_id.keys()):
                raise BusinessRuleError("Um ou mais itens informados não pertencem a esta solicitação.")
            # Cotação pode ser parcial — o fornecedor nem sempre tem todos os itens
            # nem a quantidade cheia (quantidade_atendida < quantidade_solicitada).
            itens_cotados = []
            for item in data.itens:
                sol_item = itens_por_id[item.solicitacao_item_id]
                qtd_atendida = item.quantidade_atendida if item.quantidade_atendida is not None else sol_item.quantidade_solicitada
                if qtd_atendida > sol_item.quantidade_solicitada:
                    raise BusinessRuleError(
                        f"Quantidade atendida de '{sol_item.produto_nome or 'item'}' ({qtd_atendida}) "
                        f"não pode ser maior que a solicitada ({sol_item.quantidade_solicitada})."
                    )
                itens_cotados.append((sol_item, item.valor_unitario, qtd_atendida))
        else:
            if len(itens_solicitacao) != 1 or data.valor_unitario is None:
                raise BusinessRuleError("Informe 'itens' — esta solicitação tem mais de um item.")
            sol_item = itens_solicitacao[0]
            qtd_atendida = data.quantidade_atendida if data.quantidade_atendida is not None else sol_item.quantidade_solicitada
            if qtd_atendida > sol_item.quantidade_solicitada:
                raise BusinessRuleError(
                    f"Quantidade atendida ({qtd_atendida}) não pode ser maior que a solicitada ({sol_item.quantidade_solicitada})."
                )
            itens_cotados = [(sol_item, data.valor_unitario, qtd_atendida)]

        fornecedor = await self.obter_fornecedor_orm(data.fornecedor_id)
        if not fornecedor:
            raise BusinessRuleError("Fornecedor não encontrado.")
        dados_fornecedor = await obter_dados_exibicao_fornecedor(self.session, fornecedor.pessoa_id)
        condicoes_pagamento = data.condicoes_pagamento or fornecedor.condicoes_pagamento

        # Guardrail: cotação usa histórico compatível; `Produto.preco_medio` não é fonte de verdade.
        # Calculado por item; o cabeçalho reporta o pior caso entre os itens.
        acima_media = False
        percentual = 0.0
        mensagem = None
        valor_total_geral = 0.0

        for sol_item, valor_unitario, qtd_atendida in itens_cotados:
            valor_total_geral += round(valor_unitario * qtd_atendida, 2)
            stats = await self.get_historico_precos(sol_item.produto_id)
            preco_medio = stats.get("preco_medio", 0)
            if preco_medio > 0 and valor_unitario > (preco_medio * 1.15):
                percentual_item = round(((valor_unitario / preco_medio) - 1) * 100, 2)
                if percentual_item > percentual:
                    acima_media = True
                    percentual = percentual_item
                    mensagem = f"{sol_item.produto_nome or 'Item'} {percentual_item}% acima da média histórica (R$ {preco_medio:,.2f})"

        numero_cotacao = await SequencialService(self.session, self.tenant_id).proximo_numero("compras_cotacao")

        cotacao = CotacaoCompra(
            tenant_id=self.tenant_id,
            numero=numero_cotacao,
            solicitacao_id=solicitacao_id,
            fornecedor_id=fornecedor.id,
            fornecedor_nome=dados_fornecedor["nome_fantasia"],
            fornecedor_contato=dados_fornecedor["email"] or dados_fornecedor["telefone"],
            condicoes_pagamento=condicoes_pagamento,
            # atalho legado só faz sentido com 1 item
            valor_unitario=itens_cotados[0][1] if len(itens_cotados) == 1 else None,
            valor_total=round(valor_total_geral, 2),
            prazo_entrega_dias=data.prazo_entrega_dias if data.prazo_entrega_dias is not None else fornecedor.prazo_entrega_dias,
            status="RECEBIDA",
            acima_media=acima_media,
            percentual_acima_media=percentual if acima_media else None,
            mensagem_alerta=mensagem
        )
        self.session.add(cotacao)
        await self.session.flush()

        for sol_item, valor_unitario, qtd_atendida in itens_cotados:
            self.session.add(CotacaoItem(
                cotacao_id=cotacao.id,
                solicitacao_item_id=sol_item.id,
                produto_id=sol_item.produto_id,
                quantidade=qtd_atendida,
                valor_unitario=valor_unitario,
                valor_total=round(valor_unitario * qtd_atendida, 2),
            ))
        await self.session.flush()
        cotacao.itens = await self._enriquecer_itens_cotacao(cotacao.id)
        return cotacao

    async def _enriquecer_itens_cotacao(self, cotacao_id: uuid.UUID) -> List[CotacaoItem]:
        from core.cadastros.produtos.models import Produto

        stmt = (
            select(CotacaoItem, Produto.nome)
            .join(Produto, CotacaoItem.produto_id == Produto.id)
            .where(CotacaoItem.cotacao_id == cotacao_id)
        )
        result = await self.session.execute(stmt)
        pares = result.all()

        stmt_com_pedido = (
            select(AlocacaoItem.cotacao_item_id)
            .where(
                AlocacaoItem.cotacao_item_id.in_([item.id for item, _ in pares]),
                AlocacaoItem.pedido_id.isnot(None),
            )
            .distinct()
        )
        cotacao_item_ids_com_pedido = {
            row[0] for row in (await self.session.execute(stmt_com_pedido)).all()
        }

        itens = []
        for item, p_nome in pares:
            item.produto_nome = p_nome
            item.tem_pedido_gerado = item.id in cotacao_item_ids_com_pedido
            itens.append(item)
        return itens

    async def atualizar_item_cotacao(
        self, solicitacao_id: uuid.UUID, cotacao_id: uuid.UUID, item_id: uuid.UUID, valor_unitario: float,
        quantidade_atendida: Optional[float] = None,
    ) -> CotacaoCompra:
        """Corrige o valor unitário de um item de uma cotação já registrada
        (ex: erro de digitação). Só permitido enquanto a cotação ainda está
        RECEBIDA — depois de aprovada, o valor já virou pedido de compra e
        corrigir aqui deixaria pedido e cotação divergentes."""
        from core.exceptions import BusinessRuleError, EntityNotFoundError

        cotacao = (await self.session.execute(
            select(CotacaoCompra).where(
                CotacaoCompra.id == cotacao_id,
                CotacaoCompra.tenant_id == self.tenant_id,
                CotacaoCompra.solicitacao_id == solicitacao_id,
            )
        )).scalar_one_or_none()
        if not cotacao:
            raise EntityNotFoundError("Cotação não encontrada.")

        if cotacao.status != "RECEBIDA":
            raise BusinessRuleError(
                "Só é possível editar uma cotação enquanto ela está RECEBIDA. "
                "Esta já foi aprovada ou recusada."
            )

        item = (await self.session.execute(
            select(CotacaoItem).where(CotacaoItem.id == item_id, CotacaoItem.cotacao_id == cotacao_id)
        )).scalar_one_or_none()
        if not item:
            raise EntityNotFoundError("Item da cotação não encontrado.")

        tem_alocacao = (await self.session.execute(
            select(func.count(AlocacaoItem.id)).where(AlocacaoItem.cotacao_item_id == item_id)
        )).scalar_one()
        if tem_alocacao:
            raise BusinessRuleError("Este item já foi alocado em uma compra — não é possível alterar o valor.")

        if valor_unitario <= 0:
            raise BusinessRuleError("Valor unitário deve ser maior que zero.")

        if quantidade_atendida is not None:
            sol_item = await self.session.get(SolicitacaoItem, item.solicitacao_item_id)
            if quantidade_atendida > sol_item.quantidade_solicitada:
                raise BusinessRuleError(
                    f"Quantidade atendida ({quantidade_atendida}) não pode ser maior "
                    f"que a solicitada ({sol_item.quantidade_solicitada})."
                )
            item.quantidade = quantidade_atendida

        item.valor_unitario = valor_unitario
        item.valor_total = round(valor_unitario * item.quantidade, 2)
        await self.session.flush()

        todos_itens = (await self.session.execute(
            select(CotacaoItem).where(CotacaoItem.cotacao_id == cotacao_id)
        )).scalars().all()
        cotacao.valor_total = round(sum(i.valor_total for i in todos_itens), 2)
        if len(todos_itens) == 1:
            cotacao.valor_unitario = todos_itens[0].valor_unitario

        acima_media = False
        percentual = 0.0
        mensagem = None
        for i in todos_itens:
            stats = await self.get_historico_precos(i.produto_id)
            preco_medio = stats.get("preco_medio", 0)
            if preco_medio > 0 and i.valor_unitario > (preco_medio * 1.15):
                percentual_item = round(((i.valor_unitario / preco_medio) - 1) * 100, 2)
                if percentual_item > percentual:
                    acima_media = True
                    percentual = percentual_item
                    mensagem = f"{i.produto_nome or 'Item'} {percentual_item}% acima da média histórica (R$ {preco_medio:,.2f})"
        cotacao.acima_media = acima_media
        cotacao.percentual_acima_media = percentual if acima_media else None
        cotacao.mensagem_alerta = mensagem

        await self.session.flush()
        cotacao.itens = await self._enriquecer_itens_cotacao(cotacao.id)
        return cotacao

    async def atualizar_cotacao(
        self, solicitacao_id: uuid.UUID, cotacao_id: uuid.UUID,
        condicoes_pagamento: Optional[str], prazo_entrega_dias: Optional[int],
    ) -> CotacaoCompra:
        """Corrige condições de pagamento / prazo de entrega de uma cotação
        já registrada. Só permitido enquanto RECEBIDA."""
        from core.exceptions import BusinessRuleError, EntityNotFoundError

        cotacao = (await self.session.execute(
            select(CotacaoCompra).where(
                CotacaoCompra.id == cotacao_id,
                CotacaoCompra.tenant_id == self.tenant_id,
                CotacaoCompra.solicitacao_id == solicitacao_id,
            )
        )).scalar_one_or_none()
        if not cotacao:
            raise EntityNotFoundError("Cotação não encontrada.")

        if cotacao.status != "RECEBIDA":
            raise BusinessRuleError(
                "Só é possível editar uma cotação enquanto ela está RECEBIDA. "
                "Esta já foi aprovada ou recusada."
            )

        if condicoes_pagamento is not None:
            cotacao.condicoes_pagamento = condicoes_pagamento
        if prazo_entrega_dias is not None:
            cotacao.prazo_entrega_dias = prazo_entrega_dias

        await self.session.flush()
        cotacao.itens = await self._enriquecer_itens_cotacao(cotacao.id)
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
        itens_solicitacao = await self._enriquecer_itens_solicitacao(solicitacao_id) if solicitacao else []
        produto_principal_id = itens_solicitacao[0].produto_id if itens_solicitacao else None

        # Enriquecer com Score de Compra (Step 159) — calculado com base no
        # item de maior valor da cotação (representativo do fornecedor).
        for cot in cotacoes:
            cot.itens = await self._enriquecer_itens_cotacao(cot.id)
            item_ref_produto_id = produto_principal_id
            item_ref_valor_unitario = cot.valor_unitario
            if cot.itens:
                item_ref = max(cot.itens, key=lambda i: i.valor_total)
                item_ref_produto_id = item_ref.produto_id
                item_ref_valor_unitario = item_ref.valor_unitario
            res_score = await self.calcular_score_compra(cot, item_ref_produto_id, item_ref_valor_unitario)
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

        if cotacao.status == "APROVADA":
            stmt_pedido_existente = select(PedidoCompra).where(
                PedidoCompra.tenant_id == self.tenant_id,
                PedidoCompra.cotacao_id == cotacao_id
            )
            pedido_existente = (await self.session.execute(stmt_pedido_existente)).scalar_one_or_none()
            if pedido_existente:
                return pedido_existente
            raise BusinessRuleError("Esta cotação já foi aprovada.")

        solicitacao = await self.session.get(SolicitacaoCompra, solicitacao_id)
        if not solicitacao or solicitacao.status != "APROVADA":
            raise BusinessRuleError("A solicitação deve estar em status APROVADA.")

        # Guardrail: "Aprovar" recusa TODAS as outras cotações da solicitação
        # (modelo "1 cotação vence tudo") — incompatível com o fluxo de
        # Alocação por Item, que permite dividir a quantidade de um item
        # entre cotações/fornecedores diferentes quando nenhum fornecedor
        # sozinho atende a quantidade solicitada. Se já existe alguma
        # alocação parcial registrada para esta solicitação, bloqueia aqui
        # em vez de recusar silenciosamente cotações já comprometidas.
        tem_alocacao = (
            await self.session.execute(
                select(func.count(AlocacaoItem.id))
                .join(SolicitacaoItem, AlocacaoItem.solicitacao_item_id == SolicitacaoItem.id)
                .where(SolicitacaoItem.solicitacao_id == solicitacao_id)
            )
        ).scalar_one()
        if tem_alocacao > 0:
            raise BusinessRuleError(
                "Esta solicitação já tem alocação parcial entre fornecedores em andamento. "
                "Use 'Alocação por Item' e 'Gerar Pedidos' em vez de 'Aprovar' — aprovar uma "
                "cotação aqui recusaria as demais e destruiria a divisão já feita."
            )

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
        # Savings = soma por item de (Pior valor_total do item entre as cotações recusadas - valor_total escolhido)
        cotacao.itens = await self._enriquecer_itens_cotacao(cotacao.id)
        for o in outras:
            o.itens = await self._enriquecer_itens_cotacao(o.id)

        economia_absoluta = 0.0
        for item in cotacao.itens:
            piores = [
                oi.valor_total for o in outras for oi in o.itens
                if oi.solicitacao_item_id == item.solicitacao_item_id
            ]
            if piores:
                economia_absoluta += max(piores) - item.valor_total
        pior_total_geral = max([cotacao.valor_total] + [o.valor_total for o in outras])
        economia_percentual = (economia_absoluta / pior_total_geral * 100) if pior_total_geral > 0 else 0.0

        # 4. Resolver fornecedor cadastrado — cotações antigas (pré-vínculo com
        # o cadastro real) ainda podem não ter fornecedor_id; nesse caso,
        # resolve/cria a partir do texto legado como fallback.
        if cotacao.fornecedor_id:
            fornecedor = await self.obter_fornecedor_orm(cotacao.fornecedor_id)
        else:
            fornecedor = await self._resolver_ou_criar_fornecedor_por_nome(
                cotacao.fornecedor_nome, cotacao.fornecedor_contato
            )

        # 5. Criar Pedido de Compra — condições de pagamento vêm da cotação
        # vencedora (a negociação real desta compra), não do padrão do cadastro.
        numero_pedido = await SequencialService(self.session, self.tenant_id).proximo_numero("compras_pedido")

        pedido = PedidoCompra(
            tenant_id=self.tenant_id,
            numero=numero_pedido,
            solicitacao_id=solicitacao_id,
            cotacao_id=cotacao_id,
            fornecedor_id=fornecedor.id,
            fornecedor_nome=cotacao.fornecedor_nome,
            fornecedor_contato=cotacao.fornecedor_contato,
            condicoes_pagamento=cotacao.condicoes_pagamento or fornecedor.condicoes_pagamento,
            valor_total=cotacao.valor_total,
            status="ABERTO",
            economia_absoluta=economia_absoluta,
            economia_percentual=economia_percentual,
            usuario_solicitante_id=solicitacao.solicitante_id,
        )
        self.session.add(pedido)
        await self.session.flush()

        itens_solicitacao_por_id = {i.id: i for i in await self._enriquecer_itens_solicitacao(solicitacao_id)}
        for item in cotacao.itens:
            sol_item = itens_solicitacao_por_id.get(item.solicitacao_item_id)
            self.session.add(ItemPedidoCompra(
                pedido_id=pedido.id,
                produto_id=item.produto_id,
                deposito_id=sol_item.deposito_id if sol_item else None,
                unidade=sol_item.unidade if sol_item else "UN",
                quantidade_solicitada=item.quantidade,
                preco_estimado_unitario=item.valor_unitario,
                valor_total=item.valor_total,
                status_item="PENDENTE",
            ))
        await self.session.flush()
        return pedido

    async def alocar_itens(
        self, solicitacao_id: uuid.UUID, alocacoes: list,
    ) -> List[SolicitacaoItem]:
        """Aloca quantidades de itens da solicitação a cotações/fornecedores
        específicos. Um item pode receber várias alocações (fornecedores
        diferentes, quantidades parciais); pode ser chamado várias vezes até
        completar o item ou até o solicitante encerrar a solicitação.

        `alocacoes`: lista de objetos com `solicitacao_item_id`,
        `cotacao_item_id`, `quantidade` (ex: AlocacaoItemCreate).
        """
        from core.exceptions import BusinessRuleError

        solicitacao = await self.session.get(SolicitacaoCompra, solicitacao_id)
        if not solicitacao or solicitacao.tenant_id != self.tenant_id:
            raise BusinessRuleError("Solicitação não encontrada.")
        if solicitacao.status != "APROVADA":
            raise BusinessRuleError("Só é possível alocar itens de solicitações APROVADAS.")

        itens_solicitacao = await self._enriquecer_itens_solicitacao(solicitacao_id)
        itens_por_id = {i.id: i for i in itens_solicitacao}
        saldo_item = {i.id: i.quantidade_solicitada - i.quantidade_alocada for i in itens_solicitacao}

        cotacao_item_ids = list({a.cotacao_item_id for a in alocacoes})
        stmt_ci = (
            select(CotacaoItem, CotacaoCompra.solicitacao_id, CotacaoCompra.status, CotacaoCompra.tenant_id)
            .join(CotacaoCompra, CotacaoItem.cotacao_id == CotacaoCompra.id)
            .where(CotacaoItem.id.in_(cotacao_item_ids))
        )
        cotacao_itens_por_id = {}
        for ci, sol_id, cot_status, cot_tenant_id in (await self.session.execute(stmt_ci)).all():
            cotacao_itens_por_id[ci.id] = (ci, sol_id, cot_status, cot_tenant_id)

        stmt_saldo_ci = (
            select(AlocacaoItem.cotacao_item_id, func.coalesce(func.sum(AlocacaoItem.quantidade_alocada), 0.0))
            .where(AlocacaoItem.cotacao_item_id.in_(cotacao_item_ids))
            .group_by(AlocacaoItem.cotacao_item_id)
        )
        alocado_por_cotacao_item = dict((await self.session.execute(stmt_saldo_ci)).all())

        for aloc in alocacoes:
            entry = cotacao_itens_por_id.get(aloc.cotacao_item_id)
            if not entry:
                raise BusinessRuleError("Item de cotação não encontrado.")
            cotacao_item, cot_solicitacao_id, cot_status, cot_tenant_id = entry
            if cot_tenant_id != self.tenant_id or cot_solicitacao_id != solicitacao_id:
                raise BusinessRuleError("Item de cotação não pertence a esta solicitação.")
            if cot_status == "RECUSADA":
                raise BusinessRuleError("Não é possível alocar a partir de uma cotação recusada.")
            if cotacao_item.solicitacao_item_id != aloc.solicitacao_item_id:
                raise BusinessRuleError("O item de cotação informado não corresponde ao item da solicitação.")
            if aloc.solicitacao_item_id not in itens_por_id:
                raise BusinessRuleError("Item da solicitação não encontrado.")

            saldo_cotado = cotacao_item.quantidade - alocado_por_cotacao_item.get(aloc.cotacao_item_id, 0.0)
            if aloc.quantidade > saldo_cotado + 1e-6:
                raise BusinessRuleError(
                    f"Quantidade alocada ({aloc.quantidade}) excede o saldo cotado por este fornecedor ({saldo_cotado})."
                )
            saldo_pedido = saldo_item.get(aloc.solicitacao_item_id, 0.0)
            if aloc.quantidade > saldo_pedido + 1e-6:
                raise BusinessRuleError(
                    f"Quantidade alocada ({aloc.quantidade}) excede o saldo pendente do item ({saldo_pedido})."
                )

            alocado_por_cotacao_item[aloc.cotacao_item_id] = alocado_por_cotacao_item.get(aloc.cotacao_item_id, 0.0) + aloc.quantidade
            saldo_item[aloc.solicitacao_item_id] = saldo_pedido - aloc.quantidade

            self.session.add(AlocacaoItem(
                solicitacao_item_id=aloc.solicitacao_item_id,
                cotacao_item_id=aloc.cotacao_item_id,
                quantidade_alocada=aloc.quantidade,
            ))

        await self.session.flush()
        return await self._enriquecer_itens_solicitacao(solicitacao_id)

    async def gerar_pedidos_de_alocacoes(self, solicitacao_id: uuid.UUID) -> List[PedidoCompra]:
        """Converte as alocações pendentes (ainda sem pedido) de uma
        solicitação em pedidos de compra — 1 pedido por fornecedor com itens
        alocados. Pode gerar vários pedidos numa única chamada."""
        from core.exceptions import BusinessRuleError

        solicitacao = await self.session.get(SolicitacaoCompra, solicitacao_id)
        if not solicitacao or solicitacao.tenant_id != self.tenant_id:
            raise BusinessRuleError("Solicitação não encontrada.")

        stmt = (
            select(AlocacaoItem, CotacaoItem, CotacaoCompra)
            .join(CotacaoItem, AlocacaoItem.cotacao_item_id == CotacaoItem.id)
            .join(CotacaoCompra, CotacaoItem.cotacao_id == CotacaoCompra.id)
            .where(
                CotacaoCompra.solicitacao_id == solicitacao_id,
                AlocacaoItem.pedido_id.is_(None),
            )
        )
        linhas = (await self.session.execute(stmt)).all()
        if not linhas:
            return []

        itens_solicitacao_por_id = {i.id: i for i in await self._enriquecer_itens_solicitacao(solicitacao_id)}

        # Maior valor_unitario cotado por item (entre todas as cotações não recusadas),
        # usado como referência de "pior preço" para o cálculo de economia.
        stmt_pior = (
            select(CotacaoItem.solicitacao_item_id, func.max(CotacaoItem.valor_unitario))
            .join(CotacaoCompra, CotacaoItem.cotacao_id == CotacaoCompra.id)
            .where(CotacaoCompra.solicitacao_id == solicitacao_id, CotacaoCompra.status != "RECUSADA")
            .group_by(CotacaoItem.solicitacao_item_id)
        )
        pior_valor_unitario_por_item = dict((await self.session.execute(stmt_pior)).all())

        grupos: dict = {}
        for alocacao, cotacao_item, cotacao in linhas:
            grupos.setdefault(cotacao.fornecedor_id or cotacao.id, []).append((alocacao, cotacao_item, cotacao))

        pedidos_gerados = []
        for chave, itens_grupo in grupos.items():
            _, _, cotacao_ref = itens_grupo[0]
            if cotacao_ref.fornecedor_id:
                fornecedor = await self.obter_fornecedor_orm(cotacao_ref.fornecedor_id)
            else:
                fornecedor = await self._resolver_ou_criar_fornecedor_por_nome(
                    cotacao_ref.fornecedor_nome, cotacao_ref.fornecedor_contato
                )

            valor_total_pedido = sum(a.quantidade_alocada * ci.valor_unitario for a, ci, _ in itens_grupo)
            economia_absoluta = sum(
                (pior_valor_unitario_por_item.get(ci.solicitacao_item_id, ci.valor_unitario) - ci.valor_unitario) * a.quantidade_alocada
                for a, ci, _ in itens_grupo
            )
            pior_total = sum(
                pior_valor_unitario_por_item.get(ci.solicitacao_item_id, ci.valor_unitario) * a.quantidade_alocada
                for a, ci, _ in itens_grupo
            )
            economia_percentual = (economia_absoluta / pior_total * 100) if pior_total > 0 else 0.0

            numero_pedido = await SequencialService(self.session, self.tenant_id).proximo_numero("compras_pedido")

            pedido = PedidoCompra(
                tenant_id=self.tenant_id,
                numero=numero_pedido,
                solicitacao_id=solicitacao_id,
                cotacao_id=cotacao_ref.id,
                fornecedor_id=fornecedor.id,
                fornecedor_nome=cotacao_ref.fornecedor_nome,
                fornecedor_contato=cotacao_ref.fornecedor_contato,
                condicoes_pagamento=cotacao_ref.condicoes_pagamento or fornecedor.condicoes_pagamento,
                valor_total=round(valor_total_pedido, 2),
                status="ABERTO",
                economia_absoluta=round(economia_absoluta, 2),
                economia_percentual=round(economia_percentual, 2),
                usuario_solicitante_id=solicitacao.solicitante_id,
            )
            self.session.add(pedido)
            await self.session.flush()

            for alocacao, cotacao_item, _ in itens_grupo:
                sol_item = itens_solicitacao_por_id.get(alocacao.solicitacao_item_id)
                self.session.add(ItemPedidoCompra(
                    pedido_id=pedido.id,
                    produto_id=cotacao_item.produto_id,
                    deposito_id=sol_item.deposito_id if sol_item else None,
                    unidade=sol_item.unidade if sol_item else "UN",
                    quantidade_solicitada=alocacao.quantidade_alocada,
                    preco_estimado_unitario=cotacao_item.valor_unitario,
                    valor_total=round(alocacao.quantidade_alocada * cotacao_item.valor_unitario, 2),
                    status_item="PENDENTE",
                ))
                alocacao.pedido_id = pedido.id
                self.session.add(alocacao)

            pedidos_gerados.append(pedido)

        await self.session.flush()
        return pedidos_gerados

    async def encerrar_solicitacao(self, solicitacao_id: uuid.UUID, usuario_id: uuid.UUID | None) -> SolicitacaoCompra:
        """Encerra uma solicitação — inclusive com itens PENDENTE/PARCIAL — a
        pedido do próprio solicitante, que é quem sabe se o atendimento
        parcial já resolve a necessidade dele. Só o solicitante pode chamar
        (registros legados sem solicitante_id não são bloqueados)."""
        from core.exceptions import BusinessRuleError, TenantViolationError

        solicitacao = await self.session.get(SolicitacaoCompra, solicitacao_id)
        if not solicitacao or solicitacao.tenant_id != self.tenant_id:
            raise BusinessRuleError("Solicitação não encontrada.")
        if solicitacao.solicitante_id is not None and str(solicitacao.solicitante_id) != str(usuario_id):
            raise TenantViolationError("Apenas quem criou a solicitação pode encerrá-la.")
        if solicitacao.status not in ("APROVADA", "ABERTA", "EM_ANALISE"):
            raise BusinessRuleError(f"Não é possível encerrar uma solicitação com status {solicitacao.status}.")

        solicitacao.status = "ENCERRADA"
        await self.session.flush()
        solicitacao.itens = await self._enriquecer_itens_solicitacao(solicitacao.id)
        await self._enriquecer_solicitante_nome(solicitacao)
        return solicitacao

    async def atualizar_condicoes_pagamento(
        self, pedido_id: uuid.UUID, condicoes_pagamento: str
    ) -> PedidoCompra:
        pedido = await self.session.get(PedidoCompra, pedido_id)
        if not pedido or pedido.tenant_id != self.tenant_id:
            raise BusinessRuleError("Pedido não encontrado.")
        if pedido.status in ("RECEBIDO", "CANCELADO"):
            raise BusinessRuleError(
                "Não é possível alterar condições de pagamento de um pedido recebido ou cancelado."
            )
        pedido.condicoes_pagamento = condicoes_pagamento
        self.session.add(pedido)
        await self.session.flush()
        return pedido

    async def atualizar_adiantamento(
        self, pedido_id: uuid.UUID, valor_adiantamento: float
    ) -> PedidoCompra:
        pedido = await self.session.get(PedidoCompra, pedido_id)
        if not pedido or pedido.tenant_id != self.tenant_id:
            raise BusinessRuleError("Pedido não encontrado.")
        if pedido.status not in ("ABERTO", "ENVIADO"):
            raise BusinessRuleError(
                "Adiantamento só pode ser definido antes da confirmação do fornecedor."
            )
        if valor_adiantamento > float(pedido.valor_total or 0.0):
            raise BusinessRuleError("Adiantamento não pode ser maior que o valor total do pedido.")
        pedido.valor_adiantamento = valor_adiantamento
        self.session.add(pedido)
        await self.session.flush()
        return pedido

    async def _gerar_despesa_adiantamento(self, pedido: PedidoCompra) -> Despesa | None:
        """Gera a Despesa de adiantamento — só deve ser chamada após a
        confirmação de aceite do fornecedor (status CONFIRMADO)."""
        if not pedido.valor_adiantamento or float(pedido.valor_adiantamento) <= 0:
            return None

        existente = (
            await self.session.execute(
                select(Despesa).where(
                    Despesa.tenant_id == self.tenant_id,
                    Despesa.origem_tipo == "COMPRA_ADIANTAMENTO",
                    Despesa.origem_id == pedido.id,
                    Despesa.ativo == True,
                ).limit(1)
            )
        ).scalar_one_or_none()
        if existente is not None:
            return existente

        item_principal = await self._get_or_create_item_pedido_principal(pedido)
        deposito = await self.session.get(Deposito, item_principal.deposito_id)
        produto = await self.session.get(Produto, item_principal.produto_id)
        if not deposito or deposito.tenant_id != self.tenant_id:
            raise BusinessRuleError("Deposito do pedido indisponível para integração financeira da compra.")
        if not produto or produto.tenant_id != self.tenant_id:
            raise BusinessRuleError("Produto do pedido indisponível para integração financeira da compra.")

        plano_conta_id = await self._resolver_plano_conta_compra(produto)
        if plano_conta_id is None:
            raise BusinessRuleError("Nenhum plano de contas de despesa analítica foi encontrado para integrar a compra.")

        pessoa_id, fornecedor_nome, _fornecedor = await self._resolver_fornecedor_financeiro(pedido)
        hoje = date.today()

        payload = DespesaCreate(
            unidade_produtiva_id=deposito.unidade_produtiva_id,
            plano_conta_id=plano_conta_id,
            descricao=f"Adiantamento de compra de {produto.nome}",
            valor_total=float(pedido.valor_adiantamento),
            data_emissao=hoje,
            data_vencimento=hoje,
            competencia=hoje.replace(day=1),
            status="A_PAGAR",
            pessoa_id=pessoa_id,
            fornecedor=fornecedor_nome or pedido.fornecedor_nome,
            origem_id=pedido.id,
            origem_tipo="COMPRA_ADIANTAMENTO",
            observacoes=f"Adiantamento pago na confirmação de aceite do pedido {pedido.id}.",
            rateios=[],
        )
        despesas = await DespesaService(self.session, self.tenant_id).create_with_rateio(payload)
        return despesas[0] if despesas else None

    async def listar_pedidos(self) -> List[PedidoCompra]:
        """Lista todos os pedidos de compra com dados enriquecidos."""
        stmt = (
            select(PedidoCompra)
            .where(PedidoCompra.tenant_id == self.tenant_id)
            .order_by(PedidoCompra.created_at.desc())
        )
        pedidos = (await self.session.execute(stmt)).scalars().all()
        return [await self._enriquecer_pedido(ped) for ped in pedidos]

    async def _enriquecer_itens_pedido(self, pedido_id: uuid.UUID) -> List[ItemPedidoCompra]:
        from core.cadastros.produtos.models import Produto
        from operacional.models.estoque import Deposito

        stmt = (
            select(ItemPedidoCompra, Produto.nome, Deposito.nome)
            .join(Produto, ItemPedidoCompra.produto_id == Produto.id)
            .outerjoin(Deposito, ItemPedidoCompra.deposito_id == Deposito.id)
            .where(ItemPedidoCompra.pedido_id == pedido_id)
        )
        result = await self.session.execute(stmt)
        itens = []
        for item, p_nome, d_nome in result.all():
            item.produto_nome = p_nome
            item.deposito_nome = d_nome
            itens.append(item)
        return itens

    async def _resolver_resumo_entrega_pedido(
        self, itens: List[ItemPedidoCompra]
    ) -> tuple[uuid.UUID | None, str, str | None]:
        """Resolve o resumo de entrega do pedido a partir dos depósitos dos itens."""
        deposito_ids = {item.deposito_id for item in itens if item.deposito_id}
        if not deposito_ids:
            return None, "Depósito vinculado ao pedido", None
        if len(deposito_ids) > 1:
            return None, "Múltiplos depósitos", None
        deposito_id = next(iter(deposito_ids))
        deposito_nome, endereco = await self._resolver_endereco_entrega(deposito_id)
        return deposito_id, deposito_nome or "Depósito vinculado ao item", endereco

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
            recebimentos_existentes = (
                await self.session.execute(
                    select(RecebimentoParcial).where(RecebimentoParcial.pedido_id == pedido.id)
                )
            ).scalars().all()
            for rec in recebimentos_existentes:
                await self._garantir_despesa_financeira_compra(pedido, recebimento=rec)
            return await self._enriquecer_pedido(pedido)  # Já recebido, idempotente

        item_pedido = await self._get_or_create_item_pedido_principal(pedido)
        if data is None:
            recebimento_data = await self._build_recebimento_fallback(pedido, item_pedido)
        elif not data.itens:
            # Cabeçalho (NF/chave/observações) veio explícito, mas sem itens —
            # completa com o fallback (recebe todos os itens do pedido).
            fallback = await self._build_recebimento_fallback(pedido, item_pedido)
            recebimento_data = data.model_copy(update={"itens": fallback.itens})
        else:
            recebimento_data = data

        # 2. Verificar se já existe movimentação para este pedido (idempotência extra).
        # Movimentos "COMPRA" já totalmente revertidos por um estorno (AJUSTE com
        # ajuste_de apontando pra eles, ver estornar_recebimento) não contam como
        # recebimento ativo — senão um receber-depois-de-estornar fica travado achando
        # que já foi recebido, sem nunca rematerializar estoque/itens.
        stmt_check = select(EstoqueMovimento).where(
            EstoqueMovimento.origem == "COMPRA",
            EstoqueMovimento.origem_id == pedido.id,
            EstoqueMovimento.tenant_id == self.tenant_id
        )
        compra_movs = (await self.session.execute(stmt_check)).scalars().all()
        revertidos_ids = set()
        if compra_movs:
            stmt_revertidos = select(EstoqueMovimento.ajuste_de).where(
                EstoqueMovimento.origem == "AJUSTE",
                EstoqueMovimento.ajuste_de.in_([m.id for m in compra_movs]),
            )
            revertidos_ids = {row[0] for row in (await self.session.execute(stmt_revertidos)).all()}
        existing_mov = any(m.id not in revertidos_ids for m in compra_movs)

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
                    preco_real_unitario=float(item_model.preco_real_unitario or 0.0) or self._resolver_custo_recebimento(item_alvo),
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
        await self._garantir_despesa_financeira_compra(pedido, recebimento=recebimento)

        return await self._enriquecer_pedido(pedido)

    async def _status_anterior_ao_recebimento(self, pedido_id: uuid.UUID) -> str:
        """Infere o status do pedido antes de ter sido marcado RECEBIDO, com
        base no histórico de confirmação com o fornecedor (não há campo de
        status anterior persistido)."""
        confirmacoes = (
            await self.session.execute(
                select(PedidoConfirmacaoFornecedor.status)
                .where(PedidoConfirmacaoFornecedor.pedido_id == pedido_id)
                .order_by(PedidoConfirmacaoFornecedor.data_expiracao.desc())
            )
        ).scalars().all()
        if any(s == "CONFIRMADO" for s in confirmacoes):
            return "CONFIRMADO"
        if confirmacoes:
            return "ENVIADO"
        return "ABERTO"

    async def estornar_recebimento(
        self, pedido_id: uuid.UUID, motivo: str, usuario_id: uuid.UUID | None = None,
    ) -> PedidoCompra:
        """Desfaz um recebimento feito por engano: reverte estoque (lote/saldo),
        desativa a despesa gerada e apaga o registro de recebimento — só é
        permitido enquanto nada do estoque recebido foi consumido. Se já houve
        consumo, o caminho correto é registrar uma Devolução ao Fornecedor.

        `motivo` é obrigatório e fica registrado no movimento de estorno e no
        log de auditoria — é a justificativa de por que o recebimento foi
        desfeito (rastreabilidade para fiscal/financeiro)."""
        if not motivo or not motivo.strip():
            raise BusinessRuleError("Informe a justificativa do estorno.")

        pedido = await self.session.get(PedidoCompra, pedido_id)
        if not pedido or pedido.tenant_id != self.tenant_id:
            raise BusinessRuleError("Pedido não encontrado.")
        if pedido.status != "RECEBIDO":
            raise BusinessRuleError("Só é possível estornar um pedido que esteja RECEBIDO.")

        status_antes = pedido.status

        todos_compra = (
            await self.session.execute(
                select(EstoqueMovimento).where(
                    EstoqueMovimento.tenant_id == self.tenant_id,
                    EstoqueMovimento.origem == "COMPRA",
                    EstoqueMovimento.origem_id == pedido.id,
                )
            )
        ).scalars().all()
        if not todos_compra:
            raise BusinessRuleError("Nenhum movimento de estoque encontrado para este recebimento.")

        # Só reverte movimentos "COMPRA" que ainda não foram revertidos antes —
        # senão um segundo estorno (depois de um receber-de-novo) reverteria de
        # novo um movimento já zerado, decrementando o saldo em dobro.
        ja_revertidos = {
            row[0] for row in (
                await self.session.execute(
                    select(EstoqueMovimento.ajuste_de).where(
                        EstoqueMovimento.origem == "AJUSTE",
                        EstoqueMovimento.ajuste_de.in_([m.id for m in todos_compra]),
                    )
                )
            ).all()
        }
        movimentos = [m for m in todos_compra if m.id not in ja_revertidos]
        if not movimentos:
            raise BusinessRuleError("Este recebimento já foi estornado anteriormente.")

        # 1ª passada: valida que nada foi consumido antes de mexer em qualquer dado.
        saldos_por_movimento = {}
        for mov in movimentos:
            saldo = (
                await self.session.execute(
                    select(SaldoEstoque).where(
                        SaldoEstoque.deposito_id == mov.deposito_id,
                        SaldoEstoque.produto_id == mov.produto_id,
                    )
                )
            ).scalar_one_or_none()
            if saldo is None or saldo.quantidade_atual + 1e-6 < float(mov.quantidade):
                produto = await self.session.get(Produto, mov.produto_id)
                raise BusinessRuleError(
                    f"Não é possível estornar: o estoque de '{produto.nome if produto else mov.produto_id}' "
                    "recebido neste pedido já foi parcialmente consumido. Registre uma Devolução ao "
                    "Fornecedor para corrigir este caso."
                )
            saldos_por_movimento[mov.id] = saldo

        # Restaura o CMPM para o valor de antes da(s) entrada(s) estornada(s) — usa o
        # custo_medio_anterior do movimento mais antigo por saldo, cobrindo o caso de
        # mais de um movimento (mesmo produto/depósito) sendo estornado de uma vez.
        mais_antigo_por_saldo: dict = {}
        for mov in movimentos:
            saldo = saldos_por_movimento[mov.id]
            atual = mais_antigo_por_saldo.get(saldo.id)
            if atual is None or mov.created_at < atual.created_at:
                mais_antigo_por_saldo[saldo.id] = mov

        # 2ª passada: reverte estoque via movimento de ajuste referenciando o original
        # (estoque_movimentos é append-only no banco — correções usam ajuste_de, nunca DELETE).
        for mov in movimentos:
            saldo = saldos_por_movimento[mov.id]
            saldo.quantidade_atual -= float(mov.quantidade)
            if mais_antigo_por_saldo.get(saldo.id) is mov:
                custo_anterior = mov.custo_medio_anterior
                saldo.custo_medio = float(custo_anterior) if custo_anterior is not None else None
            self.session.add(saldo)
            if mov.lote_id:
                lote = await self.session.get(LoteEstoque, mov.lote_id)
                if lote:
                    lote.quantidade_atual = max(0.0, float(lote.quantidade_atual) - float(mov.quantidade))
                    if lote.quantidade_atual <= 0:
                        lote.status = "ESGOTADO"
                    self.session.add(lote)

            await registrar_ledger_estoque(
                self.session,
                tenant_id=self.tenant_id,
                produto_id=mov.produto_id,
                deposito_id=mov.deposito_id,
                lote_id=mov.lote_id,
                tipo_movimento="AJUSTE",
                quantidade=-float(mov.quantidade),
                custo_unitario=float(mov.custo_unitario) if mov.custo_unitario else None,
                origem="AJUSTE",
                origem_id=pedido.id,
                ajuste_de=mov.id,
                observacoes=f"Estorno de recebimento (pedido {pedido.numero or pedido.id}): {motivo.strip()}",
                custo_medio_anterior=float(mov.custo_medio_resultante) if mov.custo_medio_resultante is not None else None,
                custo_medio_resultante=float(saldo.custo_medio) if saldo.custo_medio is not None else None,
            )

        # Desativa (não apaga) a despesa financeira gerada — preserva auditoria.
        recebimentos = (
            await self.session.execute(
                select(RecebimentoParcial).where(RecebimentoParcial.pedido_id == pedido.id)
            )
        ).scalars().all()
        for rec in recebimentos:
            despesas = (
                await self.session.execute(
                    select(Despesa).where(
                        Despesa.tenant_id == self.tenant_id,
                        Despesa.origem_tipo == "COMPRA",
                        Despesa.origem_id == rec.id,
                    )
                )
            ).scalars().all()
            for despesa in despesas:
                despesa.ativo = False
                self.session.add(despesa)

            itens_recebimento = (
                await self.session.execute(
                    select(ItemRecebimento).where(ItemRecebimento.recebimento_id == rec.id)
                )
            ).scalars().all()
            for item_rec in itens_recebimento:
                await self.session.delete(item_rec)
            await self.session.delete(rec)

        itens_pedido = (
            await self.session.execute(
                select(ItemPedidoCompra).where(ItemPedidoCompra.pedido_id == pedido.id)
            )
        ).scalars().all()
        for item in itens_pedido:
            item.quantidade_recebida = 0.0
            item.preco_real_unitario = None
            item.status_item = "PENDENTE"
            self.session.add(item)

        pedido.status = await self._status_anterior_ao_recebimento(pedido.id)
        self.session.add(pedido)
        await self.session.flush()

        from core.services.audit_service import write_audit_log
        await write_audit_log(
            self.session,
            tenant_id=self.tenant_id,
            user_id=usuario_id,
            action="ESTORNO_RECEBIMENTO",
            resource="compras_pedidos",
            resource_id=pedido.id,
            payload_before={"status": status_antes},
            payload_after={"status": pedido.status, "motivo": motivo.strip()},
        )

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

        if novo_status == "CANCELADO":
            await self._reabrir_cotacoes_concorrentes(pedido)

        return await self._enriquecer_pedido(pedido)

    async def _reabrir_cotacoes_concorrentes(self, pedido: PedidoCompra) -> None:
        """Ao cancelar um pedido, marca a cotação de origem como perdida e libera
        as demais cotações da mesma solicitação para uma nova escolha, evitando
        que o comprador precise recotar do zero."""
        if not pedido.solicitacao_id:
            return

        if pedido.cotacao_id:
            cotacao_perdedora = await self.session.get(CotacaoCompra, pedido.cotacao_id)
            if cotacao_perdedora and cotacao_perdedora.tenant_id == self.tenant_id:
                cotacao_perdedora.status = "RECUSADA"
                self.session.add(cotacao_perdedora)

        stmt = select(CotacaoCompra).where(
            CotacaoCompra.solicitacao_id == pedido.solicitacao_id,
            CotacaoCompra.tenant_id == self.tenant_id,
            CotacaoCompra.id != pedido.cotacao_id,
        )
        concorrentes = (await self.session.execute(stmt)).scalars().all()
        for cotacao in concorrentes:
            if cotacao.status == "RECUSADA":
                cotacao.status = "RECEBIDA"
                self.session.add(cotacao)

        await self.session.flush()

    async def enviar_pedido_fornecedor(self, pedido_id: uuid.UUID) -> PedidoCompra:
        """Gera link+senha de confirmação e envia e-mail ao fornecedor,
        marcando o pedido como ENVIADO (aguardando aceite)."""
        pedido = await self.session.get(PedidoCompra, pedido_id)
        if not pedido or pedido.tenant_id != self.tenant_id:
            raise BusinessRuleError("Pedido não encontrado.")
        if pedido.status not in ("ABERTO", "ENVIADO"):
            raise BusinessRuleError("Só é possível enviar ao fornecedor pedidos em aberto.")
        if not pedido.fornecedor_id:
            raise BusinessRuleError("Pedido sem fornecedor cadastrado vinculado.")

        fornecedor = await self.session.get(Fornecedor, pedido.fornecedor_id)
        if not fornecedor:
            raise BusinessRuleError("Fornecedor não encontrado.")
        dados_fornecedor = await obter_dados_exibicao_fornecedor(self.session, fornecedor.pessoa_id)
        if not dados_fornecedor["email"]:
            raise BusinessRuleError(
                "Fornecedor sem e-mail cadastrado. Cadastre um e-mail antes de enviar o pedido."
            )

        pendentes = (
            await self.session.execute(
                select(PedidoConfirmacaoFornecedor).where(
                    PedidoConfirmacaoFornecedor.pedido_id == pedido.id,
                    PedidoConfirmacaoFornecedor.status == "PENDENTE",
                )
            )
        ).scalars().all()
        for antiga in pendentes:
            antiga.status = "EXPIRADO"
            self.session.add(antiga)

        token = secrets.token_urlsafe(32)
        senha = f"{secrets.randbelow(1_000_000):06d}"
        senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        dias_expiracao = 5

        confirmacao = PedidoConfirmacaoFornecedor(
            tenant_id=self.tenant_id,
            pedido_id=pedido.id,
            token_confirmacao=token,
            senha_confirmacao_hash=senha_hash,
            data_expiracao=datetime.now(timezone.utc) + timedelta(days=dias_expiracao),
        )
        self.session.add(confirmacao)

        pedido.status = "ENVIADO"
        self.session.add(pedido)
        await self.session.flush()

        itens_pedido = await self._enriquecer_itens_pedido(pedido.id)
        tenant = await self.session.get(Tenant, self.tenant_id)
        deposito_id_entrega = itens_pedido[0].deposito_id if itens_pedido else None
        _, endereco_entrega = (
            await self._resolver_endereco_entrega(deposito_id_entrega) if deposito_id_entrega else (None, None)
        )

        itens_email = [
            {
                "produto_nome": i.produto_nome or "",
                "quantidade": i.quantidade_solicitada,
                "unidade": i.unidade,
                "preco_unitario": _formatar_moeda_brl(i.preco_estimado_unitario),
                "valor_total": _formatar_moeda_brl(i.valor_total),
            }
            for i in itens_pedido
        ]

        try:
            await email_service.send_pedido_compra_confirmacao(
                email=dados_fornecedor["email"],
                fornecedor_nome=dados_fornecedor["nome_fantasia"],
                tenant_nome=tenant.nome if tenant else "",
                itens=itens_email,
                valor_total=_formatar_moeda_brl(pedido.valor_total),
                condicoes_pagamento=pedido.condicoes_pagamento or "A combinar",
                endereco_entrega=endereco_entrega or "A combinar",
                prazo_entrega_dias=fornecedor.prazo_entrega_dias,
                token=token,
                senha_confirmacao=senha,
                dias_expiracao=dias_expiracao,
                tenant_id=self.tenant_id,
                numero_pedido=pedido.numero,
            )
        except Exception as e:
            logger.error(f"Falha ao enviar e-mail de confirmação do pedido {pedido.id}: {e}")

        return await self._enriquecer_pedido(pedido)

    async def _resolver_endereco_entrega(self, deposito_id: uuid.UUID) -> tuple[str | None, str | None]:
        """Retorna (nome_deposito, endereco_formatado) a partir da Unidade
        Produtiva vinculada ao depósito — usado no pedido e no e-mail ao
        fornecedor, para indicar onde a mercadoria deve ser entregue."""
        from operacional.models.estoque import Deposito
        from core.models.unidade_produtiva import UnidadeProdutiva

        deposito = await self.session.get(Deposito, deposito_id)
        if not deposito:
            return None, None

        up = await self.session.get(UnidadeProdutiva, deposito.unidade_produtiva_id)
        if not up:
            return deposito.nome, None

        partes = [
            f"{up.logradouro}, {up.numero}" if up.logradouro else None,
            up.complemento,
            up.bairro,
            f"{up.municipio}/{up.uf}" if up.municipio and up.uf else (up.municipio or up.uf),
            f"CEP {up.cep}" if up.cep else None,
        ]
        endereco = ", ".join(p for p in partes if p) or None
        return deposito.nome, endereco

    async def _enriquecer_pedido(self, pedido: PedidoCompra) -> PedidoCompra:
        """Adiciona itens, nomes de item/depósito, endereço de entrega e prazo
        de entrega do fornecedor ao objeto do pedido (atributos transientes,
        não persistidos — usados só para a resposta da API).

        item_nome/deposito_id/deposito_nome/quantidade/unidade/valor_unitario
        são campos de conveniência calculados a partir de `itens` — só fazem
        sentido (ficam preenchidos) quando o pedido tem 1 item só; a UI deve
        iterar `itens` para o caso geral multi-item."""
        pedido.itens = await self._enriquecer_itens_pedido(pedido.id)
        item_unico = pedido.itens[0] if len(pedido.itens) == 1 else None

        pedido.item_nome = item_unico.produto_nome if item_unico else (
            "Múltiplos itens" if pedido.itens else "N/A"
        )
        pedido.deposito_id, pedido.deposito_nome, pedido.endereco_entrega = (
            await self._resolver_resumo_entrega_pedido(pedido.itens)
        )

        pedido.quantidade = item_unico.quantidade_solicitada if item_unico else None
        pedido.unidade = item_unico.unidade if item_unico else None
        pedido.valor_unitario = item_unico.preco_estimado_unitario if item_unico else None

        fornecedor = await self.session.get(Fornecedor, pedido.fornecedor_id) if pedido.fornecedor_id else None
        pedido.prazo_entrega_dias = fornecedor.prazo_entrega_dias if fornecedor else None
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
        titulo = f"PEDIDO DE COMPRA {pedido.numero}" if pedido.numero else "PEDIDO DE COMPRA"
        elements.append(Paragraph(titulo, title_style))
        elements.append(Spacer(1, 12))

        # Tabela de Dados Gerais
        data_geral = [
            ["Nº do Pedido:", pedido.numero or str(pedido.id)],
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
            ["Contato:", pedido.fornecedor_contato or "N/A"],
            ["Condições de Pagamento:", pedido.condicoes_pagamento or "A combinar"],
            ["Prazo de Entrega:", f"{pedido.prazo_entrega_dias} dias" if pedido.prazo_entrega_dias else "A combinar"],
        ]
        t_forn = Table(data_forn, colWidths=[100, 300])
        t_forn.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
        ]))
        elements.append(t_forn)
        elements.append(Spacer(1, 20))
        
        # Itens do Pedido
        elements.append(Paragraph("<b>ITENS DO PEDIDO</b>", styles['Normal']))
        elements.append(Spacer(1, 6))
        header_itens = ["Descrição do produto", "Quantidade", "Preço unitário", "Preço total"]
        rows_itens = [
            [
                item.produto_nome or "N/A",
                f"{item.quantidade_solicitada:g} {item.unidade}",
                _formatar_moeda_brl(item.preco_estimado_unitario),
                _formatar_moeda_brl(item.valor_total),
            ]
            for item in pedido.itens
        ]

        t_itens = Table([header_itens] + rows_itens, colWidths=[220, 90, 90, 90])
        t_itens.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,1), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
        ]))
        elements.append(t_itens)
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"<b>Valor total do pedido:</b> {_formatar_moeda_brl(pedido.valor_total)}", styles['Normal']))
        elements.append(Spacer(1, 20))

        # Local de Entrega
        elements.append(Paragraph(f"<b>Local de Entrega:</b> {pedido.deposito_nome}", styles['Normal']))
        if pedido.endereco_entrega:
            elements.append(Paragraph(f"<b>Endereço:</b> {pedido.endereco_entrega}", styles['Normal']))
        
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
        header_table = ["Nº Cotação", "Ranking", "Fornecedor", "Valor Unit", "Valor Total", "Prazo", "Score", "Classificação", "Melhor Opção"]
        rows = []
        for cot in cotacoes:
            rows.append([
                cot.numero or "-",
                f"#{cot.posicao_ranking}",
                cot.fornecedor_nome,
                f"R$ {cot.valor_unitario:,.2f}" if cot.valor_unitario is not None else "Múltiplos itens",
                f"R$ {cot.valor_total:,.2f}",
                f"{cot.prazo_entrega_dias} dias" if cot.prazo_entrega_dias else "N/A",
                f"{cot.score_compra:.1f}",
                cot.classificacao_score,
                "SIM" if cot.melhor_opcao else ""
            ])
            
        t_comp = Table([header_table] + rows, colWidths=[70, 50, 150, 70, 70, 55, 50, 90, 70])
        
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
                 table_style_list.append(('TEXTCOLOR', (7, i+1), (7, i+1), colors.red))
                 
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
        # 1. Query para Cotações — usa CotacaoItem (linha por produto), não o
        # campo legado CotacaoCompra.valor_unitario, que é NULL em cotações
        # multi-item e quebraria as agregações abaixo (sum() com None).
        stmt_cot = (
            select(
                CotacaoCompra.fornecedor_nome,
                CotacaoItem.valor_unitario,
                CotacaoCompra.created_at.label("data"),
                literal_column("'COTACAO'").label("origem")
            )
            .join(CotacaoItem, CotacaoItem.cotacao_id == CotacaoCompra.id)
            .where(
                CotacaoItem.produto_id == item_id,
                CotacaoCompra.tenant_id == self.tenant_id
            )
        )
        
        # 2. Query para Pedidos — via ItemPedidoCompra (um pedido pode ter
        # múltiplos itens; o preço é por item, não por pedido).
        stmt_ped = (
            select(
                PedidoCompra.fornecedor_nome,
                ItemPedidoCompra.preco_estimado_unitario.label("valor_unitario"),
                PedidoCompra.created_at.label("data"),
                literal_column("'PEDIDO'").label("origem")
            )
            .join(PedidoCompra, ItemPedidoCompra.pedido_id == PedidoCompra.id)
            .where(
                ItemPedidoCompra.produto_id == item_id,
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
            if row.valor_unitario is not None:
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

    async def calcular_score_compra(
        self, cotacao: CotacaoCompra, item_id: Optional[uuid.UUID] = None,
        valor_unitario: Optional[float] = None,
    ) -> dict:
        """
        Calcula o score de 0 a 100 para uma cotação baseado em múltiplos critérios.
        Retorna score, classificação e lista de motivos.

        `valor_unitario`: preço a comparar (item de referência). Se omitido, usa
        `cotacao.valor_unitario` — só existe para cotações de 1 item só.
        """
        score = 0.0
        motivos = []
        valor_unitario = valor_unitario if valor_unitario is not None else cotacao.valor_unitario

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
                
                if valor_unitario <= p_ideal:
                    score += 40
                    motivos.append("Preço excelente (abaixo ou igual à meta ideal)")
                elif valor_unitario <= p_max:
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
        
        # Melhor Decisão (Maior Economia Absoluta) — pega o pedido campeão e
        # usa o nome do primeiro item dele como rótulo (aproximação para
        # pedidos multi-item, igual ao comportamento anterior de item único).
        stmt_pedido_best = (
            select(PedidoCompra.id, PedidoCompra.economia_absoluta)
            .where(PedidoCompra.tenant_id == self.tenant_id)
            .order_by(PedidoCompra.economia_absoluta.desc())
            .limit(1)
        )
        pedido_best = (await self.session.execute(stmt_pedido_best)).one_or_none()
        best = None
        if pedido_best:
            stmt_item_best = (
                select(Produto.nome)
                .join(ItemPedidoCompra, ItemPedidoCompra.produto_id == Produto.id)
                .where(ItemPedidoCompra.pedido_id == pedido_best.id)
                .order_by(ItemPedidoCompra.id.asc())
                .limit(1)
            )
            nome_item_best = (await self.session.execute(stmt_item_best)).scalar_one_or_none()
            best = (nome_item_best or "N/A", pedido_best.economia_absoluta)

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

        # Item representante de cada pedido (o primeiro) — evita fan-out do
        # JOIN duplicar/multiplicar economia_absoluta em pedidos multi-item.
        item_principal_sq = (
            select(ItemPedidoCompra.pedido_id, ItemPedidoCompra.produto_id)
            .distinct(ItemPedidoCompra.pedido_id)
            .order_by(ItemPedidoCompra.pedido_id, ItemPedidoCompra.id.asc())
        ).subquery()

        stmt = (
            select(
                categoria_macro,
                func.sum(PedidoCompra.economia_absoluta).label("total_cat")
            )
            .join(item_principal_sq, item_principal_sq.c.pedido_id == PedidoCompra.id)
            .join(Produto, item_principal_sq.c.produto_id == Produto.id)
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


def _formatar_moeda_brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


async def _listar_itens_pedido_para_exibicao(session, pedido_id: uuid.UUID) -> list["ItemPedidoConfirmacaoPublica"]:
    """Retorna os itens do pedido formatados para exibição em telas/e-mails
    que apresentam os produtos em formato de tabela."""
    from operacional.schemas.compras import ItemPedidoConfirmacaoPublica

    stmt = (
        select(ItemPedidoCompra, Produto.nome)
        .join(Produto, ItemPedidoCompra.produto_id == Produto.id)
        .where(ItemPedidoCompra.pedido_id == pedido_id)
    )
    itens = (await session.execute(stmt)).all()
    return [
        ItemPedidoConfirmacaoPublica(
            produto_nome=nome,
            quantidade=item.quantidade_solicitada,
            unidade=item.unidade,
            preco_unitario=item.preco_estimado_unitario,
            valor_total=item.valor_total,
        )
        for item, nome in itens
    ]


async def obter_confirmacao_publica(session, token: str):
    """Consulta pública (sem tenant/JWT) do estado de um link de confirmação
    de pedido enviado ao fornecedor. Usada pela tela pública de confirmação."""
    from operacional.schemas.compras import PedidoConfirmacaoPublicaResponse

    stmt = select(PedidoConfirmacaoFornecedor).where(
        PedidoConfirmacaoFornecedor.token_confirmacao == token
    )
    confirmacao = (await session.execute(stmt)).scalar_one_or_none()
    if not confirmacao:
        raise BusinessRuleError("Link de confirmação inválido.")

    if confirmacao.status == "PENDENTE" and confirmacao.data_expiracao < datetime.now(timezone.utc):
        confirmacao.status = "EXPIRADO"
        session.add(confirmacao)
        await session.commit()

    pedido = await session.get(PedidoCompra, confirmacao.pedido_id)
    if not pedido:
        raise BusinessRuleError("Pedido não encontrado.")

    fornecedor = await session.get(Fornecedor, pedido.fornecedor_id) if pedido.fornecedor_id else None
    dados_fornecedor = (
        await obter_dados_exibicao_fornecedor(session, fornecedor.pessoa_id) if fornecedor else None
    )
    tenant = await session.get(Tenant, confirmacao.tenant_id)
    itens = await _listar_itens_pedido_para_exibicao(session, pedido.id)

    return PedidoConfirmacaoPublicaResponse(
        status=confirmacao.status,
        fornecedor_nome=(dados_fornecedor["nome_fantasia"] if dados_fornecedor else pedido.fornecedor_nome),
        tenant_nome=tenant.nome if tenant else "",
        itens=itens,
        valor_total=pedido.valor_total,
        condicoes_pagamento=pedido.condicoes_pagamento,
    )


async def responder_confirmacao_publica(session, token: str, senha: str, aceito: bool):
    """Registra o aceite ou a recusa do fornecedor. O token já identifica de
    forma única o tenant/pedido, então não há parâmetro de tenant aqui."""
    from operacional.schemas.compras import PedidoConfirmacaoPublicaResponse

    stmt = select(PedidoConfirmacaoFornecedor).where(
        PedidoConfirmacaoFornecedor.token_confirmacao == token
    )
    confirmacao = (await session.execute(stmt)).scalar_one_or_none()
    if not confirmacao:
        raise BusinessRuleError("Link de confirmação inválido.")
    if confirmacao.status != "PENDENTE":
        raise BusinessRuleError("Este pedido já foi respondido ou o link expirou.")
    if confirmacao.data_expiracao < datetime.now(timezone.utc):
        confirmacao.status = "EXPIRADO"
        session.add(confirmacao)
        await session.commit()
        raise BusinessRuleError("Link de confirmação expirado. Solicite o reenvio do pedido.")
    if confirmacao.tentativas_senha >= 5:
        raise BusinessRuleError("Número máximo de tentativas excedido. Solicite o reenvio do pedido.")

    senha_valida = bcrypt.checkpw(
        senha.encode("utf-8"), confirmacao.senha_confirmacao_hash.encode("utf-8")
    )
    if not senha_valida:
        confirmacao.tentativas_senha += 1
        session.add(confirmacao)
        await session.commit()
        raise BusinessRuleError("Senha de confirmação incorreta.")

    pedido = await session.get(PedidoCompra, confirmacao.pedido_id)
    if not pedido:
        raise BusinessRuleError("Pedido não encontrado.")

    confirmacao.status = "CONFIRMADO" if aceito else "RECUSADO"
    confirmacao.respondido_em = datetime.now(timezone.utc)
    session.add(confirmacao)

    if aceito:
        pedido.status = "CONFIRMADO"
        session.add(pedido)
        await session.flush()
        svc = ComprasService(session, pedido.tenant_id)
        await svc._gerar_despesa_adiantamento(pedido)
        await session.flush()
    else:
        pedido.status = "RECUSADO_FORNECEDOR"
        session.add(pedido)
        await session.flush()
        svc = ComprasService(session, pedido.tenant_id)
        await svc._reabrir_cotacoes_concorrentes(pedido)

    await session.commit()

    fornecedor = await session.get(Fornecedor, pedido.fornecedor_id) if pedido.fornecedor_id else None
    dados_fornecedor = (
        await obter_dados_exibicao_fornecedor(session, fornecedor.pessoa_id) if fornecedor else None
    )
    tenant = await session.get(Tenant, pedido.tenant_id)
    itens = await _listar_itens_pedido_para_exibicao(session, pedido.id)

    return PedidoConfirmacaoPublicaResponse(
        status=confirmacao.status,
        fornecedor_nome=(dados_fornecedor["nome_fantasia"] if dados_fornecedor else pedido.fornecedor_nome),
        tenant_nome=tenant.nome if tenant else "",
        itens=itens,
        valor_total=pedido.valor_total,
        condicoes_pagamento=pedido.condicoes_pagamento,
    )
