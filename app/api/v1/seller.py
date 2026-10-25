from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, update
from app.db.session import get_db
from app.schemas.seller import (
    UploadStartIn, UploadStartOut, UploadFileOut, UploadStatusOut,
    CropIn, OrderIn, ReelCreateIn, ReelOut, ReelListResponse, ReelListOut, ListingOut
)
from app.db.models import MediaUpload, MediaFile, Reel, ReelMedia, Listing, User, Promotion
from app.core.security import get_current_user
from app.services.s3_service import s3_service, get_s3_key
from app.core.config import settings
from uuid import UUID, uuid4
from datetime import datetime

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
        if f.size_bytes > 200 * 1024 * 1024:  # 200MB
            raise HTTPException(status_code=413, detail={"error": {"code": "too_large", "message": "Video exceeds 200MB"}})
        if not f.content_type.startswith("video/"):
            raise HTTPException(status_code=415, detail={"error": {"code": "bad_format", "message": "Not a video"}})
    elif data.kind == "photos":
        if len(data.files) > 10:
            raise HTTPException(status_code=422, detail={"error": {"code": "too_many_files", "message": "Max 10 photos"}})
        for f in data.files:
            if f.size_bytes > 10 * 1024 * 1024:  # 10MB
                raise HTTPException(status_code=413, detail={"error": {"code": "too_large", "message": "Photo exceeds 10MB"}})
            if not f.content_type.startswith("image/"):
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
        put_url = await s3_service.generate_presigned_url(storage_key)
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
    upload_id: str,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    upload = await session.get(MediaUpload, UUID(upload_id))
    if not upload or upload.user_id != user.id:
        raise HTTPException(status_code=404, detail="Upload not found")

    upload.status = "uploaded"
    # Имитируем быстрый старт обработки
    upload.status = "ready"
    await session.commit()
    return {"status": "processing"}

@router.get("/media/uploads/{upload_id}", response_model=UploadStatusOut)
async def get_upload_status(
    upload_id: str,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    upload = await session.get(MediaUpload, UUID(upload_id))
    if not upload or upload.user_id != user.id:
        raise HTTPException(status_code=404, detail="Upload not found")

    files_res = await session.execute(
        select(MediaFile).where(MediaFile.upload_id == upload.id).order_by(MediaFile.position)
    )
    files = files_res.scalars().all()

    file_list = []
    for f in files:
        url = await s3_service.get_file_url(f.storage_key)
        file_list.append({
            "file_id": str(f.id),
            "preview_url": url,
            "filename": f.filename
        })

    return UploadStatusOut(
        status=upload.status,
        error=upload.error,
        duration_sec=15 if upload.kind == "video" else None,
        files=file_list
    )

@router.post("/media/uploads/{upload_id}/crop")
async def crop_media(
    upload_id: str,
    data: CropIn,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    # Для демо возвращаем статус успеха
    return {"status": "ok", "message": "Crop applied"}

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
        reel_res = await session.execute(select(Reel).where(Reel.listing_id == l.id))
        has_reel = reel_res.scalar_one_or_none() is not None
        res.append(ListingOut(
            id=str(l.id),
            title=l.title,
            price=l.price_amount,
            has_reel=has_reel
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

    listing = await session.get(Listing, UUID(data.listing_id))
    if not listing or listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Проверка: один рилс на объявление
    existing = await session.execute(
        select(Reel).where(Reel.listing_id == listing.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Reel already exists for this listing")

    upload = await session.get(MediaUpload, UUID(data.upload_id))
    if not upload or upload.user_id != user.id:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Получаем файлы загрузки
    files_res = await session.execute(
        select(MediaFile).where(MediaFile.upload_id == upload.id).order_by(MediaFile.position)
    )
    files = files_res.scalars().all()
    if not files:
        raise HTTPException(status_code=400, detail="Upload has no files")

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
        description=data.description[:300] if data.description else None,
        cover_url=await s3_service.get_file_url(files[0].storage_key),
        enabled=True,
        published_at=datetime.utcnow() if status_str == "published" else None
    )
    session.add(reel)

    # Добавляем элементы медиа
    for pos, f in enumerate(files):
        url = await s3_service.get_file_url(f.storage_key)
        rm = ReelMedia(
            id=uuid4(),
            reel_id=reel.id,
            kind="video" if upload.kind == "video" else "photo",
            url=url,
            poster_url=url if upload.kind == "video" else None,
            duration_sec=15 if upload.kind == "video" else None,
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
        cover_url=reel.cover_url,
        enabled=reel.enabled,
        published_at=reel.published_at
    )

@router.get("/me/reels", response_model=ReelListResponse)
async def get_my_reels(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = None,
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

    res = await session.execute(query)
    rows = res.all()

    items = []
    now = datetime.utcnow()
    for reel, listing in rows[:limit]:
        # Статистика
        stats = {"views": 120, "likes": 15}

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
            "active_until": prom.active_until.isoformat() if prom else None
        }

        items.append(ReelListOut(
            reel_id=str(reel.id),
            listing_id=str(listing.id),
            title=listing.title,
            price=listing.price_amount,
            cover_url=reel.cover_url,
            status=reel.status,
            reject_reason=reel.reject_reason,
            stats=stats,
            promotion=promotion_info
        ))

    next_cursor = str(items[-1].reel_id) if len(items) == limit else None

    return ReelListResponse(
        items=items,
        next_cursor=next_cursor
    )

@router.patch("/reels/{reel_id}", response_model=ReelOut)
async def update_reel(
    reel_id: str,
    show_price: Optional[bool] = None,
    description: Optional[str] = None,
    enabled: Optional[bool] = None,
    token: str = Header(..., alias="Authorization"),
    session: AsyncSession = Depends(get_db)
):
    token = token.replace("Bearer ", "")
    user = await get_current_user(token, session)

    reel = await session.get(Reel, UUID(reel_id))
    if not reel:
        raise HTTPException(status_code=404, detail="Reel not found")

    if reel.seller_id != user.id:
        raise HTTPException(status_code=403, detail={"error": {"code": "forbidden", "message": "Not your reel"}})

    if show_price is not None:
        reel.show_price = show_price
    if description is not None:
        reel.description = description[:300]
    if enabled is not None:
        reel.enabled = enabled

    await session.commit()

    return ReelOut(
        reel_id=str(reel.id),
        listing_id=str(reel.listing_id),
        status=reel.status,
        media_type=reel.media_type,
        show_price=reel.show_price,
        description=reel.description,
        cover_url=reel.cover_url,
        enabled=reel.enabled,
        published_at=reel.published_at
    )
