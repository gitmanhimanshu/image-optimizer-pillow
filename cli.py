"""CLI utility for category-wise image optimization."""

import argparse
import sys
from pathlib import Path
from image_optimizer.config import IMAGE_CONFIG
from image_optimizer.optimizer import ImageOptimizer
from image_optimizer.exceptions import ImageOptimizerError


def main():
    parser = argparse.ArgumentParser(
        description="Category-wise image optimizer using Python Pillow."
    )
    parser.add_argument(
        "-i", "--input", required=True, help="Path to input image file."
    )
    parser.add_argument(
        "-c",
        "--category",
        required=True,
        choices=list(IMAGE_CONFIG.keys()),
        help=f"Target category: {', '.join(IMAGE_CONFIG.keys())}",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Path to save optimized image (defaults to <name>_optimized.webp).",
    )
    parser.add_argument(
        "--pad-to-canvas",
        action="store_true",
        help="Pad image to exact canvas dimensions while preserving aspect ratio.",
    )
    parser.add_argument(
        "--allow-upscale",
        action="store_true",
        help="Allow upscaling if image is smaller than target dimensions.",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"Error: Input file does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    optimizer = ImageOptimizer()
    try:
        result = optimizer.optimize(
            image_input=input_path,
            category=args.category,
            pad_to_canvas=args.pad_to_canvas,
            allow_upscale=args.allow_upscale,
        )
    except ImageOptimizerError as e:
        print(f"Optimization failed: {e}", file=sys.stderr)
        sys.exit(1)

    output_path = (
        Path(args.output)
        if args.output
        else input_path.with_name(f"{input_path.stem}_{args.category}_opt.webp")
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(result.data)

    print("Optimization successful!")
    print(f"  Category:           {result.category}")
    print(f"  Original Size:      {result.original_width}x{result.original_height} ({result.original_size_bytes:,} bytes)")
    print(f"  Optimized Size:     {result.width}x{result.height} ({result.optimized_size_bytes:,} bytes)")
    print(f"  Format:             {result.format}")
    print(f"  Reduction:          {result.savings_percent}% ({result.saved_bytes:,} bytes saved)")
    print(f"  Saved to:           {output_path.resolve()}")


if __name__ == "__main__":
    main()

