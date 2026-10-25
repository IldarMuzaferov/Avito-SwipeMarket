import aioboto3
from app.core.config import settings
from uuid import uuid4
from datetime import datetime, timedelta

class S3Service:
    def __init__(self):
        self.endpoint = settings.S3_ENDPOINT
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.bucket = settings.S3_BUCKET

    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        session = aioboto3.Session()
        async with session.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        ) as s3:
            url = await s3.generate_presigned_url(
                "put_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in
            )
        return url

    async def get_file_url(self, key: str) -> str:
        return f"{self.endpoint}/{self.bucket}/{key}"

def get_s3_key(upload_id: str, file_id: str, filename: str, kind: str) -> str:
    # Разделяем фото и видео в разные папки
    folder = "videos" if kind == "video" else "photos"
    return f"{folder}/{upload_id}/{file_id}/{filename}"

s3_service = S3Service()