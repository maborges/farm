import re
from pathlib import Path

def remove_legacy_tests_and_patches(filepath: Path):
    content = filepath.read_text()
    
    # Remove the patch blocks
    content = re.sub(
        r'\s*monkeypatch\.setattr\(\s*erp_router_module,\s*"resolve_legacy_sankhya_provider",\s*AsyncMock\(return_value=False\),\s*\)',
        '',
        content
    )
    content = re.sub(
        r'\s*monkeypatch\.setattr\(\s*erp_router_module,\s*"resolve_legacy_sankhya_provider",\s*AsyncMock\(return_value=True\),\s*\)',
        '',
        content
    )
    
    # Delete the entire test_status_erp_usa_fallback_legacy_sankhya_quando_runtime_ainda_nao_existe
    content = re.sub(
        r'    @pytest\.mark\.asyncio\n    async def test_status_erp_usa_fallback_legacy_sankhya_quando_runtime_ainda_nao_existe.*?(?=\n    @pytest|\Z)',
        '',
        content,
        flags=re.DOTALL
    )

    filepath.write_text(content)

base = Path("/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes")
remove_legacy_tests_and_patches(base / "test_erp_router.py")

print("Cleaned up test_erp_router.py")
