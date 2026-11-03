"""
Image Optimizer Package
Category-Wise Image Optimization and Resizing System Using Python Pillow.
"""

from .config import (
    IMAGE_CONFIG,
    get_category_config,
    register_category_config,
    SUPPORTED_FORMATS,
    DEFAULT_MAX_FILE_SIZE_BYTES,
)
from .exceptions import (
    ImageOptimizerError,
    InvalidImageError,
    CorruptedImageError,
    UnsupportedFormatError,
    FileSizeExceededError,
    CategoryNotFoundError,
)
from .optimizer import ImageOptimizer, OptimizationResult
from .storage import (
    BaseStorage,
    LocalStorage,
    MemoryStorage,
    S3StorageAdapter,
    CloudinaryStorageAdapter,
)
from .pipeline import ImageUploadPipeline, UploadResult
from .validator import validate_image_bytes, read_and_validate_input

__all__ = [
    "IMAGE_CONFIG",
    "get_category_config",
    "register_category_config",
    "SUPPORTED_FORMATS",
    "DEFAULT_MAX_FILE_SIZE_BYTES",
    "ImageOptimizerError",
    "InvalidImageError",
    "CorruptedImageError",
    "UnsupportedFormatError",
    "FileSizeExceededError",
    "CategoryNotFoundError",
    "ImageOptimizer",
    "OptimizationResult",
    "BaseStorage",
    "LocalStorage",
    "MemoryStorage",
    "S3StorageAdapter",
    "CloudinaryStorageAdapter",
    "ImageUploadPipeline",
    "UploadResult",
    "validate_image_bytes",
    "read_and_validate_input",
]
