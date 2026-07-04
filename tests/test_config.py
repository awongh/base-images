import json

import pytest

from base_images import DEFAULT_ASSET_CONFIG, AssetGenerator, resolve_config
from base_images.config import ConfigError, DEFAULT_CONFIG_PATH


def test_default_config_file_matches_exported_dict() -> None:
    with DEFAULT_CONFIG_PATH.open(encoding="utf-8") as config_file:
        file_config = json.load(config_file)

    assert file_config == DEFAULT_ASSET_CONFIG


def test_default_specs_match_readme_layouts() -> None:
    config = resolve_config(None)

    og = config.spec("og-image")
    assert (og.width, og.height) == (1200, 630)
    assert og.aspect_ratio == "40:21"
    assert og.safe_zone is not None
    assert (og.safe_zone.width, og.safe_zone.height) == (1080, 600)
    assert og.background == "solid"
    assert og.format == "jpg"
    assert og.max_bytes == 500000

    assert config.spec("favicon-ico").ico_sizes == ((16, 16), (32, 32))
    assert config.spec("icon-48").background == "transparent"
    assert config.spec("icon-192").background == "transparent"
    assert config.spec("apple-touch-icon").padding_percent == 15
    assert config.spec("icon-512").padding_percent == 15


def test_config_overrides_merge_over_defaults() -> None:
    config = resolve_config(
        {
            "outputs": {
                "og-image": {
                    "filename": "social.png",
                    "width": 1000,
                    "height": 500,
                    "aspect_ratio": "2:1",
                    "safe_zone": {"width": 800, "height": 400},
                    "format": "png",
                },
                "icon-512": {
                    "filename": "app-icon.png",
                    "width": 256,
                    "height": 256,
                    "aspect_ratio": "1:1",
                    "padding_percent": 20,
                },
            }
        }
    )

    og = config.spec("og-image")
    assert og.filename == "social.png"
    assert (og.width, og.height) == (1000, 500)
    assert og.aspect_ratio == "2:1"
    assert og.format == "png"
    assert og.safe_zone is not None
    assert (og.safe_zone.width, og.safe_zone.height) == (800, 400)

    icon = config.spec("icon-512")
    assert icon.filename == "app-icon.png"
    assert (icon.width, icon.height) == (256, 256)
    assert icon.padding_percent == 20


def test_invalid_ratio_raises_clear_error() -> None:
    with pytest.raises(ConfigError, match="aspect_ratio"):
        resolve_config(
            {
                "outputs": {
                    "icon-512": {
                        "width": 512,
                        "height": 256,
                        "aspect_ratio": "1:1",
                    }
                }
            }
        )


def test_tier_specific_svgs_fall_back_to_base(tmp_path) -> None:
    base = tmp_path / "base.svg"
    search = tmp_path / "search.svg"
    base.write_text("<svg><title>base</title></svg>", encoding="utf-8")
    search.write_text("<svg><title>search</title></svg>", encoding="utf-8")

    generator = AssetGenerator(base, tmp_path / "assets", search_svg=search)

    assert generator.svg_for_tier("micro") == base
    assert generator.svg_for_tier("search") == search
    assert generator.svg_for_tier("macro") == base
    assert generator.svg_for_tier("social") == base
