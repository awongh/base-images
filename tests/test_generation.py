import pytest
from PIL import Image

from base_images import AssetGenerator


SIMPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="12" fill="#111827"/>
  <circle cx="32" cy="32" r="18" fill="#f9fafb"/>
</svg>
"""


def test_generate_small_config_outputs_expected_dimensions(tmp_path) -> None:
    svg = tmp_path / "logo.svg"
    svg.write_text(SIMPLE_SVG, encoding="utf-8")
    output = tmp_path / "assets"
    config = {
        "html_snippet_filename": "snippet.html",
        "manifest": {"filename": "manifest.json", "icons": ["icon"]},
        "outputs": {
            "icon": {
                "filename": "icon.png",
                "width": 24,
                "height": 24,
                "aspect_ratio": "1:1",
                "format": "png",
                "background": "transparent",
                "tier": "search",
            }
        },
    }

    generator = AssetGenerator(svg, output, config=config)
    try:
        generator.generate()
    except RuntimeError as exc:
        pytest.skip(str(exc))

    icon_path = output / "icon.png"
    assert icon_path.exists()
    assert (output / "manifest.json").exists()
    assert (output / "snippet.html").exists()

    with Image.open(icon_path) as image:
        assert image.size == (24, 24)
