import re
from pathlib import Path

def remove_legacy_patches(filepath: Path):
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
    
    # Remove TestFallbackLegado class completely
    # We can just match from "class TestFallbackLegado:" to the end of the file or next class
    content = re.sub(
        r'class TestFallbackLegado:.*?(?=\nclass |\Z)',
        '',
        content,
        flags=re.DOTALL
    )
    
    filepath.write_text(content)

base = Path("/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes")
remove_legacy_patches(base / "test_erp_provider_contract.py")
remove_legacy_patches(base / "test_erp_router.py")

print("Done removing patches.")
