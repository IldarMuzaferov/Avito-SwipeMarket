import pytest
from httpx import AsyncClient
from app.main import app
from app.db.session import engine, async_session
from app.db.models import Base, User, Category, Listing, Reel, WishlistItem, WishlistShare
from uuid import uuid4
from datetime import datetime

@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        user = User(id=uuid4(), name="Владелец", is_guest=False)
        seller = User(id=uuid4(), name="Продавец", is_guest=False)
        cat = Category(id=uuid4(), slug="cat1", name="Категория 1")
        listing = Listing(
            id=uuid4(), seller_id=seller.id, category_id=cat.id,
            title="Тестовый товар", price_amount=5000, status="active"
        )
        reel = Reel(
            id=uuid4(), listing_id=listing.id, seller_id=seller.id,
            status="published", media_type="video"
        )
        wish = WishlistItem(
            id=uuid4(), user_id=user.id, listing_id=listing.id, reel_id=reel.id
        )
        share = WishlistShare(
            user_id=user.id, token="testtoken", enabled=True, rotated_at=datetime.utcnow()
        )
        
        session.add_all([user, seller, cat, listing, reel, wish, share])
        await session.commit()
    yield

@pytest.mark.asyncio
async def test_get_wishlist():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Авторизуемся как владелец (через demo или guest, но проще выдать токен напрямую)
        from app.core.security import create_access_token
        # Узнаем ID пользователя из базы
        async with async_session() as session:
            from sqlalchemy import select
            user = (await session.execute(select(User).where(User.name == "Владелец"))).scalar_one()
            token = create_access_token({"sub": str(user.id)})

        res = await client.get("/api/v1/wishlist", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Тестовый товар"
        assert data["share"]["enabled"] is True
        assert "testtoken" in data["share"]["url"]

@pytest.mark.asyncio
async def test_public_wishlist():
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.get("/api/v1/public/wishlists/testtoken")
        assert res.status_code == 200
        data = res.json()
        assert data["owner"]["display_name"] == "Владелец"
        assert data["count"] == 1
        assert len(data["items"]) == 1

@pytest.mark.asyncio
async def test_share_toggle_and_rotate():
    async with AsyncClient(app=app, base_url="http://test") as client:
        from app.core.security import create_access_token
        async with async_session() as session:
            from sqlalchemy import select
            user = (await session.execute(select(User).where(User.name == "Владелец"))).scalar_one()
            token = create_access_token({"sub": str(user.id)})

        # Отключаем шаринг
        res = await client.put(
            "/api/v1/wishlist/share",
            headers={"Authorization": f"Bearer {token}"},
            json={"enabled": False}
        )
        assert res.status_code == 200
        assert res.json()["enabled"] is False

        # Проверяем что публичная ручка выдает 410
        pub_res = await client.get("/api/v1/public/wishlists/testtoken")
        assert pub_res.status_code == 410

        # Ротируем токен
        rotate_res = await client.post(
            "/api/v1/wishlist/share/rotate",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert rotate_res.status_code == 200
        new_url = rotate_res.json()["url"]
        assert new_url is not None
        assert "testtoken" not in new_url
