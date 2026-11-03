"""
Copy original gallery photos with '_original' suffix and generate optimized versions
along with an interactive visual comparison HTML tool.
"""

import shutil
from pathlib import Path
from PIL import Image

from image_optimizer import ImageOptimizer, IMAGE_CONFIG

ORIGINAL_SOURCES = [
    Path(r"C:\Users\HP\Downloads\1767166405747_logo-nobg.png"),
    Path(r"C:\Users\HP\Downloads\B2B-Platform-Banner_1.webp"),
    Path(r"C:\Users\HP\Downloads\banners.webp"),
    Path(r"C:\Users\HP\Downloads\e42cf482-7e5e-4d6e-9939-8bdfde71f1bb.jpg"),
    Path(r"C:\Users\HP\Downloads\Flipkart_-_Personal_-_Microsoft_Edge_17-01-2025_13_36_09.png"),
    Path(r"C:\Users\HP\Downloads\Frame-1437256605-2-2.jpg"),
    Path(r"C:\Users\HP\Downloads\1.png"),
    Path(r"C:\Users\HP\Downloads\2nd.png"),
    Path(r"C:\Users\HP\Downloads\3rd.png"),
    Path(r"C:\Users\HP\Downloads\claude.png"),
    Path(r"C:\Users\HP\Downloads\converted-image.png"),
    Path(r"C:\Users\HP\Downloads\Discord_TA_pfp (1).webp"),
    Path(r"C:\Users\HP\Downloads\download.png"),
    Path(r"C:\Users\HP\Downloads\code2linkedin-extension\icons\icon128.png"),
]

def format_bytes(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.2f} MB"

def main():
    target_dir = Path(r"d:\photos\comparison")
    target_dir.mkdir(parents=True, exist_ok=True)

    optimizer = ImageOptimizer()
    comparison_items = []

    clean_sources = [p for p in ORIGINAL_SOURCES if p.is_file()][:14]
    print(f"Processing {len(clean_sources)} photos into {target_dir}...")

    for idx, src_path in enumerate(clean_sources, 1):
        clean_stem = src_path.stem.replace(" ", "_").replace("(", "").replace(")", "")[:25]
        orig_suffix = src_path.suffix.lower()

        # 1. Copy original file with suffix
        dest_orig_name = f"{idx:02d}_{clean_stem}_original{orig_suffix}"
        dest_orig_path = target_dir / dest_orig_name
        shutil.copy2(src_path, dest_orig_path)

        with Image.open(dest_orig_path) as im:
            orig_w, orig_h = im.size
        orig_size = dest_orig_path.stat().st_size

        item_data = {
            "id": idx,
            "name": clean_stem,
            "orig_file": dest_orig_name,
            "orig_dim": f"{orig_w}x{orig_h}",
            "orig_size": format_bytes(orig_size),
            "orig_bytes": orig_size,
            "categories": {},
        }

        # 2. Generate optimized versions for each category
        for cat in IMAGE_CONFIG.keys():
            res = optimizer.optimize(dest_orig_path, category=cat)
            opt_filename = f"{idx:02d}_{clean_stem}_{cat}_optimized.webp"
            opt_path = target_dir / opt_filename
            with open(opt_path, "wb") as f:
                f.write(res.data)

            item_data["categories"][cat] = {
                "file": opt_filename,
                "dim": f"{res.width}x{res.height}",
                "size": format_bytes(res.optimized_size_bytes),
                "saved_pct": f"{res.savings_percent:.1f}%",
                "bytes": res.optimized_size_bytes,
                "has_transparency": res.has_transparency,
            }

        comparison_items.append(item_data)
        print(f"[{idx:02d}/{len(clean_sources):02d}] Done: {clean_stem}")

    # 3. Generate HTML Visual Comparison Dashboard
    html_content = generate_html(comparison_items)
    index_html_path = target_dir / "index.html"
    with open(index_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\nCompleted! Comparison dashboard generated at: {index_html_path}")


def generate_html(items) -> str:
    cards_html = ""
    for item in items:
        # Default category: product
        prod = item["categories"]["product"]
        banner = item["categories"]["banner"]
        cat = item["categories"]["category"]
        logo = item["categories"]["logo"]
        template = item["categories"]["template"]

        cards_html += f"""
        <div class="card" id="card-{item['id']}">
            <div class="card-header">
                <h3>#{item['id']} {item['name']}</h3>
                <div class="tabs">
                    <button class="tab-btn active" onclick="switchCategory({item['id']}, 'product')">Product (800x800)</button>
                    <button class="tab-btn" onclick="switchCategory({item['id']}, 'category')">Category (600x400)</button>
                    <button class="tab-btn" onclick="switchCategory({item['id']}, 'banner')">Banner (1600x500)</button>
                    <button class="tab-btn" onclick="switchCategory({item['id']}, 'template')">Template (1200x800)</button>
                    <button class="tab-btn" onclick="switchCategory({item['id']}, 'logo')">Logo (400x200)</button>
                </div>
            </div>

            <div class="comparison-grid">
                <!-- Original Image Column -->
                <div class="img-box">
                    <div class="badge badge-orig">ORIGINAL</div>
                    <div class="img-wrapper">
                        <img src="{item['orig_file']}" alt="Original" loading="lazy" />
                    </div>
                    <div class="meta">
                        <div><strong>Dimensions:</strong> {item['orig_dim']}</div>
                        <div><strong>Size:</strong> {item['orig_size']}</div>
                        <div class="file-link"><a href="{item['orig_file']}" target="_blank">Open File</a></div>
                    </div>
                </div>

                <!-- Arrow -->
                <div class="arrow">&rarr;</div>

                <!-- Optimized Image Column -->
                <div class="img-box">
                    <div class="badge badge-opt">OPTIMIZED (WebP)</div>
                    <div class="img-wrapper">
                        <img id="opt-img-{item['id']}" src="{prod['file']}" alt="Optimized" loading="lazy" />
                    </div>
                    <div class="meta">
                        <div><strong>Dimensions:</strong> <span id="opt-dim-{item['id']}">{prod['dim']}</span></div>
                        <div><strong>Size:</strong> <span id="opt-size-{item['id']}">{prod['size']}</span> (<span id="opt-pct-{item['id']}" class="highlight">{prod['saved_pct']} saved</span>)</div>
                        <div class="file-link"><a id="opt-link-{item['id']}" href="{prod['file']}" target="_blank">Open File</a></div>
                    </div>
                </div>
            </div>
        </div>
        """

    # Embed JSON config for interactive client-side switching
    import json
    json_data = json.dumps(items)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Image Optimization Live Comparison</title>
<style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; }}
    header {{ text-align: center; margin-bottom: 30px; }}
    h1 {{ font-size: 28px; margin-bottom: 8px; color: #38bdf8; }}
    p.subtitle {{ color: #94a3b8; font-size: 14px; }}
    .stats-bar {{ display: flex; justify-content: center; gap: 24px; margin: 20px 0; }}
    .stat-pill {{ background: #1e293b; padding: 10px 18px; border-radius: 999px; border: 1px solid #334155; font-size: 13px; }}
    .stat-pill strong {{ color: #38bdf8; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; margin-bottom: 28px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }}
    .card-header {{ padding: 14px 20px; background: #182234; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }}
    .card-header h3 {{ font-size: 16px; color: #f1f5f9; }}
    .tabs {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    .tab-btn {{ background: #334155; color: #cbd5e1; border: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; transition: 0.2s; }}
    .tab-btn:hover {{ background: #475569; }}
    .tab-btn.active {{ background: #0284c7; color: #fff; font-weight: 600; }}
    .comparison-grid {{ display: grid; grid-template-columns: 1fr auto 1fr; gap: 16px; padding: 20px; align-items: center; }}
    .img-box {{ background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 12px; display: flex; flex-direction: column; align-items: center; position: relative; }}
    .badge {{ position: absolute; top: 12px; left: 12px; padding: 3px 8px; font-size: 10px; font-weight: bold; border-radius: 4px; }}
    .badge-orig {{ background: #475569; color: #e2e8f0; }}
    .badge-opt {{ background: #059669; color: #ecfdf5; }}
    .img-wrapper {{ width: 100%; height: 320px; display: flex; align-items: center; justify-content: center; background: repeating-conic-gradient(#1e293b 0% 25%, #0f172a 0% 50%) 50% / 20px 20px; border-radius: 6px; overflow: hidden; margin: 24px 0 12px; }}
    .img-wrapper img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
    .meta {{ width: 100%; font-size: 13px; line-height: 1.6; color: #cbd5e1; border-top: 1px solid #1e293b; padding-top: 8px; }}
    .arrow {{ font-size: 28px; color: #38bdf8; font-weight: bold; }}
    .highlight {{ color: #4ade80; font-weight: bold; }}
    .file-link a {{ color: #38bdf8; text-decoration: none; font-size: 12px; }}
    .file-link a:hover {{ text-decoration: underline; }}
    @media (max-width: 900px) {{
        .comparison-grid {{ grid-template-columns: 1fr; }}
        .arrow {{ transform: rotate(90deg); text-align: center; }}
    }}
</style>
</head>
<body>
    <header>
        <h1>Live Side-by-Side Image Optimization Comparison</h1>
        <p class="subtitle">14 Real Gallery Photos tested across 5 E-commerce Categories with Python Pillow</p>
        <div class="stats-bar">
            <div class="stat-pill">No Cropping: <strong>100%</strong></div>
            <div class="stat-pill">No Distortion: <strong>100%</strong></div>
            <div class="stat-pill">LANCZOS Resampling: <strong>Active</strong></div>
            <div class="stat-pill">WebP Compression: <strong>Active</strong></div>
        </div>
    </header>

    <div class="cards-container">
        {cards_html}
    </div>

    <script>
        const data = {json_data};
        const itemsMap = {{}};
        data.forEach(item => itemsMap[item.id] = item);

        function switchCategory(itemId, catName) {{
            const card = document.getElementById('card-' + itemId);
            const btns = card.querySelectorAll('.tab-btn');
            btns.forEach(btn => {{
                if (btn.textContent.toLowerCase().includes(catName)) {{
                    btn.classList.add('active');
                }} else {{
                    btn.classList.remove('active');
                }}
            }});

            const item = itemsMap[itemId];
            const catData = item.categories[catName];
            if (!catData) return;

            document.getElementById('opt-img-' + itemId).src = catData.file;
            document.getElementById('opt-dim-' + itemId).textContent = catData.dim;
            document.getElementById('opt-size-' + itemId).textContent = catData.size;
            document.getElementById('opt-pct-' + itemId).textContent = catData.saved_pct + ' saved';
            document.getElementById('opt-link-' + itemId).href = catData.file;
        }}
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    main()

