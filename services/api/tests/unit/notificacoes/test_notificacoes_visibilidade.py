"""Testes do RBAC de visibilidade de notificações (NotificacaoService).

Notificacao é tenant-wide na criação (sem destinatário). Estes testes cobrem
`_filtrar_notificacoes_visiveis` (decide se a notificação aparece na lista,
diferente de `_filtrar_acoes_por_permissao`, que decide os botões de ação de
uma notificação que já apareceu) e o reflexo do mesmo filtro em
`total_nao_lidas` (contador do sino).
"""
import uuid
import pytest
from unittest.mock import AsyncMock, patch

from notificacoes.service import NotificacaoService
from notificacoes.models import Notificacao


def _notif(tipo: str) -> Notificacao:
    n = Notificacao()
    n.id = uuid.uuid4()
    n.tenant_id = uuid.uuid4()
    n.tipo = tipo
    n.titulo = "titulo"
    n.mensagem = "msg"
    n.nivel = "INFO"
    n.meta = {}
    return n


def _make_service() -> NotificacaoService:
    session = AsyncMock()
    return NotificacaoService(session, uuid.uuid4())


@pytest.mark.asyncio
async def test_usuario_sem_permissao_financeira_nao_ve_notificacao_financeira():
    svc = _make_service()
    notif = _notif("FINANCEIRO_VENCIDO")
    with patch(
        "core.dependencies.resolver_permissao_usuario", new=AsyncMock(return_value=False)
    ):
        visiveis = await svc._filtrar_notificacoes_visiveis([notif], uuid.uuid4())
    assert visiveis == []


@pytest.mark.asyncio
async def test_usuario_com_permissao_financeira_ve_notificacao():
    svc = _make_service()
    notif = _notif("FINANCEIRO_VENCIDO")
    with patch(
        "core.dependencies.resolver_permissao_usuario", new=AsyncMock(return_value=True)
    ):
        visiveis = await svc._filtrar_notificacoes_visiveis([notif], uuid.uuid4())
    assert visiveis == [notif]


@pytest.mark.asyncio
async def test_owner_ve_tudo():
    svc = _make_service()
    notifs = [_notif("FINANCEIRO_VENCIDO"), _notif("HEDGE_ALERTA"), _notif("ESG_NAO_CONFORMIDADE_ABERTA")]
    # is_owner=True já retorna sempre True dentro de resolver_permissao_usuario;
    # simulamos esse efeito diretamente no mock.
    with patch(
        "core.dependencies.resolver_permissao_usuario", new=AsyncMock(return_value=True)
    ):
        visiveis = await svc._filtrar_notificacoes_visiveis(notifs, uuid.uuid4())
    assert visiveis == notifs


@pytest.mark.asyncio
async def test_tipos_de_proposito_geral_sempre_visiveis():
    svc = _make_service()
    notifs = [_notif("RESUMO_DIARIO"), _notif("PLANO_ACAO"), _notif("RECOMENDACAO")]
    mock_resolver = AsyncMock(return_value=False)
    with patch("core.dependencies.resolver_permissao_usuario", new=mock_resolver):
        visiveis = await svc._filtrar_notificacoes_visiveis(notifs, uuid.uuid4())
    assert visiveis == notifs
    mock_resolver.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_permissao_uma_vez_por_permissao_distinta():
    svc = _make_service()
    notifs = [_notif("FINANCEIRO_VENCIDO"), _notif("HEDGE_ALERTA"), _notif("ALERTA_FINANCEIRO")]
    mock_resolver = AsyncMock(return_value=True)
    with patch("core.dependencies.resolver_permissao_usuario", new=mock_resolver):
        visiveis = await svc._filtrar_notificacoes_visiveis(notifs, uuid.uuid4())
    assert len(visiveis) == 3
    # todos os 3 tipos mapeiam para "financeiro:*" -> deve resolver 1x só (cache)
    assert mock_resolver.await_count == 1


@pytest.mark.asyncio
async def test_nao_lidas_count_reflete_mesmo_filtro():
    svc = _make_service()
    tenant_id = svc.tenant_id
    usuario_id = uuid.uuid4()

    class _Result:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    notif_financeira_id = uuid.uuid4()
    notif_geral_id = uuid.uuid4()
    svc.session.execute = AsyncMock(
        return_value=_Result(
            [
                (notif_financeira_id, "FINANCEIRO_VENCIDO"),
                (notif_geral_id, "RESUMO_DIARIO"),
            ]
        )
    )

    with patch(
        "core.dependencies.resolver_permissao_usuario", new=AsyncMock(return_value=False)
    ):
        total = await svc.total_nao_lidas(usuario_id)

    # só a RESUMO_DIARIO (tipo de propósito geral) conta, pois o usuário não
    # tem financeiro:*
    assert total == 1
