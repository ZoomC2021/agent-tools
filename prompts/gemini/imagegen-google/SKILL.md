---
name: imagegen-google
description: Generate or edit images with Google Nano Banana Pro (gemini-3-pro-image-preview) via the Vertex AI Express mode of the google-genai SDK. Use when the user asks to generate an image, create concept art / mockups / icons / hero images, or edit a reference image and explicitly wants `/imagegen-google` or Nano Banana Pro / Gemini image generation.
---

# Imagegen (Google)

Generate or edit images using **Google Nano Banana Pro** (`gemini-3-pro-image-preview`) via the Vertex AI Express mode of the `google-genai` Python SDK.

## Requirements

- `GOOGLE_API_KEY` must be set in the shell environment with a Vertex AI Express API key (starts with `AQ.`).
- `python3` and the `google-genai` package must be available. Install with `pip install --upgrade google-genai pillow` if missing.
- Default model: `gemini-3-pro-image-preview` (Nano Banana Pro).
- For lower cost / faster turnaround the user may request `gemini-2.5-flash-image-preview` (Nano Banana); otherwise stay on Pro.

## Workflow

1. **Clarify only if necessary.** If the user did not specify an output path, use a safe local filename such as `imagegen-output.png` or a descriptive slug in the current directory.
2. **Write a complete visual prompt.** Include subject, composition, style, lighting, color palette, aspect ratio intent, and any text that must appear in the image. Preserve the user's requested style and constraints.
3. **Choose parameters deliberately.**
   - `aspect_ratio`: Nano Banana Pro accepts `1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`. Pick the requested ratio, or infer from purpose (`1:1` icon/social, `16:9` hero/desktop, `9:16` mobile/story, `21:9` ultrawide banner).
   - Number of outputs: pass `number_of_images` only when the user asks for variations; otherwise generate one.
4. **Write the image to disk.** The model returns image bytes inline. Decode and save immediately; report the path only after the file exists.
5. **Report the result.** Include the saved file path, model used, and the key parameters. Do not claim success until `file` confirms a real image.

## Text-to-Image

```bash
test -n "$GOOGLE_API_KEY" || { echo "GOOGLE_API_KEY is not set" >&2; exit 1; }

python3 - <<'PY'
import os, sys
from google import genai
from google.genai import types

client = genai.Client(vertexai=True, api_key=os.environ["GOOGLE_API_KEY"])

prompt = (
    "A polished 1:1 macOS app icon for a CLI image generator, dark indigo "
    "background, luminous cyan camera aperture merged with a terminal cursor, "
    "clean vector-like 3D, soft glow, high contrast, no text"
)
out = "imagegen-output.png"

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=prompt,
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(aspect_ratio="1:1"),
    ),
)

saved = False
for part in response.candidates[0].content.parts:
    if getattr(part, "inline_data", None) and part.inline_data.data:
        with open(out, "wb") as f:
            f.write(part.inline_data.data)
        saved = True
        break

if not saved:
    sys.exit("No image returned. Check prompt safety filters and quota.")
print(out)
PY

file imagegen-output.png
```

For multiple variations, set `number_of_images` in `ImageConfig` and write each `inline_data` part to its own filename.

## Image Editing / Multi-Image Composition

Nano Banana Pro accepts up to 14 reference images in a single call. Pass each reference as a `Part` with inline image bytes alongside the prompt. Describe the role of every reference explicitly (subject, style, color palette, layout) and say what must remain unchanged.

```bash
test -n "$GOOGLE_API_KEY" || { echo "GOOGLE_API_KEY is not set" >&2; exit 1; }

python3 - <<'PY'
import mimetypes, os, sys
from google import genai
from google.genai import types

client = genai.Client(vertexai=True, api_key=os.environ["GOOGLE_API_KEY"])

src = "input.png"
out = "imagegen-edit.png"
prompt = (
    "Keep the same composition, but render it as a premium product hero image "
    "with warm studio lighting, sharper contrast, a clean off-white background, "
    "and no added text."
)

mime = mimetypes.guess_type(src)[0] or "image/png"
with open(src, "rb") as f:
    image_bytes = f.read()

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[
        types.Part.from_bytes(data=image_bytes, mime_type=mime),
        prompt,
    ],
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(aspect_ratio="16:9"),
    ),
)

saved = False
for part in response.candidates[0].content.parts:
    if getattr(part, "inline_data", None) and part.inline_data.data:
        with open(out, "wb") as f:
            f.write(part.inline_data.data)
        saved = True
        break

if not saved:
    sys.exit("No image returned. Check prompt safety filters and quota.")
print(out)
PY

file imagegen-edit.png
```

For multi-image edits, append additional `types.Part.from_bytes(...)` entries to `contents` before the text prompt and label each reference's role in the prompt (e.g., "subject from image 1, palette from image 2, layout from image 3").

## Prompting Guidelines

- Be concrete: subject, environment, camera angle, framing, material, lighting, mood, palette, and rendering style.
- Match the output format to the destination: square icons, widescreen hero images, vertical social assets, or banner ratios.
- For UI mockups, specify device/frame, screen state, layout hierarchy, typography feel, spacing, and color system. Avoid asking for tiny unreadable body text.
- For logos/icons, ask for simple silhouettes, strong contrast, centered composition, and no small text.
- For edits, say what must remain unchanged as well as what should change.
- Nano Banana Pro is strong at in-image text rendering — when text matters, quote it exactly and specify font feel, casing, and placement.

## Safety and Secrets

- Never write API keys into files, prompts, logs, or committed config.
- Use `$GOOGLE_API_KEY` from the environment; the Vertex AI Express key (prefix `AQ.`) is passed directly to `genai.Client(vertexai=True, api_key=...)`.
- Do not upload private user images unless the user has explicitly asked to use them for generation/editing.
- All Nano Banana Pro outputs include an invisible SynthID watermark; do not attempt to strip or hide it.
