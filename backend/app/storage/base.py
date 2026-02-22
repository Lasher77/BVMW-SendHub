from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageBackend(ABC):
    @abstractmethod
    def save(self, path: str, data: BinaryIO) -> str:
        """Save file data to the given relative path. Returns the stored path."""

    @abstractmethod
    def read(self, path: str) -> bytes:
        """Read and return file bytes from the given path."""

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete the file at the given path."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check whether the file exists."""
