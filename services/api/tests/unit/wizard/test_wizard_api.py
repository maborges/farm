from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

import wizard.router as wizard_router_module
from core.exceptions import BusinessRuleError
from wizard.models import (
    ChecklistItemSeverity,
    ChecklistItemStatus,
    ImplantacaoChecklistItem,
    ImplantacaoEtapa,
    ImplantacaoOperacional,
    ImplantacaoPendencia,
    PendenciaSeverity,
    PendenciaStatus,
    PendenciaTipo,
    WizardEtapaStatus,
    WizardStatus,
)

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python < 3.11 compatibility
    UTC = timezone.utc  # noqa: UP017


API_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = Path(__file__).resolve().parents[5]


def _make_session() -> AsyncSession:
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


def _make_implantacao(
    status: str = WizardStatus.IN_PROGRESS.value,
    *,
    unidade_produtiva_id: uuid.UUID | None = None,
) -> ImplantacaoOperacional:
    return ImplantacaoOperacional(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        owner_usuario_id=uuid.uuid4(),
        status=status,
        etapa_atual="DIAGNOSTICO",
        percentual_progresso=35,
        checklist_minimo_percentual=0,
        unidade_produtiva_id=unidade_produtiva_id,
    )


def _make_etapa(codigo: str, ordem: int) -> ImplantacaoEtapa:
    now = datetime.now(UTC)
    return ImplantacaoEtapa(
        id=uuid.uuid4(),
        implantacao_id=uuid.uuid4(),
        codigo_etapa=codigo,
        nome=codigo.title(),
        status=WizardEtapaStatus.NOT_STARTED.value,
        obrigatoria=True,
        ordem=ordem,
        percentual_peso=10,
        created_at=now,
        updated_at=now,
    )


def _make_item(codigo: str) -> ImplantacaoChecklistItem:
    now = datetime.now(UTC)
    return ImplantacaoChecklistItem(
        id=uuid.uuid4(),
        implantacao_id=uuid.uuid4(),
        codigo_item=codigo,
        descricao=codigo,
        obrigatorio=True,
        status=ChecklistItemStatus.PENDENTE.value,
        severidade=ChecklistItemSeverity.CRITICO.value,
        evidencia_tipo="AUTOMATICA",
        created_at=now,
        updated_at=now,
    )


def _make_pendencia(
    status: str = PendenciaStatus.ABERTA.value,
    *,
    severidade: str = PendenciaSeverity.CRITICA.value,
) -> ImplantacaoPendencia:
    now = datetime.now(UTC)
    return ImplantacaoPendencia(
        id=uuid.uuid4(),
        implantacao_id=uuid.uuid4(),
        tipo=PendenciaTipo.BLOQUEIO.value,
        severidade=severidade,
        status=status,
        titulo="Pendencia",
        descricao="Pendencia critica",
        created_at=now,
        updated_at=now,
    )


def _build_service(
    implantacao: ImplantacaoOperacional,
    *,
    etapas: list[ImplantacaoEtapa] | None = None,
    itens: list[ImplantacaoChecklistItem] | None = None,
    pendencias: list[ImplantacaoPendencia] | None = None,
    checklist_minimo_satisfeito: bool = True,
):
    service = MagicMock()
    service.retomar_implantacao = AsyncMock(return_value=implantacao)
    service.create_or_get_active = AsyncMock(return_value=implantacao)
    service.aplicar_transicao_estado = AsyncMock(return_value=implantacao)
    service.etapa_service = MagicMock()
    service.etapa_service.listar_etapas = AsyncMock(return_value=etapas or [])
    service.checklist_service = MagicMock()
    service.checklist_service.listar_itens = AsyncMock(return_value=itens or [])
    service.checklist_service.minimum_checklist_satisfied = AsyncMock(
        return_value=checklist_minimo_satisfeito
    )
    service.pendencia_service = MagicMock()
    service.pendencia_service.listar_pendencias = AsyncMock(
        return_value=pendencias or []
    )
    return service


def _build_client(session: AsyncSession | None = None) -> tuple[TestClient, AsyncSession]:
    app = FastAPI()
    app.include_router(wizard_router_module.router, prefix="/api/v1")

    @app.exception_handler(BusinessRuleError)
    async def _business_rule_handler(_, exc: BusinessRuleError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    session = session or _make_session()
    tenant_id = uuid.uuid4()
    current_user = SimpleNamespace(id=uuid.uuid4())

    app.dependency_overrides[wizard_router_module.get_session] = lambda: session
    app.dependency_overrides[wizard_router_module.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[wizard_router_module.get_current_user] = lambda: current_user
    return TestClient(app), session


def test_iniciar_wizard_cria_implantacao_e_transiciona_para_in_progress() -> None:
    implantacao = _make_implantacao(WizardStatus.NOT_STARTED.value)
    service = _build_service(implantacao)
    engine = MagicMock()
    engine.avaliar_implantacao = AsyncMock(return_value=[])

    async def _apply_transition(*args, **kwargs):
        implantacao.status = kwargs["novo_status"] if "novo_status" in kwargs else args[1]
        return implantacao

    service.aplicar_transicao_estado = AsyncMock(side_effect=_apply_transition)

    client, session = _build_client()
    with (
        patch("wizard.router.ImplantacaoService", return_value=service),
        patch("wizard.router.ChecklistEngine", return_value=engine),
    ):
        response = client.post("/api/v1/wizard/iniciar", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == WizardStatus.IN_PROGRESS.value
    assert body["implantacao_id"] == str(implantacao.id)
    service.create_or_get_active.assert_awaited_once()
    engine.avaliar_implantacao.assert_awaited_once()
    session.commit.assert_awaited_once()


def test_iniciar_wizard_duas_vezes_retorna_mesma_implantacao_ativa() -> None:
    implantacao = _make_implantacao(WizardStatus.IN_PROGRESS.value)
    service = _build_service(implantacao)
    engine = MagicMock()
    engine.avaliar_implantacao = AsyncMock(return_value=[])

    client, _ = _build_client()
    with (
        patch("wizard.router.ImplantacaoService", return_value=service),
        patch("wizard.router.ChecklistEngine", return_value=engine),
    ):
        first = client.post("/api/v1/wizard/iniciar", json={})
        second = client.post("/api/v1/wizard/iniciar", json={})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["implantacao_id"] == second.json()["implantacao_id"]
    assert service.create_or_get_active.await_count == 2


def test_status_retorna_resumo_da_implantacao_ativa() -> None:
    implantacao = _make_implantacao(
        WizardStatus.IN_PROGRESS.value,
        unidade_produtiva_id=uuid.uuid4(),
    )
    pendencia = _make_pendencia()
    item = _make_item("CHECK_UNIDADE_PRODUTIVA")
    service = _build_service(
        implantacao,
        itens=[item],
        pendencias=[pendencia],
        checklist_minimo_satisfeito=True,
    )

    client, _ = _build_client()
    with patch("wizard.router.ImplantacaoService", return_value=service):
        response = client.get("/api/v1/wizard/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == WizardStatus.IN_PROGRESS.value
    assert body["pendencias_criticas_abertas"] == 1
    assert body["checklist_minimo_satisfeito"] is True
    assert body["pendencias_criticas"][0]["titulo"] == pendencia.titulo
    assert body["itens_checklist_faltantes"][0]["codigo_item"] == item.codigo_item
    assert "pendências críticas abertas" in body["motivos_bloqueio"][0]


def test_status_expoe_motivos_de_bloqueio_sem_unidade_produtiva_e_checklist() -> None:
    implantacao = _make_implantacao(WizardStatus.BLOCKED.value)
    item = _make_item("CHECK_UNIDADE_PRODUTIVA")
    service = _build_service(
        implantacao,
        itens=[item],
        checklist_minimo_satisfeito=False,
    )

    client, _ = _build_client()
    with patch("wizard.router.ImplantacaoService", return_value=service):
        response = client.get("/api/v1/wizard/status")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == WizardStatus.BLOCKED.value
    assert len(body["motivos_bloqueio"]) >= 3
    assert any("BLOCKED" in motivo for motivo in body["motivos_bloqueio"])
    assert any("UnidadeProdutiva" in motivo for motivo in body["motivos_bloqueio"])
    assert any("checklist mínimo" in motivo for motivo in body["motivos_bloqueio"])


def test_etapas_retorna_etapas_canonicas() -> None:
    implantacao = _make_implantacao()
    etapas = [_make_etapa("DIAGNOSTICO", 1), _make_etapa("UNIDADE_PRODUTIVA", 2)]
    service = _build_service(implantacao, etapas=etapas)

    client, _ = _build_client()
    with patch("wizard.router.ImplantacaoService", return_value=service):
        response = client.get("/api/v1/wizard/etapas")

    assert response.status_code == 200
    assert [item["codigo_etapa"] for item in response.json()] == [
        "DIAGNOSTICO",
        "UNIDADE_PRODUTIVA",
    ]


def test_checklist_retorna_itens() -> None:
    implantacao = _make_implantacao()
    itens = [_make_item("CHECK_UNIDADE_PRODUTIVA")]
    service = _build_service(implantacao, itens=itens, checklist_minimo_satisfeito=False)

    client, _ = _build_client()
    with patch("wizard.router.ImplantacaoService", return_value=service):
        response = client.get("/api/v1/wizard/checklist")

    assert response.status_code == 200
    body = response.json()
    assert body["checklist_minimo_satisfeito"] is False
    assert body["itens"][0]["codigo_item"] == "CHECK_UNIDADE_PRODUTIVA"
    assert "unidade produtiva" in body["itens"][0]["acao_recomendada"].lower()
    assert body["itens"][0]["acao_label"] == "Abrir propriedades"
    assert body["itens"][0]["acao_link"] == "/cadastros/propriedades"


def test_reavaliar_checklist_e_idempotente() -> None:
    implantacao = _make_implantacao()
    itens = [_make_item("CHECK_UNIDADE_PRODUTIVA")]
    service = _build_service(implantacao, itens=itens)
    engine = MagicMock()
    engine.avaliar_implantacao = AsyncMock(return_value=[])

    client, session = _build_client()
    with (
        patch("wizard.router.ImplantacaoService", return_value=service),
        patch("wizard.router.ChecklistEngine", return_value=engine),
    ):
        first = client.post("/api/v1/wizard/checklist/reavaliar")
        second = client.post("/api/v1/wizard/checklist/reavaliar")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["itens"][0]["codigo_item"] == second.json()["itens"][0]["codigo_item"]
    assert engine.avaliar_implantacao.await_count == 2
    assert session.commit.await_count == 2


def test_pendencias_retorna_lista() -> None:
    implantacao = _make_implantacao()
    pendencias = [_make_pendencia(), _make_pendencia(PendenciaStatus.RESOLVIDA.value)]
    service = _build_service(implantacao, pendencias=pendencias)

    client, _ = _build_client()
    with patch("wizard.router.ImplantacaoService", return_value=service):
        response = client.get("/api/v1/wizard/pendencias")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_pronto_go_live_bloqueia_sem_unidade_produtiva() -> None:
    implantacao = _make_implantacao(WizardStatus.IN_PROGRESS.value)
    service = _build_service(implantacao)
    engine = MagicMock()
    engine.avaliar_implantacao = AsyncMock(return_value=[])
    service.aplicar_transicao_estado = AsyncMock(
        side_effect=BusinessRuleError(
            "Transição para 'READY_FOR_GO_LIVE' exige unidade_produtiva_id."
        )
    )

    client, _ = _build_client()
    with (
        patch("wizard.router.ImplantacaoService", return_value=service),
        patch("wizard.router.ChecklistEngine", return_value=engine),
    ):
        response = client.post("/api/v1/wizard/pronto-go-live", json={})

    assert response.status_code == 400
    assert "unidade_produtiva_id" in response.json()["detail"]


def test_pronto_go_live_bloqueia_com_checklist_minimo_falso() -> None:
    implantacao = _make_implantacao(
        WizardStatus.IN_PROGRESS.value,
        unidade_produtiva_id=uuid.uuid4(),
    )
    service = _build_service(implantacao, checklist_minimo_satisfeito=False)
    engine = MagicMock()
    engine.avaliar_implantacao = AsyncMock(return_value=[])
    service.aplicar_transicao_estado = AsyncMock(
        side_effect=BusinessRuleError(
            "Transição para 'READY_FOR_GO_LIVE' exige checklist mínimo satisfeito."
        )
    )

    client, _ = _build_client()
    with (
        patch("wizard.router.ImplantacaoService", return_value=service),
        patch("wizard.router.ChecklistEngine", return_value=engine),
    ):
        response = client.post("/api/v1/wizard/pronto-go-live", json={})

    assert response.status_code == 400
    assert "checklist mínimo satisfeito" in response.json()["detail"]


def test_pronto_go_live_bloqueia_com_pendencia_critica() -> None:
    implantacao = _make_implantacao(
        WizardStatus.IN_PROGRESS.value,
        unidade_produtiva_id=uuid.uuid4(),
    )
    pendencias = [_make_pendencia()]
    service = _build_service(implantacao, pendencias=pendencias)
    engine = MagicMock()
    engine.avaliar_implantacao = AsyncMock(return_value=[])
    service.aplicar_transicao_estado = AsyncMock(
        side_effect=BusinessRuleError(
            "Transição para 'READY_FOR_GO_LIVE' bloqueada por pendência crítica aberta."
        )
    )

    client, _ = _build_client()
    with (
        patch("wizard.router.ImplantacaoService", return_value=service),
        patch("wizard.router.ChecklistEngine", return_value=engine),
    ):
        response = client.post("/api/v1/wizard/pronto-go-live", json={})

    assert response.status_code == 400
    assert "pendência crítica aberta" in response.json()["detail"]


def test_go_live_bloqueia_sem_ready_for_go_live() -> None:
    implantacao = _make_implantacao(
        WizardStatus.IN_PROGRESS.value,
        unidade_produtiva_id=uuid.uuid4(),
    )
    service = _build_service(implantacao)
    engine = MagicMock()
    engine.avaliar_implantacao = AsyncMock(return_value=[])
    service.aplicar_transicao_estado = AsyncMock(
        side_effect=BusinessRuleError(
            "Transição 'IN_PROGRESS' -> 'GO_LIVE' não permitida."
        )
    )

    client, _ = _build_client()
    with (
        patch("wizard.router.ImplantacaoService", return_value=service),
        patch("wizard.router.ChecklistEngine", return_value=engine),
    ):
        response = client.post("/api/v1/wizard/go-live", json={})

    assert response.status_code == 400
    assert "GO_LIVE" in response.json()["detail"]


def test_pausar_e_retomar_funcionam() -> None:
    implantacao = _make_implantacao(WizardStatus.IN_PROGRESS.value)
    service = _build_service(implantacao)

    async def _apply_transition(*args, **kwargs):
        implantacao.status = kwargs["novo_status"] if "novo_status" in kwargs else args[1]
        return implantacao

    service.aplicar_transicao_estado = AsyncMock(side_effect=_apply_transition)
    client, _ = _build_client()
    with patch("wizard.router.ImplantacaoService", return_value=service):
        paused = client.post("/api/v1/wizard/pausar", json={})
        resumed = client.post("/api/v1/wizard/retomar", json={})

    assert paused.status_code == 200
    assert paused.json()["status"] == WizardStatus.PAUSED.value
    assert resumed.status_code == 200
    assert resumed.json()["status"] == WizardStatus.IN_PROGRESS.value


def test_bloquear_e_desbloquear_funcionam() -> None:
    implantacao = _make_implantacao(WizardStatus.IN_PROGRESS.value)
    service = _build_service(implantacao)

    async def _apply_transition(*args, **kwargs):
        implantacao.status = kwargs["novo_status"] if "novo_status" in kwargs else args[1]
        return implantacao

    service.aplicar_transicao_estado = AsyncMock(side_effect=_apply_transition)
    client, _ = _build_client()
    with patch("wizard.router.ImplantacaoService", return_value=service):
        blocked = client.post("/api/v1/wizard/bloquear", json={"motivo": "Bloqueio teste"})
        unblocked = client.post("/api/v1/wizard/desbloquear", json={})

    assert blocked.status_code == 200
    assert blocked.json()["status"] == WizardStatus.BLOCKED.value
    assert unblocked.status_code == 200
    assert unblocked.json()["status"] == WizardStatus.IN_PROGRESS.value


def test_cancelar_funciona() -> None:
    implantacao = _make_implantacao(WizardStatus.PAUSED.value)
    service = _build_service(implantacao)

    async def _apply_transition(*args, **kwargs):
        implantacao.status = kwargs["novo_status"] if "novo_status" in kwargs else args[1]
        return implantacao

    service.aplicar_transicao_estado = AsyncMock(side_effect=_apply_transition)
    client, _ = _build_client()
    with patch("wizard.router.ImplantacaoService", return_value=service):
        response = client.post("/api/v1/wizard/cancelar", json={"motivo": "Encerrar piloto"})

    assert response.status_code == 200
    assert response.json()["status"] == WizardStatus.CANCELLED.value


def test_router_nao_importa_billing_convites_frontend_ou_routers_indevidos() -> None:
    source = (API_ROOT / "wizard" / "router.py").read_text()
    forbidden_terms = [
        "billing",
        "convite",
        "frontend",
        "next",
        "router_user",
    ]
    for term in forbidden_terms:
        assert term not in source.lower()


def test_router_nao_cria_rotas_de_usuario_tenant_assinatura_ou_convite() -> None:
    client, _ = _build_client()
    paths = {route.path for route in client.app.routes if route.path.startswith("/api/v1/wizard")}
    forbidden_fragments = ("usuario", "tenant", "assinatura", "convite")
    assert not any(fragment in path for path in paths for fragment in forbidden_fragments)


def test_main_registra_router_do_wizard() -> None:
    source = (API_ROOT / "main.py").read_text()
    assert "from wizard.router import router as wizard_router" in source
    assert 'app.include_router(wizard_router, prefix="/api/v1")' in source
