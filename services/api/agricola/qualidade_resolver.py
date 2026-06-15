from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from agricola.colheita.models import ProdutoColhido
from agricola.romaneios.models import RomaneioColheita


@dataclass(frozen=True)
class QualidadeEfetiva:
    qualidade_laudo_id: UUID | None
    qualidade_status: str | None
    peso_desconto_qualidade_kg: float
    peso_liquido_comercial_kg: float | None


def resolver_qualidade_efetiva(
    produto_colhido: ProdutoColhido | None = None,
    romaneio: RomaneioColheita | None = None,
) -> QualidadeEfetiva:
    """Resolve os campos de qualidade já persistidos sem alterar a regra vigente."""
    return QualidadeEfetiva(
        qualidade_laudo_id=_resolver_attr(produto_colhido, romaneio, "qualidade_laudo_id"),
        qualidade_status=_resolver_attr(produto_colhido, romaneio, "qualidade_status"),
        peso_desconto_qualidade_kg=float(
            _resolver_attr(produto_colhido, romaneio, "peso_desconto_qualidade_kg", default=0) or 0
        ),
        peso_liquido_comercial_kg=_coerce_float_or_none(
            produto_colhido,
            romaneio,
            "peso_liquido_comercial_kg",
        ),
    )


def _resolver_attr(
    produto_colhido: ProdutoColhido | None,
    romaneio: RomaneioColheita | None,
    attr: str,
    default=None,
):
    if produto_colhido is not None:
        valor = getattr(produto_colhido, attr, None)
        if valor is not None:
            return valor

    if romaneio is not None:
        valor = getattr(romaneio, attr, None)
        if valor is not None:
            return valor

    return default


def _coerce_float_or_none(
    produto_colhido: ProdutoColhido | None,
    romaneio: RomaneioColheita | None,
    attr: str,
):
    valor = _resolver_attr(produto_colhido, romaneio, attr)
    if valor is None:
        return None
    return float(valor)
