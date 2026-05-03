import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from notificacoes.schemas import NotificacaoCreate
from notificacoes.service import NotificacaoService
from notificacoes.models import Notificacao

@pytest.fixture
def session_mock():
    session = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_cria_notificacao_sem_cooldown(session_mock):
    tenant_id = uuid.uuid4()
    svc = NotificacaoService(session_mock, tenant_id)
    
    # Ajustar mock para retornar nenhum cooldown
    mock_result_email = MagicMock()
    mock_result_email.scalar.return_value = "dono@teste.com"
    
    mock_result_user = MagicMock()
    # 1. user, 2. recente (None), 3. pref (None)
    mock_result_user.scalar_one_or_none.side_effect = [
        MagicMock(id=uuid.uuid4()), # user
        None, # recente
        None  # preferencia
    ]
    
    session_mock.execute = AsyncMock(side_effect=[mock_result_email, mock_result_user, mock_result_user, mock_result_user])
    
    dados = NotificacaoCreate(
        tipo="ALERTA_FINANCEIRO",
        titulo="Alerta",
        mensagem="Msg",
        nivel="DANGER"
    )
    
    # Mock create
    notif = Notificacao(id=uuid.uuid4(), tipo="ALERTA_FINANCEIRO", nivel="DANGER", created_at=datetime.now(timezone.utc))
    svc.create = AsyncMock(return_value=notif)
    
    with patch("notificacoes.service.manager.push", new_callable=AsyncMock):
        result = await svc.criar_e_push(dados)
        
    assert result is not None
    assert result.tipo == "ALERTA_FINANCEIRO"
    svc.create.assert_called_once()

@pytest.mark.asyncio
async def test_suprime_notificacao_dentro_cooldown(session_mock):
    tenant_id = uuid.uuid4()
    svc = NotificacaoService(session_mock, tenant_id)
    
    # Ajustar mock para retornar uma notificação recente no cooldown
    recente = Notificacao(id=uuid.uuid4(), tipo="ALERTA_FINANCEIRO", created_at=datetime.now(timezone.utc))
    
    mock_result_email = MagicMock()
    mock_result_email.scalar.return_value = "dono@teste.com"
    
    mock_result_user = MagicMock()
    # 1. user, 2. recente (encontrou!)
    mock_result_user.scalar_one_or_none.side_effect = [
        MagicMock(id=uuid.uuid4()), # user
        recente
    ]
    
    session_mock.execute = AsyncMock(side_effect=[mock_result_email, mock_result_user, mock_result_user])
    
    dados = NotificacaoCreate(
        tipo="ALERTA_FINANCEIRO",
        titulo="Alerta",
        mensagem="Msg",
        nivel="DANGER"
    )
    
    svc.create = AsyncMock()
    
    result = await svc.criar_e_push(dados)
    
    # Não deve criar
    assert result is None
    svc.create.assert_not_called()

@pytest.mark.asyncio
@patch("notificacoes.service.logger")
async def test_logs_suprimir_cooldown(mock_logger, session_mock):
    tenant_id = uuid.uuid4()
    svc = NotificacaoService(session_mock, tenant_id)
    
    recente = Notificacao(id=uuid.uuid4())
    mock_result_email = MagicMock()
    mock_result_email.scalar.return_value = "dono@teste.com"
    
    mock_result_user = MagicMock()
    # 1. user, 2. recente (encontrou!)
    mock_result_user.scalar_one_or_none.side_effect = [
        MagicMock(id=uuid.uuid4()), recente
    ]
    session_mock.execute = AsyncMock(side_effect=[mock_result_email, mock_result_user, mock_result_user])
    
    dados = NotificacaoCreate(tipo="ALERTA_FINANCEIRO", titulo="X", mensagem="Y")
    await svc.criar_e_push(dados)
    
    # Verifica se logou
    mock_logger.info.assert_called_with("Notificação suprimida por cooldown: ALERTA_FINANCEIRO (origem=None)")
