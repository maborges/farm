import asyncio
import httpx
from fastapi import Request
from main import app
from jose import jwt
from core.config import settings
from datetime import datetime, timedelta

async def test_api():
    # Criar um token mockado válido
    tenant_id = "74b78031-2c24-4678-b135-e18d2b2c2be0"
    user_id = "00000000-0000-0000-0000-000000000001"
    
    payload = {
        "tenant_id": tenant_id,
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(days=1)
    }
    
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "x-tenant-id": tenant_id
    }
    
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Testa a exclusão
        print("Testing DELETE...")
        response = await client.delete("/api/v1/unidades-produtivas/932ac45d-429f-4109-ab4b-b84457bda21d", headers=headers)
        print("STATUS:", response.status_code)
        print("BODY:", response.text)
        print("HEADERS:", response.headers)

if __name__ == "__main__":
    asyncio.run(test_api())
