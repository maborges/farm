"""Integração oficial, HTTP-only, com a Plataforma TARA."""

from .client import TaraApiError, TaraClient

__all__ = ["TaraApiError", "TaraClient"]
