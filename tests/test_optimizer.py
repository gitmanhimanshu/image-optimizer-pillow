"""
Comprehensive Test Suite for Image Optimization System.
Covers all requirements from Section 5 of t.txt:
- Portrait images (height > width)
- Landscape images (width > height)
- Square images (width == height)
- High-resolution images (4K UHD)
- Low-resolution images (smaller than category config - no unnecessary upscaling)
- Transparent PNG images (alpha preservation in WebP)
- Multi-format support (JPEG, PNG, WEBP, BMP, GIF)
- Aspect ratio preservation (no distortion, no cropping)
- Output dimensions matching category configuration
- File size optimization
- Invalid/corrupted file error handling
- Canvas containment padding
- Upload pipeline and deduplication
"""

import io
import unittest
from PIL import Image

from image_optimizer.config import IMAGE_CONFIG, get_category_config
from image_optimizer.optimizer import ImageOptimizer
from image_optimizer.pipeline import ImageUploadPipeline
from image_optimizer.storage import MemoryStorage
from image_optimizer.exceptions import (
    InvalidImageError,
    CorruptedImageError,
    CategoryNotFoundError,
    FileSizeExceededError,
)
from tests.generate_test_assets import (
    create_portrait_image,
    create_landscape_image,
    create_square_image,
    create_high_res_image,
    create_low_res_image,
    create_transparent_png,
    create_format_samples,
)


class TestImageOptimizer(unittest.TestCase):

    def setUp(self):
        self.optimizer = ImageOptimizer()

    def test_portrait_image_preserves_aspect_ratio_no_crop_no_distortion(self):
        """Portrait image (1200x2400, aspect ratio 0.5) optimized for 'product' (800x800)."""
        data = create_portrait_image(1200, 2400)
        res = self.optimizer.optimize(data, category="product")

        # Must fit within 800x800
        self.assertLessEqual(res.width, 800)
        self.assertLessEqual(res.height, 800)
        # Bounding box constraint: height is maxed out at 800, width scaled down proportionally
        self.assertEqual(res.height, 800)
        self.assertEqual(res.width, 400)

        # Aspect ratio check: 1200/2400 = 0.5, 400/800 = 0.5
        orig_ratio = 1200 / 2400
        opt_ratio = res.width / res.height
        self.assertAlmostEqual(orig_ratio, opt_ratio, places=2)

        # WebP format check
        self.assertEqual(res.format, "WEBP")
        self.assertLess(res.optimized_size_bytes, res.original_size_bytes)

    def test_landscape_image_preserves_aspect_ratio_no_crop_no_distortion(self):
        """Landscape image (2400x1200, aspect ratio 2.0) optimized for 'banner' (1600x500)."""
        data = create_landscape_image(2400, 1200)
        res = self.optimizer.optimize(data, category="banner")

        # Must fit within 1600x500
        self.assertLessEqual(res.width, 1600)
        self.assertLessEqual(res.height, 500)
        # Limiting dimension is height: 500 * 2 = 1000 width
        self.assertEqual(res.height, 500)
        self.assertEqual(res.width, 1000)

        orig_ratio = 2400 / 1200
        opt_ratio = res.width / res.height
        self.assertAlmostEqual(orig_ratio, opt_ratio, places=2)
        self.assertEqual(res.format, "WEBP")

    def test_square_image_dimensions(self):
        """Square image (1500x1500) optimized for 'product' (800x800)."""
        data = create_square_image(1500)
        res = self.optimizer.optimize(data, category="product")

        self.assertEqual(res.width, 800)
        self.assertEqual(res.height, 800)
        self.assertEqual(res.aspect_ratio, 1.0)
        self.assertLess(res.optimized_size_bytes, res.original_size_bytes)

    def test_high_resolution_image_optimization(self):
        """4K image (3840x2160) for 'template' (1200x800)."""
        data = create_high_res_image(3840, 2160)
        res = self.optimizer.optimize(data, category="template")

        self.assertLessEqual(res.width, 1200)
        self.assertLessEqual(res.height, 800)
        # Significant file size reduction
        self.assertGreater(res.savings_percent, 50.0)

    def test_low_resolution_image_does_not_upscale_unnecessarily(self):
        """Low-res image (150x100) must NOT be upscaled by default."""
        data = create_low_res_image(150, 100)
        res = self.optimizer.optimize(data, category="product", allow_upscale=False)

        # Dimensions must remain original 150x100, not blown up to 800x800
        self.assertEqual(res.width, 150)
        self.assertEqual(res.height, 100)

    def test_transparent_png_preserves_alpha_transparency(self):
        """Logo with alpha channel retains transparency in WebP output."""
        data = create_transparent_png(600, 300)
        res = self.optimizer.optimize(data, category="logo")

        self.assertTrue(res.has_transparency)
        # Verify alpha channel in resulting WebP image
        with Image.open(io.BytesIO(res.data)) as loaded_img:
            self.assertEqual(loaded_img.mode, "RGBA")
            # Verify transparent pixels exist
            alpha = loaded_img.getchannel("A")
            min_alpha, max_alpha = alpha.getextrema()
            self.assertEqual(min_alpha, 0)  # Contains transparent areas

    def test_exact_canvas_dimensions_with_padding(self):
        """When pad_to_canvas=True, output has exact target dimensions with image centered."""
        data = create_portrait_image(600, 1200)  # aspect 0.5
        # Category config has 600x400
        res = self.optimizer.optimize(data, category="category", pad_to_canvas=True)

        self.assertEqual(res.width, 600)
        self.assertEqual(res.height, 400)
        self.assertTrue(res.is_padded)

    def test_all_configured_categories(self):
        """Verify each category in IMAGE_CONFIG processes successfully."""
        data = create_landscape_image(2000, 1000)
        for cat, cfg in IMAGE_CONFIG.items():
            res = self.optimizer.optimize(data, category=cat)
            self.assertLessEqual(res.width, cfg["width"])
            self.assertLessEqual(res.height, cfg["height"])
            self.assertEqual(res.format, "WEBP")

    def test_various_image_formats_supported(self):
        """Verify JPEG, PNG, WEBP, BMP, GIF are all handled cleanly."""
        samples = create_format_samples()
        for fmt, sample_bytes in samples.items():
            res = self.optimizer.optimize(sample_bytes, category="product")
            self.assertEqual(res.format, "WEBP")
            self.assertGreater(len(res.data), 0)

    def test_invalid_and_corrupt_files_handled_gracefully(self):
        """Gracefully handle bad inputs without crashing."""
        # Empty input
        with self.assertRaises(InvalidImageError):
            self.optimizer.optimize(b"", category="product")

        # Corrupt data with fake header
        fake_jpeg = b"\xFF\xD8\xFF\xE0" + b"random corrupt gibberish"
        with self.assertRaises(CorruptedImageError):
            self.optimizer.optimize(fake_jpeg, category="product")

        # Random text file
        with self.assertRaises(InvalidImageError):
            self.optimizer.optimize(b"Hello world, this is a plain text file", category="product")

    def test_unknown_category_raises_error(self):
        """Unknown category triggers CategoryNotFoundError."""
        data = create_square_image(200)
        with self.assertRaises(CategoryNotFoundError):
            self.optimizer.optimize(data, category="unknown_nonexistent_category")

    def test_file_size_limit_enforced(self):
        """Oversized files are rejected before processing."""
        data = b"\xFF\xD8\xFF" + (b"0" * 1000)
        from image_optimizer.validator import read_and_validate_input
        with self.assertRaises(FileSizeExceededError):
            read_and_validate_input(data, max_size_bytes=500)


class TestUploadPipeline(unittest.TestCase):

    def setUp(self):
        self.storage = MemoryStorage()
        self.pipeline = ImageUploadPipeline(
            storage=self.storage,
            preserve_original=True,
            enable_deduplication=True,
        )

    def test_pipeline_process_and_store(self):
        data = create_landscape_image(1800, 900)
        result = self.pipeline.process_and_store(
            file_input=data,
            filename="my_product.jpg",
            category="product",
        )

        self.assertTrue(result.url.startswith("memory://product/my_product_"))
        self.assertTrue(result.original_url.startswith("memory://originals/product/my_product_"))
        self.assertEqual(result.category, "product")
        self.assertEqual(result.format, "WEBP")
        self.assertLessEqual(result.width, 800)
        self.assertLessEqual(result.height, 800)
        self.assertFalse(result.is_cached)

    def test_pipeline_deduplication(self):
        data = create_square_image(600)
        res1 = self.pipeline.process_and_store(data, "item.png", "category")
        self.assertFalse(res1.is_cached)

        # Second upload with exact same bytes
        res2 = self.pipeline.process_and_store(data, "item_copy.png", "category")
        self.assertTrue(res2.is_cached)
        self.assertEqual(res1.url, res2.url)


if __name__ == "__main__":
    unittest.main()

