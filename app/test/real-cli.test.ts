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
 * Skipped, with a reason, when `scripts/cli/devteam` or a working python3 is not present —
 * this file must not turn a checkout without python into a red suite. Both halves of that
 * condition are now implemented; see `python3Works` below.
 */

import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readdir, realpath, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { invokeDevteam } from '../src/cli/invoke.js';
import { ranAndAnswered } from '../src/cli/contract.js';
import { APP_STORE_SCHEMAS, performHandshake, writeDeclarationFile } from '../src/cli/declaration.js';
import { catalogSummary, doctor, listProjects } from '../src/cli/operations.js';

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
const available = cliPresent && pythonPresent;

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
});

describe.skipIf(available)('real CLI unavailable', () => {
  it('is skipped because the CLI or a working python3 is missing, and says which', () => {
    expect(available).toBe(false);
    // Not a bare `false` assertion: the reason is the useful part when a contributor sees
    // ten skipped tests and has to decide whether that is expected.
    expect(cliPresent && pythonPresent).toBe(false);
    if (!cliPresent) expect(existsSync(REAL_CLI)).toBe(false);
    else expect(pythonPresent).toBe(false);
  });
});
