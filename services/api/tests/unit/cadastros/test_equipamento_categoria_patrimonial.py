from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.equipamentos.models import CategoriaPatrimonial, Equipamento
from core.cadastros.equipamentos.schemas import EquipamentoCreate


async def _garantir_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, "
            "storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": f"Tenant {str(tenant_id)[:8]}", "doc": str(tenant_id)[:11]},
    )
    await session.commit()


@pytest.mark.asyncio
async def test_equipamento_sem_categoria_usa_default_ativo_depreciavel(session: AsyncSession, tenant_id: uuid.UUID):
    await _garantir_tenant(session, tenant_id)
    equipamento = Equipamento(
        tenant_id=tenant_id, nome=f"Trator {uuid.uuid4().hex[:6]}", tipo="TRATOR", combustivel="DIESEL", status="ATIVO",
    )
    session.add(equipamento)
    await session.commit()
    await session.refresh(equipamento)

    assert equipamento.categoria_patrimonial == CategoriaPatrimonial.ATIVO_DEPRECIAVEL.value


@pytest.mark.asyncio
async def test_equipamento_categoria_ferramenta_baixo_valor_persiste(session: AsyncSession, tenant_id: uuid.UUID):
    await _garantir_tenant(session, tenant_id)
    equipamento = Equipamento(
        tenant_id=tenant_id, nome=f"Enxada {uuid.uuid4().hex[:6]}", tipo="OUTRO", combustivel="NAO_APLICAVEL",
        status="ATIVO", categoria_patrimonial=CategoriaPatrimonial.FERRAMENTA_BAIXO_VALOR.value,
    )
    session.add(equipamento)
    await session.commit()
    await session.refresh(equipamento)

    assert equipamento.categoria_patrimonial == "FERRAMENTA_BAIXO_VALOR"


def test_equipamento_create_schema_aceita_ambas_categorias():
    for valor in ("ATIVO_DEPRECIAVEL", "FERRAMENTA_BAIXO_VALOR"):
        data = EquipamentoCreate(nome="Item Teste", categoria_patrimonial=valor)
        assert data.categoria_patrimonial == valor


def test_equipamento_create_schema_default_ativo_depreciavel():
    data = EquipamentoCreate(nome="Item Teste")
    assert data.categoria_patrimonial == "ATIVO_DEPRECIAVEL"
