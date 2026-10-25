import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import engine, async_session
from app.db.models import (
    Base, User, Category, UserOnboarding, UserInterest,
    Listing, ListingImage, Reel, ReelMedia, WishlistItem, WishlistShare,
    PromotionPlan, Promotion
)
from uuid import uuid4
from datetime import datetime, timedelta

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Пользователи
        buyer = User(id=uuid4(), name="Покупатель", is_guest=False, demo_role="buyer")
        friend = User(id=uuid4(), name="Друг", is_guest=False, demo_role="friend")
        seller = User(id=uuid4(), name="Продавец", is_guest=False, demo_role="seller")
        session.add_all([buyer, friend, seller])
        await session.flush()

        # Категории
        categories = []
        for i, (slug, name, color) in enumerate([
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
        ]):
            categories.append(Category(id=uuid4(), slug=slug, name=name, color=color, sort=i))
        session.add_all(categories)
        await session.flush()

        # Онбординг для покупателя
        onboarding = UserOnboarding(user_id=buyer.id, interests_done=True, hint_seen=True)
        session.add(onboarding)

        # Интересы покупателя
        session.add(UserInterest(user_id=buyer.id, category_id=categories[0].id))
        session.add(UserInterest(user_id=buyer.id, category_id=categories[1].id))
        session.add(UserInterest(user_id=buyer.id, category_id=categories[2].id))

        # Товары
        listings = []
        for i in range(30):
            cat = categories[i % len(categories)]
            listing = Listing(
                id=uuid4(),
                seller_id=seller.id,
                category_id=cat.id,
                title=f"Товар {i+1}",
                description=f"Описание товара {i+1}",
                price_amount=1000 + i * 500,
                currency="RUB",
                city="Москва",
                status="active",
                listing_url=f"https://avito.ru/item/{i+1}"
            )
            listings.append(listing)
        session.add_all(listings)
        await session.flush()

        # Рилсы
        reels = []
        for i, listing in enumerate(listings[:20]):
            reel = Reel(
                id=uuid4(),
                listing_id=listing.id,
                seller_id=seller.id,
                status="published",
                media_type="video" if i % 2 == 0 else "photo",
                show_price=True,
                description=f"Рилс для товара {i+1}",
                cover_url=f"https://cdn.example.com/reels/{i+1}/cover.jpg",
                enabled=True,
                published_at=datetime.utcnow() - timedelta(days=i % 5)
            )
            reels.append(reel)
        session.add_all(reels)
        await session.flush()

        # Медиа для рилсов
        media = []
        for i, reel in enumerate(reels):
            if reel.media_type == "video":
                media.append(ReelMedia(
                    id=uuid4(), reel_id=reel.id, kind="video",
                    url=f"https://cdn.example.com/reels/{i+1}/video.mp4",
                    poster_url=f"https://cdn.example.com/reels/{i+1}/poster.jpg",
                    duration_sec=24, width=1080, height=1920, position=0
                ))
            else:
                for j in range(3):
                    media.append(ReelMedia(
                        id=uuid4(), reel_id=reel.id, kind="photo",
                        url=f"https://cdn.example.com/reels/{i+1}/photo_{j}.jpg",
                        width=1080, height=1920, position=j
                    ))
        session.add_all(media)
        await session.flush()

        # Вишлист покупателя (8 товаров)
        wishlist_items = []
        for i in range(8):
            wishlist_items.append(WishlistItem(
                id=uuid4(),
                user_id=buyer.id,
                listing_id=listings[i].id,
                reel_id=reels[i].id,
                added_at=datetime.utcnow() - timedelta(days=7-i)
            ))
        session.add_all(wishlist_items)

        # Один товар продан
        listings[5].status = "sold"

        # Продвижение одного рилса
        plan = PromotionPlan(
            id=uuid4(), days=7, estimated_reach=5000,
            price_amount=500, is_best_value=True
        )
        session.add(plan)
        await session.flush()

        promotion = Promotion(
            id=uuid4(),
            reel_id=reels[0].id,
            plan_id=plan.id,
            status="active",
            starts_at=datetime.utcnow() - timedelta(days=1),
            active_until=datetime.utcnow() + timedelta(days=6)
        )
        session.add(promotion)

        # Доступ к вишлисту по ссылке
        share = WishlistShare(
            user_id=buyer.id,
            token="k7x2p9",
            enabled=True,
            rotated_at=datetime.utcnow()
        )
        session.add(share)

        await session.commit()
        print("Seed completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed())