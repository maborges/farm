from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from certificacoes_esg.models import StatusPassaporte, TipoEventoPassaporte
from certificacoes_esg.schemas import (
    PassaporteRastreabilidadeCreate,
    PassaporteRastreabilidadeEventoCreate,
    PassaporteRastreabilidadeUpdateStatus,
)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def test_passaporte_rejeita_versao_invalida():
    with pytest.raises(ValidationError, match="versao"):
        PassaporteRastreabilidadeCreate(
            titulo="Passaporte",
            versao=0,
        )


def test_passaporte_publicado_exige_publicado_em():
    with pytest.raises(ValidationError, match="publicado_em"):
        PassaporteRastreabilidadeCreate(
            titulo="Passaporte",
            status=StatusPassaporte.PUBLICADO,
        )


def test_update_status_passaporte_aceita_enum_oficial():
    payload = PassaporteRastreabilidadeUpdateStatus(
        status=StatusPassaporte.REVOGADO,
        revogado_em=datetime.now(timezone.utc),
    )
    assert payload.status == StatusPassaporte.REVOGADO


def test_evento_passaporte_valida_enum_oficial():
    payload = PassaporteRastreabilidadeEventoCreate(
        passaporte_id=_uuid(),
        tipo_evento=TipoEventoPassaporte.GERADO,
        titulo="Evento",
        descricao="Descrição",
        ocorrido_em=datetime.now(timezone.utc),
        origem_tipo="RELATORIO_TECNICO",
        origem_id=_uuid(),
    )
    assert payload.tipo_evento == TipoEventoPassaporte.GERADO
