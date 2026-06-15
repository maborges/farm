import re

with open("services/api/tests/integration/operacional/test_compras.py", "r") as f:
    content = f.read()

# Replace test_criar_pedido_compra
new_test_1 = """# ---------------------------------------------------------------------------
# OPR-COM-01: Criar solicitação de compra
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_criar_solicitacao_compra(client, session, headers_operacional):
    \"\"\"OPR-COM-01: POST /compras/solicitacoes cria solicitacao e retorna 201\"\"\"
    await _garantir_suporte(session)

    response = await client.post(
        "/api/v1/compras/solicitacoes",
        json={
            "produto_id": str(PRODUTO_ID),
            "deposito_id": str(DEPOSITO_ID),
            "quantidade_solicitada": 500.0,
            "unidade": "KG",
            "origem": "MANUAL",
        },
        headers=headers_operacional,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "id" in data
    assert data["status"] == "PENDENTE"
"""

content = re.sub(
    r"# ---------------------------------------------------------------------------\n# OPR-COM-01: Criar pedido de compra\n# ---------------------------------------------------------------------------\n\n@pytest.mark.asyncio\nasync def test_criar_pedido_compra.*?assert data\[\"status\"\] in \(\"RASCUNHO\", \"PENDENTE\", \"ABERTO\"\)\n",
    new_test_1,
    content,
    flags=re.DOTALL
)

# Remove test_criar_pedido_com_itens completely
content = re.sub(
    r"\n\n# ---------------------------------------------------------------------------\n# OPR-COM-01b: Criar pedido e adicionar itens\n# ---------------------------------------------------------------------------\n\n@pytest.mark.asyncio\nasync def test_criar_pedido_com_itens.*?assert item_resp.json\(\)\[\"quantidade_solicitada\"\] == 500.0\n",
    "",
    content,
    flags=re.DOTALL
)

# Replace test_adicionar_cotacao_pedido
new_test_3 = """# ---------------------------------------------------------------------------
# OPR-COM-02: Adicionar cotação à solicitação
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adicionar_cotacao_solicitacao(client, session, headers_operacional):
    \"\"\"OPR-COM-02: Cotação vinculada à solicitação é registrada corretamente\"\"\"
    await _garantir_suporte(session)

    r = await client.post(
        "/api/v1/compras/solicitacoes",
        json={
            "produto_id": str(PRODUTO_ID),
            "deposito_id": str(DEPOSITO_ID),
            "quantidade_solicitada": 500.0,
            "unidade": "KG",
        },
        headers=headers_operacional,
    )
    assert r.status_code == 201
    solicitacao_id = r.json()["id"]

    cotacao = await client.post(
        f"/api/v1/compras/solicitacoes/{solicitacao_id}/cotacoes",
        json={
            "fornecedor_nome": "Fornecedor Teste",
            "valor_unitario": 3.50,
            "prazo_entrega_dias": 5,
        },
        headers=headers_operacional,
    )
    assert cotacao.status_code in (200, 201), cotacao.text
"""

content = re.sub(
    r"# ---------------------------------------------------------------------------\n# OPR-COM-02: Adicionar cotação ao pedido\n# ---------------------------------------------------------------------------\n\n@pytest.mark.asyncio\nasync def test_adicionar_cotacao_pedido.*?assert cotacao.status_code in \(200, 201\), cotacao.text\n",
    new_test_3,
    content,
    flags=re.DOTALL
)

# Replace test_aprovar_pedido
new_test_4 = """# ---------------------------------------------------------------------------
# OPR-COM-03: Aprovar cotação (Gera Pedido)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_aprovar_cotacao_gera_pedido(client, session, headers_operacional):
    \"\"\"OPR-COM-03: Aprovar cotação gera pedido APROVADO\"\"\"
    await _garantir_suporte(session)

    r = await client.post(
        "/api/v1/compras/solicitacoes",
        json={
            "produto_id": str(PRODUTO_ID),
            "deposito_id": str(DEPOSITO_ID),
            "quantidade_solicitada": 500.0,
            "unidade": "KG",
        },
        headers=headers_operacional,
    )
    assert r.status_code == 201
    solicitacao_id = r.json()["id"]

    cotacao = await client.post(
        f"/api/v1/compras/solicitacoes/{solicitacao_id}/cotacoes",
        json={
            "fornecedor_nome": "Fornecedor Teste",
            "valor_unitario": 3.50,
            "prazo_entrega_dias": 5,
        },
        headers=headers_operacional,
    )
    cotacao_id = cotacao.json()["id"]

    aprovacao = await client.patch(
        f"/api/v1/compras/solicitacoes/{solicitacao_id}/cotacoes/{cotacao_id}/aprovar",
        headers=headers_operacional,
    )
    assert aprovacao.status_code in (200, 201), aprovacao.text
    assert aprovacao.json()["status"] == "APROVADO"
"""

content = re.sub(
    r"# ---------------------------------------------------------------------------\n# OPR-COM-03: Aprovar pedido\n# ---------------------------------------------------------------------------\n\n@pytest.mark.asyncio\nasync def test_aprovar_pedido.*?assert aprovacao.json\(\)\[\"status\"\] == \"APROVADO\"\n",
    new_test_4,
    content,
    flags=re.DOTALL
)

# Replace test_receber_pedido_gera_entrada_estoque
new_test_5 = """# ---------------------------------------------------------------------------
# OPR-COM-04: Receber pedido gera entrada de estoque
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_receber_pedido_gera_entrada_estoque(client, session, headers_operacional):
    \"\"\"OPR-COM-04: Recebimento de pedido cria movimentação de entrada no estoque\"\"\"
    await _garantir_suporte(session)

    r = await client.post(
        "/api/v1/compras/solicitacoes",
        json={
            "produto_id": str(PRODUTO_ID),
            "deposito_id": str(DEPOSITO_ID),
            "quantidade_solicitada": 200.0,
            "unidade": "KG",
        },
        headers=headers_operacional,
    )
    assert r.status_code == 201
    solicitacao_id = r.json()["id"]

    cotacao = await client.post(
        f"/api/v1/compras/solicitacoes/{solicitacao_id}/cotacoes",
        json={
            "fornecedor_nome": "Fornecedor Teste",
            "valor_unitario": 3.50,
            "prazo_entrega_dias": 5,
        },
        headers=headers_operacional,
    )
    cotacao_id = cotacao.json()["id"]

    aprovacao = await client.patch(
        f"/api/v1/compras/solicitacoes/{solicitacao_id}/cotacoes/{cotacao_id}/aprovar",
        headers=headers_operacional,
    )
    assert aprovacao.status_code in (200, 201), aprovacao.text
    pedido_id = aprovacao.json()["id"]

    # No novo fluxo, o PedidoCompra tem os itens associados ao pedido.
    # O `aprovar_cotacao` gera um `ItemPedidoCompra` vinculado ao pedido e ao produto da solicitação.
    
    # Precisamos do id do item do pedido gerado
    pedido_get = await client.get(
        f"/api/v1/compras/pedidos/{pedido_id}",
        headers=headers_operacional,
    )
    assert pedido_get.status_code == 200
    # O PedidoCompraResponse na v2 tem `item_id` como UUID do produto_id (espera-se) ou `item_id` é o ID do produto?
    # O router `GET /pedidos/{pedido_id}` retorna PedidoCompraResponse que tem `item_id` e `item_nome`.
    # O patch `receber` usa `itens: [{"item_id": ...}]` que é o id da tabela `ItemPedidoCompra` se for o caso.
    # Mas wait, em `compras.py`: `pedido.item_id` é o produto! Wait! Se for isso, o receiving needs the `ItemPedidoCompra` id or `Produto` id?
    # `receber_pedido` logic is complex, it expects `ItemPedidoCompra.id` as `item_id`.
    # Let's get it directly from DB for the test.
    
    from sqlalchemy import text
    item_pedido_id = await session.execute(
        text("SELECT id FROM compras_pedido_itens WHERE pedido_id = :pedido_id LIMIT 1"),
        {"pedido_id": pedido_id}
    )
    item_pedido_id = str(item_pedido_id.scalar_one())

    # Recebe o pedido
    import uuid
    from datetime import date
    recebimento = await client.patch(
        f"/api/v1/compras/pedidos/{pedido_id}/receber",
        json={
            "deposito_id": str(DEPOSITO_ID),
            "itens": [{
                "item_id": item_pedido_id,
                "quantidade_recebida": 200.0,
                "preco_real_unitario": 3.50,
                "numero_lote": f"LOTE-{uuid.uuid4().hex[:6].upper()}",
                "data_validade": str(date(2026, 12, 31)),
            }],
            "nota_fiscal": "NF-001234",
        },
        headers=headers_operacional,
    )
    assert recebimento.status_code in (200, 201), recebimento.text
"""

content = re.sub(
    r"# ---------------------------------------------------------------------------\n# OPR-COM-04: Receber pedido gera entrada de estoque\n# ---------------------------------------------------------------------------\n\n@pytest.mark.asyncio\nasync def test_receber_pedido_gera_entrada_estoque.*?assert recebimento.status_code in \(200, 201\), recebimento.text\n",
    new_test_5,
    content,
    flags=re.DOTALL
)


with open("services/api/tests/integration/operacional/test_compras.py", "w") as f:
    f.write(content)

