"""HTML template helpers used as the rendering source of truth."""

from __future__ import annotations

import base64
import html
import re
import urllib.parse

from base_images.config import (
    GradientCircle,
    GradientColorMix,
    OutputSpec,
    WordmarkStyle,
)


def render_asset_html(
    spec: OutputSpec,
    svg_text: str,
    background_color: str,
    *,
    wordmark_text: str | None = None,
    wordmark_style: WordmarkStyle | None = None,
) -> str:
    """Build the HTML document rendered by the browser screenshot step."""

    base_background = (
        background_color if spec.background == "solid" else "transparent"
    )
    canvas_background = _canvas_background(spec, base_background)
    svg_data = base64.b64encode(svg_text.encode("utf-8")).decode("ascii")
    wordmark_style = wordmark_style or WordmarkStyle()
    show_wordmark = bool(wordmark_text and spec.wordmark.enabled)
    image_width, image_height = _artwork_box(
        spec, include_wordmark=show_wordmark)
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
      background: {html.escape(base_background)};
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
      background: {html.escape(canvas_background)};
    }}

    .asset-artwork {{
      width: {image_width}px;
      height: {image_height}px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }}

    .asset-artwork img {{
      display: block;
      max-width: 100%;
      max-height: 100%;
      width: auto;
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


def _canvas_background(spec: OutputSpec, background: str) -> str:
    if spec.background != "solid" or not spec.background_gradient.enabled:
        return background

    gradient_colors = _derived_gradient_colors(background, spec)
    if gradient_colors is None:
        return background

    highlight, lowlight = gradient_colors
    return (
        f"{_radial_gradient(spec.background_gradient.highlight, highlight)}, "
        f"{_radial_gradient(spec.background_gradient.lowlight, lowlight)}, "
        f"{background}"
    )


def _derived_gradient_colors(
    background: str,
    spec: OutputSpec,
) -> tuple[tuple[int, int, int], tuple[int, int, int]] | None:
    rgb = _parse_hex_color(background)
    if rgb is None:
        return None

    # The two returned colors become the top-left highlight and bottom-right
    # lowlight circles. Luminance lets us pick nearby colors with enough
    # contrast to show texture without drifting away from the chosen background.
    luminance = _relative_luminance(rgb)
    if luminance >= 0.72:
        # Very light backgrounds need darker derived stops; adding white would
        # disappear against the base color.
        return _mix_gradient_colors(
            rgb,
            (0, 0, 0),
            spec.background_gradient.contrast_percent,
            spec.background_gradient.light_mix,
        )
    if luminance <= 0.18:
        # Very dark backgrounds need lifted stops, with the highlight mixed
        # further toward white than the lowlight.
        return _mix_gradient_colors(
            rgb,
            (255, 255, 255),
            spec.background_gradient.contrast_percent,
            spec.background_gradient.dark_mix,
        )

    # Mid-tone backgrounds can support both directions: a lighter circle for
    # the highlight and a darker circle for depth.
    return (
        _mix_rgb(
            rgb,
            (255, 255, 255),
            (spec.background_gradient.mid_mix.highlight_percent / 100)
            * (spec.background_gradient.contrast_percent / 100),
        ),
        _mix_rgb(
            rgb,
            (0, 0, 0),
            (spec.background_gradient.mid_mix.lowlight_percent / 100)
            * (spec.background_gradient.contrast_percent / 100),
        ),
    )


def _parse_hex_color(color: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", color.strip())
    if match is None:
        return None

    value = match.group(1)
    if len(value) == 3:
        value = "".join(channel * 2 for channel in value)

    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
    )


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    linear = [_linearized_srgb(channel / 255) for channel in rgb]
    return (linear[0] * 0.2126) + (linear[1] * 0.7152) + (linear[2] * 0.0722)


def _linearized_srgb(value: float) -> float:
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _mix_rgb(
    rgb: tuple[int, int, int],
    target: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    return tuple(
        round(channel + ((target_channel - channel) * amount))
        for channel, target_channel in zip(rgb, target)
    )


def _mix_gradient_colors(
    rgb: tuple[int, int, int],
    target: tuple[int, int, int],
    contrast_percent: float,
    mix: GradientColorMix,
) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    contrast = contrast_percent / 100
    return (
        _mix_rgb(rgb, target, (mix.highlight_percent / 100) * contrast),
        _mix_rgb(rgb, target, (mix.lowlight_percent / 100) * contrast),
    )


def _radial_gradient(circle: GradientCircle, rgb: tuple[int, int, int]) -> str:
    stops = ", ".join(
        f"{_rgba(rgb, stop.opacity)} {stop.position_percent:g}%"
        for stop in circle.stops
    )
    return (
        f"radial-gradient(circle at {circle.x_percent:g}% {circle.y_percent:g}%, "
        f"{stops})"
    )


def _rgba(rgb: tuple[int, int, int], alpha: float) -> str:
    return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha:g})"


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

    font_size = max(
        1, round(spec.height * (spec.wordmark.font_size_percent / 100)))
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
