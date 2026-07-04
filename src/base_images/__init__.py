"""Generate website image assets from SVG source files."""

from base_images.config import (
    DEFAULT_ASSET_CONFIG,
    AssetConfig,
    OutputSpec,
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
    "OutputSpec",
    "OutputWordmark",
    "WordmarkStyle",
    "load_config",
    "resolve_config",
]
