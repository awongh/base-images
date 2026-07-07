"""Generate website image assets from SVG source files."""

from base_images.config import (
    DEFAULT_ASSET_CONFIG,
    AssetConfig,
    GradientCircle,
    GradientCircleStop,
    GradientColorMix,
    OutputSpec,
    OutputBackgroundGradient,
    OutputWordmark,
    WordmarkStyle,
    load_config,
    resolve_config,
)
from base_images.generator import AssetGenerator, GeneratedAsset

__all__ = [
    "AssetConfig",
    "AssetGenerator",
    "DEFAULT_ASSET_CONFIG",
    "GeneratedAsset",
    "GradientCircle",
    "GradientCircleStop",
    "GradientColorMix",
    "OutputBackgroundGradient",
    "OutputSpec",
    "OutputWordmark",
    "WordmarkStyle",
    "load_config",
    "resolve_config",
]
