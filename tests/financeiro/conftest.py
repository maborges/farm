"""
conftest.py local para /tests/financeiro

Garante que services/api está no sys.path antes de qualquer import
de módulo financeiro nos testes dessa pasta.
"""
import sys
from pathlib import Path

_api_path = str(Path(__file__).parent.parent.parent / "services" / "api")
if _api_path not in sys.path:
    sys.path.insert(0, _api_path)
