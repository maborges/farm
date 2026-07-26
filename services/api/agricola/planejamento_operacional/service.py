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
)
from agricola.safras.models import Safra
from agricola.tarefas.models import SafraTarefa, SafraTarefaNecessidade
from core.cadastros.produtos.models import Produto
from core.cadastros.tipos_servico.models import TipoServico
from rh.models import ColaboradorRH
from operacional.models.estoque import SaldoEstoque, Deposito, ReservaEstoque
from operacional.services.estoque_service import EstoqueService
from operacional.schemas.estoque import ReservaCreate
from operacional.models.compras import SolicitacaoCompra
from operacional.services.compras_service import ComprasService
from operacional.schemas.compras import SolicitacaoCompraCreate, SolicitacaoItemCreate

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

    def _validar_plano_editavel_para_insumo(self, plano: PlanoOperacional) -> None:
        if plano.status in PLANO_STATUS_FECHADO_PARA_SIMULACAO:
            raise BusinessRuleError(
                f"Plano com status '{plano.status}' não aceita mais simulação/edição de insumos."
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

    def _resolver_custo_produto(self, produto: Produto) -> tuple[float | None, str]:
        # Nunca inventa valor: sem preco_medio confiável (>0), sinaliza
        # CUSTO_INCOMPLETO em vez de gravar um custo fictício (ver relatório §7).
        if produto.preco_medio and produto.preco_medio > 0:
            return float(produto.preco_medio), "PRODUTO_PRECO_MEDIO"
        return None, "CUSTO_INCOMPLETO"

    async def _montar_snapshot(self, insumo: PlanoOperacionalTarefaInsumo) -> None:
        produto = await self._validar_produto(insumo.produto_id)
        saldo_fisico, saldo_reservado = await self._calcular_disponibilidade(insumo.produto_id, insumo.deposito_id)
        saldo_disponivel = saldo_fisico - saldo_reservado

        insumo.quantidade_disponivel_snapshot = saldo_disponivel
        insumo.quantidade_reservada = saldo_reservado
        insumo.quantidade_faltante = max(0.0, float(insumo.quantidade_planejada) - saldo_disponivel)

        custo_unitario, fonte_custo = self._resolver_custo_produto(produto)
        insumo.custo_unitario_snapshot = custo_unitario
        insumo.custo_total_estimado = (
            round(custo_unitario * float(insumo.quantidade_planejada), 2) if custo_unitario is not None else None
        )
        insumo.fonte_custo = fonte_custo

    async def adicionar_insumo(
        self, plano_id: uuid.UUID, item_id: uuid.UUID, dados: PlanoOperacionalTarefaInsumoCreate
    ) -> PlanoOperacionalTarefaInsumo:
        plano, item = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano)
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
        plano, _ = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano)
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
        plano, _ = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano)
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
        plano, _ = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano)
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
        self._validar_plano_editavel_para_insumo(plano)
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
        self._validar_plano_editavel_para_insumo(plano)
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
        await self._get_plano_e_item(plano_id, item_id)
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

    def _resolver_custo_hora(
        self, tipo_servico: TipoServico, colaborador: ColaboradorRH | None
    ) -> tuple[float | None, str]:
        # Prioriza o custo real da pessoa alocada; cai para a referência do
        # tipo de serviço só quando não há pessoa definida ainda. Nunca inventa
        # valor: sem nenhuma fonte confiável (>0), sinaliza CUSTO_INCOMPLETO.
        if colaborador:
            if colaborador.valor_hora and colaborador.valor_hora > 0:
                return float(colaborador.valor_hora), "PESSOA_VALOR_HORA"
            if colaborador.valor_diaria and colaborador.valor_diaria > 0:
                return float(colaborador.valor_diaria) / 8.0, "PESSOA_VALOR_HORA"
        if tipo_servico.custo_referencia and tipo_servico.custo_referencia > 0:
            return float(tipo_servico.custo_referencia), "TIPO_SERVICO_CUSTO_REFERENCIA"
        return None, "CUSTO_INCOMPLETO"

    async def _montar_snapshot_mao_obra(self, mao_obra: PlanoOperacionalTarefaMaoObra) -> None:
        tipo_servico = await self._validar_tipo_servico(mao_obra.tipo_servico_id)

        colaborador = None
        if mao_obra.pessoa_id:
            stmt = select(ColaboradorRH).where(
                ColaboradorRH.tenant_id == self.tenant_id,
                ColaboradorRH.pessoa_id == mao_obra.pessoa_id,
            )
            colaborador = (await self.session.execute(stmt)).scalars().first()

        custo_hora, fonte_custo = self._resolver_custo_hora(tipo_servico, colaborador)
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
        self._validar_plano_editavel_para_insumo(plano)
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
        plano, _ = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano)
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
        plano, _ = await self._get_plano_e_item(plano_id, item_id)
        self._validar_plano_editavel_para_insumo(plano)
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
