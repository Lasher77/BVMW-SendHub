from app.storage.base import StorageBackend
from app.storage.local import LocalStorage
from app.config import settings


def get_storage() -> StorageBackend:
    if settings.STORAGE_BACKEND == "s3":
        from app.storage.s3 import S3Storage
        return S3Storage(
            bucket=settings.S3_BUCKET,
            region=settings.AWS_REGION,
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    return LocalStorage(base_path=settings.STORAGE_LOCAL_BASE)


storage = get_storage()
