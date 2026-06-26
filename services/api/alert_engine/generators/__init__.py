"""Alert Engine canonical generators and execution infrastructure."""

from .agricultura_generator import AgriculturaAlertGenerator  # noqa: F401
from .base import BaseAlertGenerator  # noqa: F401
from .campo_generator import CampoAlertGenerationResult, CampoAlertGenerator  # noqa: F401
from .context import AlertGeneratorContext  # noqa: F401
from .esg_certificacoes_generator import ESGCertificacoesAlertGenerator  # noqa: F401
from .financeiro_generator import FinanceiroAlertGenerator  # noqa: F401
from .pecuaria_generator import PecuariaAlertGenerationResult, PecuariaAlertGenerator  # noqa: F401
from .registry import (  # noqa: F401
    AlertGeneratorRegistry,
    alert_generator_registry,
    register_alert_generator,
)
from .result import AlertGeneratorResult  # noqa: F401
from .runner import AlertGeneratorRunner  # noqa: F401

__all__ = [
    "AlertGeneratorContext",
    "AlertGeneratorRegistry",
    "AlertGeneratorResult",
    "AlertGeneratorRunner",
    "AgriculturaAlertGenerator",
    "BaseAlertGenerator",
    "CampoAlertGenerationResult",
    "CampoAlertGenerator",
    "ESGCertificacoesAlertGenerator",
    "FinanceiroAlertGenerator",
    "PecuariaAlertGenerationResult",
    "PecuariaAlertGenerator",
    "alert_generator_registry",
    "register_alert_generator",
]
