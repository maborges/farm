from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, create_autospec

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.cadastros.pessoas.models import Pessoa
from core.cadastros.pessoas.schemas import (
    ContatoCreate,
    PessoaCreate,
    PessoaPIIUpdate,
    PessoaUpdate,
)
from core.cadastros.pessoas.service import PessoaService
from core.exceptions import BusinessRuleError


def _service() -> PessoaService:
    session = create_autospec(AsyncSession, instance=True)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return PessoaService(Pessoa, session, uuid.uuid4())


@pytest.mark.asyncio
async def test_erp_governando_bloqueia_criacao_local_de_pessoa(monkeypatch) -> None:
    service = _service()
    monkeypatch.setattr(service, "_erp_governa_pessoas", AsyncMock(return_value=True))

    with pytest.raises(BusinessRuleError, match="ID do ERP"):
        await service.criar(PessoaCreate(tipo="PJ", nome_exibicao="Fornecedor Local"))


@pytest.mark.asyncio
async def test_erp_governando_bloqueia_identidade_pii_e_contato(monkeypatch) -> None:
    service = _service()
    pessoa = SimpleNamespace(id=uuid.uuid4(), nome_exibicao="Fornecedor")
    monkeypatch.setattr(service, "_get_pessoa", AsyncMock(return_value=pessoa))
    monkeypatch.setattr(service, "_erp_governa_pessoas", AsyncMock(return_value=True))

    with pytest.raises(BusinessRuleError):
        await service.atualizar(pessoa.id, PessoaUpdate(nome_exibicao="Novo nome"))
    with pytest.raises(BusinessRuleError):
        await service.atualizar_pii(pessoa.id, PessoaPIIUpdate(cnpj="12345678000199"))
    with pytest.raises(BusinessRuleError):
        await service.adicionar_contato(
            pessoa.id,
            ContatoCreate(tipo="EMAIL", valor="financeiro@example.com"),
        )


@pytest.mark.asyncio
async def test_erp_governando_preserva_campos_locais_do_agrosaas(monkeypatch) -> None:
    service = _service()
    pessoa = SimpleNamespace(id=uuid.uuid4(), base_legal="CONTRATO")
    monkeypatch.setattr(service, "_get_pessoa", AsyncMock(return_value=pessoa))
    monkeypatch.setattr(service, "_erp_governa_pessoas", AsyncMock(return_value=True))

    result = await service.atualizar(
        pessoa.id,
        PessoaUpdate(base_legal="OBRIGACAO_LEGAL"),
    )

    assert result.base_legal == "OBRIGACAO_LEGAL"


@pytest.mark.asyncio
async def test_sem_governanca_erp_mantem_crud_local(monkeypatch) -> None:
    service = _service()
    pessoa = SimpleNamespace(id=uuid.uuid4(), nome_exibicao="Fornecedor")
    monkeypatch.setattr(service, "_get_pessoa", AsyncMock(return_value=pessoa))
    monkeypatch.setattr(service, "_erp_governa_pessoas", AsyncMock(return_value=False))

    result = await service.atualizar(
        pessoa.id,
        PessoaUpdate(nome_exibicao="Fornecedor Local"),
    )

    assert result.nome_exibicao == "Fornecedor Local"
