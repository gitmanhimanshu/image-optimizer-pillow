"""Core image optimization engine using Python Pillow."""

import io
from dataclasses import dataclass
from typing import Union, BinaryIO, Optional, Tuple
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter

from .config import (
    IMAGE_CONFIG,
    get_category_config,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_PADDING_COLOR_RGB,
    DEFAULT_PADDING_COLOR_RGBA,
)
from .exceptions import CategoryNotFoundError, InvalidImageError
from .validator import read_and_validate_input


@dataclass(frozen=True)
class OptimizationResult:
    """Detailed result of an image optimization operation."""
    data: bytes
    format: str
    category: str
    original_width: int
    original_height: int
    width: int
    height: int
    original_size_bytes: int
    optimized_size_bytes: int
    saved_bytes: int
    compression_ratio: float
    has_transparency: bool
    is_padded: bool

    @property
    def aspect_ratio(self) -> float:
        """Returns the width / height aspect ratio of the optimized image content."""
        return round(self.width / self.height, 4) if self.height > 0 else 0.0

    @property
    def savings_percent(self) -> float:
        """Percentage of file size reduced."""
        if self.original_size_bytes <= 0:
            return 0.0
        return round((self.saved_bytes / self.original_size_bytes) * 100, 2)


class ImageOptimizer:
    """
    Production-ready, category-wise image optimizer using Python Pillow.

    Enforces:
    - Aspect-ratio preserving resizing with LANCZOS.
    - Zero cropping and zero stretching/distortion.
    - EXIF orientation auto-correction.
    - WebP conversion with alpha-channel transparency preservation.
    - No unnecessary upscaling of low-resolution images.
    - Optional exact canvas containment with suitable padding.
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config if config is not None else IMAGE_CONFIG

    def optimize(
        self,
        image_input: Union[bytes, io.BytesIO, BinaryIO, str, Path],
        category: str,
        pad_to_canvas: Optional[bool] = None,
        allow_upscale: bool = False,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
        custom_quality: Optional[int] = None,
        padding_color: Optional[Tuple[int, ...]] = None,
        custom_dimensions: Optional[Tuple[int, int]] = None,
        mode: str = "fit",
    ) -> OptimizationResult:
        """
        Optimize and resize an image according to its category specification or custom dimensions.

        Args:
            image_input: Path, bytes, or file-like object containing the raw image.
            category: Target category (e.g., 'product', 'category', 'banner', 'template', 'logo', 'custom').
            pad_to_canvas: If True, pads the image to exact target canvas dimensions while
                           preserving aspect ratio. If None, inherits from category config.
            allow_upscale: If False, images smaller than target dimensions are not scaled up.
            output_format: Target format (default: 'WEBP').
            custom_quality: Optional quality override (1-100).
            padding_color: Optional RGBA or RGB tuple for canvas padding background.
            custom_dimensions: Optional (width, height) tuple overriding or defining dimensions.

        Returns:
            OptimizationResult containing optimized bytes and metadata.
        """
        # 1. Fetch category configuration or use custom dimensions
        normalized_cat = category.strip().lower() if category else "custom"
        if normalized_cat == "custom" or custom_dimensions is not None:
            if custom_dimensions is None:
                raise ValueError("custom_dimensions (width, height) must be provided when category is 'custom'.")
            target_w, target_h = custom_dimensions
            quality = custom_quality if custom_quality is not None else 88
            should_pad = pad_to_canvas if pad_to_canvas is not None else False
        else:
            try:
                cat_cfg = get_category_config(normalized_cat)
            except KeyError as err:
                raise CategoryNotFoundError(str(err)) from err

            target_w = cat_cfg["width"]
            target_h = cat_cfg["height"]
            quality = custom_quality if custom_quality is not None else cat_cfg["quality"]
            should_pad = pad_to_canvas if pad_to_canvas is not None else cat_cfg.get("pad_to_canvas", False)

        if custom_dimensions is not None:
            target_w, target_h = custom_dimensions

        # 2. Read and validate input
        raw_bytes, detected_format = read_and_validate_input(image_input)
        original_size_bytes = len(raw_bytes)

        # 3. Open image with Pillow
        try:
            img = Image.open(io.BytesIO(raw_bytes))
            # Load pixel data into memory so the stream can be closed safely
            img.load()
        except Exception as e:
            raise InvalidImageError(f"Failed to open image for processing: {e}") from e

        # 4. Correct image orientation using EXIF metadata
        try:
            transposed = ImageOps.exif_transpose(img)
            if transposed is not None:
                img = transposed
        except Exception:
            # If EXIF is corrupt or missing orientation, retain current image
            pass

        orig_w, orig_h = img.size

        # 5. Detect and preserve transparency / normalize color mode
        has_transparency = self._has_transparency(img)
        img = self._normalize_color_mode(img, has_transparency)

        # 6. Resize according to requested mode ('fit', 'stretch', 'cover', 'pad')
        normalized_mode = mode.lower() if mode else ("pad" if should_pad else "fit")
        is_padded = False

        if normalized_mode == "amazon":
            # Amazon & Flipkart Standard: 85% product fill, centered on seamless canvas
            inner_w = int(target_w * 0.85)
            inner_h = int(target_h * 0.85)
            img = ImageOps.contain(img, (inner_w, inner_h), method=Image.Resampling.LANCZOS)
            auto_bg = ImageOptimizer.detect_edge_background_color(img)
            img = self._pad_to_canvas(
                img,
                canvas_size=(target_w, target_h),
                has_transparency=has_transparency,
                padding_color=padding_color if padding_color is not None else auto_bg,
            )
            is_padded = True
        elif normalized_mode == "blur_fill":
            # Ambient Blur Fill: Photo softly blurred in background, sharp photo centered on top
            # 100% color and mood match, zero white space, zero distortion!
            bg = img.resize((target_w, target_h), resample=Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(30))
            contained = ImageOps.contain(img, (target_w, target_h), method=Image.Resampling.LANCZOS)
            cw, ch = contained.size
            offset_x = (target_w - cw) // 2
            offset_y = (target_h - ch) // 2
            bg.paste(contained, (offset_x, offset_y))
            img = bg
            is_padded = True
        elif normalized_mode == "stretch":
            # Stretch to exact dimensions: Zero white space, fills 100% of target
            img = img.resize((target_w, target_h), resample=Image.Resampling.LANCZOS)
        elif normalized_mode == "cover":
            # Fill exact dimensions without stretching: Zero white space, center cropped
            img = ImageOps.fit(img, (target_w, target_h), method=Image.Resampling.LANCZOS)
        elif normalized_mode == "pad" or should_pad:
            # Contain preserving aspect ratio, then pad remaining space
            needs_downscale = (orig_w > target_w) or (orig_h > target_h)
            if needs_downscale or allow_upscale:
                img = ImageOps.contain(img, (target_w, target_h), method=Image.Resampling.LANCZOS)
            content_w, content_h = img.size
            if content_w != target_w or content_h != target_h:
                img = self._pad_to_canvas(
                    img,
                    canvas_size=(target_w, target_h),
                    has_transparency=has_transparency,
                    padding_color=padding_color,
                )
                is_padded = True
        else:  # 'fit' (default)
            # Scale down to fit within target dimensions preserving aspect ratio: ZERO white space
            needs_downscale = (orig_w > target_w) or (orig_h > target_h)
            if needs_downscale:
                img = ImageOps.contain(img, (target_w, target_h), method=Image.Resampling.LANCZOS)
            elif allow_upscale:
                img = ImageOps.contain(img, (target_w, target_h), method=Image.Resampling.LANCZOS)
            # No padding added! Dimensions remain exactly the image content

        final_w, final_h = img.size

        # 8. Encode optimized output (WebP by default)
        output_format_normalized = output_format.upper()
        output_io = io.BytesIO()

        save_kwargs = {
            "format": output_format_normalized,
            "optimize": True,
        }

        if output_format_normalized == "WEBP":
            save_kwargs["quality"] = quality
            save_kwargs["method"] = 6  # highest compression effort
            # For RGBA images with transparency, Pillow preserves the alpha channel in WebP
        elif output_format_normalized in ("JPEG", "JPG"):
            # JPEG does not support alpha channel
            if img.mode in ("RGBA", "LA"):
                img = self._flatten_alpha(img)
            save_kwargs["quality"] = quality
            save_kwargs["progressive"] = True
        elif output_format_normalized == "PNG":
            save_kwargs["compress_level"] = 9

        img.save(output_io, **save_kwargs)
        optimized_bytes = output_io.getvalue()
        optimized_size_bytes = len(optimized_bytes)
        saved_bytes = original_size_bytes - optimized_size_bytes
        compression_ratio = round(
            original_size_bytes / max(optimized_size_bytes, 1), 2
        )

        return OptimizationResult(
            data=optimized_bytes,
            format=output_format_normalized,
            category=category.strip().lower(),
            original_width=orig_w,
            original_height=orig_h,
            width=final_w,
            height=final_h,
            original_size_bytes=original_size_bytes,
            optimized_size_bytes=optimized_size_bytes,
            saved_bytes=saved_bytes,
            compression_ratio=compression_ratio,
            has_transparency=has_transparency,
            is_padded=is_padded,
        )

    @staticmethod
    def _has_transparency(img: Image.Image) -> bool:
        """Check whether the image possesses an alpha channel or transparency mask."""
        if img.mode in ("RGBA", "LA"):
            # Check if any pixel actually has alpha < 255
            try:
                alpha = img.getchannel("A")
                extrema = alpha.getextrema()
                # If minimum alpha is 255, image is completely opaque
                return extrema[0] < 255
            except Exception:
                return True
        if img.mode == "P" and "transparency" in img.info:
            return True
        return False

    @staticmethod
    def _normalize_color_mode(img: Image.Image, has_transparency: bool) -> Image.Image:
        """Convert CMYK, Palette, and Greyscale images to suitable RGB/RGBA modes."""
        if has_transparency:
            if img.mode != "RGBA":
                return img.convert("RGBA")
            return img
        else:
            if img.mode in ("CMYK", "P", "LA"):
                return img.convert("RGB")
            elif img.mode == "RGBA":
                # Fully opaque RGBA can be kept as RGB to save WebP metadata overhead
                return img.convert("RGB")
            elif img.mode not in ("RGB", "L"):
                return img.convert("RGB")
            return img

    @staticmethod
    def _pad_to_canvas(
        img: Image.Image,
        canvas_size: Tuple[int, int],
        has_transparency: bool,
        padding_color: Optional[Tuple[int, ...]] = None,
    ) -> Image.Image:
        """
        Center image on a canvas of target dimensions without distortion or cropping.
        """
        target_w, target_h = canvas_size
        img_w, img_h = img.size

        if has_transparency or img.mode == "RGBA":
            canvas_mode = "RGBA"
            bg_color = padding_color if padding_color is not None else DEFAULT_PADDING_COLOR_RGBA
            canvas = Image.new(canvas_mode, (target_w, target_h), bg_color)
            offset_x = (target_w - img_w) // 2
            offset_y = (target_h - img_h) // 2
            # Paste using alpha mask to preserve transparency cleanly
            canvas.paste(img, (offset_x, offset_y), mask=img if img.mode == "RGBA" else None)
            return canvas
        else:
            canvas_mode = "RGB"
            # Smart background auto-detection: Blends seamlessly with image edge
            if padding_color is not None:
                bg_color = padding_color
            else:
                bg_color = ImageOptimizer.detect_edge_background_color(img)
            canvas = Image.new(canvas_mode, (target_w, target_h), bg_color)
            offset_x = (target_w - img_w) // 2
            offset_y = (target_h - img_h) // 2
            canvas.paste(img, (offset_x, offset_y))
            return canvas

    @staticmethod
    def detect_edge_background_color(img: Image.Image) -> Tuple[int, int, int]:
        """
        Sample the perimeter border pixels of the image to detect its natural edge color.
        If corners/edges are near-white (>235), normalizes to pure Amazon white (255, 255, 255).
        Otherwise returns the dominant/median color along the photo's boundary so padding blends seamlessly.
        """
        w, h = img.size
        rgb_img = img.convert("RGB")
        border_pixels = []

        step_x = max(1, w // 40)
        step_y = max(1, h // 40)

        for x in range(0, w, step_x):
            border_pixels.append(rgb_img.getpixel((x, 0)))
            border_pixels.append(rgb_img.getpixel((x, max(0, h - 1))))
        for y in range(0, h, step_y):
            border_pixels.append(rgb_img.getpixel((0, y)))
            border_pixels.append(rgb_img.getpixel((max(0, w - 1), y)))

        r_avg = sum(c[0] for c in border_pixels) / len(border_pixels)
        g_avg = sum(c[1] for c in border_pixels) / len(border_pixels)
        b_avg = sum(c[2] for c in border_pixels) / len(border_pixels)

        # Amazon / Flipkart pure white threshold
        if r_avg > 235 and g_avg > 235 and b_avg > 235:
            return (255, 255, 255)

        # Pure black threshold
        if r_avg < 25 and g_avg < 25 and b_avg < 25:
            return (0, 0, 0)

        # Dominant color clustering
        from collections import Counter
        clustered = [((c[0] // 8) * 8, (c[1] // 8) * 8, (c[2] // 8) * 8) for c in border_pixels]
        most_common = Counter(clustered).most_common(1)[0][0]
        return most_common

    @staticmethod
    def _flatten_alpha(
        img: Image.Image, bg_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> Image.Image:
        """Flatten RGBA image onto solid background for non-alpha formats like JPEG."""
        background = Image.new("RGB", img.size, bg_color)
        background.paste(img, mask=img.split()[3])
        return background
