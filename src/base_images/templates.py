"""HTML template helpers used as the rendering source of truth."""

from __future__ import annotations

import base64
import html
import urllib.parse

from base_images.config import OutputSpec, WordmarkStyle


def render_asset_html(
    spec: OutputSpec,
    svg_text: str,
    background_color: str,
    *,
    wordmark_text: str | None = None,
    wordmark_style: WordmarkStyle | None = None,
) -> str:
    """Build the HTML document rendered by the browser screenshot step."""

    background = (
        background_color if spec.background == "solid" else "transparent"
    )
    svg_data = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
    wordmark_style = wordmark_style or WordmarkStyle()
    show_wordmark = bool(wordmark_text and spec.wordmark.enabled)
    image_width, image_height = _artwork_box(spec, include_wordmark=show_wordmark)
    canvas_classes = _canvas_classes(spec, show_wordmark)
    font_link = _google_font_link(wordmark_style) if show_wordmark else ""
    wordmark_css = _wordmark_css(spec, wordmark_style, show_wordmark)
    wordmark_markup = _wordmark_markup(wordmark_text) if show_wordmark else ""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width={spec.width}, initial-scale=1">
{font_link}
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
      display: flex;
      align-items: center;
      justify-content: center;
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

{wordmark_css}
  </style>
</head>
<body>
  <main
    class="{canvas_classes}"
    data-output-key="{html.escape(spec.key)}"
    data-width="{spec.width}"
    data-height="{spec.height}"
    data-aspect-ratio="{html.escape(spec.aspect_ratio)}"
    data-format="{html.escape(spec.format)}"
    data-background="{html.escape(spec.background)}"
    data-wordmark-layout="{html.escape(spec.wordmark.layout)}"
    data-wordmark-position="{html.escape(spec.wordmark.position)}"
  >
    <div class="asset-artwork">
      <img alt="" src="data:image/svg+xml;base64,{svg_data}">
    </div>
{wordmark_markup}
  </main>
</body>
</html>
"""


def _artwork_box(spec: OutputSpec, *, include_wordmark: bool = False) -> tuple[int, int]:
    if spec.safe_zone is not None:
        width, height = spec.safe_zone.width, spec.safe_zone.height
    else:
        horizontal_padding = round(spec.width * (spec.padding_percent / 100))
        vertical_padding = round(spec.height * (spec.padding_percent / 100))
        width = max(1, spec.width - (horizontal_padding * 2))
        height = max(1, spec.height - (vertical_padding * 2))

    if not include_wordmark:
        return width, height

    artwork_fraction = spec.wordmark.artwork_area_percent / 100
    if spec.wordmark.position in {"left", "right"}:
        return max(1, round(width * artwork_fraction)), height

    return (
        width,
        max(1, round(height * artwork_fraction)),
    )


def _canvas_classes(spec: OutputSpec, show_wordmark: bool) -> str:
    classes = ["asset-canvas"]
    if show_wordmark:
        classes.extend(
            [
                "asset-has-wordmark",
                f"asset-layout-{spec.wordmark.layout}",
                f"asset-position-{spec.wordmark.position}",
            ]
        )
    return html.escape(" ".join(classes))


def _google_font_link(style: WordmarkStyle) -> str:
    if not style.google_fonts:
        return ""

    family = urllib.parse.quote_plus(style.font_family)
    return (
        "  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n"
        "  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>\n"
        "  <link "
        f"href=\"https://fonts.googleapis.com/css2?family={family}:wght@{style.font_weight}&display=swap\" "
        "rel=\"stylesheet\">"
    )


def _wordmark_css(
    spec: OutputSpec,
    style: WordmarkStyle,
    show_wordmark: bool,
) -> str:
    if not show_wordmark:
        return ""

    font_size = max(1, round(spec.height * (spec.wordmark.font_size_percent / 100)))
    gap = max(0, round(spec.width * (spec.wordmark.gap_percent / 100)))
    flex_direction = _flex_direction(spec)
    default_max_width_percent = (
        45 if spec.wordmark.position in {"left", "right"} else 90
    )
    max_width_percent = spec.wordmark.max_width_percent or default_max_width_percent
    max_width = max(1, round(spec.width * (max_width_percent / 100)))
    white_space = "normal" if spec.wordmark.wrap else "nowrap"
    text_wrap = "\n      text-wrap: balance;" if spec.wordmark.wrap else ""
    overflow_wrap = "\n      overflow-wrap: anywhere;" if spec.wordmark.wrap else ""
    text_overflow = "clip" if spec.wordmark.wrap else "ellipsis"

    return f"""    .asset-canvas.asset-has-wordmark {{
      flex-direction: {flex_direction};
      gap: {gap}px;
    }}

    .asset-wordmark {{
      max-width: {max_width}px;
      color: {html.escape(style.color)};
      font-family: "{html.escape(style.font_family)}", sans-serif;
      font-size: {font_size}px;
      font-weight: {style.font_weight};
      line-height: {spec.wordmark.line_height};
      letter-spacing: {spec.wordmark.letter_spacing_em}em;
      overflow: hidden;
      text-align: center;
      text-overflow: {text_overflow};{text_wrap}{overflow_wrap}
      white-space: {white_space};
    }}"""


def _flex_direction(spec: OutputSpec) -> str:
    if spec.wordmark.position == "left":
        return "row-reverse"
    if spec.wordmark.position == "right":
        return "row"
    if spec.wordmark.position == "above":
        return "column-reverse"
    return "column"


def _wordmark_markup(wordmark_text: str | None) -> str:
    if not wordmark_text:
        return ""
    return f'    <div class="asset-wordmark">{html.escape(wordmark_text)}</div>'
