from __future__ import annotations

import uuid
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text

from campo.schemas import SyncPullResponse
from campo.service import SyncService
from campo.models import DispositivoCampo

pytestmark = pytest.mark.asyncio

async def _ensure_tenant_and_unit(session, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Pessoas", "doc": str(tenant_id)[:11]},
    )
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'Fazenda Pessoas', true, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(unidade_produtiva_id), "tenant_id": str(tenant_id)},
    )
    await session.commit()

async def _seed_pessoa_and_relacionamentos(
    session,
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID | None,
    nome_exibicao: str,
    codigo_papel: str,
    ativo_desde: date | None = None,
    ativo_ate: date | None = None,
    pessoa_ativo: bool = True,
    tipo_ativo: bool = True,
) -> uuid.UUID:
    pessoa_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_pessoas (id, tenant_id, tipo, nome_exibicao, base_legal, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'PF', :nome, 'CONTRATO', :ativo, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(pessoa_id), "tenant_id": str(tenant_id), "nome": nome_exibicao, "ativo": pessoa_ativo},
    )

    tipo_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_tipos_relacionamento (id, tenant_id, codigo, nome, sistema, ativo, cor, icone) "
            "VALUES (:id, :tenant_id, :codigo, :codigo, false, :ativo, '#6B7280', 'user') "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tipo_id), "tenant_id": str(tenant_id), "codigo": codigo_papel, "ativo": tipo_ativo},
    )

    await session.execute(
        text(
            "INSERT INTO cadastros_pessoa_relacionamentos (id, pessoa_id, tipo_id, unidade_produtiva_id, ativo_desde, ativo_ate) "
            "VALUES (:id, :pessoa_id, :tipo_id, :up_id, :desde, :ate) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": str(uuid.uuid4()),
            "pessoa_id": str(pessoa_id),
            "tipo_id": str(tipo_id),
            "up_id": str(unidade_produtiva_id) if unidade_produtiva_id else None,
            "desde": ativo_desde,
            "ate": ativo_ate,
        },
    )
    await session.commit()
    return pessoa_id

async def test_sync_pull_pessoas_operacionais_valida(session, tenant_id):
    unidade_produtiva_id = uuid.uuid4()
    await _ensure_tenant_and_unit(session, tenant_id, unidade_produtiva_id)

    # 1. Vigente, mesma UP -> deve aparecer
    p1 = await _seed_pessoa_and_relacionamentos(
        session, tenant_id, unidade_produtiva_id, "João Vigente", "OPERADOR"
    )

    # 2. Encerrado no passado -> NÃO deve aparecer
    p2 = await _seed_pessoa_and_relacionamentos(
        session, tenant_id, unidade_produtiva_id, "Maria Encerrada", "MOTORISTA",
        ativo_ate=date.today() - timedelta(days=2)
    )

    # 3. UP não autorizada -> NÃO deve aparecer
    outra_up = uuid.uuid4()
    await _ensure_tenant_and_unit(session, tenant_id, outra_up)
    p3 = await _seed_pessoa_and_relacionamentos(
        session, tenant_id, outra_up, "José Outra UP", "GERENTE"
    )

    # 4. Inativo -> NÃO deve aparecer
    p4 = await _seed_pessoa_and_relacionamentos(
        session, tenant_id, unidade_produtiva_id, "Ana Inativa", "OPERADOR", pessoa_ativo=False
    )
    
    # 5. Tenant-wide -> NÃO deve aparecer por regra conservadora
    p5 = await _seed_pessoa_and_relacionamentos(
        session, tenant_id, None, "Carlos Global", "DIRETOR"
    )

    device = DispositivoCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=uuid.uuid4(),
        nome="Tablet A",
        fazenda_ids=[unidade_produtiva_id],
        modulos=["agricola"],
        status="ATIVO",
        expires_at=datetime.utcnow(),
    )

    data = await SyncService(session, tenant_id, device).pull(None)

    pessoas = data.get("pessoas_operacionais", [])
    assert len(pessoas) == 1
    assert pessoas[0]["pessoa_id"] == str(p1)
    assert pessoas[0]["nome_exibicao"] == "João Vigente"
    assert "OPERADOR" in pessoas[0]["papeis"]
    assert "cpf" not in pessoas[0]

async def test_sync_pull_multiplos_papeis(session, tenant_id):
    unidade_produtiva_id = uuid.uuid4()
    await _ensure_tenant_and_unit(session, tenant_id, unidade_produtiva_id)

    pessoa_id = await _seed_pessoa_and_relacionamentos(
        session, tenant_id, unidade_produtiva_id, "João Múltiplo", "OPERADOR"
    )
    # Adicionar outro papel
    tipo_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_tipos_relacionamento (id, tenant_id, codigo, nome, sistema, ativo, cor, icone) "
            "VALUES (:id, :tenant_id, 'MOTORISTA', 'MOTORISTA', false, true, '#6B7280', 'user')"
        ),
        {"id": str(tipo_id), "tenant_id": str(tenant_id)},
    )
    await session.execute(
        text(
            "INSERT INTO cadastros_pessoa_relacionamentos (id, pessoa_id, tipo_id, unidade_produtiva_id) "
            "VALUES (:id, :pessoa_id, :tipo_id, :up_id)"
        ),
        {"id": str(uuid.uuid4()), "pessoa_id": str(pessoa_id), "tipo_id": str(tipo_id), "up_id": str(unidade_produtiva_id)},
    )
    await session.commit()

    device = DispositivoCampo(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=uuid.uuid4(),
        nome="Tablet A",
        fazenda_ids=[unidade_produtiva_id],
        modulos=["agricola"],
        status="ATIVO",
        expires_at=datetime.utcnow(),
    )

    data = await SyncService(session, tenant_id, device).pull(None)

    pessoas = data.get("pessoas_operacionais", [])
    assert len(pessoas) == 1
    assert pessoas[0]["pessoa_id"] == str(pessoa_id)
    assert "OPERADOR" in pessoas[0]["papeis"]
    assert "MOTORISTA" in pessoas[0]["papeis"]
    assert len(pessoas[0]["papeis"]) == 2
