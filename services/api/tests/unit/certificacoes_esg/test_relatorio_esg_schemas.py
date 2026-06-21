from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from certificacoes_esg.models import StatusPassaporte, StatusRelatorioESG, TipoEventoPassaporte
from certificacoes_esg.schemas import (
    PassaporteRastreabilidadeCreate,
    PassaporteRastreabilidadeEventoCreate,
    RelatorioESGCreate,
    RelatorioESGIndicadorCreate,
)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def test_relatorio_rejeita_periodo_invalido():
    inicio = datetime.now(timezone.utc)
    with pytest.raises(ValidationError, match="periodo_fim"):
        RelatorioESGCreate(
            titulo="Relatório ESG",
            periodo_inicio=inicio,
            periodo_fim=inicio - timedelta(days=1),
            status=StatusRelatorioESG.RASCUNHO,
        )


def test_relatorio_publicado_exige_hash_e_data():
    with pytest.raises(ValidationError, match="publicado_em"):
        RelatorioESGCreate(
            titulo="Relatório ESG",
            status=StatusRelatorioESG.PUBLICADO,
        )


def test_indicador_rejeita_valor_negativo():
    with pytest.raises(ValidationError, match="valor"):
        RelatorioESGIndicadorCreate(
            relatorio_id=_uuid(),
            nome="Emissões",
            valor=-1,
        )


def test_passaporte_publicado_exige_hash_e_data():
    with pytest.raises(ValidationError, match="publicado_em"):
        PassaporteRastreabilidadeCreate(
            titulo="Passaporte",
            status=StatusPassaporte.PUBLICADO,
        )


def test_evento_exige_snapshot_hash_quando_snapshot_existe():
    with pytest.raises(ValidationError, match="snapshot_hash"):
        PassaporteRastreabilidadeEventoCreate(
            passaporte_id=_uuid(),
            tipo_evento=TipoEventoPassaporte.GERADO,
            titulo="Evento",
            descricao="Descrição",
            ocorrido_em=datetime.now(timezone.utc),
            origem_tipo="RELATORIO_TECNICO",
            origem_id=_uuid(),
            snapshot_json={"a": 1},
        )
