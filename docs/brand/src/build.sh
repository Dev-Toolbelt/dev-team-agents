#!/usr/bin/env bash
# Regenerates the brand illustrations in docs/brand/ (SVG + 2x PNG, EN and pt-BR).
# Requires python3 and rsvg-convert (librsvg). The team sheet reads
# app/src/renderer/assets/agents/agents.json and the avatar SVGs next to it.
# Counts in overview.py and layers.py (agents, commands) are hand-kept: update them when they change.
set -euo pipefail

src="$(cd "$(dirname "$0")" && pwd)"
out="$(dirname "$src")"

python3 "$src/overview.py" en > "$out/dev-team-agents-overview.svg"
python3 "$src/overview.py" pt > "$out/dev-team-agents-visao-geral-pt-BR.svg"
python3 "$src/layers.py" en > "$out/dev-team-agents-layers.svg"
python3 "$src/layers.py" pt > "$out/dev-team-agents-camadas-pt-BR.svg"
python3 "$src/team.py" "$out/dev-team-agents-team.svg" en
python3 "$src/team.py" "$out/dev-team-agents-time-pt-BR.svg" pt-BR

for name in overview visao-geral-pt-BR layers camadas-pt-BR team time-pt-BR; do
  rsvg-convert -z 2 "$out/dev-team-agents-$name.svg" -o "$out/dev-team-agents-$name.png"
done
