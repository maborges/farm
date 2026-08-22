import pytest
from datetime import date, datetime
from sqlalchemy import func, select

from agricola.climatico.service import ClimaService
from agricola.climatico.events import ClimaSyncRealizado, PrevisaoClimaSyncRealizado
from agricola.climatico.models import PrevisaoClima, RegistroClima
from agricola.climatico.subscribers import ClimaEventSubscriber, PrevisaoClimaEventSubscriber
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


async def test_subscriber_clima_e_idempotente(tenant_session, tenant_id, unidade_produtiva_id):
    subscriber = ClimaEventSubscriber(tenant_session)
    event = ClimaSyncRealizado(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        provider="OPENWEATHER",
        source_type="OPENWEATHER",
        domain=Domain.AGRICULTURE,
        temperatura=25.0,
        chuva_mm=2.0,
        umidade=60.0,
        vento_kmh=10.0,
        occurred_at=datetime(2026, 8, 20, 12, 0),
    )

    first = await subscriber.handle(event)
    second = await subscriber.handle(event)

    count = await tenant_session.scalar(
        select(func.count(RegistroClima.id)).where(
            RegistroClima.tenant_id == tenant_id,
            RegistroClima.unidade_produtiva_id == unidade_produtiva_id,
        )
    )
    assert first.created == 1
    assert second.updated == 1
    assert count == 1


async def test_subscriber_previsao_valida_unidade_e_atualiza(tenant_session, tenant_id, unidade_produtiva_id):
    subscriber = PrevisaoClimaEventSubscriber(tenant_session)
    event = PrevisaoClimaSyncRealizado(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        provider="OPENWEATHER",
        source_type="OPENWEATHER",
        domain=Domain.AGRICULTURE,
        occurred_at=datetime(2026, 8, 20, 12, 0),
        previsoes=[
            {
                "data_previsao": "2026-08-21",
                "precipitacao_mm": 4.0,
                "temp_max_c": 30.0,
                "temp_min_c": 18.0,
                "probabilidade_chuva_pct": 60.0,
            }
        ],
    )

    result = await subscriber.handle(event)
    registro = await tenant_session.scalar(
        select(PrevisaoClima).where(
            PrevisaoClima.tenant_id == tenant_id,
            PrevisaoClima.unidade_produtiva_id == unidade_produtiva_id,
        )
    )
    assert result.created == 1
    assert registro is not None
    assert float(registro.precipitacao_mm) == 4.0
