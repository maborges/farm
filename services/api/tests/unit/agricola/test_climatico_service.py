import pytest
from datetime import date, datetime

from agricola.climatico.service import ClimaService
from agricola.climatico.models import RegistroClima
from alert_engine.models import OperationalAlert, AlertStatus, Severity, Priority
from alert_engine.schemas import Domain, Category

pytestmark = pytest.mark.asyncio

async def test_get_resumo_climatico_sem_dados(tenant_session, tenant_id, unidade_produtiva_id):
    svc = ClimaService(tenant_session, tenant_id)
    
    resumo = await svc.get_resumo_climatico(unidade_produtiva_id)
    
    assert resumo.unidade_produtiva_id == unidade_produtiva_id
    assert resumo.status_operacional == "SEM_DADOS"
    assert resumo.data_registro is None

async def test_get_resumo_climatico_com_dados_normal(tenant_session, tenant_id, unidade_produtiva_id):
    svc = ClimaService(tenant_session, tenant_id)
    
    # Inserir RegistroClima
    registro = RegistroClima(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        data_registro=date.today(),
        temp_media_c=25.0,
        temp_min_c=20.0,
        temp_max_c=30.0,
        umidade_rel_pct=60.0,
        precipitacao_mm=10.0,
        vento_kmh=15.0,
        fonte="TEST_SOURCE"
    )
    tenant_session.add(registro)
    await tenant_session.commit()
    
    resumo = await svc.get_resumo_climatico(unidade_produtiva_id)
    
    assert resumo.status_operacional == "NORMAL"
    assert resumo.temperatura_atual == 25.0
    assert resumo.fonte == "TEST_SOURCE"
    assert resumo.alertas_ativos == 0

async def test_get_resumo_climatico_com_alertas(tenant_session, tenant_id, unidade_produtiva_id):
    svc = ClimaService(tenant_session, tenant_id)
    
    # Inserir RegistroClima
    registro = RegistroClima(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        data_registro=date.today(),
        temp_media_c=35.0,
        temp_min_c=20.0,
        temp_max_c=40.0,
        umidade_rel_pct=30.0,
        precipitacao_mm=0.0,
        vento_kmh=15.0,
        fonte="TEST_SOURCE"
    )
    tenant_session.add(registro)

    # Inserir Alerta
    alerta = OperationalAlert(
        tenant_id=tenant_id,
        domain=Domain.AGRICULTURE,
        category=Category.CLIMATICO,
        severity=Severity.CRITICAL,
        priority=Priority.HIGH,
        title="Alerta Teste",
        message="Teste",
        source_type="CLIMA_TEMPERATURA_EXTREMA",
        unidade_produtiva_id=unidade_produtiva_id, source_id=str(unidade_produtiva_id),
        status=AlertStatus.OPEN,
        created_at=datetime.utcnow(), trigger_type="RULE", dedupe_key="test", source_event_ids=[], source_indicator_ids=[]
    )
    tenant_session.add(alerta)
    await tenant_session.commit()
    
    resumo = await svc.get_resumo_climatico(unidade_produtiva_id)
    
    assert resumo.status_operacional == "CRITICO"
    assert resumo.alertas_ativos == 1

async def test_get_alertas_ativos(tenant_session, tenant_id, unidade_produtiva_id):
    svc = ClimaService(tenant_session, tenant_id)

    # Inserir Alerta
    alerta = OperationalAlert(
        tenant_id=tenant_id,
        domain=Domain.AGRICULTURE,
        category=Category.CLIMATICO,
        severity=Severity.WARNING,
        priority=Priority.NORMAL,
        title="Vento Forte",
        message="Ventos acima de 30km/h",
        source_type="CLIMA_VENTO_ALTO",
        unidade_produtiva_id=unidade_produtiva_id, source_id=str(unidade_produtiva_id),
        status=AlertStatus.OPEN,
        created_at=datetime.utcnow(), trigger_type="RULE", dedupe_key="test", source_event_ids=[], source_indicator_ids=[]
    )
    tenant_session.add(alerta)
    await tenant_session.commit()
    
    alertas = await svc.get_alertas_ativos(unidade_produtiva_id)
    
    assert len(alertas) == 1
    assert alertas[0].severity == "WARNING"
    assert alertas[0].source_type == "CLIMA_VENTO_ALTO"
