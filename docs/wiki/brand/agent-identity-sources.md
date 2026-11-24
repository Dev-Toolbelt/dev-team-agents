# Agent Identity Sources

**Origin:** brand illustrations regeneration (orchestrator avatar, EN and pt-BR images) | 2026-11-24
**Tags:** agents.json, agent avatar, team sheet, tiers.json, tier and model mirror, brand illustrations, build.sh, rsvg-convert

> Changing an agent's tier, model or count touches three hand-kept places, and the brand images do not update on their own.

---

## What it is
The agent identity shown in the brand images and the desktop app comes from one JSON file and a set of avatar SVGs beside it. The brand generators read these files; nothing reads the agent frontmatter for them.

## How it works
| Source | Read by | Role |
|--------|---------|------|
| `app/src/renderer/assets/agents/agents.json` | `docs/brand/src/team.py`, the app | Agent name, `tier`, `model` per agent |
| `app/src/renderer/assets/agents/<agent>.svg` | `docs/brand/src/team.py`, the app | One avatar per agent, including `orchestrator.svg` |
| `docs/brand/src/overview.py`, `docs/brand/src/layers.py` | `build.sh` | Hardcoded counts (agents, commands, skills) |

Rebuild the images from the repository root:

```bash
bash docs/brand/src/build.sh
```

The script needs `python3` and `rsvg-convert` (librsvg). It writes the SVG and 2x PNG outputs in EN and pt-BR into `docs/brand/`.

## Gotchas
- **Tier and model are copied by hand.** `tier` and `model` in `agents.json` are not synced from `agents/*.md`. A tier or model change must be made in three places that stay in step:
  1. `scripts/lib/tiers.json` (canonical tier to model map)
  2. the agent's frontmatter in `agents/<agent>.md`
  3. the entry in `app/src/renderer/assets/agents/agents.json`
- **Counts are hand-kept.** `overview.py` hardcodes the agent count (19), the command count (43) and the skill count (150+). `layers.py` hardcodes the agent and skill counts. Adding or removing an agent or command means editing those numbers by hand, in both files and in both languages.
- **A new agent needs an avatar.** The team sheet expects `<agent>.svg` beside `agents.json`.

## References
- `docs/brand/src/build.sh`
- `scripts/lib/tiers.json`
- `CLAUDE.md` § Agents (tier and model rules)
