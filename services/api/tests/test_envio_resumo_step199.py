import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

# Mocks para dependências que podem falhar no ambiente de teste
import sys
from types import ModuleType
from sqlalchemy.orm import DeclarativeBase

def mock_module(name):
    m = ModuleType(name)
    sys.modules[name] = m
    return m

from sqlalchemy import Column, String, Uuid as UUID_COL
class MockBase(DeclarativeBase):
    pass

mock_db = mock_module("core.database")
mock_db.async_session_maker = MagicMock()
mock_db.Base = MockBase

class MockUsuario(MockBase):
    __tablename__ = "usuarios"
    id = Column(UUID_COL, primary_key=True)
    email = Column(String)
    telefone = Column(String)

mock_auth = mock_module("core.models.auth")
mock_auth.Usuario = MockUsuario

mock_rd = mock_module("financeiro.services.resumo_diario_service")
mock_rd.ResumoDiarioService = MagicMock()

mock_email = mock_module("notificacoes.email_service")
mock_email.enviar_email = AsyncMock()

from notificacoes.resumo_diario_envio_service import EnvioResumoDiarioService
from notificacoes.models import NotificacaoPreferencia

@pytest.mark.asyncio
async def test_envio_resumo_agendado_logic():
    """Testa se a lógica de filtro de horário e canal funciona."""
    
    # Mock da sessão e do resultado da query
    mock_session = AsyncMock()
    mock_db.async_session_maker.return_value.__aenter__.return_value = mock_session
    
    pref = NotificacaoPreferencia(
        id=uuid4(),
        tenant_id=uuid4(),
        usuario_id=uuid4(),
        tipo="RESUMO_DIARIO",
        email_ativo=True,
        horario_envio=datetime.now(timezone.utc).strftime("%H:%M")
    )
    user = MockUsuario(id=pref.usuario_id, email="test@example.com", telefone="123456")
    
    # Mock do retorno do banco: (pref, user)
    mock_result = MagicMock()
    mock_result.all.return_value = [(pref, user)]
    mock_session.execute.return_value = mock_result
    
    # Mock do check de duplicidade (não existe hoje)
    mock_session.execute.side_effect = [
        mock_result, # primeira chamada: busca agendados
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)) # segunda: check duplicidade
    ]
    
    # Mock do serviço de resumo
    mock_resumo_data = MagicMock()
    mock_resumo_data.resumo_ia = "Resumo Teste"
    mock_resumo_data.top_alertas = []
    mock_resumo_data.risco_principal = "Risco"
    mock_resumo_data.oportunidade_principal = "Oportunidade"
    
    with patch("notificacoes.resumo_diario_envio_service.ResumoDiarioService") as MockSvc:
        instance = MockSvc.return_value
        instance.obter_resumo = AsyncMock(return_value=mock_resumo_data)
        
        await EnvioResumoDiarioService.enviar_resumos_agendados()
        
        # Verificar se e-mail foi "enviado"
        mock_email.enviar_email.assert_called_once()
        args, _ = mock_email.enviar_email.call_args
        assert "test@example.com" in args
        assert "Resumo Diário" in args[1]
        
        # Verificar se registrou a notificação
        assert mock_session.add.called
