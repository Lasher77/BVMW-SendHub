import os
from typing import BinaryIO
from app.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    def __init__(self, base_path: str):
        self.base_path = os.path.abspath(base_path)

    def _full_path(self, path: str) -> str:
        full = os.path.normpath(os.path.join(self.base_path, path))
        # Guard against path traversal
        if not full.startswith(self.base_path):
            raise ValueError(f"Invalid storage path: {path}")
        return full

    def save(self, path: str, data: BinaryIO) -> str:
        full = self._full_path(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            while chunk := data.read(1024 * 64):
                f.write(chunk)
        return path

    def read(self, path: str) -> bytes:
        full = self._full_path(path)
        with open(full, "rb") as f:
            return f.read()

    def delete(self, path: str) -> None:
        full = self._full_path(path)
        if os.path.exists(full):
            os.remove(full)

    def exists(self, path: str) -> bool:
        return os.path.exists(self._full_path(path))
