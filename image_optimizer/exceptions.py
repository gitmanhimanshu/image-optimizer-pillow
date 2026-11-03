"""Custom exceptions for the image optimization module."""


class ImageOptimizerError(Exception):
    """Base exception for all image optimization errors."""
    pass


class InvalidImageError(ImageOptimizerError):
    """Raised when the uploaded file is not a valid or recognizable image."""
    pass


class CorruptedImageError(InvalidImageError):
    """Raised when the image file is corrupted or truncated."""
    pass


class UnsupportedFormatError(ImageOptimizerError):
    """Raised when the image format is not supported for processing."""
    pass


class FileSizeExceededError(ImageOptimizerError):
    """Raised when the input file size exceeds the allowed threshold."""
    pass


class CategoryNotFoundError(ImageOptimizerError):
    """Raised when the requested image category is not registered in the configuration."""
    pass
