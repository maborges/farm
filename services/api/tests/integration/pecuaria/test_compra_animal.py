from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from pecuaria.animal.models import Animal, LoteAnimal
from pecuaria.schemas.animal_schema import AnimalCreate
from pecuaria.services.animal_service import AnimalService

pytestmark = pytest.mark.asyncio


async def test_compra_animal_create_injeta_dados_extras_e_reusa_integracao(monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    lote = LoteAnimal(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        identificacao="Lote API",
        especie="BOVINO",
        categoria="BEZERRO",
        raca="Nelore",
        quantidade_cabecas=0,
        peso_medio_kg=0.0,
        data_formacao=date(2026, 6, 20),
        ativo=True,
    )

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()

    svc = AnimalService(session, tenant_id)
    created_calls: list[Animal] = []

    async def fake_compra(animal: Animal, compra=None):  # noqa: ANN001
        created_calls.append(animal)
        animal.dados_extras = {
            **(animal.dados_extras or {}),
            "compra": {
                "fornecedor": "Fornecedor API",
                "evento_compra_id": str(uuid.uuid4()),
                "despesa_compra_id": str(uuid.uuid4()),
            },
        }
        return None, None

    materialized: list[uuid.UUID | None] = []

    async def fake_materializar(lote_id):  # noqa: ANN001
        materialized.append(lote_id)

    monkeypatch.setattr(svc, "_validate_references", AsyncMock(return_value=None))
    monkeypatch.setattr(svc, "_registrar_compra_financeira", fake_compra)
    monkeypatch.setattr(svc, "_materializar_lote", fake_materializar)
    monkeypatch.setattr(
        "core.base_service.write_audit_log",
        AsyncMock(return_value=None),
    )

    animal = await svc.create(
        AnimalCreate(
            unidade_produtiva_id=unidade_produtiva_id,
            lote_id=lote.id,
            numero_brinco="API-001",
            sexo="MACHO",
            categoria="BEZERRO",
            peso_atual_kg=330.0,
            valor_aquisicao=6100.0,
            data_entrada=date(2026, 6, 20),
            fornecedor="Fornecedor API",
            numero_nf="NF-API-001",
        )
    )

    assert created_calls and created_calls[0].id == animal.id
    assert animal.valor_aquisicao == 6100.0
    assert animal.dados_extras["compra"]["fornecedor"] == "Fornecedor API"
    assert materialized == [lote.id]
    session.add.assert_called()
    session.flush.assert_awaited()
