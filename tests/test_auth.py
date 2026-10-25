import pytest
from httpx import AsyncClient
from app.main import app
from app.db.session import engine, async_session
from app.db.models import Base
from app.core.security import create_access_token
from uuid import uuid4

@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_auth_guest():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/auth/guest", json={"name": "Тестовый гость"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["is_guest"] is True
        assert data["user"]["name"] == "Тестовый гость"

@pytest.mark.asyncio
async def test_auth_demo():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/auth/demo", json={"role": "buyer"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["is_guest"] is False

@pytest.mark.asyncio
async def test_get_me():
    async with AsyncClient(app=app, base_url="http://test") as client:
        auth_response = await client.post("/api/v1/auth/guest", json={"name": "Тест"})
        token = auth_response.json()["access_token"]
        
        response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Тест"
        assert data["is_guest"] is True

@pytest.mark.asyncio
async def test_categories():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/categories")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_onboarding_flow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        auth_response = await client.post("/api/v1/auth/guest", json={"name": "Тест"})
        token = auth_response.json()["access_token"]
        
        response = await client.get("/api/v1/users/me/onboarding", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["interests_done"] is False
        
        response = await client.put("/api/v1/users/me/interests", 
            headers={"Authorization": f"Bearer {token}"},
            json={"category_ids": ["00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002", "00000000-0000-0000-0000-000000000003"]})
        assert response.status_code == 200
        
        response = await client.get("/api/v1/users/me/onboarding", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["interests_done"] is True