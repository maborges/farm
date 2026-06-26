from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from pecuaria.animal.models import Animal, CategoriaAnimal, EventoAnimal, SexoAnimal
from pecuaria.services.manejo_sync_service import ManejoSyncService

pytestmark = pytest.mark.asyncio


def _fake_task(tipo: str, dados: dict) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        type=tipo,
        module="pecuaria",
        status_execucao="CONCLUIDA",
        status="CONCLUIDA",
        concluida_em=date(2026, 6, 26),
        operado_id=None,
        operador_id=None,
        unidade_produtiva_id=uuid.uuid4(),
        lote_id=uuid.uuid4(),
        client_id=str(uuid.uuid4()),
        dados=dados,
    )


def _fake_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    return session


async def test_reproducao_cobertura_materializa_evento(monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    lote_id = uuid.uuid4()
    mother = Animal(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=uuid.uuid4(),
        lote_id=lote_id,
        numero_brinco="MAT-001",
        especie="BOVINO",
        categoria=CategoriaAnimal.VACA_CORTE.value,
        sexo=SexoAnimal.FEMEA.value,
        status="ATIVO",
        data_entrada=date(2026, 1, 1),
    )
    session = _fake_session()
    svc = ManejoSyncService(session, tenant_id)
    task = _fake_task(
        "INSEMINACAO",
        {
            "lote_id": str(lote_id),
            "animal_id": str(mother.id),
            "reprodutor_id": str(uuid.uuid4()),
            "data_evento": "2026-06-26",
            "metodo": "IATF",
            "observacoes": "Cobertura teste",
        },
    )

    monkeypatch.setattr(svc, "_obter_animal", AsyncMock(return_value=mother))
    monkeypatch.setattr(svc, "_evento_reprodutivo_existente", AsyncMock(return_value=False))
    monkeypatch.setattr(svc, "_publish_reproducao_evento", AsyncMock(return_value=None))

    resultado = await svc._processar_apareamento(task)

    assert resultado.status == "SUCCESS"
    evento = session.add.call_args.args[0]
    assert isinstance(evento, EventoAnimal)
    assert evento.tipo == "INSEMINACAO"
    assert mother.dados_extras["reproducao"]["ultimo_evento"] == "INSEMINACAO"


async def test_reproducao_parto_cria_cria_e_eventos(monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    lote_id = uuid.uuid4()
    mother = Animal(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=uuid.uuid4(),
        lote_id=lote_id,
        numero_brinco="MAT-002",
        especie="BOVINO",
        categoria=CategoriaAnimal.VACA_CORTE.value,
        sexo=SexoAnimal.FEMEA.value,
        status="ATIVO",
        data_entrada=date(2026, 1, 1),
    )
    session = _fake_session()
    svc = ManejoSyncService(session, tenant_id)
    task = _fake_task(
        "PARTO",
        {
            "lote_id": str(lote_id),
            "mae_id": str(mother.id),
            "pai_id": str(uuid.uuid4()),
            "sexo_cria": "FEMEA",
            "peso_nascimento_kg": 34.5,
            "cria_numero_brinco": "CR-001",
            "data_evento": "2026-06-26",
            "observacoes": "Parto assistido",
        },
    )

    monkeypatch.setattr(svc, "_obter_animal", AsyncMock(return_value=mother))
    monkeypatch.setattr(svc, "_evento_reprodutivo_existente", AsyncMock(return_value=False))
    monkeypatch.setattr(svc, "_obter_cria_existente", AsyncMock(return_value=None))
    monkeypatch.setattr(svc, "_publish_reproducao_evento", AsyncMock(return_value=None))

    resultado = await svc._processar_parto(task)

    assert resultado.status == "SUCCESS"
    cria = next(
        call.args[0]
        for call in session.add.call_args_list
        if isinstance(call.args[0], Animal) and call.args[0].id != mother.id
    )
    assert cria.mae_id == mother.id
    assert cria.lote_id == lote_id
    assert cria.categoria == CategoriaAnimal.BEZERRA.value
    eventos = session.add_all.call_args.args[0]
    assert {evt.tipo for evt in eventos} == {"PARTO", "NASCIMENTO"}


async def test_reproducao_desmama_atualiza_categoria_e_lote(monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    lote_origem = uuid.uuid4()
    lote_destino = uuid.uuid4()
    cria = Animal(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=uuid.uuid4(),
        lote_id=lote_origem,
        numero_brinco="CR-002",
        especie="BOVINO",
        categoria=CategoriaAnimal.BEZERRO.value,
        sexo=SexoAnimal.MACHO.value,
        status="ATIVO",
        data_entrada=date(2026, 1, 1),
    )
    session = _fake_session()
    svc = ManejoSyncService(session, tenant_id)
    task = _fake_task(
        "DESMAME",
        {
            "animal_id": str(cria.id),
            "lote_destino_id": str(lote_destino),
            "peso_desmama_kg": 180.0,
            "data_evento": "2026-06-26",
            "observacoes": "Desmama teste",
        },
    )

    monkeypatch.setattr(svc, "_obter_animal", AsyncMock(return_value=cria))
    monkeypatch.setattr(svc, "_evento_reprodutivo_existente", AsyncMock(return_value=False))
    monkeypatch.setattr(svc, "_publish_reproducao_evento", AsyncMock(return_value=None))

    resultado = await svc._processar_desmame(task)

    assert resultado.status == "SUCCESS"
    assert cria.lote_id == lote_destino
    assert cria.categoria == CategoriaAnimal.GARROTE.value
    evento = session.add.call_args_list[0].args[0]
    assert isinstance(evento, EventoAnimal)
    assert evento.tipo == "DESMAME"
