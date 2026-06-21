from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from certificacoes_esg.models import (
    StatusPassaporte,
    StatusRelatorioESG,
    TipoEvidencia,
    TipoEventoPassaporte,
)
from certificacoes_esg.schemas import (
    PassaporteRastreabilidadeCreate,
    PassaporteRastreabilidadeEvidenciaCreate,
    PassaporteRastreabilidadeEventoCreate,
    PassaporteRastreabilidadeUpdateStatus,
    RelatorioESGCreate,
    RelatorioESGEvidenciaCreate,
    RelatorioESGIndicadorCreate,
    RelatorioESGUpdateStatus,
)
from certificacoes_esg.service import CertificacoesESGService


pytestmark = pytest.mark.asyncio


class DummyScalarResult:
    def __init__(self, items: list[object]):
        self._items = items

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)


class DummyExecuteResult:
    def __init__(self, items: list[object]):
        self._items = items

    def scalars(self):
        return DummyScalarResult(self._items)


class DummySession:
    def __init__(self):
        self.execute = AsyncMock()
        self.add = MagicMock()
        self.flush = AsyncMock()
        self.refresh = AsyncMock()


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _result(items: list[object]) -> DummyExecuteResult:
    return DummyExecuteResult(items)


def _programa(tenant_id: uuid.UUID):
    return SimpleNamespace(id=_uuid(), tenant_id=tenant_id)


async def test_criar_relatorio_esg_usa_tenant():
    tenant_id = _uuid()
    user_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id, user_id=user_id)
    session.execute = AsyncMock(return_value=_result([_programa(tenant_id)]))
    payload = RelatorioESGCreate(
        programa_id=_uuid(),
        titulo="Relatório ESG",
        status=StatusRelatorioESG.RASCUNHO,
        versao=1,
    )
    obj = await service.criar_relatorio_esg(payload)
    assert obj.tenant_id == tenant_id
    assert obj.created_by == user_id


async def test_atualizar_status_relatorio_esg_publicado_exige_snapshot_hash():
    tenant_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id)
    relatorio = SimpleNamespace(
        id=_uuid(),
        tenant_id=tenant_id,
        status=StatusRelatorioESG.RASCUNHO,
        snapshot_hash=None,
        snapshot_json=None,
        publicado_em=None,
        cancelado_em=None,
    )
    session.execute = AsyncMock(return_value=_result([relatorio]))

    atualizado = await service.atualizar_status_relatorio_esg(
        relatorio.id,
        RelatorioESGUpdateStatus(
            status=StatusRelatorioESG.PUBLICADO,
            publicado_em=datetime.now(timezone.utc),
            snapshot_hash="hash-01",
            snapshot_json={"a": 1},
        ),
    )
    assert atualizado.status == StatusRelatorioESG.PUBLICADO
    assert atualizado.snapshot_hash == "hash-01"


async def test_adicionar_indicador_relatorio_esg_valida_tenant():
    tenant_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id)
    relatorio = SimpleNamespace(id=_uuid(), tenant_id=tenant_id)
    session.execute = AsyncMock(return_value=_result([relatorio]))
    payload = RelatorioESGIndicadorCreate(
        relatorio_id=relatorio.id,
        nome="Emissões",
        valor=12.5,
        score=1.2,
    )
    obj = await service.adicionar_indicador_relatorio_esg(payload)
    assert obj.tenant_id == tenant_id
    session.add.assert_called_once()


async def test_vincular_evidencia_relatorio_esg_respeita_tenant():
    tenant_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id)
    relatorio = SimpleNamespace(id=_uuid(), tenant_id=tenant_id)
    evidencia = SimpleNamespace(id=_uuid(), tenant_id=tenant_id)
    session.execute = AsyncMock(return_value=_result([relatorio, evidencia]))
    payload = RelatorioESGEvidenciaCreate(relatorio_id=relatorio.id, evidencia_id=evidencia.id)
    obj = await service.vincular_evidencia_relatorio_esg(payload)
    assert obj.tenant_id == tenant_id


async def test_criar_passaporte_rastreabilidade_usa_tenant():
    tenant_id = _uuid()
    user_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id, user_id=user_id)
    session.execute = AsyncMock(return_value=_result([_programa(tenant_id)]))
    payload = PassaporteRastreabilidadeCreate(
        titulo="Passaporte",
        status=StatusPassaporte.RASCUNHO,
        versao=1,
    )
    obj = await service.criar_passaporte_rastreabilidade(payload)
    assert obj.tenant_id == tenant_id
    assert obj.created_by == user_id


async def test_atualizar_status_passaporte_publicado_exige_snapshot_hash():
    tenant_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id)
    passaporte = SimpleNamespace(
        id=_uuid(),
        tenant_id=tenant_id,
        status=StatusPassaporte.RASCUNHO,
        snapshot_hash=None,
        snapshot_json=None,
        publicado_em=None,
        revogado_em=None,
    )
    session.execute = AsyncMock(return_value=_result([passaporte]))

    atualizado = await service.atualizar_status_passaporte_rastreabilidade(
        passaporte.id,
        PassaporteRastreabilidadeUpdateStatus(
            status=StatusPassaporte.PUBLICADO,
            publicado_em=datetime.now(timezone.utc),
            snapshot_hash="hash-02",
            snapshot_json={"a": 1},
        ),
    )
    assert atualizado.status == StatusPassaporte.PUBLICADO
    assert atualizado.snapshot_hash == "hash-02"


async def test_adicionar_evento_passaporte_valida_snapshot():
    tenant_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id)
    passaporte = SimpleNamespace(id=_uuid(), tenant_id=tenant_id)
    session.execute = AsyncMock(return_value=_result([passaporte]))
    payload = PassaporteRastreabilidadeEventoCreate(
        passaporte_id=passaporte.id,
        tipo_evento=TipoEventoPassaporte.GERADO,
        titulo="Evento",
        descricao="Descrição",
        ocorrido_em=datetime.now(timezone.utc),
        origem_tipo="RELATORIO_TECNICO",
        origem_id=_uuid(),
        snapshot_json={"a": 1},
        snapshot_hash="hash-03",
    )
    obj = await service.adicionar_evento_passaporte(payload)
    assert obj.tenant_id == tenant_id


async def test_vincular_evidencia_passaporte_respeita_tenant():
    tenant_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id)
    passaporte = SimpleNamespace(id=_uuid(), tenant_id=tenant_id)
    evidencia = SimpleNamespace(id=_uuid(), tenant_id=tenant_id)
    session.execute = AsyncMock(return_value=_result([passaporte, evidencia]))
    payload = PassaporteRastreabilidadeEvidenciaCreate(passaporte_id=passaporte.id, evidencia_id=evidencia.id)
    obj = await service.vincular_evidencia_passaporte(payload)
    assert obj.tenant_id == tenant_id
