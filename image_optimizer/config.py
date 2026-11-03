"""Image optimization configuration module."""

from typing import Dict, Any

IMAGE_CONFIG: Dict[str, Dict[str, Any]] = {
    "product": {
        "width": 800,
        "height": 800,
        "quality": 88,
        "pad_to_canvas": False,
    },
    "category": {
        "width": 600,
        "height": 400,
        "quality": 88,
        "pad_to_canvas": False,
    },
    "banner": {
        "width": 1600,
        "height": 500,
        "quality": 90,
        "pad_to_canvas": False,
    },
    "template": {
        "width": 1200,
        "height": 800,
        "quality": 90,
        "pad_to_canvas": False,
    },
    "logo": {
        "width": 400,
        "height": 200,
        "quality": 90,
        "pad_to_canvas": False,
    },
}

# Maximum allowed upload file size: 25 MB
DEFAULT_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

# Supported input image formats
SUPPORTED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP", "BMP", "TIFF", "GIF"}

# Default output format
DEFAULT_OUTPUT_FORMAT = "WEBP"

# Default background colors for canvas padding
DEFAULT_PADDING_COLOR_RGB = (255, 255, 255)
DEFAULT_PADDING_COLOR_RGBA = (0, 0, 0, 0)


def get_category_config(category: str) -> Dict[str, Any]:
    """
    Retrieve dimensions and quality configuration for a given category.

    Args:
        category: The image category name (e.g. 'product', 'category', 'banner', 'template', 'logo').

    Returns:
        Dict containing 'width', 'height', 'quality', and optional 'pad_to_canvas'.

    Raises:
        KeyError: If category is not found in IMAGE_CONFIG.
    """
    normalized_category = category.strip().lower()
    if normalized_category not in IMAGE_CONFIG:
        valid_keys = ", ".join(IMAGE_CONFIG.keys())
        raise KeyError(
            f"Unknown image category '{category}'. Available categories: {valid_keys}"
        )
    return IMAGE_CONFIG[normalized_category].copy()


def register_category_config(
    category: str,
    width: int,
    height: int,
    quality: int = 88,
    pad_to_canvas: bool = False,
) -> None:
    """
    Dynamically register or update a category configuration.
    """
    normalized_category = category.strip().lower()
    IMAGE_CONFIG[normalized_category] = {
        "width": width,
        "height": height,
        "quality": quality,
        "pad_to_canvas": pad_to_canvas,
    }
