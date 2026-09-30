/**
 * Facts about the build, stated rather than implied.
 *
 * `CODE_SIGNED` is `false` and must stay `false` until someone wires real signing. It is
 * a source constant, and greppable, so "is this build signed?" has an answer a reviewer
 * can read in the diff instead of inferring from an electron-builder config.
 *
 * ADR-0011 says macOS artifacts are signed and notarised; its M4.1 amendment records
 * that the app is "blocked on signing credentials the repository owner holds". So this
 * repository can build a `.dmg` and cannot build a shippable one. The UI says so, the
 * build prints it, and `packaging/homebrew/devteam-app.rb`'s `brew audit --cask`
 * codesign check would fail — which is the correct outcome, not a bug to route around.
 */
export const CODE_SIGNED = false;

/**
 * Whether this build exposes any write action at all.
 *
 * `true`: the project lifecycle — bind, unbind, sync, pin, upgrade — and the global
 * skills install/remove are reachable from the UI, alongside `devteam doctor`, which was
 * the one mutating command before it. See
 * `cli/operations.ts` -> `GATED_COMMANDS` for the full list of commands the framework
 * classifies as mutating that this build runs, and why each was admitted rather than
 * filed under read-only.
 */
export const HAS_WRITE_ACTIONS = true;
