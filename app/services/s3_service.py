from pathlib import PurePath
from urllib.parse import unquote, urlsplit

import aioboto3

from app.core.config import settings


class S3Service:
    def __init__(self) -> None:
        self.endpoint = settings.S3_ENDPOINT
        self.public_endpoint = settings.S3_PUBLIC_ENDPOINT
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.bucket = settings.S3_BUCKET
        self.session = aioboto3.Session()

    def _client(self, endpoint: str):
        return self.session.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="us-east-1",
        )

    async def generate_presigned_url(
        self, key: str, content_type: str, expires_in: int = 3600
    ) -> str:
        async with self._client(self.public_endpoint) as client:
            return await client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )

    async def head_object(self, key: str) -> dict:
        async with self._client(self.endpoint) as client:
            return await client.head_object(Bucket=self.bucket, Key=key)

    async def check_bucket(self) -> None:
        async with self._client(self.endpoint) as client:
            await client.head_bucket(Bucket=self.bucket)

    async def download_file(self, key: str, destination: str) -> None:
        async with self._client(self.endpoint) as client:
            response = await client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"]
            with open(destination, "wb") as file:
                while chunk := await body.read(1024 * 1024):
                    file.write(chunk)

    async def upload_file(self, key: str, source: str, content_type: str) -> None:
        async with self._client(self.endpoint) as client:
            await client.upload_file(
                source,
                self.bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )

    async def delete_file(self, key: str) -> None:
        async with self._client(self.endpoint) as client:
            await client.delete_object(Bucket=self.bucket, Key=key)

    async def get_file_url(self, key: str, expires_in: int = 3600) -> str:
        parsed = urlsplit(key)
        if parsed.scheme and parsed.netloc:
            public_endpoint = urlsplit(self.public_endpoint)
            if (
                parsed.scheme != public_endpoint.scheme
                or parsed.netloc != public_endpoint.netloc
            ):
                return key
            path = unquote(parsed.path).lstrip("/")
            bucket_prefix = f"{self.bucket}/"
            if not path.startswith(bucket_prefix):
                return key
            key = path[len(bucket_prefix):]

        async with self._client(self.public_endpoint) as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )


def get_s3_key(upload_id: str, file_id: str, filename: str, kind: str) -> str:
    folder = "videos" if kind == "video" else "photos"
    suffix = PurePath(filename).suffix.lower()
    if len(suffix) > 12 or not suffix[1:].isalnum():
        suffix = ""
    return f"{folder}/{upload_id}/{file_id}{suffix}"


s3_service = S3Service()
