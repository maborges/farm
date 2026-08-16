"""Routers para agricola/ndvi_avancado."""

from .ndvi import router as ndvi_router
from .meteorologia import router as meteorologia_router

__all__ = ["ndvi_router", "meteorologia_router"]
