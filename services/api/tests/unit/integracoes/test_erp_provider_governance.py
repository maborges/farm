"""Testes estáticos de governança de imports ERP.

Falham se módulos genéricos do core ERP importarem diretamente
implementações Sankhya, garantindo que o acoplamento não volte.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SERVICES_ROOT = Path(__file__).resolve().parents[3]

# Módulos genéricos que NÃO podem importar Sankhya.
GENERIC_MODULES = [
    SERVICES_ROOT / "integracoes" / "erp" / "router.py",
    SERVICES_ROOT / "integracoes" / "erp_readiness_service.py",
]

# Imports bloqueados nos módulos genéricos.
BLOCKED_IMPORTS = {
    "integracoes.sankhya.routers",
    "integracoes.sankhya.schemas",
    "integracoes.sankhya.services",
    "integracoes.sankhya.models",
}

BLOCKED_NAMES = {
    "SankhyaSyncService",
    "SankhyaCanonicalAdapter",
    "SankhyaGatewayAuthService",
    "SankhyaPessoaService",
    "SankhyaProdutoService",
    "SankhyaNFeService",
    "SankhyaFinanceiroService",
    "SankhyaConfigCreate",
    "SankhyaConfigResponse",
    "SankhyaTimelineItemResponse",
    "SankhyaOperationalDiagnosisResponse",
    "SankhyaHealthResponse",
    "SankhyaSyncStatusResponse",
}

# Módulos onde o import de Sankhya É permitido.
ALLOWED_MODULES = {
    SERVICES_ROOT / "integracoes" / "erp" / "provider_bootstrap.py",
    SERVICES_ROOT / "integracoes" / "erp" / "providers" / "sankhya_runtime.py",
}


def _extract_imports(filepath: Path) -> list[str]:
    """Extrai todos os módulos importados de um arquivo Python."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _extract_imported_names(filepath: Path) -> list[str]:
    """Extrai todos os nomes importados de um arquivo Python."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))

    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
    return names


class TestGovernancaImports:
    """Verifica que módulos genéricos não importam Sankhya."""

    @pytest.mark.parametrize(
        "module_path",
        GENERIC_MODULES,
        ids=[str(p.relative_to(SERVICES_ROOT)) for p in GENERIC_MODULES],
    )
    def test_modulo_generico_nao_importa_sankhya_modules(
        self,
        module_path: Path,
    ) -> None:
        """Nenhum módulo genérico pode fazer 'from integracoes.sankhya.* import ...'."""
        assert module_path.exists(), f"Arquivo não encontrado: {module_path}"

        imports = _extract_imports(module_path)
        violations = [
            imp for imp in imports
            if any(imp.startswith(blocked) for blocked in BLOCKED_IMPORTS)
        ]

        assert not violations, (
            f"O módulo genérico {module_path.name} importa pacotes Sankhya bloqueados: "
            f"{violations}. Esses imports devem estar apenas no bootstrap ou na "
            f"implementação runtime."
        )

    @pytest.mark.parametrize(
        "module_path",
        GENERIC_MODULES,
        ids=[str(p.relative_to(SERVICES_ROOT)) for p in GENERIC_MODULES],
    )
    def test_modulo_generico_nao_importa_classes_sankhya(
        self,
        module_path: Path,
    ) -> None:
        """Nenhum módulo genérico pode importar classes concretas do Sankhya."""
        assert module_path.exists(), f"Arquivo não encontrado: {module_path}"

        names = _extract_imported_names(module_path)
        violations = [name for name in names if name in BLOCKED_NAMES]

        assert not violations, (
            f"O módulo genérico {module_path.name} importa classes Sankhya bloqueadas: "
            f"{violations}."
        )

    def test_bootstrap_e_unico_ponto_de_registro(self) -> None:
        """O bootstrap é o único módulo ERP genérico que importa SankhyaProviderRuntime."""
        bootstrap_path = SERVICES_ROOT / "integracoes" / "erp" / "provider_bootstrap.py"
        assert bootstrap_path.exists()

        names = _extract_imported_names(bootstrap_path)
        assert "SankhyaProviderRuntime" in names

    def test_sankhya_runtime_e_unica_implementacao_no_pacote_providers(self) -> None:
        """Verifica que o pacote providers contém a implementação Sankhya."""
        runtime_path = (
            SERVICES_ROOT / "integracoes" / "erp" / "providers" / "sankhya_runtime.py"
        )
        assert runtime_path.exists()

        names = _extract_imported_names(runtime_path)
        assert "SankhyaSyncService" in names

    def test_router_nao_contem_branch_por_provider_slug(self) -> None:
        """O router não pode conter 'if provider_slug == \"sankhya\"' ou equivalente."""
        router_path = SERVICES_ROOT / "integracoes" / "erp" / "router.py"
        source = router_path.read_text(encoding="utf-8")

        assert 'provider_slug == "sankhya"' not in source
        assert "provider_slug == 'sankhya'" not in source
        assert 'slug == "sankhya"' not in source

    def test_allowed_modules_podem_importar_sankhya(self) -> None:
        """Confirma que os módulos permitidos existem e importam Sankhya."""
        for module_path in ALLOWED_MODULES:
            assert module_path.exists(), f"Módulo permitido não encontrado: {module_path}"
            imports = _extract_imports(module_path)
            has_sankhya = any(
                "sankhya" in imp for imp in imports
            )
            assert has_sankhya, (
                f"Módulo {module_path.name} deveria importar algo do pacote Sankhya "
                f"mas não importa."
            )
