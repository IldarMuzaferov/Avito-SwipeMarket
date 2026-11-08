from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.db.models import Category, Listing, MediaFile, MediaUpload, Reel, User
from app.main import app


@pytest.mark.asyncio
async def test_upload_and_create_reel(client, monkeypatch):
    seller = User(name="Продавец", is_guest=False, demo_role="seller")
    async with app.state.test_session_factory() as session:
        category = Category(slug="camera", name="Фото")
        session.add_all([seller, category])
        await session.flush()
        listing = Listing(
            seller_id=seller.id,
            category_id=category.id,
            title="Камера",
            price_amount=30000,
            status="active",
        )
        session.add(listing)
        await session.commit()
        seller_id, listing_id = seller.id, listing.id

    from app.api.v1 import seller as seller_api
    from app.core.security import create_access_token

    seen_keys = []

    async def presigned(key, content_type, expires_in=3600):
        seen_keys.append(key)
        return "https://minio.test/presigned"

    async def head(key):
        return {"ContentLength": 123, "ContentType": "video/mp4"}

    async def file_url(key):
        return f"https://cdn.test/{key}"

    monkeypatch.setattr(seller_api.s3_service, "generate_presigned_url", presigned)
    monkeypatch.setattr(seller_api.s3_service, "head_object", head)
    monkeypatch.setattr(seller_api.s3_service, "get_file_url", file_url)

    class Queue:
        async def enqueue_job(self, name, upload_id):
            assert name == "process_media_upload"
            assert UUID(upload_id)

        async def aclose(self):
            return None

    async def create_queue(*args, **kwargs):
        return Queue()

    monkeypatch.setattr(seller_api, "create_pool", create_queue)

    headers = {"Authorization": f"Bearer {create_access_token({'sub': str(seller_id)})}"}
    started = await client.post(
        "/api/v1/media/uploads",
        headers=headers,
        json={
            "kind": "video",
            "files": [
                {"filename": "../../unsafe.mp4", "content_type": "video/mp4", "size_bytes": 123}
            ],
        },
    )
    assert started.status_code == 200
    upload_id = started.json()["upload_id"]
    assert seen_keys[0].startswith("videos/")
    assert ".." not in seen_keys[0]

    completed = await client.post(
        f"/api/v1/media/uploads/{upload_id}/complete",
        headers=headers,
    )
    assert completed.status_code == 202
    assert completed.json()["status"] == "processing"

    async with app.state.test_session_factory() as session:
        upload = await session.get(MediaUpload, UUID(upload_id))
        media = await session.scalar(select(MediaFile).where(MediaFile.upload_id == upload.id))
        upload.status = "ready"
        media.status = "ready"
        media.duration_sec = 25
        media.poster_storage_key = f"videos/{upload_id}/{media.id}/poster.jpg"
        await session.commit()

    created = await client.post(
        "/api/v1/reels",
        headers=headers,
        json={
            "listing_id": str(listing_id),
            "upload_id": upload_id,
            "show_price": False,
            "description": "Коротко о товаре",
        },
    )
    assert created.status_code == 201
    assert created.json()["description"] == "Коротко о товаре"
    assert created.json()["status"] in {"moderation", "published"}

    my_reels = await client.get("/api/v1/me/reels", headers=headers)
    assert my_reels.status_code == 200
    assert my_reels.json()["items"][0]["title"] == "Камера"

    patch = await client.patch(
        f"/api/v1/reels/{created.json()['reel_id']}",
        headers=headers,
        json={"description": "Обновлено", "show_price": True},
    )
    assert patch.status_code == 200
    assert patch.json()["description"] == "Обновлено"

    async with app.state.test_session_factory() as session:
        second_upload = MediaUpload(
            id=UUID("d0000000-0000-4000-8000-000000000001"),
            user_id=seller_id,
            kind="video",
            status="ready",
        )
        session.add(second_upload)
        await session.flush()
        session.add(
            MediaFile(
                id=UUID("d0000000-0000-4000-8000-000000000002"),
                upload_id=second_upload.id,
                filename="second.mp4",
                content_type="video/mp4",
                size_bytes=123,
                storage_key="videos/second.mp4",
                status="ready",
                duration_sec=20,
                position=0,
            )
        )
        await session.commit()

    listings = await client.get("/api/v1/me/listings", headers=headers)
    assert listings.status_code == 200
    assert listings.json()[0]["has_reel"] is True

    second_reel = await client.post(
        "/api/v1/reels",
        headers=headers,
        json={
            "listing_id": str(listing_id),
            "upload_id": "d0000000-0000-4000-8000-000000000001",
            "show_price": True,
            "description": "Второй рилс",
        },
    )
    assert second_reel.status_code == 201
    async with app.state.test_session_factory() as session:
        reel_count = await session.scalar(
            select(func.count(Reel.id)).where(Reel.listing_id == listing_id)
        )
        assert reel_count == 2


@pytest.mark.asyncio
async def test_upload_validation(client):
    auth = await client.post("/api/v1/auth/guest", json={})
    headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}
    response = await client.post(
        "/api/v1/media/uploads",
        headers=headers,
        json={
            "kind": "video",
            "files": [
                {"filename": "large.mp4", "content_type": "video/mp4", "size_bytes": 300 * 1024 * 1024}
            ],
        },
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "too_large"


@pytest.mark.asyncio
async def test_photo_upload_persists_upload_before_files(client, monkeypatch):
    auth = await client.post("/api/v1/auth/guest", json={})
    headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}

    from app.api.v1 import seller as seller_api

    async def presigned(key, content_type, expires_in=3600):
        return "https://storage.test/presigned"

    monkeypatch.setattr(seller_api.s3_service, "generate_presigned_url", presigned)
    response = await client.post(
        "/api/v1/media/uploads",
        headers=headers,
        json={
            "kind": "photos",
            "files": [
                {"filename": "photo.png", "content_type": "image/png", "size_bytes": 100}
            ],
        },
    )

    assert response.status_code == 200
    upload_id = UUID(response.json()["upload_id"])
    async with app.state.test_session_factory() as session:
        upload = await session.get(MediaUpload, upload_id)
        media = await session.scalar(select(MediaFile).where(MediaFile.upload_id == upload_id))
        assert upload is not None
        assert media is not None
