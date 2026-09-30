#!/usr/bin/env bash
# Regenerate the derived brand assets from the brand source.
#
# Four kinds of output, all generated and all committed:
#   build/icon.icns                          — the macOS app icon, from the app-icon tile
#   build/icon.png                           — 1024px, the cross-platform icon source
#   src/renderer/logo/derived/symbol-128.png — the asterisk symbol, for small surfaces
#   src/renderer/logo/derived/wordmark-*     — the lockup with the slogan cropped off
#
# WHY A PNG TOO, when the icns already exists: `iconutil` is macOS-only and writes no
# `.ico`, so the Windows installer had no icon of its own and would have shipped
# Electron's default. electron-builder derives the per-platform icons — including that
# `.ico` — from a single square PNG of at least 256px, so one 1024px file closes it with
# no new tool. The same file is the window icon on Windows and Linux in development,
# where there is no bundle to take an icon from.
#
# The files in src/renderer/logo/ are the brand SOURCE: 2400x2400 and 3600x1440 PNGs,
# 3.1 MB in total. The renderer must never import one directly — Vite emits whatever it
# is handed, so importing the 2400px symbol for a 20px header put 224 kB of the bundle
# into an image nobody can see at that size. Import from derived/ instead.
#
# Source: src/renderer/logo/logo-icone-app.png — the APP ICON composition (folder, `/d`
# and the asterisk on a white tile), which the brand guide records as its own
# composition distinct from the symbol. It is already laid out on Apple's icon grid: a
# 824px rounded tile, with its shadow, centred on a 1024px transparent canvas. So, unlike
# the bare asterisk it replaced, it is only downscaled here — never padded, never stretched.
#
# The tile itself is generated from the original art (logo-icone-app-original.png, the
# drawing on a white field) by `make-icon.sh --tile`, which is the only path that needs
# ImageMagick. Everything else requires only macOS built-ins: sips and iconutil.
set -euo pipefail
cd "$(dirname "$0")/.."

LOGO=src/renderer/logo
TILE=$LOGO/logo-icone-app.png

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

if [ "${1:-}" = "--tile" ]; then
  command -v magick >/dev/null || { echo "--tile needs ImageMagick (magick)" >&2; exit 1; }
  ORIGINAL=$LOGO/logo-icone-app-original.png
  [ -f "$ORIGINAL" ] || { echo "no $ORIGINAL" >&2; exit 1; }
  # The art's own field is off-white (254,254,254): the tile is filled with that same
  # colour so the trimmed drawing sits on it with no visible seam.
  FIELD='srgb(254,254,254)'
  # Trim the white field, then fit the drawing to 640px wide — 78% of the tile, the
  # optical weight of a landscape mark on Apple's grid. -resize keeps the ratio.
  # Every intermediate is written as PNG32: a tile holding only white and a grey hairline
  # is otherwise saved as grayscale, and the composite onto it inherits that colourspace —
  # which is how the first run turned the orange grey.
  magick "$ORIGINAL" -fuzz 8% -trim +repage -resize 640x640 "PNG32:$WORK/art.png"
  # 824px tile, 185px corner radius (Apple's ~22.4%), with a faint hairline so the white
  # tile still reads on a white Finder window.
  magick -size 824x824 xc:none -fill "$FIELD" -stroke 'rgba(0,0,0,0.08)' -strokewidth 2 \
    -draw 'roundrectangle 1,1 822,822 185,185' "PNG32:$WORK/tile.png"
  magick "$WORK/tile.png" "$WORK/art.png" -gravity center -composite "PNG32:$WORK/tile-art.png"
  # A soft drop shadow like the system icons', then centred on the 1024 canvas.
  magick "$WORK/tile-art.png" \( +clone -background black -shadow 30x12+0+10 \) +swap \
    -background none -layers merge +repage "PNG32:$WORK/shadowed.png"
  magick -size 1024x1024 xc:none "$WORK/shadowed.png" -gravity center -composite "PNG32:$TILE"
  echo "$TILE written ($(wc -c < "$TILE") bytes)"
fi

[ -f "$TILE" ] || { echo "no $TILE — run with --tile once" >&2; exit 1; }

SET="$WORK/icon.iconset"
mkdir -p "$SET"

# The names are fixed by iconutil: each base size plus its @2x at double the pixels.
for size in 16 32 128 256 512; do
  retina=$((size * 2))
  sips -z "$size" "$size" "$TILE" --out "$SET/icon_${size}x${size}.png" >/dev/null
  sips -z "$retina" "$retina" "$TILE" --out "$SET/icon_${size}x${size}@2x.png" >/dev/null
done

iconutil -c icns "$SET" -o build/icon.icns
echo "build/icon.icns written ($(wc -c < build/icon.icns) bytes)"

# 1024px: electron-builder's documented floor is 256, and 1024 is what macOS and the
# Windows installer's largest slot actually want. From the same tile as the icns, so no
# platform's icon is framed differently from another's.
sips -z 1024 1024 "$TILE" --out build/icon.png >/dev/null
echo "build/icon.png written ($(wc -c < build/icon.png) bytes)"

# The symbol alone — the asterisk, not the app icon — for renderer surfaces too small for
# the tile. 128px covers a 20px box up to a 3x display. The source art carries a 5%
# transparent inset; padding 2400 -> 2700 gives it the same breathing room it had as the
# app icon, and -z on a square canvas cannot distort it.
mkdir -p src/renderer/logo/derived
sips -p 2700 2700 src/renderer/logo/logo-simbolo-transparente.png --out "$WORK/symbol.png" >/dev/null
sips -z 128 128 "$WORK/symbol.png" --out src/renderer/logo/derived/symbol-128.png >/dev/null
echo "src/renderer/logo/derived/symbol-128.png written ($(wc -c < src/renderer/logo/derived/symbol-128.png) bytes)"

# The tray / menu-bar icon: 16pt, plus the @2x Electron picks up by name on a Retina
# display. The coloured symbol rather than a monochrome template — the brand pack has no
# template glyph, and inventing one is a brand decision, not a build step. Shipped via
# electron-builder's `extraResources` (build/ itself is not packaged), read from
# `process.resourcesPath/tray/` in a packaged app and from here in development.
mkdir -p build/tray
sips -z 16 16 "$WORK/padded.png" --out build/tray/tray.png >/dev/null
sips -z 32 32 "$WORK/padded.png" --out build/tray/tray@2x.png >/dev/null
echo "build/tray/tray.png and tray@2x.png written"

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

# The same lockup with the slogan cropped away, for the header — where the full
# composition cannot go. The guide says not to use the slogan at a size that hurts its
# legibility, and the header row is exactly that size; cropping it off is what makes the
# lockup usable there at all, and is why the header carried the symbol alone until now.
#
# The crop is MEASURED, not eyeballed. Decoding logo-horizontal-transparente.png's alpha
# gives two content bands and 224 empty rows between them:
#     mark    rows  150..866   (x 175..3400, so 3226x717 — a 4.5:1 mark)
#     slogan  rows 1091..1274
# So the cut lands in dead space with ~100 rows of clearance on each side, and a 10px
# margin is kept around the mark so nothing antialiased is clipped. Both source
# compositions are 3600x1440 and aligned, so one geometry serves both.
#
# Re-measure if the brand source is ever replaced. A hardcoded crop against art that
# moved would silently shave the mark instead of the slogan.
for variant in "logo-horizontal-transparente wordmark-light-720" \
               "logo-principal-dark-negativa wordmark-dark-720"; do
  src_name=${variant%% *}
  out_name=${variant##* }
  sips -c 737 3245 --cropOffset 140 165 "src/renderer/logo/${src_name}.png" \
    --out "$WORK/${out_name}.png" >/dev/null
  sips -Z 720 "$WORK/${out_name}.png" \
    --out "src/renderer/logo/derived/${out_name}.png" >/dev/null
  echo "src/renderer/logo/derived/${out_name}.png written ($(wc -c < "src/renderer/logo/derived/${out_name}.png") bytes)"
done
