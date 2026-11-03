"""Unified upload pipeline for e-commerce endpoints."""

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Union, BinaryIO, Optional, Dict, Any
import io

from .optimizer import ImageOptimizer, OptimizationResult
from .storage import BaseStorage, LocalStorage
from .exceptions import ImageOptimizerError


@dataclass(frozen=True)
class UploadResult:
    """Standardized response returned by upload pipeline."""
    url: str
    original_url: Optional[str]
    category: str
    format: str
    width: int
    height: int
    original_width: int
    original_height: int
    size_bytes: int
    saved_bytes: int
    savings_percent: float
    is_cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching standard API response contracts."""
        return {
            "url": self.url,
            "original_url": self.original_url,
            "category": self.category,
            "format": self.format,
            "width": self.width,
            "height": self.height,
            "original_width": self.original_width,
            "original_height": self.original_height,
            "size_bytes": self.size_bytes,
            "saved_bytes": self.saved_bytes,
            "savings_percent": self.savings_percent,
            "is_cached": self.is_cached,
        }


class ImageUploadPipeline:
    """
    End-to-end image processing and storage pipeline for upload endpoints.
    
    Seamlessly integrates into:
    - FastAPI: UploadFile
    - Flask: request.files['image']
    - Django: request.FILES['image']
    - Background workers (Celery, RQ, threading)
    """

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        optimizer: Optional[ImageOptimizer] = None,
        preserve_original: bool = True,
        enable_deduplication: bool = True,
    ):
        self.storage = storage if storage is not None else LocalStorage()
        self.optimizer = optimizer if optimizer is not None else ImageOptimizer()
        self.preserve_original = preserve_original
        self.enable_deduplication = enable_deduplication
        # Cache mapping sha256 -> UploadResult
        self._hash_cache: Dict[str, UploadResult] = {}

    def process_and_store(
        self,
        file_input: Union[bytes, io.BytesIO, BinaryIO, str, Path],
        filename: str,
        category: str,
        pad_to_canvas: Optional[bool] = None,
        allow_upscale: bool = False,
    ) -> UploadResult:
        """
        Process the uploaded image according to its category and store it.

        Args:
            file_input: Uploaded file contents or file-like object.
            filename: Original filename (used for naming convention).
            category: E-commerce category ('product', 'category', 'banner', 'template', 'logo').
            pad_to_canvas: Optional canvas padding override.
            allow_upscale: Whether to upscale if image is smaller than target.

        Returns:
            UploadResult with public URLs and image metadata.
        """
        # Ensure we have raw bytes for hashing and processing
        if isinstance(file_input, (str, Path)):
            with open(file_input, "rb") as f:
                raw_bytes = f.read()
        elif isinstance(file_input, bytes):
            raw_bytes = file_input
        elif hasattr(file_input, "read"):
            pos = file_input.tell() if hasattr(file_input, "tell") else None
            raw_bytes = file_input.read()
            if pos is not None and hasattr(file_input, "seek"):
                file_input.seek(pos)
        else:
            raise ImageOptimizerError(f"Unsupported file_input type: {type(file_input)}")

        # Deduplication check
        file_hash = ""
        if self.enable_deduplication:
            file_hash = hashlib.sha256(raw_bytes).hexdigest()
            cache_key = f"{category}_{file_hash}_{pad_to_canvas}"
            if cache_key in self._hash_cache:
                cached_res = self._hash_cache[cache_key]
                # Return cached result with is_cached=True
                return UploadResult(
                    url=cached_res.url,
                    original_url=cached_res.original_url,
                    category=cached_res.category,
                    format=cached_res.format,
                    width=cached_res.width,
                    height=cached_res.height,
                    original_width=cached_res.original_width,
                    original_height=cached_res.original_height,
                    size_bytes=cached_res.size_bytes,
                    saved_bytes=cached_res.saved_bytes,
                    savings_percent=cached_res.savings_percent,
                    is_cached=True,
                )

        # 1. Run optimization engine
        opt_res: OptimizationResult = self.optimizer.optimize(
            image_input=raw_bytes,
            category=category,
            pad_to_canvas=pad_to_canvas,
            allow_upscale=allow_upscale,
        )

        # 2. Generate clean storage keys
        base_name = Path(filename).stem or "image"
        # Sanitize base_name
        clean_base_name = "".join(c for c in base_name if c.isalnum() or c in ("-", "_"))[:40]
        unique_token = uuid.uuid4().hex[:10]
        normalized_cat = category.strip().lower()

        # Output key: e.g. "product/shoes_a1b2c3d4.webp"
        optimized_key = f"{normalized_cat}/{clean_base_name}_{unique_token}.{opt_res.format.lower()}"
        optimized_url = self.storage.save(
            key=optimized_key,
            data=opt_res.data,
            content_type=f"image/{opt_res.format.lower()}",
        )

        # 3. Optionally preserve original image separately
        original_url = None
        if self.preserve_original:
            orig_suffix = Path(filename).suffix.lstrip(".") or "orig"
            original_key = f"originals/{normalized_cat}/{clean_base_name}_{unique_token}.{orig_suffix}"
            original_url = self.storage.save(
                key=original_key,
                data=raw_bytes,
                content_type=f"image/{orig_suffix.lower()}",
            )

        result = UploadResult(
            url=optimized_url,
            original_url=original_url,
            category=normalized_cat,
            format=opt_res.format,
            width=opt_res.width,
            height=opt_res.height,
            original_width=opt_res.original_width,
            original_height=opt_res.original_height,
            size_bytes=opt_res.optimized_size_bytes,
            saved_bytes=opt_res.saved_bytes,
            savings_percent=opt_res.savings_percent,
            is_cached=False,
        )

        if self.enable_deduplication and file_hash:
            cache_key = f"{category}_{file_hash}_{pad_to_canvas}"
            self._hash_cache[cache_key] = result

        return result
