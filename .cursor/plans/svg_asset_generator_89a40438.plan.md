---
name: SVG Asset Generator
overview: Implement a Python asset generator that renders SVG variants through configurable HTML layout templates into the favicon, app icon, and Open Graph outputs defined in the README. The first version will include a reusable class, a small CLI, and focused tests for sizing, ratios, naming, and template generation.
todos:
  - id: create-package
    content: Create the `src/base_images` package with layout specs, `AssetGenerator`, and rendering helpers.
    status: completed
  - id: add-cli
    content: Add a `python -m base_images` CLI for full bundle generation with layout config overrides.
    status: completed
  - id: add-deps
    content: Add a `Pipfile` with runtime and dev dependencies for rendering, post-processing, and tests.
    status: completed
  - id: add-tests
    content: Add focused unit tests plus a guarded end-to-end generation test.
    status: completed
  - id: update-docs
    content: Update README usage instructions to match the implemented API and CLI.
    status: completed
isProject: false
---

# SVG Asset Generator Plan

## Scope

- Add a Python package under [`src/base_images`](src/base_images) with an `AssetGenerator` class that accepts a base SVG plus optional tier-specific SVGs for `micro`, `search`, `macro`, and `social`.
- Add an explicit default configuration as both a loadable config file, such as [`configs/default-assets.json`](configs/default-assets.json), and an in-code default config dict exported by the package.
- Generate the README bundle into an output directory:
  - `favicon.svg`
  - `favicon.ico`
  - `icon-48.png`
  - `icon-192.png`
  - `apple-touch-icon.png`
  - `icon-512.png`
  - `og-image.jpg`
  - `manifest.json`
  - an HTML snippet helper for the documented `<head>` tags
- Use HTML templates as the rendering source of truth so each output has configurable canvas dimensions, aspect ratio validation, background behavior, safe-zone padding, and SVG placement.

## Implementation Approach

- Add dependencies through [`Pipfile`](Pipfile): `playwright` and `Pillow` as runtime packages for HTML-to-image screenshots and post-processing/JPEG/ICO packaging, with `pytest` in `[dev-packages]` for tests. Keep the existing dev container behavior aligned with Pipenv, which already installs with `pipenv install --dev` when a `Pipfile` exists.
- Create configurable layout definitions in code for the README tiers, using README values as defaults:
  - Social preview: `1200x630`, solid background, centered SVG constrained to the `1080x600` safe zone, JPG output with quality tuning to stay under 500 KB when practical.
  - Micro: transparent background, favicon SVG copy plus ICO sizes `16x16` and `32x32`, using the `micro` SVG if supplied.
  - Search/UI: transparent background PNGs at `48x48` and `192x192`, using the `search` SVG if supplied.
  - Macro: solid background PNGs at `180x180` and `512x512`, centered with 15% padding, using the `macro` SVG if supplied.
- Represent output configuration with typed specs that include filename, width, height, derived or expected aspect ratio, format, background mode, padding/safe-zone strategy, SVG tier, and any output-specific options such as JPG quality/size limit or ICO embedded sizes.
- Ship the README defaults in a versioned default config file, then load that same structure into an exported `DEFAULT_ASSET_CONFIG` dict so file-based config, code defaults, and tests all share one canonical shape.
- Allow callers to override sizes and ratios through a configuration object or file while preserving sensible README defaults. Validate that configured ratios match the requested dimensions, or derive ratios automatically when omitted.
- Keep SVG “simplification” manual: the class will not infer or mutate design detail. It will select the correct provided SVG per tier and fall back to the base SVG when a tier file is omitted.
- Render each output by loading a generated HTML document in headless Chromium, setting the viewport to the target size, and taking a screenshot. Use temporary HTML files or data URLs so the class can run without a web server.
- Use `Pillow` only after screenshots where needed: convert macro/social backgrounds to non-transparent formats, build the multi-size `favicon.ico`, and retry/compress `og-image.jpg` quality if it exceeds the README size limit.

## Public Interface

- Expose a class shaped roughly like:

```python
AssetGenerator(
    base_svg: Path,
    output_dir: Path,
    micro_svg: Path | None = None,
    search_svg: Path | None = None,
    macro_svg: Path | None = None,
    social_svg: Path | None = None,
    background: str = "#ffffff",
    config: AssetConfig | Path | None = None,
)
```

- Provide `generate()` for the full bundle and smaller helpers for rendering individual specs where tests benefit from direct calls.
- Add `AssetConfig`/`OutputSpec` types so applications can customize all output filenames, dimensions, ratios, formats, backgrounds, padding, safe zones, and compression limits without editing generator internals.
- When `config` is omitted, `AssetGenerator` will use the package’s `DEFAULT_ASSET_CONFIG`. When `config` is a path or dict, merge it over the default config so users can override only the fields they need.
- Add a CLI entrypoint such as:

```bash
python -m base_images --base logo.svg --output assets --background '#ffffff' --micro logo-micro.svg --search logo-search.svg --macro logo-macro.svg --social logo-social.svg
python -m base_images --base logo.svg --output assets --config asset-config.json
```

- Support a config file shape that can express per-output overrides, for example:

```json
{
  "outputs": {
    "og-image": {
      "width": 1200,
      "height": 630,
      "aspect_ratio": "40:21",
      "safe_zone": { "width": 1080, "height": 600 },
      "format": "jpg"
    },
    "icon-512": {
      "width": 512,
      "height": 512,
      "aspect_ratio": "1:1",
      "padding_percent": 15
    }
  }
}
```

## Tests

- Add tests under [`tests`](tests) that avoid depending on visual correctness pixel-by-pixel where possible:
  - verify [`configs/default-assets.json`](configs/default-assets.json) and `DEFAULT_ASSET_CONFIG` expose the same default output definitions;
  - verify default layout specs match README dimensions, ratios, formats, backgrounds, and padding rules;
  - verify custom configuration can override every output size, aspect ratio, safe zone, padding value, filename, and format;
  - verify invalid size/ratio combinations fail with a clear validation error;
  - verify tier-specific SVG selection and fallback behavior;
  - verify generated HTML contains the expected canvas size, background, and safe-zone placement;
  - where feasible, run a small end-to-end generation against a simple inline SVG and assert output files exist with expected image dimensions.
- If browser binaries are not available in the current environment, mark only the screenshot end-to-end test as skipped with a clear reason, while keeping pure unit tests active.

## Documentation

- Update [`README.md`](README.md) with installation notes, the Playwright browser setup command, Python API usage, CLI usage, expected outputs, the default config file path, how to provide optional per-tier SVG variants, and how to configure output sizes/ratios/layout rules.