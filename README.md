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

*   **Output File:** `og-image.jpg`
*   **Dimensions:** `1200 x 630 px` (1.91:1 aspect ratio)
*   **Format:** JPG (or PNG if text-heavy)
*   **Size Limit:** **< 500 KB** (Strict requirement to prevent WhatsApp rendering failures)
*   **Background:** **Solid colors only.** Do not use transparency, as messaging apps will render unpredictable background colors (white/dark gray) that may hide the logo.
*   **Design Rule (The "Safe Zone"):** 
    *   Scale and center the base SVG.
    *   Keep all critical elements within the center **1080 x 600 px**.
    *   The outer 60px on the sides and 15px on the top/bottom act as bleed/padding for UI cropping.

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
  └── og-image.jpg            # 1200x630, Solid BG, <500KB, centered safe zone
```

### 4. HTML Snippet Generator (Feature Idea)
The app should output this exact HTML snippet for the user to copy/paste into their `<head>` to properly map the generated files:

```html
<!-- Open Graph / Social Previews -->
<meta property="og:image" content="/og-image.jpg" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta name="twitter:card" content="summary_large_image" />

<!-- Favicons (Modern & Legacy) -->
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="icon" href="/favicon.ico" sizes="32x32" />

<!-- OS Native Icons -->
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
<link rel="manifest" href="/manifest.json" /> <!-- Ensure 192 and 512 are linked inside -->
```

## 5. Generator Usage

Install dependencies with Pipenv:

```bash
pipenv install --dev
pipenv run playwright install chromium
```

Generate the default bundle from one SVG:

```bash
pipenv run python -m base_images --base logo.svg --output assets --background '#ffffff'
```

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
)
generator.generate()
```

### Configuration

The default layout lives in `configs/default-assets.json` and is also exported as `DEFAULT_ASSET_CONFIG`. If no config is supplied, `AssetGenerator` uses that default config.

Pass a JSON config file to override only the values that differ from the defaults:

```bash
pipenv run python -m base_images --base logo.svg --output assets --config asset-config.json
```

Example override:

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

Each output can configure `filename`, `width`, `height`, `aspect_ratio`, `format`, `background`, `tier`, `padding_percent`, `safe_zone`, `ico_sizes`, and compression fields such as `quality`, `min_quality`, and `max_bytes`. Ratios are validated against the configured dimensions.