from __future__ import annotations

import uuid
from unittest.mock import create_autospec

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from integracoes.erp.policy_service import (
    ErpSyncPolicyService,
    ErpSyncPolicyValidationError,
)
from integracoes.erp.schemas import ErpSyncPolicyUpdate
from integracoes.models import IntegrationFeature, IntegrationSyncPolicy, TenantIntegracao


def _feature(*modes: str) -> IntegrationFeature:
    return IntegrationFeature(
        codigo="produtos",
        nome="Produtos",
        settings_payload={"runtime_sync_modes": list(modes)},
    )


def test_politica_agendada_exige_frequencia() -> None:
    with pytest.raises(ValidationError):
        ErpSyncPolicyUpdate(mode="AGENDADO")


def test_produtos_aceita_agendamento_suportado() -> None:
    payload = ErpSyncPolicyUpdate(mode="AGENDADO", trigger_expression="0 * * * *")
    ErpSyncPolicyService._validar(_feature("MANUAL", "AGENDADO"), payload)


def test_fluxo_legado_preserva_modo_pull_sem_inventar_agendamento() -> None:
    payload = ErpSyncPolicyUpdate(mode="PULL")
    ErpSyncPolicyService._validar(_feature("MANUAL", "PULL"), payload)
    assert payload.trigger_expression is None


def test_pessoas_manual_nao_aceita_escopo_de_importacao_total() -> None:
    payload = ErpSyncPolicyUpdate(mode="MANUAL", record_scope="ALL_EXTERNAL")

    with pytest.raises(ErpSyncPolicyValidationError, match="automático"):
        ErpSyncPolicyService._validar(_feature("MANUAL", "AGENDADO"), payload)


def test_pessoas_agendada_aceita_somente_vinculados_ou_total() -> None:
    for scope in ("LINKED_ONLY", "ALL_EXTERNAL"):
        payload = ErpSyncPolicyUpdate(
            mode="AGENDADO",
            record_scope=scope,
            trigger_expression="0 * * * *",
        )
        ErpSyncPolicyService._validar(_feature("MANUAL", "AGENDADO"), payload)


def test_rejeita_modo_ou_agenda_fora_do_contrato_do_provider() -> None:
    with pytest.raises(ErpSyncPolicyValidationError):
        ErpSyncPolicyService._validar(
            _feature("MANUAL"),
            ErpSyncPolicyUpdate(mode="AGENDADO", trigger_expression="0 * * * *"),
        )
    with pytest.raises(ErpSyncPolicyValidationError):
        ErpSyncPolicyService._validar(
            _feature("MANUAL", "AGENDADO"),
            ErpSyncPolicyUpdate(mode="AGENDADO", trigger_expression="* * * * *"),
        )


@pytest.mark.asyncio
async def test_execucao_manual_respeita_estado_e_modo_da_politica(monkeypatch) -> None:
    service = ErpSyncPolicyService(session=create_autospec(AsyncSession, instance=True))
    tenant_id = uuid.uuid4()
    feature = _feature("MANUAL", "AGENDADO")
    feature.habilitada = True
    policy = IntegrationSyncPolicy(mode="MANUAL", ativa=True)
    config = TenantIntegracao()

    async def obter(*_args):
        return policy, feature, config

    monkeypatch.setattr(service, "_obter", obter)
    await service.garantir_execucao_manual(tenant_id, "produtos")

    policy.ativa = False
    with pytest.raises(ErpSyncPolicyValidationError, match="desativada"):
        await service.garantir_execucao_manual(tenant_id, "produtos")

    policy.ativa = True
    policy.mode = "AGENDADO"
    with pytest.raises(ErpSyncPolicyValidationError, match="agendada"):
        await service.garantir_execucao_manual(tenant_id, "produtos")


@pytest.mark.asyncio
async def test_execucao_manual_de_pessoas_orienta_importacao_por_id(monkeypatch) -> None:
    service = ErpSyncPolicyService(session=create_autospec(AsyncSession, instance=True))
    feature = _feature("MANUAL", "AGENDADO")
    feature.codigo = "pessoas"
    feature.habilitada = True
    policy = IntegrationSyncPolicy(mode="MANUAL", ativa=True)

    async def obter(*_args):
        return policy, feature, TenantIntegracao()

    monkeypatch.setattr(service, "_obter", obter)

    with pytest.raises(ErpSyncPolicyValidationError, match="ID do ERP"):
        await service.garantir_execucao_manual(uuid.uuid4(), "pessoas")


def test_endpoint_da_politica_e_resolvido_sem_duplicar_gateway() -> None:
    metadata = {
        "path": "/gateway/v1/mge/service.sbr",
        "query": {
            "serviceName": "CRUDServiceProvider.loadRecords",
            "outputType": "json",
        },
    }

    endpoint = ErpSyncPolicyService._resolve_endpoint_url(
        "https://api.sankhya.com.br/gateway/v1",
        metadata,
    )

    assert endpoint == (
        "https://api.sankhya.com.br/gateway/v1/mge/service.sbr"
        "?serviceName=CRUDServiceProvider.loadRecords&outputType=json"
    )
