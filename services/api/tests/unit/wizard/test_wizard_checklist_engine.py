from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from wizard.checklist_engine import ChecklistEngine
from wizard.models import (
    ChecklistItemSeverity,
    ChecklistItemStatus,
    ImplantacaoChecklistItem,
    ImplantacaoOperacional,
)

pytestmark = pytest.mark.asyncio(loop_scope="function")

REPO_ROOT = Path(__file__).resolve().parents[5]


def _make_session() -> AsyncSession:
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_implantacao(
    *,
    escopo_modulos: dict[str, bool] | None = None,
    unidade_produtiva_id: uuid.UUID | None = None,
) -> ImplantacaoOperacional:
    return ImplantacaoOperacional(
        tenant_id=uuid.uuid4(),
        owner_usuario_id=uuid.uuid4(),
        status="IN_PROGRESS",
        etapa_atual="DIAGNOSTICO",
        unidade_produtiva_id=unidade_produtiva_id,
        escopo_modulos=escopo_modulos or {},
    )


def _make_item(codigo: str, *, obrigatorio: bool = True) -> ImplantacaoChecklistItem:
    return ImplantacaoChecklistItem(
        implantacao_id=uuid.uuid4(),
        codigo_item=codigo,
        descricao=codigo,
        obrigatorio=obrigatorio,
        status=ChecklistItemStatus.PENDENTE.value,
        severidade=ChecklistItemSeverity.CRITICO.value,
        evidencia_tipo="AUTOMATICA",
    )


async def test_unidade_produtiva_valida_automaticamente() -> None:
    session = _make_session()
    engine = ChecklistEngine(session)
    implantacao = _make_implantacao()
    item = _make_item("CHECK_UNIDADE_PRODUTIVA")
    unidade_id = uuid.uuid4()

    engine._find_unidade_produtiva = AsyncMock(  # type: ignore[method-assign]
        return_value=unidade_id
    )
    engine.implantacao_service.pendencia_service.buscar_pendencia_aberta_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.pendencia_service.resolver_pendencia_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.historico_service.registrar = AsyncMock()

    result = await engine.avaliar_item(implantacao, item)

    assert result.status == ChecklistItemStatus.ATENDIDO.value
    assert result.evidencia is not None
    assert result.evidencia.entidade == "Unidade Produtiva"
    assert result.evidencia.entidade_id == str(unidade_id)
    engine.implantacao_service.historico_service.registrar.assert_awaited_once()


async def test_unidade_produtiva_inexistente_abre_pendencia_critica() -> None:
    session = _make_session()
    engine = ChecklistEngine(session)
    implantacao = _make_implantacao()
    item = _make_item("CHECK_UNIDADE_PRODUTIVA")

    engine._find_unidade_produtiva = AsyncMock(return_value=None)  # type: ignore[method-assign]
    engine.implantacao_service.pendencia_service.buscar_pendencia_aberta_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.pendencia_service.criar_ou_manter_pendencia = AsyncMock(
        return_value=(MagicMock(), True)
    )
    engine.implantacao_service.historico_service.registrar = AsyncMock()

    result = await engine.avaliar_item(implantacao, item)

    assert result.status == ChecklistItemStatus.PENDENTE.value
    assert result.pendencia_severidade == "CRITICA"
    engine.implantacao_service.pendencia_service.criar_ou_manter_pendencia.assert_awaited_once()
    engine.implantacao_service.historico_service.registrar.assert_awaited_once()


async def test_area_rural_existente_valida_estrutura_territorial() -> None:
    session = _make_session()
    engine = ChecklistEngine(session)
    implantacao = _make_implantacao()
    item = _make_item("CHECK_ESTRUTURA_TERRITORIAL")

    engine._find_area_rural = AsyncMock(return_value=uuid.uuid4())  # type: ignore[method-assign]
    engine.implantacao_service.pendencia_service.buscar_pendencia_aberta_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.pendencia_service.resolver_pendencia_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.historico_service.registrar = AsyncMock()

    result = await engine.avaliar_item(implantacao, item)

    assert result.status == ChecklistItemStatus.ATENDIDO.value
    assert result.evidencia is not None
    assert result.evidencia.entidade == "Área Rural"


async def test_agricultura_sem_talhao_falha_com_pendencia_critica() -> None:
    session = _make_session()
    engine = ChecklistEngine(session)
    implantacao = _make_implantacao(escopo_modulos={"agricultura": True})
    item = _make_item("CHECK_AGRICULTURA_TALHAO")

    engine._find_area_by_tipo = AsyncMock(return_value=None)  # type: ignore[method-assign]
    engine.implantacao_service.pendencia_service.buscar_pendencia_aberta_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.pendencia_service.criar_ou_manter_pendencia = AsyncMock(
        return_value=(MagicMock(), True)
    )
    engine.implantacao_service.historico_service.registrar = AsyncMock()

    result = await engine.avaliar_item(implantacao, item)

    assert result.status == ChecklistItemStatus.FALHOU.value
    assert result.pendencia_severidade == "CRITICA"


async def test_pecuaria_sem_piquete_falha_com_pendencia_critica() -> None:
    session = _make_session()
    engine = ChecklistEngine(session)
    implantacao = _make_implantacao(escopo_modulos={"pecuaria": True})
    item = _make_item("CHECK_PECUARIA_PIQUETE")

    engine._find_area_by_tipo = AsyncMock(return_value=None)  # type: ignore[method-assign]
    engine.implantacao_service.pendencia_service.buscar_pendencia_aberta_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.pendencia_service.criar_ou_manter_pendencia = AsyncMock(
        return_value=(MagicMock(), True)
    )
    engine.implantacao_service.historico_service.registrar = AsyncMock()

    result = await engine.avaliar_item(implantacao, item)

    assert result.status == ChecklistItemStatus.FALHOU.value
    assert result.pendencia_severidade == "CRITICA"


async def test_estoque_sem_deposito_permanece_pendente() -> None:
    session = _make_session()
    engine = ChecklistEngine(session)
    implantacao = _make_implantacao(escopo_modulos={"estoque": True})
    item = _make_item("CHECK_ESTOQUE_DEPOSITO")

    engine._find_deposito = AsyncMock(return_value=None)  # type: ignore[method-assign]
    engine.implantacao_service.pendencia_service.buscar_pendencia_aberta_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.pendencia_service.criar_ou_manter_pendencia = AsyncMock(
        return_value=(MagicMock(), True)
    )
    engine.implantacao_service.historico_service.registrar = AsyncMock()

    result = await engine.avaliar_item(implantacao, item)

    assert result.status == ChecklistItemStatus.PENDENTE.value


async def test_financeiro_sem_plano_conta_permanece_pendente() -> None:
    session = _make_session()
    engine = ChecklistEngine(session)
    implantacao = _make_implantacao(escopo_modulos={"financeiro": True})
    item = _make_item("CHECK_FINANCEIRO_PLANO_CONTA")

    engine._find_plano_conta = AsyncMock(return_value=None)  # type: ignore[method-assign]
    engine.implantacao_service.pendencia_service.buscar_pendencia_aberta_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.pendencia_service.criar_ou_manter_pendencia = AsyncMock(
        return_value=(MagicMock(), True)
    )
    engine.implantacao_service.historico_service.registrar = AsyncMock()

    result = await engine.avaliar_item(implantacao, item)

    assert result.status == ChecklistItemStatus.PENDENTE.value


async def test_produto_inexistente_permanece_pendente() -> None:
    session = _make_session()
    engine = ChecklistEngine(session)
    implantacao = _make_implantacao(escopo_modulos={"agricultura": True})
    item = _make_item("CHECK_PRODUTO_CATALOGO")

    engine._find_produto = AsyncMock(return_value=None)  # type: ignore[method-assign]
    engine.implantacao_service.pendencia_service.buscar_pendencia_aberta_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.pendencia_service.criar_ou_manter_pendencia = AsyncMock(
        return_value=(MagicMock(), True)
    )
    engine.implantacao_service.historico_service.registrar = AsyncMock()

    result = await engine.avaliar_item(implantacao, item)

    assert result.status == ChecklistItemStatus.PENDENTE.value


async def test_equipamento_inexistente_permanece_pendente() -> None:
    session = _make_session()
    engine = ChecklistEngine(session)
    implantacao = _make_implantacao(escopo_modulos={"frota": True})
    item = _make_item("CHECK_EQUIPAMENTO_CADASTRO")

    engine._find_equipamento = AsyncMock(return_value=None)  # type: ignore[method-assign]
    engine.implantacao_service.pendencia_service.buscar_pendencia_aberta_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.pendencia_service.criar_ou_manter_pendencia = AsyncMock(
        return_value=(MagicMock(), True)
    )
    engine.implantacao_service.historico_service.registrar = AsyncMock()

    result = await engine.avaliar_item(implantacao, item)

    assert result.status == ChecklistItemStatus.PENDENTE.value


async def test_criacao_automatica_e_resolucao_automatica_de_pendencia() -> None:
    session = _make_session()
    engine = ChecklistEngine(session)
    implantacao = _make_implantacao()
    item = _make_item("CHECK_UNIDADE_PRODUTIVA")
    pendencia = MagicMock()

    engine._find_unidade_produtiva = AsyncMock(  # type: ignore[method-assign]
        side_effect=[None, uuid.uuid4()]
    )
    engine.implantacao_service.historico_service.registrar = AsyncMock()
    engine.implantacao_service.pendencia_service.buscar_pendencia_aberta_por_titulo = AsyncMock(
        side_effect=[None, pendencia]
    )
    engine.implantacao_service.pendencia_service.criar_ou_manter_pendencia = AsyncMock(
        return_value=(pendencia, True)
    )
    engine.implantacao_service.pendencia_service.resolver_pendencia_por_titulo = AsyncMock(
        return_value=pendencia
    )

    primeiro = await engine.avaliar_item(implantacao, item)
    segundo = await engine.avaliar_item(implantacao, item)

    assert primeiro.status == ChecklistItemStatus.PENDENTE.value
    assert segundo.status == ChecklistItemStatus.ATENDIDO.value
    eventos = [
        call.kwargs["evento"]
        for call in engine.implantacao_service.historico_service.registrar.await_args_list
    ]
    assert "CHECKLIST_ITEM_FAILED" in eventos
    assert "CHECKLIST_ITEM_RESOLVED" in eventos


async def test_execucao_idempotente_nao_duplica_historico_nem_pendencia() -> None:
    session = _make_session()
    engine = ChecklistEngine(session)
    implantacao = _make_implantacao()
    item = _make_item("CHECK_UNIDADE_PRODUTIVA")
    unidade_id = uuid.uuid4()
    item.status = ChecklistItemStatus.ATENDIDO.value
    item.evidencia_ref_id = str(unidade_id)
    item.evidencia_tipo = "AUTOMATICA"
    item.checked_by_usuario_id = implantacao.owner_usuario_id

    engine._find_unidade_produtiva = AsyncMock(  # type: ignore[method-assign]
        return_value=unidade_id
    )
    engine.implantacao_service.pendencia_service.buscar_pendencia_aberta_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.pendencia_service.resolver_pendencia_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.historico_service.registrar = AsyncMock()

    await engine.avaliar_item(implantacao, item)

    engine.implantacao_service.historico_service.registrar.assert_not_awaited()


async def test_avaliar_implantacao_recalcula_e_sincroniza_servicos() -> None:
    session = _make_session()
    engine = ChecklistEngine(session)
    implantacao = _make_implantacao()
    item = _make_item("CHECK_UNIDADE_PRODUTIVA")
    engine.implantacao_service.etapa_service.inicializar_etapas_canonicas = (
        AsyncMock(return_value=[])
    )
    engine.implantacao_service.etapa_service.listar_etapas = AsyncMock(return_value=[])
    engine.implantacao_service.checklist_service.criar_checklist_base_idempotente = (
        AsyncMock(return_value=[item])
    )
    engine.implantacao_service.checklist_service.listar_itens = AsyncMock(return_value=[item])
    engine.implantacao_service.pendencia_service.has_open_critical_blockers = (
        AsyncMock(return_value=False)
    )
    engine.implantacao_service.recalcular_progresso_basico = AsyncMock(return_value=0)
    engine._find_unidade_produtiva = AsyncMock(  # type: ignore[method-assign]
        return_value=uuid.uuid4()
    )
    engine.implantacao_service.pendencia_service.buscar_pendencia_aberta_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.pendencia_service.resolver_pendencia_por_titulo = (
        AsyncMock(return_value=None)
    )
    engine.implantacao_service.historico_service.registrar = AsyncMock()

    resultados = await engine.avaliar_implantacao(implantacao)

    assert len(resultados) == 1
    engine.implantacao_service.recalcular_progresso_basico.assert_awaited_once_with(implantacao.id)


async def test_checklist_engine_nao_importa_auth_billing_convites_ou_frontend() -> None:
    source = (
        REPO_ROOT / "services" / "api" / "wizard" / "checklist_engine.py"
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
