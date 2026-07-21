from datetime import datetime, timedelta
from types import SimpleNamespace
import uuid

from integracoes.erp.scheduler import (
    _create_job,
    _mark_job_failure,
    _mark_job_success,
    is_policy_due,
    supports_scheduled_runtime,
)
from integracoes.models import IntegrationFeature, IntegrationJobStatus, IntegrationJobTrigger


def test_politica_sem_execucao_anterior_vence_imediatamente() -> None:
    assert is_policy_due("*/15 * * * *", None, datetime(2026, 7, 18, 10, 0))


def test_politica_respeita_intervalo_configurado() -> None:
    now = datetime(2026, 7, 18, 10, 0)
    assert not is_policy_due("0 * * * *", now - timedelta(minutes=59), now)
    assert is_policy_due("0 * * * *", now - timedelta(hours=1), now)


def test_expressao_nao_homologada_nunca_e_executada() -> None:
    assert not is_policy_due("* * * * *", None, datetime(2026, 7, 18, 10, 0))


def test_agendador_respeita_capacidade_real_declarada_pelo_adapter() -> None:
    produtos = IntegrationFeature(settings_payload={"runtime_sync_modes": ["MANUAL", "AGENDADO"]})
    financeiro = IntegrationFeature(settings_payload={"runtime_sync_modes": ["MANUAL", "PULL"]})

    assert supports_scheduled_runtime(produtos)
    assert not supports_scheduled_runtime(financeiro)


def test_job_agendado_registra_policy_e_resultado() -> None:
    tenant_id = uuid.uuid4()
    scheduled = SimpleNamespace(
        config=SimpleNamespace(id=10),
        feature=SimpleNamespace(id=20, codigo="pessoas"),
        policy=SimpleNamespace(id=30),
        provider=SimpleNamespace(id=40),
    )

    job = _create_job(tenant_id, scheduled)
    _mark_job_success(job, {"processados": 7, "sucesso": True})

    assert job.tenant_id == tenant_id
    assert job.sync_policy_id == 30
    assert job.trigger_type == IntegrationJobTrigger.SCHEDULED.value
    assert job.status == IntegrationJobStatus.SUCCESS.value
    assert job.processados == 7
    assert job.sucessos == 7


def test_job_agendado_registra_falha() -> None:
    job = _create_job(
        uuid.uuid4(),
        SimpleNamespace(
            config=SimpleNamespace(id=10),
            feature=SimpleNamespace(id=20, codigo="pessoas"),
            policy=SimpleNamespace(id=30),
            provider=SimpleNamespace(id=40),
        ),
    )

    _mark_job_failure(job, RuntimeError("timeout ERP"))

    assert job.status == IntegrationJobStatus.FAILED.value
    assert job.erros == 1
    assert job.error_message == "timeout ERP"
