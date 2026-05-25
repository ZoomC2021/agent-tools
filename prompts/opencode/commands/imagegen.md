---
description: Generate and edit images with xAI Grok Imagine from OpenCode.
mode: subagent
model: fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo
---

# Imagegen

Generate or edit images from OpenCode using xAI Grok Imagine.

Use this when the user asks to generate an image, create visual assets, make concept art, produce mockups, create app icons, create hero images, or edit/reference an existing image and explicitly wants `/imagegen` or Grok Imagine.

## Requirements

- `XAI_API_KEY` must be set in the shell environment.
- `curl`, `jq`, and `python3` should be available.
- Default model: `grok-imagine-image-quality`.
- Do not use deprecated `grok-imagine-image-pro` for new requests.

## Workflow

1. **Clarify only if necessary.** If the user did not specify an output path, use a safe local filename such as `imagegen-output.png` or a descriptive slug in the current directory.
2. **Write a complete visual prompt.** Include subject, composition, style, lighting, color palette, aspect ratio intent, and any text that must appear in the image. Preserve the user's requested style and constraints.
3. **Choose parameters deliberately.**
   - `aspect_ratio`: use the requested ratio, or infer from purpose (`1:1` icon/social, `16:9` hero/desktop, `9:16` mobile/story, `2:1` banner). Use `auto` when unsure.
   - `resolution`: use `1k` by default; use `2k` for final assets, hero images, print-like quality, or when the user asks for high resolution.
   - `n`: use `1` by default; use up to `4` only when the user asks for variations.
4. **Request base64 output when saving locally.** xAI returns temporary URLs by default; prefer `response_format: "b64_json"` and write the image file immediately.
5. **Report the result.** Include the saved file path and the key parameters used. Do not claim success until the file exists.

## Text-to-Image

Use the image generation endpoint for new images.

```bash
test -n "$XAI_API_KEY" || { echo "XAI_API_KEY is not set" >&2; exit 1; }

prompt='A polished 1:1 macOS app icon for a CLI image generator, dark indigo background, luminous cyan camera aperture merged with a terminal cursor, clean vector-like 3D, soft glow, high contrast, no text'
out='imagegen-output.png'

curl -sS https://api.x.ai/v1/images/generations \
  -H "Authorization: Bearer $XAI_API_KEY" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n \
    --arg model 'grok-imagine-image-quality' \
    --arg prompt "$prompt" \
    --arg aspect_ratio '1:1' \
    --arg resolution '2k' \
    '{model:$model,prompt:$prompt,aspect_ratio:$aspect_ratio,resolution:$resolution,response_format:"b64_json"}')" \
  | jq -r '.data[0].b64_json' \
  | python3 -c 'import base64,sys; sys.stdout.buffer.write(base64.b64decode(sys.stdin.read()))' > "$out"

file "$out"
```

For multiple variations, add `n` to the JSON body and save each `.data[]` item separately.

## Image Editing

Use the edits endpoint when the user provides a source/reference image. xAI accepts a public image URL or a base64 data URI. The OpenAI SDK `images.edit()` multipart path is not compatible with xAI image editing; use direct JSON HTTP, the xAI SDK, or the Vercel AI SDK instead.

```bash
test -n "$XAI_API_KEY" || { echo "XAI_API_KEY is not set" >&2; exit 1; }

src='input.png'
prompt='Keep the same composition, but render it as a premium product hero image with warm studio lighting, sharper contrast, clean background, and no added text.'
out='imagegen-edit.png'
mime="$(file --mime-type -b "$src")"
data_uri="data:${mime};base64,$(base64 < "$src" | tr -d '\n')"

curl -sS https://api.x.ai/v1/images/edits \
  -H "Authorization: Bearer $XAI_API_KEY" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n \
    --arg model 'grok-imagine-image-quality' \
    --arg prompt "$prompt" \
    --arg url "$data_uri" \
    --arg resolution '1k' \
    '{model:$model,prompt:$prompt,image:{url:$url,type:"image_url"},resolution:$resolution,response_format:"b64_json"}')" \
  | jq -r '.data[0].b64_json' \
  | python3 -c 'import base64,sys; sys.stdout.buffer.write(base64.b64decode(sys.stdin.read()))' > "$out"

file "$out"
```

For multi-image edits, provide up to three source images as the API supports, and explicitly describe the role of each reference in the prompt (for example, subject from image 1, color palette from image 2, layout from image 3).

## Prompting Guidelines

- Be concrete: subject, environment, camera angle, framing, material, lighting, mood, palette, and rendering style.
- Match the output format to the destination: square icons, widescreen hero images, vertical social assets, or banner ratios.
- For UI mockups, specify device/frame, screen state, layout hierarchy, typography feel, spacing, and color system. Avoid asking for tiny unreadable body text.
- For logos/icons, ask for simple silhouettes, strong contrast, centered composition, and no small text.
- For edits, say what must remain unchanged as well as what should change.
- If the output URL is used instead of base64, download it immediately because generated URLs are temporary.

## Safety and Secrets

- Never write API keys into files, prompts, logs, or committed config.
- Use `$XAI_API_KEY` from the environment.
- Do not upload private user images unless the user has explicitly asked to use them for generation/editing.
