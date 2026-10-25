from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 день для демонстрации

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    to_encode["type"] = "access"
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode.update({
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str, session: AsyncSession) -> User:
    token = token.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id or payload.get("type") != "access":
            raise ValueError("Invalid access token")
        user_uuid = UUID(user_id)
        result = await session.execute(select(User).where(User.id == user_uuid))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        return user
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Invalid or expired access token"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

async def create_guest_user(session: AsyncSession, name: str | None = None) -> User:
    user = User(
        id=uuid4(),
        name=name or "Гость",
        is_guest=True,
        demo_role=None
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

async def get_demo_user(session: AsyncSession, role: str) -> User:
    result = await session.execute(
        select(User).where(User.is_guest.is_(False), User.demo_role == role)
    )
    user = result.scalar_one_or_none()
    if not user:
        # fallback: создадим при первом запуске
        user = User(id=uuid4(), name=role.capitalize(), is_guest=False, demo_role=role)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user