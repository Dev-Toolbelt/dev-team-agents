# ADR-0021: Project folders are an app-local tree capped by a depth limit

**Date:** 2026-09-30
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

With more than a handful of bound projects, the desktop app's Projects screen becomes a flat list
that is hard to scan. Users want to group projects the way they think of them — sites, online
stores, apps — move them between groups by drag and drop, and act on several at once.

Two questions needed deciding:

- **Where the grouping lives.** [ADR-0016](0016-the-project-display-name-is-app-local-and-never-reaches-the-cli.md)
  already answered this for a display name: a label that configures nothing and identifies nothing
  belongs to the client that shows it, not to the framework. A folder is the same kind of record — it
  exists so a person can find a row — and [ADR-0015](0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md)
  forbids the app from writing into the store except through CLI commands.
- **How deep folders go.** One level covers the request. Subfolders are a plausible next step, and
  a flat `project → group name` map would make that step a format migration.

## Decision

**Folders are the app's own record, stored as a tree, with depth limited by a constant.**

1. **Storage.** `projectFolders` in the app's `settings.json`, written through the same serialized,
   atomic `writeSettings` as every other field, which already refuses to overwrite a file it could
   not read. No CLI flag, no `project.json` key, no `--json` field.
2. **Shape.** `{ folders: [{ id, name, parentId, collapsed }], membership: { project_id → folder id } }`.
   Membership is separate from the folders, so a project is in at most one folder and deleting a
   folder can never delete a project: its projects and subfolders move up to its parent — the top
   level today, which reads as "No folder".
3. **Depth.** `MAX_FOLDER_DEPTH` in `app/src/shared/projectFolders.ts` is `1`. Every function in that
   module walks the tree without assuming a depth. The write validator `projectFoldersProblem`
   refuses anything deeper, and the read-side `normalizeProjectFolders` lifts a too-deep folder to
   the deepest allowed level instead of dropping it — so a file written by a future app that allows
   subfolders still opens in this one with every project filed. Whatever the reader produces, the
   validator accepts, which the tests assert over adversarial input.
4. **One module, both sides.** The model lives in `app/src/shared/`, so the renderer applies changes
   optimistically with the same transforms the main process validates. A refused or failed save
   restores the last accepted state and tells the user; a change queued behind the failed one is
   dropped, not saved on top of it, and counted in the message. The main process writes a copy
   rebuilt from the model's fields, never the renderer's object, and caps names, membership and
   project ids so the file cannot grow without limit. **A failed read is not "no folders"**: until
   the stored state has been read, every folder change is blocked, so a transient read error can
   never be saved over the real grouping.
5. **Drag and drop is never the only path.** Every move is also available from a row's folder menu
   and from the bulk-action bar, both keyboard reachable. The drag handle is hidden from assistive
   technology for that reason.

## Consequences

### Positive
- No change to the CLI's public surface or the store; nothing in `tests/test_json_contract.py` moves.
- Subfolders are a constant change plus a UI entry point (`canNestIn` already gates "New subfolder").
- Losing or corrupting the folder record costs a grouping, never a binding: the screen falls back to
  every project in "No folder".

### Negative
- Folders are per machine and per client, with the same limits ADR-0016 records for names: they do
  not survive a fresh install on another machine, and the CLI and other clients do not see them.
- Membership keyed by `project_id` can outlive an unbind. The screen prunes it on the next successful
  listing, which is a write the user did not ask for.

### Neutral
- Folder names are unique among siblings, compared case-insensitively, and siblings are shown sorted
  by name. Manual ordering is not modelled; adding it would mean a new `order` field.

## Risks

| Risk | Mitigation |
|------|------------|
| A newer app writes subfolders and an older app rewrites the file flattened | The older app lifts, never drops; the grouping degrades one level and every project stays filed |
| Bulk sync over many projects contends for the store lock | Syncs run one after another, never in parallel, and each failure is named in the summary |

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| A `group` string per project | The simplest shape for one level, and a format migration the day subfolders are wanted |
| Folders in the store, written through a new CLI command | Makes grouping visible to every client, and makes a presentation choice part of the framework's contract — the same trade ADR-0016 declined for names |
| A drag-and-drop library | Native HTML5 drag and drop plus the menu path covers the need with no new dependency in `app/` |
