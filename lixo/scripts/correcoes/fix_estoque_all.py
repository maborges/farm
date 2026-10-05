import re
import uuid

with open("services/api/tests/integration/operacional/test_estoque_implantacao.py", "r") as f:
    content = f.read()

# Replace the calls to _garantir_suporte_implantacao and the csv strings
def replacer(match):
    uid = uuid.uuid4().hex[:6]
    return f'codigo_interno="U{uid}",\n        nome_deposito="Dep {uid}"\n    )\n\n    csv_valido = (\n        "produto_codigo,produto_nome,deposito_nome,quantidade,custo_unitario\\n"\n        f"U{uid},Herbicida X,Dep {uid},5,10\\n"\n    )'

# First, restore generic calls
content = re.sub(
    r'codigo_interno="UNIQUE123",\n\s*nome_deposito="Deposito Conf3"\n\s*\)\n\n\s*csv_valido = \(\n\s*"produto_codigo,produto_nome,deposito_nome,quantidade,custo_unitario\\n"\n\s*"UNIQUE123,Herbicida X,Deposito Conf3,5,10\\n"\n\s*\)',
    replacer,
    content
)

with open("services/api/tests/integration/operacional/test_estoque_implantacao.py", "w") as f:
    f.write(content)

