from __future__ import annotations

import uuid
from datetime import timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from wizard.models import (
    ChecklistItemSeverity,
    ChecklistItemStatus,
    ImplantacaoChecklistItem,
    ImplantacaoEtapa,
    ImplantacaoOperacional,
    ImplantacaoPendencia,
    WizardEtapaStatus,
    WizardStatus,
)
from wizard.services import CHECKLIST_DEFINITIONS, STAGE_DEFINITIONS, ImplantacaoService

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python < 3.11 compatibility
    UTC = timezone.utc  # noqa: UP017


pytestmark = pytest.mark.asyncio(loop_scope="function")

REPO_ROOT = Path(__file__).resolve().parents[5]


def _make_session() -> AsyncSession:
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    return session


def _make_implantacao(
    status: str = "NOT_STARTED",
    *,
    unidade_produtiva_id: uuid.UUID | None = None,
) -> ImplantacaoOperacional:
    return ImplantacaoOperacional(
        tenant_id=uuid.uuid4(),
        owner_usuario_id=uuid.uuid4(),
        status=status,
        etapa_atual="DIAGNOSTICO",
        unidade_produtiva_id=unidade_produtiva_id,
    )


def _make_etapa(
    codigo: str,
    *,
    obrigatoria: bool = True,
    ordem: int = 1,
    percentual_peso: int = 10,
) -> ImplantacaoEtapa:
    return ImplantacaoEtapa(
        implantacao_id=uuid.uuid4(),
        codigo_etapa=codigo,
        nome=codigo.title(),
        obrigatoria=obrigatoria,
        ordem=ordem,
        percentual_peso=percentual_peso,
        status=WizardEtapaStatus.NOT_STARTED.value,
    )


def _make_checklist_item(
    codigo: str,
    *,
    obrigatorio: bool = True,
) -> ImplantacaoChecklistItem:
    return ImplantacaoChecklistItem(
        implantacao_id=uuid.uuid4(),
        codigo_item=codigo,
        descricao=codigo,
        obrigatorio=obrigatorio,
        status=ChecklistItemStatus.PENDENTE.value,
        severidade=ChecklistItemSeverity.CRITICO.value,
    )


async def test_criacao_idempotente_de_implantacao_ativa() -> None:
    session = _make_session()
    service = ImplantacaoService(session)
    tenant_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    active: list[ImplantacaoOperacional | None] = [None]

    async def fake_get_active(_: uuid.UUID) -> ImplantacaoOperacional | None:
        return active[0]

    service.get_active_implantacao = fake_get_active  # type: ignore[method-assign]
    service.historico_service.registrar = AsyncMock()
    service.etapa_service.inicializar_etapas_canonicas = AsyncMock(return_value=[])
    service.etapa_service.listar_etapas = AsyncMock(return_value=[])
    service.checklist_service.criar_checklist_base_idempotente = AsyncMock(return_value=[])
    service.recalcular_progresso_basico = AsyncMock(return_value=0)

    primeira = await service.create_or_get_active(
        tenant_id=tenant_id,
        owner_usuario_id=owner_id,
    )
    active[0] = primeira
    segunda = await service.create_or_get_active(
        tenant_id=tenant_id,
        owner_usuario_id=owner_id,
    )

    assert primeira is segunda
    assert session.add.call_count == 1
    service.historico_service.registrar.assert_awaited_once()


async def test_inicializacao_idempotente_de_etapas() -> None:
    session = _make_session()
    service = ImplantacaoService(session)
    implantacao = _make_implantacao()
    etapas_canonicas = [
        _make_etapa(
            definition.codigo,
            obrigatoria=definition.obrigatoria,
            ordem=definition.ordem,
            percentual_peso=definition.percentual_peso,
        )
        for definition in STAGE_DEFINITIONS
    ]
    service.etapa_service.listar_etapas = AsyncMock(
        side_effect=[[], etapas_canonicas, etapas_canonicas, etapas_canonicas]
    )

    primeira = await service.etapa_service.inicializar_etapas_canonicas(implantacao)
    segunda = await service.etapa_service.inicializar_etapas_canonicas(implantacao)

    assert len(primeira) == len(STAGE_DEFINITIONS)
    assert len(segunda) == len(STAGE_DEFINITIONS)
    assert session.add.call_count == len(STAGE_DEFINITIONS)


async def test_inicializacao_idempotente_do_checklist() -> None:
    session = _make_session()
    service = ImplantacaoService(session)
    implantacao = _make_implantacao()
    etapas = [
        _make_etapa(definition.codigo, obrigatoria=definition.obrigatoria, ordem=definition.ordem)
        for definition in STAGE_DEFINITIONS
    ]
    itens = [
        _make_checklist_item(definition.codigo, obrigatorio=definition.obrigatorio)
        for definition in CHECKLIST_DEFINITIONS
    ]
    service.checklist_service.listar_itens = AsyncMock(
        side_effect=[[], itens, itens, itens]
    )

    primeira = await service.checklist_service.criar_checklist_base_idempotente(
        implantacao,
        etapas,
    )
    segunda = await service.checklist_service.criar_checklist_base_idempotente(
        implantacao,
        etapas,
    )

    assert len(primeira) == len(CHECKLIST_DEFINITIONS)
    assert len(segunda) == len(CHECKLIST_DEFINITIONS)
    assert session.add.call_count == len(CHECKLIST_DEFINITIONS)


async def test_etapa_equipe_permanece_opcional() -> None:
    equipe = next(definition for definition in STAGE_DEFINITIONS if definition.codigo == "EQUIPE")
    assert equipe.obrigatoria is False


async def test_nao_e_possivel_pular_etapa_obrigatoria_sem_regra() -> None:
    session = _make_session()
    service = ImplantacaoService(session)
    implantacao = _make_implantacao()
    etapa = _make_etapa("DIAGNOSTICO", obrigatoria=True)
    service.etapa_service._buscar_etapa = AsyncMock(return_value=etapa)

    with pytest.raises(Exception, match="etapa obrigatória"):
        await service.etapa_service.pular_etapa(implantacao, "DIAGNOSTICO")


async def test_item_obrigatorio_de_checklist_exige_evidencia() -> None:
    session = _make_session()
    service = ImplantacaoService(session)
    item = _make_checklist_item("CHECK_UNIDADE_PRODUTIVA", obrigatorio=True)
    service.checklist_service._buscar_item = AsyncMock(return_value=item)

    with pytest.raises(Exception, match="exige evidência"):
        await service.checklist_service.marcar_item_atendido(
            item.implantacao_id,
            item.codigo_item,
            checked_by_usuario_id=uuid.uuid4(),
            evidencia_ref_id=None,
        )


async def test_listar_itens_recupera_uuid_vazio_legado() -> None:
    session = _make_session()
    service = ImplantacaoService(session)
    item = _make_checklist_item("CHECK_UNIDADE_PRODUTIVA")
    db_error = DBAPIError(
        "SELECT wizard_implantacoes_checklist_itens",
        None,
        Exception('invalid input syntax for type uuid: ""'),
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [item]
    session.execute = AsyncMock(side_effect=[db_error, result])
    service.checklist_service._sanitize_legacy_nullable_uuid_columns = AsyncMock()  # type: ignore[method-assign]

    itens = await service.checklist_service.listar_itens(item.implantacao_id)

    assert itens == [item]
    service.checklist_service._sanitize_legacy_nullable_uuid_columns.assert_awaited_once()  # type: ignore[attr-defined]
    session.rollback.assert_awaited_once()
    assert session.execute.await_count == 2


async def test_listar_pendencias_recupera_uuid_vazio_legado() -> None:
    session = _make_session()
    service = ImplantacaoService(session)
    pendencia = ImplantacaoPendencia(
        implantacao_id=uuid.uuid4(),
        tipo="BLOQUEIO",
        severidade="CRITICA",
        status="ABERTA",
        titulo="WIZARD::CHECK_UNIDADE_PRODUTIVA",
        descricao="Pendência crítica",
    )
    db_error = DBAPIError(
        "SELECT wizard_implantacoes_pendencias",
        None,
        Exception('invalid input syntax for type uuid: ""'),
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [pendencia]
    session.execute = AsyncMock(side_effect=[db_error, result])
    service.pendencia_service.session = session  # explicit for clarity
    original_sanitize = service.pendencia_service.listar_pendencias.__globals__[
        "sanitize_legacy_wizard_nullable_uuid_columns"
    ]
    service.pendencia_service.listar_pendencias.__globals__[
        "sanitize_legacy_wizard_nullable_uuid_columns"
    ] = AsyncMock()

    itens = await service.pendencia_service.listar_pendencias(pendencia.implantacao_id)

    assert itens == [pendencia]
    session.rollback.assert_awaited_once()
    assert session.execute.await_count == 2
    service.pendencia_service.listar_pendencias.__globals__[
        "sanitize_legacy_wizard_nullable_uuid_columns"
    ].assert_awaited_once_with(session)
    service.pendencia_service.listar_pendencias.__globals__[
        "sanitize_legacy_wizard_nullable_uuid_columns"
    ] = original_sanitize


async def test_checklist_minimo_falso_bloqueia_ready_for_go_live() -> None:
    session = _make_session()
    service = ImplantacaoService(session)
    implantacao = _make_implantacao(
        "IN_PROGRESS",
        unidade_produtiva_id=uuid.uuid4(),
    )
    service.checklist_service.minimum_checklist_satisfied = AsyncMock(return_value=False)
    service.pendencia_service.has_open_critical_blockers = AsyncMock(return_value=False)

    with pytest.raises(Exception, match="checklist mínimo satisfeito"):
        await service.aplicar_transicao_estado(
            implantacao,
            WizardStatus.READY_FOR_GO_LIVE.value,
            ator_usuario_id=uuid.uuid4(),
        )


async def test_pendencia_critica_aberta_bloqueia_ready_for_go_live() -> None:
    session = _make_session()
    service = ImplantacaoService(session)
    implantacao = _make_implantacao(
        "IN_PROGRESS",
        unidade_produtiva_id=uuid.uuid4(),
    )
    service.checklist_service.minimum_checklist_satisfied = AsyncMock(return_value=True)
    service.pendencia_service.has_open_critical_blockers = AsyncMock(return_value=True)

    with pytest.raises(Exception, match="pendência crítica aberta"):
        await service.aplicar_transicao_estado(
            implantacao,
            WizardStatus.READY_FOR_GO_LIVE.value,
            ator_usuario_id=uuid.uuid4(),
        )


async def test_transicao_valida_persiste_historico() -> None:
    session = _make_session()
    service = ImplantacaoService(session)
    implantacao = _make_implantacao()
    service.checklist_service.minimum_checklist_satisfied = AsyncMock(return_value=True)
    service.pendencia_service.has_open_critical_blockers = AsyncMock(return_value=False)
    service.historico_service.registrar_transicao = AsyncMock()
    service.recalcular_progresso_basico = AsyncMock(return_value=0)

    await service.aplicar_transicao_estado(
        implantacao,
        WizardStatus.IN_PROGRESS.value,
        ator_usuario_id=uuid.uuid4(),
        payload_snapshot={"origem": "teste"},
    )

    assert implantacao.status == WizardStatus.IN_PROGRESS.value
    service.historico_service.registrar_transicao.assert_awaited_once()
    payload = service.historico_service.registrar_transicao.await_args.args[1]
    assert payload["status_novo"] == WizardStatus.IN_PROGRESS.value


async def test_historico_nao_e_alterado_apenas_acrescentado() -> None:
    session = _make_session()
    service = ImplantacaoService(session)
    implantacao = _make_implantacao()
    service.checklist_service.minimum_checklist_satisfied = AsyncMock(return_value=True)
    service.pendencia_service.has_open_critical_blockers = AsyncMock(return_value=False)
    service.historico_service.registrar_transicao = AsyncMock()
    service.recalcular_progresso_basico = AsyncMock(return_value=0)

    await service.aplicar_transicao_estado(
        implantacao,
        WizardStatus.IN_PROGRESS.value,
        ator_usuario_id=uuid.uuid4(),
    )
    implantacao.unidade_produtiva_id = uuid.uuid4()
    await service.aplicar_transicao_estado(
        implantacao,
        WizardStatus.READY_FOR_GO_LIVE.value,
        ator_usuario_id=uuid.uuid4(),
    )

    assert service.historico_service.registrar_transicao.await_count == 2
    session.delete.assert_not_called()


async def test_blocked_so_desbloqueia_para_in_progress() -> None:
    session = _make_session()
    service = ImplantacaoService(session)
    implantacao = _make_implantacao(
        "BLOCKED",
        unidade_produtiva_id=uuid.uuid4(),
    )
    service.checklist_service.minimum_checklist_satisfied = AsyncMock(return_value=True)
    service.pendencia_service.has_open_critical_blockers = AsyncMock(return_value=False)

    with pytest.raises(Exception, match="não permitida"):
        await service.aplicar_transicao_estado(
            implantacao,
            WizardStatus.READY_FOR_GO_LIVE.value,
            ator_usuario_id=uuid.uuid4(),
        )

    service.historico_service.registrar_transicao = AsyncMock()
    service.recalcular_progresso_basico = AsyncMock(return_value=0)
    await service.desbloquear_implantacao(implantacao, ator_usuario_id=uuid.uuid4())
    assert implantacao.status == WizardStatus.IN_PROGRESS.value


async def test_go_live_exige_unidade_produtiva() -> None:
    session = _make_session()
    service = ImplantacaoService(session)
    implantacao = _make_implantacao("IN_PROGRESS")
    service.checklist_service.minimum_checklist_satisfied = AsyncMock(return_value=True)
    service.pendencia_service.has_open_critical_blockers = AsyncMock(return_value=False)

    with pytest.raises(Exception, match="exige unidade_produtiva_id"):
        await service.aplicar_transicao_estado(
            implantacao,
            WizardStatus.READY_FOR_GO_LIVE.value,
            ator_usuario_id=uuid.uuid4(),
        )


async def test_recalculo_basico_de_progresso() -> None:
    session = _make_session()
    service = ImplantacaoService(session)
    implantacao = _make_implantacao()
    etapas = [
        ImplantacaoEtapa(
            implantacao_id=implantacao.id,
            codigo_etapa="DIAGNOSTICO",
            nome="Diagnóstico",
            obrigatoria=True,
            ordem=1,
            percentual_peso=10,
            status=WizardEtapaStatus.COMPLETED.value,
        ),
        ImplantacaoEtapa(
            implantacao_id=implantacao.id,
            codigo_etapa="UNIDADE_PRODUTIVA",
            nome="Unidade",
            obrigatoria=True,
            ordem=2,
            percentual_peso=15,
            status=WizardEtapaStatus.NOT_STARTED.value,
        ),
    ]
    service.etapa_service.listar_etapas = AsyncMock(return_value=etapas)
    service.checklist_service.minimum_checklist_satisfied = AsyncMock(return_value=False)

    progresso = await service.recalcular_progresso_basico(implantacao)

    assert progresso == 40
    assert implantacao.percentual_progresso == 40
    assert implantacao.checklist_minimo_percentual == 0


async def test_services_nao_importam_auth_billing_convites_ou_frontend() -> None:
    source = (
        REPO_ROOT / "services" / "api" / "wizard" / "services.py"
    ).read_text(encoding="utf-8")

    forbidden_imports = [
        "from core.models.auth",
        "from core.models.billing",
        "AssinaturaTenant",
        "ConviteAcesso",
        "TenantUsuario",
        "from fastapi",
        "APIRouter",
        "apps/web",
        "apps/campo",
    ]

    for forbidden in forbidden_imports:
        assert forbidden not in source
