import uuid
from datetime import datetime
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_service import BaseService
from core.exceptions import BusinessRuleError, EntityNotFoundError
from agricola.planejamento_operacional.models import (
    PlanoOperacional,
    PlanoOperacionalTarefa,
    PlanoOperacionalTarefaInsumo,
    PlanoOperacionalTarefaMaoObra,
    PlanoOperacionalTarefaMaquinario,
)
from agricola.planejamento_operacional.schemas import (
    PlanoOperacionalCreate,
    PlanoOperacionalUpdate,
    PlanoOperacionalTarefaCreate,
    PlanoOperacionalTarefaUpdate,
    PlanoOperacionalTarefaInsumoCreate,
    PlanoOperacionalTarefaInsumoUpdate,
    PlanoOperacionalTarefaMaoObraCreate,
    PlanoOperacionalTarefaMaoObraUpdate,
    PlanoOperacionalTarefaMaquinarioCreate,
    PlanoOperacionalTarefaMaquinarioUpdate,
    SugestaoProdutoOrcamentoResponse,
    InsumoConsolidadoResponse,
    AplicarInsumoLoteRequest,
    AplicarInsumoLoteResponse,
    AplicarMaquinarioLoteRequest,
    AplicarMaoObraLoteRequest,
)
from agricola.safras.models import Safra
from agricola.tarefas.models import SafraTarefa, SafraTarefaNecessidade
from agricola.tarefas.schemas import TarefaUpdate
from agricola.a1_planejamento.models import ItemOrcamentoSafra
from core.cadastros.produtos.models import Produto
from core.cadastros.tipos_servico.models import TipoServico
from core.cadastros.equipamentos.models import Equipamento
from rh.models import ColaboradorRH
from operacional.models.estoque import SaldoEstoque, Deposito, ReservaEstoque
from operacional.services.estoque_service import EstoqueService
from operacional.schemas.estoque import ReservaCreate
from operacional.models.compras import SolicitacaoCompra
from operacional.services.compras_service import ComprasService
from operacional.schemas.compras import SolicitacaoCompraCreate, SolicitacaoItemCreate
from agricola.a1_planejamento.snapshot_service import SnapshotCustoService

# Status de SolicitacaoCompra que ainda contam como "pendência em aberto" para
# fins de idempotência — ver _get_solicitacao_ativa_do_insumo.
SOLICITACAO_COMPRA_STATUS_ENCERRADOS = {"ENCERRADA", "CANCELADA"}

# Planos nesses status não aceitam mais simulação/edição de insumos — a decisão
# já foi congelada (aprovação real de reserva/custo entra na Fase 4).
PLANO_STATUS_FECHADO_PARA_SIMULACAO = {"APROVADO", "EM_EXECUCAO", "CONCLUIDO", "CANCELADO"}

STATUS_ITEM_VALIDOS = {
    "NAO_ANALISADA", "AGUARDANDO_DEFINICAO", "PRONTA", "AGUARDANDO_COMPRA",
    "PARCIALMENTE_ATENDIDA", "PROGRAMADA", "REMOVIDA", "CANCELADA",
}
STATUS_ITEM_ATIVO_NO_PLANO = STATUS_ITEM_VALIDOS - {"REMOVIDA", "CANCELADA"}

# Planos nesses status "travam" a tarefa: ela não pode ser adicionada a outro plano
# enquanto este permanecer ativo, para evitar dupla programação do mesmo recurso.
PLANO_STATUS_ATIVO = {"APROVADO", "EM_EXECUCAO"}

TRANSICOES_PLANO = {
    "RASCUNHO":              ["EM_ANALISE", "CANCELADO"],
    "EM_ANALISE":            ["PARCIALMENTE_PRONTO", "PRONTO", "RASCUNHO", "CANCELADO"],
    "PARCIALMENTE_PRONTO":   ["PRONTO", "APROVADO", "CANCELADO"],
    "PRONTO":                ["APROVADO", "CANCELADO"],
    "APROVADO":              ["EM_EXECUCAO", "CANCELADO"],
    "EM_EXECUCAO":           ["CONCLUIDO", "CANCELADO"],
    "CONCLUIDO":             [],
    "CANCELADO":             [],
}


class PlanoOperacionalService(BaseService[PlanoOperacional]):
    """Fase 1 (PLANO-OPERACIONAL-01): CRUD do cabeçalho do plano e associação de
    tarefas. Sem reserva de estoque, sem compras, sem mão de obra — isso entra em
    fases posteriores (ver docs/implementation/reports/PLANO-OPERACIONAL-01-*.md).
    """

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        super().__init__(PlanoOperacional, session, tenant_id, user_id=user_id)

    async def _validar_safra(self, safra_id: uuid.UUID) -> None:
        stmt = select(Safra).where(Safra.id == safra_id, Safra.tenant_id == self.tenant_id)
        safra = (await self.session.execute(stmt)).scalars().first()
        if not safra:
            raise EntityNotFoundError(f"Safra {safra_id} não encontrada.")

    async def criar(self, dados: PlanoOperacionalCreate) -> PlanoOperacional:
        await self._validar_safra(dados.safra_id)
        return await self.create(dados)

    async def atualizar(self, plano_id: uuid.UUID, dados: PlanoOperacionalUpdate) -> PlanoOperacional:
        plano = await self.get_or_fail(plano_id)
        if plano.status not in ("RASCUNHO", "EM_ANALISE"):
            raise BusinessRuleError(
                f"Plano com status '{plano.status}' não pode ter o cabeçalho editado. "
                "Apenas planos em RASCUNHO ou EM_ANALISE aceitam edição direta."
            )
        return await self.update(plano_id, dados)

    async def avancar_status(self, plano_id: uuid.UUID, novo_status: str) -> PlanoOperacional:
        plano = await self.get_or_fail(plano_id)
        permitidos = TRANSICOES_PLANO.get(plano.status, [])
        if novo_status not in permitidos:
            raise BusinessRuleError(
                f"Transição de status '{plano.status}' -> '{novo_status}' não é permitida."
            )

        if novo_status == "CANCELADO":
            # Reservas ativas de insumos deste plano nunca podem sobreviver ao
            # cancelamento do plano — senão o estoque fica bloqueado para sempre.
            await self._liberar_todas_reservas_do_plano(plano_id)

        update_kwargs: dict = {"status": novo_status}
        if novo_status == "APROVADO":
            update_kwargs["aprovado_por"] = self.user_id
            update_kwargs["aprovado_em"] = datetime.utcnow()

        return await self.update(plano_id, update_kwargs)

    # ------------------------------------------------------------------
    # Itens do plano (PlanoOperacionalTarefa)
    # ------------------------------------------------------------------

    async def _validar_tarefa(self, safra_tarefa_id: uuid.UUID) -> SafraTarefa:
        stmt = select(SafraTarefa).where(
            SafraTarefa.id == safra_tarefa_id,
            SafraTarefa.tenant_id == self.tenant_id,
        )
        tarefa = (await self.session.execute(stmt)).scalars().first()
        if not tarefa:
            raise EntityNotFoundError(f"Tarefa {safra_tarefa_id} não encontrada.")
        if tarefa.status != "APROVADA":
            raise BusinessRuleError(
                f"Tarefa com status '{tarefa.status}' não pode entrar em um plano. "
                "Apenas tarefas já aprovadas agronomicamente podem ser planejadas."
            )
        return tarefa

    async def _tarefa_em_plano_ativo(self, safra_tarefa_id: uuid.UUID, ignorar_item_id: uuid.UUID | None = None) -> bool:
        stmt = (
            select(PlanoOperacionalTarefa)
            .join(PlanoOperacional, PlanoOperacionalTarefa.plano_operacional_id == PlanoOperacional.id)
            .where(
                PlanoOperacionalTarefa.tenant_id == self.tenant_id,
                PlanoOperacionalTarefa.safra_tarefa_id == safra_tarefa_id,
                PlanoOperacionalTarefa.status_planejamento.in_(STATUS_ITEM_ATIVO_NO_PLANO),
                PlanoOperacional.status.in_(PLANO_STATUS_ATIVO),
            )
        )
        if ignorar_item_id:
            stmt = stmt.where(PlanoOperacionalTarefa.id != ignorar_item_id)
        existente = (await self.session.execute(stmt)).scalars().first()
        return existente is not None

    async def adicionar_tarefa(self, plano_id: uuid.UUID, dados: PlanoOperacionalTarefaCreate) -> PlanoOperacionalTarefa:
        plano = await self.get_or_fail(plano_id)
        if plano.status in ("CONCLUIDO", "CANCELADO"):
            raise BusinessRuleError(f"Plano com status '{plano.status}' não aceita novas tarefas.")

        tarefa = await self._validar_tarefa(dados.safra_tarefa_id)
        if tarefa.safra_id != plano.safra_id:
            raise BusinessRuleError("A tarefa pertence a uma safra diferente da safra do plano.")

        if await self._tarefa_em_plano_ativo(dados.safra_tarefa_id):
            raise BusinessRuleError(
                "Esta tarefa já está em outro plano operacional aprovado/em execução. "
                "Uma tarefa não pode ser programada por dois planos ativos simultaneamente."
            )

        # Idempotência: se já existe o vínculo (inclusive removido), reativa em vez de duplicar.
        stmt_existente = select(PlanoOperacionalTarefa).where(
            PlanoOperacionalTarefa.tenant_id == self.tenant_id,
            PlanoOperacionalTarefa.plano_operacional_id == plano_id,
            PlanoOperacionalTarefa.safra_tarefa_id == dados.safra_tarefa_id,
        )
        item_existente = (await self.session.execute(stmt_existente)).scalars().first()
        if item_existente:
            if item_existente.status_planejamento in ("REMOVIDA", "CANCELADA"):
                item_existente.status_planejamento = "NAO_ANALISADA"
                self.session.add(item_existente)
                await self.session.flush()
            return item_existente

        item = PlanoOperacionalTarefa(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            plano_operacional_id=plano_id,
            safra_tarefa_id=dados.safra_tarefa_id,
            status_planejamento="NAO_ANALISADA",
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def _get_item_or_fail(self, plano_id: uuid.UUID, item_id: uuid.UUID) -> PlanoOperacionalTarefa:
        stmt = select(PlanoOperacionalTarefa).where(
            PlanoOperacionalTarefa.id == item_id,
            PlanoOperacionalTarefa.plano_operacional_id == plano_id,
            PlanoOperacionalTarefa.tenant_id == self.tenant_id,
        )
        item = (await self.session.execute(stmt)).scalars().first()
        if not item:
            raise EntityNotFoundError(f"Item {item_id} não encontrado neste plano.")
        return item

    async def atualizar_item(
        self, plano_id: uuid.UUID, item_id: uuid.UUID, dados: PlanoOperacionalTarefaUpdate
    ) -> PlanoOperacionalTarefa:
        item = await self._get_item_or_fail(plano_id, item_id)
        dados_dict = dados.model_dump(exclude_unset=True)

        novo_status = dados_dict.get("status_planejamento")
        if novo_status is not None and novo_status not in STATUS_ITEM_VALIDOS:
            raise BusinessRuleError(f"Status de item de plano inválido: '{novo_status}'.")

        for campo, valor in dados_dict.items():
            setattr(item, campo, valor)

        self.session.add(item)
        await self.session.flush()
        return item

    async def remover_tarefa(self, plano_id: uuid.UUID, item_id: uuid.UUID) -> PlanoOperacionalTarefa:
        """Remoção lógica (nunca hard_delete): preserva histórico de que a tarefa
        já passou por este plano, consistente com o restante do domínio (nenhuma
        entidade ligada ao pipeline econômico é excluída fisicamente por aqui)."""
        item = await self._get_item_or_fail(plano_id, item_id)
        item.status_planejamento = "REMOVIDA"
        self.session.add(item)
        await self.session.flush()
        return item

    async def listar_itens(self, plano_id: uuid.UUID) -> list[PlanoOperacionalTarefa]:
        await self.get_or_fail(plano_id)  # valida existência + tenant
        stmt = select(PlanoOperacionalTarefa).where(
            PlanoOperacionalTarefa.tenant_id == self.tenant_id,
            PlanoOperacionalTarefa.plano_operacional_id == plano_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    # ------------------------------------------------------------------
    # Insumos do item de plano (PlanoOperacionalTarefaInsumo) — Fase 3
    # ------------------------------------------------------------------

    async def _get_plano_e_item(self, plano_id: uuid.UUID, item_id: uuid.UUID) -> tuple[PlanoOperacional, PlanoOperacionalTarefa]:
        plano = await self.get_or_fail(plano_id)
        item = await self._get_item_or_fail(plano_id, item_id)
        return plano, item

    def _validar_plano_editavel_para_insumo(
        self, plano: PlanoOperacional, item: PlanoOperacionalTarefa | None = None
    ) -> None:
        if plano.status in PLANO_STATUS_FECHADO_PARA_SIMULACAO:
            raise BusinessRuleError(
                f"Plano com status '{plano.status}' não aceita mais simulação/edição de insumos."
            )
        # Uma vez que a OS (OperacaoAgricola + TarefaCampo) já foi gerada para este
        # item, ele sai do domínio de simulação/planejamento — mexer em insumo, mão
        # de obra, maquinário ou receita aqui não é mais refletido na OS já criada e
        # possivelmente já sincronizada com o campo.
        if item is not None and item.status_planejamento == "PROGRAMADA":
            raise BusinessRuleError(
                "Este item já teve a OS gerada — não é mais possível editar "
                "insumos, mão de obra, maquinário ou receita dele neste plano."
            )

    async def _validar_produto(self, produto_id: uuid.UUID) -> Produto:
        stmt = select(Produto).where(
            Produto.id == produto_id,
            or_(Produto.tenant_id.is_(None), Produto.tenant_id == self.tenant_id),
        )
        produto = (await self.session.execute(stmt)).scalars().first()
        if not produto:
            raise EntityNotFoundError(f"Produto {produto_id} não encontrado.")
        return produto

    async def _calcular_disponibilidade(
        self, produto_id: uuid.UUID, deposito_id: uuid.UUID | None
    ) -> tuple[float, float]:
        """Soma `SaldoEstoque` (físico e reservado por OUTROS fluxos, ex.: compras)
        do produto, escopado ao tenant via join com `Deposito`, e opcionalmente a
        um depósito específico. Não cria nem altera nenhuma reserva — leitura pura,
        consistente com o guardrail A do relatório de auditoria (reserva nunca é
        um lançamento/campo tocado fora do fluxo próprio de `ReservaEstoque`)."""
        stmt = (
            select(
                func.coalesce(func.sum(SaldoEstoque.quantidade_atual), 0.0),
                func.coalesce(func.sum(SaldoEstoque.quantidade_reservada), 0.0),
            )
            .select_from(SaldoEstoque)
            .join(Deposito, SaldoEstoque.deposito_id == Deposito.id)
            .where(
                Deposito.tenant_id == self.tenant_id,
                SaldoEstoque.produto_id == produto_id,
            )
        )
        if deposito_id:
            stmt = stmt.where(SaldoEstoque.deposito_id == deposito_id)
        saldo_fisico, saldo_reservado = (await self.session.execute(stmt)).first()
        return float(saldo_fisico or 0.0), float(saldo_reservado or 0.0)

    async def _resolver_custo_produto(self, produto_id: uuid.UUID, unidade: str) -> tuple[float | None, str]:
        # Reaproveita o SnapshotCustoService já existente (agricola/a1_planejamento),
        # a mesma fonte de captura de custo usada no orçamento de safra — não
        # duplica lógica de "ler preço do cadastro mestre" (ver relatório §7/§12).
        # Nunca inventa valor: capturar() sempre retorna um Decimal (0 quando o
        # cadastro não tem preço), então tratamos 0/None como CUSTO_INCOMPLETO.
        snapshot_svc = SnapshotCustoService(self.session, self.tenant_id)
        preco, _ = await snapshot_svc.capturar("PRODUTO", produto_id, unidade)
        if preco and preco > 0:
            return float(preco), "PRODUTO_PRECO_MEDIO"
        return None, "CUSTO_INCOMPLETO"

    async def _montar_snapshot(self, insumo: PlanoOperacionalTarefaInsumo) -> None:
        await self._validar_produto(insumo.produto_id)
        saldo_fisico, saldo_reservado = await self._calcular_disponibilidade(insumo.produto_id, insumo.deposito_id)
        saldo_disponivel = saldo_fisico - saldo_reservado

        insumo.quantidade_disponivel_snapshot = saldo_disponivel
        insumo.quantidade_reservada = saldo_reservado
        insumo.quantidade_faltante = max(0.0, float(insumo.quantidade_planejada) - saldo_disponivel)

        custo_unitario, fonte_custo = await self._resolver_custo_produto(insumo.produto_id, insumo.unidade_dose)
        insumo.custo_unitario_snapshot = custo_unitario
        insumo.custo_total_estimado = (
            round(custo_unitario * float(insumo.quantidade_planejada), 2) if custo_unitario is not None else None
        )
        insumo.fonte_custo = fonte_custo

    # Necessidade não usa exatamente o vocabulário de CategoriaOrcamento
    # (tem CORRETIVO, que no orçamento é lançado como FERTILIZANTE).
    _CATEGORIA_NECESSIDADE_PARA_ORCAMENTO = {"CORRETIVO": "FERTILIZANTE", "OUTRO": "OUTROS"}

    # Categoria da necessidade -> qual fluxo de aplicação em lote usar.
    _CATEGORIA_PARA_TIPO_RECURSO = {
        "MAQUINARIO": "MAQUINARIO",
        "MAO_DE_OBRA": "MAO_DE_OBRA",
        "SERVICO": "MAO_DE_OBRA",
    }

    async def listar_insumos_consolidados(self, plano_id: uuid.UUID) -> list[InsumoConsolidadoResponse]:
        """
        Agrupa as necessidades técnicas de TODAS as tarefas do plano por
        categoria+item de origem (ex.: "FERTILIZANTE — NPK 20-05-20"), somando
        a quantidade entre talhões — para configurar o produto comercial uma
        vez e aplicar a todas as tarefas pendentes de uma vez, em vez de entrar
        tarefa por tarefa.
        """
        await self.get_or_fail(plano_id)  # valida existência/tenant do plano

        itens_stmt = select(PlanoOperacionalTarefa).where(
            PlanoOperacionalTarefa.plano_operacional_id == plano_id,
            PlanoOperacionalTarefa.tenant_id == self.tenant_id,
        )
        itens = (await self.session.execute(itens_stmt)).scalars().all()
        tarefa_id_por_safra_tarefa = {item.safra_tarefa_id: item for item in itens}
        if not tarefa_id_por_safra_tarefa:
            return []

        nec_stmt = select(SafraTarefaNecessidade).where(
            SafraTarefaNecessidade.tenant_id == self.tenant_id,
            SafraTarefaNecessidade.safra_tarefa_id.in_(tarefa_id_por_safra_tarefa.keys()),
        )
        necessidades = (await self.session.execute(nec_stmt)).scalars().all()
        if not necessidades:
            return []

        item_ids = [item.id for item in tarefa_id_por_safra_tarefa.values()]
        ja_aplicadas: set = set()
        for Model in (PlanoOperacionalTarefaInsumo, PlanoOperacionalTarefaMaoObra, PlanoOperacionalTarefaMaquinario):
            stmt = select(Model.safra_tarefa_necessidade_id).where(
                Model.plano_operacional_tarefa_id.in_(item_ids),
                Model.safra_tarefa_necessidade_id.is_not(None),
            )
            ja_aplicadas.update(row[0] for row in (await self.session.execute(stmt)).all())

        grupos: dict[str, dict] = {}
        for nec in necessidades:
            titulo = (nec.parametros_calculo or {}).get("titulo_item") or nec.categoria
            chave = f"{nec.categoria}::{titulo}"
            g = grupos.setdefault(chave, {
                "chave_grupo": chave,
                "categoria": nec.categoria,
                "titulo": titulo,
                "unidade": nec.unidade_referencia,
                "quantidade_total": 0.0,
                "quantidade_tarefas": 0,
                "quantidade_pendentes": 0,
                "necessidade_ids_pendentes": [],
                "tipo_recurso": self._CATEGORIA_PARA_TIPO_RECURSO.get(nec.categoria, "INSUMO"),
            })
            g["quantidade_total"] += float(nec.quantidade_tecnica or 0)
            g["quantidade_tarefas"] += 1
            if nec.id not in ja_aplicadas:
                g["quantidade_pendentes"] += 1
                g["necessidade_ids_pendentes"].append(nec.id)

        return [InsumoConsolidadoResponse(**g) for g in grupos.values()]

    async def aplicar_insumo_lote(
        self, plano_id: uuid.UUID, dados: AplicarInsumoLoteRequest
    ) -> AplicarInsumoLoteResponse:
        """Aplica o mesmo produto comercial a várias necessidades de uma vez (uma por tarefa)."""
        plano = await self.get_or_fail(plano_id)
        await self._validar_produto(dados.produto_id)

        itens_stmt = select(PlanoOperacionalTarefa).where(
            PlanoOperacionalTarefa.plano_operacional_id == plano_id,
            PlanoOperacionalTarefa.tenant_id == self.tenant_id,
        )
        itens_por_safra_tarefa = {
            item.safra_tarefa_id: item
            for item in (await self.session.execute(itens_stmt)).scalars().all()
        }

        aplicadas = 0
        ignoradas = 0
        for necessidade_id in dados.necessidade_ids:
            necessidade = await self.session.get(SafraTarefaNecessidade, necessidade_id)
            if not necessidade or necessidade.tenant_id != self.tenant_id:
                ignoradas += 1
                continue
            item = itens_por_safra_tarefa.get(necessidade.safra_tarefa_id)
            if item is None:
                ignoradas += 1
                continue
            try:
                self._validar_plano_editavel_para_insumo(plano, item)
            except BusinessRuleError:
                ignoradas += 1
                continue

            ja_existe_stmt = select(PlanoOperacionalTarefaInsumo.id).where(
                PlanoOperacionalTarefaInsumo.plano_operacional_tarefa_id == item.id,
                PlanoOperacionalTarefaInsumo.safra_tarefa_necessidade_id == necessidade_id,
            )
            if (await self.session.execute(ja_existe_stmt)).scalar_one_or_none():
                ignoradas += 1
                continue

            insumo = PlanoOperacionalTarefaInsumo(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                plano_operacional_tarefa_id=item.id,
                safra_tarefa_necessidade_id=necessidade_id,
                produto_id=dados.produto_id,
                deposito_id=dados.deposito_id,
                dose_planejada=necessidade.dose_tecnica,
                unidade_dose=necessidade.unidade_referencia,
                quantidade_planejada=necessidade.quantidade_tecnica or 0,
            )
            await self._montar_snapshot(insumo)
            self.session.add(insumo)
            aplicadas += 1

        await self.session.flush()
        return AplicarInsumoLoteResponse(quantidade_aplicada=aplicadas, quantidade_ignorada=ignoradas)

    async def aplicar_maquinario_lote(
        self, plano_id: uuid.UUID, dados: AplicarMaquinarioLoteRequest
    ) -> AplicarInsumoLoteResponse:
        """Aplica a mesma máquina/implemento a várias necessidades de MAQUINARIO de uma vez."""
        plano = await self.get_or_fail(plano_id)
        if not dados.maquina_id and not dados.implemento_id:
            raise BusinessRuleError("Informe ao menos uma máquina ou um implemento.")

        itens_stmt = select(PlanoOperacionalTarefa).where(
            PlanoOperacionalTarefa.plano_operacional_id == plano_id,
            PlanoOperacionalTarefa.tenant_id == self.tenant_id,
        )
        itens_por_safra_tarefa = {
            item.safra_tarefa_id: item
            for item in (await self.session.execute(itens_stmt)).scalars().all()
        }

        aplicadas = 0
        ignoradas = 0
        for necessidade_id in dados.necessidade_ids:
            necessidade = await self.session.get(SafraTarefaNecessidade, necessidade_id)
            if not necessidade or necessidade.tenant_id != self.tenant_id:
                ignoradas += 1
                continue
            item = itens_por_safra_tarefa.get(necessidade.safra_tarefa_id)
            if item is None:
                ignoradas += 1
                continue
            try:
                self._validar_plano_editavel_para_insumo(plano, item)
            except BusinessRuleError:
                ignoradas += 1
                continue

            ja_existe_stmt = select(PlanoOperacionalTarefaMaquinario.id).where(
                PlanoOperacionalTarefaMaquinario.plano_operacional_tarefa_id == item.id,
                PlanoOperacionalTarefaMaquinario.safra_tarefa_necessidade_id == necessidade_id,
            )
            if (await self.session.execute(ja_existe_stmt)).scalar_one_or_none():
                ignoradas += 1
                continue

            maquinario = PlanoOperacionalTarefaMaquinario(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                plano_operacional_tarefa_id=item.id,
                safra_tarefa_necessidade_id=necessidade_id,
                maquina_id=dados.maquina_id,
                implemento_id=dados.implemento_id,
                horas_estimadas=necessidade.quantidade_tecnica,
            )
            await self._montar_snapshot_maquinario(maquinario)
            self.session.add(maquinario)
            aplicadas += 1

        await self.session.flush()
        return AplicarInsumoLoteResponse(quantidade_aplicada=aplicadas, quantidade_ignorada=ignoradas)

    async def aplicar_mao_obra_lote(
        self, plano_id: uuid.UUID, dados: AplicarMaoObraLoteRequest
    ) -> AplicarInsumoLoteResponse:
        """Aplica o mesmo tipo de serviço/pessoa a várias necessidades de MAO_DE_OBRA/SERVICO de uma vez."""
        plano = await self.get_or_fail(plano_id)
        await self._validar_tipo_servico(dados.tipo_servico_id)

        itens_stmt = select(PlanoOperacionalTarefa).where(
            PlanoOperacionalTarefa.plano_operacional_id == plano_id,
            PlanoOperacionalTarefa.tenant_id == self.tenant_id,
        )
        itens_por_safra_tarefa = {
            item.safra_tarefa_id: item
            for item in (await self.session.execute(itens_stmt)).scalars().all()
        }

        aplicadas = 0
        ignoradas = 0
        for necessidade_id in dados.necessidade_ids:
            necessidade = await self.session.get(SafraTarefaNecessidade, necessidade_id)
            if not necessidade or necessidade.tenant_id != self.tenant_id:
                ignoradas += 1
                continue
            item = itens_por_safra_tarefa.get(necessidade.safra_tarefa_id)
            if item is None:
                ignoradas += 1
                continue
            try:
                self._validar_plano_editavel_para_insumo(plano, item)
            except BusinessRuleError:
                ignoradas += 1
                continue

            ja_existe_stmt = select(PlanoOperacionalTarefaMaoObra.id).where(
                PlanoOperacionalTarefaMaoObra.plano_operacional_tarefa_id == item.id,
                PlanoOperacionalTarefaMaoObra.safra_tarefa_necessidade_id == necessidade_id,
            )
            if (await self.session.execute(ja_existe_stmt)).scalar_one_or_none():
                ignoradas += 1
                continue

            mao_obra = PlanoOperacionalTarefaMaoObra(
                id=uuid.uuid4(),
                tenant_id=self.tenant_id,
                plano_operacional_tarefa_id=item.id,
                safra_tarefa_necessidade_id=necessidade_id,
                tipo_servico_id=dados.tipo_servico_id,
                pessoa_id=dados.pessoa_id,
                quantidade_pessoas=dados.quantidade_pessoas,
                horas_estimadas=necessidade.quantidade_tecnica,
            )
            await self._montar_snapshot_mao_obra(mao_obra)
            self.session.add(mao_obra)
            aplicadas += 1

        await self.session.flush()
        return AplicarInsumoLoteResponse(quantidade_aplicada=aplicadas, quantidade_ignorada=ignoradas)

    async def sugerir_produtos_orcamento(
        self, safra_tarefa_necessidade_id: uuid.UUID
    ) -> list[SugestaoProdutoOrcamentoResponse]:
        """
        Sugere produtos já escolhidos no orçamento da safra (mesma categoria,
        origem_tipo=PRODUTO) para preencher o produto comercial de uma
        necessidade técnica — evita escolher de novo algo já decidido lá.
        Não substitui a busca manual: quando não há candidato, retorna vazio.
        """
        necessidade = await self.session.get(SafraTarefaNecessidade, safra_tarefa_necessidade_id)
        if not necessidade or necessidade.tenant_id != self.tenant_id:
            raise EntityNotFoundError(f"Necessidade {safra_tarefa_necessidade_id} não encontrada.")

        tarefa = await self.session.get(SafraTarefa, necessidade.safra_tarefa_id)
        if not tarefa:
            raise EntityNotFoundError(f"Tarefa {necessidade.safra_tarefa_id} não encontrada.")

        categoria_orcamento = self._CATEGORIA_NECESSIDADE_PARA_ORCAMENTO.get(
            necessidade.categoria, necessidade.categoria
        )

        stmt = (
            select(ItemOrcamentoSafra, Produto.nome)
            .join(Produto, Produto.id == ItemOrcamentoSafra.origem_id)
            .where(
                ItemOrcamentoSafra.tenant_id == self.tenant_id,
                ItemOrcamentoSafra.safra_id == tarefa.safra_id,
                ItemOrcamentoSafra.categoria == categoria_orcamento,
                ItemOrcamentoSafra.origem_tipo == "PRODUTO",
                ItemOrcamentoSafra.origem_id.is_not(None),
            )
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            SugestaoProdutoOrcamentoResponse(
                item_orcamento_id=item.id,
                produto_id=item.origem_id,
                produto_nome=produto_nome,
                descricao=item.descricao,
                unidade=item.unidade,
                custo_unitario_efetivo=item.custo_unitario_efetivo,
            )
            for item, produto_nome in rows
        ]

    async def adicionar_insumo(
        self, plano_id: uuid.UUID, item_id: uuid.UUID, dados: PlanoOperacionalTarefaInsumoCreate
    ) -> PlanoOperacionalTarefaInsumo:
        plano, item = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano, item)
        await self._validar_produto(dados.produto_id)

        if dados.safra_tarefa_necessidade_id:
            stmt = select(SafraTarefaNecessidade).where(
                SafraTarefaNecessidade.id == dados.safra_tarefa_necessidade_id,
                SafraTarefaNecessidade.tenant_id == self.tenant_id,
                SafraTarefaNecessidade.safra_tarefa_id == item.safra_tarefa_id,
            )
            necessidade = (await self.session.execute(stmt)).scalars().first()
            if not necessidade:
                raise EntityNotFoundError(
                    f"Necessidade {dados.safra_tarefa_necessidade_id} não encontrada nesta tarefa."
                )

        insumo = PlanoOperacionalTarefaInsumo(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            plano_operacional_tarefa_id=item_id,
            safra_tarefa_necessidade_id=dados.safra_tarefa_necessidade_id,
            produto_id=dados.produto_id,
            deposito_id=dados.deposito_id,
            dose_planejada=dados.dose_planejada,
            unidade_dose=dados.unidade_dose,
            quantidade_planejada=dados.quantidade_planejada,
        )
        await self._montar_snapshot(insumo)
        self.session.add(insumo)
        await self.session.flush()
        return insumo

    async def recalcular_insumo(
        self, plano_id: uuid.UUID, item_id: uuid.UUID, insumo_id: uuid.UUID
    ) -> PlanoOperacionalTarefaInsumo:
        """Reprocessa o snapshot (disponibilidade/custo) com os dados atuais de
        estoque/produto — só permitido enquanto o plano ainda está em simulação."""
        plano, item = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano, item)
        insumo = await self._get_insumo_or_fail(item_id, insumo_id)
        await self._montar_snapshot(insumo)
        self.session.add(insumo)
        await self.session.flush()
        return insumo

    async def _get_insumo_or_fail(
        self, item_id: uuid.UUID, insumo_id: uuid.UUID
    ) -> PlanoOperacionalTarefaInsumo:
        stmt = select(PlanoOperacionalTarefaInsumo).where(
            PlanoOperacionalTarefaInsumo.id == insumo_id,
            PlanoOperacionalTarefaInsumo.plano_operacional_tarefa_id == item_id,
            PlanoOperacionalTarefaInsumo.tenant_id == self.tenant_id,
        )
        insumo = (await self.session.execute(stmt)).scalars().first()
        if not insumo:
            raise EntityNotFoundError(f"Insumo {insumo_id} não encontrado neste item de plano.")
        return insumo

    async def atualizar_insumo(
        self, plano_id: uuid.UUID, item_id: uuid.UUID, insumo_id: uuid.UUID, dados: PlanoOperacionalTarefaInsumoUpdate
    ) -> PlanoOperacionalTarefaInsumo:
        plano, item = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano, item)
        insumo = await self._get_insumo_or_fail(item_id, insumo_id)

        dados_dict = dados.model_dump(exclude_unset=True)
        # Mudar produto/depósito/quantidade invalida uma reserva já feita para os
        # dados antigos — libera antes de aplicar, para não deixar estoque preso
        # a um insumo que não existe mais desse jeito.
        campos_sensiveis = {"produto_id", "deposito_id", "quantidade_planejada"}
        if insumo.reserva_estoque_id and campos_sensiveis & dados_dict.keys():
            await self.liberar_reserva_insumo(plano_id, item_id, insumo_id)

        for campo, valor in dados_dict.items():
            setattr(insumo, campo, valor)

        await self._montar_snapshot(insumo)
        self.session.add(insumo)
        await self.session.flush()
        return insumo

    async def remover_insumo(self, plano_id: uuid.UUID, item_id: uuid.UUID, insumo_id: uuid.UUID) -> None:
        plano, item = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano, item)
        insumo = await self._get_insumo_or_fail(item_id, insumo_id)
        if insumo.reserva_estoque_id:
            await self.liberar_reserva_insumo(plano_id, item_id, insumo_id)
        # Hard delete seguro aqui: é só decisão de planejamento/simulação, nenhum
        # estoque_movimentos ou OperacaoExecucao real foi criado a partir disto.
        await self.session.delete(insumo)
        await self.session.flush()

    async def listar_insumos(self, plano_id: uuid.UUID, item_id: uuid.UUID) -> list[PlanoOperacionalTarefaInsumo]:
        await self._get_plano_e_item(plano_id, item_id)
        stmt = select(PlanoOperacionalTarefaInsumo).where(
            PlanoOperacionalTarefaInsumo.tenant_id == self.tenant_id,
            PlanoOperacionalTarefaInsumo.plano_operacional_tarefa_id == item_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    # ------------------------------------------------------------------
    # Reserva real de estoque e aprovação parcial (Fase 4)
    # ------------------------------------------------------------------

    async def _resolver_deposito_para_reserva(self, insumo: PlanoOperacionalTarefaInsumo) -> uuid.UUID:
        if insumo.deposito_id:
            return insumo.deposito_id

        stmt = (
            select(SaldoEstoque.deposito_id)
            .select_from(SaldoEstoque)
            .join(Deposito, SaldoEstoque.deposito_id == Deposito.id)
            .where(
                Deposito.tenant_id == self.tenant_id,
                SaldoEstoque.produto_id == insumo.produto_id,
                (SaldoEstoque.quantidade_atual - SaldoEstoque.quantidade_reservada) >= float(insumo.quantidade_planejada),
            )
        )
        candidatos = list((await self.session.execute(stmt)).scalars().all())
        if len(candidatos) == 1:
            return candidatos[0]
        if not candidatos:
            raise BusinessRuleError(
                "Nenhum depósito tem saldo suficiente para reservar este insumo. "
                "Solicite compra ou informe o depósito manualmente."
            )
        raise BusinessRuleError(
            "Mais de um depósito tem saldo suficiente para este produto. "
            "Defina explicitamente o depósito do insumo antes de reservar."
        )

    async def reservar_insumo(
        self, plano_id: uuid.UUID, item_id: uuid.UUID, insumo_id: uuid.UUID
    ) -> PlanoOperacionalTarefaInsumo:
        """Cria uma reserva real (`ReservaEstoque`) para o insumo, revalidando
        saldo na mesma transação com lock de linha em `SaldoEstoque` — ordem de
        lock fixada pelo ponto B do relatório de auditoria: reserva/estoque
        sempre ANTES de qualquer chamada a `gerar_operacao_planejada` (que já
        lockeia `SafraTarefa` internamente), para nunca invertê-la em outra
        rotina e criar deadlock cruzado.
        """
        plano, item = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano, item)
        insumo = await self._get_insumo_or_fail(item_id, insumo_id)

        if insumo.reserva_estoque_id:
            reserva_existente = await self.session.get(ReservaEstoque, insumo.reserva_estoque_id)
            if reserva_existente and reserva_existente.status == "ATIVA":
                return insumo  # idempotente: já reservado, não duplica

        deposito_id = await self._resolver_deposito_para_reserva(insumo)

        stmt_lock = select(SaldoEstoque).where(
            SaldoEstoque.deposito_id == deposito_id,
            SaldoEstoque.produto_id == insumo.produto_id,
        ).with_for_update()
        saldo = (await self.session.execute(stmt_lock)).scalars().first()
        disponivel = (float(saldo.quantidade_atual) - float(saldo.quantidade_reservada)) if saldo else 0.0

        if disponivel < float(insumo.quantidade_planejada):
            insumo.deposito_id = deposito_id
            await self._montar_snapshot(insumo)
            self.session.add(insumo)
            await self.session.flush()
            raise BusinessRuleError(
                f"Saldo insuficiente para reservar este insumo: disponível {disponivel:.2f}, "
                f"necessário {float(insumo.quantidade_planejada):.2f}."
            )

        estoque_svc = EstoqueService(self.session, self.tenant_id)
        reserva = await estoque_svc.criar_reserva(
            ReservaCreate(
                produto_id=insumo.produto_id,
                deposito_id=deposito_id,
                quantidade=float(insumo.quantidade_planejada),
                motivo=f"Planejamento Operacional — item {item_id}",
                referencia_tipo="PLANO_OPERACIONAL",
                referencia_id=insumo.id,
            ),
            usuario_id=self.user_id,
        )
        insumo.deposito_id = deposito_id
        insumo.reserva_estoque_id = reserva.id
        await self._montar_snapshot(insumo)
        self.session.add(insumo)
        await self.session.flush()
        return insumo

    async def liberar_reserva_insumo(
        self, plano_id: uuid.UUID, item_id: uuid.UUID, insumo_id: uuid.UUID
    ) -> PlanoOperacionalTarefaInsumo:
        """Cancela a reserva ativa do insumo (se houver) e devolve o saldo
        reservado. Intencionalmente NÃO bloqueado por `_validar_plano_editavel_
        para_insumo`: precisa funcionar mesmo com o plano já CANCELADO/APROVADO
        (é exatamente quando uma reserva precisa ser liberada)."""
        await self._get_plano_e_item(plano_id, item_id)
        insumo = await self._get_insumo_or_fail(item_id, insumo_id)
        if insumo.reserva_estoque_id:
            estoque_svc = EstoqueService(self.session, self.tenant_id)
            reserva = await self.session.get(ReservaEstoque, insumo.reserva_estoque_id)
            if reserva and reserva.status == "ATIVA":
                await estoque_svc.cancelar_reserva(reserva.id)
            insumo.reserva_estoque_id = None
            await self._montar_snapshot(insumo)
            self.session.add(insumo)
            await self.session.flush()
        return insumo

    async def _liberar_todas_reservas_do_plano(self, plano_id: uuid.UUID) -> None:
        itens = await self.listar_itens(plano_id)
        for item in itens:
            insumos = await self.listar_insumos(plano_id, item.id)
            for insumo in insumos:
                if insumo.reserva_estoque_id:
                    await self.liberar_reserva_insumo(plano_id, item.id, insumo.id)

    async def aprovar_item(self, plano_id: uuid.UUID, item_id: uuid.UUID) -> PlanoOperacionalTarefa:
        """Aprovação PARCIAL: tenta reservar todos os insumos do item. Insumos
        sem saldo suficiente não travam os demais — o item fica PRONTA (tudo
        reservado), AGUARDANDO_COMPRA (nada reservado) ou PARCIALMENTE_ATENDIDA
        (alguns sim, outros não), permitindo que o plano avance com o que já
        está disponível enquanto o resto aguarda compra."""
        plano, item = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano, item)
        insumos = await self.listar_insumos(plano_id, item_id)
        if not insumos:
            raise BusinessRuleError("Item de plano sem insumos definidos não pode ser aprovado.")

        sucesso = 0
        for insumo in insumos:
            try:
                await self.reservar_insumo(plano_id, item_id, insumo.id)
                sucesso += 1
            except BusinessRuleError:
                continue

        if sucesso == len(insumos):
            item.status_planejamento = "PRONTA"
        elif sucesso == 0:
            item.status_planejamento = "AGUARDANDO_COMPRA"
        else:
            item.status_planejamento = "PARCIALMENTE_ATENDIDA"

        self.session.add(item)
        await self.session.flush()
        return item

    # ------------------------------------------------------------------
    # Integração com Compras (Fase 5) — nunca silenciosa: sempre uma ação
    # explícita do usuário, nunca disparada automaticamente ao detectar falta.
    # ------------------------------------------------------------------

    async def _get_solicitacao_ativa_do_insumo(self, insumo_id: uuid.UUID) -> SolicitacaoCompra | None:
        stmt = select(SolicitacaoCompra).where(
            SolicitacaoCompra.tenant_id == self.tenant_id,
            SolicitacaoCompra.origem == "PLANO_OPERACIONAL",
            SolicitacaoCompra.origem_id == str(insumo_id),
            SolicitacaoCompra.status.notin_(SOLICITACAO_COMPRA_STATUS_ENCERRADOS),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def solicitar_compra_insumo(
        self, plano_id: uuid.UUID, item_id: uuid.UUID, insumo_id: uuid.UUID
    ) -> SolicitacaoCompra:
        """Cria uma `SolicitacaoCompra` (reaproveitando `ComprasService.
        criar_solicitacao`, já maduro — não recria pedido/cotação/fornecedor)
        para a quantidade faltante do insumo. Idempotente: uma solicitação
        ativa (não encerrada/cancelada) já existente para este insumo é
        retornada em vez de duplicada. Requer confirmação explícita do
        usuário — nunca é disparada automaticamente ao detectar falta."""
        plano, item = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano, item)
        insumo = await self._get_insumo_or_fail(item_id, insumo_id)

        await self._montar_snapshot(insumo)  # garante que a falta reflete o saldo atual
        self.session.add(insumo)
        await self.session.flush()

        if not insumo.quantidade_faltante or insumo.quantidade_faltante <= 0:
            raise BusinessRuleError(
                "Este insumo não tem quantidade faltante — não há necessidade de solicitar compra."
            )
        if not insumo.deposito_id:
            raise BusinessRuleError(
                "Defina o depósito do insumo antes de solicitar compra "
                "(não escolhemos automaticamente sem saldo suficiente para confirmar o destino)."
            )

        solicitacao_existente = await self._get_solicitacao_ativa_do_insumo(insumo.id)
        if solicitacao_existente:
            return solicitacao_existente

        compras_svc = ComprasService(self.session, self.tenant_id)
        return await compras_svc.criar_solicitacao(
            SolicitacaoCompraCreate(
                itens=[
                    SolicitacaoItemCreate(
                        produto_id=insumo.produto_id,
                        deposito_id=insumo.deposito_id,
                        quantidade_solicitada=float(insumo.quantidade_faltante),
                        unidade=insumo.unidade_dose,
                    )
                ],
                origem="PLANO_OPERACIONAL",
                origem_id=str(insumo.id),
            ),
            solicitante_id=self.user_id,
        )

    # ------------------------------------------------------------------
    # Mão de obra do item de plano (Fase 6)
    # ------------------------------------------------------------------

    async def _validar_tipo_servico(self, tipo_servico_id: uuid.UUID) -> TipoServico:
        stmt = select(TipoServico).where(
            TipoServico.id == tipo_servico_id,
            or_(TipoServico.tenant_id.is_(None), TipoServico.tenant_id == self.tenant_id),
        )
        tipo_servico = (await self.session.execute(stmt)).scalars().first()
        if not tipo_servico:
            raise EntityNotFoundError(f"Tipo de serviço {tipo_servico_id} não encontrado.")
        return tipo_servico

    async def _resolver_custo_hora(
        self, tipo_servico_id: uuid.UUID, colaborador: ColaboradorRH | None
    ) -> tuple[float | None, str]:
        # Reaproveita o SnapshotCustoService já existente — mesma fonte de custo
        # do orçamento de safra (agricola/a1_planejamento). Prioriza o custo real
        # da pessoa alocada (ColaboradorRH.id, não pessoa_id — o service espera o
        # id do colaborador); cai para a referência do tipo de serviço só quando
        # não há pessoa definida ainda. Nunca inventa valor: sem fonte confiável
        # (>0), sinaliza CUSTO_INCOMPLETO. `unidade="hora"` força o service a usar
        # `valor_hora` (não `valor_diaria`) — nossa estimativa é sempre em horas.
        snapshot_svc = SnapshotCustoService(self.session, self.tenant_id)

        if colaborador:
            preco, _ = await snapshot_svc.capturar("PESSOA", colaborador.id, "hora")
            if preco and preco > 0:
                return float(preco), "PESSOA_VALOR_HORA"

        preco, _ = await snapshot_svc.capturar("SERVICO", tipo_servico_id, "hora")
        if preco and preco > 0:
            return float(preco), "TIPO_SERVICO_CUSTO_REFERENCIA"
        return None, "CUSTO_INCOMPLETO"

    async def _montar_snapshot_mao_obra(self, mao_obra: PlanoOperacionalTarefaMaoObra) -> None:
        await self._validar_tipo_servico(mao_obra.tipo_servico_id)

        colaborador = None
        if mao_obra.pessoa_id:
            stmt = select(ColaboradorRH).where(
                ColaboradorRH.tenant_id == self.tenant_id,
                ColaboradorRH.pessoa_id == mao_obra.pessoa_id,
            )
            colaborador = (await self.session.execute(stmt)).scalars().first()

        custo_hora, fonte_custo = await self._resolver_custo_hora(mao_obra.tipo_servico_id, colaborador)
        mao_obra.custo_hora_snapshot = custo_hora
        mao_obra.fonte_custo = fonte_custo
        if custo_hora is not None and mao_obra.horas_estimadas:
            mao_obra.custo_total_estimado = round(
                custo_hora * float(mao_obra.horas_estimadas) * mao_obra.quantidade_pessoas, 2
            )
        else:
            mao_obra.custo_total_estimado = None

    async def _calcular_horas_estimadas(
        self, item: PlanoOperacionalTarefa, dados: PlanoOperacionalTarefaMaoObraCreate
    ) -> float:
        if dados.horas_estimadas is not None:
            return dados.horas_estimadas
        tarefa = await self.session.get(SafraTarefa, item.safra_tarefa_id)
        area_ha = float(tarefa.area_ha) if tarefa and tarefa.area_ha else 0.0
        return dados.horas_fixas + dados.horas_por_hectare * area_ha

    async def adicionar_mao_obra(
        self, plano_id: uuid.UUID, item_id: uuid.UUID, dados: PlanoOperacionalTarefaMaoObraCreate
    ) -> PlanoOperacionalTarefaMaoObra:
        plano, item = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano, item)
        await self._validar_tipo_servico(dados.tipo_servico_id)

        horas_estimadas = await self._calcular_horas_estimadas(item, dados)
        mao_obra = PlanoOperacionalTarefaMaoObra(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            plano_operacional_tarefa_id=item_id,
            tipo_servico_id=dados.tipo_servico_id,
            pessoa_id=dados.pessoa_id,
            funcao=dados.funcao,
            quantidade_pessoas=dados.quantidade_pessoas,
            horas_estimadas=horas_estimadas,
        )
        await self._montar_snapshot_mao_obra(mao_obra)
        self.session.add(mao_obra)
        await self.session.flush()
        return mao_obra

    async def _get_mao_obra_or_fail(
        self, item_id: uuid.UUID, mao_obra_id: uuid.UUID
    ) -> PlanoOperacionalTarefaMaoObra:
        stmt = select(PlanoOperacionalTarefaMaoObra).where(
            PlanoOperacionalTarefaMaoObra.id == mao_obra_id,
            PlanoOperacionalTarefaMaoObra.plano_operacional_tarefa_id == item_id,
            PlanoOperacionalTarefaMaoObra.tenant_id == self.tenant_id,
        )
        mao_obra = (await self.session.execute(stmt)).scalars().first()
        if not mao_obra:
            raise EntityNotFoundError(f"Necessidade de mão de obra {mao_obra_id} não encontrada neste item.")
        return mao_obra

    async def atualizar_mao_obra(
        self, plano_id: uuid.UUID, item_id: uuid.UUID, mao_obra_id: uuid.UUID, dados: PlanoOperacionalTarefaMaoObraUpdate
    ) -> PlanoOperacionalTarefaMaoObra:
        plano, item = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano, item)
        mao_obra = await self._get_mao_obra_or_fail(item_id, mao_obra_id)

        dados_dict = dados.model_dump(exclude_unset=True)
        if "tipo_servico_id" in dados_dict:
            await self._validar_tipo_servico(dados_dict["tipo_servico_id"])

        for campo, valor in dados_dict.items():
            setattr(mao_obra, campo, valor)

        await self._montar_snapshot_mao_obra(mao_obra)
        self.session.add(mao_obra)
        await self.session.flush()
        return mao_obra

    async def remover_mao_obra(self, plano_id: uuid.UUID, item_id: uuid.UUID, mao_obra_id: uuid.UUID) -> None:
        plano, item = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano, item)
        mao_obra = await self._get_mao_obra_or_fail(item_id, mao_obra_id)
        # Hard delete seguro: é só estimativa de planejamento, nada realizado
        # foi criado a partir disto (equipe/execução ficam em OperacaoAgricola).
        await self.session.delete(mao_obra)
        await self.session.flush()

    async def listar_mao_obra(self, plano_id: uuid.UUID, item_id: uuid.UUID) -> list[PlanoOperacionalTarefaMaoObra]:
        await self._get_plano_e_item(plano_id, item_id)
        stmt = select(PlanoOperacionalTarefaMaoObra).where(
            PlanoOperacionalTarefaMaoObra.tenant_id == self.tenant_id,
            PlanoOperacionalTarefaMaoObra.plano_operacional_tarefa_id == item_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    # ------------------------------------------------------------------
    # Maquinário do item de plano (máquina + implemento)
    # ------------------------------------------------------------------

    async def _validar_equipamento(self, equipamento_id: uuid.UUID) -> Equipamento:
        stmt = select(Equipamento).where(
            Equipamento.id == equipamento_id,
            Equipamento.tenant_id == self.tenant_id,
        )
        equipamento = (await self.session.execute(stmt)).scalars().first()
        if not equipamento:
            raise EntityNotFoundError(f"Equipamento {equipamento_id} não encontrado.")
        return equipamento

    async def _resolver_custo_maquinario(
        self, maquina_id: uuid.UUID | None, implemento_id: uuid.UUID | None
    ) -> tuple[float | None, float | None, str]:
        # Reaproveita o SnapshotCustoService com origem_tipo="MAQUINA" — mesmo
        # caminho já usado no orçamento de safra (custo/hora real via
        # FrotaCustoService.obter_custo_equipamento). Implemento é o mesmo
        # cadastro de Equipamento, só outro registro; nenhuma lógica de custo
        # nova é criada aqui. Nunca inventa valor: sem custo/hora (>0) a
        # parcela correspondente fica None.
        snapshot_svc = SnapshotCustoService(self.session, self.tenant_id)

        custo_maquina = None
        custo_implemento = None
        if maquina_id:
            preco, _ = await snapshot_svc.capturar("MAQUINA", maquina_id, "hora")
            if preco and preco > 0:
                custo_maquina = float(preco)
        if implemento_id:
            preco, _ = await snapshot_svc.capturar("MAQUINA", implemento_id, "hora")
            if preco and preco > 0:
                custo_implemento = float(preco)

        if custo_maquina is not None and custo_implemento is not None:
            fonte_custo = "MAQUINA_E_IMPLEMENTO"
        elif custo_maquina is not None:
            fonte_custo = "SO_MAQUINA"
        elif custo_implemento is not None:
            fonte_custo = "SO_IMPLEMENTO"
        else:
            fonte_custo = "CUSTO_INCOMPLETO"
        return custo_maquina, custo_implemento, fonte_custo

    async def _montar_snapshot_maquinario(self, maquinario: PlanoOperacionalTarefaMaquinario) -> None:
        if maquinario.maquina_id:
            await self._validar_equipamento(maquinario.maquina_id)
        if maquinario.implemento_id:
            await self._validar_equipamento(maquinario.implemento_id)

        custo_maquina, custo_implemento, fonte_custo = await self._resolver_custo_maquinario(
            maquinario.maquina_id, maquinario.implemento_id
        )
        maquinario.custo_hora_maquina_snapshot = custo_maquina
        maquinario.custo_hora_implemento_snapshot = custo_implemento
        maquinario.fonte_custo = fonte_custo

        custo_hora_total = (custo_maquina or 0) + (custo_implemento or 0)
        if fonte_custo != "CUSTO_INCOMPLETO" and maquinario.horas_estimadas:
            maquinario.custo_total_estimado = round(custo_hora_total * float(maquinario.horas_estimadas), 2)
        else:
            maquinario.custo_total_estimado = None

    async def adicionar_maquinario(
        self, plano_id: uuid.UUID, item_id: uuid.UUID, dados: PlanoOperacionalTarefaMaquinarioCreate
    ) -> PlanoOperacionalTarefaMaquinario:
        plano, item = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano, item)
        if not dados.maquina_id and not dados.implemento_id:
            raise BusinessRuleError(
                "Informe ao menos uma máquina ou um implemento para adicionar necessidade de maquinário."
            )

        maquinario = PlanoOperacionalTarefaMaquinario(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            plano_operacional_tarefa_id=item_id,
            maquina_id=dados.maquina_id,
            implemento_id=dados.implemento_id,
            horas_estimadas=dados.horas_estimadas,
        )
        await self._montar_snapshot_maquinario(maquinario)
        self.session.add(maquinario)
        await self.session.flush()
        return maquinario

    async def _get_maquinario_or_fail(
        self, item_id: uuid.UUID, maquinario_id: uuid.UUID
    ) -> PlanoOperacionalTarefaMaquinario:
        stmt = select(PlanoOperacionalTarefaMaquinario).where(
            PlanoOperacionalTarefaMaquinario.id == maquinario_id,
            PlanoOperacionalTarefaMaquinario.plano_operacional_tarefa_id == item_id,
            PlanoOperacionalTarefaMaquinario.tenant_id == self.tenant_id,
        )
        maquinario = (await self.session.execute(stmt)).scalars().first()
        if not maquinario:
            raise EntityNotFoundError(f"Necessidade de maquinário {maquinario_id} não encontrada neste item.")
        return maquinario

    async def atualizar_maquinario(
        self,
        plano_id: uuid.UUID,
        item_id: uuid.UUID,
        maquinario_id: uuid.UUID,
        dados: PlanoOperacionalTarefaMaquinarioUpdate,
    ) -> PlanoOperacionalTarefaMaquinario:
        plano, item = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano, item)
        maquinario = await self._get_maquinario_or_fail(item_id, maquinario_id)

        dados_dict = dados.model_dump(exclude_unset=True)
        for campo, valor in dados_dict.items():
            setattr(maquinario, campo, valor)

        if not maquinario.maquina_id and not maquinario.implemento_id:
            raise BusinessRuleError(
                "A necessidade de maquinário precisa manter ao menos uma máquina ou um implemento."
            )

        await self._montar_snapshot_maquinario(maquinario)
        self.session.add(maquinario)
        await self.session.flush()
        return maquinario

    async def remover_maquinario(self, plano_id: uuid.UUID, item_id: uuid.UUID, maquinario_id: uuid.UUID) -> None:
        plano, item = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano, item)
        maquinario = await self._get_maquinario_or_fail(item_id, maquinario_id)
        # Hard delete seguro: só estimativa de planejamento (mesma justificativa
        # usada em remover_mao_obra).
        await self.session.delete(maquinario)
        await self.session.flush()

    async def listar_maquinario(
        self, plano_id: uuid.UUID, item_id: uuid.UUID
    ) -> list[PlanoOperacionalTarefaMaquinario]:
        await self._get_plano_e_item(plano_id, item_id)
        stmt = select(PlanoOperacionalTarefaMaquinario).where(
            PlanoOperacionalTarefaMaquinario.tenant_id == self.tenant_id,
            PlanoOperacionalTarefaMaquinario.plano_operacional_tarefa_id == item_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    # ------------------------------------------------------------------
    # Aplicação em lote de Receita de Aplicação (evita lançar insumo/mão de
    # obra um a um por tarefa quando várias tarefas do plano usam o mesmo
    # pacote — ex.: mesma pulverização em vários talhões).
    # ------------------------------------------------------------------

    async def aplicar_receita(
        self,
        plano_id: uuid.UUID,
        receita_id: uuid.UUID,
        plano_operacional_tarefa_ids: list[uuid.UUID],
    ) -> list[dict]:
        # Import local para evitar dependência circular entre os dois módulos
        # (receitas_aplicacao não depende de planejamento_operacional).
        from agricola.receitas_aplicacao.service import ReceitaAplicacaoService
        from agricola.tarefas.service import TarefaService

        receita_svc = ReceitaAplicacaoService(self.session, self.tenant_id, self.user_id)
        await receita_svc.get_or_fail(receita_id)  # valida existência + tenant
        insumos_receita = await receita_svc.listar_insumos(receita_id)
        mao_obra_receita = await receita_svc.listar_mao_obra(receita_id)

        resultados = []
        for item_id in plano_operacional_tarefa_ids:
            plano, item = await self._get_plano_e_item(plano_id, item_id)
            self._validar_plano_editavel_para_insumo(plano, item)

            tarefa = await self.session.get(SafraTarefa, item.safra_tarefa_id)
            area_ha = float(tarefa.area_ha) if tarefa and tarefa.area_ha else 0.0

            insumos_criados = 0
            for insumo_receita in insumos_receita:
                quantidade = float(insumo_receita.dose_ha) * area_ha
                if quantidade <= 0:
                    raise BusinessRuleError(
                        f"A tarefa {item_id} não tem área de talhão cadastrada — "
                        "não é possível calcular a quantidade a partir da dose/ha da receita."
                    )
                await self.adicionar_insumo(
                    plano_id, item_id,
                    PlanoOperacionalTarefaInsumoCreate(
                        produto_id=insumo_receita.produto_id,
                        deposito_id=insumo_receita.deposito_id,
                        dose_planejada=float(insumo_receita.dose_ha),
                        unidade_dose=insumo_receita.unidade_dose,
                        quantidade_planejada=quantidade,
                    ),
                )
                insumos_criados += 1

            mao_obra_criada = 0
            for mo in mao_obra_receita:
                await self.adicionar_mao_obra(
                    plano_id, item_id,
                    PlanoOperacionalTarefaMaoObraCreate(
                        tipo_servico_id=mo.tipo_servico_id,
                        funcao=mo.funcao,
                        quantidade_pessoas=mo.quantidade_pessoas,
                        horas_fixas=float(mo.horas_fixas),
                        horas_por_hectare=float(mo.horas_por_hectare),
                    ),
                )
                mao_obra_criada += 1

            # Ressincroniza o "Agronômico" (SafraTarefa.custo_estimado) com o
            # custo real dos produtos da receita — snapshot, mesmo padrão já
            # usado nos insumos (custo_unitario_snapshot). Antes deste ponto,
            # custo_estimado vinha só da estimativa de preço de mercado fixo em
            # analises_solo/service.py, sem relação com o preço real do tenant.
            insumos_item = await self.listar_insumos(plano_id, item_id)
            mao_obra_item = await self.listar_mao_obra(plano_id, item_id)
            custo_total_item = (
                sum(i.custo_total_estimado or 0 for i in insumos_item)
                + sum(m.custo_total_estimado or 0 for m in mao_obra_item)
            )
            tarefa_svc = TarefaService(self.session, self.tenant_id, self.user_id)
            await tarefa_svc.atualizar(item.safra_tarefa_id, TarefaUpdate(custo_estimado=custo_total_item))

            resultados.append({
                "plano_operacional_tarefa_id": item_id,
                "insumos_criados": insumos_criados,
                "mao_obra_criada": mao_obra_criada,
            })
        return resultados

    # ------------------------------------------------------------------
    # Geração de OS em lote — fecha o ciclo do plano: sem isto, aprovar/
    # reservar insumos em lote não tinha efeito nenhum na execução real
    # (o operador de campo nunca via a tarefa, ver TarefaCampo/PWA).
    # ------------------------------------------------------------------

    async def gerar_os_lote(self, plano_id: uuid.UUID, itens: list) -> list[dict]:
        from agricola.tarefas.service import TarefaService
        from agricola.tarefas.schemas import PlanejarOperacaoRequest, PlanejarInsumoRequest

        await self.get_or_fail(plano_id)  # valida existência + tenant
        tarefa_svc = TarefaService(self.session, self.tenant_id, self.user_id)

        resultados = []
        for item_input in itens:
            item_id = item_input.plano_operacional_tarefa_id
            try:
                item = await self._get_item_or_fail(plano_id, item_id)
                if item.status_planejamento != "PRONTA":
                    raise BusinessRuleError(
                        f"Item com status '{item.status_planejamento}' não está pronto para gerar OS "
                        "(insumos precisam estar totalmente reservados)."
                    )

                tarefa = await self.session.get(SafraTarefa, item.safra_tarefa_id)
                if not tarefa:
                    raise EntityNotFoundError(f"Tarefa {item.safra_tarefa_id} não encontrada.")
                area_ha = float(tarefa.area_ha) if tarefa.area_ha else 0.0

                insumos_item = await self.listar_insumos(plano_id, item_id)
                insumos_request = []
                for insumo in insumos_item:
                    dose_por_ha = float(insumo.dose_planejada) if insumo.dose_planejada else None
                    if not dose_por_ha and area_ha > 0:
                        dose_por_ha = float(insumo.quantidade_planejada) / area_ha
                    if not dose_por_ha:
                        raise BusinessRuleError(
                            f"Insumo {insumo.produto_id} sem dose/ha calculável (tarefa sem área definida) "
                            "— não é possível gerar a OS."
                        )
                    insumos_request.append(PlanejarInsumoRequest(
                        produto_id=insumo.produto_id,
                        dose_por_ha=dose_por_ha,
                        unidade=insumo.unidade_dose,
                    ))

                operacao = await tarefa_svc.gerar_operacao_planejada(
                    item.safra_tarefa_id,
                    PlanejarOperacaoRequest(
                        data_prevista=item_input.data_prevista,
                        operador_id=item_input.operador_id,
                        maquina_id=item_input.maquina_id,
                        implemento_id=item_input.implemento_id,
                        insumos=insumos_request,
                    ),
                )
                item.status_planejamento = "PROGRAMADA"
                self.session.add(item)
                await self.session.flush()
                await self.session.commit()

                resultados.append({
                    "plano_operacional_tarefa_id": item_id,
                    "sucesso": True,
                    "operacao_agricola_id": operacao.id,
                    "erro": None,
                })
            except (BusinessRuleError, EntityNotFoundError) as e:
                await self.session.rollback()
                resultados.append({
                    "plano_operacional_tarefa_id": item_id,
                    "sucesso": False,
                    "operacao_agricola_id": None,
                    "erro": str(e),
                })
        return resultados
