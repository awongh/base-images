from base_images import AssetGenerator, resolve_config


def test_rendered_html_contains_canvas_and_safe_zone(tmp_path) -> None:
    svg = tmp_path / "logo.svg"
    svg.write_text("<svg viewBox='0 0 10 10'></svg>", encoding="utf-8")
    generator = AssetGenerator(svg, tmp_path / "assets")
    spec = resolve_config(None).spec("og-image")

    html = generator.render_html(spec)

    assert 'data-output-key="og-image"' in html
    assert 'data-width="1200"' in html
    assert 'data-height="630"' in html
    assert 'data-aspect-ratio="40:21"' in html
    assert "width: 1080px;" in html
    assert "height: 600px;" in html
    assert "background: #ffffff;" in html


def test_padding_controls_artwork_box(tmp_path) -> None:
    svg = tmp_path / "logo.svg"
    svg.write_text("<svg viewBox='0 0 10 10'></svg>", encoding="utf-8")
    generator = AssetGenerator(svg, tmp_path / "assets")
    spec = resolve_config(None).spec("icon-512")

    html = generator.render_html(spec)

    assert "width: 358px;" in html
    assert "height: 358px;" in html
