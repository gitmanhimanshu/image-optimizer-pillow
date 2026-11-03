"""Storage abstraction and adapters for local, S3/R2, and Cloudinary backends."""

import os
from abc import ABC, abstractmethod
from typing import Optional, Dict
from pathlib import Path


class BaseStorage(ABC):
    """Abstract interface for image storage backends."""

    @abstractmethod
    def save(self, key: str, data: bytes, content_type: str = "image/webp") -> str:
        """
        Store raw bytes under the specified key/path.

        Returns:
            The public or accessible URL / path of the saved file.
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if an image key exists."""
        pass

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Retrieve stored bytes for a given key."""
        pass


class LocalStorage(BaseStorage):
    """Local filesystem storage implementation."""

    def __init__(self, base_dir: str | Path = "uploads", base_url: str = "/media"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip("/")

    def save(self, key: str, data: bytes, content_type: str = "image/webp") -> str:
        file_path = self.base_dir / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(data)
        # Return URL-like path or relative path
        return f"{self.base_url}/{key}".replace("\\", "/")

    def exists(self, key: str) -> bool:
        return (self.base_dir / key).is_file()

    def get(self, key: str) -> bytes:
        file_path = self.base_dir / key
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(file_path, "rb") as f:
            return f.read()


class MemoryStorage(BaseStorage):
    """In-memory storage for unit testing and ephemeral uploads."""

    def __init__(self):
        self._store: Dict[str, bytes] = {}
        self._content_types: Dict[str, str] = {}

    def save(self, key: str, data: bytes, content_type: str = "image/webp") -> str:
        self._store[key] = data
        self._content_types[key] = content_type
        return f"memory://{key}"

    def exists(self, key: str) -> bool:
        return key in self._store

    def get(self, key: str) -> bytes:
        if key not in self._store:
            raise FileNotFoundError(f"Key not found in memory: {key}")
        return self._store[key]


class S3StorageAdapter(BaseStorage):
    """
    Adapter for AWS S3 and Cloudflare R2 storage.
    Delegates to boto3 s3 client if boto3 is installed.
    """

    def __init__(
        self,
        bucket_name: str,
        s3_client=None,
        public_url_base: Optional[str] = None,
    ):
        self.bucket_name = bucket_name
        self.public_url_base = public_url_base
        if s3_client is None:
            try:
                import boto3
                self.s3_client = boto3.client("s3")
            except ImportError:
                self.s3_client = None
        else:
            self.s3_client = s3_client

    def save(self, key: str, data: bytes, content_type: str = "image/webp") -> str:
        if self.s3_client is None:
            raise RuntimeError(
                "boto3 is not installed or configured. Install boto3 to use S3StorageAdapter."
            )
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        if self.public_url_base:
            return f"{self.public_url_base.rstrip('/')}/{key}"
        return f"s3://{self.bucket_name}/{key}"

    def exists(self, key: str) -> bool:
        if self.s3_client is None:
            return False
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def get(self, key: str) -> bytes:
        if self.s3_client is None:
            raise RuntimeError("boto3 is not installed.")
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        return response["Body"].read()


class CloudinaryStorageAdapter(BaseStorage):
    """
    Adapter for Cloudinary image hosting.
    Delegates to cloudinary SDK if installed.
    """

    def __init__(self, cloudinary_uploader=None):
        if cloudinary_uploader is None:
            try:
                import cloudinary.uploader
                self.uploader = cloudinary.uploader
            except ImportError:
                self.uploader = None
        else:
            self.uploader = cloudinary_uploader

    def save(self, key: str, data: bytes, content_type: str = "image/webp") -> str:
        if self.uploader is None:
            raise RuntimeError(
                "cloudinary is not installed. Install cloudinary to use CloudinaryStorageAdapter."
            )
        import io
        public_id = Path(key).stem
        res = self.uploader.upload(
            io.BytesIO(data),
            public_id=public_id,
            resource_type="image",
            format="webp",
        )
        return res.get("secure_url", res.get("url", ""))

    def exists(self, key: str) -> bool:
        return False

    def get(self, key: str) -> bytes:
        raise NotImplementedError("Direct byte retrieval via Cloudinary API should use public URL.")
