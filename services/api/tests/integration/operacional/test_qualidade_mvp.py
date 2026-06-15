import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

@pytest.mark.asyncio
async def test_create_protocolo_and_laudo(client: AsyncClient, token_admin: str):
    headers = {"Authorization": f"Bearer {token_admin}"}
    
    # 1. Create Protocolo
    protocolo_payload = {
        "nome": "Qualidade Café SCA",
        "ativo": True,
        "criterios": [
            {
                "nome": "Umidade",
                "tipo_dado": "NUMERIC",
                "unidade": "%",
                "max_aceitavel": 12.0
            },
            {
                "nome": "Impurezas",
                "tipo_dado": "NUMERIC",
                "unidade": "%",
                "max_aceitavel": 1.0
            }
        ]
    }
    
    resp_prot = await client.post("/api/v1/qualidade/protocolos", json=protocolo_payload, headers=headers)
    assert resp_prot.status_code == 201, resp_prot.text
    protocolo_data = resp_prot.json()
    assert protocolo_data["nome"] == "Qualidade Café SCA"
    assert len(protocolo_data["criterios"]) == 2
    
    protocolo_id = protocolo_data["id"]
    criterio_umidade_id = next(c["id"] for c in protocolo_data["criterios"] if c["nome"] == "Umidade")
    criterio_impureza_id = next(c["id"] for c in protocolo_data["criterios"] if c["nome"] == "Impurezas")
    
    # 2. Create Laudo
    laudo_payload = {
        "protocolo_id": protocolo_id,
        "status": "CONCLUIDO",
        "resultados": [
            {
                "criterio_id": criterio_umidade_id,
                "valor_numerico": 11.5
            },
            {
                "criterio_id": criterio_impureza_id,
                "valor_numerico": 0.8
            }
        ]
    }
    
    resp_laudo = await client.post("/api/v1/qualidade/laudos", json=laudo_payload, headers=headers)
    assert resp_laudo.status_code == 201, resp_laudo.text
    laudo_data = resp_laudo.json()
    assert laudo_data["protocolo_id"] == protocolo_id
    assert laudo_data["status"] == "CONCLUIDO"
    assert len(laudo_data["resultados"]) == 2
