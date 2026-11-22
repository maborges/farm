"""Interface base e registro de coletores por estratégia/slug."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from ..contracts import CollectorExecutionPayload
from ..fetcher import SafeHttpFetcher
from ..models import AgroDataSource


@dataclass(frozen=True, slots=True)
class CollectorContext:
    """Contexto imutável passado a um coletor para execução única."""

    source: AgroDataSource
    fetcher: SafeHttpFetcher
    last_etag: str | None = None
    last_modified: str | None = None
    ia_callable: Callable[..., Awaitable[str]] | None = None


class BaseCollector(ABC):
    """Contrato abstrato de coletores de dados públicos ou parceiros."""

    slug: str

    @abstractmethod
    async def collect(self, ctx: CollectorContext) -> CollectorExecutionPayload:
        """Executa coleta segura e extração estruturada da fonte.

        Args:
            ctx: Contexto contendo fonte homologada, fetcher seguro e cache HTTP.

        Returns:
            ``CollectorExecutionPayload`` com bytes brutos e observações extraídas.
        """


def get_collector_for_source(source_or_slug: str | AgroDataSource) -> BaseCollector:
    """Resolve a instância de coletor homologada para a fonte ou ``slug``.

    Args:
        source_or_slug: Objeto ``AgroDataSource`` ou string de identificação ``slug``.

    Returns:
        Coletor concreto que implementa ``BaseCollector``.

    Raises:
        KeyError: Se não houver coletor habilitado para o slug/estratégia.
    """
    from .deral_pr import DeralPrCollector
    from .emater_rs import EmaterRsPdfCollector
    from .iea_sp import IeaSpCollector
    from .partner import GenericPartnerCollector
    from .seapa_mg import SeapaMgPdfCollector

    registry: dict[str, BaseCollector] = {
        DeralPrCollector.slug: DeralPrCollector(),
        IeaSpCollector.slug: IeaSpCollector(),
        EmaterRsPdfCollector.slug: EmaterRsPdfCollector(),
        SeapaMgPdfCollector.slug: SeapaMgPdfCollector(),
        GenericPartnerCollector.slug: GenericPartnerCollector(),
    }
    if isinstance(source_or_slug, str):
        slug = source_or_slug
        estrategia = None
        licenca = None
    else:
        slug = source_or_slug.slug
        estrategia = source_or_slug.estrategia_coleta
        licenca = source_or_slug.tipo_licenca

    if slug in registry:
        return registry[slug]
    if licenca == "PARCEIRO_AUTORIZADO" or estrategia == "GENERICO_PARCEIRO":
        return registry[GenericPartnerCollector.slug]
    raise KeyError(f"Coletor '{slug}' não habilitado ou indisponível nesta fase.")
