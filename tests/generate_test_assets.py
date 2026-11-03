"""Generate test images for portrait, landscape, square, hi-res, low-res, transparent, and multi-format testing."""

import io
from pathlib import Path
from PIL import Image, ImageDraw


def create_portrait_image(width: int = 1200, height: int = 2400) -> bytes:
    """Generate a high-resolution portrait image (2:1 aspect ratio)."""
    img = Image.new("RGB", (width, height), color=(50, 120, 200))
    draw = ImageDraw.Draw(img)
    # Draw geometric patterns to give compressibility & texture
    for i in range(0, height, 40):
        draw.line([(0, i), (width, i)], fill=(200, 220, 240), width=3)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def create_landscape_image(width: int = 2400, height: int = 1200) -> bytes:
    """Generate a high-resolution landscape image (2:1 aspect ratio)."""
    img = Image.new("RGB", (width, height), color=(40, 180, 120))
    draw = ImageDraw.Draw(img)
    for i in range(0, width, 40):
        draw.line([(i, 0), (i, height)], fill=(180, 240, 210), width=3)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def create_square_image(size: int = 1500) -> bytes:
    """Generate a square image (1:1 aspect ratio)."""
    img = Image.new("RGB", (size, size), color=(220, 80, 60))
    draw = ImageDraw.Draw(img)
    draw.ellipse([size // 4, size // 4, size * 3 // 4, size * 3 // 4], fill=(255, 200, 150))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def create_high_res_image(width: int = 3840, height: int = 2160) -> bytes:
    """Generate a 4K UHD high-resolution image."""
    img = Image.new("RGB", (width, height), color=(30, 30, 45))
    draw = ImageDraw.Draw(img)
    draw.rectangle([200, 200, width - 200, height - 200], outline=(255, 215, 0), width=10)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def create_low_res_image(width: int = 150, height: int = 100) -> bytes:
    """Generate a low-resolution image smaller than any config category."""
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, width - 10, height - 10], fill=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_transparent_png(width: int = 600, height: int = 300) -> bytes:
    """Generate a transparent PNG logo with true alpha channel transparency."""
    img = Image.new("RGBA", (width, height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw centered badge with semi-transparent elements
    draw.ellipse([50, 20, width - 50, height - 20], fill=(70, 130, 180, 230))
    draw.rectangle([100, 80, width - 100, height - 80], fill=(255, 255, 255, 180))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_format_samples() -> dict[str, bytes]:
    """Generate sample images in various formats: JPEG, PNG, WEBP, BMP, GIF."""
    samples = {}
    base_img = Image.new("RGB", (400, 300), color=(128, 64, 192))

    for fmt in ["JPEG", "PNG", "WEBP", "BMP", "GIF"]:
        buf = io.BytesIO()
        base_img.save(buf, format=fmt)
        samples[fmt] = buf.getvalue()

    return samples
