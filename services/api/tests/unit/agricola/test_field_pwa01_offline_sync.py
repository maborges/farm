import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from core.exceptions import BusinessRuleError
from core.models import TenantUsuario, Usuario
from campo.models import DispositivoCampo
from agricola.caderno.schemas import EventoCadernoOfflinePayload, EvidenciaOfflinePayload
from agricola.caderno.service import CadernoCampoService


async def _ensure_caderno_offline_schema(session) -> None:
    for ddl in [
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS device_id UUID",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS unidade_produtiva_id UUID",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS client_created_at TIMESTAMP",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS client_updated_at TIMESTAMP",
        "ALTER TABLE caderno_campo_entradas ADD COLUMN IF NOT EXISTS payload_operacional JSON",
    ]:
        await session.execute(text(ddl))


async def _seed_context(session, tenant_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID, DispositivoCampo]:
    await _ensure_caderno_offline_schema(session)

    await session.execute(
        text(
            """
            INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at)
            VALUES (:id, :nome, :documento, true, 0, 10240, 'pt-BR', NOW(), NOW())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(tenant_id), "nome": f"Tenant {tenant_id.hex[:6]}", "documento": tenant_id.hex[:11]},
    )

    usuario = Usuario(
        id=uuid.uuid4(),
        email=f"campo-{tenant_id.hex[:8]}@agrosaas.local",
        username=f"campo_{tenant_id.hex[:8]}",
        nome_completo=f"Operador {tenant_id.hex[:6]}",
        ativo=True,
        is_superuser=False,
    )
    session.add(usuario)
    await session.flush()
    session.add(TenantUsuario(tenant_id=tenant_id, usuario_id=usuario.id, is_owner=True, status="ATIVO"))

    unidade_produtiva_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, 'Fazenda Campo', true, NOW(), NOW())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(unidade_produtiva_id), "tenant_id": str(tenant_id)},
    )

    talhao_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO cadastros_areas_rurais (id, tenant_id, unidade_produtiva_id, tipo, nome, area_hectares, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, :unidade_produtiva_id, 'TALHAO', 'Talhão Campo', 120.0, true, NOW(), NOW())
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": str(talhao_id),
            "tenant_id": str(tenant_id),
            "unidade_produtiva_id": str(unidade_produtiva_id),
        },
    )

    safra_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO safras (id, tenant_id, ano_safra, cultura, status, created_at, updated_at)
            VALUES (:id, :tenant_id, '2025/26', 'Soja', 'PLANEJADA', NOW(), NOW())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(safra_id), "tenant_id": str(tenant_id)},
    )

    await session.execute(
        text(
            """
            INSERT INTO safra_talhoes (id, tenant_id, safra_id, area_id, area_ha, principal, created_at)
            VALUES (:id, :tenant_id, :safra_id, :talhao_id, 120.0, true, NOW())
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "tenant_id": str(tenant_id),
            "safra_id": str(safra_id),
            "talhao_id": str(talhao_id),
        },
    )

    device = DispositivoCampo(
        tenant_id=tenant_id,
        user_id=usuario.id,
        nome="Tablet Campo",
        fazenda_ids=[unidade_produtiva_id],
        modulos=["agricola"],
        status="ATIVO",
        device_fingerprint="fp-" + tenant_id.hex[:8],
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    session.add(device)
    await session.commit()
    return safra_id, talhao_id, device


def _offline_event(
    *,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    talhao_id: uuid.UUID,
    device: DispositivoCampo,
    local_id: str | None = None,
    tipo_evento: str = "MONITORAMENTO",
) -> EventoCadernoOfflinePayload:
    now = datetime.now(timezone.utc)
    return EventoCadernoOfflinePayload(
        local_id=local_id or str(uuid.uuid4()),
        tenant_id=tenant_id,
        unidade_produtiva_id=device.fazenda_ids[0],
        safra_id=safra_id,
        talhao_id=talhao_id,
        tipo_evento=tipo_evento,  # type: ignore[arg-type]
        status="PENDENTE_SINCRONIZACAO",
        client_created_at=now,
        client_updated_at=now,
        device_id=str(device.id),
        usuario_id=device.user_id,
        origem_evento="PWA_OFFLINE",
        origem_tecnica="SYNC_PWA",
        evidencias=[
            EvidenciaOfflinePayload(
                tipo="foto",
                url="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD",
                latitude=-23.5,
                longitude=-46.6,
                data_captura=now,
                metadata={
                    "nome_arquivo": "foto-1.jpg",
                    "mime_type": "image/jpeg",
                    "tamanho": 1024,
                    "captured_at": now.isoformat(),
                },
            )
        ],
        payload_operacional={"descricao": "Evento offline", "data_registro": now.date().isoformat()},
    )


@pytest.mark.asyncio
async def test_sync_offline_evento_valido(session):
    tenant_id = uuid.uuid4()
    safra_id, talhao_id, device = await _seed_context(session, tenant_id)
    svc = CadernoCampoService(session, tenant_id)

    resultado = await svc.sincronizar_eventos_offline([_offline_event(tenant_id=tenant_id, safra_id=safra_id, talhao_id=talhao_id, device=device)], device=device)

    assert resultado[0].status == "SYNCED"
    assert resultado[0].server_id is not None


@pytest.mark.asyncio
async def test_sync_offline_evento_critico_fica_pendente_aprovacao(session):
    tenant_id = uuid.uuid4()
    safra_id, talhao_id, device = await _seed_context(session, tenant_id)
    svc = CadernoCampoService(session, tenant_id)

    resultado = await svc.sincronizar_eventos_offline(
        [_offline_event(tenant_id=tenant_id, safra_id=safra_id, talhao_id=talhao_id, device=device, tipo_evento="APLICACAO")],
        device=device,
    )

    assert resultado[0].status_evento == "PENDENTE_APROVACAO"


@pytest.mark.asyncio
async def test_sync_offline_idempotencia_por_device_e_local_id(session):
    tenant_id = uuid.uuid4()
    safra_id, talhao_id, device = await _seed_context(session, tenant_id)
    svc = CadernoCampoService(session, tenant_id)
    local_id = str(uuid.uuid4())
    evento = _offline_event(tenant_id=tenant_id, safra_id=safra_id, talhao_id=talhao_id, device=device, local_id=local_id)

    primeiro = await svc.sincronizar_eventos_offline([evento], device=device)
    segundo = await svc.sincronizar_eventos_offline([evento], device=device)

    assert primeiro[0].server_id == segundo[0].server_id


@pytest.mark.asyncio
async def test_sync_offline_isolamento_por_tenant(session):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    safra_a, talhao_a, device_a = await _seed_context(session, tenant_a)
    safra_b, talhao_b, device_b = await _seed_context(session, tenant_b)

    svc_a = CadernoCampoService(session, tenant_a)
    svc_b = CadernoCampoService(session, tenant_b)

    res_a = await svc_a.sincronizar_eventos_offline([_offline_event(tenant_id=tenant_a, safra_id=safra_a, talhao_id=talhao_a, device=device_a)], device=device_a)
    res_b = await svc_b.sincronizar_eventos_offline([_offline_event(tenant_id=tenant_b, safra_id=safra_b, talhao_id=talhao_b, device=device_b)], device=device_b)

    assert res_a[0].status == "SYNCED"
    assert res_b[0].status == "SYNCED"


@pytest.mark.asyncio
async def test_sync_offline_safra_ou_talhao_invalido(session):
    tenant_id = uuid.uuid4()
    safra_id, talhao_id, device = await _seed_context(session, tenant_id)
    svc = CadernoCampoService(session, tenant_id)

    evento = _offline_event(tenant_id=tenant_id, safra_id=uuid.uuid4(), talhao_id=talhao_id, device=device)
    resultado = await svc.sincronizar_eventos_offline([evento], device=device)
    assert resultado[0].status == "ERROR"
    assert "Safra inválida" in (resultado[0].erro or "")
