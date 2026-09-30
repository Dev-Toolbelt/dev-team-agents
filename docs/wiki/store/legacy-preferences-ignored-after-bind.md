# A v2 preferences.json stops applying the moment a project is bound

**Origin:** noticed while building the desktop app's project settings screen | 2026-09-29
**Tags:** preferences, cascade, v2, user-data, bind, upgrade, collision, quarantine, import, layout 1

> The project preference layer lives in the store on every layout. A `user-data/preferences.json` left in a bound project is read by nothing — not by the cascade, not by agents, not by the app.

---

## What it is

`prefs.project_file()` is `data/projects/<project_id>/preferences.json` whatever `project.json`'s
`layout` says. Layout 1 moves *memory* (session summary, state) into the store only on `devteam
upgrade`, so it is easy to assume the preferences file follows the same rule. It does not: once
`bind` writes `resolved/preferences.json`, the hooks and agents read that projection, which is built
from defaults → global → the store's project layer.

## How it works

- Before 2026-09-29 the v2 file simply stopped applying after a bind, and `devteam upgrade` later
  refused with a collision if anything had been written to the project layer in between (a
  `prefs set --scope project`, or the app's settings screen).
- Since then `bind`/`sync` call `prefs.import_legacy()`: copy the declared, well-typed keys → read
  them back → move the file to quarantine (`imported-preferences`). The project layer wins a conflict.

## Gotchas

- `session-start.sh` backfills `user-data/preferences.json` only when there is **no**
  `resolved/preferences.json` (`devteam_prefs_is_legacy`), so a bound project never gets the file
  recreated after the import. If that guard is ever loosened, a recreated file full of defaults would
  be imported as if the user had chosen them.
- `suppress_notifications` was documented in v2 as "bool or array"; its default is a boolean, so the
  import special-cases the list form (`prefs.BOOL_OR_LIST_KEYS`) instead of discarding it.
