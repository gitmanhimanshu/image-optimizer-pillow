"""Validation module for uploaded image files."""

import io
from typing import Union, BinaryIO
from pathlib import Path
from PIL import Image

from .config import DEFAULT_MAX_FILE_SIZE_BYTES, SUPPORTED_FORMATS
from .exceptions import (
    FileSizeExceededError,
    InvalidImageError,
    CorruptedImageError,
    UnsupportedFormatError,
)

# Known image magic headers
MAGIC_NUMBERS = {
    b"\xFF\xD8\xFF": "JPEG",
    b"\x89PNG\r\n\x1a\n": "PNG",
    b"GIF87a": "GIF",
    b"GIF89a": "GIF",
    b"BM": "BMP",
    b"II*\x00": "TIFF",
    b"MM\x00*": "TIFF",
}


def _check_magic_bytes(header: bytes) -> str | None:
    """Identify image format by magic signature."""
    # Special check for WebP (RIFF....WEBP)
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "WEBP"

    for magic, fmt in MAGIC_NUMBERS.items():
        if header.startswith(magic):
            return fmt
    return None


def validate_image_bytes(
    data: bytes,
    max_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
) -> str:
    """
    Validate raw image bytes for size, magic bytes signature, and data integrity.

    Args:
        data: Raw image bytes.
        max_size_bytes: Maximum allowed size in bytes.

    Returns:
        Detected image format string (e.g. 'JPEG', 'PNG', 'WEBP').

    Raises:
        FileSizeExceededError: If byte length exceeds max_size_bytes.
        InvalidImageError: If data is empty or does not have image magic header.
        UnsupportedFormatError: If the detected format is not in SUPPORTED_FORMATS.
        CorruptedImageError: If PIL verification fails.
    """
    if not data or len(data) == 0:
        raise InvalidImageError("Uploaded file is empty (0 bytes).")

    if len(data) > max_size_bytes:
        raise FileSizeExceededError(
            f"File size {len(data)} bytes exceeds maximum allowed limit of {max_size_bytes} bytes."
        )

    # Magic byte check
    detected_format = _check_magic_bytes(data[:16])
    if not detected_format:
        # Fallback to PIL format check before rejecting
        try:
            with Image.open(io.BytesIO(data)) as test_img:
                detected_format = test_img.format
        except Exception as e:
            raise InvalidImageError(f"File is not a valid image format: {e}") from e

    if not detected_format or detected_format.upper() not in SUPPORTED_FORMATS:
        raise UnsupportedFormatError(
            f"Unsupported image format '{detected_format}'. Supported formats: {sorted(SUPPORTED_FORMATS)}"
        )

    # Verify structural integrity with PIL
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except Exception as e:
        raise CorruptedImageError(f"Corrupted or truncated image data: {e}") from e

    return detected_format.upper()


def read_and_validate_input(
    image_input: Union[bytes, io.BytesIO, BinaryIO, str, Path],
    max_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
) -> tuple[bytes, str]:
    """
    Accepts bytes, a file-like stream, or a filesystem path, reads it safely, and validates.

    Returns:
        tuple[bytes, str]: (raw_image_bytes, detected_format)
    """
    if isinstance(image_input, (str, Path)):
        path = Path(image_input)
        if not path.is_file():
            raise InvalidImageError(f"File not found: {path}")
        with open(path, "rb") as f:
            raw_bytes = f.read()
    elif isinstance(image_input, bytes):
        raw_bytes = image_input
    elif hasattr(image_input, "read"):
        current_pos = image_input.tell() if hasattr(image_input, "tell") else None
        raw_bytes = image_input.read()
        if current_pos is not None and hasattr(image_input, "seek"):
            image_input.seek(current_pos)
    else:
        raise InvalidImageError(f"Unsupported input type: {type(image_input)}")

    detected_format = validate_image_bytes(raw_bytes, max_size_bytes=max_size_bytes)
    return raw_bytes, detected_format
