import pytest
from datetime import date, datetime
import uuid

from agricola.climatico.recommendation_service import ClimaRecommendationService
from agricola.climatico.models import RegistroClima
from alert_engine.models import OperationalAlert, AlertStatus, Severity, Priority
from alert_engine.schemas import Domain, Category

pytestmark = pytest.mark.asyncio


async def test_recomendacao_sem_dados(tenant_session, tenant_id, unidade_produtiva_id):
    svc = ClimaRecommendationService(tenant_session, tenant_id)
    recs = await svc.get_recomendacoes(unidade_produtiva_id)

    assert len(recs) == 4
    tipos = {r.tipo_operacao: r for r in recs}
    
    assert tipos["PULVERIZACAO"].status == "SEM_DADOS"
    assert tipos["COLHEITA"].status == "SEM_DADOS"
    assert tipos["ADUBACAO"].status == "ATENCAO"
    assert tipos["GERAL"].status == "SEM_DADOS"


async def test_recomendacao_clima_normal(tenant_session, tenant_id, unidade_produtiva_id):
    svc = ClimaRecommendationService(tenant_session, tenant_id)
    
    registro = RegistroClima(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        data_registro=date.today(),
        temp_media_c=25.0,
        temp_min_c=20.0,
        temp_max_c=30.0,
        umidade_rel_pct=60.0,
        precipitacao_mm=0.0,
        vento_kmh=10.0,
        fonte="TEST_SOURCE"
    )
    tenant_session.add(registro)
    await tenant_session.commit()
    
    recs = await svc.get_recomendacoes(unidade_produtiva_id)
    tipos = {r.tipo_operacao: r for r in recs}

    assert tipos["PULVERIZACAO"].status == "RECOMENDADO"
    assert tipos["COLHEITA"].status == "RECOMENDADO"
    assert tipos["ADUBACAO"].status == "RECOMENDADO"
    assert tipos["GERAL"].status == "FAVORAVEL"


async def test_recomendacao_vento_alto(tenant_session, tenant_id, unidade_produtiva_id):
    svc = ClimaRecommendationService(tenant_session, tenant_id)
    
    registro = RegistroClima(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        data_registro=date.today(),
        vento_kmh=30.0, # acima de 25
        fonte="TEST_SOURCE"
    )
    tenant_session.add(registro)
    await tenant_session.commit()
    
    recs = await svc.get_recomendacoes(unidade_produtiva_id)
    tipos = {r.tipo_operacao: r for r in recs}

    assert tipos["PULVERIZACAO"].status == "NAO_RECOMENDADO"
    assert tipos["PULVERIZACAO"].severidade == "CRITICAL"
    assert tipos["GERAL"].status == "CRITICO"


async def test_recomendacao_alerta_chuva(tenant_session, tenant_id, unidade_produtiva_id):
    svc = ClimaRecommendationService(tenant_session, tenant_id)
    
    registro = RegistroClima(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        data_registro=date.today(),
        vento_kmh=10.0,
        precipitacao_mm=15.0,
        fonte="TEST_SOURCE"
    )
    tenant_session.add(registro)

    alerta = OperationalAlert(
        tenant_id=tenant_id,
        domain=Domain.AGRICULTURE,
        category=Category.CLIMATICO,
        severity=Severity.WARNING,
        priority=Priority.NORMAL,
        title="Vento Forte",
        message="Ventos acima de 30km/h",
        source_type="CLIMA_CHUVA_RECENTE",
        unidade_produtiva_id=unidade_produtiva_id, source_id=str(unidade_produtiva_id),
        status=AlertStatus.OPEN,
        created_at=datetime.utcnow(), trigger_type="RULE", dedupe_key="test", source_event_ids=[], source_indicator_ids=[]
    )
    tenant_session.add(alerta)
    await tenant_session.commit()
    
    recs = await svc.get_recomendacoes(unidade_produtiva_id)
    tipos = {r.tipo_operacao: r for r in recs}

    assert tipos["PULVERIZACAO"].status == "ATENCAO"
    assert tipos["COLHEITA"].status == "ATENCAO"
    assert tipos["ADUBACAO"].status == "ATENCAO"
    assert tipos["GERAL"].status == "ATENCAO"
