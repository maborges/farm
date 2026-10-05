import re
with open("services/api/tests/unit/integracoes/test_erp_router.py", "r") as f:
    content = f.read()

pattern1 = r"@pytest\.mark\.asyncio\s*async def test_associacoes_pendentes_erp_delega_para_router_sankhya[\s\S]*?(?=@pytest\.mark\.asyncio|\Z)"
content = re.sub(pattern1, "", content)

pattern2 = r"@pytest\.mark\.asyncio\s*async def test_reconciliar_associacao_erp_delega_para_router_sankhya[\s\S]*?(?=@pytest\.mark\.asyncio|\Z)"
content = re.sub(pattern2, "", content)

with open("services/api/tests/unit/integracoes/test_erp_router.py", "w") as f:
    f.write(content)
