import uuid
from datetime import date, datetime, timedelta, timezone
import pytest
from sqlalchemy import select, and_, text
from core.exceptions import BusinessRuleError
from core.models import TenantUsuario, Usuario
from campo.models import DispositivoCampo
from agricola.caderno.schemas import EventoCadernoOfflinePayload, EvidenciaOfflinePayload
from agricola.caderno.service import CadernoCampoService
from agricola.caderno.models import EPIEntrega, CadernoCampoEntrada
from rh.models import ColaboradorRH
from core.cadastros.pessoas.models import Pessoa


async def _criar_colaborador(session, tenant_id: uuid.UUID, nome: str) -> ColaboradorRH:
    """ColaboradorRH é um papel sobre Pessoa (migration 20260724c) — nome/cpf
    não existem mais na tabela rh_colaboradores, sempre via Pessoa."""
    pessoa = Pessoa(id=uuid.uuid4(), tenant_id=tenant_id, tipo="PF", nome_exibicao=nome)
    session.add(pessoa)
    await session.flush()
    colaborador = ColaboradorRH(id=uuid.uuid4(), tenant_id=tenant_id, pessoa_id=pessoa.id, ativo=True)
    session.add(colaborador)
    return colaborador


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


def _offline_epi_event(
    *,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    talhao_id: uuid.UUID,
    device: DispositivoCampo,
    colaborador_id: uuid.UUID,
    local_id: str | None = None,
) -> EventoCadernoOfflinePayload:
    now = datetime.now(timezone.utc)
    return EventoCadernoOfflinePayload(
        local_id=local_id or str(uuid.uuid4()),
        tenant_id=tenant_id,
        unidade_produtiva_id=device.fazenda_ids[0],
        safra_id=safra_id,
        talhao_id=talhao_id,
        tipo_evento="EPI_ENTREGA",  # type: ignore[arg-type]
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
                    "nome_arquivo": "assinatura.png",
                    "mime_type": "image/png",
                    "tamanho": 1024,
                    "captured_at": now.isoformat(),
                },
            )
        ],
        payload_operacional={
            "descricao": "Entrega de EPI: Óculos de Proteção",
            "trabalhador_id": str(colaborador_id),
            "nome_trabalhador": "João da Silva",
            "epi_tipo": "Óculos de Proteção",
            "quantidade": 2,
            "data_entrega": now.date().isoformat(),
            "validade": (now.date() + timedelta(days=365)).isoformat(),
        },
    )


@pytest.mark.asyncio
async def test_sync_offline_epi_entrega(session):
    tenant_id = uuid.uuid4()
    safra_id, talhao_id, device = await _seed_context(session, tenant_id)
    
    # Seed ColaboradorRH
    colaborador = await _criar_colaborador(session, tenant_id, "João da Silva")
    await session.commit()

    svc = CadernoCampoService(session, tenant_id)
    local_id = str(uuid.uuid4())
    event = _offline_epi_event(
        tenant_id=tenant_id,
        safra_id=safra_id,
        talhao_id=talhao_id,
        device=device,
        colaborador_id=colaborador.id,
        local_id=local_id,
    )

    resultado = await svc.sincronizar_eventos_offline([event], device=device)
    assert resultado[0].status == "SYNCED"
    server_id = resultado[0].server_id
    assert server_id is not None

    # Verify CadernoCampoEntrada was created
    stmt_entrada = select(CadernoCampoEntrada).where(CadernoCampoEntrada.id == server_id)
    entrada = (await session.execute(stmt_entrada)).scalar_one()
    assert entrada.tipo == "EPI_ENTREGA"
    assert entrada.origem_evento == "EPI_ENTREGA"
    assert entrada.origem_id == local_id

    # Verify EPIEntrega was created
    stmt_epi = select(EPIEntrega).where(EPIEntrega.id == uuid.UUID(local_id))
    epi = (await session.execute(stmt_epi)).scalar_one()
    assert epi.tenant_id == tenant_id
    assert epi.trabalhador_id == colaborador.id
    assert epi.nome_trabalhador == "João da Silva"
    assert epi.epi_tipo == "Óculos de Proteção"
    assert epi.quantidade == 2
    assert epi.assinatura_url is None

    # Test evidence upload to link signature_url
    foto = await svc.upload_evidencia_offline(
        entrada_id=server_id,
        device=device,
        local_evidence_id="ev-signature-0",
        file_content=b"dummy_image_content",
        filename="assinatura.png",
        mime_type="image/png",
        size_bytes=len(b"dummy_image_content"),
        captured_at=datetime.utcnow(),
        latitude=-23.5,
        longitude=-46.6,
    )
    
    assert foto.url is not None
    
    # Refresh epi and verify signature_url is linked
    await session.refresh(epi)
    assert epi.assinatura_url == foto.url


@pytest.mark.asyncio
async def test_epi_sync_tenant_isolation(session):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    
    safra_a, talhao_a, device_a = await _seed_context(session, tenant_a)
    colab_a = await _criar_colaborador(session, tenant_a, "Trabalhador A")

    safra_b, talhao_b, device_b = await _seed_context(session, tenant_b)
    colab_b = await _criar_colaborador(session, tenant_b, "Trabalhador B")

    await session.commit()

    svc_a = CadernoCampoService(session, tenant_a)
    local_id = str(uuid.uuid4())
    event_a = _offline_epi_event(
        tenant_id=tenant_a,
        safra_id=safra_a,
        talhao_id=talhao_a,
        device=device_a,
        colaborador_id=colab_a.id,
        local_id=local_id,
    )

    # Sync under tenant A
    await svc_a.sincronizar_eventos_offline([event_a], device=device_a)

    # Verify it exists in Tenant A
    stmt_epi_a = select(EPIEntrega).where(and_(EPIEntrega.id == uuid.UUID(local_id), EPIEntrega.tenant_id == tenant_a))
    epi_a = (await session.execute(stmt_epi_a)).scalar_one_or_none()
    assert epi_a is not None

    # Verify it does not exist under Tenant B
    stmt_epi_b = select(EPIEntrega).where(and_(EPIEntrega.id == uuid.UUID(local_id), EPIEntrega.tenant_id == tenant_b))
    epi_b = (await session.execute(stmt_epi_b)).scalar_one_or_none()
    assert epi_b is None
