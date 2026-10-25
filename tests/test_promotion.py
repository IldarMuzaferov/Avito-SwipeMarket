import pytest
from httpx import AsyncClient
from app.main import app
from app.db.session import engine, async_session
from app.db.models import Base, User, Category, Listing, Reel, PromotionPlan
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
            title="Товар", price_amount=1000, status="active"
        )
        reel = Reel(
            id=uuid4(), listing_id=listing.id, seller_id=seller.id,
            status="published", media_type="video"
        )
        plan = PromotionPlan(
            id=uuid4(), days=7, estimated_reach=5000,
            price_amount=500, is_best_value=True
        )
        session.add_all([seller, cat, listing, reel, plan])
        await session.commit()
    yield

@pytest.mark.asyncio
async def test_promotion_flow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        from app.core.security import create_access_token
        async with async_session() as session:
            from sqlalchemy import select
            seller = (await session.execute(select(User).where(User.demo_role == "seller"))).scalar_one()
            reel = (await session.execute(select(Reel))).scalar_one()
            plan = (await session.execute(select(PromotionPlan))).scalar_one()
            token = create_access_token({"sub": str(seller.id)})

        # 1. Получаем тарифы
        plans_res = await client.get("/api/v1/promotion/plans")
        assert plans_res.status_code == 200
        assert len(plans_res.json()) == 1

        # 2. Создаем продвижение
        prom_res = await client.post(
            f"/api/v1/reels/{reel.id}/promotions",
            headers={"Authorization": f"Bearer {token}"},
            json={"plan_id": str(plan.id)}
        )
        assert prom_res.status_code == 200
        prom_data = prom_res.json()
        assert prom_data["status"] == "pending_payment"
        prom_id = prom_data["promotion_id"]

        # 3. Эмулируем оплату
        pay_res = await client.post(
            f"/api/v1/promotions/{prom_id}/mock-pay",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert pay_res.status_code == 200
        assert pay_res.json()["status"] == "active"

@pytest.mark.asyncio
async def test_events():
    async with AsyncClient(app=app, base_url="http://test") as client:
        from app.core.security import create_access_token
        async with async_session() as session:
            from sqlalchemy import select
            seller = (await session.execute(select(User).where(User.demo_role == "seller"))).scalar_one()
            reel = (await session.execute(select(Reel))).scalar_one()
            token = create_access_token({"sub": str(seller.id)})

        res = await client.post(
            "/api/v1/events",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "events": [
                    {"type": "watch", "reel_id": str(reel.id), "value_ms": 2500},
                    {"type": "expand_description", "reel_id": str(reel.id)}
                ]
            }
        )
        assert res.status_code == 202
