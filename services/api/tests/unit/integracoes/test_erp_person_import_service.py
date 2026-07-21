from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from core.cadastros.pessoas.models import Pessoa
from integracoes.models import ExternalRecordAssociationStatus
from integracoes.erp.person_service import ErpPersonImportService, ErpPersonNotFoundError
from integracoes.erp.schemas import ErpPersonImportRequest, ErpPersonRecord


def _record() -> ErpPersonRecord:
    return ErpPersonRecord(
        external_id="42",
        tipo="PJ",
        nome_exibicao="Fazenda Teste",
        cnpj="00111222000133",
        ativo_no_erp=False,
    )


class _SessionStub:
    def __init__(self, scalars: list[object] | None = None) -> None:
        self._scalars = list(scalars or [])
        self.deleted: list[object] = []

    async def scalar(self, *_args, **_kwargs):
        return self._scalars.pop(0) if self._scalars else None

    def add(self, obj: object) -> None:
        return None

    async def delete(self, obj: object) -> None:
        self.deleted.append(obj)


class _ExecuteResult:
    def __init__(self, row: tuple[object, ...] | None) -> None:
        self._row = row

    def first(self) -> tuple[object, ...] | None:
        return self._row


def test_importacao_exige_id_externo() -> None:
    with pytest.raises(ValidationError):
        ErpPersonImportRequest(external_id="", base_legal="CONTRATO")


def test_dados_do_erp_nao_desativam_pessoa_local() -> None:
    pessoa = Pessoa(
        tenant_id=uuid.uuid4(),
        tipo="PF",
        nome_exibicao="Nome antigo",
        base_legal="CONTRATO",
        ativo=True,
    )

    ErpPersonImportService._apply_person_fields(pessoa, _record())

    assert pessoa.tipo == "PJ"
    assert pessoa.nome_exibicao == "Fazenda Teste"
    assert pessoa.ativo is True


@pytest.mark.asyncio
async def test_consulta_rejeita_id_inexistente_no_erp() -> None:
    runtime = SimpleNamespace(get_person_by_external_id=AsyncMock(return_value=None))
    service = ErpPersonImportService(SimpleNamespace(), runtime)

    with pytest.raises(ErpPersonNotFoundError, match="42"):
        await service.consultar(uuid.uuid4(), "42")


@pytest.mark.asyncio
async def test_contexto_de_pessoas_filtra_marketplace_por_coluna_ativa() -> None:
    config = SimpleNamespace(
        id=10,
        connection_payload={"environment": "homologacao"},
    )
    provider = SimpleNamespace(id=20)
    feature = SimpleNamespace(id=30)
    session = SimpleNamespace(execute=AsyncMock(return_value=_ExecuteResult((config, provider, feature))))
    runtime = SimpleNamespace(provider_slug="sankhya")

    context = await ErpPersonImportService(session, runtime)._load_context(uuid.uuid4())

    assert context.provider_id == 20
    assert context.config_id == 10
    assert context.feature_id == 30
    assert context.environment == "homologacao"


@pytest.mark.asyncio
async def test_sincronizacao_total_lista_erp_e_vinculados_nao_lista(monkeypatch) -> None:
    runtime = SimpleNamespace(list_people=AsyncMock(return_value=[{"external_id": "42"}]))
    service = ErpPersonImportService(SimpleNamespace(), runtime)
    sync_all = AsyncMock(return_value=1)
    sync_linked = AsyncMock(return_value=2)
    monkeypatch.setattr(service, "_sync_all_records", sync_all)
    monkeypatch.setattr(service, "_sync_linked_records", sync_linked)

    assert await service.sincronizar(uuid.uuid4(), "ALL_EXTERNAL") == 1
    runtime.list_people.assert_awaited_once()
    sync_all.assert_awaited_once()

    assert await service.sincronizar(uuid.uuid4(), "LINKED_ONLY") == 2
    sync_linked.assert_awaited_once()


@pytest.mark.asyncio
async def test_contato_removido_no_erp_desativa_contato_principal_local() -> None:
    contact = SimpleNamespace(ativo=True)
    service = ErpPersonImportService(_SessionStub([contact]), SimpleNamespace())

    await service._upsert_contact(SimpleNamespace(id=uuid.uuid4()), "EMAIL", None)

    assert contact.ativo is False


@pytest.mark.asyncio
async def test_documento_removido_no_erp_apaga_documento_local() -> None:
    document = SimpleNamespace()
    session = _SessionStub([document])
    service = ErpPersonImportService(session, SimpleNamespace())
    record = ErpPersonRecord(external_id="42", tipo="PJ", nome_exibicao="Sem CNPJ")

    await service._upsert_document(SimpleNamespace(id=uuid.uuid4()), record)

    assert session.deleted == [document]


@pytest.mark.asyncio
async def test_troca_de_id_erp_substitui_vinculo_ativo_anterior(monkeypatch) -> None:
    pessoa = SimpleNamespace(id=uuid.uuid4())
    context = SimpleNamespace(provider_id=1, config_id=2, feature_id=3, environment="producao")
    current = SimpleNamespace(external_record_id="10", status=ExternalRecordAssociationStatus.ACTIVE.value)
    service = ErpPersonImportService(_SessionStub(), SimpleNamespace(provider_slug="sankhya"))
    service.associations = SimpleNamespace(replace_association=AsyncMock())
    monkeypatch.setattr(service, "_find_association", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_find_active_local_association", AsyncMock(return_value=current))

    await service._link_external(uuid.uuid4(), pessoa, _record(), context)

    service.associations.replace_association.assert_awaited_once()
