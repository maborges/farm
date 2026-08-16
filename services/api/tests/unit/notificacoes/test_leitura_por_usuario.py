"""Testes de leitura de notificação por usuário (notificacoes_leituras).

Antes, `Notificacao.lida` era um campo único tenant-wide: um usuário marcando
como lida afetava todos os outros do tenant. Agora o estado é por usuário.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from notificacoes.service import NotificacaoService
from notificacoes.models import Notificacao


def _row(notif: Notificacao, lida_usuario: bool, acao: str | None = None):
    return (notif, lida_usuario, acao)


def _make_notif() -> Notificacao:
    n = Notificacao()
    n.id = uuid.uuid4()
    n.tenant_id = uuid.uuid4()
    n.tipo = "PLANO_ACAO"
    n.titulo = "Teste"
    n.mensagem = "msg"
    n.nivel = "INFO"
    n.lida = False
    n.meta = {}
    n.origem = None
    n.origem_id = None
    return n


@pytest.mark.asyncio
async def test_listar_reflete_leitura_do_usuario_atual():
    """listar() deve trazer lida=True só para o usuário que efetivamente leu, não pra todos."""
    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    notif = _make_notif()

    result_mock = MagicMock()
    result_mock.all.return_value = [_row(notif, True)]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)
    session.expunge = MagicMock()

    svc = NotificacaoService(session, tenant_id)
    notificacoes = await svc.listar(usuario_id)

    assert len(notificacoes) == 1
    assert notificacoes[0].lida is True
    session.expunge.assert_called_once_with(notif)


@pytest.mark.asyncio
async def test_listar_nao_lida_para_usuario_sem_registro_de_leitura():
    """Sem linha em notificacoes_leituras para o usuário, lida deve vir False (default)."""
    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    notif = _make_notif()

    result_mock = MagicMock()
    result_mock.all.return_value = [_row(notif, False)]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)
    session.expunge = MagicMock()

    svc = NotificacaoService(session, tenant_id)
    notificacoes = await svc.listar(usuario_id)

    assert notificacoes[0].lida is False


@pytest.mark.asyncio
async def test_marcar_lidas_nao_afeta_outro_usuario():
    """marcar_lidas grava upsert só para o usuario_id informado — outro usuário mantém não-lida."""
    tenant_id = uuid.uuid4()
    usuario_a = uuid.uuid4()
    notif_id = uuid.uuid4()

    select_ids_result = MagicMock()
    select_ids_result.all.return_value = [(notif_id,)]
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[select_ids_result, MagicMock()])

    svc = NotificacaoService(session, tenant_id)
    count = await svc.marcar_lidas(usuario_a, [notif_id])
    assert count == 1

    upsert_stmt = session.execute.call_args_list[1].args[0]
    # values do upsert devem conter o usuario_id do chamador, não um genérico
    compiled_params = upsert_stmt.compile().params
    assert any(v == usuario_a for v in compiled_params.values())


@pytest.mark.asyncio
async def test_listar_filtra_por_sistema_ativo_da_preferencia_do_usuario():
    """sistema_ativo=False na preferência do usuário deve suprimir a notificação daquele tipo para ele."""
    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()
    notif = _make_notif()

    result_mock = MagicMock()
    result_mock.all.return_value = []  # suprimida pelo filtro sistema_ativo == True
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)
    session.expunge = MagicMock()

    svc = NotificacaoService(session, tenant_id)
    notificacoes = await svc.listar(usuario_id)

    assert notificacoes == []
    stmt = session.execute.call_args.args[0]
    assert "notificacoes_preferencias" in str(stmt)
    assert "sistema_ativo" in str(stmt)


@pytest.mark.asyncio
async def test_total_nao_lidas_por_usuario():
    tenant_id = uuid.uuid4()
    usuario_id = uuid.uuid4()

    # total_nao_lidas agora traz (id, tipo) por linha e aplica o filtro de
    # visibilidade RBAC em Python (mesma lógica de _filtrar_notificacoes_visiveis),
    # em vez de um COUNT puro em SQL — tipos de propósito geral (sem entrada em
    # notificacoes/constants.py) contam sempre.
    result_mock = MagicMock()
    result_mock.all.return_value = [
        (uuid.uuid4(), "RESUMO_DIARIO"),
        (uuid.uuid4(), "PLANO_ACAO"),
        (uuid.uuid4(), "RECOMENDACAO"),
    ]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)

    svc = NotificacaoService(session, tenant_id)
    total = await svc.total_nao_lidas(usuario_id)
    assert total == 3
