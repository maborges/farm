import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from ia.models import IAAlertaHistorico
from financeiro.services.alerta_inteligente_service import AlertaInteligenteService

from sqlalchemy import delete
from tests.conftest import TENANT_A_ID

@pytest.mark.asyncio
async def test_classificacao_perfil_conservador(session: AsyncSession):
    tenant_id = TENANT_A_ID
    safra_id = uuid.uuid4()
    
    # Limpa histórico anterior
    await session.execute(delete(IAAlertaHistorico).where(IAAlertaHistorico.tenant_id == tenant_id))
    
    # Cria 10 alertas, onde 6 foram ignorados (60% ignorados -> CONSERVADOR)
    for i in range(10):
        alerta = IAAlertaHistorico(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            safra_id=safra_id,
            tipo_alerta="TESTE",
            titulo=f"Alerta {i}",
            mensagem="...",
            gravidade="media",
            ignorado=True if i < 6 else False,
            acao_executada=False,
            created_at=datetime.now(timezone.utc)
        )
        session.add(alerta)
    
    await session.commit()
    
    svc = AlertaInteligenteService(session, tenant_id)
    comportamento = await svc._analisar_comportamento_usuario()
    
    assert comportamento["perfil"] == "CONSERVADOR"
    assert comportamento["taxa_ignorado"] == 60.0
    assert comportamento["taxa_execucao"] == 0.0

@pytest.mark.asyncio
async def test_classificacao_perfil_agressivo(session: AsyncSession):
    tenant_id = TENANT_A_ID
    safra_id = uuid.uuid4()
    
    # Limpa histórico anterior
    await session.execute(delete(IAAlertaHistorico).where(IAAlertaHistorico.tenant_id == tenant_id))
    
    # Cria 10 alertas, onde 5 foram executados (50% executados -> AGRESSIVO)
    for i in range(10):
        alerta = IAAlertaHistorico(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            safra_id=safra_id,
            tipo_alerta="TESTE_RISCO",
            titulo=f"Alerta {i}",
            mensagem="...",
            gravidade="media",
            ignorado=False,
            acao_executada=True if i < 5 else False,
            created_at=datetime.now(timezone.utc)
        )
        session.add(alerta)
    
    await session.commit()
    
    svc = AlertaInteligenteService(session, tenant_id)
    comportamento = await svc._analisar_comportamento_usuario()
    
    assert comportamento["perfil"] == "AGRESSIVO"
    assert comportamento["taxa_execucao"] == 50.0
    assert "TESTE_RISCO" in comportamento["tipos_mais_executados"]

@pytest.mark.asyncio
async def test_classificacao_perfil_equilibrado(session: AsyncSession):
    tenant_id = TENANT_A_ID
    safra_id = uuid.uuid4()
    
    # Limpa histórico anterior
    await session.execute(delete(IAAlertaHistorico).where(IAAlertaHistorico.tenant_id == tenant_id))
    
    # Poucas interações ou interações mistas (5 alertas total)
    for i in range(5):
        alerta = IAAlertaHistorico(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            safra_id=safra_id,
            tipo_alerta="TESTE_MIX",
            titulo=f"Alerta {i}",
            mensagem="...",
            gravidade="media",
            ignorado=True if i == 0 else False,
            acao_executada=True if i == 1 else False,
            created_at=datetime.now(timezone.utc)
        )
        session.add(alerta)
    
    await session.commit()
    
    svc = AlertaInteligenteService(session, tenant_id)
    comportamento = await svc._analisar_comportamento_usuario()
    
    assert comportamento["perfil"] == "EQUILIBRADO"
    assert comportamento["taxa_execucao"] == 20.0 # 1 em 5
    assert comportamento["taxa_ignorado"] == 20.0 # 1 em 5
