"""Core SVG asset generation."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from base_images.config import AssetConfig, OutputSpec, SvgTier, resolve_config
from base_images.templates import render_asset_html


@dataclass(frozen=True)
class GeneratedAsset:
    """A file written by the generator."""

    key: str
    path: Path


class AssetGenerator:
    """Generate favicon, app icon, and social preview assets from SVG files."""

    def __init__(
        self,
        base_svg: Path | str,
        output_dir: Path | str,
        *,
        micro_svg: Path | str | None = None,
        search_svg: Path | str | None = None,
        macro_svg: Path | str | None = None,
        social_svg: Path | str | None = None,
        background: str | None = None,
        wordmark: str | None = None,
        config: AssetConfig | Mapping[str, Any] | Path | str | None = None,
    ) -> None:
        self.base_svg = Path(base_svg)
        self.output_dir = Path(output_dir)
        self.background = background
        self.wordmark = wordmark
        self.config = resolve_config(config)
        self.svg_paths: dict[SvgTier, Path] = {
            "micro": Path(micro_svg) if micro_svg else self.base_svg,
            "search": Path(search_svg) if search_svg else self.base_svg,
            "macro": Path(macro_svg) if macro_svg else self.base_svg,
            "social": Path(social_svg) if social_svg else self.base_svg,
        }

    def generate(self) -> list[GeneratedAsset]:
        """Generate every configured asset and metadata file."""

        self.output_dir.mkdir(parents=True, exist_ok=True)
        generated: list[GeneratedAsset] = []

        for spec in self.config.outputs:
            generated.append(self.generate_spec(spec))

        generated.append(self._write_manifest())
        generated.append(self._write_html_snippet())
        return generated

    def generate_spec(self, spec: OutputSpec) -> GeneratedAsset:
        """Generate a single configured output."""

        destination = self.output_dir / spec.filename
        svg_text = self.svg_for_tier(spec.tier).read_text(encoding="utf-8")

        if spec.format == "svg":
            destination.write_text(svg_text, encoding="utf-8")
        elif spec.format == "ico":
            self._render_ico(spec, svg_text, destination)
        elif spec.format in {"png", "jpg", "jpeg"}:
            self._render_raster(spec, svg_text, destination)
        else:
            raise ValueError(f"Unsupported format {spec.format!r}")

        return GeneratedAsset(key=spec.key, path=destination)

    def svg_for_tier(self, tier: SvgTier) -> Path:
        """Return the SVG path selected for a tier, falling back to the base SVG."""

        return self.svg_paths[tier]

    def render_html(self, spec: OutputSpec) -> str:
        """Render the HTML template for a spec without taking a screenshot."""

        svg_text = self.svg_for_tier(spec.tier).read_text(encoding="utf-8")
        return render_asset_html(
            spec,
            svg_text,
            self._background_color(),
            wordmark_text=self.wordmark,
            wordmark_style=self.config.wordmark,
        )

    def render_html_for_key(self, key: str) -> str:
        """Render the HTML template for a configured output key."""

        return self.render_html(self.config.spec(key))

    def _render_raster(self, spec: OutputSpec, svg_text: str, destination: Path) -> None:
        png_path = destination
        if spec.format in {"jpg", "jpeg"}:
            png_path = destination.with_suffix(".png")

        self._screenshot_html(spec, svg_text, png_path)

        if spec.format in {"jpg", "jpeg"}:
            self._write_jpeg(png_path, destination, spec)
            png_path.unlink(missing_ok=True)

    def _render_ico(self, spec: OutputSpec, svg_text: str, destination: Path) -> None:
        from PIL import Image

        sizes = spec.ico_sizes or ((spec.width, spec.height),)
        png_paths: list[Path] = []

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            for width, height in sizes:
                size_spec = _resize_spec(spec, width, height)
                png_path = temp_path / f"favicon-{width}x{height}.png"
                self._screenshot_html(size_spec, svg_text, png_path)
                png_paths.append(png_path)

            images = [Image.open(path).convert("RGBA") for path in png_paths]
            images[0].save(destination, format="ICO", sizes=sizes, append_images=images[1:])

    def _screenshot_html(self, spec: OutputSpec, svg_text: str, destination: Path) -> None:
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is required to render images. Install dependencies with "
                "`pipenv install --dev` and browsers with `pipenv run playwright install chromium`."
            ) from exc

        html = render_asset_html(
            spec,
            svg_text,
            self._background_color(),
            wordmark_text=self.wordmark,
            wordmark_style=self.config.wordmark,
        )

        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch()
            except PlaywrightError as exc:
                raise RuntimeError(
                    "Playwright Chromium and its Linux system dependencies are required "
                    "to render images. Install them with "
                    "`pipenv run playwright install --with-deps chromium`."
                ) from exc

            try:
                page = browser.new_page(
                    viewport={"width": spec.width, "height": spec.height},
                    device_scale_factor=1,
                )
                page.set_content(html, wait_until="load")
                page.evaluate(
                    "() => document.fonts ? document.fonts.ready : Promise.resolve()"
                )
                page.screenshot(
                    path=str(destination),
                    omit_background=spec.background == "transparent",
                )
            finally:
                browser.close()

    def _write_jpeg(self, source_png: Path, destination: Path, spec: OutputSpec) -> None:
        from PIL import Image

        image = Image.open(source_png).convert("RGB")
        quality = spec.quality
        while True:
            image.save(destination, format="JPEG", quality=quality, optimize=True)
            if spec.max_bytes is None or destination.stat().st_size <= spec.max_bytes:
                return
            if quality <= spec.min_quality:
                return
            quality = max(spec.min_quality, quality - 5)

    def _write_manifest(self) -> GeneratedAsset:
        icons = []
        specs_by_key = {spec.key: spec for spec in self.config.outputs}
        for key in self.config.manifest_icon_keys:
            spec = specs_by_key.get(key)
            if spec is None:
                continue
            icons.append(
                {
                    "src": f"/{spec.filename}",
                    "sizes": f"{spec.width}x{spec.height}",
                    "type": f"image/{'jpeg' if spec.format == 'jpg' else spec.format}",
                    "purpose": "any",
                }
            )

        destination = self.output_dir / self.config.manifest_filename
        destination.write_text(
            json.dumps({"icons": icons}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return GeneratedAsset(key="manifest", path=destination)

    def _write_html_snippet(self) -> GeneratedAsset:
        destination = self.output_dir / self.config.html_snippet_filename
        destination.write_text(self.html_snippet(), encoding="utf-8")
        return GeneratedAsset(key="html-snippet", path=destination)

    def html_snippet(self) -> str:
        """Return the HTML snippet users should paste into their document head."""

        spec_by_key = {spec.key: spec for spec in self.config.outputs}
        og = spec_by_key.get("og-image")
        twitter = spec_by_key.get("twitter-image")
        favicon_svg = spec_by_key.get("favicon-svg")
        favicon_ico = spec_by_key.get("favicon-ico")
        apple = spec_by_key.get("apple-touch-icon")
        additional_social_images = _additional_social_image_snippet(spec_by_key)

        og_filename = og.filename if og else "og-image.jpg"
        og_width = og.width if og else 1200
        og_height = og.height if og else 630
        twitter_filename = twitter.filename if twitter else og_filename
        favicon_svg_filename = favicon_svg.filename if favicon_svg else "favicon.svg"
        favicon_ico_filename = favicon_ico.filename if favicon_ico else "favicon.ico"
        apple_filename = apple.filename if apple else "apple-touch-icon.png"

        return f"""<!-- Open Graph / Social Previews -->
<meta property="og:image" content="/{og_filename}" />
<meta property="og:image:width" content="{og_width}" />
<meta property="og:image:height" content="{og_height}" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:image" content="/{twitter_filename}" />
{additional_social_images}

<!-- Favicons (Modern & Legacy) -->
<link rel="icon" href="/{favicon_svg_filename}" type="image/svg+xml" />
<link rel="icon" href="/{favicon_ico_filename}" sizes="32x32" />

<!-- OS Native Icons -->
<link rel="apple-touch-icon" href="/{apple_filename}" />
<link rel="manifest" href="/{self.config.manifest_filename}" />
"""

    def _background_color(self) -> str:
        return self.background or self.config.background


def _additional_social_image_snippet(spec_by_key: Mapping[str, OutputSpec]) -> str:
    social_image_keys = (
        ("linkedin-image", "LinkedIn link preview"),
        ("social-square", "Square social fallback"),
        ("social-portrait", "Portrait feed export"),
        ("pinterest-pin", "Pinterest pin export"),
        ("story-image", "Story/Reels export"),
    )
    lines: list[str] = []
    for key, label in social_image_keys:
        spec = spec_by_key.get(key)
        if spec is None:
            continue
        lines.extend(
            [
                f"<!-- {label} -->",
                f'<meta property="og:image" content="/{spec.filename}" />',
                f'<meta property="og:image:width" content="{spec.width}" />',
                f'<meta property="og:image:height" content="{spec.height}" />',
            ]
        )

    if not lines:
        return ""
    return "\n<!-- Additional Social Image Exports -->\n" + "\n".join(lines)


def _resize_spec(spec: OutputSpec, width: int, height: int) -> OutputSpec:
    return OutputSpec(
        key=spec.key,
        filename=spec.filename,
        width=width,
        height=height,
        aspect_ratio=f"{width}:{height}" if width != height else "1:1",
        format="png",
        background=spec.background,
        tier=spec.tier,
        padding_percent=spec.padding_percent,
        safe_zone=None,
        quality=spec.quality,
        min_quality=spec.min_quality,
        max_bytes=spec.max_bytes,
        wordmark=spec.wordmark,
        background_gradient=spec.background_gradient,
    )
