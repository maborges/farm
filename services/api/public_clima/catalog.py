"""Catálogo oficial de municípios brasileiros com coordenadas geográficas homologadas pelo IBGE."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Final

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field

from .contracts import MunicipioItem, MunicipiosBuscaResponse

SIGLAS_UF_VALIDAS: Final[frozenset[str]] = frozenset({
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO",
})


class CatalogUnavailableError(RuntimeError):
    """Exceção levantada quando a base territorial de municípios não pode ser carregada."""


class InvalidUfError(ValueError):
    """Exceção levantada quando a UF fornecida não é uma das 27 brasileiras."""


class QueryTooShortError(ValueError):
    """Exceção levantada quando os critérios mínimos de busca não são fornecidos."""


class SearchParams(BaseModel):
    """Critérios de consulta ao catálogo de municípios."""

    model_config = ConfigDict(extra="forbid")

    query: str | None = None
    uf: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


def remover_acentos(texto: str) -> str:
    """Normaliza texto removendo acentos gráficos e convertendo para minúsculas.

    Args:
        texto: Cadeia de caracteres a normalizar.

    Returns:
        Cadeia sem diacríticos e em minúsculas.
    """
    nfkd = unicodedata.normalize("NFKD", texto)
    return nfkd.encode("ASCII", "ignore").decode("utf-8").lower().strip()


class MunicipalCatalog:
    """Gerenciador em memória do catálogo oficial de municípios brasileiros."""

    def __init__(self, data_path: Path | None = None) -> None:
        self.data_path = data_path or (Path(__file__).parent / "data" / "municipios_ibge.json")
        self._items: list[MunicipioItem] = []
        self._normalized_index: list[tuple[str, MunicipioItem]] = []
        self._error: CatalogUnavailableError | None = None
        self._load_catalog()

    def _load_catalog(self) -> None:
        """Carrega e indexa os municípios a partir do arquivo JSON oficial."""
        if not self.data_path.exists():
            logger.error("Arquivo territorial do IBGE não encontrado", path=str(self.data_path))
            self._error = CatalogUnavailableError(
                f"Catálogo territorial ausente em: {self.data_path}"
            )
            return

        try:
            with open(self.data_path, encoding="utf-8") as f:
                raw_data = json.load(f)
            self._items = [MunicipioItem.model_validate(item) for item in raw_data]
            self._normalized_index = [
                (remover_acentos(item.nome), item) for item in self._items
            ]
            logger.info("Catálogo municipal carregado", total=len(self._items))
        except Exception as exc:
            logger.error("Falha ao analisar base territorial de municípios", error=str(exc))
            self._error = CatalogUnavailableError(f"Erro ao carregar catálogo: {exc}")

    def search(self, params: SearchParams) -> MunicipiosBuscaResponse:
        """Executa busca flexível, case-insensitive e sem acentos no catálogo.

        Args:
            params: Objeto SearchParams contendo query, uf, limit e offset.

        Returns:
            MunicipiosBuscaResponse estruturada com lista de itens e metadados.

        Raises:
            CatalogUnavailableError: Se o catálogo não estiver disponível.
            InvalidUfError: Se a UF for informada e não constar nas 27 UFs válidas.
            QueryTooShortError: Se nem query válida nem UF forem fornecidas.
        """
        if self._error is not None:
            raise self._error

        uf_filtrada = self._validar_parametros(params)
        q_norm = remover_acentos(params.query) if params.query else None

        candidatos = self._filtrar_candidatos(q_norm, uf_filtrada)
        total = len(candidatos)
        paginados = candidatos[params.offset : params.offset + params.limit]

        return MunicipiosBuscaResponse(
            sucesso=True,
            total=total,
            limite=params.limit,
            offset=params.offset,
            itens=paginados,
        )

    def _validar_parametros(self, params: SearchParams) -> str | None:
        """Valida e normaliza os filtros de busca."""
        uf_normalizada: str | None = None
        if params.uf:
            uf_upper = params.uf.strip().upper()
            if uf_upper not in SIGLAS_UF_VALIDAS:
                raise InvalidUfError(
                    f"UF '{params.uf}' inválida. Utilize uma das 27 siglas federativas brasileiras."
                )
            uf_normalizada = uf_upper

        has_query = bool(params.query and len(params.query.strip()) >= 2)
        if not has_query and not uf_normalizada:
            raise QueryTooShortError(
                "Informe pelo menos 2 caracteres para o campo 'q' ou selecione uma 'uf'."
            )
        return uf_normalizada

    def _filtrar_candidatos(
        self, q_norm: str | None, uf_filtrada: str | None
    ) -> list[MunicipioItem]:
        """Aplica filtros e ranqueia os resultados com desempate determinístico."""
        resultados: list[tuple[int, str, str, MunicipioItem]] = []

        for norm_name, item in self._normalized_index:
            if uf_filtrada and item.uf != uf_filtrada:
                continue

            if q_norm:
                score = self._calcular_score(norm_name, q_norm)
                if score is not None:
                    resultados.append((score, item.nome, item.uf, item))
            else:
                resultados.append((0, item.nome, item.uf, item))

        resultados.sort(key=lambda x: (x[0], x[1], x[2]))
        return [r[3] for r in resultados]

    @staticmethod
    def _calcular_score(norm_name: str, q_norm: str) -> int | None:
        """Calcula prioridade de relevância do match textual."""
        if norm_name == q_norm:
            return 0
        if norm_name.startswith(q_norm):
            return 1
        if q_norm in norm_name:
            return 2
        return None
