import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_calculo_ajuste_desconto_e_idempotencia(client: AsyncClient, token_operacional: str, token_admin: str):
    headers = {"Authorization": f"Bearer {token_operacional}"}
    
    # 1. Create Protocol with adjustment rule
    proto_payload = {
        "nome": "Soja Especial",
        "ativo": True,
        "criterios": [
            {
                "nome": "Umidade",
                "tipo_dado": "NUMERIC",
                "unidade": "%",
                "valor_padrao": 14.0,
                "regra_ajuste_json": {
                    "type": "DISCOUNT_WEIGHT",
                    "trigger": "ABOVE_STANDARD",
                    "standard_value": 14.0,
                    "rate_per_unit": 1.0,
                    "unit": "%"
                }
            }
        ]
    }
    
    res_proto = await client.post("/api/v1/qualidade/protocolos", json=proto_payload, headers=headers)
    if res_proto.status_code != 201:
        print(f"ERROR PROTOCOL: {res_proto.status_code} - {res_proto.text}")
    assert res_proto.status_code == 201
    proto = res_proto.json()
    criterio_id = proto["criterios"][0]["id"]
    
    # 2. Create Laudo
    laudo_payload = {
        "protocolo_id": proto["id"],
        "status": "RASCUNHO",
        "resultados": [
            {
                "criterio_id": criterio_id,
                "valor_numerico": 15.5 # diff = 1.5
            }
        ]
    }
    
    res_laudo = await client.post("/api/v1/qualidade/laudos", json=laudo_payload, headers=headers)
    assert res_laudo.status_code == 201
    laudo_id = res_laudo.json()["id"]
    
    # 3. Try to calculate adjustments while RASCUNHO (should fail)
    res_calc_err = await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/calcular-ajustes", headers=headers)
    assert res_calc_err.status_code == 400
    
    # 4. Approve laudo
    res_approve = await client.patch(f"/api/v1/qualidade/laudos/{laudo_id}/status", json={"status": "APROVADO"}, headers=headers)
    assert res_approve.status_code == 200
    
    # 5. Calculate adjustments
    res_calc = await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/calcular-ajustes", headers=headers)
    assert res_calc.status_code == 201
    ajustes = res_calc.json()
    assert len(ajustes) == 1
    
    ajuste = ajustes[0]
    assert ajuste["tipo"] == "DISCOUNT_WEIGHT"
    assert ajuste["valor_numerico"] == 1.5 # 15.5 - 14.0 = 1.5 * 1.0
    assert ajuste["valor_unidade"] == "%"
    
    # 6. Idempotency test (calculate again, should overwrite and return same count)
    res_calc2 = await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/calcular-ajustes", headers=headers)
    assert res_calc2.status_code == 201
    assert len(res_calc2.json()) == 1
    
    # 7. Get endpoints verify
    res_get = await client.get(f"/api/v1/qualidade/laudos/{laudo_id}/ajustes", headers=headers)
    assert res_get.status_code == 200
    assert len(res_get.json()) == 1

@pytest.mark.asyncio
async def test_calculo_ajuste_cross_tenant_bloqueio(client: AsyncClient, token_operacional: str):
    from tests.integration.conftest import _gerar_token
    import uuid
    # Setup Protocol in Tenant 1 (token_operacional)
    h1 = {"Authorization": f"Bearer {token_operacional}"}
    proto_res = await client.post("/api/v1/qualidade/protocolos", json={
        "nome": "Cafe T1",
        "criterios": [
            {
                "nome": "Broca",
                "tipo_dado": "NUMERIC",
                "regra_ajuste_json": {
                    "type": "REJECTION",
                    "trigger": "ABOVE_STANDARD",
                    "standard_value": 3.0
                }
            }
        ]
    }, headers=h1)
    proto_id = proto_res.json()["id"]
    crit_id = proto_res.json()["criterios"][0]["id"]
    
    laudo_res = await client.post("/api/v1/qualidade/laudos", json={
        "protocolo_id": proto_id,
        "status": "RASCUNHO",
        "resultados": [{"criterio_id": crit_id, "valor_numerico": 5.0}]
    }, headers=h1)
    laudo_id = laudo_res.json()["id"]
    await client.patch(f"/api/v1/qualidade/laudos/{laudo_id}/status", json={"status": "APROVADO"}, headers=h1)
    
    # Try to calculate from Tenant 2
    tenant_2_id = uuid.uuid4()
    token_t2 = _gerar_token(tenant_2_id, ["CORE"])
    h2 = {"Authorization": f"Bearer {token_t2}"}
    res_calc_cross = await client.post(f"/api/v1/qualidade/laudos/{laudo_id}/calcular-ajustes", headers=h2)
    assert res_calc_cross.status_code in (403, 404) # Will be 404 because get_laudo won't find it for tenant 2
