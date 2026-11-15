from __future__ import annotations

from typing import Any
from uuid import UUID


BALANCA_COMPLETED_EVENT = "balanca.pesagem.concluida.v1"

_REFERENCE_TYPES = {
    "agricola:romaneio": "COLHEITA",
    "financeiro:comercializacao": "VENDA",
    "operacional:compra": "COMPRA",
    "pecuaria:animal": "PECUARIA",
}


def completed_weighing_metadata(event: Any) -> dict[str, Any]:
    """Normaliza o envelope externo para os consumidores legados do DeepFarms."""

    metadata = dict(getattr(event, "metadata", {}) or {})
    payload = metadata.get("payload") or getattr(event, "payload", None) or {}
    external_reference = metadata.get("external_reference") or getattr(
        event, "external_reference", None
    )
    if not external_reference:
        return metadata

    prefix, separator, origin_id = str(external_reference).rpartition(":")
    origin_type = _REFERENCE_TYPES.get(prefix)
    if not separator or not origin_type:
        return metadata
    try:
        UUID(origin_id)
    except ValueError:
        return metadata

    normalized = {
        **metadata,
        "origem_tipo": origin_type,
        "origem_id": origin_id,
        "peso_bruto_kg": payload.get("peso_bruto_kg", payload.get("peso_aferido_kg")),
        "peso_tara_kg": payload.get("peso_tara_kg", "0"),
        "peso_liquido_kg": payload.get("peso_liquido_kg"),
    }
    return normalized
