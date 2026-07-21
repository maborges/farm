# ruff: noqa: S105, S106
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from integracoes.erp.providers.sankhya_runtime import SankhyaProviderRuntime
from integracoes.sankhya.routers import sincronizar_pessoas
from integracoes.sankhya.services.auth_service import SankhyaConnectionData
from integracoes.sankhya.services.canonical_adapter import SankhyaCanonicalAdapter
from integracoes.sankhya.services.gateway_contract import (
    SankhyaGatewayAuthorizationError,
)
from integracoes.sankhya.services.sync_service import SankhyaPessoaService, SankhyaWSClient


def _gateway_connection() -> SankhyaConnectionData:
    return SankhyaConnectionData(
        environment="producao",
        api_base_url="https://api.sankhya.com.br/gateway/v1",
        auth_url="https://api.sankhya.com.br/authenticate",
        client_id="client-id",
        client_secret="client-secret",
        x_token="x-token",
    )


def test_resumo_de_health_respeita_limite_da_coluna() -> None:
    error = "Falha externa: " + "x" * 500

    summary = SankhyaCanonicalAdapter._build_health_summary(False, "pessoas", error)

    assert len(summary) == 200
    assert summary.endswith("…")
    assert summary.startswith("Falha externa:")


@pytest.mark.asyncio
async def test_gateway_busca_pessoa_no_load_records_oficial() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "status": "1",
                "responseBody": {
                    "entities": {
                        "total": "1",
                        "hasMoreResult": "false",
                        "entity": {
                            "CODPARC": {"$": "10"},
                            "NOMEPARC": {"$": "Pessoa Teste"},
                            "TIPPESSOA": {"$": "F"},
                            "CGC_CPF": {"$": "12345678901"},
                            "ATIVO": {"$": "S"},
                        },
                    }
                },
            },
        )

    client = SankhyaWSClient(_gateway_connection())
    client._session = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client.auth_service.authenticate = AsyncMock(return_value="access-token")
    try:
        result = await client.executar_ws("PessoaFisica", "findAll", {})
    finally:
        await client._session.aclose()

    assert captured["url"] == (
        "https://api.sankhya.com.br/gateway/v1/mge/service.sbr"
        "?serviceName=CRUDServiceProvider.loadRecords&outputType=json"
    )
    assert captured["headers"]["content-type"] == "application/json"
    assert captured["headers"]["authorization"] == "Bearer access-token"
    assert "x-token" not in captured["headers"]
    assert "soapaction" not in captured["headers"]
    dataset = captured["body"]["requestBody"]["dataSet"]
    assert dataset["rootEntity"] == "Parceiro"
    assert dataset["ignoreCalculatedFields"] == "true"
    assert dataset["tryJoinedFields"] == "true"
    assert dataset["entity"] == [
        {
            "path": "",
            "fieldset": {
                "list": "CODPARC,NOMEPARC,TIPPESSOA,CGC_CPF,EMAIL,TELEFONE,CEP,IDENTINSCESTAD,ATIVO"
            },
        }
    ]
    assert result["pessoas"] == [
        {
            "CODPARC": "10",
            "NOME": "Pessoa Teste",
            "TIPPESSOA": "F",
            "CGC_CPF": "12345678901",
            "ATIVO": "S",
        }
    ]


@pytest.mark.asyncio
async def test_gateway_busca_pessoa_individual_por_codparc_parametrizado() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "status": "1",
                "responseBody": {
                    "entities": {
                        "hasMoreResult": "false",
                        "entity": {"CODPARC": {"$": "42"}, "NOMEPARC": {"$": "Maria"}},
                    }
                },
            },
        )

    client = SankhyaWSClient(_gateway_connection())
    client._session = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client.auth_service.authenticate = AsyncMock(return_value="access-token")
    try:
        result = await client.buscar_registro("PessoaFisica", "findAll", "42")
    finally:
        await client._session.aclose()

    dataset = captured["body"]["requestBody"]["dataSet"]
    assert dataset["criteria"] == {
        "expression": {"$": "CODPARC = ?"},
        "parameter": [{"$": "42", "type": "I"}],
    }
    assert result["CODPARC"] == "42"


@pytest.mark.asyncio
async def test_gateway_normaliza_campos_posicionais_do_load_records() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "1",
                "responseBody": {
                    "entities": {
                        "total": "1",
                        "hasMoreResult": "false",
                        "entity": {
                            "f0": {"$": "10"},
                            "f1": {"$": "Pessoa Posicional"},
                            "f2": {"$": "F"},
                            "f3": {"$": "12345678901"},
                            "f8": {"$": "S"},
                        },
                    }
                },
            },
        )

    client = SankhyaWSClient(_gateway_connection())
    client._session = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client.auth_service.authenticate = AsyncMock(return_value="access-token")
    try:
        result = await client.executar_ws("PessoaFisica", "findAll", {})
    finally:
        await client._session.aclose()

    assert result["pessoas"] == [
        {
            "CODPARC": "10",
            "NOME": "Pessoa Posicional",
            "TIPPESSOA": "F",
            "CGC_CPF": "12345678901",
            "ATIVO": "S",
        }
    ]


@pytest.mark.asyncio
async def test_gateway_rejeita_operacao_sem_mapeamento_em_vez_de_chamar_path_invalido() -> None:
    client = SankhyaWSClient(_gateway_connection())
    client._session = AsyncMock()

    with pytest.raises(ValueError, match="não mapeada para o Gateway"):
        await client.executar_ws("ServicoInexistente", "findAll", {})

    client._session.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_gateway_classifica_negacao_da_camada_de_autorizacao() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"status": "0", "statusMessage": "Não autorizado."},
        )

    client = SankhyaWSClient(_gateway_connection())
    client._session = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client.auth_service.authenticate = AsyncMock(return_value="access-token")
    try:
        with pytest.raises(SankhyaGatewayAuthorizationError, match="Parceiro"):
            await client.executar_ws("PessoaFisica", "findAll", {})
    finally:
        await client._session.aclose()


@pytest.mark.asyncio
async def test_sync_pessoas_retorna_403_quando_sankhya_nega_autorizacao() -> None:
    error = SankhyaGatewayAuthorizationError("Cadastro de Parceiros não autorizado")
    sync_service = SimpleNamespace(
        iniciar_sync_log=AsyncMock(return_value=SimpleNamespace(id=91)),
        finalizar_sync_log=AsyncMock(),
    )
    pessoa_service = SimpleNamespace(importar_pessoas=AsyncMock(side_effect=error))
    policy_service = SimpleNamespace(garantir_execucao_manual=AsyncMock())

    with pytest.raises(HTTPException) as captured:
        await sincronizar_pessoas(
            tenant_id=uuid.uuid4(),
            sync_service=sync_service,
            pessoa_service=pessoa_service,
            policy_service=policy_service,
        )

    assert captured.value.status_code == 403
    assert captured.value.detail == "Cadastro de Parceiros não autorizado"
    sync_service.finalizar_sync_log.assert_awaited_once()


@pytest.mark.asyncio
async def test_importacao_libera_transacao_antes_de_consultar_gateway(monkeypatch) -> None:
    events: list[str] = []
    db = SimpleNamespace(
        commit=AsyncMock(side_effect=lambda: events.append("commit")),
        rollback=AsyncMock(),
    )
    service = SankhyaPessoaService(db)
    service._get_config = AsyncMock(return_value=SimpleNamespace())
    service._restore_rls_context = AsyncMock(side_effect=lambda tenant: events.append("rls"))
    service._salvar_pessoa_fisica = AsyncMock()

    class Gateway:
        def __init__(self, config) -> None:
            self.config = config

        async def __aenter__(self):
            events.append("gateway")
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def executar_ws(self, service_name: str, method: str, params: dict) -> dict:
            if service_name == "PessoaFisica":
                return {"pessoas": [{"CODPARC": "10", "NOME": "Pessoa"}]}
            return {"pessoas": []}

    monkeypatch.setattr("integracoes.sankhya.services.sync_service.SankhyaWSClient", Gateway)

    assert await service.importar_pessoas("tenant-a") == 1
    assert events[:3] == ["commit", "gateway", "rls"]
    service._restore_rls_context.assert_awaited_once_with("tenant-a")


@pytest.mark.asyncio
async def test_importacao_aborta_segunda_categoria_quando_banco_falha(monkeypatch) -> None:
    db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
    service = SankhyaPessoaService(db)
    service._get_config = AsyncMock(return_value=SimpleNamespace())
    service._restore_rls_context = AsyncMock()
    service._salvar_pessoa_fisica = AsyncMock(side_effect=SQLAlchemyError("db indisponível"))
    calls: list[str] = []

    class Gateway:
        def __init__(self, config) -> None:
            self.config = config

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def executar_ws(self, service_name: str, method: str, params: dict) -> dict:
            calls.append(service_name)
            return {"pessoas": [{"CODPARC": "10", "NOME": "Pessoa"}]}

    monkeypatch.setattr("integracoes.sankhya.services.sync_service.SankhyaWSClient", Gateway)

    with pytest.raises(SQLAlchemyError, match="db indisponível"):
        await service.importar_pessoas("tenant-a")

    assert calls == ["PessoaFisica"]


@pytest.mark.asyncio
async def test_runtime_manual_busca_pessoa_fisica_quando_pj_nao_existe(monkeypatch) -> None:
    calls: list[str] = []
    runtime = SankhyaProviderRuntime(SimpleNamespace())
    runtime._sync_service._get_operational_config = AsyncMock(return_value=SimpleNamespace())

    class Gateway:
        def __init__(self, config) -> None:
            self.config = config

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def buscar_registro(self, service_name: str, method: str, external_id: str):
            calls.append(service_name)
            if service_name == "PessoaFisica":
                return {"CODPARC": external_id, "TIPPESSOA": "F", "NOME": "Maria"}
            return None

    monkeypatch.setattr("integracoes.erp.providers.sankhya_runtime.SankhyaWSClient", Gateway)

    result = await runtime.get_person_by_external_id("tenant-a", "42")

    assert calls == ["PessoaJuridica", "PessoaFisica"]
    assert result["tipo"] == "PF"


@pytest.mark.asyncio
async def test_sync_preserva_log_id_quando_rollback_expira_objeto() -> None:
    class ExpiringLog:
        reads = 0

        @property
        def id(self) -> int:
            self.reads += 1
            if self.reads > 1:
                raise AssertionError("log.id foi acessado novamente após a falha")
            return 95

    sync_service = SimpleNamespace(
        iniciar_sync_log=AsyncMock(return_value=ExpiringLog()),
        finalizar_sync_log=AsyncMock(),
    )
    pessoa_service = SimpleNamespace(
        importar_pessoas=AsyncMock(side_effect=RuntimeError("connection is closed")),
    )
    policy_service = SimpleNamespace(garantir_execucao_manual=AsyncMock())

    with pytest.raises(HTTPException) as captured:
        await sincronizar_pessoas(
            tenant_id=uuid.uuid4(),
            sync_service=sync_service,
            pessoa_service=pessoa_service,
            policy_service=policy_service,
        )

    assert captured.value.status_code == 500
    assert captured.value.detail == "connection is closed"
    sync_service.finalizar_sync_log.assert_awaited_once_with(
        95, False, 0, 0, "connection is closed", 0
    )
