from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

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
    PlanoAcaoCertificacaoCreate,
)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def test_evidencia_rejeita_fonte_oficial_territorial():
    with pytest.raises(ValidationError, match="origem_tipo"):
        EvidenciaCertificacaoCreate(
            programa_id=_uuid(),
            tipo_evidencia=TipoEvidencia.DOCUMENTO_PDF,
            titulo="Evidência técnica",
            descricao="Documento interno",
            origem_tipo="CAR",
            origem_id=_uuid(),
        )


def test_evidencia_exige_hash_do_snapshot():
    with pytest.raises(ValidationError, match="snapshot_hash"):
        EvidenciaCertificacaoCreate(
            programa_id=_uuid(),
            tipo_evidencia=TipoEvidencia.FOTO_CAMPO,
            titulo="Foto de campo",
            descricao="Registro fotográfico",
            origem_tipo="RELATORIO_TECNICO",
            origem_id=_uuid(),
            snapshot_json={"source": "app"},
        )


def test_evidencia_exige_hash_do_arquivo():
    with pytest.raises(ValidationError, match="arquivo_hash"):
        EvidenciaCertificacaoCreate(
            programa_id=_uuid(),
            tipo_evidencia=TipoEvidencia.DOCUMENTO_PDF,
            titulo="PDF",
            descricao="Arquivo anexo",
            origem_tipo="RELATORIO_TECNICO",
            origem_id=_uuid(),
            arquivo_url="https://example.com/arquivo.pdf",
        )


def test_nao_conformidade_rejeita_prazo_anterior():
    detectada = datetime.now(timezone.utc)
    with pytest.raises(ValidationError, match="prazo_correcao"):
        NaoConformidadeCertificacaoCreate(
            programa_id=_uuid(),
            titulo="NC 1",
            descricao="Descrição",
            severidade=SeveridadeNaoConformidade.MENOR,
            detectada_em=detectada,
            prazo_correcao=detectada - timedelta(days=1),
        )


def test_nao_conformidade_status_oficial():
    payload = NaoConformidadeCertificacaoCreate(
        programa_id=_uuid(),
        titulo="NC 1",
        descricao="Descrição",
        severidade=SeveridadeNaoConformidade.MAIOR,
    )
    assert payload.status == StatusNaoConformidade.ABERTA


def test_plano_acao_aceita_enum_e_campos_minimos():
    payload = PlanoAcaoCertificacaoCreate(
        programa_id=_uuid(),
        titulo="Plano 1",
        descricao="Ação corretiva",
        prioridade=PrioridadePlanoAcao.ALTA,
        status=StatusPlanoAcao.PENDENTE,
    )
    assert payload.status == StatusPlanoAcao.PENDENTE
