# Third-Party Skills

Skills written and maintained outside this repository, vendored unchanged so the framework's agents can use them on every provider. Decision record: [ADR-0047](../../docs/development/adrs/0047-third-party-skills-are-vendored-apart-from-the-framework-s-own-and-pinned-by-commit-and-content-hash.md).

| Skill | Upstream | License | Attribution |
|---|---|---|---|
| `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | MIT | `ui-ux-pro-max/LICENSE` |
| `impeccable` | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | Apache-2.0 | `impeccable/LICENSE`, `impeccable/NOTICE.md` |
| `emil-design-eng` | [emilkowalski/skills](https://github.com/emilkowalski/skills) | MIT | `emil-design-eng/LICENSE` |

The pinned commit, upstream path and content hash of each one are in `sources.json`.

## Rules

- **Never edit a vendored folder.** Each one must match the hash recorded in `sources.json`; a local change belongs upstream or in your project's own skills.
- `impeccable` ships as instructions only: its launcher and the engine binary it downloads are deliberately left out.
- Agents load these skills through `skills/design/third-party-design-skills/SKILL.md`, which also limits what their scripts may run.
