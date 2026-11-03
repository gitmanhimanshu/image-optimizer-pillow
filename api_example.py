"""
Integration Examples: Showing how to plug the optimizer into existing web frameworks.

This file provides production-ready snippets for:
1. FastAPI
2. Flask
3. Django
4. Standalone Python script / Celery background task
"""

from pathlib import Path
from image_optimizer import ImageOptimizer, ImageUploadPipeline, LocalStorage

# Shared pipeline instance
storage = LocalStorage(base_dir="uploads", base_url="/media")
pipeline = ImageUploadPipeline(storage=storage, preserve_original=True)


# ==========================================
# 1. FastAPI Integration
# ==========================================
def create_fastapi_router():
    """
    Example FastAPI upload endpoint.
    Usage:
        from fastapi import FastAPI, UploadFile, File, Form, HTTPException
        app = FastAPI()
        app.include_router(create_fastapi_router())
    """
    try:
        from fastapi import APIRouter, UploadFile, File, Form, HTTPException
        router = APIRouter()

        @router.post("/api/upload/{category}")
        async def upload_image(
            category: str,
            file: UploadFile = File(...),
            pad_to_canvas: bool = Form(False),
        ):
            try:
                # Read upload file contents
                content = await file.read()
                result = pipeline.process_and_store(
                    file_input=content,
                    filename=file.filename or "upload.jpg",
                    category=category,
                    pad_to_canvas=pad_to_canvas,
                )
                return result.to_dict()
            except Exception as exc:
                raise HTTPException(status_code=400, detail=str(exc))

        return router
    except ImportError:
        return None


# ==========================================
# 2. Flask Integration
# ==========================================
def create_flask_blueprint():
    """
    Example Flask upload endpoint.
    Usage:
        from flask import Flask
        app = Flask(__name__)
        app.register_blueprint(create_flask_blueprint())
    """
    try:
        from flask import Blueprint, request, jsonify
        bp = Blueprint("images", __name__)

        @bp.route("/api/upload/<category>", methods=["POST"])
        def upload_image(category):
            if "image" not in request.files:
                return jsonify({"error": "No image field provided"}), 400
            file = request.files["image"]
            pad_to_canvas = request.form.get("pad_to_canvas", "false").lower() == "true"

            try:
                result = pipeline.process_and_store(
                    file_input=file.stream,
                    filename=file.filename or "upload.jpg",
                    category=category,
                    pad_to_canvas=pad_to_canvas,
                )
                return jsonify(result.to_dict()), 200
            except Exception as exc:
                return jsonify({"error": str(exc)}), 400

        return bp
    except ImportError:
        return None


# ==========================================
# 3. Django Integration Example
# ==========================================
"""
# In your Django views.py:
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from image_optimizer import ImageUploadPipeline, LocalStorage

pipeline = ImageUploadPipeline(storage=LocalStorage("media/uploads", "/media/uploads"))

@csrf_exempt
def upload_image_view(request, category):
    if request.method != "POST" or "image" not in request.FILES:
        return JsonResponse({"error": "POST request with 'image' file required."}, status=400)

    uploaded_file = request.FILES["image"]
    pad_to_canvas = request.POST.get("pad_to_canvas", "").lower() == "true"

    try:
        res = pipeline.process_and_store(
            file_input=uploaded_file.read(),
            filename=uploaded_file.name,
            category=category,
            pad_to_canvas=pad_to_canvas,
        )
        return JsonResponse(res.to_dict())
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)
"""


# ==========================================
# 4. Direct Standalone Usage
# ==========================================
def direct_example():
    optimizer = ImageOptimizer()
    print("Testing direct optimization on test square image...")
    from tests.generate_test_assets import create_square_image
    sample_bytes = create_square_image(1200)

    res = optimizer.optimize(sample_bytes, category="product")
    print(f"Product optimization result: {res.width}x{res.height}, {res.format}, saved {res.savings_percent}%")


if __name__ == "__main__":
    direct_example()

