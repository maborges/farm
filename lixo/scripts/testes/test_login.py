import sys
import asyncio
import httpx
sys.path.append("/opt/lampp/htdocs/farm/services/api")
try:
    from main import app
except Exception as e:
    print(f"Failed to import app: {e}")
    sys.exit(1)

async def test_login():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        try:
            response = await ac.post("/api/v1/auth/login", json={"email": "test@example.com", "senha": "password"})
            print(f"Status: {response.status_code}")
            print(f"Body: {response.text}")
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(test_login())
