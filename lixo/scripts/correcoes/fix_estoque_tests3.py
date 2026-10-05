import re

with open("services/api/tests/integration/operacional/test_estoque_implantacao.py", "r") as f:
    content = f.read()

# Make _garantir_suporte_implantacao return a tuple (produto_codigo, deposito_nome)
content = content.replace(
    'async def _garantir_suporte_implantacao(session, client, headers, nome_produto: str = "Herbicida X", codigo_interno: str = "ABC123", nome_deposito: str = "Deposito Central"):',
    'async def _garantir_suporte_implantacao(session, client, headers):\n    import uuid\n    uid = uuid.uuid4().hex[:6]\n    nome_produto = f"Herbicida {uid}"\n    codigo_interno = f"UNIQ{uid}"\n    nome_deposito = f"Dep {uid}"'
)

# And return (codigo_interno, nome_produto, nome_deposito)
content = content.replace(
    '    return {"fazenda_id": fazenda_id}',
    '    return {"fazenda_id": fazenda_id, "codigo_interno": codigo_interno, "nome_produto": nome_produto, "nome_deposito": nome_deposito}'
)

with open("services/api/tests/integration/operacional/test_estoque_implantacao.py", "w") as f:
    f.write(content)

