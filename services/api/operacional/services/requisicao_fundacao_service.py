"""Serviços da fundação 01C sem transição de workflow legado."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.operacoes.models import OperacaoAgricola
from agricola.operacoes.models import OperacaoExecucao
from agricola.planejamento_operacional.models import PlanoOperacionalTarefa
from agricola.safras.models import Safra
from agricola.tarefas.models import SafraTarefa
from campo.models import DispositivoCampo
from core.cadastros.pessoas.models import Pessoa
from core.exceptions import BusinessRuleError, EntityNotFoundError, TenantViolationError
from operacional.models.estoque import (
    Deposito,
    ItemRequisicao,
    LoteEstoque,
    RequisicaoItemEvento,
    RequisicaoMaterial,
)
from core.cadastros.produtos.models import Produto
from operacional.schemas.estoque import RequisicaoCreate, RequisicaoItemEventoCreate


class RequisicaoFundacaoService:
    """Valida relações estruturais sem executar entrega, consumo ou devolução."""

    @staticmethod
    async def validar_origem(
        session: AsyncSession,
        tenant_id: UUID,
        data: RequisicaoCreate,
    ) -> None:
        """Valida origem operacional e relações tenant-safe da requisição.

        Args:
            session: Sessão SQLAlchemy da transação corrente.
            tenant_id: Tenant autenticado da operação.
            data: Dados de criação da requisição.
        Raises:
            BusinessRuleError: Quando a origem é ausente, cruzada ou inconsistente.
        """
        rows = await _carregar_origem(session, tenant_id, data)
        _validar_existencia_origem(data, rows)
        _validar_consistencia_origem(data, rows)
        await RequisicaoFundacaoService.validar_itens(session, tenant_id, data)

    @staticmethod
    async def validar_itens(
        session: AsyncSession,
        tenant_id: UUID,
        data: RequisicaoCreate,
    ) -> None:
        """Valida produto e depósito sem aceitar referências de outro tenant."""
        for item in data.itens:
            produto = await session.execute(
                select(Produto.id).where(
                    Produto.id == item.produto_id,
                    (Produto.tenant_id == tenant_id) | Produto.tenant_id.is_(None),
                )
            )
            if produto.scalar_one_or_none() is None:
                raise TenantViolationError(
                    "Produto não pertence ao tenant atual.",
                    tenant_id=tenant_id,
                    resource="produto",
                )
            if item.deposito_id is not None:
                deposito = await session.execute(
                    select(Deposito.id).where(
                        Deposito.id == item.deposito_id,
                        Deposito.tenant_id == tenant_id,
                    )
                )
                if deposito.scalar_one_or_none() is None:
                    raise TenantViolationError(
                        "Depósito não pertence ao tenant atual.",
                        tenant_id=tenant_id,
                        resource="deposito",
                    )


async def _carregar_origem(
    session: AsyncSession,
    tenant_id: UUID,
    data: RequisicaoCreate,
) -> dict[str, object | None]:
    """Carrega somente entidades de origem pertencentes ao tenant."""
    return {
        "safra": await _get_tenant_row(session, Safra, tenant_id, data.safra_id),
        "tarefa": await _get_tenant_row(session, SafraTarefa, tenant_id, data.safra_tarefa_id),
        "plano": await _get_tenant_row(
            session, PlanoOperacionalTarefa, tenant_id, data.plano_operacional_tarefa_id
        ),
        "operacao": await _get_tenant_row(
            session, OperacaoAgricola, tenant_id, data.operacao_agricola_id
        ),
        "pessoa": await _get_tenant_row(session, Pessoa, tenant_id, data.responsavel_pessoa_id),
    }


async def _get_tenant_row(
    session: AsyncSession,
    model: type,
    tenant_id: UUID,
    row_id: UUID | None,
) -> object | None:
    """Busca uma origem por tenant e ID, sem fallback global."""
    if row_id is None:
        return None
    stmt = select(model).where(model.id == row_id, model.tenant_id == tenant_id)
    return (await session.execute(stmt)).scalars().first()


def _validar_existencia_origem(data: RequisicaoCreate, rows: dict[str, object | None]) -> None:
    """Rejeita IDs fornecidos que não foram encontrados no tenant atual."""
    fields = {
        "safra_id": "safra",
        "safra_tarefa_id": "tarefa",
        "plano_operacional_tarefa_id": "plano",
        "operacao_agricola_id": "operacao",
        "responsavel_pessoa_id": "pessoa",
    }
    for field, key in fields.items():
        if getattr(data, field) is not None and rows[key] is None:
            raise EntityNotFoundError(f"Origem {field} não encontrada no tenant atual.")


def _validar_consistencia_origem(data: RequisicaoCreate, rows: dict[str, object | None]) -> None:
    """Impede combinações de safra, tarefa, plano e operação incompatíveis."""
    safra, tarefa, plano, operacao = rows["safra"], rows["tarefa"], rows["plano"], rows["operacao"]
    if safra and tarefa and safra.id != tarefa.safra_id:
        raise BusinessRuleError("Safra e SafraTarefa não pertencem à mesma origem.")
    if tarefa and plano and tarefa.id != plano.safra_tarefa_id:
        raise BusinessRuleError("PlanoOperacionalTarefa e SafraTarefa são incompatíveis.")
    if operacao and tarefa and operacao.tarefa_id != tarefa.id:
        raise BusinessRuleError("Operação e SafraTarefa são incompatíveis.")
    if operacao and safra and operacao.safra_id != safra.id:
        raise BusinessRuleError("Operação e Safra são incompatíveis.")


class RequisicaoItemEventoService:
    """Registra fatos append-only e idempotentes por item."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def registrar(self, data: RequisicaoItemEventoCreate) -> RequisicaoItemEvento:
        """Registra ou retorna o mesmo fato idempotente.

        Args:
            data: Fato por item com chave de operação opcional.
        Return:
            Evento persistido e sua versão de requisição.
        Raises:
            BusinessRuleError: Quando a chave é reutilizada com outro payload.
            EntityNotFoundError: Quando requisição ou item não pertencem ao tenant.
        """
        existing = await self._find_existing(data.client_operation_id)
        if existing:
            self.validar_retentativa(existing, data)
            return existing
        req, item = await self._lock_context(data.item_id)
        # A segunda leitura ocorre depois do lock do agregado. Ela cobre o
        # retry concorrente que chegou enquanto o primeiro comando ainda estava
        # aguardando commit, sem depender de transformar a unique violation em
        # ACK no chamador.
        existing = await self._find_existing(data.client_operation_id)
        if existing:
            self.validar_retentativa(existing, data)
            return existing
        self._validate_item(req, item, data)
        self._validate_expected_version(req, data)
        await self._validate_references(req, item, data)
        event = self._build_event(req, item, data)
        req.version = event.versao_requisicao
        self.session.add(event)
        await self.session.flush()
        await self._enqueue_event(event, req.unidade_produtiva_id)
        return event

    async def _find_existing(self, client_operation_id: str | None) -> RequisicaoItemEvento | None:
        """Busca a chave idempotente dentro do tenant corrente."""
        if not client_operation_id:
            return None
        stmt = select(RequisicaoItemEvento).where(
            RequisicaoItemEvento.tenant_id == self.tenant_id,
            RequisicaoItemEvento.client_operation_id == client_operation_id,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def _lock_context(self, item_id: UUID) -> tuple[RequisicaoMaterial, ItemRequisicao]:
        """Carrega requisição e item sob lock e com escopo de tenant."""
        stmt = (
            select(RequisicaoMaterial, ItemRequisicao)
            .join(ItemRequisicao, ItemRequisicao.requisicao_id == RequisicaoMaterial.id)
            .where(
                RequisicaoMaterial.tenant_id == self.tenant_id,
                ItemRequisicao.tenant_id == self.tenant_id,
                ItemRequisicao.id == item_id,
            )
            .with_for_update()
        )
        row = (await self.session.execute(stmt)).first()
        if not row:
            raise EntityNotFoundError("Item de requisição não encontrado no tenant atual.")
        return row

    @staticmethod
    def _validate_item(
        req: RequisicaoMaterial,
        item: ItemRequisicao,
        data: RequisicaoItemEventoCreate,
    ) -> None:
        """Valida produto e origem explícita antes do append."""
        if data.produto_id and data.produto_id != item.produto_id:
            raise BusinessRuleError("Produto do evento não pertence ao item da requisição.")
        if data.operacao_agricola_id and data.operacao_agricola_id != req.operacao_agricola_id:
            raise BusinessRuleError("Operação do evento não pertence à requisição.")

    @staticmethod
    def _validate_expected_version(
        req: RequisicaoMaterial,
        data: RequisicaoItemEventoCreate,
    ) -> None:
        """Rejeita comando baseado em uma versão obsoleta, quando informada."""
        if (
            data.versao_requisicao_esperada is not None
            and data.versao_requisicao_esperada != req.version
        ):
            raise BusinessRuleError(
                "Versão da requisição obsoleta; recarregue o contexto antes de tentar novamente."
            )

    async def _validate_references(
        self,
        req: RequisicaoMaterial,
        item: ItemRequisicao,
        data: RequisicaoItemEventoCreate,
    ) -> None:
        """Valida snapshots opcionais usando o tenant como limite de segurança."""
        deposito_id = data.deposito_id or item.deposito_id
        if deposito_id is not None:
            deposito = await self.session.execute(
                select(Deposito.id).where(
                    Deposito.id == deposito_id,
                    Deposito.tenant_id == self.tenant_id,
                )
            )
            if deposito.scalar_one_or_none() is None:
                raise TenantViolationError(
                    "Depósito do item não pertence ao tenant atual.",
                    tenant_id=self.tenant_id,
                    resource="deposito",
                )

        if data.lote_id is not None:
            lote = await self.session.execute(
                select(LoteEstoque.id)
                .join(Deposito, Deposito.id == LoteEstoque.deposito_id)
                .where(
                    LoteEstoque.id == data.lote_id,
                    Deposito.tenant_id == self.tenant_id,
                )
            )
            if lote.scalar_one_or_none() is None:
                raise TenantViolationError(
                    "Lote não pertence ao tenant atual.",
                    tenant_id=self.tenant_id,
                    resource="lote",
                )

        if data.operacao_execucao_id is not None:
            execution = await self.session.execute(
                select(OperacaoExecucao).where(
                    OperacaoExecucao.id == data.operacao_execucao_id,
                    OperacaoExecucao.tenant_id == self.tenant_id,
                )
            )
            execution_row = execution.scalars().first()
            if execution_row is None:
                raise TenantViolationError(
                    "Execução não pertence ao tenant atual.",
                    tenant_id=self.tenant_id,
                    resource="operacao_execucao",
                )
            if req.operacao_agricola_id and execution_row.operacao_id != req.operacao_agricola_id:
                raise BusinessRuleError("Execução não pertence à operação da requisição.")

        for pessoa_id, resource in ((data.pessoa_operacional_id, "pessoa_operacional"),):
            if pessoa_id is not None:
                pessoa = await self.session.execute(
                    select(Pessoa.id).where(
                        Pessoa.id == pessoa_id,
                        Pessoa.tenant_id == self.tenant_id,
                    )
                )
                if pessoa.scalar_one_or_none() is None:
                    raise TenantViolationError(
                        "Pessoa operacional não pertence ao tenant atual.",
                        tenant_id=self.tenant_id,
                        resource=resource,
                    )

        if data.dispositivo_id is not None:
            dispositivo = await self.session.execute(
                select(DispositivoCampo.id).where(
                    DispositivoCampo.id == data.dispositivo_id,
                    DispositivoCampo.tenant_id == self.tenant_id,
                )
            )
            if dispositivo.scalar_one_or_none() is None:
                raise TenantViolationError(
                    "Dispositivo não pertence ao tenant atual.",
                    tenant_id=self.tenant_id,
                    resource="dispositivo",
                )

    def _build_event(
        self,
        req: RequisicaoMaterial,
        item: ItemRequisicao,
        data: RequisicaoItemEventoCreate,
    ) -> RequisicaoItemEvento:
        """Materializa o evento com snapshot do item e versão seguinte."""
        return RequisicaoItemEvento(
            tenant_id=self.tenant_id,
            requisicao_id=req.id,
            item_requisicao_id=item.id,
            tipo_evento=data.tipo_evento.value,
            quantidade=data.quantidade,
            unidade=data.unidade,
            produto_id=data.produto_id or item.produto_id,
            lote_id=data.lote_id,
            deposito_id=data.deposito_id or item.deposito_id,
            operacao_agricola_id=data.operacao_agricola_id or req.operacao_agricola_id,
            operacao_execucao_id=data.operacao_execucao_id,
            usuario_id=data.usuario_id,
            pessoa_operacional_id=data.pessoa_operacional_id or req.responsavel_pessoa_id,
            dispositivo_id=data.dispositivo_id,
            ocorrido_em_dispositivo=data.ocorrido_em_dispositivo,
            motivo=data.motivo,
            versao_requisicao=req.version + 1,
            correlation_id=data.correlation_id,
            causation_id=data.causation_id,
            client_operation_id=data.client_operation_id,
            provenance=data.provenance,
        )

    async def _enqueue_event(self, event: RequisicaoItemEvento, unidade_id: UUID) -> None:
        """Enfileira um único evento de fundação na mesma transação."""
        from events import DomainEvent, DomainEventOutboxService

        domain_event = DomainEvent(
            tenant_id=self.tenant_id,
            unidade_produtiva_id=unidade_id,
            domain="operacional",
            event_type="operational.material_request.item_event_recorded",
            source_type="RequisicaoItemEvento",
            entity_type="RequisicaoItemEvento",
            entity_id=event.id,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            metadata={
                "item_event_type": event.tipo_evento,
                "requisicao_id": str(event.requisicao_id),
                "item_requisicao_id": str(event.item_requisicao_id),
                "client_operation_id": event.client_operation_id,
            },
        )
        await DomainEventOutboxService(self.session, self.tenant_id).enqueue(
            domain_event, commit=False
        )

    @staticmethod
    def validar_retentativa(
        existing: RequisicaoItemEvento,
        data: RequisicaoItemEventoCreate,
    ) -> None:
        """Garante que retry da chave seja exatamente o mesmo fato.

        Args:
            existing: Evento já persistido com a chave do cliente.
            data: Novo payload recebido no retry.
        Return:
            None quando o payload é idêntico.
        Raises:
            BusinessRuleError: Quando a chave é reutilizada para outro fato.
        """
        same_fact = (
            existing.item_requisicao_id == data.item_id
            and existing.tipo_evento == data.tipo_evento.value
            and Decimal(str(existing.quantidade)) == data.quantidade
            and existing.unidade == data.unidade
        )
        if not same_fact:
            raise BusinessRuleError("client_operation_id já identifica outro fato.")
