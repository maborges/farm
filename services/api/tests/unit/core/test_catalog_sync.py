"""
Testes unitários do CORE para garantir sincronismo entre catálogo backend e frontend.

Objetivo:
- evitar divergência entre `services/api/core/constants.py`
- `apps/web/src/lib/constants/modulos.ts`
- `apps/web/src/lib/constants/pacotes.ts`
"""

from __future__ import annotations

import re
from pathlib import Path

from core.constants import Modulos, ModuloMetadata


ROOT = Path(__file__).resolve().parents[5]
FRONTEND_MODULOS = ROOT / "apps/web/src/lib/constants/modulos.ts"
FRONTEND_PACOTES = ROOT / "apps/web/src/lib/constants/pacotes.ts"


def _backend_module_map() -> dict[str, str]:
    return {
        name: value
        for name, value in vars(Modulos).items()
        if not name.startswith("_") and isinstance(value, str)
    }


def _backend_module_names() -> set[str]:
    return set(_backend_module_map().keys())


def _parse_frontend_module_map() -> dict[str, str]:
    text = FRONTEND_MODULOS.read_text(encoding="utf-8")
    pattern = re.compile(r"^\s*([A-Z0-9_]+):\s*\"([A-Z0-9_]+)\"", re.MULTILINE)
    return {name: value for name, value in pattern.findall(text)}


def _parse_frontend_package_modules() -> set[str]:
    text = FRONTEND_PACOTES.read_text(encoding="utf-8")
    return set(re.findall(r"Modulos\.([A-Z0-9_]+)", text))


def test_catalogo_modulos_backend_e_frontend_estao_sincronizados():
    backend = _backend_module_map()
    frontend = _parse_frontend_module_map()

    assert backend == frontend


def test_todos_os_modulos_tem_metadata():
    backend_values = set(_backend_module_map().values())
    metadata_keys = set(ModuloMetadata.CATALOGO.keys())

    assert backend_values == metadata_keys


def test_pacotes_frontend_usam_so_modulos_conhecidos():
    backend_names = _backend_module_names()
    package_modules = _parse_frontend_package_modules()

    assert package_modules <= backend_names
