import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_me_navigation_preference(client: AsyncClient, headers_admin: dict):
    response = await client.get("/api/v1/auth/me", headers=headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert "navigation_mode" in data

@pytest.mark.asyncio
async def test_update_navigation_preference_success(client: AsyncClient, headers_admin: dict):
    # Update to MEGA_MENU
    payload = {"navigation_mode": "MEGA_MENU"}
    response = await client.patch("/api/v1/auth/me/preferences/navigation", json=payload, headers=headers_admin)
    assert response.status_code == 200
    data = response.json()
    assert data["navigation_mode"] == "MEGA_MENU"

    # Verify update persisted
    me_response = await client.get("/api/v1/auth/me", headers=headers_admin)
    me_data = me_response.json()
    assert me_data["navigation_mode"] == "MEGA_MENU"
    
    # Restore to SIDEBAR
    payload = {"navigation_mode": "SIDEBAR"}
    response = await client.patch("/api/v1/auth/me/preferences/navigation", json=payload, headers=headers_admin)
    assert response.status_code == 200
    assert response.json()["navigation_mode"] == "SIDEBAR"

@pytest.mark.asyncio
async def test_update_navigation_preference_invalid(client: AsyncClient, headers_admin: dict):
    # Try invalid enum
    payload = {"navigation_mode": "INVALID_MODE"}
    response = await client.patch("/api/v1/auth/me/preferences/navigation", json=payload, headers=headers_admin)
    assert response.status_code == 422 # Pydantic validation error

@pytest.mark.asyncio
async def test_update_navigation_preference_unauthorized(client: AsyncClient):
    # Try without auth
    payload = {"navigation_mode": "MEGA_MENU"}
    response = await client.patch("/api/v1/auth/me/preferences/navigation", json=payload)
    assert response.status_code == 401

