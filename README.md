# base-images

## Dev Container

This repository includes a basic Python dev container in `.devcontainer/`.

When the container is created:

- If a `Pipfile` exists, dependencies are installed with `pipenv install --dev`.
- Otherwise, a local `.venv` is created and upgraded with current packaging tools.
- If `requirements.txt` exists, it is installed into that `.venv`.

No ports are forwarded by default. The container is intended for Python apps that make outbound requests.

## Image Generation Specifications 

This document outlines the technical and design specifications for generating website image assets (Favicons, App Icons, and Social Previews) from a base SVG. 

## 1. Social Preview (Open Graph) Images
Used for link previews in social media, messaging apps (WhatsApp, iMessage, Slack), and search AI.

*   **Primary Output File:** `og-image.jpg`
*   **Dimensions:** `1200 x 630 px` (1.91:1 aspect ratio)
*   **Format:** JPG (or PNG if text-heavy)
*   **Size Limit:** **< 500 KB** (Strict requirement to prevent WhatsApp rendering failures)
*   **Background:** **Solid colors only.** Do not use transparency, as messaging apps will render unpredictable background colors (white/dark gray) that may hide the logo.
*   **Design Rule (The "Safe Zone"):** 
    *   Scale and center the base SVG.
    *   Keep all critical elements within the center **1080 x 600 px**.
    *   The outer 60px on the sides and 15px on the top/bottom act as bleed/padding for UI cropping.

### Platform-Optimized Social Variants
The default config also exports additional social sizes for platforms whose preview or feed layouts benefit from a different crop:

| Output | Dimensions | Best fit | Wordmark layout |
| --- | ---: | --- | --- |
| `og-image.jpg` | `1200 x 630` | Universal Open Graph, Facebook, Slack, Discord, WhatsApp, iMessage | Inline, mark left and wordmark right |
| `twitter-image.jpg` | `1200 x 628` | X/Twitter `summary_large_image` | Inline, tighter vertical safe zone |
| `linkedin-image.jpg` | `1200 x 627` | LinkedIn link previews | Inline, LinkedIn's exact link-share ratio |
| `social-square.jpg` | `1200 x 1200` | Square thumbnails and fallback social cards | Stacked, mark above wordmark |
| `social-portrait.jpg` | `1080 x 1350` | LinkedIn/Instagram-style feed exports | Poster, wrapped wordmark below mark |
| `pinterest-pin.jpg` | `1000 x 1500` | Pinterest standard pins | Poster, wrapped wordmark above mark |
| `story-image.jpg` | `1080 x 1920` | Story/Reels-style manual sharing | Poster, wrapped wordmark above mark with wider vertical safe zone |

### Platform Metadata Behavior
Most social and messaging platforms do not have their own image meta tag. They scrape the shared page URL and read the first valid Open Graph image. X/Twitter is the major exception because it supports a dedicated `twitter:image`, and Pinterest can receive a vertical image through explicit Pin/share URLs.

| Platform | Image URL to set | Recommended asset | Notes |
| --- | --- | --- | --- |
| Facebook / Messenger | `og:image` | `og-image.jpg` | Uses Open Graph. Keep the universal `1200 x 630` image first. |
| LinkedIn | `og:image` | `og-image.jpg` by default, or `linkedin-image.jpg` on a LinkedIn-specific share page | No reliable `linkedin:image` tag. LinkedIn reads Open Graph. |
| iMessage | `og:image` | `og-image.jpg` | Uses Open Graph link metadata. No iMessage-specific image tag. |
| WhatsApp | `og:image` | `og-image.jpg` | Uses Open Graph. Keep the image absolute HTTPS and ideally under `500 KB`. |
| Slack | `og:image` | `og-image.jpg` | Uses Open Graph and may also inspect Twitter card tags. No Slack-specific image tag for normal links. |
| Microsoft Teams | `og:image` | `og-image.jpg` | Uses Open Graph for link unfurls. No Teams-specific image tag. |
| Discord | `og:image` | `og-image.jpg` | Uses Open Graph for embeds. |
| Telegram / Signal | `og:image` | `og-image.jpg` | Generally use Open Graph and cache aggressively. |
| Reddit | `og:image` | `og-image.jpg` or `social-square.jpg` on a Reddit-specific share page | Uses Open Graph/Twitter metadata; exact crop can vary by client. |
| Bluesky / Mastodon | `og:image` | `og-image.jpg` | Generally use Open Graph/Twitter metadata fallbacks. |
| X / Twitter | `twitter:image` | `twitter-image.jpg` | Use with `twitter:card=summary_large_image`. This is the real platform-specific override. |
| Pinterest | `data-pin-media` or share URL `media=` | `pinterest-pin.jpg` | Normal page previews can use Open Graph, but Pin buttons/share links should point directly at the vertical asset. |
| Instagram / Stories / Reels | No normal link-preview meta URL | `social-portrait.jpg` or `story-image.jpg` | Use these as manual upload/export assets rather than page `<head>` metadata. |

If a platform-specific crop is required for a platform that only reads Open Graph, create a dedicated share route where that asset is the first `og:image`. For example, a LinkedIn-only route can use `linkedin-image.jpg` as its first Open Graph image while the main page keeps `og-image.jpg`.

---

## 2. Favicons & App Icons (Optical Sizing)
Because the base SVG will be viewed at drastically different sizes, the app should generate three distinct optical sizes.

### A. The "Micro" Tier (Browser Tabs & Bookmarks)
*   **Output Files:** `favicon.svg` (Dynamic), `favicon.ico` (Contains 16x16 & 32x32 fallback)
*   **Dimensions:** `16 x 16 px`, `32 x 32 px`
*   **Format:** SVG, ICO
*   **Background:** Transparent (SVG can use CSS `@media (prefers-color-scheme: dark)` for dynamic theming).
*   **Design Rules:**
    *   **Hyper-simplified:** Strip all text, wordmarks, and tiny details.
    *   Exaggerate negative space and snap edges to the pixel grid to prevent anti-aliasing blur.

### B. The "Search & UI" Tier (Google Search Results & Android Manifest)
*   **Output Files:** `icon-48.png`, `icon-192.png`
*   **Dimensions:** `48 x 48 px`, `192 x 192 px`
*   **Format:** PNG
*   **Background:** Transparent.
*   **Design Rules:**
    *   **Moderately detailed:** Main logomark can be used.
    *   Thicken hairline strokes to ensure visibility. Avoid complex gradients.
    *   *(Note: 48px is Google Search's strict minimum requirement for mobile search favicons).*

### C. The "Macro" Tier (Apple Touch & App Icons)
*   **Output Files:** `apple-touch-icon.png`, `icon-512.png`
*   **Dimensions:** `180 x 180 px`, `512 x 512 px`
*   **Format:** PNG
*   **Background:** **Solid colors only.** No transparency allowed by iOS/Android standards. 
*   **Design Rules:**
    *   **Full detail:** Complex branding, gradients, and shadows are safe.
    *   **App Logic (Safe Zone):** The app must automatically scale down the base SVG to sit in the center with **15-20% padding** around the edges. iOS and Android will aggressively mask/crop the edges into circles or "squircles".

---

## 3. App Output Checklist (The Generation Pipeline)
When a user uploads their base SVG(s) and selects their background colors, the app should generate and export the following bundle:

### Core Files Structure
```text
/assets
  ├── favicon.svg             # Base SVG with light/dark CSS embedded
  ├── favicon.ico             # Flattened legacy container (16x16 + 32x32)
  ├── icon-48.png             # Transparent BG, moderate detail
  ├── icon-192.png            # Transparent BG, moderate detail
  ├── apple-touch-icon.png    # 180x180, Solid BG, 15% edge padding
  ├── icon-512.png            # 512x512, Solid BG, 15% edge padding
  ├── og-image.jpg            # 1200x630, universal OG card, <500KB
  ├── twitter-image.jpg       # 1200x628, X/Twitter large card
  ├── linkedin-image.jpg      # 1200x627, LinkedIn link preview
  ├── social-square.jpg       # 1200x1200, square fallback/export
  ├── social-portrait.jpg     # 1080x1350, portrait feed export
  ├── pinterest-pin.jpg       # 1000x1500, Pinterest pin export
  └── story-image.jpg         # 1080x1920, story/reels export
```

### 4. HTML Snippet Generator (Feature Idea)
The app should output HTML for users to paste into their `<head>` to properly map the generated files. Production sites should use absolute HTTPS URLs instead of root-relative paths:

```html
<!-- Open Graph / Social Previews -->
<meta property="og:type" content="website" />
<meta property="og:url" content="https://example.com/page" />
<meta property="og:title" content="Page title" />
<meta property="og:description" content="Page description" />
<meta property="og:image" content="https://example.com/og-image.jpg" />
<meta property="og:image:secure_url" content="https://example.com/og-image.jpg" />
<meta property="og:image:type" content="image/jpeg" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:image:alt" content="Preview image description" />

<!-- X / Twitter -->
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="Page title" />
<meta name="twitter:description" content="Page description" />
<meta name="twitter:image" content="https://example.com/twitter-image.jpg" />
<meta name="twitter:image:alt" content="Preview image description" />

<!-- Favicons (Modern & Legacy) -->
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="icon" href="/favicon.ico" sizes="32x32" />

<!-- OS Native Icons -->
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
<link rel="manifest" href="/manifest.json" /> <!-- Ensure 192 and 512 are linked inside -->
```

Pinterest can target the generated vertical Pin image through an explicit share URL or Pin button:

```html
<a
  href="https://www.pinterest.com/pin/create/button/?url=https%3A%2F%2Fexample.com%2Fpage&media=https%3A%2F%2Fexample.com%2Fpinterest-pin.jpg&description=Page%20description"
>
  Save to Pinterest
</a>
```

## 5. Generator Usage

Install dependencies with Pipenv:

```bash
pipenv install --dev
pipenv run playwright install --with-deps chromium
```

Generate the default bundle from one SVG:

```bash
pipenv run python -m base_images \
  --base logo.svg \
  --output assets \
  --background '#ffffff' \
  --wordmark 'Acme'
```

The optional `--wordmark` text is rendered on the larger macro and social outputs by default: `apple-touch-icon.png`, `icon-512.png`, `og-image.jpg`, `twitter-image.jpg`, `linkedin-image.jpg`, `social-square.jpg`, `social-portrait.jpg`, `pinterest-pin.jpg`, and `story-image.jpg`.

Debug the renderable browser source for an output without writing the image:

```bash
pipenv run python -m base_images \
  --base logo.svg \
  --output assets \
  --wordmark 'Acme' \
  --serve-render-html \
  --debug-output og-image
```

This starts a local server at `http://127.0.0.1:8000/` with a framed debug view for the selected output. The page uses a dark checkerboard background and an orange border so the image bounds stay visible even when the generated image is white on white. Open `/outputs` to switch between configured outputs, or pass another key such as `--debug-output icon-512`. Use `/raw/og-image.html` when you need the exact HTML Playwright screenshots without the debug frame. Use `--port 8001` or `--host 0.0.0.0` when you need a different bind address, and add `--open-browser` to ask Python to open the page automatically.

Provide optical SVG variants when the base SVG is too detailed for smaller sizes:

```bash
pipenv run python -m base_images \
  --base logo.svg \
  --micro logo-micro.svg \
  --search logo-search.svg \
  --macro logo-macro.svg \
  --social logo-social.svg \
  --output assets
```

The optional tier files map to the specification tiers:

- `--micro` is used for `favicon.svg` and `favicon.ico`.
- `--search` is used for `icon-48.png` and `icon-192.png`.
- `--macro` is used for `apple-touch-icon.png` and `icon-512.png`.
- `--social` is used for `og-image.jpg`.
- Any omitted tier falls back to `--base`.

### Python API

```python
from pathlib import Path

from base_images import AssetGenerator

generator = AssetGenerator(
    base_svg=Path("logo.svg"),
    output_dir=Path("assets"),
    background="#ffffff",
    wordmark="Acme",
)
generator.generate()
```

### Configuration

The default layout lives in `configs/default-assets.jsonc` and is also exported as `DEFAULT_ASSET_CONFIG`. If no config is supplied, `AssetGenerator` uses that default config.

Pass a JSON or JSONC config file to override only the values that differ from the defaults:

```bash
pipenv run python -m base_images --base logo.svg --output assets --config asset-config.jsonc
```

Example override:

```json
{
  "wordmark": {
    "font_family": "Archivo Black",
    "font_weight": 400,
    "google_fonts": true,
    "color": "#111827"
  },
  "outputs": {
    "og-image": {
      "width": 1200,
      "height": 630,
      "aspect_ratio": "40:21",
      "safe_zone": { "width": 1080, "height": 600 },
      "format": "jpg",
      "wordmark": {
        "enabled": true,
        "layout": "inline",
        "position": "right",
        "font_size_percent": 11,
        "gap_percent": 5,
        "artwork_area_percent": 42
      }
    },
    "icon-512": {
      "width": 512,
      "height": 512,
      "aspect_ratio": "1:1",
      "padding_percent": 15,
      "wordmark": {
        "enabled": true,
        "layout": "stacked",
        "position": "below",
        "font_size_percent": 11,
        "gap_percent": 4,
        "artwork_area_percent": 68
      }
    }
  }
}
```

Each output can configure `filename`, `width`, `height`, `aspect_ratio`, `format`, `background`, `tier`, `padding_percent`, `safe_zone`, `ico_sizes`, `wordmark`, and compression fields such as `quality`, `min_quality`, and `max_bytes`. Ratios are validated against the configured dimensions.

Wordmarks use Google Fonts by default and render in `Archivo Black` regular 400. Set `wordmark.google_fonts` to `false` to skip the Google Fonts link, or change `wordmark.font_family` / `wordmark.font_weight` to use a different configured font. Per-output `wordmark.enabled` controls whether the text is rendered for that asset. Per-output wordmarks can also choose `layout` (`inline`, `stacked`, or `poster`), `position`, `max_width_percent`, `wrap`, `line_height`, and spacing values so landscape cards, square exports, and vertical posters use different CSS without needing separate Python templates.
