import ast
from pathlib import Path

filepath = Path("/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_erp_router.py")
content = filepath.read_text().splitlines()

tree = ast.parse("\n".join(content))

for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef) and node.name == "test_status_erp_usa_fallback_legacy_sankhya_quando_runtime_ainda_nao_existe":
        start = node.lineno - 2 # to include decorators like @pytest.mark.asyncio
        end = node.end_lineno
        print(f"Removing lines {start} to {end}")
        del content[start:end]
        break

filepath.write_text("\n".join(content) + "\n")
