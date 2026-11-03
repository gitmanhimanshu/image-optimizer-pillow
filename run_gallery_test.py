"""
Test the Image Optimizer against 12-15 real user gallery photos across all dimensions/categories.
"""

import sys
from pathlib import Path
from PIL import Image

from image_optimizer import ImageOptimizer, IMAGE_CONFIG

CANDIDATE_PATHS = [
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

def main():
    existing_photos = [p for p in CANDIDATE_PATHS if p.is_file()][:14]
    
    if not existing_photos:
        print("No candidate photos found.")
        return

    output_dir = Path("d:/photos/gallery_test_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    optimizer = ImageOptimizer()
    categories = list(IMAGE_CONFIG.keys())

    print(f"Found {len(existing_photos)} real photos to test across {len(categories)} categories.\n")

    results_table = []

    for idx, photo_path in enumerate(existing_photos, 1):
        try:
            with Image.open(photo_path) as im:
                orig_w, orig_h = im.size
                orig_mode = im.mode
                orig_fmt = im.format
            orig_size = photo_path.stat().st_size
            orig_ratio = orig_w / orig_h if orig_h else 0
        except Exception as e:
            print(f"Skipping {photo_path.name}: {e}")
            continue

        photo_category_results = []
        for cat in categories:
            cfg = IMAGE_CONFIG[cat]
            target_w, target_h = cfg["width"], cfg["height"]

            res = optimizer.optimize(photo_path, category=cat)

            # Check bounds
            fits_bounds = (res.width <= target_w) and (res.height <= target_h)
            
            # Check aspect ratio
            res_ratio = res.width / res.height if res.height else 0
            ratio_match = abs(orig_ratio - res_ratio) < 0.02 or (res.width == orig_w and res.height == orig_h)

            # Save sample to output directory
            out_filename = f"img{idx}_{photo_path.stem[:15]}_{cat}.webp"
            out_path = output_dir / out_filename
            with open(out_path, "wb") as f:
                f.write(res.data)

            photo_category_results.append({
                "category": cat,
                "target": f"{target_w}x{target_h}",
                "output_dim": f"{res.width}x{res.height}",
                "opt_size": res.optimized_size_bytes,
                "savings_pct": res.savings_percent,
                "transparency": res.has_transparency,
                "fits": fits_bounds,
                "ratio_match": ratio_match,
            })

        results_table.append({
            "idx": idx,
            "filename": photo_path.name[:25],
            "orig_dim": f"{orig_w}x{orig_h}",
            "orig_size": orig_size,
            "orig_fmt": orig_fmt or photo_path.suffix.upper(),
            "orig_mode": orig_mode,
            "cat_results": photo_category_results,
        })

    # Print summary report
    print("=" * 115)
    print(f"{'#':<3} | {'Original File':<25} | {'Orig Dim':<11} | {'Orig Size':<10} | {'Category':<9} | {'Target Max':<11} | {'Output Dim':<11} | {'Opt Size':<10} | {'Saved %':<8} | {'Aspect OK'}")
    print("=" * 115)

    for item in results_table:
        for c_idx, cr in enumerate(item["cat_results"]):
            file_col = item["filename"] if c_idx == 0 else ""
            orig_dim_col = item["orig_dim"] if c_idx == 0 else ""
            orig_size_col = f"{item['orig_size']:,} B" if c_idx == 0 else ""
            num_col = str(item["idx"]) if c_idx == 0 else ""

            aspect_ok = "PASS" if cr["ratio_match"] and cr["fits"] else "FAIL"
            print(f"{num_col:<3} | {file_col:<25} | {orig_dim_col:<11} | {orig_size_col:<10} | {cr['category']:<9} | {cr['target']:<11} | {cr['output_dim']:<11} | {cr['opt_size']:>8,} B | {cr['savings_pct']:>6.1f}% | {aspect_ok}")
        print("-" * 115)

    print(f"\nAll optimized files have been saved to: {output_dir.resolve()}")

if __name__ == "__main__":
    main()

