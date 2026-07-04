"""Configuration models and defaults for asset generation."""

from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping, MutableMapping

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / "configs" / "default-assets.json"

ImageFormat = Literal["svg", "ico", "png", "jpg", "jpeg"]
BackgroundMode = Literal["transparent", "solid"]
SvgTier = Literal["micro", "search", "macro", "social"]


class ConfigError(ValueError):
    """Raised when an asset configuration is invalid."""


def _load_default_config() -> dict[str, Any]:
    with DEFAULT_CONFIG_PATH.open(encoding="utf-8") as config_file:
        return json.load(config_file)


DEFAULT_ASSET_CONFIG: dict[str, Any] = _load_default_config()


@dataclass(frozen=True)
class SafeZone:
    """The centered area that should contain critical visual details."""

    width: int
    height: int


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

    @classmethod
    def from_mapping(cls, key: str, values: Mapping[str, Any]) -> "OutputSpec":
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

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "AssetConfig":
        outputs = values.get("outputs")
        if not isinstance(outputs, Mapping) or not outputs:
            raise ConfigError("config must include a non-empty outputs mapping")

        specs = tuple(
            OutputSpec.from_mapping(key, output_values)
            for key, output_values in outputs.items()
        )

        manifest = values.get("manifest", {})
        if manifest is None:
            manifest = {}
        if not isinstance(manifest, Mapping):
            raise ConfigError("manifest must be an object when provided")

        return cls(
            version=int(values.get("version", 1)),
            background=str(values.get("background", "#ffffff")),
            outputs=specs,
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


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a JSON config file."""

    with Path(path).open(encoding="utf-8") as config_file:
        return json.load(config_file)


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
