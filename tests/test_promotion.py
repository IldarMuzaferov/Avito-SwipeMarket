import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.models import Category, Event, Listing, PromotionPlan, Reel, User
from app.main import app


@pytest.mark.asyncio
async def test_promotion_and_events(client):
    async with app.state.test_session_factory() as session:
        seller = User(name="Продавец", is_guest=False)
        category = Category(slug="bike", name="Велосипеды")
        session.add_all([seller, category])
        await session.flush()
        listing = Listing(
            seller_id=seller.id,
            category_id=category.id,
            title="Велосипед",
            price_amount=10000,
            status="active",
        )
        plan = PromotionPlan(
            days=7, estimated_reach=5000, price_amount=500, is_best_value=True
        )
        session.add_all([listing, plan])
        await session.flush()
        reel = Reel(
            listing_id=listing.id,
            seller_id=seller.id,
            status="published",
            media_type="photo",
        )
        session.add(reel)
        await session.commit()
        seller_id, reel_id, plan_id = seller.id, reel.id, plan.id

    headers = {"Authorization": f"Bearer {create_access_token({'sub': str(seller_id)})}"}
    plans = await client.get("/api/v1/promotion/plans")
    assert plans.status_code == 200
    assert plans.json()[0]["days"] == 7

    created = await client.post(
        f"/api/v1/reels/{reel_id}/promotions",
        headers=headers,
        json={"plan_id": str(plan_id)},
    )
    assert created.status_code == 200
    promotion_id = created.json()["promotion_id"]
    assert created.json()["status"] == "pending_payment"

    paid = await client.post(
        f"/api/v1/promotions/{promotion_id}/mock-pay",
        headers=headers,
    )
    assert paid.status_code == 200
    assert paid.json()["status"] == "active"
    assert paid.json()["active_until"]

    history = await client.get(
        f"/api/v1/reels/{reel_id}/promotions",
        headers=headers,
    )
    assert history.status_code == 200
    assert len(history.json()) == 1

    events_response = await client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "events": [
                {"type": "watch", "reel_id": str(reel_id), "value_ms": 2500},
                {"type": "expand_description", "reel_id": str(reel_id)},
            ]
        },
    )
    assert events_response.status_code == 202
    async with app.state.test_session_factory() as session:
        assert len((await session.scalars(select(Event))).all()) == 2


@pytest.mark.asyncio
async def test_event_rejects_unknown_type(client):
    response = await client.post(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {create_access_token({'sub': '00000000-0000-0000-0000-000000000000'})}"},
        json={
            "events": [
                {"type": "comment", "reel_id": "00000000-0000-0000-0000-000000000001"}
            ]
        },
    )
    assert response.status_code == 422
