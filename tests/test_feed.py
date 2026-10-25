from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models import Category, Listing, Reel, ReelMedia, Swipe, User, WishlistItem
from app.main import app


@pytest.mark.asyncio
async def test_feed_swipe_idempotency_and_undo(client):
    seller = User(name="Продавец", is_guest=False, demo_role="seller")
    category = Category(slug="shoes", name="Обувь")
    async with app.state.test_session_factory() as session:
        session.add_all([seller, category])
        await session.flush()
        listing = Listing(
            seller_id=seller.id,
            category_id=category.id,
            title="Кроссовки",
            description="Описание",
            price_amount=6500,
            status="active",
        )
        session.add(listing)
        await session.flush()
        reel = Reel(
            listing_id=listing.id,
            seller_id=seller.id,
            status="published",
            media_type="video",
            show_price=False,
            description="Короткое описание",
        )
        session.add(reel)
        await session.flush()
        session.add(
            ReelMedia(
                reel_id=reel.id,
                kind="video",
                url="https://cdn.example/video.mp4",
                duration_sec=20,
            )
        )
        await session.commit()
        reel_id = reel.id
        listing_id = listing.id

    auth = await client.post("/api/v1/auth/guest", json={"name": "Гость"})
    headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}
    feed = await client.get("/api/v1/feed", headers=headers)
    assert feed.status_code == 200
    card = feed.json()["items"][0]
    assert card["price"] is None
    assert card["title"] == "Кроссовки"

    swipe_payload = {
        "reel_id": str(reel_id),
        "action": "like",
        "client_id": str(uuid4()),
        "session_id": "session-test",
        "dwell_ms": 4000,
        "position": 0,
    }
    first = await client.post("/api/v1/swipes", headers=headers, json=swipe_payload)
    repeated = await client.post("/api/v1/swipes", headers=headers, json=swipe_payload)
    assert first.status_code == repeated.status_code == 200
    assert first.json()["wishlist_count"] == repeated.json()["wishlist_count"] == 1
    assert first.json()["swipes_total"] == repeated.json()["swipes_total"] == 1

    async with app.state.test_session_factory() as session:
        assert await session.scalar(
            select(WishlistItem.id).where(WishlistItem.listing_id == listing_id)
        )
        assert len((await session.scalars(select(Swipe))).all()) == 1

    undo = await client.post("/api/v1/swipes/undo", headers=headers)
    assert undo.status_code == 200
    assert str(undo.json()["reel_id"]) == str(reel_id)
    no_more_undo = await client.post("/api/v1/swipes/undo", headers=headers)
    assert no_more_undo.status_code == 404


@pytest.mark.asyncio
async def test_listing_public_detail(client):
    async with app.state.test_session_factory() as session:
        seller = User(name="Продавец", is_guest=False)
        category = Category(slug="books", name="Книги")
        session.add_all([seller, category])
        await session.flush()
        listing = Listing(
            seller_id=seller.id,
            category_id=category.id,
            title="Книга",
            price_amount=100,
            status="sold",
            listing_url="https://avito.example/listing",
        )
        session.add(listing)
        await session.commit()
        listing_id = listing.id

    response = await client.get(f"/api/v1/listings/{listing_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "sold"
