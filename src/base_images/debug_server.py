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

            output_key = _output_key_from_path(parsed.path, default_output_key)
            try:
                response = generator.render_html_for_key(output_key)
            except KeyError:
                self._send_html(
                    _render_not_found(generator, output_key),
                    status=HTTPStatus.NOT_FOUND,
                )
                return

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
        rows.append(
            "<li>"
            f"<a href=\"{href}\">{html.escape(spec.key)}</a> "
            f"<span>{spec.width}x{spec.height} {html.escape(spec.format)}</span>"
            "</li>"
        )

    return _debug_shell(
        title="Renderable Asset Outputs",
        body=(
            "<p>Open an output to inspect the exact HTML that Playwright screenshots.</p>"
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
