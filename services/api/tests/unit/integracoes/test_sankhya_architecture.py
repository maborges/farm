from __future__ import annotations

import ast
from pathlib import Path

PROHIBITED_SYMBOL = "SankhyaConfig"
LEGACY_MODULE = "integracoes.sankhya.models"


def _prohibited_files(base_dir: Path) -> list[Path]:
    """Arquivos que foram desacoplados e não podem importar o model legado do sqlalchemy."""
    prohibited_files = [
        base_dir / "services" / "auth_service.py",
        base_dir / "services" / "nfe_financeiro_service.py",
    ]

    # Todos os routers também não deveriam acessar diretamente o SankhyaConfig,
    # eles devem usar a leitura canônica ou depender do sync_service.
    routers_dir = base_dir / "routers"
    if routers_dir.exists():
        prohibited_files.extend(sorted(routers_dir.glob("*.py")))

    return prohibited_files


def _module_matches_legacy(module: str) -> bool:
    return module == LEGACY_MODULE or module.endswith("." + LEGACY_MODULE)


def _dotted_name(node: ast.expr) -> str | None:
    """Resolve `a.b.c` (Attribute/Name aninhados) para a string 'a.b.c', senão None."""
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


def check_source_for_legacy_orm_import(content: str, file_label: str = "<source>") -> None:
    """Levanta AssertionError se `content` importar/acessar o ORM legado SankhyaConfig.

    Cobre: `from integracoes.sankhya.models import SankhyaConfig` (com ou sem alias),
    `import integracoes.sankhya.models` seguido de acesso `modulo.SankhyaConfig`, e
    imports locais dentro de função (ast.walk percorre o corpo de qualquer FunctionDef).
    Schemas homônimos (`SankhyaConfigCreate`, `SankhyaConfigResponse`) são ignorados
    por comparação exata de nome, não substring.
    """
    tree = ast.parse(content)

    module_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and _module_matches_legacy(node.module):
                for alias in node.names:
                    if alias.name == PROHIBITED_SYMBOL:
                        raise AssertionError(
                            f"Violação de Arquitetura: {file_label} "
                            f"importa {PROHIBITED_SYMBOL} diretamente."
                        )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if _module_matches_legacy(alias.name):
                    module_aliases.add(alias.asname or alias.name)

    if module_aliases:
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == PROHIBITED_SYMBOL:
                dotted = _dotted_name(node.value)
                if dotted in module_aliases:
                    raise AssertionError(
                        f"Violação de Arquitetura: {file_label} "
                        f"acessa {PROHIBITED_SYMBOL} via import de módulo completo."
                    )


def test_sankhya_architecture_no_legacy_orm_in_decoupled_consumers() -> None:
    """Garante que os serviços desacoplados não importem diretamente o SankhyaConfig."""

    base_dir = Path(__file__).resolve().parent.parent.parent.parent / "integracoes" / "sankhya"
    assert base_dir.exists(), f"Diretório de referência do guardrail não existe: {base_dir}"

    for file_path in _prohibited_files(base_dir):
        if not file_path.exists():
            continue

        content = file_path.read_text(encoding="utf-8")
        check_source_for_legacy_orm_import(content, file_label=file_path.name)


def test_sankhya_architecture_guardrail_detects_prohibited_import() -> None:
    """Teste negativo: comprova que o analisador falha diante de uma violação real."""
    direct_import = "from integracoes.sankhya.models import SankhyaConfig\n"
    try:
        check_source_for_legacy_orm_import(direct_import, file_label="violation_direct.py")
    except AssertionError:
        pass
    else:
        raise AssertionError("Guardrail deveria falhar diante de import direto proibido.")

    aliased_import = "from integracoes.sankhya.models import SankhyaConfig as LegacyConfig\n"
    try:
        check_source_for_legacy_orm_import(aliased_import, file_label="violation_alias.py")
    except AssertionError:
        pass
    else:
        raise AssertionError("Guardrail deveria falhar diante de import proibido com alias.")

    module_import_with_usage = (
        "import integracoes.sankhya.models as legacy_models\n"
        "\n"
        "def load(db):\n"
        "    return db.query(legacy_models.SankhyaConfig).first()\n"
    )
    try:
        check_source_for_legacy_orm_import(
            module_import_with_usage, file_label="violation_module.py"
        )
    except AssertionError:
        pass
    else:
        raise AssertionError(
            "Guardrail deveria falhar diante de import de módulo completo com uso de SankhyaConfig."
        )


def test_sankhya_architecture_guardrail_allows_homonym_schema() -> None:
    """Schemas homônimos (SankhyaConfigCreate/Response) não devem gerar falso positivo."""
    safe_source = (
        "from integracoes.sankhya.schemas import SankhyaConfigCreate, SankhyaConfigResponse\n"
    )
    check_source_for_legacy_orm_import(safe_source, file_label="safe_schema.py")
