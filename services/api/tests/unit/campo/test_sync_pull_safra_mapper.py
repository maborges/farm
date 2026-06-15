from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from datetime import date

import pytest

from agricola.caderno.schemas import EntradaCreate
from agricola.caderno.service import CadernoCampoService
from campo.models import DispositivoCampo, TarefaCampo
from campo.service import SyncService
from core.models import Usuario
from core.cadastros.propriedades.models import AreaRural
from sqlalchemy import text


pytestmark = pytest.mark.asyncio


async def test_sync_pull_nao_quebra_ao_carregar_safra(session, tenant_id):
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Teste", "doc": str(tenant_id)[:11]},
    )

    user = Usuario(
        id=uuid.uuid4(),
        email=f"sync-pull-{uuid.uuid4().hex[:8]}@teste.com",
        username=f"sync_pull_{uuid.uuid4().hex[:8]}",
        nome_completo="Operador Sync Pull",
        senha_hash="hash",
        ativo=True,
        is_superuser=False,
    )
    session.add(user)
    await session.commit()

    device = DispositivoCampo(
        tenant_id=tenant_id,
        user_id=user.id,
        nome="Tablet Campo",
        fazenda_ids=[uuid.uuid4()],
        modulos=["agricola"],
        status="ATIVO",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    session.add(device)
    await session.commit()

    svc = SyncService(session, tenant_id, device)
    data = await svc.pull(None)

    assert "sync_at" in data
    assert "safras" in data
    assert isinstance(data["safras"], list)


async def test_sync_pull_usa_area_hectares_manual_do_talhao(session, tenant_id):
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Teste", "doc": str(tenant_id)[:11]},
    )

    user = Usuario(
        id=uuid.uuid4(),
        email=f"sync-pull-area-{uuid.uuid4().hex[:8]}@teste.com",
        username=f"sync_pull_area_{uuid.uuid4().hex[:8]}",
        nome_completo="Operador Sync Pull",
        senha_hash="hash",
        ativo=True,
        is_superuser=False,
    )
    session.add(user)
    await session.commit()

    unidade_produtiva_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'Fazenda Pull', true, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(unidade_produtiva_id), "tenant_id": str(tenant_id)},
    )

    talhao = AreaRural(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo="TALHAO",
        nome="Talhão Pull",
        area_hectares=None,
        area_hectares_manual=123.4567,
        ativo=True,
    )
    session.add(talhao)

    device = DispositivoCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user.id,
        nome="Tablet Campo",
        fazenda_ids=[unidade_produtiva_id],
        modulos=["agricola"],
        status="ATIVO",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    session.add(device)
    await session.commit()

    svc = SyncService(session, tenant_id, device)
    data = await svc.pull(None)

    assert len(data["talhoes"]) == 1
    assert data["talhoes"][0]["area_ha"] == pytest.approx(123.4567, rel=1e-6)


async def test_sync_pull_inclui_tarefa_programada_futura_atribuida_ao_dispositivo(session, tenant_id):
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Teste", "doc": str(tenant_id)[:11]},
    )

    user = Usuario(
        id=uuid.uuid4(),
        email=f"sync-pull-task-{uuid.uuid4().hex[:8]}@teste.com",
        username=f"sync_pull_task_{uuid.uuid4().hex[:8]}",
        nome_completo="Operador Sync Pull",
        senha_hash="hash",
        ativo=True,
        is_superuser=False,
    )
    session.add(user)
    await session.commit()

    unidade_produtiva_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'Fazenda Pull', true, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(unidade_produtiva_id), "tenant_id": str(tenant_id)},
    )

    device = DispositivoCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user.id,
        nome="Tablet Campo",
        fazenda_ids=[unidade_produtiva_id],
        modulos=["agricola"],
        status="ATIVO",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    session.add(device)

    task = TarefaCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        dispositivo_id=device.id,
        user_id=user.id,
        client_id=str(uuid.uuid4()),
        origem="PROGRAMADA",
        status_execucao="PENDENTE",
        titulo="Tarefa Futura",
        data_programada=date.today() + timedelta(days=3),
        prioridade="NORMAL",
        type="APLICACAO_DEFENSIVO",
        module="agricola",
        unidade_produtiva_id=unidade_produtiva_id,
        status="PENDENTE",
        dados={},
        fotos=[],
        localizacao_status="INDISPONIVEL",
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
    )
    session.add(task)
    await session.commit()

    svc = SyncService(session, tenant_id, device)
    data = await svc.pull(None)

    assert len(data["tarefas_pendentes"]) == 1
    assert data["tarefas_pendentes"][0]["dispositivo_id"] == device.id


async def test_sync_pull_inclui_eventos_canonicos_do_caderno(session, tenant_id):
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Teste", "doc": str(tenant_id)[:11]},
    )

    user = Usuario(
        id=uuid.uuid4(),
        email=f"sync-pull-caderno-{uuid.uuid4().hex[:8]}@teste.com",
        username=f"sync_pull_caderno_{uuid.uuid4().hex[:8]}",
        nome_completo="Operador Sync Pull",
        senha_hash="hash",
        ativo=True,
        is_superuser=False,
    )
    session.add(user)
    await session.commit()

    safra_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    talhao_id = uuid.uuid4()

    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'Fazenda Pull', true, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(unidade_produtiva_id), "tenant_id": str(tenant_id)},
    )
    await session.execute(
        text(
            """
            INSERT INTO safras (id, tenant_id, ano_safra, cultura, status, created_at, updated_at)
            VALUES (:id, :tenant_id, '2025/26', 'Soja', 'PLANEJADA', now(), now())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(safra_id), "tenant_id": str(tenant_id)},
    )
    await session.execute(
        text(
            """
            INSERT INTO cadastros_areas_rurais (id, tenant_id, unidade_produtiva_id, tipo, nome, area_hectares, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, :unidade_produtiva_id, 'TALHAO', 'Talhão Pull', 50.0, true, now(), now())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(talhao_id), "tenant_id": str(tenant_id), "unidade_produtiva_id": str(unidade_produtiva_id)},
    )

    device = DispositivoCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user.id,
        nome="Tablet Campo",
        fazenda_ids=[unidade_produtiva_id],
        modulos=["agricola"],
        status="ATIVO",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    session.add(device)
    await session.commit()

    caderno_svc = CadernoCampoService(session, tenant_id)
    local_id = f"local-{uuid.uuid4()}"
    entrada = await caderno_svc.criar_entrada(
        EntradaCreate(
            safra_id=safra_id,
            talhao_id=talhao_id,
            tipo="OBSERVACAO",
            tipo_evento="OBSERVACAO",
            descricao="Evento oficial sincronizado",
            data_registro=date.today(),
            origem_evento="PWA_OFFLINE",
            origem_id=local_id,
            origem_tecnica="SYNC_PWA",
            status_evento="PENDENTE_APROVACAO",
        ),
        usuario_id=user.id,
    )
    await session.execute(
        text("UPDATE caderno_campo_entradas SET device_id = :device_id WHERE id = :entrada_id"),
        {"device_id": str(device.id), "entrada_id": str(entrada.id)},
    )
    await caderno_svc.adicionar_foto(entrada.id, "https://example.com/foto.jpg")
    await caderno_svc.alterar_status_evento(
        entrada.id,
        novo_status="APROVADO",
        justificativa="Conferido",
        usuario_id=user.id,
        usuario_role="agronomo",
    )
    await session.commit()

    svc = SyncService(session, tenant_id, device)
    data = await svc.pull(None)

    assert len(data["eventos_caderno_oficiais"]) == 1
    assert data["eventos_caderno_oficiais"][0]["server_id"] == str(entrada.id)
    assert data["eventos_caderno_oficiais"][0]["local_id"] == local_id
    assert data["eventos_caderno_oficiais"][0]["device_id"] == str(device.id)
    assert data["eventos_caderno_oficiais"][0]["status_evento"] == "APROVADO"
    assert data["eventos_caderno_oficiais"][0]["justificativa"] == "Conferido"


async def test_sync_pull_reflete_tarefa_invalidada_recente(session, tenant_id):
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Teste", "doc": str(tenant_id)[:11]},
    )

    user = Usuario(
        id=uuid.uuid4(),
        email=f"sync-pull-invalidada-{uuid.uuid4().hex[:8]}@teste.com",
        username=f"sync_pull_invalidada_{uuid.uuid4().hex[:8]}",
        nome_completo="Operador Sync Pull",
        senha_hash="hash",
        ativo=True,
        is_superuser=False,
    )
    session.add(user)
    await session.commit()

    unidade_produtiva_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'Fazenda Pull', true, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(unidade_produtiva_id), "tenant_id": str(tenant_id)},
    )

    device = DispositivoCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user.id,
        nome="Tablet Campo",
        fazenda_ids=[unidade_produtiva_id],
        modulos=["agricola"],
        status="ATIVO",
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    session.add(device)

    task = TarefaCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        dispositivo_id=device.id,
        user_id=user.id,
        client_id=str(uuid.uuid4()),
        origem="PROGRAMADA",
        status_execucao="INVALIDADA",
        titulo="Tarefa Invalidada",
        data_programada=date.today(),
        prioridade="NORMAL",
        type="APLICACAO_DEFENSIVO",
        module="agricola",
        unidade_produtiva_id=unidade_produtiva_id,
        status="PENDENTE",
        dados={},
        fotos=[],
        localizacao_status="INDISPONIVEL",
        invalidado_em=datetime.utcnow(),
        client_created_at=datetime.utcnow(),
        client_updated_at=datetime.utcnow(),
    )
    session.add(task)
    await session.commit()

    svc = SyncService(session, tenant_id, device)
    data = await svc.pull(datetime.utcnow() - timedelta(days=1))

    assert len(data["tarefas_pendentes"]) == 1
    assert data["tarefas_pendentes"][0]["status_execucao"] == "INVALIDADA"
