"""Command line interface for base_images."""

from __future__ import annotations

import argparse
from pathlib import Path

from base_images.generator import AssetGenerator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate favicon, app icon, and Open Graph assets from SVG files."
    )
    parser.add_argument("--base", required=True, type=Path, help="Base SVG file.")
    parser.add_argument("--output", required=True, type=Path, help="Output directory.")
    parser.add_argument("--micro", type=Path, help="Optional micro-tier SVG.")
    parser.add_argument("--search", type=Path, help="Optional search/UI-tier SVG.")
    parser.add_argument("--macro", type=Path, help="Optional macro-tier SVG.")
    parser.add_argument("--social", type=Path, help="Optional social preview SVG.")
    parser.add_argument(
        "--background",
        help="Solid background color used by solid-background outputs.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional JSON config file merged over configs/default-assets.json.",
    )

    args = parser.parse_args()
    generator = AssetGenerator(
        base_svg=args.base,
        output_dir=args.output,
        micro_svg=args.micro,
        search_svg=args.search,
        macro_svg=args.macro,
        social_svg=args.social,
        background=args.background,
        config=args.config,
    )
    generated = generator.generate()

    for asset in generated:
        print(asset.path)


if __name__ == "__main__":
    main()
