from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from botocore.exceptions import BotoCoreError, ClientError

from app.api import api_router
from app.core.config import settings
from app.db.session import engine
from app.services.s3_service import s3_service

app = FastAPI(title="Avito Svayp API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Internal-Key",
        "X-Admin-Key",
        "X-Payment-Signature",
    ],
)
app.include_router(api_router)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and isinstance(detail.get("error"), dict):
        error = detail["error"]
    elif isinstance(detail, dict) and "code" in detail:
        error = detail
    else:
        code = {
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            409: "validation_error",
            410: "wishlist_disabled",
            413: "too_large",
            415: "bad_format",
            422: "validation_error",
            429: "rate_limited",
        }.get(exc.status_code, "http_error")
        error = {"code": code, "message": str(detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    missing_auth = any(
        error.get("loc", ())[:2] == ("header", "Authorization")
        and error.get("type") == "missing"
        for error in exc.errors()
    )
    return JSONResponse(
        status_code=401 if missing_auth else 422,
        content={
            "error": {
                "code": "unauthorized" if missing_auth else "validation_error",
                "message": "Bearer token required" if missing_auth else "Request validation failed",
                "details": jsonable_encoder(exc.errors()),
            }
        },
    )


@app.get("/ready", include_in_schema=False)
@app.get("/api/v1/ready", include_in_schema=False)
async def readiness() -> JSONResponse:
    checks = {"database": False, "redis": False, "storage": False}
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        checks["database"] = True
    except SQLAlchemyError:
        pass

    redis = Redis.from_url(settings.REDIS_URL)
    try:
        await redis.ping()
        checks["redis"] = True
    except RedisError:
        pass
    finally:
        await redis.aclose()

    try:
        await s3_service.check_bucket()
        checks["storage"] = True
    except (BotoCoreError, ClientError, OSError):
        pass
    status_code = 200 if all(checks.values()) else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if status_code == 200 else "not_ready", "checks": checks},
    )