"""Configuration models and defaults for asset generation."""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping, MutableMapping

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "configs" / "default-assets.jsonc"

ImageFormat = Literal["svg", "ico", "png", "jpg", "jpeg"]
BackgroundMode = Literal["transparent", "solid"]
SvgTier = Literal["micro", "search", "macro", "social"]
WordmarkPosition = Literal["above", "below", "left", "right"]
WordmarkLayout = Literal["inline", "stacked", "poster"]


class ConfigError(ValueError):
    """Raised when an asset configuration is invalid."""


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a JSON or JSONC config file."""

    config_text = Path(path).read_text(encoding="utf-8")
    return json.loads(_strip_json_comments(config_text))


def _strip_json_comments(value: str) -> str:
    """Remove JSONC comments without touching comment markers inside strings."""

    result: list[str] = []
    in_string = False
    is_escaped = False
    index = 0

    while index < len(value):
        char = value[index]
        next_char = value[index + 1] if index + 1 < len(value) else ""

        if in_string:
            result.append(char)
            if is_escaped:
                is_escaped = False
            elif char == "\\":
                is_escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            result.append(char)
            index += 1
            continue

        if char == "/" and next_char == "/":
            index += 2
            while index < len(value) and value[index] not in "\r\n":
                index += 1
            continue

        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(value) and value[index : index + 2] != "*/":
                result.append("\n" if value[index] in "\r\n" else " ")
                index += 1
            index += 2
            continue

        result.append(char)
        index += 1

    return "".join(result)


def _load_default_config() -> dict[str, Any]:
    return load_config(DEFAULT_CONFIG_PATH)


DEFAULT_ASSET_CONFIG: dict[str, Any] = _load_default_config()


@dataclass(frozen=True)
class SafeZone:
    """The centered area that should contain critical visual details."""

    width: int
    height: int


@dataclass(frozen=True)
class WordmarkStyle:
    """Global wordmark typography settings."""

    font_family: str = "Archivo Black"
    font_weight: int = 400
    google_fonts: bool = True
    color: str = "#ffffff"

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any] | None) -> "WordmarkStyle":
        if values is None:
            values = {}
        if not isinstance(values, Mapping):
            raise ConfigError("wordmark must be an object when provided")

        font_weight = int(values.get("font_weight", 400))
        if font_weight <= 0:
            raise ConfigError("wordmark.font_weight must be positive")

        return cls(
            font_family=str(values.get("font_family", "Archivo Black")),
            font_weight=font_weight,
            google_fonts=bool(values.get("google_fonts", True)),
            color=str(values.get("color", "#ffffff")),
        )


@dataclass(frozen=True)
class OutputWordmark:
    """Per-output wordmark layout settings."""

    enabled: bool = False
    layout: WordmarkLayout = "stacked"
    position: WordmarkPosition = "below"
    font_size_percent: float = 11
    gap_percent: float = 4
    artwork_area_percent: float = 68
    max_width_percent: float | None = None
    wrap: bool = False
    line_height: float = 1
    letter_spacing_em: float = -0.03

    @classmethod
    def from_mapping(cls, key: str, value: Any) -> "OutputWordmark":
        if value in (None, {}):
            return cls()
        if not isinstance(value, Mapping):
            raise ConfigError(f"{key}: wordmark must be an object")

        position = str(value.get("position", "below")).lower()
        if position not in {"above", "below", "left", "right"}:
            raise ConfigError(
                f"{key}: wordmark.position must be above, below, left, or right"
            )

        layout = str(value.get("layout") or _default_wordmark_layout(position)).lower()
        if layout not in {"inline", "stacked", "poster"}:
            raise ConfigError(
                f"{key}: wordmark.layout must be inline, stacked, or poster"
            )

        font_size_percent = float(value.get("font_size_percent", 11))
        gap_percent = float(value.get("gap_percent", 4))
        artwork_area_percent = float(value.get("artwork_area_percent", 68))
        max_width_percent_value = value.get("max_width_percent")
        max_width_percent = (
            None
            if max_width_percent_value is None
            else float(max_width_percent_value)
        )
        wrap = bool(value.get("wrap", layout == "poster"))
        line_height = float(value.get("line_height", 0.95 if layout == "poster" else 1))
        letter_spacing_em = float(value.get("letter_spacing_em", -0.03))

        if not 0 < font_size_percent < 50:
            raise ConfigError(f"{key}: wordmark.font_size_percent must be between 0 and 50")
        if gap_percent < 0 or gap_percent >= 50:
            raise ConfigError(f"{key}: wordmark.gap_percent must be between 0 and 50")
        if not 0 < artwork_area_percent <= 100:
            raise ConfigError(
                f"{key}: wordmark.artwork_area_percent must be between 0 and 100"
            )
        if max_width_percent is not None and not 0 < max_width_percent <= 100:
            raise ConfigError(
                f"{key}: wordmark.max_width_percent must be between 0 and 100"
            )
        if not 0 < line_height <= 2:
            raise ConfigError(f"{key}: wordmark.line_height must be between 0 and 2")
        if not -0.5 <= letter_spacing_em <= 0.5:
            raise ConfigError(
                f"{key}: wordmark.letter_spacing_em must be between -0.5 and 0.5"
            )

        return cls(
            enabled=bool(value.get("enabled", False)),
            layout=layout,  # type: ignore[arg-type]
            position=position,  # type: ignore[arg-type]
            font_size_percent=font_size_percent,
            gap_percent=gap_percent,
            artwork_area_percent=artwork_area_percent,
            max_width_percent=max_width_percent,
            wrap=wrap,
            line_height=line_height,
            letter_spacing_em=letter_spacing_em,
        )


@dataclass(frozen=True)
class GradientCircleStop:
    """One opacity stop inside a derived radial gradient circle."""

    opacity: float
    position_percent: float

    @classmethod
    def from_mapping(
        cls,
        key: str,
        value: Any,
        *,
        circle_name: str,
        stop_index: int,
    ) -> "GradientCircleStop":
        if not isinstance(value, Mapping):
            raise ConfigError(
                f"{key}: background_gradient.{circle_name}.stops[{stop_index}] must be an object"
            )

        opacity = float(value.get("opacity", 0))
        position_percent = float(value.get("position_percent", 0))
        if not 0 <= opacity <= 1:
            raise ConfigError(
                f"{key}: background_gradient.{circle_name}.stops[{stop_index}].opacity "
                "must be between 0 and 1"
            )
        if not 0 <= position_percent <= 100:
            raise ConfigError(
                f"{key}: background_gradient.{circle_name}.stops[{stop_index}]."
                "position_percent must be between 0 and 100"
            )

        return cls(opacity=opacity, position_percent=position_percent)


@dataclass(frozen=True)
class GradientCircle:
    """One radial gradient circle layered over the base background."""

    x_percent: float
    y_percent: float
    stops: tuple[GradientCircleStop, ...]

    @classmethod
    def from_mapping(
        cls,
        key: str,
        value: Any,
        *,
        circle_name: str,
        default: "GradientCircle | None" = None,
    ) -> "GradientCircle":
        if value in (None, {}):
            if default is not None:
                return default
            value = {}
        if not isinstance(value, Mapping):
            raise ConfigError(f"{key}: background_gradient.{circle_name} must be an object")

        x_percent = float(value.get("x_percent", default.x_percent if default else 50))
        y_percent = float(value.get("y_percent", default.y_percent if default else 50))
        if not 0 <= x_percent <= 100:
            raise ConfigError(
                f"{key}: background_gradient.{circle_name}.x_percent must be between 0 and 100"
            )
        if not 0 <= y_percent <= 100:
            raise ConfigError(
                f"{key}: background_gradient.{circle_name}.y_percent must be between 0 and 100"
            )

        stop_values = value.get("stops")
        if stop_values is None and default is not None:
            stops = default.stops
        elif not isinstance(stop_values, list) or not stop_values:
            raise ConfigError(
                f"{key}: background_gradient.{circle_name}.stops must be a non-empty list"
            )
        else:
            stops = tuple(
                GradientCircleStop.from_mapping(
                    key,
                    stop_value,
                    circle_name=circle_name,
                    stop_index=index,
                )
                for index, stop_value in enumerate(stop_values)
            )
        positions = [stop.position_percent for stop in stops]
        if positions != sorted(positions):
            raise ConfigError(
                f"{key}: background_gradient.{circle_name}.stops must be sorted by "
                "position_percent"
            )

        return cls(x_percent=x_percent, y_percent=y_percent, stops=stops)


@dataclass(frozen=True)
class GradientColorMix:
    """How far derived gradient colors move away from the base background."""

    highlight_percent: float
    lowlight_percent: float

    @classmethod
    def from_mapping(
        cls,
        key: str,
        value: Any,
        *,
        mix_name: str,
        default: "GradientColorMix | None" = None,
    ) -> "GradientColorMix":
        if value in (None, {}):
            if default is not None:
                return default
            value = {}
        if not isinstance(value, Mapping):
            raise ConfigError(f"{key}: background_gradient.color_mix.{mix_name} must be an object")

        highlight_percent = float(
            value.get(
                "highlight_percent",
                default.highlight_percent if default else 0,
            )
        )
        lowlight_percent = float(
            value.get(
                "lowlight_percent",
                default.lowlight_percent if default else 0,
            )
        )
        for field_name, field_value in (
            ("highlight_percent", highlight_percent),
            ("lowlight_percent", lowlight_percent),
        ):
            if not 0 <= field_value <= 100:
                raise ConfigError(
                    f"{key}: background_gradient.color_mix.{mix_name}.{field_name} "
                    "must be between 0 and 100"
                )

        return cls(
            highlight_percent=highlight_percent,
            lowlight_percent=lowlight_percent,
        )


@dataclass(frozen=True)
class OutputBackgroundGradient:
    """Per-output radial background texture settings."""

    enabled: bool = False
    contrast_percent: float = 100
    highlight: GradientCircle = GradientCircle(
        x_percent=18,
        y_percent=20,
        stops=(
            GradientCircleStop(opacity=0.92, position_percent=0),
            GradientCircleStop(opacity=0.42, position_percent=20),
            GradientCircleStop(opacity=0, position_percent=38),
        ),
    )
    lowlight: GradientCircle = GradientCircle(
        x_percent=82,
        y_percent=78,
        stops=(
            GradientCircleStop(opacity=0.68, position_percent=0),
            GradientCircleStop(opacity=0.30, position_percent=24),
            GradientCircleStop(opacity=0, position_percent=44),
        ),
    )
    light_mix: GradientColorMix = GradientColorMix(
        highlight_percent=30,
        lowlight_percent=50,
    )
    dark_mix: GradientColorMix = GradientColorMix(
        highlight_percent=48,
        lowlight_percent=30,
    )
    mid_mix: GradientColorMix = GradientColorMix(
        highlight_percent=36,
        lowlight_percent=30,
    )

    @classmethod
    def from_mapping(
        cls,
        key: str,
        value: Any,
        *,
        default: "OutputBackgroundGradient | None" = None,
    ) -> "OutputBackgroundGradient":
        default = default or cls()
        if value is None:
            return default
        if not isinstance(value, Mapping):
            raise ConfigError(f"{key}: background_gradient must be an object")

        contrast_percent = float(
            value.get("contrast_percent", default.contrast_percent)
        )
        if contrast_percent < 0:
            raise ConfigError(
                f"{key}: background_gradient.contrast_percent must be non-negative"
            )

        color_mix = value.get("color_mix", {})
        if not isinstance(color_mix, Mapping):
            raise ConfigError(f"{key}: background_gradient.color_mix must be an object")

        return cls(
            enabled=bool(value.get("enabled", default.enabled)),
            contrast_percent=contrast_percent,
            highlight=GradientCircle.from_mapping(
                key,
                value.get("highlight"),
                circle_name="highlight",
                default=default.highlight,
            ),
            lowlight=GradientCircle.from_mapping(
                key,
                value.get("lowlight"),
                circle_name="lowlight",
                default=default.lowlight,
            ),
            light_mix=GradientColorMix.from_mapping(
                key,
                color_mix.get("light"),
                mix_name="light",
                default=default.light_mix,
            ),
            dark_mix=GradientColorMix.from_mapping(
                key,
                color_mix.get("dark"),
                mix_name="dark",
                default=default.dark_mix,
            ),
            mid_mix=GradientColorMix.from_mapping(
                key,
                color_mix.get("mid"),
                mix_name="mid",
                default=default.mid_mix,
            ),
        )


@dataclass(frozen=True)
class OutputSpec:
    """One output file's layout and rendering settings."""

    key: str
    filename: str
    width: int
    height: int
    aspect_ratio: str
    format: ImageFormat
    background: BackgroundMode
    tier: SvgTier
    padding_percent: float = 0
    safe_zone: SafeZone | None = None
    ico_sizes: tuple[tuple[int, int], ...] = ()
    quality: int = 92
    min_quality: int = 60
    max_bytes: int | None = None
    wordmark: OutputWordmark = OutputWordmark()
    background_gradient: OutputBackgroundGradient = OutputBackgroundGradient()

    @classmethod
    def from_mapping(
        cls,
        key: str,
        values: Mapping[str, Any],
        *,
        background_gradient_defaults: Mapping[SvgTier, OutputBackgroundGradient] | None = None,
    ) -> "OutputSpec":
        width = _positive_int(values, "width", output_key=key)
        height = _positive_int(values, "height", output_key=key)
        aspect_ratio = str(values.get("aspect_ratio") or _ratio_string(width, height))
        _validate_aspect_ratio(key, width, height, aspect_ratio)

        image_format = str(values.get("format", "")).lower()
        if image_format not in {"svg", "ico", "png", "jpg", "jpeg"}:
            raise ConfigError(f"{key}: unsupported format {image_format!r}")

        background = str(values.get("background", "")).lower()
        if background not in {"transparent", "solid"}:
            raise ConfigError(f"{key}: background must be 'transparent' or 'solid'")

        tier = str(values.get("tier", "")).lower()
        if tier not in {"micro", "search", "macro", "social"}:
            raise ConfigError(f"{key}: tier must be micro, search, macro, or social")

        padding_percent = float(values.get("padding_percent", 0))
        if padding_percent < 0 or padding_percent >= 50:
            raise ConfigError(f"{key}: padding_percent must be between 0 and 50")

        safe_zone = _safe_zone_from_mapping(key, values.get("safe_zone"), width, height)
        ico_sizes = _ico_sizes_from_mapping(key, values.get("ico_sizes", ()))
        wordmark = OutputWordmark.from_mapping(key, values.get("wordmark"))
        default_gradient = (
            background_gradient_defaults.get(tier, OutputBackgroundGradient())
            if background_gradient_defaults
            else OutputBackgroundGradient()
        )
        background_gradient = OutputBackgroundGradient.from_mapping(
            key,
            values.get("background_gradient"),
            default=default_gradient,
        )

        quality = int(values.get("quality", 92))
        min_quality = int(values.get("min_quality", 60))
        if not 1 <= min_quality <= quality <= 100:
            raise ConfigError(f"{key}: expected 1 <= min_quality <= quality <= 100")

        max_bytes = values.get("max_bytes")
        if max_bytes is not None:
            max_bytes = int(max_bytes)
            if max_bytes <= 0:
                raise ConfigError(f"{key}: max_bytes must be positive")

        return cls(
            key=key,
            filename=str(values["filename"]),
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            format=image_format,  # type: ignore[arg-type]
            background=background,  # type: ignore[arg-type]
            tier=tier,  # type: ignore[arg-type]
            padding_percent=padding_percent,
            safe_zone=safe_zone,
            ico_sizes=ico_sizes,
            quality=quality,
            min_quality=min_quality,
            max_bytes=max_bytes,
            wordmark=wordmark,
            background_gradient=background_gradient,
        )


@dataclass(frozen=True)
class AssetConfig:
    """Validated generator configuration."""

    version: int
    background: str
    outputs: tuple[OutputSpec, ...]
    html_snippet_filename: str = "html-snippet.html"
    manifest_filename: str = "manifest.json"
    manifest_icon_keys: tuple[str, ...] = ("icon-192", "icon-512")
    wordmark: WordmarkStyle = WordmarkStyle()
    background_gradients: Mapping[SvgTier, OutputBackgroundGradient] | None = None

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "AssetConfig":
        outputs = values.get("outputs")
        if not isinstance(outputs, Mapping) or not outputs:
            raise ConfigError("config must include a non-empty outputs mapping")

        background_gradients = _background_gradients_from_mapping(
            values.get("background_gradients")
        )
        specs = tuple(
            OutputSpec.from_mapping(
                key,
                output_values,
                background_gradient_defaults=background_gradients,
            )
            for key, output_values in outputs.items()
        )

        manifest = values.get("manifest", {})
        if manifest is None:
            manifest = {}
        if not isinstance(manifest, Mapping):
            raise ConfigError("manifest must be an object when provided")

        return cls(
            version=int(values.get("version", 1)),
            background=str(values.get("background", "#8E8E93")),
            outputs=specs,
            wordmark=WordmarkStyle.from_mapping(values.get("wordmark")),
            background_gradients=background_gradients,
            html_snippet_filename=str(
                values.get("html_snippet_filename", "html-snippet.html")
            ),
            manifest_filename=str(manifest.get("filename", "manifest.json")),
            manifest_icon_keys=tuple(manifest.get("icons", ("icon-192", "icon-512"))),
        )

    def spec(self, key: str) -> OutputSpec:
        for output in self.outputs:
            if output.key == key:
                return output
        raise KeyError(key)


def resolve_config(config: AssetConfig | Mapping[str, Any] | str | Path | None) -> AssetConfig:
    """Merge an optional config override onto the default and validate it."""

    if isinstance(config, AssetConfig):
        return config

    merged = copy.deepcopy(DEFAULT_ASSET_CONFIG)
    if config is not None:
        overrides = load_config(config) if isinstance(config, (str, Path)) else dict(config)
        _deep_merge(merged, overrides)
    return AssetConfig.from_mapping(merged)


def _deep_merge(target: MutableMapping[str, Any], overrides: Mapping[str, Any]) -> None:
    for key, value in overrides.items():
        if (
            key in target
            and isinstance(target[key], MutableMapping)
            and isinstance(value, Mapping)
        ):
            _deep_merge(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


def _positive_int(values: Mapping[str, Any], name: str, *, output_key: str) -> int:
    try:
        value = int(values[name])
    except KeyError as exc:
        raise ConfigError(f"{output_key}: missing required field {name!r}") from exc
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{output_key}: {name} must be an integer") from exc

    if value <= 0:
        raise ConfigError(f"{output_key}: {name} must be positive")
    return value


def _ratio_string(width: int, height: int) -> str:
    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def _default_wordmark_layout(position: str) -> WordmarkLayout:
    return "inline" if position in {"left", "right"} else "stacked"


def _background_gradients_from_mapping(
    value: Any,
) -> dict[SvgTier, OutputBackgroundGradient]:
    if value in (None, {}):
        return {}
    if not isinstance(value, Mapping):
        raise ConfigError("background_gradients must be an object when provided")

    gradients: dict[SvgTier, OutputBackgroundGradient] = {}
    for tier, gradient_values in value.items():
        tier_name = str(tier).lower()
        if tier_name not in {"macro", "social"}:
            raise ConfigError("background_gradients keys must be macro or social")
        gradients[tier_name] = OutputBackgroundGradient.from_mapping(
            f"background_gradients.{tier_name}",
            gradient_values,
        )
    return gradients


def _parse_ratio(value: str) -> tuple[int, int]:
    parts = value.split(":", maxsplit=1)
    if len(parts) != 2:
        raise ValueError("ratio must use W:H format")
    left = int(parts[0])
    right = int(parts[1])
    if left <= 0 or right <= 0:
        raise ValueError("ratio values must be positive")
    return left, right


def _validate_aspect_ratio(key: str, width: int, height: int, aspect_ratio: str) -> None:
    try:
        ratio_width, ratio_height = _parse_ratio(aspect_ratio)
    except ValueError as exc:
        raise ConfigError(f"{key}: invalid aspect_ratio {aspect_ratio!r}") from exc

    if width * ratio_height != height * ratio_width:
        expected = _ratio_string(width, height)
        raise ConfigError(
            f"{key}: aspect_ratio {aspect_ratio!r} does not match "
            f"{width}x{height}; expected {expected!r}"
        )


def _safe_zone_from_mapping(
    key: str,
    value: Any,
    output_width: int,
    output_height: int,
) -> SafeZone | None:
    if value in (None, {}):
        return None
    if not isinstance(value, Mapping):
        raise ConfigError(f"{key}: safe_zone must be an object")

    width = _positive_int(value, "width", output_key=key)
    height = _positive_int(value, "height", output_key=key)
    if width > output_width or height > output_height:
        raise ConfigError(f"{key}: safe_zone cannot exceed output dimensions")
    return SafeZone(width=width, height=height)


def _ico_sizes_from_mapping(key: str, value: Any) -> tuple[tuple[int, int], ...]:
    if value in (None, ()):
        return ()
    if not isinstance(value, list):
        raise ConfigError(f"{key}: ico_sizes must be a list")

    sizes: list[tuple[int, int]] = []
    for item in value:
        if not isinstance(item, list | tuple) or len(item) != 2:
            raise ConfigError(f"{key}: ico_sizes entries must be [width, height]")
        width, height = int(item[0]), int(item[1])
        if width <= 0 or height <= 0:
            raise ConfigError(f"{key}: ico_sizes entries must be positive")
        sizes.append((width, height))
    return tuple(sizes)
