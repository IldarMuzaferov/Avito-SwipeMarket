"""Рекомендательный сервис (заглушка).

Интерфейс: recommend(user_id, limit, exclude_ids) -> list[reel_id]
В будущем заменится на отдельный ML-сервис.
"""

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Reel, Swipe, UserInterest
from datetime import datetime, timedelta


async def recommend(
    session: AsyncSession,
    user_id: str,
    limit: int = 20,
    exclude_ids: list = None,
) -> list:
    """Возвращает список reel_id для показа."""
    if exclude_ids is None:
        exclude_ids = []

    # Получаем интересы пользователя
    result = await session.execute(
        select(UserInterest.category_id).where(UserInterest.user_id == user_id)
    )
    user_category_ids = [r[0] for r in result.fetchall()]

    # Базовый запрос: опубликованные рилсы с активными товарами
    query = (
        select(Reel)
        .where(
            Reel.status == "published",
            Reel.enabled == True,
            Reel.seller_id != user_id,
        )
        .order_by(Reel.published_at.desc())
        .limit(limit * 3)  # Берём с запасом на фильтры
    )

    if user_category_ids:
        # Сначала рилсы из интересующих категорий
        query = query.where(Reel.listing_id.in_(
            select(Reel.listing_id).where(
                Reel.listing_id.in_(
                    select(Reel.listing_id).join(
                        UserInterest,
                        UserInterest.category_id == Reel.listing_id,
                    )
                )
            )
        ))

    result = await session.execute(query)
    reels = result.scalars().all()

    # Фильтруем уже показанные
    filtered = [r for r in reels if r.id not in exclude_ids]

    return [r.id for r in filtered[:limit]]


def score_swipe(action: str, dwell_ms: int | None = None) -> float:
    """Возвращает вес действия для рекомендаций."""
    scores = {
        "like": 1.0,
        "dislike": -1.0,
        "skip": -0.05,
    }
    base = scores.get(action, 0.0)

    # Долгий просмотр = положительный сигнал
    if dwell_ms and dwell_ms > 3000:
        base += 0.5
    # Быстрый свайп = отрицательный сигнал
    if dwell_ms and dwell_ms < 300:
        base -= 0.3

    return base