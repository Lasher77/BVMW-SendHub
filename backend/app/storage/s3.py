import io
from typing import BinaryIO
import boto3
from app.storage.base import StorageBackend


class S3Storage(StorageBackend):
    def __init__(self, bucket: str, region: str, access_key: str, secret_key: str):
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
        )

    def save(self, path: str, data: BinaryIO) -> str:
        self.client.upload_fileobj(data, self.bucket, path)
        return path

    def read(self, path: str) -> bytes:
        buf = io.BytesIO()
        self.client.download_fileobj(self.bucket, path, buf)
        return buf.getvalue()

    def delete(self, path: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=path)

    def exists(self, path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=path)
            return True
        except self.client.exceptions.ClientError:
            return False
