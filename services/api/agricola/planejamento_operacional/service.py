import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base_service import BaseService
from core.exceptions import BusinessRuleError, EntityNotFoundError
from agricola.planejamento_operacional.models import PlanoOperacional, PlanoOperacionalTarefa
from agricola.planejamento_operacional.schemas import (
    PlanoOperacionalCreate,
    PlanoOperacionalUpdate,
    PlanoOperacionalTarefaCreate,
    PlanoOperacionalTarefaUpdate,
)
from agricola.safras.models import Safra
from agricola.tarefas.models import SafraTarefa

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
