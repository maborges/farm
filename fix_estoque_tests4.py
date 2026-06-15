import re

with open("services/api/tests/integration/operacional/test_estoque_implantacao.py", "r") as f:
    content = f.read()

# Replace csv_valido with f-string based on suporte
content = re.sub(
    r'csv_valido = \(\n\s*"produto_codigo,produto_nome,deposito_nome,quantidade,custo_unitario\\n"\n\s*"UNIQUE123,Herbicida X,Deposito Conf2,5,10\\n"\n\s*\).encode\("utf-8"\)',
    'csv_valido = (\n        f"produto_codigo,produto_nome,deposito_nome,quantidade,custo_unitario\\n"\n        f"{suporte[\'codigo_interno\']},{suporte[\'nome_produto\']},{suporte[\'nome_deposito\']},5,10\\n"\n    ).encode("utf-8")',
    content
)

# test_csv_duplicado_retorna_erro_controlado
content = re.sub(
    r'csv_invalido = \(\n\s*"produto_codigo,produto_nome,deposito_nome,quantidade,custo_unitario\\n"\n\s*"UNIQUE123,Herbicida X,Deposito Conf2,5,10\\n"\n\s*"UNIQUE123,Herbicida X,Deposito Conf2,5,10\\n"\n\s*\).encode\("utf-8"\)',
    'csv_invalido = (\n        f"produto_codigo,produto_nome,deposito_nome,quantidade,custo_unitario\\n"\n        f"{suporte[\'codigo_interno\']},{suporte[\'nome_produto\']},{suporte[\'nome_deposito\']},5,10\\n"\n        f"{suporte[\'codigo_interno\']},{suporte[\'nome_produto\']},{suporte[\'nome_deposito\']},5,10\\n"\n    ).encode("utf-8")',
    content
)

# test_confirmacao_http_bloqueia_sessao_com_erro
content = re.sub(
    r'csv_invalido = \(\n\s*"produto_codigo,produto_nome,deposito_nome,quantidade,custo_unitario\\n"\n\s*"UNIQUE123,Herbicida X,Deposito Conf2,-5,10\\n"\n\s*\).encode\("utf-8"\)',
    'csv_invalido = (\n        f"produto_codigo,produto_nome,deposito_nome,quantidade,custo_unitario\\n"\n        f"{suporte[\'codigo_interno\']},{suporte[\'nome_produto\']},{suporte[\'nome_deposito\']},-5,10\\n"\n    ).encode("utf-8")',
    content
)


with open("services/api/tests/integration/operacional/test_estoque_implantacao.py", "w") as f:
    f.write(content)

