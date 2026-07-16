from __future__ import annotations

import ast
from pathlib import Path


def test_sankhya_architecture_no_legacy_orm_in_decoupled_consumers() -> None:
    """Garante que os serviços desacoplados não importem diretamente o SankhyaConfig."""
    
    base_dir = Path(__file__).parent.parent.parent.parent.parent / "services" / "api" / "integracoes" / "sankhya"
    
    # Arquivos que foram desacoplados e não podem importar o model legado do sqlalchemy
    prohibited_files = [
        base_dir / "services" / "auth_service.py",
        base_dir / "services" / "nfe_financeiro_service.py",
    ]
    
    # Todos os routers também não deveriam acessar diretamente o SankhyaConfig,
    # eles devem usar a leitura canônica ou depender do sync_service.
    routers_dir = base_dir / "routers"
    if routers_dir.exists():
        for py_file in routers_dir.glob("*.py"):
            prohibited_files.append(py_file)
            
    for file_path in prohibited_files:
        if not file_path.exists():
            continue
            
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "integracoes.sankhya.models" in node.module:
                    for alias in node.names:
                        if alias.name == "SankhyaConfig":
                            raise AssertionError(
                                f"Violação de Arquitetura: {file_path.name} "
                                "importa SankhyaConfig diretamente."
                            )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "SankhyaConfig" in alias.name:
                        raise AssertionError(
                            f"Violação de Arquitetura: {file_path.name} "
                            "importa SankhyaConfig diretamente."
                        )
