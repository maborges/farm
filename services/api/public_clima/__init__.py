"""Módulo público de agrometeorologia e previsão do tempo do DeepFarms Agro."""

from .catalog import (
    CatalogUnavailableError,
    InvalidUfError,
    MunicipalCatalog,
    QueryTooShortError,
)
from .contracts import (
    ClimaPrevisaoResponse,
    CondicaoAtual,
    MunicipioItem,
    MunicipiosBuscaResponse,
    PrevisaoDiariaItem,
    PrevisaoHorariaItem,
    StatusOperacional,
    TipoDado,
)
from .grid import GeoGridPolicy
from .service import CoordinateValidationError, PublicClimaService

__all__ = [
    "CatalogUnavailableError",
    "ClimaPrevisaoResponse",
    "CondicaoAtual",
    "CoordinateValidationError",
    "GeoGridPolicy",
    "InvalidUfError",
    "MunicipalCatalog",
    "MunicipioItem",
    "MunicipiosBuscaResponse",
    "PrevisaoDiariaItem",
    "PrevisaoHorariaItem",
    "PublicClimaService",
    "QueryTooShortError",
    "StatusOperacional",
    "TipoDado",
]
