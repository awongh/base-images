import threading
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from base_images import AssetGenerator
from base_images.debug_server import make_debug_server


def test_render_html_for_key_uses_configured_output(tmp_path) -> None:
    svg = tmp_path / "logo.svg"
    svg.write_text("<svg viewBox='0 0 10 10'></svg>", encoding="utf-8")
    generator = AssetGenerator(svg, tmp_path / "assets")

    html = generator.render_html_for_key("icon-512")

    assert 'data-output-key="icon-512"' in html
    assert 'data-width="512"' in html
    assert 'data-height="512"' in html


def test_debug_server_serves_default_output_and_index(tmp_path) -> None:
    svg = tmp_path / "logo.svg"
    svg.write_text("<svg viewBox='0 0 10 10'></svg>", encoding="utf-8")
    generator = AssetGenerator(svg, tmp_path / "assets")
    server = make_debug_server(generator, output_key="icon-512", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        base_url = _server_url(server)
        with urlopen(base_url, timeout=5) as response:
            body = response.read().decode("utf-8")
        with urlopen(f"{base_url}outputs", timeout=5) as response:
            index_body = response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert 'data-output-key="icon-512"' in body
    assert "Open an output to inspect the exact HTML" in index_body
    assert '<a href="/og-image.html">og-image</a>' in index_body
    assert '<a href="/">icon-512</a>' in index_body


def test_debug_server_returns_404_for_unknown_output(tmp_path) -> None:
    svg = tmp_path / "logo.svg"
    svg.write_text("<svg viewBox='0 0 10 10'></svg>", encoding="utf-8")
    generator = AssetGenerator(svg, tmp_path / "assets")
    server = make_debug_server(generator, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with pytest.raises(HTTPError) as exc_info:
            urlopen(f"{_server_url(server)}missing.html", timeout=5)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert exc_info.value.code == 404


def _server_url(server) -> str:
    host, port = server.server_address[:2]
    return f"http://{host}:{port}/"
