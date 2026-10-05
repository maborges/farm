import sys
import asyncio
import httpx
sys.path.append("/opt/lampp/htdocs/farm/services/api")
from main import app

async def test_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        try:
            response = await ac.post("/api/v1/financeiro/planos-conta/")
            print(f"Status: {response.status_code}")
            print(f"Body: {response.text}")
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(test_endpoint())
