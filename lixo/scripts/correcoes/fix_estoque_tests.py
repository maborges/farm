import re

with open("services/api/tests/integration/operacional/test_estoque_implantacao.py", "r") as f:
    content = f.read()

# Remove DELETE FROM estoque_movimentos
content = content.replace(
    '    await session.execute(text("""\n        DELETE FROM estoque_movimentos WHERE tenant_id = :tenant_id\n    """), {"tenant_id": str(tenant_id)})\n',
    ''
)

# Change signature to accept nome_deposito
content = content.replace(
    'nome_produto: str = "Herbicida X", codigo_interno: str = "ABC123"',
    'nome_produto: str = "Herbicida X", codigo_interno: str = "ABC123", nome_deposito: str = "Deposito Central"'
)

# Change INSERT query to use :nome_deposito
content = content.replace(
    "VALUES (:id, :tenant_id, :unidade_produtiva_id, 'Deposito Central', 'ALMOXARIFADO', true)",
    "VALUES (:id, :tenant_id, :unidade_produtiva_id, :nome_deposito, 'ALMOXARIFADO', true)"
)

# Change INSERT bind to include "nome_deposito": nome_deposito
content = content.replace(
    '"unidade_produtiva_id": str(fazenda_id),\n    })',
    '"unidade_produtiva_id": str(fazenda_id),\n        "nome_deposito": nome_deposito,\n    })'
)

with open("services/api/tests/integration/operacional/test_estoque_implantacao.py", "w") as f:
    f.write(content)

