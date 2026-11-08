from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, func, select, update
from app.db.session import get_db
from app.schemas.seller import (
    UploadStartIn, UploadStartOut, UploadFileOut, UploadStatusOut,
    CropIn, OrderIn, ReelCreateIn, ReelOut, ReelListResponse, ReelListOut, ListingOut,
    ReelPatchIn,
)
from app.db.models import Event, MediaUpload, MediaFile, Reel, ReelMedia, Listing, User, Promotion, Swipe, WishlistItem
from app.core.security import get_current_user
from app.services.s3_service import s3_service, get_s3_key
from app.core.config import settings
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List, Optional

router = APIRouter()

@router.post("/media/uploads", response_model=UploadStartOut)
async def start_upload(
    data: UploadStartIn,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    # Проверки лимитов
    if data.kind == "video":
        if len(data.files) != 1:
            raise HTTPException(status_code=422, detail={"error": {"code": "bad_format", "message": "Expected 1 video file"}})
        f = data.files[0]
        if f.size_bytes > 200 * 1024 * 1024:
            raise HTTPException(status_code=413, detail={"error": {"code": "too_large", "message": "Video exceeds 200MB"}})
        if f.content_type not in {"video/mp4", "video/quicktime", "video/webm"}:
            raise HTTPException(status_code=415, detail={"error": {"code": "bad_format", "message": "Not a video"}})
    elif data.kind == "photos":
        if len(data.files) > 10:
            raise HTTPException(status_code=422, detail={"error": {"code": "too_many_files", "message": "Max 10 photos"}})
        for f in data.files:
            if f.size_bytes > 10 * 1024 * 1024:
                raise HTTPException(status_code=413, detail={"error": {"code": "too_large", "message": "Photo exceeds 10MB"}})
            if f.content_type not in {"image/jpeg", "image/png", "image/webp"}:
                raise HTTPException(status_code=415, detail={"error": {"code": "bad_format", "message": "Not an image"}})
    else:
        raise HTTPException(status_code=422, detail="Invalid kind")

    upload_id = uuid4()
    upload = MediaUpload(
        id=upload_id,
        user_id=user.id,
        kind=data.kind,
        status="created"
    )
    session.add(upload)
    await session.flush()

    res_files = []
    for pos, f in enumerate(data.files):
        file_id = uuid4()
        storage_key = get_s3_key(str(upload_id), str(file_id), f.filename, data.kind)
        
        mf = MediaFile(
            id=file_id,
            upload_id=upload_id,
            filename=f.filename,
            content_type=f.content_type,
            size_bytes=f.size_bytes,
            storage_key=storage_key,
            status="pending",
            position=pos
        )
        session.add(mf)

        # Presigned URL
        put_url = await s3_service.generate_presigned_url(
            storage_key, f.content_type
        )
        res_files.append(UploadFileOut(
            file_id=str(file_id),
            put_url=put_url,
            headers={"Content-Type": f.content_type}
        ))

    await session.commit()
    return UploadStartOut(
        upload_id=str(upload_id),
        files=res_files,
        expires_in=3600
    )

@router.post("/media/uploads/{upload_id}/complete", status_code=202)
async def complete_upload(
    upload_id: UUID,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    upload = await session.get(MediaUpload, upload_id)
    if not upload or upload.user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Upload not found"})
    if upload.status not in {"created", "uploaded"}:
        raise HTTPException(status_code=409, detail={"code": "validation_error", "message": "Upload cannot be completed in its current state"})
    files_result = await session.scalars(
        select(MediaFile)
        .where(MediaFile.upload_id == upload.id)
        .order_by(MediaFile.position)
    )
    files = list(files_result.all())
    if not files:
        raise HTTPException(status_code=422, detail={"code": "validation_error", "message": "Upload has no files"})
    for media_file in files:
        metadata = await s3_service.head_object(media_file.storage_key)
        actual_size = metadata.get("ContentLength", 0)
        if actual_size != media_file.size_bytes:
            raise HTTPException(status_code=413, detail={"code": "too_large", "message": "Uploaded file exceeds declared size"})
        if metadata.get("ContentType") != media_file.content_type:
            raise HTTPException(status_code=415, detail={"code": "bad_format", "message": "Uploaded content type does not match declaration"})
        media_file.status = "uploaded"
    upload.status = "uploaded"
    await session.commit()

    queue = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    try:
        await queue.enqueue_job("process_media_upload", str(upload.id))
    finally:
        await queue.aclose()
    return {"status": "processing"}

@router.get("/media/uploads/{upload_id}", response_model=UploadStatusOut)
async def get_upload_status(
    upload_id: UUID,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    upload = await session.get(MediaUpload, upload_id)
    if not upload or upload.user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Upload not found"})

    files_res = await session.execute(
        select(MediaFile).where(MediaFile.upload_id == upload.id).order_by(MediaFile.position)
    )
    files = files_res.scalars().all()

    file_list = []
    for f in files:
        url = await s3_service.get_file_url(
            f.poster_storage_key or f.storage_key
        )
        file_list.append({
            "file_id": str(f.id),
            "preview_url": url,
            "filename": f.filename,
            "duration_sec": f.duration_sec,
            "status": f.status,
        })

    return UploadStatusOut(
        status=upload.status,
        error=upload.error,
        duration_sec=max((f.duration_sec or 0 for f in files), default=0) or None,
        files=file_list
    )

@router.post("/media/uploads/{upload_id}/crop")
async def crop_media(
    upload_id: UUID,
    data: CropIn,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.removeprefix("Bearer ").strip()
    user = await get_current_user(token, session)
    upload = await session.get(MediaUpload, upload_id)
    if upload is None or upload.user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Upload not found"})
    if upload.status not in {"created", "uploaded"}:
        raise HTTPException(status_code=409, detail={"code": "validation_error", "message": "Crop must be set before processing"})
    files = await session.scalars(
        select(MediaFile).where(MediaFile.upload_id == upload.id)
    )
    for media_file in files.all():
        media_file.crop_x = data.x
        media_file.crop_y = data.y
        media_file.crop_width = data.width
        media_file.crop_height = data.height
    await session.commit()
    return {"status": "ok"}


@router.put("/media/uploads/{upload_id}/order", status_code=204)
async def order_upload_files(
    upload_id: UUID,
    data: OrderIn,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> Response:
    user = await get_current_user(token, session)
    upload = await session.get(MediaUpload, upload_id)
    if upload is None or upload.user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Upload not found"})
    files_result = await session.scalars(
        select(MediaFile).where(MediaFile.upload_id == upload.id)
    )
    files = list(files_result.all())
    if len(set(data.file_ids)) != len(data.file_ids) or set(data.file_ids) != {item.id for item in files}:
        raise HTTPException(status_code=422, detail={"code": "validation_error", "message": "file_ids must contain every upload file exactly once"})
    by_id = {item.id: item for item in files}
    for position, file_id in enumerate(data.file_ids):
        by_id[file_id].position = position
    await session.commit()
    return Response(status_code=204)


@router.delete("/media/uploads/{upload_id}/files/{file_id}", status_code=204)
async def delete_upload_file(
    upload_id: UUID,
    file_id: UUID,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> Response:
    user = await get_current_user(token, session)
    upload = await session.get(MediaUpload, upload_id)
    media_file = await session.get(MediaFile, file_id)
    if upload is None or upload.user_id != user.id or media_file is None or media_file.upload_id != upload.id:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Upload file not found"})
    await s3_service.delete_file(media_file.storage_key)
    if media_file.poster_storage_key:
        await s3_service.delete_file(media_file.poster_storage_key)
    await session.delete(media_file)
    await session.commit()
    return Response(status_code=204)

@router.get("/me/listings", response_model=List[ListingOut])
async def get_my_listings(
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    listings_res = await session.execute(
        select(Listing).where(Listing.seller_id == user.id, Listing.status == "active")
    )
    listings = listings_res.scalars().all()

    res = []
    for l in listings:
        reel_id = await session.scalar(
            select(Reel.id).where(Reel.listing_id == l.id).limit(1)
        )
        res.append(ListingOut(
            id=str(l.id),
            title=l.title,
            price=l.price_amount,
            has_reel=reel_id is not None
        ))
    return res

@router.post("/reels", response_model=ReelOut, status_code=201)
async def create_reel(
    data: ReelCreateIn,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    listing = await session.get(Listing, data.listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Listing not found"})
    if listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "Not your listing"})
    if listing.status != "active":
        raise HTTPException(status_code=409, detail={"code": "listing_unavailable", "message": "Listing is no longer available"})

    upload = await session.get(MediaUpload, data.upload_id)
    if not upload or upload.user_id != user.id:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Upload not found"})
    if upload.status != "ready":
        raise HTTPException(status_code=409, detail={"code": "validation_error", "message": "Media upload is not ready"})

    # Получаем файлы загрузки
    files_res = await session.execute(
        select(MediaFile).where(MediaFile.upload_id == upload.id).order_by(MediaFile.position)
    )
    files = files_res.scalars().all()
    if not files:
        raise HTTPException(status_code=422, detail={"code": "validation_error", "message": "Upload has no files"})

    # Авто-публикация для демо
    status_str = "published" if settings.AUTO_PUBLISH else "moderation"
    media_type = "video" if upload.kind == "video" else ("album" if len(files) > 1 else "photo")

    reel = Reel(
        id=uuid4(),
        listing_id=listing.id,
        seller_id=user.id,
        status=status_str,
        media_type=media_type,
        show_price=data.show_price,
        description=data.description,
        cover_url=files[0].poster_storage_key or files[0].storage_key,
        enabled=True,
        published_at=datetime.now(timezone.utc) if status_str == "published" else None
    )
    session.add(reel)

    # Добавляем элементы медиа
    for pos, f in enumerate(files):
        url = f.storage_key
        rm = ReelMedia(
            id=uuid4(),
            reel_id=reel.id,
            kind="video" if upload.kind == "video" else "photo",
            url=url,
            poster_url=f.poster_storage_key,
            duration_sec=f.duration_sec,
            width=1080,
            height=1920,
            position=pos
        )
        session.add(rm)

    await session.commit()

    return ReelOut(
        reel_id=str(reel.id),
        listing_id=str(reel.listing_id),
        status=reel.status,
        media_type=reel.media_type,
        show_price=reel.show_price,
        description=reel.description,
        cover_url=await s3_service.get_file_url(reel.cover_url) if reel.cover_url else None,
        enabled=reel.enabled,
        published_at=reel.published_at
    )

@router.get("/me/reels", response_model=ReelListResponse)
async def get_my_reels(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=50),
    cursor: UUID | None = None,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    query = (
        select(Reel, Listing)
        .join(Listing, Reel.listing_id == Listing.id)
        .where(Reel.seller_id == user.id)
        .order_by(Reel.created_at.desc())
    )
    if status_filter:
        query = query.where(Reel.status == status_filter)
    if cursor:
        cursor_reel = await session.scalar(
            select(Reel).where(Reel.id == cursor, Reel.seller_id == user.id)
        )
        if cursor_reel is None:
            raise HTTPException(status_code=400, detail={"code": "validation_error", "message": "Invalid reel cursor"})
        query = query.where(
            (Reel.created_at < cursor_reel.created_at)
            | ((Reel.created_at == cursor_reel.created_at) & (Reel.id < cursor_reel.id))
        )

    res = await session.execute(query.limit(limit + 1))
    rows = res.all()

    items = []
    now = datetime.now(timezone.utc)
    for reel, listing in rows[:limit]:
        views = await session.scalar(
            select(func.count(Event.id)).where(
                Event.reel_id == reel.id,
                Event.type.in_(("view", "watch")),
            )
        )
        likes = await session.scalar(
            select(func.count(Swipe.id)).where(
                Swipe.reel_id == reel.id,
                Swipe.action == "like",
                Swipe.undone_at.is_(None),
            )
        )
        stats = {"views": views or 0, "likes": likes or 0}

        # Продвижение
        prom_res = await session.execute(
            select(Promotion).where(
                Promotion.reel_id == reel.id,
                Promotion.status == "active",
                Promotion.active_until > now
            )
        )
        prom = prom_res.scalar_one_or_none()
        promotion_info = {
            "active_until": prom.active_until if prom else None
        }

        items.append(ReelListOut(
            reel_id=str(reel.id),
            listing_id=str(listing.id),
            title=listing.title,
            price=listing.price_amount,
            cover_url=await s3_service.get_file_url(reel.cover_url) if reel.cover_url else None,
            status=reel.status,
            reject_reason=reel.reject_reason,
            stats=stats,
            promotion=promotion_info
        ))

    next_cursor = items[-1].reel_id if len(rows) > limit and items else None

    return ReelListResponse(
        items=items,
        next_cursor=next_cursor
    )

@router.get("/reels/{reel_id}/preview")
async def preview_reel(
    reel_id: UUID,
    show_price: bool | None = None,
    description: str | None = Query(default=None, max_length=300),
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db),
):
    user = await get_current_user(token, session)
    reel = await session.get(Reel, reel_id)
    if reel is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Reel not found"})
    if reel.seller_id != user.id:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "Not your reel"})
    from app.api.v1.feed import build_feed_item

    listing = await session.get(Listing, reel.listing_id)
    seller = await session.get(User, reel.seller_id)
    card = await build_feed_item(session, reel, listing, seller, user.id, set())
    if show_price is not None:
        card.price = (
            {"amount": listing.price_amount, "currency": listing.currency}
            if show_price
            else None
        )
    if description is not None:
        card.description = description
    return card


@router.patch("/reels/{reel_id}", response_model=ReelOut)
async def update_reel(
    reel_id: UUID,
    data: ReelPatchIn,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> ReelOut:
    user = await get_current_user(token, session)
    reel = await session.get(Reel, reel_id)
    if reel is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Reel not found"})
    if reel.seller_id != user.id:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "Not your reel"})
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(reel, field, value)
    await session.commit()
    return ReelOut(
        reel_id=reel.id,
        listing_id=reel.listing_id,
        status=reel.status,
        media_type=reel.media_type,
        show_price=reel.show_price,
        description=reel.description,
        cover_url=await s3_service.get_file_url(reel.cover_url) if reel.cover_url else None,
        enabled=reel.enabled,
        published_at=reel.published_at,
    )


@router.delete("/reels/{reel_id}", status_code=204)
async def delete_reel(
    reel_id: UUID,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db),
) -> Response:
    user = await get_current_user(token, session)
    reel = await session.get(Reel, reel_id)
    if reel is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Reel not found"})
    if reel.seller_id != user.id:
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "Not your reel"})
    await session.execute(
        update(WishlistItem)
        .where(WishlistItem.reel_id == reel.id)
        .values(reel_id=None)
    )
    await session.execute(delete(Promotion).where(Promotion.reel_id == reel.id))
    await session.execute(delete(ReelMedia).where(ReelMedia.reel_id == reel.id))
    await session.delete(reel)
    await session.commit()
    return Response(status_code=204)
