import pytest
import asyncio
from unittest.mock import patch, MagicMock
from notificacoes.email_service import enviar_email, _send_email_sync

@pytest.mark.asyncio
@patch('notificacoes.email_service.smtplib.SMTP')
@patch('notificacoes.email_service.settings')
async def test_enviar_email_sucesso(mock_settings, mock_smtp_class):
    # Setup
    mock_settings.smtp_host = 'smtp.fake.io'
    mock_settings.smtp_port = 2525
    mock_settings.smtp_user = 'user'
    mock_settings.smtp_pass = 'pass'
    mock_settings.mail_from = 'teste@agrosaas.com.br'
    mock_settings.frontend_url = 'http://localhost'

    mock_smtp_instance = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance

    destinatario = 'produtor@teste.com'
    assunto = 'Atenção na Safra'
    mensagem = 'Margem negativa detectada'

    # Act
    await enviar_email(destinatario, assunto, mensagem)

    # Verifica se conectou no SMTP
    mock_smtp_class.assert_called_with('smtp.fake.io', 2525)
    
    # Verifica login
    mock_smtp_instance.login.assert_called_once_with('user', 'pass')
    
    # Verifica envio
    mock_smtp_instance.send_message.assert_called_once()
    msg_enviada = mock_smtp_instance.send_message.call_args[0][0]
    
    assert msg_enviada['To'] == destinatario
    assert msg_enviada['Subject'] == assunto
    assert msg_enviada['From'] == mock_settings.mail_from

@pytest.mark.asyncio
@patch('notificacoes.email_service.smtplib.SMTP')
@patch('notificacoes.email_service.settings')
async def test_enviar_email_sem_host(mock_settings, mock_smtp_class):
    # Setup
    mock_settings.smtp_host = ""  # Vazio, não deve tentar enviar
    
    # Act
    await enviar_email("dest", "assunto", "msg")
    
    # Assert
    mock_smtp_class.assert_not_called()

@pytest.mark.asyncio
@patch('notificacoes.email_service.smtplib.SMTP')
@patch('notificacoes.email_service.settings')
async def test_enviar_email_nao_quebra_com_erro(mock_settings, mock_smtp_class):
    # Setup
    mock_settings.smtp_host = 'smtp.fake.io'
    mock_smtp_class.side_effect = Exception("Erro forçado conexão recusada")
    
    # Act - não deve dar raise
    await enviar_email("dest", "assunto", "msg")
    
    # Se chegamos aqui sem exceção, sucesso
    assert True
