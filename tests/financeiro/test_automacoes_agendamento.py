import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import sys

# Mock dependências do service que não precisamos para testar o cálculo de datas
sys.modules['financeiro.services.lancamento_service'] = MagicMock()
sys.modules['financeiro.models.plano_acao'] = MagicMock()
sys.modules['notificacoes.service'] = MagicMock()
sys.modules['notificacoes.schemas'] = MagicMock()
sys.modules['automacoes.models'] = MagicMock()

from automacoes.service import _calcular_proxima_execucao

def test_calcular_proxima_execucao_manual():
    frequencia = "MANUAL"
    resultado = _calcular_proxima_execucao(frequencia)
    assert resultado is None

@patch('automacoes.service.datetime')
def test_calcular_proxima_execucao_diaria(mock_datetime):
    mock_now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now
    
    frequencia = "DIARIA"
    expected = mock_now + timedelta(days=1)
    
    resultado = _calcular_proxima_execucao(frequencia)
    assert resultado == expected

@patch('automacoes.service.datetime')
def test_calcular_proxima_execucao_semanal(mock_datetime):
    mock_now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now
    
    frequencia = "SEMANAL"
    expected = mock_now + timedelta(days=7)
    
    resultado = _calcular_proxima_execucao(frequencia)
    assert resultado == expected

@patch('automacoes.service.datetime')
def test_calcular_proxima_execucao_mensal(mock_datetime):
    mock_now = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_now
    
    frequencia = "MENSAL"
    expected = mock_now + timedelta(days=30)
    
    resultado = _calcular_proxima_execucao(frequencia)
    assert resultado == expected

def test_calcular_proxima_execucao_nulo():
    frequencia = None
    resultado = _calcular_proxima_execucao(frequencia)
    assert resultado is None

def test_calcular_proxima_execucao_invalido():
    frequencia = "INVALIDA"
    resultado = _calcular_proxima_execucao(frequencia)
    assert resultado is None
