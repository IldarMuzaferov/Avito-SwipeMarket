import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.db.models import (
    Category,
    Listing,
    ListingImage,
    Promotion,
    PromotionPlan,
    Reel,
    ReelMedia,
    Swipe,
    User,
    UserInterest,
    UserOnboarding,
    WishlistItem,
    WishlistShare,
)
from app.db.session import async_session

CATEGORY_DATA = [
    ("electronics", "Электроника", "#FF6B00"),
    ("fashion", "Одежда", "#0099FF"),
    ("home", "Дом и квартира", "#00CC66"),
    ("sports", "Спорт", "#FF3366"),
    ("books", "Книги", "#9933FF"),
    ("toys", "Игрушки", "#FF9900"),
    ("auto", "Авто", "#666666"),
    ("pets", "Животные", "#FF66CC"),
    ("beauty", "Красота", "#FF0066"),
    ("tools", "Инструменты", "#009999"),
]


async def seed() -> None:
    async with async_session() as session:
        existing = await session.scalar(
            select(User.id).where(User.demo_role == "buyer").limit(1)
        )
        if existing:
            print("Seed data already exists; no changes made.")
            return

        now = datetime.now(timezone.utc)
        buyer = User(name="Покупатель", city="Москва", is_guest=False, demo_role="buyer")
        friend = User(name="Друг", city="Москва", is_guest=False, demo_role="friend")
        seller = User(name="Продавец", city="Москва", is_guest=False, demo_role="seller")
        session.add_all([buyer, friend, seller])
        await session.flush()

        categories = [
            Category(
                slug=slug,
                name=name,
                color=color,
                image_url=f"https://cdn.example.com/categories/{slug}.jpg",
                sort=sort,
            )
            for sort, (slug, name, color) in enumerate(CATEGORY_DATA)
        ]
        session.add_all(categories)
        await session.flush()

        session.add(
            UserOnboarding(
                user_id=buyer.id,
                interests_done=True,
                interests_skipped=False,
                hint_seen=True,
            )
        )
        session.add_all(
            UserInterest(user_id=buyer.id, category_id=category.id)
            for category in categories[:3]
        )

        listings = [
            Listing(
                seller_id=seller.id,
                category_id=categories[index % len(categories)].id,
                title=f"Товар {index + 1}",
                description=f"Описание товара {index + 1}",
                price_amount=1000 + index * 500,
                currency="RUB",
                city="Москва",
                status="sold" if index == 5 else "active",
                listing_url=f"https://avito.ru/item/{index + 1}",
            )
            for index in range(30)
        ]
        session.add_all(listings)
        await session.flush()
        session.add_all(
            ListingImage(
                listing_id=listing.id,
                url=f"https://cdn.example.com/listings/{index + 1}/1.jpg",
                position=0,
            )
            for index, listing in enumerate(listings)
        )

        reels: list[Reel] = []
        reel_media: list[ReelMedia] = []
        for index, listing in enumerate(listings):
            is_video = index % 2 == 0
            reel = Reel(
                listing_id=listing.id,
                seller_id=seller.id,
                status="published",
                media_type="video" if is_video else ("album" if index % 3 == 1 else "photo"),
                show_price=index % 7 != 0,
                description=f"Рилс для товара {index + 1}",
                cover_url=f"https://cdn.example.com/reels/{index + 1}/cover.jpg",
                enabled=True,
                published_at=now - timedelta(days=index % 5),
            )
            reels.append(reel)
        session.add_all(reels)
        await session.flush()

        for index, reel in enumerate(reels):
            if reel.media_type == "video":
                reel_media.append(
                    ReelMedia(
                        reel_id=reel.id,
                        kind="video",
                        url=f"https://cdn.example.com/videos/{index + 1}/video.mp4",
                        poster_url=f"https://cdn.example.com/videos/{index + 1}/poster.jpg",
                        duration_sec=24,
                        width=1080,
                        height=1920,
                        position=0,
                    )
                )
            else:
                photo_count = 3 if reel.media_type == "album" else 1
                reel_media.extend(
                    ReelMedia(
                        reel_id=reel.id,
                        kind="photo",
                        url=f"https://cdn.example.com/photos/{index + 1}/{photo + 1}.jpg",
                        width=1080,
                        height=1920,
                        position=photo,
                    )
                    for photo in range(photo_count)
                )
        session.add_all(reel_media)
        session.add_all(
            WishlistItem(
                user_id=buyer.id,
                listing_id=listings[index].id,
                reel_id=reels[index].id,
                added_at=now - timedelta(days=7 - index),
            )
            for index in range(8)
        )
        session.add_all(
            Swipe(
                user_id=buyer.id,
                reel_id=reels[index].id,
                action="skip" if index % 2 else "dislike",
                client_id=uuid4(),
                session_id="seed-session",
                dwell_ms=1200,
                position=index,
            )
            for index in range(8, 12)
        )

        plans = [
            PromotionPlan(
                days=days,
                estimated_reach=reach,
                price_amount=price,
                is_best_value=best,
            )
            for days, reach, price, best in (
                (3, 1800, 199, False),
                (7, 5000, 399, True),
                (14, 9500, 699, False),
            )
        ]
        session.add_all(plans)
        await session.flush()
        session.add(
            Promotion(
                reel_id=reels[0].id,
                plan_id=plans[1].id,
                status="active",
                starts_at=now - timedelta(days=1),
                active_until=now + timedelta(days=6),
            )
        )
        session.add(
            WishlistShare(
                user_id=buyer.id,
                token="k7x2p9",
                enabled=True,
                rotated_at=now,
            )
        )
        await session.commit()
    print("Seed data created.")


if __name__ == "__main__":
    asyncio.run(seed())
