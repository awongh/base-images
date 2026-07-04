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
    assert og.wordmark.layout == "inline"

    social_specs = {
        "twitter-image": ((1200, 628), "300:157", (1080, 560)),
        "linkedin-image": ((1200, 627), "400:209", (1080, 585)),
        "social-square": ((1200, 1200), "1:1", (960, 960)),
        "social-portrait": ((1080, 1350), "4:5", (900, 1188)),
        "pinterest-pin": ((1000, 1500), "2:3", (840, 1320)),
        "story-image": ((1080, 1920), "9:16", (864, 1536)),
    }
    for key, (dimensions, aspect_ratio, safe_zone) in social_specs.items():
        spec = config.spec(key)
        assert (spec.width, spec.height) == dimensions
        assert spec.aspect_ratio == aspect_ratio
        assert spec.safe_zone is not None
        assert (spec.safe_zone.width, spec.safe_zone.height) == safe_zone
        assert spec.background == "solid"
        assert spec.format == "jpg"
        assert spec.wordmark.enabled is True

    assert config.spec("favicon-ico").ico_sizes == ((16, 16), (32, 32))
    assert config.spec("icon-48").background == "transparent"
    assert config.spec("icon-192").background == "transparent"
    assert config.spec("apple-touch-icon").padding_percent == 15
    assert config.spec("icon-512").padding_percent == 15
    assert config.wordmark.font_family == "Archivo Black"
    assert config.wordmark.font_weight == 400
    assert config.wordmark.google_fonts is True
    assert config.spec("favicon-svg").wordmark.enabled is False
    assert config.spec("icon-48").wordmark.enabled is False
    assert config.spec("apple-touch-icon").wordmark.enabled is True
    assert config.spec("icon-512").wordmark.enabled is True
    assert config.spec("og-image").wordmark.enabled is True
    assert config.spec("pinterest-pin").wordmark.layout == "poster"
    assert config.spec("pinterest-pin").wordmark.position == "above"
    assert config.spec("pinterest-pin").wordmark.wrap is True


def test_config_overrides_merge_over_defaults() -> None:
    config = resolve_config(
        {
            "wordmark": {
                "font_family": "Inter",
                "font_weight": 700,
                "google_fonts": False,
                "color": "#ff00ff",
            },
            "outputs": {
                "og-image": {
                    "filename": "social.png",
                    "width": 1000,
                    "height": 500,
                    "aspect_ratio": "2:1",
                    "safe_zone": {"width": 800, "height": 400},
                    "format": "png",
                    "wordmark": {
                        "enabled": True,
                        "layout": "poster",
                        "position": "below",
                        "font_size_percent": 9,
                        "max_width_percent": 88,
                        "wrap": True,
                        "line_height": 0.9,
                        "letter_spacing_em": -0.01,
                    },
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
    assert og.wordmark.enabled is True
    assert og.wordmark.layout == "poster"
    assert og.wordmark.position == "below"
    assert og.wordmark.font_size_percent == 9
    assert og.wordmark.max_width_percent == 88
    assert og.wordmark.wrap is True
    assert og.wordmark.line_height == 0.9
    assert og.wordmark.letter_spacing_em == -0.01

    icon = config.spec("icon-512")
    assert icon.filename == "app-icon.png"
    assert (icon.width, icon.height) == (256, 256)
    assert icon.padding_percent == 20
    assert config.wordmark.font_family == "Inter"
    assert config.wordmark.font_weight == 700
    assert config.wordmark.google_fonts is False
    assert config.wordmark.color == "#ff00ff"


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
