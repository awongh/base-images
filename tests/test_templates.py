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


def test_macro_and_social_outputs_use_derived_circle_gradients(tmp_path) -> None:
    svg = tmp_path / "logo.svg"
    svg.write_text("<svg viewBox='0 0 10 10'></svg>", encoding="utf-8")
    generator = AssetGenerator(svg, tmp_path / "assets")
    config = resolve_config(None)

    macro_html = generator.render_html(config.spec("icon-512"))
    social_html = generator.render_html(config.spec("og-image"))

    assert "radial-gradient(circle at 18% 20%" in macro_html
    assert "radial-gradient(circle at 82% 78%" in macro_html
    assert "rgba(240, 240, 240, 0.88)" in macro_html
    assert "rgba(219, 219, 219, 0.54)" in macro_html
    assert "radial-gradient(circle at 18% 20%" in social_html
    assert "radial-gradient(circle at 82% 78%" in social_html


def test_dark_background_gradient_colors_are_lifted_from_background(tmp_path) -> None:
    svg = tmp_path / "logo.svg"
    svg.write_text("<svg viewBox='0 0 10 10'></svg>", encoding="utf-8")
    generator = AssetGenerator(svg, tmp_path / "assets", background="#111827")
    spec = resolve_config(None).spec("og-image")

    html = generator.render_html(spec)

    assert "rgba(69, 75, 87, 0.88)" in html
    assert "rgba(41, 47, 61, 0.54)" in html
    assert "#111827" in html


def test_gradients_skip_transparent_and_non_hex_backgrounds(tmp_path) -> None:
    svg = tmp_path / "logo.svg"
    svg.write_text("<svg viewBox='0 0 10 10'></svg>", encoding="utf-8")
    config = resolve_config(None)

    transparent_html = AssetGenerator(svg, tmp_path / "assets").render_html(
        config.spec("icon-48")
    )
    named_color_html = AssetGenerator(
        svg,
        tmp_path / "named-assets",
        background="white",
    ).render_html(config.spec("icon-512"))

    assert "radial-gradient" not in transparent_html
    assert "radial-gradient" not in named_color_html
    assert "background: transparent;" in transparent_html
    assert "background: white;" in named_color_html


def test_wordmark_renders_for_enabled_macro_and_social_outputs(tmp_path) -> None:
    svg = tmp_path / "logo.svg"
    svg.write_text("<svg viewBox='0 0 10 10'></svg>", encoding="utf-8")
    generator = AssetGenerator(svg, tmp_path / "assets", wordmark="Stack")
    spec = resolve_config(None).spec("og-image")

    html = generator.render_html(spec)

    assert "fonts.googleapis.com" in html
    assert "family=Archivo+Black:wght@400" in html
    assert 'font-family: "Archivo Black", sans-serif;' in html
    assert "font-weight: 400;" in html
    assert '<div class="asset-wordmark">Stack</div>' in html
    assert 'class="asset-canvas asset-has-wordmark asset-layout-inline asset-position-right"' in html
    assert 'data-wordmark-layout="inline"' in html
    assert 'data-wordmark-position="right"' in html
    assert "flex-direction: row;" in html


def test_stacked_wordmark_uses_square_social_layout(tmp_path) -> None:
    svg = tmp_path / "logo.svg"
    svg.write_text("<svg viewBox='0 0 10 10'></svg>", encoding="utf-8")
    generator = AssetGenerator(svg, tmp_path / "assets", wordmark="Stack")
    spec = resolve_config(None).spec("social-square")

    html = generator.render_html(spec)

    assert 'class="asset-canvas asset-has-wordmark asset-layout-stacked asset-position-below"' in html
    assert "flex-direction: column;" in html
    assert "width: 960px;" in html
    assert "height: 595px;" in html
    assert "max-width: 960px;" in html
    assert "white-space: nowrap;" in html


def test_poster_wordmark_wraps_for_vertical_social_outputs(tmp_path) -> None:
    svg = tmp_path / "logo.svg"
    svg.write_text("<svg viewBox='0 0 10 10'></svg>", encoding="utf-8")
    generator = AssetGenerator(svg, tmp_path / "assets", wordmark="Stack Images")
    spec = resolve_config(None).spec("pinterest-pin")

    html = generator.render_html(spec)

    assert 'class="asset-canvas asset-has-wordmark asset-layout-poster asset-position-above"' in html
    assert 'data-wordmark-layout="poster"' in html
    assert 'data-wordmark-position="above"' in html
    assert "flex-direction: column-reverse;" in html
    assert "width: 840px;" in html
    assert "height: 766px;" in html
    assert "max-width: 840px;" in html
    assert "line-height: 0.95;" in html
    assert "text-wrap: balance;" in html
    assert "overflow-wrap: anywhere;" in html
    assert "white-space: normal;" in html


def test_wordmark_is_not_rendered_for_disabled_outputs(tmp_path) -> None:
    svg = tmp_path / "logo.svg"
    svg.write_text("<svg viewBox='0 0 10 10'></svg>", encoding="utf-8")
    generator = AssetGenerator(svg, tmp_path / "assets", wordmark="Stack")
    spec = resolve_config(None).spec("icon-48")

    html = generator.render_html(spec)

    assert "asset-wordmark" not in html
    assert "fonts.googleapis.com" not in html
