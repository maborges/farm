from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import text

from campo.models import DispositivoCampo
from campo.service import SyncService
from core.models import Usuario
from recommendations.enums import RecommendationActionType, RecommendationPriority, RecommendationSourceType, RecommendationStatus
from recommendations.models import RecommendationResult


pytestmark = pytest.mark.asyncio


async def test_sync_pull_inclui_recomendacoes_persistidas_sem_recalcular(session, tenant_id):
    await _bootstrap_context(session, tenant_id)
    unidade_produtiva_id = uuid.uuid4()
    await _insert_unidade_produtiva(session, tenant_id, unidade_produtiva_id)
    user = await _insert_user(session)
    device = await _insert_device(session, tenant_id, user.id, unidade_produtiva_id)
    await _insert_operational_recommendation(session, tenant_id, unidade_produtiva_id)
    await _insert_climate_recommendation(session, tenant_id, unidade_produtiva_id)

    with patch(
        "agricola.climatico.recommendation_service.ClimaRecommendationService.get_recomendacoes",
        side_effect=AssertionError("pull não deve recalcular recomendações climáticas"),
    ):
        data = await SyncService(session, tenant_id, device).pull(None)

    assert len(data["recomendacoes_operacionais"]) == 2
    assert data["recomendacoes_operacionais"][0]["provider_name"] == "campo"
    assert data["recomendacoes_operacionais"][1]["provider_name"] == "clima"
    assert len(data["recomendacoes_climaticas"]) == 4
    assert any(
        rec["unidade_produtiva_id"] == unidade_produtiva_id and rec["tipo_operacao"] == "PULVERIZACAO"
        for rec in data["recomendacoes_climaticas"]
    )


async def test_sync_pull_falha_em_recomendacoes_nao_bloqueia_sync_principal(session, tenant_id, monkeypatch):
    await _bootstrap_context(session, tenant_id)
    unidade_produtiva_id = uuid.uuid4()
    await _insert_unidade_produtiva(session, tenant_id, unidade_produtiva_id)
    user = await _insert_user(session)
    device = await _insert_device(session, tenant_id, user.id, unidade_produtiva_id)

    original_execute = session.execute

    async def execute_with_recommendation_failure(statement, *args, **kwargs):
        if "recommendation_results" in str(statement):
            raise RuntimeError("falha simulada ao ler recommendation_results")
        return await original_execute(statement, *args, **kwargs)

    monkeypatch.setattr(session, "execute", execute_with_recommendation_failure)

    data = await SyncService(session, tenant_id, device).pull(None)

    assert data["recomendacoes_operacionais"] == []
    assert data["recomendacoes_climaticas"] == []
    assert "sync_at" in data


async def _bootstrap_context(session, tenant_id: uuid.UUID) -> None:
    await session.execute(text(f"SET app.current_tenant_id = '{tenant_id}';"))
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Teste", "doc": str(tenant_id)[:11]},
    )


async def _insert_user(session) -> Usuario:
    user = Usuario(
        id=uuid.uuid4(),
        email=f"sync-recommendations-{uuid.uuid4().hex[:8]}@teste.com",
        username=f"sync_recommendations_{uuid.uuid4().hex[:8]}",
        nome_completo="Operador Sync Recommendations",
        senha_hash="hash",
        ativo=True,
        is_superuser=False,
    )
    session.add(user)
    await session.commit()
    return user


async def _insert_unidade_produtiva(session, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'Fazenda Recomendações', true, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(unidade_produtiva_id), "tenant_id": str(tenant_id)},
    )
    await session.commit()


async def _insert_device(session, tenant_id: uuid.UUID, user_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> DispositivoCampo:
    device = DispositivoCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        nome="Tablet Campo",
        fazenda_ids=[unidade_produtiva_id],
        modulos=["agricola"],
        status="ATIVO",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    session.add(device)
    await session.commit()
    return device


async def _insert_operational_recommendation(session, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> None:
    session.add(
        RecommendationResult(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain="FIELD",
            status=RecommendationStatus.CREATED.value,
            priority=RecommendationPriority.URGENT.value,
            source_type=RecommendationSourceType.INDICATOR.value,
            action_type=RecommendationActionType.OPEN_ROUTE.value,
            provider_name="campo",
            rule_code="CAMPO_SYNC_DESATUALIZADO",
            scope_type="DISPOSITIVO",
            scope_id=str(uuid.uuid4()),
            title="Sincronização do dispositivo desatualizada",
            summary="O dispositivo precisa sincronizar novamente.",
            rationale="A operação de campo depende de dados atualizados no aparelho.",
            dedupe_key=f"campo:{tenant_id}:{unidade_produtiva_id}:sync",
            source_signal_ids=[str(uuid.uuid4())],
            confidence=0.94,
            action_label="Sincronizar dispositivo",
            action_target="/sync",
            context={"origin": "test"},
            created_at=datetime.utcnow() - timedelta(hours=2),
            updated_at=datetime.utcnow() - timedelta(minutes=30),
        )
    )
    await session.commit()


async def _insert_climate_recommendation(session, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> None:
    session.add(
        RecommendationResult(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain="AGRICULTURE",
            status=RecommendationStatus.CREATED.value,
            priority=RecommendationPriority.HIGH.value,
            source_type=RecommendationSourceType.INDICATOR.value,
            action_type=RecommendationActionType.OPEN_ROUTE.value,
            provider_name="clima",
            rule_code="CLIMA_JANELA_PULVERIZACAO_DESFAVORAVEL",
            scope_type="CLIMA",
            scope_id=str(unidade_produtiva_id),
            title="Janela desfavorável para pulverização",
            summary="Vento acima do limite seguro.",
            rationale="A leitura climática persistida indica condição de risco.",
            dedupe_key=f"clima:{tenant_id}:{unidade_produtiva_id}:pulverizacao",
            source_signal_ids=[str(uuid.uuid4())],
            confidence=0.97,
            action_label="Aguardar janela",
            action_target="/agricola/clima",
            context={"vento_kmh": 25},
            created_at=datetime.utcnow() - timedelta(hours=1),
            updated_at=datetime.utcnow() - timedelta(minutes=15),
        )
    )
    await session.commit()
