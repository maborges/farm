import os
from pathlib import Path

# Fix core/models/__init__.py
init_path = Path("/opt/lampp/htdocs/farm/services/api/core/models/__init__.py")
content = init_path.read_text()
if "TentativaLogin" not in content:
    content = content.replace("UnidadeProdutivaUsuario as FazendaUsuario, ConviteAcesso", "UnidadeProdutivaUsuario as FazendaUsuario, ConviteAcesso, TentativaLogin")
    init_path.write_text(content)

# Fix test_qualidade_financeiro_step137.py
test137_path = Path("/opt/lampp/htdocs/farm/services/api/tests/test_qualidade_financeiro_step137.py")
content = test137_path.read_text()
content = content.replace(
    "from financeiro.schemas.lancamento_schema import LancamentoCreate, CATEGORIAS_VALIDAS",
    "from financeiro.schemas.lancamento_schema import LancamentoCreate, CATEGORIAS_CUSTO, CATEGORIAS_RECEITA\nCATEGORIAS_VALIDAS = CATEGORIAS_CUSTO + CATEGORIAS_RECEITA"
)
test137_path.write_text(content)

# Fix test_e2e_colheita_completa.py
teste2e_path = Path("/opt/lampp/htdocs/farm/services/api/tests/test_e2e_colheita_completa.py")
if teste2e_path.exists():
    content = teste2e_path.read_text()
    content = content.replace(
        "from operacional.models.estoque import MovimentacaoEstoque",
        "from operacional.models.estoque import EstoqueMovimento as MovimentacaoEstoque"
    )
    teste2e_path.write_text(content)

# Fix test_frota_stabilization_pass.py
frota_path = Path("/opt/lampp/htdocs/farm/services/api/tests/test_frota_stabilization_pass.py")
if frota_path.exists():
    content = frota_path.read_text()
    content = content.replace(
        "from operacional.models.estoque import MovimentacaoEstoque",
        "from operacional.models.estoque import EstoqueMovimento as MovimentacaoEstoque"
    )
    content = content.replace(
        "from core.models.auth import ", "from core.models import "
    )
    frota_path.write_text(content)

# Fix all other test files
tests_dir = Path("/opt/lampp/htdocs/farm/services/api/tests")
for p in tests_dir.rglob("*.py"):
    if p.is_file():
        content = p.read_text(errors="ignore")
        if "from core.models.auth import" in content:
            new_content = content.replace("from core.models.auth import", "from core.models import")
            p.write_text(new_content)
            print(f"Fixed {p.name}")

print("Fixes applied successfully.")
