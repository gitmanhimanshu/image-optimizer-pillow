# Category-Wise Image Optimization System

A lightweight, production-ready image optimization and resizing system built with **Python Pillow (PIL)** for e-commerce platforms.

---

## Centralized Category Configuration

Defined in [`image_optimizer/config.py`](file:///d:/photos/image_optimizer/config.py):

| Category   | Target Width | Target Height | Quality | Pad to Canvas |
|------------|-------------:|--------------:|--------:|--------------:|
| `product`  | 800 px       | 800 px        | 88      | Optional      |
| `category` | 600 px       | 400 px        | 88      | Optional      |
| `banner`   | 1600 px      | 500 px        | 90      | Optional      |
| `template` | 1200 px      | 800 px        | 90      | Optional      |
| `logo`     | 400 px       | 200 px        | 90      | Optional      |

---

## Features & Guarantees

1. **Aspect Ratio Preservation**: Resizes using `ImageOps.contain()` and `Image.Resampling.LANCZOS`. Zero cropping and zero distortion.
2. **No Unnecessary Upscaling**: Images smaller than target dimensions retain their original resolution unless explicitly requested (`allow_upscale=False` by default).
3. **EXIF Orientation Auto-Correction**: Fixes smartphone and camera orientations via `ImageOps.exif_transpose`.
4. **WebP Optimization**: Converts supported images to high-compression WebP.
5. **Transparency Preservation**: Retains alpha channel transparency for PNG/WebP images and logos.
6. **Exact Canvas Padding**: Option to center contained images on an exact-size canvas with transparent or white background.
7. **Production Storage Adapters**: Pluggable storage for `LocalStorage`, `MemoryStorage`, `S3StorageAdapter` (AWS S3 & Cloudflare R2), and `CloudinaryStorageAdapter`.
8. **Deduplication & Safety**: Prevents duplicate processing via SHA-256 caching and validates file size, headers, and image integrity.

---

## Quick Usage

### 1. Python API
```python
from image_optimizer import ImageOptimizer

optimizer = ImageOptimizer()
result = optimizer.optimize("path/to/upload.jpg", category="product")

print(f"Optimized: {result.width}x{result.height}, {result.format}, saved {result.savings_percent}%")
with open("optimized.webp", "wb") as f:
    f.write(result.data)
```

### 2. End-to-End Upload Pipeline
```python
from image_optimizer import ImageUploadPipeline, LocalStorage

storage = LocalStorage(base_dir="uploads", base_url="/media")
pipeline = ImageUploadPipeline(storage=storage, preserve_original=True)

result = pipeline.process_and_store(
    file_input=uploaded_file_bytes,
    filename="sneaker.png",
    category="product"
)
print("Optimized URL:", result.url)
print("Original backup URL:", result.original_url)
```

### 3. CLI Command
```bash
python cli.py --input sample.jpg --category product
python cli.py --input logo.png --category logo --pad-to-canvas
```

---

## Integration Guides

### FastAPI
```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from image_optimizer import ImageUploadPipeline, LocalStorage

app = FastAPI()
pipeline = ImageUploadPipeline(storage=LocalStorage("uploads", "/media"))

@app.post("/upload/{category}")
async def upload(category: str, file: UploadFile = File(...)):
    try:
        content = await file.read()
        res = pipeline.process_and_store(content, file.filename, category)
        return res.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Flask
```python
from flask import Flask, request, jsonify
from image_optimizer import ImageUploadPipeline, LocalStorage

app = Flask(__name__)
pipeline = ImageUploadPipeline(storage=LocalStorage("uploads", "/media"))

@app.route("/upload/<category>", methods=["POST"])
def upload(category):
    file = request.files["image"]
    res = pipeline.process_and_store(file.stream, file.filename, category)
    return jsonify(res.to_dict())
```

---

## Running Tests

```bash
python -m unittest tests/test_optimizer.py
```

