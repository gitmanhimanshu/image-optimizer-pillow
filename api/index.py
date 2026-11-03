"""
Vercel Serverless Function for Image Optimization.
Route: /api/optimize
"""

import base64
import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Add project root directory to sys.path so image_optimizer can be imported on Vercel
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from image_optimizer import ImageOptimizer

optimizer = ImageOptimizer()


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(
            json.dumps({
                "status": "healthy",
                "service": "Image Optimizer Serverless Function",
                "version": "1.0.0"
            }).encode("utf-8")
        )

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length)

        try:
            payload = json.loads(post_body.decode("utf-8"))
            data_url = payload.get("image", "")

            # Extract base64
            if "," in data_url:
                header, b64_data = data_url.split(",", 1)
            else:
                b64_data = data_url

            raw_bytes = base64.b64decode(b64_data)
            width = int(payload.get("width", 800))
            height = int(payload.get("height", 800))
            quality = int(payload.get("quality", 88))
            mode = payload.get("mode", "stretch")
            allow_upscale = bool(payload.get("allow_upscale", False))
            category = payload.get("category", "custom")

            res = optimizer.optimize(
                image_input=raw_bytes,
                category=category,
                custom_dimensions=(width, height),
                custom_quality=quality,
                mode=mode,
                allow_upscale=allow_upscale,
            )

            out_b64 = base64.b64encode(res.data).decode("ascii")
            out_data_url = f"data:image/{res.format.lower()};base64,{out_b64}"

            response_payload = {
                "width": res.width,
                "height": res.height,
                "original_width": res.original_width,
                "original_height": res.original_height,
                "original_size_bytes": res.original_size_bytes,
                "optimized_size_bytes": res.optimized_size_bytes,
                "saved_bytes": res.saved_bytes,
                "savings_percent": res.savings_percent,
                "format": res.format,
                "has_transparency": res.has_transparency,
                "is_padded": res.is_padded,
                "optimized_image": out_data_url,
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_payload).encode("utf-8"))

        except Exception as e:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def log_message(self, format, *args):
        pass
