"""Coletores especializados por fonte institucional e parceira."""

from __future__ import annotations

from .base import BaseCollector, CollectorContext, get_collector_for_source
from .deral_pr import DeralPrCollector
from .emater_rs import EmaterRsPdfCollector
from .iea_sp import IeaSpCollector
from .partner import GenericPartnerCollector
from .seapa_mg import SeapaMgPdfCollector

__all__ = [
    "BaseCollector",
    "CollectorContext",
    "DeralPrCollector",
    "EmaterRsPdfCollector",
    "GenericPartnerCollector",
    "IeaSpCollector",
    "SeapaMgPdfCollector",
    "get_collector_for_source",
]
