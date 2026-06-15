import re

with open("services/api/tests/integration/operacional/test_estoque_implantacao.py", "r") as f:
    content = f.read()

# Update test_confirmacao_http_bloqueia_segunda_confirmacao
content = re.sub(
    r'(codigo_interno="UNIQUE123"\n    \))',
    r'codigo_interno="UNIQUE123",\n        nome_deposito="Deposito Conf2"\n    )',
    content
)

content = re.sub(
    r'"UNIQUE123,Herbicida X,Deposito Central,5,10\\n"',
    r'"UNIQUE123,Herbicida X,Deposito Conf2,5,10\n"',
    content
)

with open("services/api/tests/integration/operacional/test_estoque_implantacao.py", "w") as f:
    f.write(content)

