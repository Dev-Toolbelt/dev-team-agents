/**
 * The invocation layer against the **real** CLI in this repository.
 *
 * A fake proves the parser handles the shapes it was told about. Only the real CLI proves
 * the shapes were described correctly — the contract this app pins lives in python, and a
 * fake written from the same reading of it would agree with a misreading.
 *
 * **No real store is touched.** `DEVTEAM_HOME` points at a fresh temp directory for every
 * test, which is the seam `scripts/lib/devteam/paths.py` documents for exactly this. The
 * final test asserts the directory is still empty afterwards, so "read-only commands
 * create nothing" is verified rather than assumed.
 *
 * Skipped, with a reason, when (outside CI; under `CI` a missing CLI or python3 FAILS) `scripts/cli/devteam` or a working python3 is not present —
 * this file must not turn a checkout without python into a red suite. Both halves of that
 * condition are now implemented; see `python3Works` below.
 */

import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { mkdir, mkdtemp, readFile, readdir, realpath, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { invokeDevteam } from '../src/cli/invoke.js';
import { ranAndAnswered } from '../src/cli/contract.js';
import { APP_STORE_SCHEMAS, performHandshake, writeDeclarationFile } from '../src/cli/declaration.js';
import type { StreamEnd } from '../src/cli/stream.js';
import {
  ackNotification,
  applyMigration,
  bindProject,
  catalogSummary,
  doctor,
  listNotifications,
  planMigration,
  installSkill,
  listProjects,
  listTasks,
  listSkills,
  prefsList,
  prefsSet,
  prefsUnset,
  removeSkill,
  setPin,
  showSkill,
  unbindProject,
  watchNotifications,
  watchTasks,
  type TaskWatchEvent,
  type WatchEvent,
} from '../src/cli/operations.js';

/** `app/test/` → the repository root → `scripts/cli/devteam`. */
const REPO_ROOT = fileURLToPath(new URL('../..', import.meta.url));
const REAL_CLI = join(REPO_ROOT, 'scripts', 'cli', 'devteam');

/**
 * The CLI is a python script behind a `#!/usr/bin/env python3` line, so a checkout with no
 * working python3 cannot run it — and the header above promises that case is skipped. It
 * was not: `available` only checked the file existed, so such a checkout got 10 hard
 * failures. The interpreter is proven the way `05-app.sh` proves its node pin: by running
 * it, not by assuming the shebang resolves.
 */
function python3Works(): boolean {
  try {
    const probe = spawnSync('python3', ['-c', 'print(1)'], { stdio: 'ignore', timeout: 10_000 });
    return probe.error === undefined && probe.status === 0;
  } catch {
    return false;
  }
}

const cliPresent = existsSync(REAL_CLI);
const pythonPresent = python3Works();
/**
 * Whether this file's whole approach — spawn `REAL_CLI` directly, `shell: false`, and
 * let the OS resolve its `#!/usr/bin/env python3` shebang — can work on this platform.
 * POSIX honours the shebang; Windows has none, and `REAL_CLI` is an extensionless file
 * (`scripts/cli/devteam`, not `.py`), so there is no PATHEXT or file-association route
 * to it either. `python3Works()` only proves an interpreter exists on `PATH`, not that
 * this file's `spawnSync(REAL_CLI, …)` can start it — the fixture helper `runCliDirectly`
 * hit exactly that gap, failing with `status: null` (a process that never launched) on
 * every call. A packaged Windows CLI would be a real `.exe`, not this checked-out
 * script; ADR-0011 records that shape as still undecided, so there is no Windows
 * equivalent to run this file against yet.
 */
const canSpawnScriptDirectly = process.platform !== 'win32';
const available = cliPresent && pythonPresent && canSpawnScriptDirectly;

let home: string;
/**
 * The directory every invocation is given, as `cwd` and as `--path`.
 *
 * A fresh temp directory rather than `REPO_ROOT`: `project.resolve_root` walks up looking
 * for a `project.json` and then asks `git rev-parse`, so pointing it at this repository
 * would make the answers depend on whether the checkout happens to be bound — the class of
 * defect `CliContext.cwd` exists to remove. A directory the test created can only resolve
 * to what the test put there.
 */
let work: string;

beforeEach(async () => {
  home = await mkdtemp(join(tmpdir(), 'devteam-app-realcli-home-'));
  work = await mkdtemp(join(tmpdir(), 'devteam-app-realcli-work-'));
});

afterEach(async () => {
  await rm(home, { recursive: true, force: true });
  await rm(work, { recursive: true, force: true });
});

function context() {
  return { binary: REAL_CLI, env: { DEVTEAM_HOME: home }, cwd: work };
}

/** The version installed into the throwaway store when a test needs a bound project. */
const STORE_VERSION = '3.0.0';

/** Directories created outside `home`, torn down with it. */
const scratch: string[] = [];

afterEach(async () => {
  await Promise.all(scratch.splice(0).map((path) => rm(path, { recursive: true, force: true })));
});

/**
 * Run the CLI directly, for the *fixture* commands. Deliberately not `invokeDevteam`:
 * `store install` and `bind` are mutating, `COMMAND_SHAPES` refuses both, and that refusal
 * is a guarantee this file must not route around to build a fixture.
 */
function runCliDirectly(...args: string[]): void {
  const result = spawnSync(REAL_CLI, [...args, '--json'], {
    cwd: work,
    env: { ...process.env, DEVTEAM_HOME: home },
    encoding: 'utf8',
    timeout: 60_000,
  });
  if (result.status !== 0) {
    throw new Error(`fixture \`devteam ${args.join(' ')}\` failed (${result.status}): ${result.stderr}${result.stdout}`);
  }
}

/** Install one version into the throwaway store. Idempotent per test. */
let installed = false;

function installStoreVersion(): void {
  if (installed) return;
  runCliDirectly('store', 'install', '--from', REPO_ROOT, '--version', STORE_VERSION);
  installed = true;
}

beforeEach(() => {
  installed = false;
});

/**
 * A real git project, bound by the real CLI, so `list` has a row to return.
 *
 * `bind` needs an active version (it resolves one), so a version is installed from this
 * checkout first. Both land inside temp directories: `DEVTEAM_HOME` for the store, a fresh
 * `mkdtemp` for the project, and the final test in this file asserts the store directory is
 * still empty for the read-only path.
 */
async function bindRealProject(label: string): Promise<string> {
  installStoreVersion();
  const root = await mkdtemp(join(tmpdir(), `devteam-app-realcli-${label}-`));
  scratch.push(root);
  await writeFile(join(root, 'README.md'), `# ${label}\n`, 'utf8');
  const git = (...args: string[]): void => {
    const result = spawnSync('git', args, {
      cwd: root,
      encoding: 'utf8',
      env: {
        ...process.env,
        GIT_AUTHOR_NAME: 't',
        GIT_AUTHOR_EMAIL: 't@e',
        GIT_COMMITTER_NAME: 't',
        GIT_COMMITTER_EMAIL: 't@e',
      },
    });
    if (result.status !== 0) throw new Error(`fixture git ${args.join(' ')} failed: ${result.stderr}`);
  };
  git('init', '-q', '.');
  git('add', '-A');
  git('commit', '-qm', 'init');
  runCliDirectly('bind', root);
  return root;
}

describe.skipIf(!available)('against scripts/cli/devteam', () => {
  it('reads `version --json` and finds the compat block ADR-0011 promises', async () => {
    const result = await invokeDevteam({ ...context(), args: ['version'] });
    expect(result.outcome).toBe('success');
    if (!ranAndAnswered(result)) throw new Error('expected a document');
    if (result.document.kind !== 'payload') throw new Error('expected a payload');
    const compat = result.document.body['compat'] as Record<string, unknown>;
    expect(compat).toBeTypeOf('object');
    expect(compat['json_contract']).toBeTypeOf('number');
    expect(compat['store_schemas']).toBeTypeOf('object');
  });

  it('agrees with the real store_schemas, so the app’s constant is not a guess', async () => {
    const result = await invokeDevteam({ ...context(), args: ['version'] });
    if (!ranAndAnswered(result) || result.document.kind !== 'payload') throw new Error('expected a payload');
    const schemas = (result.document.body['compat'] as Record<string, unknown>)['store_schemas'] as Record<
      string,
      number
    >;
    // The names must match exactly: `compat.unsupported_by` counts an omission as
    // unsupported, so a shape the CLI grows and the app never hears about would silently
    // put this app into read-only — which is the safe direction, and still a bug to catch
    // here rather than in the field.
    expect(Object.keys(schemas).sort()).toEqual(Object.keys(APP_STORE_SCHEMAS).sort());
    // And the app must not be *behind* the store it was written against.
    for (const [name, version] of Object.entries(schemas)) {
      expect(APP_STORE_SCHEMAS[name], `app declares ${name}`).toBe(version);
    }
  });

  it('handshakes as compatible against the store this app was written for', async () => {
    const view = await performHandshake(context());
    expect(view.state).toBe('answered');
    if (view.state !== 'answered') throw new Error('unreachable');
    expect(view.mayWrite).toBe(true);
    expect(view.unsupported).toEqual({});
  });

  it('handshakes as behind, read-only, when the app declares an older shape', async () => {
    // The incompatible half, against the real gate rather than a fake: the declaration is
    // deliberately one behind on `project_layout`.
    const behind = { ...APP_STORE_SCHEMAS, project_layout: 1 };
    const result = await invokeDevteam({
      ...context(),
      args: ['compat', '--client', JSON.stringify(behind)],
    });
    // Exit 1 — a finding. This is the assertion that matters most in this file.
    expect(result.outcome).toBe('findings');
    if (!ranAndAnswered(result) || result.document.kind !== 'payload') throw new Error('expected a payload');
    expect(result.document.body['may_write']).toBe(false);
    expect(result.document.body['unsupported']).toMatchObject({ project_layout: { store: 2, client: 1 } });
  });

  it('is refused with exit 4 on a mutating command when the declaration is behind', async () => {
    // The write gate itself, end to end. `bind` is in `compat.MUTATING`; nothing is
    // written, because the refusal happens before the command runs.
    const declaration = join(home, 'behind.json');
    await writeFile(declaration, JSON.stringify({ ...APP_STORE_SCHEMAS, project_layout: 1 }));
    const result = await invokeDevteam({
      ...context(),
      args: ['bind'],
      declarationFile: declaration,
    });
    if (!ranAndAnswered(result)) throw new Error('expected a document');
    expect(result.outcome).toBe('conflict');
    expect(result.exitCode).toBe(4);
    if (result.document.kind !== 'error') throw new Error('expected an error document');
    expect(result.document.details?.['may_write']).toBe(false);
  });

  it('reads `list --json` on an empty store as a success with no projects', async () => {
    const result = await listProjects(context());
    expect(result.ok).toBe(true);
    if (!result.ok) throw new Error('unreachable');
    expect(result.outcome).toBe('success');
    expect(result.data.projects).toEqual([]);
    expect(result.data.current).toBeNull();
  });

  it('maps a real, non-empty `list --json` row — the mapping no empty store exercises', async () => {
    // Hardcoding `path_exists: false` in the mapper left the whole suite green, because the
    // only `list` in this file ran against an **empty** store: the entire project-row
    // mapping — mode, pin, resolves_to, providers, path_exists — was validated against zero
    // rows. So a row is created here, by the real CLI, and asserted.
    const project = await bindRealProject('kept');

    const result = await listProjects(context());
    if (!result.ok) throw new Error(`expected a payload: ${result.message}`);
    expect(result.data.current).toBe(STORE_VERSION);
    expect(result.data.projects).toHaveLength(1);

    const row = result.data.projects[0];
    if (row === undefined) throw new Error('unreachable');
    // `path` round-trips through `Path.resolve()` in the CLI, so compare the real path.
    // `realpath`: the CLI stores a resolved path, and on macOS `/var` is a symlink to `/private/var`.
    expect(row.path).toBe(await realpath(project));
    expect(row.project_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(row.path_exists).toBe(true);
    expect(row.resolves_to).toBe(STORE_VERSION);
    expect(row.pin).toBeNull();
    expect(row.mode).toBeTypeOf('string');
    expect(row.providers.length).toBeGreaterThan(0);
    // The real CLI resolves the three badge preferences per row; `auto_update` is a consent
    // key, so a project that never opted in reads `false`.
    expect(row.preferences?.auto_update).toBe(false);
    expect(typeof row.preferences?.worktree_active).toBe('boolean');
  });

  it('reports a removed project directory as false, and never as unknown', async () => {
    // The other half of the tri-state, against the real CLI: `false` is a claim the CLI
    // makes, and it must survive the mapping unchanged.
    const project = await bindRealProject('removed');
    await rm(project, { recursive: true, force: true });

    const result = await listProjects(context());
    if (!result.ok) throw new Error(`expected a payload: ${result.message}`);
    expect(result.data.projects[0]?.path_exists).toBe(false);
  });

  it('answers the same from any working directory, because the app names one', async () => {
    // The defect this pins: nothing set `cwd`, so the child inherited the main process's
    // and `catalog --json` returned a real `project_id` from inside a bound project and
    // `null` from elsewhere. Both calls below run against the same store; only the
    // directory differs, and the answer must not.
    const project = await bindRealProject('cwd');
    installStoreVersion();

    const fromWork = await catalogSummary(context());
    const fromProject = await catalogSummary({ ...context(), cwd: project });
    if (!fromWork.ok || !fromProject.ok) throw new Error('expected two payloads');
    // Each call named its own `--path`, so each answer is about the directory it named —
    // which is the point: the answer follows the argument, not the launch location.
    expect(fromWork.data.project_id).toBeNull();
    expect(fromProject.data.project_id).not.toBeNull();
    // And the app's own context always names the same directory, so the app's answer is
    // the same on every launch.
    const again = await catalogSummary(context());
    if (!again.ok) throw new Error('unreachable');
    expect(again.data.project_id).toBe(fromWork.data.project_id);
    expect(again.data.version).toBe(STORE_VERSION);
  });

  it('runs `doctor` with --no-project, so the report does not follow the directory', async () => {
    installStoreVersion();
    const project = await bindRealProject('doctor');

    const fromWork = await doctor(context());
    const fromProject = await doctor({ ...context(), cwd: project });
    if (!fromWork.ok || !fromProject.ok) throw new Error('expected two reports');
    // Without `--no-project` these two differed: `ok` from inside a bound project, `warn`
    // with "… is not a bound project" from anywhere else.
    expect(fromProject.data.status).toBe(fromWork.data.status);
    expect(fromWork.data.findings.some((finding) => finding.category === 'project')).toBe(false);
    expect(fromProject.data.findings.some((finding) => finding.category === 'project')).toBe(false);
  });

  it('reads `doctor --json` as findings — exit 1 with a full report, not an error', async () => {
    const result = await doctor(context());
    expect(result.ok).toBe(true);
    if (!result.ok) throw new Error('unreachable');
    // The store is empty, so doctor has something to say and exits 1.
    expect(result.outcome).toBe('findings');
    expect(result.data.status).toBeTypeOf('string');
    expect(result.data.findings.length).toBeGreaterThan(0);
    expect(result.data.findings.some((finding) => finding.category === 'store')).toBe(true);
  });

  it('reports `catalog` on a store with no version as an environment problem with the CLI’s own hint', async () => {
    const result = await catalogSummary(context());
    expect(result.ok).toBe(false);
    if (result.ok) throw new Error('unreachable');
    expect(result.kind).toBe('environment');
    expect(result.exitCode).toBe(3);
    expect(result.hint).toContain('devteam');
  });

  it('rejects a malformed declaration as exit 2, not as a silent ungated run', async () => {
    const declaration = join(home, 'broken.json');
    await writeFile(declaration, 'not json at all');
    const result = await invokeDevteam({ ...context(), args: ['list'], declarationFile: declaration });
    expect(result.outcome).toBe('usage');
    if (!ranAndAnswered(result)) throw new Error('expected a document');
    expect(result.exitCode).toBe(2);
  });

  it('accepts the declaration file this app writes', async () => {
    const declaration = await writeDeclarationFile(home);
    const result = await invokeDevteam({ ...context(), args: ['list'], declarationFile: declaration });
    expect(result.outcome).toBe('success');
  });

  it('touches no real store: every read-only command leaves DEVTEAM_HOME empty', async () => {
    const before = await readdir(home);
    expect(before).toEqual([]);
    await invokeDevteam({ ...context(), args: ['version'] });
    await invokeDevteam({ ...context(), args: ['compat'] });
    await listProjects(context());
    await doctor(context());
    await catalogSummary(context());
    // `devteam path`, `version`, `compat`, `list`, `doctor` and `catalog` are all in
    // `compat.READ_ONLY` and are asserted there to create nothing — including not minting
    // a machine identity. This is that claim, checked from the client side.
    expect(await readdir(home)).toEqual([]);
  });

  // ── write actions, against the real CLI ────────────────────────────────────────
  //
  // Everything above reads. These bind, unbind and pin a throwaway project inside the
  // same disposable `DEVTEAM_HOME` `beforeEach` creates — never the developer's real
  // store — and prove `cli/operations.ts`'s write functions read the CLI's real shapes,
  // not a fake's approximation of them (`app/test/ipc.test.ts` covers the main-process
  // security properties — offered paths, `project_id` resolution — against a fake CLI;
  // this file is the one place those functions run against the real one).

  it('binds a real project through bindProject(), and reads back the real BindReport shape', async () => {
    installStoreVersion();
    const result = await bindProject(context(), work, {});
    expect(result.ok).toBe(true);
    if (!result.ok) throw new Error(`expected success: ${result.message}`);
    expect(result.outcome).toBe('success');
    expect(result.data.project_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(result.data.path).toBe(await realpath(work));
    expect(result.data.version).toBe(STORE_VERSION);
    expect(result.data.providers.length).toBeGreaterThan(0);
    expect(result.data.identity_created).toBe(true);
    // The argv actually spawned, not a paraphrase of it.
    expect(result.command).toContain(`bind ${work}`);
  });

  it('unbindProject removes the registry entry a real bindProject created', async () => {
    installStoreVersion();
    const bound = await bindProject(context(), work, {});
    if (!bound.ok) throw new Error(`expected a successful bind: ${bound.message}`);

    const result = await unbindProject(context(), bound.data.project_id);
    expect(result.ok).toBe(true);
    if (!result.ok) throw new Error(`expected success: ${result.message}`);
    expect(result.data.project_id).toBe(bound.data.project_id);
    expect(result.command).toContain(`unbind --project-id ${bound.data.project_id}`);

    // The unbind actually took: nothing this project_id names is bound any more.
    const after = await listProjects(context());
    if (!after.ok) throw new Error('unreachable');
    expect(after.data.projects.find((p) => p.project_id === bound.data.project_id)).toBeUndefined();
  });

  it('setPin sets and then releases a real pin, and never sends an empty-string version', async () => {
    installStoreVersion();
    const bound = await bindProject(context(), work, {});
    if (!bound.ok) throw new Error(`expected a successful bind: ${bound.message}`);

    const pinned = await setPin(context(), work, STORE_VERSION);
    expect(pinned.ok).toBe(true);
    if (!pinned.ok) throw new Error(`expected success: ${pinned.message}`);
    expect(pinned.data.pin).toBe(STORE_VERSION);

    const released = await setPin(context(), work, null);
    expect(released.ok).toBe(true);
    if (!released.ok) throw new Error(`expected success: ${released.message}`);
    expect(released.data.pin).toBeNull();
    // `cmd_pin` refuses `pin ''` outright ("pass a version to pin, or --release to
    // clear the pin") — a release that reached the CLI as an empty string would have
    // failed this assertion with a `usage` result, not a successful release.
    expect(released.outcome).toBe('success');
  });

  it('round-trips a project-layer preference: set shows origin project, unset brings the inherited value back', async () => {
    installStoreVersion();
    const bound = await bindProject(context(), work, {});
    if (!bound.ok) throw new Error(`expected a successful bind: ${bound.message}`);

    const before = await prefsList(context(), work);
    if (!before.ok) throw new Error(`expected a payload: ${before.message}`);
    const inherited = before.data.values['session_no_commit_turns'];
    expect(before.data.origin['session_no_commit_turns']).not.toBe('project');

    const set = await prefsSet(context(), work, 'session_no_commit_turns', 13);
    if (!set.ok) throw new Error(`expected success: ${set.message}`);
    expect(set.data).toMatchObject({ key: 'session_no_commit_turns', scope: 'project' });

    const during = await prefsList(context(), work);
    if (!during.ok) throw new Error('unreachable');
    expect(during.data.values['session_no_commit_turns']).toBe(13);
    expect(during.data.origin['session_no_commit_turns']).toBe('project');

    const nulled = await prefsSet(context(), work, 'worktree_base_branch', null);
    if (!nulled.ok) throw new Error(`expected success: ${nulled.message}`);

    const unset = await prefsUnset(context(), work, 'session_no_commit_turns');
    if (!unset.ok) throw new Error(`expected success: ${unset.message}`);
    expect(unset.data.removed).toBe(true);

    const after = await prefsList(context(), work);
    if (!after.ok) throw new Error('unreachable');
    expect(after.data.values['session_no_commit_turns']).toBe(inherited);
    expect(after.data.values['worktree_base_branch']).toBeNull();
  });

  it('migrates a pre-v2.1.0 install end to end: plan, apply with --untrack, the index emptied of the old paths', async () => {
    installStoreVersion();
    const root = await mkdtemp(join(tmpdir(), 'devteam-app-realcli-pre-root-'));
    scratch.push(root);
    const legacy = join(root, '.claude', 'dev-team-agents', 'agents');
    await mkdir(legacy, { recursive: true });
    await writeFile(join(legacy, 'backend-developer.md'), '# agent\n', 'utf8');
    await mkdir(join(root, '.claude', 'user-data'), { recursive: true });
    await writeFile(join(root, '.claude', 'user-data', 'session-summary.md'), '## kept\n', 'utf8');
    const git = (...args: string[]) =>
      spawnSync('git', args, {
        cwd: root,
        encoding: 'utf8',
        env: { ...process.env, GIT_AUTHOR_NAME: 't', GIT_AUTHOR_EMAIL: 't@e', GIT_COMMITTER_NAME: 't', GIT_COMMITTER_EMAIL: 't@e' },
      });
    for (const args of [['init', '-q', '.'], ['add', '-A'], ['commit', '-qm', 'v2.0']]) {
      const result = git(...args);
      if (result.status !== 0) throw new Error(`fixture git ${args.join(' ')} failed: ${result.stderr}`);
    }

    const plan = await planMigration(context(), root, { providers: ['claude'], mode: 'link' });
    if (!plan.ok) throw new Error(`expected a plan: ${plan.message}`);
    expect(plan.data.layout).toBe('pre-root');
    expect(plan.data.git_tracked).toEqual(expect.arrayContaining(['.claude/dev-team-agents/agents', '.claude/user-data']));

    const applied = await applyMigration(context(), root, { providers: ['claude'], mode: 'link' });
    if (!applied.ok) throw new Error(`expected a migration: ${applied.message}`);
    expect(applied.data.untrack_problem).toBeNull();
    expect(applied.data.untracked).toEqual(expect.arrayContaining(['.claude/dev-team-agents/agents', '.claude/user-data']));
    expect(await readFile(join(root, '.dev-team-agents', 'user-data', 'session-summary.md'), 'utf8')).toBe('## kept\n');
    const tracked = git('ls-files', '--', '.claude/dev-team-agents', '.claude/user-data').stdout.trim();
    expect(tracked).toBe('');
    // Nothing was committed: the removals wait in the index for the user.
    expect(git('log', '--oneline').stdout.trim().split('\n')).toHaveLength(1);

    // A directory with no v2 install is exit 2 — the bind dialog's signal to bind instead.
    const fresh = await mkdtemp(join(tmpdir(), 'devteam-app-realcli-fresh-'));
    scratch.push(fresh);
    const notV2 = await planMigration(context(), fresh, {});
    if (notV2.ok) throw new Error('expected no v2 install');
    expect(notV2.exitCode).toBe(2);
  });

  it('binds over a v2 preferences.json, imports it into the project layer and moves the file out', async () => {
    installStoreVersion();
    const legacyDir = join(work, '.dev-team-agents', 'user-data');
    await mkdir(legacyDir, { recursive: true });
    await writeFile(join(legacyDir, 'preferences.json'), JSON.stringify({ session_no_commit_turns: 13 }));

    const bound = await bindProject(context(), work, {});
    if (!bound.ok) throw new Error(`expected a successful bind: ${bound.message}`);
    expect(bound.data.preferences_import?.imported).toEqual(['session_no_commit_turns']);
    expect(bound.data.preferences_import?.problem).toBeNull();
    expect(existsSync(join(legacyDir, 'preferences.json'))).toBe(false);

    const listed = await prefsList(context(), work);
    if (!listed.ok) throw new Error(listed.message);
    expect(listed.data.values['session_no_commit_turns']).toBe(13);
    expect(listed.data.origin['session_no_commit_turns']).toBe('project');
  });

  it('streams a queued notification through the real `watch`, and a real ack marks it seen', async () => {
    installStoreVersion();
    const bound = await bindProject(context(), work, {});
    if (!bound.ok) throw new Error(`expected a successful bind: ${bound.message}`);
    // Where a hook writes: the project's own `state-dir` pointer, exactly as notify.sh reads it.
    const stateDir = (await readFile(join(work, '.dev-team-agents', 'state-dir'), 'utf8')).trim();
    const record = {
      id: '1790000000-4242-1',
      ts: Math.floor(Date.now() / 1000),
      project_id: bound.data.project_id,
      session_id: 's1',
      level: 'critical',
      code: 'context.critical',
      message: 'Context window at ≈65%.',
      dedupe_key: 'context.critical:s1',
      expires_at: 0,
    };
    await writeFile(join(stateDir, 'notifications.jsonl'), `${JSON.stringify(record)}\n`);

    const events: WatchEvent[] = [];
    let finished: (end: StreamEnd) => void = () => undefined;
    const ended = new Promise<StreamEnd>((resolve) => {
      finished = resolve;
    });
    const handle = watchNotifications(context(), {
      onEvent: (event) => events.push(event),
      onInvalid: (detail) => {
        throw new Error(detail);
      },
      onEnd: finished,
    });
    if (handle === null) throw new Error('watch was refused by the allow-list');
    const deadline = Date.now() + 15_000;
    while (!events.some((e) => e.event === 'ready') && Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    handle.stop();
    expect(await ended).toMatchObject({ kind: 'exited', code: 0 });
    const streamed = events.find((e) => e.event === 'notification');
    expect(streamed?.event === 'notification' ? streamed.notification : null).toMatchObject({
      id: record.id,
      level: 'critical',
      projectId: bound.data.project_id,
    });
    expect(events[events.length - 1]).toEqual({ event: 'end', reason: 'stdin-closed' });

    const acked = await ackNotification(context(), record.id);
    if (!acked.ok) throw new Error(`expected an ack: ${acked.message}`);
    expect(acked.data.acknowledged).toEqual([record.id]);
    const listed = await listNotifications(context());
    if (!listed.ok) throw new Error(`expected a list: ${listed.message}`);
    expect(listed.data.map((n) => [n.id, n.seen])).toEqual([[record.id, true]]);
  });

  it('installs, lists, shows and removes a global skill against a throwaway user home, reading the real shapes', async () => {
    const userHome = await mkdtemp(join(tmpdir(), 'devteam-app-realcli-userhome-'));
    scratch.push(userHome);
    const source = join(userHome, 'source', 'demo-skill');
    await mkdir(source, { recursive: true });
    await writeFile(join(source, 'SKILL.md'), '---\nname: demo-skill\ndescription: A demo\n---\n# Demo\n', 'utf8');
    // `DEVTEAM_USER_HOME` is the CLI's own seam for "whose home is this": nothing here can
    // reach the developer's real `~/.claude/skills`.
    const ctx = { ...context(), env: { DEVTEAM_HOME: home, DEVTEAM_USER_HOME: userHome } };

    const installed = await installSkill(ctx, source, { providers: ['claude'], replace: false, link: false });
    if (!installed.ok) throw new Error(`install failed: ${installed.message}`);
    expect(installed.data.name).toBe('demo-skill');
    expect(installed.data.installed[0]?.root).toBe('claude');

    const again = await installSkill(ctx, source, { providers: ['claude'], replace: false, link: false });
    expect(again.ok).toBe(false);
    if (!again.ok) expect(again.kind).toBe('conflict');

    const listed = await listSkills(ctx, 'claude');
    if (!listed.ok) throw new Error(`list failed: ${listed.message}`);
    const record = listed.data.skills.find((each) => each.name === 'demo-skill');
    expect(record).toMatchObject({ root: 'claude', status: 'ok', managed: false, description: 'A demo' });

    const shown = await showSkill(ctx, 'demo-skill', 'claude');
    if (!shown.ok) throw new Error(`show failed: ${shown.message}`);
    expect(shown.data.files).toContain('SKILL.md');
    expect(shown.data.body).toContain('# Demo');

    const removed = await removeSkill(ctx, 'demo-skill', 'claude');
    if (!removed.ok) throw new Error(`remove failed: ${removed.message}`);
    expect(removed.data.action).toBe('quarantined');
    expect(removed.data.quarantined_to).not.toBeNull();
  });

  it('surfaces the exit-4 write gate as OperationResult.kind "conflict", a problem the UI can render', async () => {
    // The end-to-end version of the raw `invokeDevteam` gate test above, through the
    // same layer the app actually calls: `bindProject()`, not a hand-built argv.
    installStoreVersion();
    const declaration = join(home, 'behind.json');
    await writeFile(declaration, JSON.stringify({ ...APP_STORE_SCHEMAS, project_layout: 1 }));
    const result = await bindProject({ ...context(), declarationFile: declaration }, work, {});
    expect(result.ok).toBe(false);
    if (result.ok) throw new Error('unreachable');
    expect(result.kind).toBe('conflict');
    expect(result.exitCode).toBe(4);
    expect(result.message.length).toBeGreaterThan(0);
    expect(result.hint).toBeDefined();
  });
});

const inCI = Boolean(process.env.CI) && process.env.CI !== 'false' && process.env.CI !== '0';

describe.runIf(inCI && (!cliPresent || !pythonPresent))('real CLI required in CI', () => {
  it('fails instead of skipping: the CLI contract gate must not pass vacuously', () => {
    expect(
      { cliPresent, pythonPresent },
      'CI is set, so scripts/cli/devteam and a working python3 are mandatory',
    ).toEqual({ cliPresent: true, pythonPresent: true });
  });
});

describe.skipIf(available)('real CLI unavailable', () => {
  it('is skipped because the CLI, a working python3, or direct script execution is missing, and says which', () => {
    expect(available).toBe(false);
    // Not a bare `false` assertion: the reason is the useful part when a contributor (or
    // a Windows CI leg) sees a block of skipped tests and has to decide whether that is
    // expected.
    if (!cliPresent) expect(existsSync(REAL_CLI)).toBe(false);
    else if (!pythonPresent) expect(pythonPresent).toBe(false);
    else expect(canSpawnScriptDirectly).toBe(false);
  });
});

// ── the task board, end to end: real hooks -> real CLI -> the app's parsers ───────────────

const HOOKS_DIR = join(REPO_ROOT, 'scripts', 'hooks');

/** Drive a hook dispatcher the way a provider does: payload on stdin, cwd = the project. */
function runHook(
  dispatcher: string,
  projectRoot: string,
  payload: Record<string, unknown>,
  okStatuses: number[] = [0],
): void {
  const result = spawnSync('bash', [join(HOOKS_DIR, dispatcher)], {
    cwd: projectRoot,
    env: { ...process.env, DEVTEAM_HOME: home },
    input: JSON.stringify({ cwd: projectRoot, ...payload }),
    encoding: 'utf8',
    timeout: 30_000,
  });
  if (result.status === null || !okStatuses.includes(result.status)) throw new Error(`hook ${dispatcher} exited ${result.status}: ${result.stderr}`);
}

const claudeCreate = (root: string, session: string, id: string, subject: string, extra: Record<string, unknown> = {}) =>
  runHook('post-tool-use.sh', root, {
    session_id: session,
    tool_name: 'TaskCreate',
    tool_input: { subject },
    tool_response: { task: { id } },
    ...extra,
  });
const claudeUpdate = (root: string, session: string, id: string, status: string, extra: Record<string, unknown> = {}) =>
  runHook('post-tool-use.sh', root, {
    session_id: session,
    tool_name: 'TaskUpdate',
    tool_input: { taskId: id, status },
    ...extra,
  });
const todoWrite = (root: string, session: string, todos: Array<[string, string]>, extra: Record<string, unknown> = {}) =>
  runHook('post-tool-use.sh', root, {
    session_id: session,
    tool_name: 'TodoWrite',
    tool_input: { todos: todos.map(([content, status]) => ({ content, status })) },
    ...extra,
  });
const codexPlan = (root: string, session: string, steps: Array<[string, string]>) =>
  runHook('pre-tool-use.sh', root, {
    session_id: session,
    tool_name: 'update_plan',
    tool_input: { plan: steps.map(([step, status]) => ({ step, status })) },
  });
const opencodeTodos = (root: string, session: string, todos: Array<[string, string]>) =>
  runHook('pre-tool-use.sh', root, {
    sessionID: session,
    tool: 'todowrite',
    args: { todos: todos.map(([content, status], i) => ({ id: String(i + 1), content, status })) },
  });

async function boardFixture(): Promise<{ a: string; b: string; c: string }> {
  const a = await bindRealProject('board-a');
  const b = await bindRealProject('board-b');
  const c = await bindRealProject('board-c');
  // A: Claude TaskCreate/TaskUpdate (3), Codex update_plan (5), opencode todowrite (2).
  claudeCreate(a, 'a-claude', '1', 'A one');
  claudeCreate(a, 'a-claude', '2', 'A two');
  claudeCreate(a, 'a-claude', '3', 'A three');
  claudeUpdate(a, 'a-claude', '1', 'completed');
  claudeUpdate(a, 'a-claude', '2', 'in_progress');
  codexPlan(a, 'a-codex', [
    ['c1', 'completed'], ['c2', 'completed'], ['c3', 'in_progress'], ['c4', 'pending'], ['c5', 'pending'],
  ]);
  opencodeTodos(a, 'a-opencode', [['o1', 'completed'], ['o2', 'pending']]);
  // B: Claude TodoWrite (3) and opencode todowrite (2).
  todoWrite(b, 'b-claude', [['b1', 'completed'], ['b2', 'in_progress'], ['b3', 'pending']]);
  opencodeTodos(b, 'b-opencode', [['p1', 'pending'], ['p2', 'pending']]);
  return { a, b, c };
}

const boardContext = () => context();

async function board() {
  const listed = await listTasks(boardContext(), { staleAfterSeconds: 3600 });
  if (!listed.ok) throw new Error(`tasks list failed: ${listed.message}`);
  return listed.data.projects;
}

describe.skipIf(!available)('task board against the real hooks and CLI', () => {
  it('keeps a resume command whose session cwd holds a space and a single quote, exactly as the CLI quoted it', async () => {
    const root = await bindRealProject('board-quote');
    const awkward = join(root, "it's a dir");
    await mkdir(awkward, { recursive: true });
    claudeCreate(root, 'quote-session', '1', 'quoted', { cwd: awkward });
    const projects = await board();
    const rootReal = await realpath(root);
    let session;
    for (const project of projects) {
      if ((await realpath(project.root)) === rootReal) session = project.sessions.find((each) => each.session_id === 'quote-session');
    }
    expect(session, 'the session was recorded').toBeDefined();
    expect(session?.resume_command).not.toBeNull();

    // The CLI's own quoting, asked of python's shlex with the directory it recorded.
    const recorded = session?.cwd ?? '';
    expect(recorded).toContain("it's a dir");
    const quoted = spawnSync('python3', ['-c', 'import shlex,sys; print(shlex.quote(sys.argv[1]))', recorded], { encoding: 'utf8' });
    expect(session?.resume_command).toBe(`cd ${quoted.stdout.trim()} && claude --resume quote-session`);
  }, 120_000);

  it('lists exactly the projects with tasks, with counts, providers, durations and resume commands', async () => {
    const { a, b, c } = await boardFixture();
    const projects = await board();

    const roots = await Promise.all([a, b, c].map((p) => realpath(p)));
    const byRoot = new Map(await Promise.all(projects.map(async (p) => [await realpath(p.root), p] as const)));
    expect([...byRoot.keys()].sort()).toEqual([roots[0], roots[1]].sort());
    expect(byRoot.has(roots[2] as string)).toBe(false);

    const pa = byRoot.get(roots[0] as string)!;
    const pb = byRoot.get(roots[1] as string)!;
    expect(pa.counts).toEqual({ todo: 4, in_progress: 2, in_review: 0, done: 4, total: 10 });
    expect(pb.counts).toEqual({ todo: 3, in_progress: 1, in_review: 0, done: 1, total: 5 });
    expect([pa.sessions_total, pb.sessions_total]).toEqual([3, 2]);
    expect([...pa.providers].sort()).toEqual(['claude', 'codex', 'opencode']);
    expect([...pb.providers].sort()).toEqual(['claude', 'opencode']);

    const sizes = (p: (typeof projects)[number]) => p.sessions.map((s) => s.tasks.length).sort();
    expect(sizes(pa)).toEqual([2, 3, 5]);
    expect(sizes(pb)).toEqual([2, 3]);

    const resume = { claude: 'claude --resume', codex: 'codex resume', opencode: 'opencode --session' } as const;
    for (const project of projects) {
      for (const session of project.sessions) {
        // Nothing silently nulled by the app's RESUME_COMMAND regex or session parser.
        expect(session.resume_command, `${session.session_id} resume`).not.toBeNull();
        expect(session.resume_command).toContain(`${resume[session.provider as keyof typeof resume]} ${session.session_id}`);
        expect(session.resume_command?.startsWith('cd ')).toBe(true);
        expect(session.counts.total).toBe(session.tasks.length);
        for (const task of session.tasks) {
          expect(Object.keys(task.durations).length, `${task.key} durations`).toBeGreaterThan(0);
          expect(task.content.length).toBeGreaterThan(0);
        }
      }
    }
  }, 120_000);

  it('scopes tasks to their owner: a subagent never overwrites the main list', async () => {
    const a = await bindRealProject('board-owner');
    todoWrite(a, 's-own', [['main one', 'pending'], ['main two', 'in_progress']]);
    todoWrite(a, 's-own', [['sub one', 'in_progress']], { agent_id: 'sub-1', agent_type: 'Explore' });
    // A second replace by main must leave the subagent's task alone, and vice versa.
    todoWrite(a, 's-own', [['main one', 'completed'], ['main two', 'in_progress']]);

    const [project] = await board();
    const tasks = project!.sessions[0]!.tasks;
    expect(tasks).toHaveLength(3);
    const subTasks = tasks.filter((t) => t.owner === 'sub-1');
    expect(subTasks.map((t) => [t.content, t.agent_type, t.column])).toEqual([['sub one', 'Explore', 'in_progress']]);
    const mainTasks = tasks.filter((t) => t.owner === 'main');
    expect(mainTasks.map((t) => [t.content, t.column]).sort()).toEqual([
      ['main one', 'done'],
      ['main two', 'in_progress'],
    ]);
  }, 60_000);

  it('abandons open tasks on session end and raises one tasks.session_abandoned', async () => {
    const a = await bindRealProject('board-end');
    claudeCreate(a, 's-end', '1', 'left open');
    claudeCreate(a, 's-end', '2', 'done one');
    claudeUpdate(a, 's-end', '2', 'completed');
    runHook('session-end.sh', a, { session_id: 's-end', hook_event_name: 'SessionEnd' });

    const [project] = await board();
    const session = project!.sessions[0]!;
    expect(session.status).toBe('ended');
    expect(session.tasks.find((t) => t.content === 'left open')?.abandoned).toBe(true);
    expect(session.tasks.find((t) => t.content === 'done one')?.abandoned).toBe(false);
    expect(project!.abandoned).toBe(1);

    const notes = await listNotifications(context());
    if (!notes.ok) throw new Error(notes.message);
    const abandoned = notes.data.filter((n) => n.code === 'tasks.session_abandoned');
    expect(abandoned).toHaveLength(1);
    expect(abandoned[0]).toMatchObject({ sessionId: 's-end', level: 'warning' });
    expect(abandoned[0]?.message).toContain('1');
  }, 60_000);

  it('raises exactly one tasks.session_done when every task completes, even if repeated', async () => {
    const a = await bindRealProject('board-done');
    claudeCreate(a, 's-done', '1', 'first');
    claudeCreate(a, 's-done', '2', 'second');
    claudeUpdate(a, 's-done', '1', 'completed');
    claudeUpdate(a, 's-done', '2', 'completed');
    claudeUpdate(a, 's-done', '2', 'completed');

    const notes = await listNotifications(context());
    if (!notes.ok) throw new Error(notes.message);
    const done = notes.data.filter((n) => n.code === 'tasks.session_done');
    expect(done).toHaveLength(1);
    expect(done[0]).toMatchObject({ sessionId: 's-done', level: 'info' });
    expect(notes.data.filter((n) => n.code === 'tasks.session_abandoned')).toHaveLength(0);

    runHook('session-end.sh', a, { session_id: 's-done' });
    const after = await listNotifications(context());
    if (!after.ok) throw new Error(after.message);
    expect(after.data.filter((n) => n.code === 'tasks.session_abandoned')).toHaveLength(0);
  }, 60_000);

  it('watches: backlog snapshot, then ready, then a new snapshot after a hook call', async () => {
    const a = await bindRealProject('board-watch');
    claudeCreate(a, 's-watch', '1', 'before watch');

    const events: TaskWatchEvent[] = [];
    let finished: (end: StreamEnd) => void = () => undefined;
    const ended = new Promise<StreamEnd>((resolve) => {
      finished = resolve;
    });
    const invalid: string[] = [];
    const handle = watchTasks(
      context(),
      { staleAfterSeconds: 3600 },
      { onEvent: (e) => events.push(e), onInvalid: (d) => invalid.push(d), onEnd: finished },
    );
    if (handle === null) throw new Error('watch was refused by the allow-list');
    const until = async (predicate: () => boolean): Promise<void> => {
      const deadline = Date.now() + 20_000;
      while (!predicate() && Date.now() < deadline) await new Promise((r) => setTimeout(r, 50));
    };
    try {
      await until(() => events.some((e) => e.event === 'ready'));
      const readyAt = events.findIndex((e) => e.event === 'ready');
      expect(readyAt).toBeGreaterThan(0);
      const backlog = events[0];
      expect(backlog?.event).toBe('snapshot');
      if (backlog?.event !== 'snapshot') throw new Error('unreachable');
      expect(backlog.project.counts.total).toBe(1);

      claudeCreate(a, 's-watch', '2', 'after watch');
      await until(() => events.slice(readyAt + 1).some((e) => e.event === 'snapshot'));
      const live = events.slice(readyAt + 1).find((e) => e.event === 'snapshot');
      if (live?.event !== 'snapshot') throw new Error('no live snapshot arrived');
      expect(live.project.counts.total).toBe(2);
      expect(live.project.sessions[0]?.resume_command).not.toBeNull();
      expect(invalid).toEqual([]);
    } finally {
      handle.stop();
    }
    expect(await ended).toMatchObject({ kind: 'exited', code: 0 });
  }, 90_000);
});

// ── the In Review column, end to end: real hooks -> real CLI -> listTasks ────────────────

const reviewMarker = (n: number) => `Report.\n<!-- review-result: findings=${n} -->`;
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const spawnReviewer = (root: string, session: string, extra: Record<string, unknown> = {}, toolInput: Record<string, unknown> = {}) =>
  runHook('pre-tool-use.sh', root, {
    session_id: session,
    hook_event_name: 'PreToolUse',
    tool_name: 'Agent',
    tool_input: { description: 'qa', prompt: 'validate', subagent_type: 'qa-specialist', ...toolInput },
    ...extra,
  });
const reviewerReturns = (root: string, session: string, response: unknown, extra: Record<string, unknown> = {}, toolInput: Record<string, unknown> = {}) =>
  runHook('post-tool-use.sh', root, {
    session_id: session,
    hook_event_name: 'PostToolUse',
    tool_name: 'Agent',
    tool_input: { description: 'qa', prompt: 'validate', subagent_type: 'qa-specialist', ...toolInput },
    tool_response: response,
    ...extra,
  });
const textResponse = (text: string) => ({ content: [{ type: 'text', text }] });
const stopHook = (root: string, session: string, extra: Record<string, unknown> = {}) =>
  // The Stop dispatcher exits 2 when its session-summary sub-script blocks; the board still ran.
  runHook('stop.sh', root, { session_id: session, hook_event_name: 'Stop', ...extra }, [0, 2]);

async function newTranscript(lines: unknown[]): Promise<string> {
  const dir = await mkdtemp(join(tmpdir(), 'devteam-transcript-'));
  scratch.push(dir);
  const path = join(dir, 'session.jsonl');
  await writeFile(path, lines.map((l) => `${JSON.stringify(l)}\n`).join(''));
  return path;
}

async function sessionTasks(id: string) {
  const projects = await board();
  const session = projects.flatMap((p) => p.sessions).find((s) => s.session_id === id);
  if (!session) throw new Error(`session ${id} not on the board`);
  return session;
}
const columnsOf = (tasks: readonly { content: string; column: string }[]) =>
  Object.fromEntries(tasks.map((t) => [t.content, t.column]));

async function reviewNotifications(session: string) {
  const notes = await listNotifications(context());
  if (!notes.ok) throw new Error(notes.message);
  return notes.data.filter((n) => n.code === 'tasks.review_findings' && n.sessionId === session);
}

describe.skipIf(!available)('the In Review column against the real hooks and CLI', () => {
  const threeCompleted = (root: string, session: string) => {
    for (const id of ['1', '2', '3']) claudeCreate(root, session, id, `task ${id}`);
    for (const id of ['1', '2', '3']) claudeUpdate(root, session, id, 'completed');
  };

  it('(a) a QA spawn moves three completed tasks to In Review, and findings=0 releases them to Done', async () => {
    const root = await bindRealProject('review-pass');
    threeCompleted(root, 's-pass');
    spawnReviewer(root, 's-pass');

    const during = await sessionTasks('s-pass');
    expect(Object.values(columnsOf(during.tasks))).toEqual(['in_review', 'in_review', 'in_review']);
    expect(during.tasks.every((t) => t.review?.state === 'pending')).toBe(true);
    expect(during.counts.in_review).toBe(3);

    await sleep(1_100); // a review window of at least one whole second
    reviewerReturns(root, 's-pass', textResponse(reviewMarker(0)));
    const after = await sessionTasks('s-pass');
    expect(Object.values(columnsOf(after.tasks))).toEqual(['done', 'done', 'done']);
    for (const task of after.tasks) {
      expect(task.review).toBeNull();
      expect(Number.isInteger(task.durations['in_review'])).toBe(true);
      expect(task.durations['in_review']).toBeGreaterThanOrEqual(1);
    }
    expect(after.counts.in_review).toBe(0);
    expect(await reviewNotifications('s-pass')).toHaveLength(0);
  }, 90_000);

  it('(b) findings=2 keeps the tasks In Review with a notification until two fix tasks are done', async () => {
    const root = await bindRealProject('review-findings');
    threeCompleted(root, 's-find');
    spawnReviewer(root, 's-find');
    reviewerReturns(root, 's-find', textResponse(reviewMarker(2)));

    const held = await sessionTasks('s-find');
    expect(Object.values(columnsOf(held.tasks))).toEqual(['in_review', 'in_review', 'in_review']);
    for (const task of held.tasks) expect(task.review).toMatchObject({ state: 'findings', findings: 2 });
    const notes = await reviewNotifications('s-find');
    expect(notes).toHaveLength(1);
    expect(notes[0]).toMatchObject({ level: 'warning' });

    await sleep(1_100); // the fix rule compares created_at strictly after the result second
    claudeCreate(root, 's-find', '4', 'fix one');
    claudeCreate(root, 's-find', '5', 'fix two');
    claudeUpdate(root, 's-find', '4', 'completed');
    const half = await sessionTasks('s-find');
    expect(columnsOf(half.tasks)['task 1']).toBe('in_review');
    claudeUpdate(root, 's-find', '5', 'completed');

    const fixed = await sessionTasks('s-find');
    expect(Object.values(columnsOf(fixed.tasks))).toEqual(['done', 'done', 'done', 'done', 'done']);
  }, 90_000);

  it('(c) a task that never met a review goes in progress to Done, never through In Review', async () => {
    const root = await bindRealProject('review-none');
    claudeCreate(root, 's-plain', '1', 'plain');
    claudeUpdate(root, 's-plain', '1', 'in_progress');
    expect(columnsOf((await sessionTasks('s-plain')).tasks)).toEqual({ plain: 'in_progress' });
    claudeUpdate(root, 's-plain', '1', 'completed');
    const session = await sessionTasks('s-plain');
    expect(columnsOf(session.tasks)).toEqual({ plain: 'done' });
    expect(session.tasks[0]?.review).toBeNull();
    expect(session.counts.in_review).toBe(0);
  }, 60_000);

  it('(d) /devteam:review with no marker at Stop leaves the result unread', async () => {
    const root = await bindRealProject('review-unread');
    claudeCreate(root, 's-unread', '1', 'work');
    claudeUpdate(root, 's-unread', '1', 'in_progress');
    claudeCreate(root, 's-unread', '2', 'finished');
    claudeUpdate(root, 's-unread', '2', 'completed');
    runHook('user-prompt-submit.sh', root, { session_id: 's-unread', hook_event_name: 'UserPromptSubmit', prompt: '/devteam:review' });
    expect(columnsOf((await sessionTasks('s-unread')).tasks)).toEqual({ work: 'in_review', finished: 'in_review' });

    const transcript = await newTranscript([
      { type: 'user', message: { role: 'user', content: '/devteam:review' } },
      { type: 'assistant', message: { role: 'assistant', content: [{ type: 'text', text: 'Looks fine to me.' }] } },
    ]);
    stopHook(root, 's-unread', { transcript_path: transcript });
    const session = await sessionTasks('s-unread');
    expect(session.tasks.map((t) => t.review?.state)).toEqual(['unread', 'unread']);
    expect(session.tasks.every((t) => t.column === 'in_review')).toBe(true);
  }, 60_000);

  it('(e) a background reviewer stays pending on its launch ack and reports through the transcript', async () => {
    const root = await bindRealProject('review-background');
    threeCompleted(root, 's-bg');
    const transcript = await newTranscript([{ type: 'user', message: { role: 'user', content: 'run qa' } }]);
    const background = { run_in_background: true };
    spawnReviewer(root, 's-bg', { tool_use_id: 'toolu_bg1', transcript_path: transcript }, background);
    reviewerReturns(
      root,
      's-bg',
      { isAsync: true, status: 'async_launched', agentId: 'a1' },
      { tool_use_id: 'toolu_bg1', transcript_path: transcript },
      background,
    );
    stopHook(root, 's-bg', { transcript_path: transcript });
    const waiting = await sessionTasks('s-bg');
    expect(waiting.tasks.every((t) => t.review?.state === 'pending' && t.column === 'in_review')).toBe(true);

    const body = [
      '<task-notification>',
      '<task-id>a1</task-id>',
      '<tool-use-id>toolu_bg1</tool-use-id>',
      '<status>completed</status>',
      '<summary>Agent "qa" finished</summary>',
      `<result>${reviewMarker(2)}</result>`,
      '</task-notification>',
    ].join('\n');
    const stamp = new Date(Date.now() + 1_000).toISOString();
    const { appendFile } = await import('node:fs/promises');
    await appendFile(
      transcript,
      [
        { type: 'queue-operation', operation: 'enqueue', timestamp: stamp, content: body },
        { type: 'user', timestamp: stamp, message: { role: 'user', content: body } },
      ].map((l) => `${JSON.stringify(l)}\n`).join(''),
    );
    stopHook(root, 's-bg', { transcript_path: transcript });
    stopHook(root, 's-bg', { transcript_path: transcript });

    const done = await sessionTasks('s-bg');
    for (const task of done.tasks) expect(task.review).toMatchObject({ state: 'findings', findings: 2 });
    expect(await reviewNotifications('s-bg')).toHaveLength(1);
  }, 90_000);
});
