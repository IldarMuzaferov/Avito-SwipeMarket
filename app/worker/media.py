import asyncio
import json
import tempfile
from pathlib import Path
from uuid import UUID

from arq.connections import RedisSettings
from sqlalchemy import select

from app.core.config import settings
from app.db.models import MediaFile, MediaUpload
from app.db.session import async_session
from app.services.s3_service import s3_service


async def run_process(*args: str) -> tuple[int, bytes, bytes]:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return process.returncode, stdout, stderr


def video_filter(media_file: MediaFile) -> str:
    if all(
        value is not None
        for value in (
            media_file.crop_x,
            media_file.crop_y,
            media_file.crop_width,
            media_file.crop_height,
        )
    ):
        return (
            f"crop=iw*{media_file.crop_width}:ih*{media_file.crop_height}:"
            f"iw*{media_file.crop_x}:ih*{media_file.crop_y},"
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1"
        )
    return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"


async def process_media_upload(ctx: dict, upload_id: str) -> None:
    upload_uuid = UUID(upload_id)
    async with async_session() as db:
        upload = await db.get(MediaUpload, upload_uuid)
        if upload is None:
            return
        files_result = await db.scalars(
            select(MediaFile)
            .where(MediaFile.upload_id == upload_uuid)
            .order_by(MediaFile.position)
        )
        files = list(files_result.all())
        upload.status = "processing"
        for media_file in files:
            media_file.status = "processing"
        await db.commit()

        with tempfile.TemporaryDirectory(prefix="svayp-media-") as temp_dir:
            workdir = Path(temp_dir)
            for media_file in files:
                source = workdir / f"{media_file.id}.source"
                await s3_service.download_file(media_file.storage_key, str(source))
                if upload.kind == "video":
                    code, stdout, _ = await run_process(
                        "ffprobe",
                        "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "json",
                        str(source),
                    )
                    if code != 0:
                        upload.status = "failed"
                        upload.error = "bad_format"
                        media_file.status = "failed"
                        await db.commit()
                        return
                    try:
                        duration = float(json.loads(stdout)["format"]["duration"])
                    except (ValueError, KeyError, TypeError):
                        upload.status = "failed"
                        upload.error = "bad_format"
                        media_file.status = "failed"
                        await db.commit()
                        return
                    if duration > 60:
                        upload.status = "failed"
                        upload.error = "video_too_long"
                        media_file.status = "failed"
                        media_file.duration_sec = round(duration)
                        await db.commit()
                        return

                    output = workdir / f"{media_file.id}.mp4"
                    poster = workdir / f"{media_file.id}.jpg"
                    code, _, _ = await run_process(
                        "ffmpeg", "-y", "-i", str(source),
                        "-vf", video_filter(media_file),
                        "-c:v", "libx264", "-preset", "veryfast",
                        "-c:a", "aac", "-movflags", "+faststart",
                        str(output),
                    )
                    if code != 0:
                        upload.status = "failed"
                        upload.error = "processing_failed"
                        media_file.status = "failed"
                        await db.commit()
                        return
                    code, _, _ = await run_process(
                        "ffmpeg", "-y", "-ss", "00:00:00", "-i", str(output),
                        "-frames:v", "1", str(poster),
                    )
                    if code != 0:
                        upload.status = "failed"
                        upload.error = "poster_generation_failed"
                        media_file.status = "failed"
                        await db.commit()
                        return

                    processed_key = f"videos/{upload_uuid}/{media_file.id}/processed.mp4"
                    poster_key = f"videos/{upload_uuid}/{media_file.id}/poster.jpg"
                    await s3_service.upload_file(processed_key, str(output), "video/mp4")
                    await s3_service.upload_file(poster_key, str(poster), "image/jpeg")
                    media_file.storage_key = processed_key
                    media_file.poster_storage_key = poster_key
                    media_file.duration_sec = round(duration)
                    media_file.content_type = "video/mp4"
                    media_file.size_bytes = output.stat().st_size
                else:
                    output = workdir / f"{media_file.id}.jpg"
                    crop_filter = (
                        f"crop=iw*{media_file.crop_width}:ih*{media_file.crop_height}:"
                        f"iw*{media_file.crop_x}:ih*{media_file.crop_y},"
                        "scale=1080:1920:force_original_aspect_ratio=decrease,"
                        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
                        if all(
                            value is not None
                            for value in (
                                media_file.crop_x,
                                media_file.crop_y,
                                media_file.crop_width,
                                media_file.crop_height,
                            )
                        )
                        else "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
                    )
                    code, _, _ = await run_process(
                        "ffmpeg", "-y", "-i", str(source),
                        "-vf", crop_filter, "-frames:v", "1", str(output),
                    )
                    if code != 0:
                        upload.status = "failed"
                        upload.error = "processing_failed"
                        media_file.status = "failed"
                        await db.commit()
                        return
                    processed_key = f"photos/{upload_uuid}/{media_file.id}/processed.jpg"
                    await s3_service.upload_file(processed_key, str(output), "image/jpeg")
                    media_file.storage_key = processed_key
                    media_file.content_type = "image/jpeg"
                    media_file.size_bytes = output.stat().st_size
                media_file.status = "ready"
            upload.status = "ready"
            upload.error = None
            await db.commit()


class WorkerSettings:
    functions = [process_media_upload]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 4
    job_timeout = 15 * 60
