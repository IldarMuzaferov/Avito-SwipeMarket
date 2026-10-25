import pytest
from httpx import AsyncClient
from app.main import app
from app.db.session import engine, async_session
from app.db.models import Base, User, Category, Listing, Reel, ReelMedia
from uuid import uuid4

@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Заполняем минимальными данными
    async with async_session() as session:
        seller = User(id=uuid4(), name="Продавец", is_guest=False)
        cat = Category(id=uuid4(), slug="cat1", name="Категория 1")
        listing = Listing(
            id=uuid4(), seller_id=seller.id, category_id=cat.id,
            title="Товар 1", price_amount=1000, status="active"
        )
        reel = Reel(
            id=uuid4(), listing_id=listing.id, seller_id=seller.id,
            status="published", media_type="video", show_price=True
        )
        media = ReelMedia(id=uuid4(), reel_id=reel.id, kind="video", url="http://video.mp4")
        
        session.add_all([seller, cat, listing, reel, media])
        await session.commit()
    yield

@pytest.mark.asyncio
async def test_get_feed():
    async with AsyncClient(app=app, base_url="http://test") as client:
        auth_res = await client.post("/api/v1/auth/guest", json={"name": "Тест"})
        token = auth_res.json()["access_token"]
        
        res = await client.get("/api/v1/feed", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Товар 1"

@pytest.mark.asyncio
async def test_swipe_like():
    async with AsyncClient(app=app, base_url="http://test") as client:
        auth_res = await client.post("/api/v1/auth/guest", json={"name": "Тест"})
        token = auth_res.json()["access_token"]
        
        feed_res = await client.get("/api/v1/feed", headers={"Authorization": f"Bearer {token}"})
        reel_id = feed_res.json()["items"][0]["reel_id"]
        
        swipe_res = await client.post(
            "/api/v1/swipes",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reel_id": reel_id,
                "action": "like",
                "client_id": str(uuid4()),
                "position": 0
            }
        )
        assert swipe_res.status_code == 200
        data = swipe_res.json()
        assert data["in_wishlist"] is True
        assert data["wishlist_count"] == 1