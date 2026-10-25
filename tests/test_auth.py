import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.models import Category, User
from app.main import app


@pytest.mark.asyncio
async def test_health_and_guest_auth(client):
    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    response = await client.post(
        "/api/v1/auth/guest",
        json={"name": "Тестовый гость"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["name"] == "Тестовый гость"
    assert data["user"]["is_guest"] is True
    assert data["access_token"]
    assert data["refresh_token"]
    refreshed = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": data["refresh_token"]},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]


@pytest.mark.asyncio
async def test_demo_auth_and_profile(client):
    async with app.state.test_session_factory() as session:
        session.add(User(name="Покупатель", is_guest=False, demo_role="buyer"))
        await session.commit()
    response = await client.post("/api/v1/auth/demo", json={"role": "buyer"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    profile = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile.status_code == 200
    assert profile.json()["name"] == "Покупатель"


@pytest.mark.asyncio
async def test_onboarding_validation_and_skip(client):
    auth = await client.post("/api/v1/auth/guest", json={"name": "Тест"})
    token = auth.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    categories = [
        Category(slug=f"category-{index}", name=f"Категория {index}", sort=index)
        for index in range(3)
    ]
    async with app.state.test_session_factory() as session:
        session.add_all(categories)
        await session.commit()
        category_ids = [str(category.id) for category in categories]

    invalid = await client.put(
        "/api/v1/users/me/interests",
        headers=headers,
        json={"category_ids": category_ids[:2]},
    )
    assert invalid.status_code == 422

    saved = await client.put(
        "/api/v1/users/me/interests",
        headers=headers,
        json={"category_ids": category_ids},
    )
    assert saved.status_code == 204
    interests = await client.get("/api/v1/users/me/interests", headers=headers)
    assert set(interests.json()["category_ids"]) == set(category_ids)

    no_auth = await client.get("/api/v1/users/me")
    assert no_auth.status_code == 401
