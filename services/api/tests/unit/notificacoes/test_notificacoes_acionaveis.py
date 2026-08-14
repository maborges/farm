"""Testes do modelo de notificação acionável (meta.acoes) para RECOMENDACAO e DIARIA_PENDENTE.

Cobre: filtro de ações por permissão do usuário (não confiar em algo gravado
estaticamente na criação), registro de ação disparada (registrar_acao) e o
endpoint POST /notificacoes/{id}/acao.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from notificacoes.service import NotificacaoService
from notificacoes.models import Notificacao


def _notif_recomendacao(origem_id: str) -> Notificacao:
    n = Notificacao()
    n.id = uuid.uuid4()
    n.tenant_id = uuid.uuid4()
    n.tipo = "RECOMENDACAO"
    n.titulo = "Recomendação"
    n.mensagem = "msg"
    n.nivel = "WARNING"
    n.origem = "recommendation"
    n.origem_id = origem_id
    n.meta = {
        "acoes": [
            {"label": "Aceitar", "acao": "accept", "endpoint": "/recommendations/x/accept"},
            {"label": "Descartar", "acao": "dismiss", "endpoint": "/recommendations/x/dismiss"},
        ]
    }
    return n


def _notif_plano_acao(item_id: str) -> Notificacao:
    n = Notificacao()
    n.id = uuid.uuid4()
    n.tenant_id = uuid.uuid4()
    n.tipo = "PLANO_ACAO"
    n.titulo = "Ação pendente"
    n.mensagem = "msg"
    n.nivel = "WARNING"
    n.origem = "plano_acao"
    n.origem_id = item_id
    n.meta = {
        "acoes": [
            {"label": "Concluir", "acao": "concluir", "endpoint": f"/plano-acoes/{item_id}/status", "method": "PATCH", "body": {"status": "CONCLUIDA"}},
            {"label": "Ignorar", "acao": "ignorar", "endpoint": f"/plano-acoes/{item_id}/status", "method": "PATCH", "body": {"status": "IGNORADA"}},
        ]
    }
    return n


def _notif_diaria() -> Notificacao:
    n = Notificacao()
    n.id = uuid.uuid4()
    n.tenant_id = uuid.uuid4()
    n.tipo = "DIARIA_PENDENTE"
    n.titulo = "Diárias pendentes"
    n.mensagem = "msg"
    n.nivel = "WARNING"
    n.origem = "rh_diaria"
    n.origem_id = str(uuid.uuid4())
    n.meta = {"acoes": [{"label": "Pagar", "acao": "pagar", "endpoint": "/rh/diarias/pagar-lote"}]}
    return n


@pytest.mark.asyncio
async def test_filtra_acoes_recomendacao_por_autorizacao_real():
    """Usuário sem permissão em uma ação específica não deve ver o botão correspondente."""
    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    rec_id = uuid.uuid4()
    notif = _notif_recomendacao(str(rec_id))
    session = AsyncMock()
    svc = NotificacaoService(session, tenant_id)

    async def fake_pode_executar(self, recommendation_id, action):
        return action == "accept"  # só pode aceitar, não descartar

    with patch(
        "recommendations.authorization.RecommendationAuthorizationService.pode_executar",
        new=fake_pode_executar,
    ):
        meta = await svc._filtrar_acoes_por_permissao(notif, usuario_id, ja_executada=None)

    acoes = [item["acao"] for item in meta["acoes"]]
    assert acoes == ["accept"]


@pytest.mark.asyncio
async def test_filtra_acoes_diaria_pendente_exige_permissao_rh():
    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    notif = _notif_diaria()
    session = AsyncMock()
    svc = NotificacaoService(session, tenant_id)

    with patch(
        "core.dependencies.resolver_permissao_usuario", new=AsyncMock(return_value=False)
    ):
        meta = await svc._filtrar_acoes_por_permissao(notif, usuario_id, ja_executada=None)

    assert meta["acoes"] == []


@pytest.mark.asyncio
async def test_filtra_acoes_diaria_pendente_permitida():
    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    notif = _notif_diaria()
    session = AsyncMock()
    svc = NotificacaoService(session, tenant_id)

    with patch(
        "core.dependencies.resolver_permissao_usuario", new=AsyncMock(return_value=True)
    ):
        meta = await svc._filtrar_acoes_por_permissao(notif, usuario_id, ja_executada=None)

    assert len(meta["acoes"]) == 1


@pytest.mark.asyncio
async def test_plano_acao_nao_filtra_por_permissao_endpoint_sem_rbac():
    """PATCH /plano-acoes/{id}/status não tem checagem de permissão hoje — ações passam direto."""
    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    item_id = str(uuid.uuid4())
    notif = _notif_plano_acao(item_id)
    session = AsyncMock()
    svc = NotificacaoService(session, tenant_id)

    meta = await svc._filtrar_acoes_por_permissao(notif, usuario_id, ja_executada=None)

    assert len(meta["acoes"]) == 2
    assert {a["acao"] for a in meta["acoes"]} == {"concluir", "ignorar"}


@pytest.mark.asyncio
async def test_acao_ja_executada_esvazia_botoes_e_marca_flag():
    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    notif = _notif_diaria()
    session = AsyncMock()
    svc = NotificacaoService(session, tenant_id)

    meta = await svc._filtrar_acoes_por_permissao(notif, usuario_id, ja_executada="pagar")

    assert meta["acoes"] == []
    assert meta["acao_executada"] == "pagar"


@pytest.mark.asyncio
async def test_tipo_sem_whitelist_nao_expoe_acoes():
    """Tipo desconhecido nunca deve vazar botões de ação — default seguro é esconder."""
    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    n = Notificacao()
    n.id = uuid.uuid4()
    n.tipo = "OUTRO_TIPO_QUALQUER"
    n.origem_id = None
    n.meta = {"acoes": [{"label": "X", "acao": "x"}]}
    session = AsyncMock()
    svc = NotificacaoService(session, tenant_id)

    meta = await svc._filtrar_acoes_por_permissao(n, usuario_id, ja_executada=None)
    assert meta["acoes"] == []


@pytest.mark.asyncio
async def test_registrar_acao_faz_upsert_com_acao_e_marca_lida():
    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    notif_id = uuid.uuid4()
    session = AsyncMock()
    svc = NotificacaoService(session, tenant_id)

    await svc.registrar_acao(usuario_id, notif_id, "pagar")

    upsert_stmt = session.execute.call_args_list[0].args[0]
    assert "notificacoes_leituras" in str(upsert_stmt)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_endpoint_registrar_acao_delega_ao_service():
    from notificacoes.router import registrar_acao
    from notificacoes.schemas import NotificacaoAcaoRequest

    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    notif_id = uuid.uuid4()
    current_user = MagicMock()
    current_user.id = usuario_id

    with patch("notificacoes.router.NotificacaoService") as MockSvc:
        MockSvc.return_value.registrar_acao = AsyncMock()
        result = await registrar_acao(
            notificacao_id=notif_id,
            dados=NotificacaoAcaoRequest(acao="accept"),
            session=AsyncMock(),
            tenant_id=tenant_id,
            current_user=current_user,
        )

    MockSvc.return_value.registrar_acao.assert_awaited_once_with(usuario_id, notif_id, "accept")
    assert result == {"message": "Ação registrada"}
