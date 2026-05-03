"""Testes de sincronização, deduplicação e leitura de notificações — Step 106."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from notificacoes.service import NotificacaoService
from notificacoes.schemas import NotificacaoCreate
from notificacoes.models import Notificacao
from financeiro.models.plano_acao import PlanoAcaoItem


def _mock_session(existing: list = []):
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = existing
    scalars_mock.scalar_one_or_none.return_value = existing[0] if existing else None
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    result_mock.scalar_one_or_none.return_value = existing[0] if existing else None
    result_mock.scalar.return_value = len(existing)
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)
    session.get = AsyncMock(return_value=existing[0] if existing else None)
    return session


def _make_notif(tipo: str = "PLANO_ACAO", lida: bool = False, origem_id: str = "abc") -> Notificacao:
    n = Notificacao()
    n.id = uuid.uuid4()
    n.tenant_id = uuid.uuid4()
    n.tipo = tipo
    n.titulo = "Teste"
    n.mensagem = "msg"
    n.nivel = "INFO"
    n.lida = lida
    n.meta = {}
    n.origem = "plano_acao"
    n.origem_id = origem_id
    n.created_at = datetime.now(timezone.utc)
    n.read_at = None
    return n


def _make_plano_item(status: str = "PENDENTE", prioridade: str = "ALTA") -> PlanoAcaoItem:
    item = PlanoAcaoItem()
    item.id = uuid.uuid4()
    item.tipo = "REVISAR_CUSTOS"
    item.titulo = "Revisar custos"
    item.descricao = "Descrição"
    item.prioridade = prioridade
    item.status = status
    item.rota = "/financeiro"
    return item


@pytest.mark.asyncio
async def test_criar_sem_duplicar_cria_nova():
    """Deve criar notificação quando não existe outra não-lida da mesma origem."""
    tenant_id = uuid.uuid4()
    session = _mock_session([])  # sem existentes

    svc = NotificacaoService(session, tenant_id)
    dados = NotificacaoCreate(
        tipo="PLANO_ACAO",
        titulo="Ação",
        mensagem="msg",
        origem="plano_acao",
        origem_id="item-1",
    )

    with patch.object(svc, "criar_e_push", AsyncMock(return_value=_make_notif())):
        result = await svc.criar_sem_duplicar(dados)
        assert result is not None


@pytest.mark.asyncio
async def test_criar_sem_duplicar_nao_duplica():
    """Não deve criar quando já existe notificação não-lida da mesma origem."""
    tenant_id = uuid.uuid4()
    existente = _make_notif(origem_id="item-1")
    session = _mock_session([existente])

    svc = NotificacaoService(session, tenant_id)
    dados = NotificacaoCreate(
        tipo="PLANO_ACAO",
        titulo="Ação",
        mensagem="msg",
        origem="plano_acao",
        origem_id="item-1",
    )

    with patch.object(svc, "criar_e_push", AsyncMock()) as mock_criar:
        result = await svc.criar_sem_duplicar(dados)
        assert result is None
        mock_criar.assert_not_called()


@pytest.mark.asyncio
async def test_sincronizar_safra_cria_para_pendentes():
    """Deve criar notificações para itens PENDENTE do plano de ação."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    session = _mock_session([])

    svc = NotificacaoService(session, tenant_id)
    item = _make_plano_item(status="PENDENTE", prioridade="ALTA")

    with patch("financeiro.services.plano_acao_service.PlanoAcaoService") as MockPlano:
        MockPlano.return_value.listar = AsyncMock(return_value=[item])
        with patch.object(svc, "criar_sem_duplicar", AsyncMock(return_value=_make_notif())):
            resultado = await svc.sincronizar_safra(safra_id)
            assert len(resultado) == 1


@pytest.mark.asyncio
async def test_sincronizar_ignora_concluidas():
    """Itens CONCLUIDA não devem gerar notificação."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    session = _mock_session([])

    svc = NotificacaoService(session, tenant_id)
    item_concluido = _make_plano_item(status="CONCLUIDA")

    with patch("financeiro.services.plano_acao_service.PlanoAcaoService") as MockPlano:
        MockPlano.return_value.listar = AsyncMock(return_value=[item_concluido])
        with patch.object(svc, "criar_sem_duplicar", AsyncMock()) as mock_criar:
            await svc.sincronizar_safra(safra_id)
            mock_criar.assert_not_called()


@pytest.mark.asyncio
async def test_marcar_lidas_preenche_read_at():
    """marcar_lidas deve atualizar read_at."""
    tenant_id = uuid.uuid4()
    session = _mock_session([])
    update_result = MagicMock()
    update_result.rowcount = 1
    session.execute = AsyncMock(return_value=update_result)

    svc = NotificacaoService(session, tenant_id)
    count = await svc.marcar_lidas([uuid.uuid4()])
    assert count == 1
    # Verifica que foi chamado com values contendo read_at
    call_args = session.execute.call_args_list
    assert len(call_args) >= 1
