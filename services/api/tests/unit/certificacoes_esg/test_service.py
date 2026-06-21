from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from certificacoes_esg.models import (
    PrioridadePlanoAcao,
    SeveridadeNaoConformidade,
    StatusNaoConformidade,
    StatusPlanoAcao,
    TipoEvidencia,
)
from certificacoes_esg.schemas import (
    EvidenciaCertificacaoCreate,
    NaoConformidadeCertificacaoCreate,
    NaoConformidadeStatusUpdate,
    PlanoAcaoCertificacaoCreate,
    PlanoAcaoStatusUpdate,
)
from certificacoes_esg.service import CertificacoesESGService
from core.exceptions import BusinessRuleError, EntityNotFoundError


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


async def test_criar_evidencia_usa_tenant_e_criado_por():
    tenant_id = _uuid()
    user_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id, user_id=user_id)
    programa = _programa(tenant_id)
    session.execute = AsyncMock(return_value=_result([programa]))

    payload = EvidenciaCertificacaoCreate(
        programa_id=programa.id,
        tipo_evidencia=TipoEvidencia.DOCUMENTO_PDF,
        titulo="Evidência técnica",
        descricao="Documento interno",
        origem_tipo="RELATORIO_TECNICO",
        origem_id=_uuid(),
        snapshot_json={"source": "app", "captured_at": datetime.now(timezone.utc).isoformat()},
        snapshot_hash="hash-01",
    )

    obj = await service.criar_evidencia(payload)

    assert obj.tenant_id == tenant_id
    assert obj.created_by == user_id
    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once()


async def test_listar_evidencias_respeita_tenant_e_filtros():
    tenant_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id)
    session.execute = AsyncMock(return_value=_result([]))
    programa_id = _uuid()

    await service.listar_evidencias(programa_id=programa_id, publico=True)

    stmt = session.execute.call_args.args[0]
    sql = str(stmt)
    assert "certificacao_evidencias" in sql
    assert "tenant_id" in sql
    assert "programa_id" in sql
    assert "publico" in sql


async def test_criar_nao_conformidade_valida_datas():
    tenant_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id)
    programa = _programa(tenant_id)
    session.execute = AsyncMock(return_value=_result([programa]))

    detectada = datetime.now(timezone.utc)
    payload = NaoConformidadeCertificacaoCreate(
        programa_id=programa.id,
        titulo="NC 1",
        descricao="Descrição",
        severidade=SeveridadeNaoConformidade.MAIOR,
        detectada_em=detectada,
        prazo_correcao=detectada + timedelta(days=2),
    )

    obj = await service.criar_nao_conformidade(payload, created_by=_uuid())

    assert obj.tenant_id == tenant_id
    assert obj.status == StatusNaoConformidade.ABERTA
    assert obj.detectada_em == detectada


async def test_atualizar_status_nao_conformidade_define_resolucao():
    tenant_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id)
    detectada = datetime.now(timezone.utc) - timedelta(days=1)
    existente = SimpleNamespace(
        id=_uuid(),
        tenant_id=tenant_id,
        detectada_em=detectada,
        status=StatusNaoConformidade.ABERTA,
        prazo_correcao=None,
        resolvida_em=None,
    )
    session.execute = AsyncMock(return_value=_result([existente]))

    atualizado = await service.atualizar_status_nao_conformidade(
        existente.id,
        NaoConformidadeStatusUpdate(status=StatusNaoConformidade.RESOLVIDA),
    )

    assert atualizado.resolvida_em is not None
    assert atualizado.status == StatusNaoConformidade.RESOLVIDA


async def test_criar_plano_acao_define_prazo_padrao():
    tenant_id = _uuid()
    user_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id, user_id=user_id)
    programa = _programa(tenant_id)
    session.execute = AsyncMock(return_value=_result([programa]))

    payload = PlanoAcaoCertificacaoCreate(
        programa_id=programa.id,
        titulo="Plano",
        descricao="Ação corretiva",
        prioridade=PrioridadePlanoAcao.ALTA,
    )

    obj = await service.criar_plano_acao(payload)

    assert obj.tenant_id == tenant_id
    assert obj.created_by == user_id
    assert obj.status == StatusPlanoAcao.PENDENTE
    assert obj.prazo is not None


async def test_atualizar_status_plano_acao_bloqueia_cross_tenant():
    tenant_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id)
    session.execute = AsyncMock(return_value=_result([]))

    with pytest.raises(EntityNotFoundError, match="Plano de ação não encontrado"):
        await service.atualizar_status_plano_acao(
            _uuid(),
            PlanoAcaoStatusUpdate(status=StatusPlanoAcao.CONCLUIDO),
        )


async def test_listar_planos_acao_respeita_filtros():
    tenant_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id)
    session.execute = AsyncMock(return_value=_result([]))
    programa_id = _uuid()

    await service.listar_planos_acao(programa_id=programa_id, status=StatusPlanoAcao.PENDENTE)

    stmt = session.execute.call_args.args[0]
    sql = str(stmt)
    assert "certificacao_planos_acao" in sql
    assert "tenant_id" in sql
    assert "programa_id" in sql
    assert "status" in sql


async def test_criar_evidencia_rejeita_fonte_oficial():
    tenant_id = _uuid()
    session = DummySession()
    service = CertificacoesESGService(session, tenant_id)
    programa = _programa(tenant_id)
    session.execute = AsyncMock(return_value=_result([programa]))
    payload = EvidenciaCertificacaoCreate(
        programa_id=programa.id,
        tipo_evidencia=TipoEvidencia.OUTRO,
        titulo="Evidência",
        descricao="Texto",
        origem_tipo="RELATORIO_TECNICO",
        origem_id=_uuid(),
    )
    payload = payload.model_copy(update={"origem_tipo": "CAR"})

    with pytest.raises(BusinessRuleError, match="origem_tipo"):
        await service.criar_evidencia(payload)
