import pytest
from httpx import AsyncClient
from app.main import app
from app.db.session import engine, async_session
from app.db.models import Base, User, Category, Listing, Reel, MediaUpload, MediaFile
from uuid import uuid4

@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        seller = User(id=uuid4(), name="Продавец", is_guest=False, demo_role="seller")
        cat = Category(id=uuid4(), slug="cat1", name="Категория 1")
        listing = Listing(
            id=uuid4(), seller_id=seller.id, category_id=cat.id,
            title="Товар продавца", price_amount=3000, status="active"
        )
        session.add_all([seller, cat, listing])
        await session.commit()
    yield

@pytest.mark.asyncio
async def test_media_upload_and_reel_creation():
    async with AsyncClient(app=app, base_url="http://test") as client:
        from app.core.security import create_access_token
        async with async_session() as session:
            from sqlalchemy import select
            seller = (await session.execute(select(User).where(User.demo_role == "seller"))).scalar_one()
            listing = (await session.execute(select(Listing))).scalar_one()
            token = create_access_token({"sub": str(seller.id)})

        # 1. Стартуем загрузку видео
        upload_res = await client.post(
            "/api/v1/media/uploads",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "kind": "video",
                "files": [{"filename": "test.mp4", "content_type": "video/mp4", "size_bytes": 1024}]
            }
        )
        assert upload_res.status_code == 200
        upload_data = upload_res.json()
        upload_id = upload_data["upload_id"]
        assert len(upload_data["files"]) == 1

        # 2. Завершаем загрузку
        complete_res = await client.post(
            f"/api/v1/media/uploads/{upload_id}/complete",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert complete_res.status_code == 202

        # 3. Создаем рилс
        reel_res = await client.post(
            "/api/v1/reels",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "listing_id": str(listing.id),
                "upload_id": upload_id,
                "show_price": True,
                "description": "Супер видео товара"
            }
        )
        assert reel_res.status_code == 201
        reel_data = reel_res.json()
        assert reel_data["status"] == "published"  # благодаря AUTO_PUBLISH=true в тестах
        assert reel_data["description"] == "Супер видео товара"

        # 4. Проверяем список моих рилсов
        my_reels = await client.get(
            "/api/v1/me/reels",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert my_reels.status_code == 200
        assert my_reels.json()["items"][0]["title"] == "Товар продавца"
