from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from financeiro.models.despesa import Despesa
from pecuaria.animal.models import Animal, EventoAnimal, LoteAnimal
from pecuaria.services.animal_service import AnimalService

pytestmark = pytest.mark.asyncio


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def one(self):
        return self._value


async def test_compra_animal_cria_evento_despesa_e_materializa_lote(monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    lote = LoteAnimal(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        identificacao="Lote Compra",
        especie="BOVINO",
        categoria="BEZERRO",
        raca="Nelore",
        quantidade_cabecas=0,
        peso_medio_kg=0.0,
        data_formacao=date(2026, 6, 20),
        ativo=True,
    )
    animal = Animal(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        lote_id=lote.id,
        numero_brinco="BR-100",
        especie="BOVINO",
        categoria="BEZERRO",
        sexo="MACHO",
        status="ATIVO",
        data_entrada=date(2026, 6, 20),
        peso_atual_kg=320.0,
        valor_aquisicao=5200.0,
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock(return_value=_FakeResult((1, 320.0, 1)))
    session.get = AsyncMock(return_value=lote)

    svc = AnimalService(session, tenant_id)
    fake_despesa = SimpleNamespace(id=uuid.uuid4(), valor_total=5200.0, status="A_PAGAR")

    monkeypatch.setattr(svc, "_obter_evento_compra_existente", AsyncMock(return_value=None))
    monkeypatch.setattr(svc, "_obter_despesa_compra_existente", AsyncMock(return_value=None))
    monkeypatch.setattr(svc, "_resolver_plano_conta_compra", AsyncMock(return_value=uuid.uuid4()))

    class FakeDespesaService:
        def __init__(self, *args, **kwargs):  # noqa: D401, ARG002
            pass

        async def create_with_rateio(self, payload):  # noqa: ANN001
            assert payload.origem_tipo == "COMPRA"
            assert payload.fornecedor == "Fazenda Origem LTDA"
            assert payload.numero_nf == "NF-123"
            return [fake_despesa]

    monkeypatch.setattr("pecuaria.services.animal_service.DespesaService", FakeDespesaService)

    compra = {"fornecedor": "Fazenda Origem LTDA", "numero_nf": "NF-123"}

    evento, despesa = await svc._registrar_compra_financeira(animal, compra)
    await svc._materializar_lote(lote.id)

    assert evento is not None
    assert despesa is fake_despesa
    assert animal.valor_atual == 5200.0
    assert animal.dados_extras["compra"]["fornecedor"] == "Fazenda Origem LTDA"
    assert animal.dados_extras["compra"]["evento_compra_id"] == str(evento.id)
    assert animal.dados_extras["compra"]["despesa_compra_id"] == str(fake_despesa.id)
    assert lote.quantidade_cabecas == 1
    assert lote.peso_medio_kg == 320.0
    session.add.assert_any_call(animal)


async def test_compra_animal_financeiro_e_idempotente(monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    lote = LoteAnimal(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        identificacao="Lote Idempotente",
        especie="BOVINO",
        categoria="BEZERRO",
        raca="Nelore",
        quantidade_cabecas=0,
        peso_medio_kg=0.0,
        data_formacao=date(2026, 6, 20),
        ativo=True,
    )
    animal = Animal(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        lote_id=lote.id,
        numero_brinco="BR-101",
        especie="BOVINO",
        categoria="BEZERRO",
        sexo="FEMEA",
        status="ATIVO",
        data_entrada=date(2026, 6, 20),
        peso_atual_kg=280.0,
        valor_aquisicao=4100.0,
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock(return_value=_FakeResult((1, 280.0, 1)))
    session.get = AsyncMock(return_value=lote)

    svc = AnimalService(session, tenant_id)
    evento_existente = EventoAnimal(
        tenant_id=tenant_id,
        animal_id=animal.id,
        tipo="COMPRA",
        data_evento=date(2026, 6, 20),
        valor=4100.0,
    )
    despesa_existente = Despesa(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        plano_conta_id=uuid.uuid4(),
        descricao="Compra de animal BR-101",
        valor_total=4100.0,
        data_emissao=date(2026, 6, 20),
        data_vencimento=date(2026, 6, 20),
        status="A_PAGAR",
        origem_id=evento_existente.id,
        origem_tipo="COMPRA",
    )

    monkeypatch.setattr(
        svc,
        "_obter_evento_compra_existente",
        AsyncMock(side_effect=[evento_existente, evento_existente]),
    )
    monkeypatch.setattr(
        svc,
        "_obter_despesa_compra_existente",
        AsyncMock(side_effect=[despesa_existente, despesa_existente]),
    )
    monkeypatch.setattr(svc, "_resolver_plano_conta_compra", AsyncMock(return_value=uuid.uuid4()))

    await svc._registrar_compra_financeira(animal, {"fornecedor": "Fornecedor Idempotente"})
    await svc._registrar_compra_financeira(animal, {"fornecedor": "Fornecedor Idempotente"})

    assert animal.valor_atual == 4100.0
    assert animal.dados_extras["compra"]["despesa_compra_id"] == str(despesa_existente.id)
