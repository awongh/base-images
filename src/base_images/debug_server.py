"""Serve renderable asset HTML for browser debugging."""

from __future__ import annotations

import html
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import quote, unquote, urlparse

from base_images.generator import AssetGenerator


def make_debug_server(
    generator: AssetGenerator,
    *,
    output_key: str = "og-image",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> ThreadingHTTPServer:
    """Build an HTTP server for the browser-renderable asset HTML."""

    generator.config.spec(output_key)
    handler = _debug_handler(generator, output_key)
    return ThreadingHTTPServer((host, port), handler)


def serve_renderable_asset(
    generator: AssetGenerator,
    *,
    output_key: str = "og-image",
    host: str = "127.0.0.1",
    port: int = 8000,
    open_browser: bool = False,
) -> None:
    """Serve one renderable asset page until interrupted."""

    server = make_debug_server(
        generator,
        output_key=output_key,
        host=host,
        port=port,
    )
    url = _server_url(server)

    print(f"Serving {output_key!r} render HTML at {url}")
    print(f"All configured outputs: {url}outputs")
    print("Press Ctrl+C to stop.")

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped debug server.")
    finally:
        server.server_close()


def _debug_handler(
    generator: AssetGenerator,
    default_output_key: str,
) -> type[BaseHTTPRequestHandler]:
    class DebugAssetRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/outputs":
                self._send_html(_render_outputs_index(generator, default_output_key))
                return

            raw_output = parsed.path in {"/raw", "/raw/"} or parsed.path.startswith(
                "/raw/"
            )
            output_path = parsed.path.removeprefix("/raw") if raw_output else parsed.path
            output_key = _output_key_from_path(output_path, default_output_key)
            try:
                spec = generator.config.spec(output_key)
                asset_html = generator.render_html(spec)
            except KeyError:
                self._send_html(
                    _render_not_found(generator, output_key),
                    status=HTTPStatus.NOT_FOUND,
                )
                return

            response = (
                asset_html
                if raw_output
                else _render_debug_preview(output_key, spec.width, spec.height, asset_html)
            )
            self._send_html(response)

        def log_message(self, format: str, *args: Any) -> None:
            print(f"{self.address_string()} - {format % args}")

        def _send_html(
            self,
            body: str,
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return DebugAssetRequestHandler


def _output_key_from_path(path: str, default_output_key: str) -> str:
    if path in {"", "/"}:
        return default_output_key

    output_key = unquote(path.removeprefix("/"))
    if output_key.endswith(".html"):
        output_key = output_key.removesuffix(".html")
    return output_key


def _render_outputs_index(
    generator: AssetGenerator,
    default_output_key: str,
) -> str:
    rows = []
    for spec in generator.config.outputs:
        href = "/" if spec.key == default_output_key else f"/{quote(spec.key)}.html"
        raw_href = f"/raw/{quote(spec.key)}.html"
        rows.append(
            "<li>"
            f"<strong>{html.escape(spec.key)}</strong> "
            f"<span>{spec.width}x{spec.height} {html.escape(spec.format)}</span>"
            f" <a href=\"{href}\">debug</a>"
            f" <a href=\"{raw_href}\">raw</a>"
            "</li>"
        )

    return _debug_shell(
        title="Renderable Asset Outputs",
        body=(
            "<p>Open an output in the framed debug view, or open raw for the "
            "exact HTML that Playwright screenshots.</p>"
            f"<ul>{''.join(rows)}</ul>"
        ),
    )


def _render_not_found(generator: AssetGenerator, output_key: str) -> str:
    options = ", ".join(html.escape(spec.key) for spec in generator.config.outputs)
    return _debug_shell(
        title="Output Not Found",
        body=(
            f"<p>No configured output is named <code>{html.escape(output_key)}</code>.</p>"
            f"<p>Available outputs: {options}</p>"
        ),
    )


def _render_debug_preview(
    output_key: str,
    width: int,
    height: int,
    asset_html: str,
) -> str:
    escaped_key = html.escape(output_key)
    raw_href = f"/raw/{quote(output_key)}.html"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_key} Debug Preview</title>
  <style>
    * {{
      box-sizing: border-box;
    }}

    html,
    body {{
      min-height: 100%;
      margin: 0;
    }}

    body {{
      color: #f9fafb;
      font-family: system-ui, sans-serif;
      background-color: #111827;
      background-image:
        linear-gradient(45deg, #1f2937 25%, transparent 25%),
        linear-gradient(-45deg, #1f2937 25%, transparent 25%),
        linear-gradient(45deg, transparent 75%, #1f2937 75%),
        linear-gradient(-45deg, transparent 75%, #1f2937 75%);
      background-position: 0 0, 0 12px, 12px -12px, -12px 0;
      background-size: 24px 24px;
    }}

    header {{
      position: sticky;
      top: 0;
      z-index: 1;
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      align-items: center;
      justify-content: space-between;
      padding: 0.75rem 1rem;
      background: rgba(17, 24, 39, 0.92);
      border-bottom: 1px solid rgba(249, 250, 251, 0.18);
      backdrop-filter: blur(8px);
    }}

    h1 {{
      margin: 0;
      font-size: 1rem;
    }}

    a {{
      color: #93c5fd;
    }}

    .debug-meta {{
      color: #d1d5db;
      font-size: 0.9rem;
    }}

    .debug-stage {{
      min-width: fit-content;
      padding: 2rem;
    }}

    .asset-debug-frame {{
      width: {width}px;
      height: {height}px;
      overflow: hidden;
      background: #ffffff;
      border: 3px solid #f97316;
      box-shadow:
        0 0 0 1px rgba(255, 255, 255, 0.75),
        0 20px 60px rgba(0, 0, 0, 0.45);
    }}

    iframe {{
      display: block;
      width: {width}px;
      height: {height}px;
      border: 0;
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>{escaped_key}</h1>
      <div class="debug-meta">{width}x{height}px, orange border marks the image bounds</div>
    </div>
    <nav>
      <a href="/outputs">outputs</a>
      <a href="{raw_href}">raw screenshot HTML</a>
    </nav>
  </header>
  <main class="debug-stage">
    <div
      class="asset-debug-frame"
      data-debug-output-key="{escaped_key}"
      data-debug-width="{width}"
      data-debug-height="{height}"
    >
      <iframe
        title="{escaped_key} render HTML"
        srcdoc="{html.escape(asset_html, quote=True)}"
      ></iframe>
    </div>
  </main>
</body>
</html>
"""


def _debug_shell(*, title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      margin: 2rem;
      color: #111827;
      font-family: system-ui, sans-serif;
      line-height: 1.5;
    }}

    a {{
      color: #2563eb;
    }}

    li {{
      margin: 0.4rem 0;
    }}

    span {{
      color: #6b7280;
      margin-left: 0.5rem;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(title)}</h1>
    {body}
  </main>
</body>
</html>
"""


def _server_url(server: ThreadingHTTPServer) -> str:
    host, port = server.server_address[:2]
    display_host = "127.0.0.1" if host in {"", "0.0.0.0", "::"} else host
    return f"http://{display_host}:{port}/"
