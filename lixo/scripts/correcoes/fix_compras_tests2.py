import re

with open("services/api/tests/integration/operacional/test_compras.py", "r") as f:
    content = f.read()

add_em_cotacao = """    solicitacao_id = r.json()["id"]

    await client.patch(
        f"/api/v1/compras/solicitacoes/{solicitacao_id}/status",
        json={"status": "EM_COTACAO"},
        headers=headers_operacional,
    )
"""

content = re.sub(
    r"    assert r\.status_code == 201\n    solicitacao_id = r\.json\(\)\[\"id\"\]\n",
    "    assert r.status_code == 201\n" + add_em_cotacao,
    content,
    flags=re.MULTILINE
)

with open("services/api/tests/integration/operacional/test_compras.py", "w") as f:
    f.write(content)

