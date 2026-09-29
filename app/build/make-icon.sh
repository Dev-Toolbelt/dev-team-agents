#!/usr/bin/env bash
# Regenerate the derived brand assets from the brand source.
#
# Two outputs, both generated and both committed:
#   build/icon.icns                          — the macOS app icon
#   src/renderer/logo/derived/symbol-128.png — the symbol the renderer imports
#
# The files in src/renderer/logo/ are the brand SOURCE: 2400x2400 and 3600x1440 PNGs,
# 3.1 MB in total. The renderer must never import one directly — Vite emits whatever it
# is handed, so importing the 2400px symbol for a 20px header put 224 kB of the bundle
# into an image nobody can see at that size. Import from derived/ instead.
#
# Source: src/renderer/logo/logo-simbolo-transparente.png — the symbol alone (the
# asterisk), 2400x2400 RGBA. The brand guide (docs/brand/guia-de-cores.md)
# forbids distorting the mark, so this only pads and downscales; it never stretches.
#
# WHY IT PADS: the source art already carries a 5% transparent inset (measured alpha
# bbox 120,140 -> 2279,2258 of 2400). macOS icons want more breathing room than that,
# so the canvas is padded to 2700 to put the art at roughly 80% of the icon, which is
# the proportion Apple's icon grid uses for a mark that is not a rounded rectangle.
#
# Requires only macOS built-ins: sips and iconutil. No new dependency.
set -euo pipefail
cd "$(dirname "$0")/.."

SRC=src/renderer/logo/logo-simbolo-transparente.png
[ -f "$SRC" ] || { echo "no $SRC" >&2; exit 1; }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
SET="$WORK/icon.iconset"
mkdir -p "$SET"

sips -p 2700 2700 "$SRC" --out "$WORK/padded.png" >/dev/null

# The names are fixed by iconutil: each base size plus its @2x at double the pixels.
for size in 16 32 128 256 512; do
  retina=$((size * 2))
  sips -z "$size" "$size" "$WORK/padded.png" --out "$SET/icon_${size}x${size}.png" >/dev/null
  sips -z "$retina" "$retina" "$WORK/padded.png" --out "$SET/icon_${size}x${size}@2x.png" >/dev/null
done

iconutil -c icns "$SET" -o build/icon.icns
echo "build/icon.icns written ($(wc -c < build/icon.icns) bytes)"

# 128px covers the header's 20px box up to a 3x display with room to spare. Derived from
# the same padded canvas as the icon so the two never drift in framing.
mkdir -p src/renderer/logo/derived
sips -z 128 128 "$WORK/padded.png" --out src/renderer/logo/derived/symbol-128.png >/dev/null
echo "src/renderer/logo/derived/symbol-128.png written ($(wc -c < src/renderer/logo/derived/symbol-128.png) bytes)"

# The horizontal lockup, for the one surface with room for the slogan: the no-CLI empty
# state. 720px wide covers a 240px box at 3x. Two files because the brand guide gives a
# negative for dark backgrounds — letters to white, orange kept — rather than a mono
# white, and the renderer picks between them with prefers-color-scheme.
#
# -Z, not -z: it fits the longest edge and preserves the 2.5:1 ratio. The guide forbids
# distorting the mark, so nothing here may set both dimensions.
for variant in "logo-horizontal-transparente horizontal-light-720" \
               "logo-principal-dark-negativa horizontal-dark-720"; do
  src_name=${variant%% *}
  out_name=${variant##* }
  sips -Z 720 "src/renderer/logo/${src_name}.png" \
    --out "src/renderer/logo/derived/${out_name}.png" >/dev/null
  echo "src/renderer/logo/derived/${out_name}.png written ($(wc -c < "src/renderer/logo/derived/${out_name}.png") bytes)"
done
