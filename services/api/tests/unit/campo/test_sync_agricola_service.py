from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

from agricola.safras.models import Safra, SafraTalhao
from campo.models import TarefaCampo
from campo.schemas import SyncPullResponse
from campo.service import CampoAgricolaSyncService, SyncService
from core.cadastros.propriedades.models import AreaRural


pytestmark = pytest.mark.asyncio


async def _ensure_tenant_and_unit(session, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Campo", "doc": str(tenant_id)[:11]},
    )
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'Fazenda Campo', true, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(unidade_produtiva_id), "tenant_id": str(tenant_id)},
    )
    await session.commit()


async def _ensure_user(session, user_id: uuid.UUID, suffix: str) -> None:
    await session.execute(
        text(
            "INSERT INTO usuarios (id, email, username, nome_completo, senha_hash, ativo, is_superuser, created_at, updated_at) "
            "VALUES (:id, :email, :username, :nome, 'hash', true, false, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": str(user_id),
            "email": f"{suffix}@teste.com",
            "username": suffix,
            "nome": f"Usuario {suffix}",
        },
    )
    await session.commit()


async def test_sync_pull_response_preserva_animais_e_colaboradores():
    payload = SyncPullResponse.model_validate(
        {
            "sync_at": datetime.utcnow(),
            "safras": [],
            "fazendas": [],
            "talhoes": [],
            "lotes": [],
            "animais": [
                {
                    "id": uuid.uuid4(),
                    "unidade_produtiva_id": uuid.uuid4(),
                }
            ],
            "insumos": [],
            "colaboradores": [
                {
                    "id": uuid.uuid4(),
                    "nome": "Maria Operadora",
                }
            ],
            "tarefas_pendentes": [],
            "eventos_caderno_oficiais": [],
            "recomendacoes_operacionais": [],
            "recomendacoes_climaticas": [],
            "tombstones": {},
        }
    )

    assert len(payload.animais) == 1
    assert len(payload.colaboradores) == 1


async def test_sync_pull_filtra_tarefa_programada_por_operador(session, tenant_id):
    unidade_produtiva_id = uuid.uuid4()
    await _ensure_tenant_and_unit(session, tenant_id, unidade_produtiva_id)

    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    await _ensure_user(session, user_a, "user_a_sync_pull")
    await _ensure_user(session, user_b, "user_b_sync_pull")

    from campo.models import DispositivoCampo

    device_a = DispositivoCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_a,
        nome="Tablet A",
        fazenda_ids=[unidade_produtiva_id],
        modulos=["agricola"],
        status="ATIVO",
        expires_at=datetime.utcnow(),
    )
    session.add(device_a)
    session.add(
        TarefaCampo(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            user_id=user_b,
            operador_id=user_b,
            origem="PROGRAMADA",
            status_execucao="PENDENTE",
            titulo="Aplicação operador B",
            prioridade="NORMAL",
            type="APLICACAO_DEFENSIVO",
            module="agricola",
            unidade_produtiva_id=unidade_produtiva_id,
            data_programada=datetime.utcnow().date(),
            status="PENDENTE",
            dados={},
            fotos=[],
            localizacao_status="INDISPONIVEL",
        )
    )
    await session.commit()

    data = await SyncService(session, tenant_id, device_a).pull(None)

    assert data["tarefas_pendentes"] == []


async def test_materializa_aplicacao_do_campo_em_operacao_agricola(session, tenant_id):
    unidade_produtiva_id = uuid.uuid4()
    await _ensure_tenant_and_unit(session, tenant_id, unidade_produtiva_id)

    talhao = AreaRural(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo="TALHAO",
        nome="Talhão 01",
        area_hectares_manual=12.5,
        ativo=True,
    )
    safra = Safra(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        ano_safra="2026/2027",
        status="PLANTIO",
    )
    session.add_all([talhao, safra])
    await session.commit()
    session.add(
        SafraTalhao(
            tenant_id=tenant_id,
            safra_id=safra.id,
            area_id=talhao.id,
            area_ha=12.5,
            principal=True,
        )
    )
    user_id = uuid.uuid4()
    operador_id = uuid.uuid4()
    await _ensure_user(session, user_id, "user_aplicacao_sync")
    await _ensure_user(session, operador_id, "operador_aplicacao_sync")
    task = TarefaCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        operador_id=operador_id,
        origem="MANUAL",
        status_execucao="CONCLUIDA",
        type="APLICACAO_DEFENSIVO",
        module="agricola",
        unidade_produtiva_id=unidade_produtiva_id,
        area_rural_id=talhao.id,
        status="PENDENTE",
        dados={
            "safra_id": str(safra.id),
            "insumo_id": str(uuid.uuid4()),
            "quantidade": 2.4,
            "unidade": "L/ha",
        },
        fotos=[],
        localizacao_status="DISPONIVEL",
        concluida_em=datetime.utcnow(),
    )
    session.add(task)
    await session.commit()

    operacao_id = uuid.uuid4()
    with patch("agricola.operacoes.service.OperacaoService.criar", new=AsyncMock(return_value=SimpleNamespace(id=operacao_id))):
        result = await CampoAgricolaSyncService(session, tenant_id).processar_tarefa_campo(task.id)

    refreshed = await session.get(TarefaCampo, task.id)
    assert result["status"] == "SYNCED"
    assert result["operacao_id"] == str(operacao_id)
    assert refreshed is not None
    assert refreshed.dados["sync_agricola"]["operacao_id"] == str(operacao_id)


async def test_materializa_colheita_do_campo_em_romaneio(session, tenant_id):
    unidade_produtiva_id = uuid.uuid4()
    await _ensure_tenant_and_unit(session, tenant_id, unidade_produtiva_id)

    talhao = AreaRural(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        tipo="TALHAO",
        nome="Talhão 02",
        area_hectares_manual=8.0,
        ativo=True,
    )
    safra = Safra(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        ano_safra="2026/2027",
        status="COLHEITA",
    )
    session.add_all([talhao, safra])
    await session.commit()
    session.add(
        SafraTalhao(
            tenant_id=tenant_id,
            safra_id=safra.id,
            area_id=talhao.id,
            area_ha=8.0,
            principal=True,
        )
    )
    user_id = uuid.uuid4()
    operador_id = uuid.uuid4()
    await _ensure_user(session, user_id, "user_colheita_sync")
    await _ensure_user(session, operador_id, "operador_colheita_sync")
    task = TarefaCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user_id,
        operador_id=operador_id,
        origem="MANUAL",
        status_execucao="CONCLUIDA",
        type="COLHEITA_REGISTRO",
        module="agricola",
        unidade_produtiva_id=unidade_produtiva_id,
        area_rural_id=talhao.id,
        status="PENDENTE",
        dados={
            "safra_id": str(safra.id),
            "quantidade": 40,
            "unidade": "sc",
            "umidade_perc": 14,
            "preco_saca": 550,
        },
        fotos=[],
        localizacao_status="DISPONIVEL",
        concluida_em=datetime.utcnow(),
    )
    session.add(task)
    await session.commit()

    romaneio_id = uuid.uuid4()
    fake_romaneio = SimpleNamespace(id=romaneio_id, sacas_60kg=40.0, receita_total=22000.0)
    with patch("agricola.romaneios.service.RomaneioService.criar", new=AsyncMock(return_value=fake_romaneio)):
        result = await CampoAgricolaSyncService(session, tenant_id).processar_tarefa_campo(task.id)

    refreshed = await session.get(TarefaCampo, task.id)
    assert result["status"] == "SYNCED"
    assert result["romaneio_id"] == str(romaneio_id)
    assert "receita_financeira" in result["efeitos"]
    assert refreshed is not None
    assert refreshed.dados["sync_agricola"]["romaneio_id"] == str(romaneio_id)
