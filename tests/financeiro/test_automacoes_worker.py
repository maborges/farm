import pytest
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import sys

# Mocks para evitar importações de arquivos dependentes complexos do financeiro
sys.modules['financeiro.services.lancamento_service'] = MagicMock()
sys.modules['financeiro.models.plano_acao'] = MagicMock()
sys.modules['notificacoes.service'] = MagicMock()
sys.modules['notificacoes.schemas'] = MagicMock()

# Como _calcular_proxima_execucao será usado no worker e importado do automacoes.service
from automacoes.models import AutomacaoConfiguracao
from automacoes.worker import process_automations

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session

@pytest.fixture
def configuracao_vencida():
    cfg = AutomacaoConfiguracao(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        safra_id=uuid.uuid4(),
        regra="MARGEM_NEGATIVA",
        ativa=True,
        frequencia="DIARIA",
        proxima_execucao=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    return cfg

@pytest.fixture
def configuracao_futura():
    cfg = AutomacaoConfiguracao(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        safra_id=uuid.uuid4(),
        regra="MARGEM_NEGATIVA",
        ativa=True,
        frequencia="DIARIA",
        proxima_execucao=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    return cfg

@pytest.mark.asyncio
@patch('automacoes.worker.get_db_session')
@patch('automacoes.worker.AutomacoesService')
async def test_process_automations_sucesso(mock_service_class, mock_get_db, mock_db_session, configuracao_vencida):
    # Setup
    mock_get_db.return_value = mock_db_session
    
    # Mock return configs
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [configuracao_vencida]
    mock_db_session.execute.return_value = mock_result
    
    # Mock do serviço e execução
    mock_service_instance = AsyncMock()
    mock_service_instance.executar.return_value = MagicMock(acoes_criadas=1, notificacoes_criadas=1)
    mock_service_class.return_value = mock_service_instance
    
    # Act
    await process_automations()
    
    # Assert
    # Executou a verificação
    assert mock_db_session.execute.called
    
    # Chamou o AutomacoesService
    mock_service_class.assert_called_once_with(mock_db_session, configuracao_vencida.tenant_id)
    mock_service_instance.executar.assert_called_once_with(configuracao_vencida.safra_id)
    
    # Proxima execução foi atualizada
    assert configuracao_vencida.proxima_execucao > datetime.now(timezone.utc)
    
    # Comitou no banco
    assert mock_db_session.commit.called
    assert mock_db_session.close.called

@pytest.mark.asyncio
@patch('automacoes.worker.get_db_session')
@patch('automacoes.worker.AutomacoesService')
async def test_process_automations_falha_em_um_registro(mock_service_class, mock_get_db, mock_db_session, configuracao_vencida):
    # Setup
    mock_get_db.return_value = mock_db_session
    
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [configuracao_vencida]
    mock_db_session.execute.return_value = mock_result
    
    # Mock para falhar a execução do primeiro
    mock_service_instance = AsyncMock()
    mock_service_instance.executar.side_effect = Exception("Erro forçado")
    mock_service_class.return_value = mock_service_instance
    
    # Act
    await process_automations()
    
    # Assert
    # Ocorreu rollback e fechou a sessao
    assert mock_db_session.rollback.called
    assert mock_db_session.close.called

@pytest.mark.asyncio
@patch('automacoes.worker.get_db_session')
@patch('automacoes.worker.AutomacoesService')
async def test_process_automations_nao_faz_nada_quando_vazio(mock_service_class, mock_get_db, mock_db_session):
    # Setup
    mock_get_db.return_value = mock_db_session
    
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_db_session.execute.return_value = mock_result
    
    # Act
    await process_automations()
    
    # Assert
    # Não chamou AutomacoesService
    assert not mock_service_class.called
    # Fechou
    assert mock_db_session.close.called
