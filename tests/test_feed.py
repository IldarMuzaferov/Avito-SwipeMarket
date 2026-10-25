from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.db.models import (
    Category,
    Event,
    Listing,
    Promotion,
    PromotionPlan,
    Reel,
    ReelMedia,
    Swipe,
    User,
    UserInterest,
    WishlistItem,
)
from app.main import app
from app.services.recommender import recommend


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


@pytest.mark.asyncio
async def test_feed_filters_swiped_reels_before_ad_insertion_and_keeps_trailing_ads(
    client,
):
    auth = await client.post("/api/v1/auth/guest", json={"name": "Покупатель"})
    headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}
    user_id = UUID(auth.json()["user"]["id"])
    now = datetime.now(timezone.utc)

    async with app.state.test_session_factory() as session:
        seller = User(name="Продавец", is_guest=False)
        category = Category(slug="feed-ads", name="Объявления")
        plan = PromotionPlan(days=1, estimated_reach=100, price_amount=100)
        session.add_all([seller, category, plan])
        await session.flush()

        organic_ids = []
        promoted_ids = []
        excluded_ids = []
        old_skip_id = None
        for index in range(15):
            listing = Listing(
                seller_id=seller.id,
                category_id=category.id,
                title=f"Товар {index}",
                description="Описание",
                price_amount=1000 + index,
                status="active",
            )
            session.add(listing)
            await session.flush()
            reel = Reel(
                listing_id=listing.id,
                seller_id=seller.id,
                status="published",
                media_type="video",
                show_price=True,
                enabled=True,
                published_at=now - timedelta(minutes=index),
            )
            session.add(reel)
            await session.flush()
            if index < 5:
                organic_ids.append(reel.id)
            elif index < 12:
                promoted_ids.append(reel.id)
                session.add(
                    Promotion(
                        reel_id=reel.id,
                        plan_id=plan.id,
                        status="active",
                        starts_at=now - timedelta(hours=1),
                        active_until=now + timedelta(days=1),
                    )
                )
            elif index < 14:
                excluded_ids.append(reel.id)
            else:
                old_skip_id = reel.id
                organic_ids.append(reel.id)

        session.add_all(
            [
                Swipe(
                    user_id=user_id,
                    reel_id=excluded_ids[0],
                    action="like",
                    client_id=uuid4(),
                    position=0,
                ),
                Swipe(
                    user_id=user_id,
                    reel_id=excluded_ids[1],
                    action="skip",
                    client_id=uuid4(),
                    position=0,
                    created_at=now - timedelta(hours=23),
                ),
                Swipe(
                    user_id=user_id,
                    reel_id=old_skip_id,
                    action="skip",
                    client_id=uuid4(),
                    position=0,
                    created_at=now - timedelta(hours=25),
                ),
            ]
        )
        await session.commit()

    response = await client.get("/api/v1/feed?limit=20", headers=headers)

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 13
    assert [item["is_promoted"] for item in items] == (
        [False] * 4 + [True] + [False] * 2 + [True] * 6
    )
    item_ids = {item["reel_id"] for item in items}
    assert not item_ids.intersection(str(reel_id) for reel_id in excluded_ids)
    assert str(old_skip_id) in item_ids
    assert {str(reel_id) for reel_id in promoted_ids} == {
        item["reel_id"] for item in items if item["is_promoted"]
    }
    assert {str(reel_id) for reel_id in organic_ids} == {
        item["reel_id"] for item in items if not item["is_promoted"]
    }


@pytest.mark.asyncio
async def test_recommender_aggregates_category_signals_and_diversifies():
    now = datetime.now(timezone.utc)
    async with app.state.test_session_factory() as session:
        user = User(name="Покупатель", is_guest=True)
        seller = User(name="Продавец", is_guest=False)
        preferred = Category(slug="preferred", name="Выбранная категория")
        signaled = Category(slug="signaled", name="Категория сигналов")
        ignored = Category(slug="ignored", name="Категория отменённого сигнала")
        session.add_all([user, seller, preferred, signaled, ignored])
        await session.flush()
        session.add(UserInterest(user_id=user.id, category_id=preferred.id))
        await session.flush()

        async def add_reel(category, title, age_minutes):
            listing = Listing(
                seller_id=seller.id,
                category_id=category.id,
                title=title,
                description="Описание",
                price_amount=1000,
                status="active",
            )
            session.add(listing)
            await session.flush()
            reel = Reel(
                listing_id=listing.id,
                seller_id=seller.id,
                status="published",
                media_type="video",
                enabled=True,
                published_at=now - timedelta(minutes=age_minutes),
            )
            session.add(reel)
            await session.flush()
            return reel

        signaled_reels = [
            await add_reel(signaled, f"Сигнальный {index}", index)
            for index in range(5)
        ]
        preferred_reels = [
            await add_reel(preferred, f"Интерес {index}", index + 10)
            for index in range(2)
        ]
        ignored_reel = await add_reel(ignored, "Отменённый сигнал", 20)

        session.add_all(
            [
                Swipe(
                    user_id=user.id,
                    reel_id=signaled_reels[-1].id,
                    action="like",
                    dwell_ms=4000,
                    client_id=uuid4(),
                    position=0,
                ),
                Swipe(
                    user_id=user.id,
                    reel_id=signaled_reels[0].id,
                    action="dislike",
                    dwell_ms=100,
                    client_id=uuid4(),
                    position=0,
                ),
                Swipe(
                    user_id=user.id,
                    reel_id=ignored_reel.id,
                    action="like",
                    client_id=uuid4(),
                    position=0,
                    undone_at=now,
                ),
                Event(user_id=user.id, reel_id=signaled_reels[-1].id, type="open_listing"),
                Event(
                    user_id=user.id,
                    reel_id=signaled_reels[-1].id,
                    type="watch",
                    value_ms=4000,
                ),
                Event(user_id=user.id, reel_id=signaled_reels[-1].id, type="view"),
            ]
        )
        await session.commit()

        ranked_ids = await recommend(session, user.id, limit=20)

    assert ranked_ids[:4] == [reel.id for reel in signaled_reels[:4]]
    assert ranked_ids[4] == preferred_reels[0].id
    assert ranked_ids[-1] == ignored_reel.id
