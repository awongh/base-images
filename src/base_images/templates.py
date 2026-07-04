"""HTML template helpers used as the rendering source of truth."""

from __future__ import annotations

import base64
import html

from base_images.config import OutputSpec


def render_asset_html(spec: OutputSpec, svg_text: str, background_color: str) -> str:
    """Build the HTML document rendered by the browser screenshot step."""

    image_width, image_height = _artwork_box(spec)
    background = (
        background_color if spec.background == "solid" else "transparent"
    )
    svg_data = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width={spec.width}, initial-scale=1">
  <style>
    * {{
      box-sizing: border-box;
    }}

    html,
    body {{
      width: {spec.width}px;
      height: {spec.height}px;
      margin: 0;
      overflow: hidden;
      background: {html.escape(background)};
    }}

    body {{
      display: grid;
      place-items: center;
    }}

    .asset-canvas {{
      width: {spec.width}px;
      height: {spec.height}px;
      display: grid;
      place-items: center;
      background: {html.escape(background)};
    }}

    .asset-artwork {{
      width: {image_width}px;
      height: {image_height}px;
      display: grid;
      place-items: center;
    }}

    .asset-artwork img {{
      display: block;
      max-width: 100%;
      max-height: 100%;
      width: 100%;
      height: 100%;
      object-fit: contain;
    }}
  </style>
</head>
<body>
  <main
    class="asset-canvas"
    data-output-key="{html.escape(spec.key)}"
    data-width="{spec.width}"
    data-height="{spec.height}"
    data-aspect-ratio="{html.escape(spec.aspect_ratio)}"
    data-format="{html.escape(spec.format)}"
    data-background="{html.escape(spec.background)}"
  >
    <div class="asset-artwork">
      <img alt="" src="data:image/svg+xml;base64,{svg_data}">
    </div>
  </main>
</body>
</html>
"""


def _artwork_box(spec: OutputSpec) -> tuple[int, int]:
    if spec.safe_zone is not None:
        return spec.safe_zone.width, spec.safe_zone.height

    horizontal_padding = round(spec.width * (spec.padding_percent / 100))
    vertical_padding = round(spec.height * (spec.padding_percent / 100))
    return (
        max(1, spec.width - (horizontal_padding * 2)),
        max(1, spec.height - (vertical_padding * 2)),
    )
