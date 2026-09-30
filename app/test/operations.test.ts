/**
 * The named operations: their validation, and — since this build's write actions
 * landed — the argv each one builds and the payload each one reads back.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

import {
  ALLOWED_COMMANDS,
  COMMAND_SHAPES,
  GATED_COMMANDS,
  READ_ONLY_COMMANDS,
  argvProblem,
  validateEntryName,
  applyUpgrade,
  asBindReport,
  asPinReport,
  asSyncAllReport,
  asSkillDetail,
  asSkillInstallReport,
  asSkillList,
  asSkillRemoveReport,
  installSkill,
  listSkills,
  removeSkill,
  showSkill,
  asUnbindReport,
  asUpgradePlan,
  asUpgradeReport,
  bindProject,
  catalogEntry,
  catalogListing,
  listProjects,
  planUpgrade,
  run,
  setPin,
  prefsList,
  prefsSet,
  prefsUnset,
  asProjectPreferences,
  asPreferenceWrite,
  syncAllProjects,
  syncProject,
  unbindProject,
} from '../src/cli/operations.js';
import { scanTopLevelJson, parseSingleDocument } from '../src/cli/parse.js';
import type { CliContext } from '../src/cli/operations.js';
import type { PreferenceValue } from '../src/shared/api.js';
import { readLauncherManifest, resolveFixtureBinary } from './fixtures/launcher-manifest.js';

/** A copy of `body` with `key` dropped, for the "missing required key" validator tests. */
function omit(body: Record<string, unknown>, key: string): Record<string, unknown> {
  const copy = { ...body };
  delete copy[key];
  return copy;
}

const FAKE = fileURLToPath(new URL('./fixtures/fake-devteam.mjs', import.meta.url));
const REPO_ROOT = fileURLToPath(new URL('../..', import.meta.url));

/** A context whose binary does not exist, so a spawn is unmistakable in the result. */
function unspawnable(): CliContext {
  return { binary: join(REPO_ROOT, 'no-such-devteam-binary'), cwd: REPO_ROOT };
}

/**
 * `fakeContext()` hands `CliContext.binary` straight to `invokeDevteam`, which spawns it
 * with `shell: false` — the same policy `invoke.ts` documents for the real CLI. `FAKE` is
 * a `.mjs` script; POSIX runs it via its shebang, but Windows has no shebang support and
 * no association for `.mjs`, so the spawn cannot start it at all. Unlike
 * `invoke.test.ts`'s `run()`, this file cannot route around that by handing `node` the
 * script path as an argument: `operations.ts` itself decides the argv (`bind`, `list`, …)
 * from `context.binary` onward, so there is no seam here to insert an interpreter ahead
 * of the subcommand without changing production code for a test's sake. `FAKE_BINARY` is
 * the compiled launcher `launcher-global-setup.ts` built instead, on Windows, when one
 * built successfully; `launcherAvailable` says whether it did, and gates every
 * `it.skipIf` below.
 */
const { binary: FAKE_BINARY, available: launcherAvailable } = resolveFixtureBinary(
  FAKE,
  readLauncherManifest()?.fakeDevteam,
);

function fakeContext(scenario = 'ok'): CliContext {
  return { binary: FAKE_BINARY, cwd: REPO_ROOT, env: { FAKE_DEVTEAM_SCENARIO: scenario } };
}

const skipOnWindows = process.platform === 'win32';
const skipOnWindowsWithoutLauncher = skipOnWindows && !launcherAvailable;

/**
 * `source.indexOf(marker)`, except a missing marker throws instead of returning -1.
 *
 * This is the strongest cross-language guard in the repository — it fails a JS test
 * when a Python table is renamed — so it must not have a silent-failure mode. An
 * unchecked `-1` from a renamed marker turns `slice(x, -1)` into "the rest of the
 * file", and every subsequent `.toContain(tuple)` check on that slice can then pass by
 * accident for a tuple that merely appears somewhere later on, not because it is in
 * the table being asserted about.
 */
function markerIndex(source: string, marker: string, file: string): number {
  const index = source.indexOf(marker);
  if (index === -1) {
    throw new Error(`expected to find the marker ${JSON.stringify(marker)} in ${file}, but it is not there`);
  }
  return index;
}

/**
 * The classification tables, read out of `compat.py` rather than restated here. A command
 * moved between them in the framework has to fail this test — which is the whole reason to
 * parse the source file instead of keeping a copy of the answer.
 */
function classificationTables() {
  const file = join(REPO_ROOT, 'scripts', 'lib', 'devteam', 'compat.py');
  const source = readFileSync(file, 'utf8');
  const mutatingStart = markerIndex(source, 'MUTATING = {', file);
  const readOnlyStart = markerIndex(source, 'READ_ONLY = {', file);
  const needsMachineLayoutStart = markerIndex(source, 'NEEDS_MACHINE_LAYOUT = {', file);
  return {
    mutating: source.slice(mutatingStart, readOnlyStart),
    readOnly: source.slice(readOnlyStart, needsMachineLayoutStart),
  };
}

function tupleLiteral(command: readonly string[]): string {
  const key = command.map((part) => `"${part}"`).join(', ');
  return command.length === 1 ? `(${key},)` : `(${key})`;
}

describe('what this slice is allowed to run', () => {
  it('keeps every READ_ONLY_COMMANDS entry in compat.READ_ONLY and out of compat.MUTATING', () => {
    const { mutating, readOnly } = classificationTables();
    for (const command of READ_ONLY_COMMANDS) {
      const tuple = tupleLiteral(command);
      expect(readOnly, `${command.join(' ')} should be in compat.READ_ONLY`).toContain(tuple);
      expect(mutating, `${command.join(' ')} must not be in compat.MUTATING`).not.toContain(tuple);
    }
  });

  it('gates exactly the project lifecycle plus `doctor`, and every one is `compat.MUTATING`', () => {
    // The tension the brief left open for `doctor` alone: the slice was specified
    // read-only and the diagnosis screen is `devteam doctor`, which `compat.MUTATING`
    // lists because it repairs what it finds. The same tension now applies to the five
    // project-lifecycle commands the write actions added — each one must be admitted
    // here rather than reclassified as read-only to dodge the gate.
    const { mutating, readOnly } = classificationTables();
    expect(GATED_COMMANDS.map((command) => command.join(' '))).toEqual([
      'doctor',
      'bind',
      'unbind',
      'sync',
      'pin',
      'upgrade',
      'prefs set',
      'prefs unset',
      'plugin enable',
      'plugin disable',
      'plugin config set',
      'plugin config unset',
      'plugin run',
      // Acknowledging a notification writes that project's seen marks — admitted as a
      // write rather than dressed up as a read.
      'notifications ack',
      'skills install',
      'skills remove',
    ]);
    for (const command of GATED_COMMANDS) {
      const tuple = tupleLiteral(command);
      expect(mutating, `${command.join(' ')} should be in compat.MUTATING`).toContain(tuple);
      expect(readOnly, `${command.join(' ')} must not be in compat.READ_ONLY`).not.toContain(tuple);
    }
  });

  it('runs nothing the framework has not classified at all', () => {
    const { mutating, readOnly } = classificationTables();
    for (const command of ALLOWED_COMMANDS) {
      const tuple = tupleLiteral(command);
      expect(
        readOnly.includes(tuple) || mutating.includes(tuple),
        `${command.join(' ')} is in neither compat table — is_mutating() fails closed on it`,
      ).toBe(true);
    }
  });

  it('never passes --reassign-identity, the one doctor flag that rewrites identity', () => {
    const source = readFileSync(
      fileURLToPath(new URL('../src/cli/operations.ts', import.meta.url)),
      'utf8',
    );
    // Only the comment explaining the rule may mention it; no argument vector may.
    expect(source).not.toContain("'--reassign-identity'");
  });

  it('never runs `cred get` — a value must not enter this app', () => {
    // ADR-0010: `cred get` refuses `--json` by design, and a secret must not reach the
    // app's memory, its logs or its renderer. The app shows references only.
    const flat = ALLOWED_COMMANDS.map((command) => command.join(' '));
    expect(flat).not.toContain('cred get');
    expect(flat.some((command) => command.startsWith('cred'))).toBe(false);
  });

  it('keeps COMMAND_SHAPES and ALLOWED_COMMANDS the same set, so neither can drift', () => {
    // The classification tests above read ALLOWED_COMMANDS; `run()` enforces COMMAND_SHAPES.
    // If the two ever diverged, one of those would be checking a list nothing consults —
    // which is the defect this whole section exists to close.
    expect(Object.keys(COMMAND_SHAPES).sort()).toEqual(ALLOWED_COMMANDS.map((c) => c.join(' ')).sort());
  });

  it('allows no command to be passed --json, which invoke.ts appends', () => {
    // A caller that supplies `--json` is a caller building an argv this layer did not mean
    // to build. Refusing it is what makes the boundary catch a call site that stopped
    // validating an operand.
    for (const [name, shape] of Object.entries(COMMAND_SHAPES)) {
      expect(Object.keys(shape.flags), name).not.toContain('--json');
      expect(Object.keys(shape.flags), name).not.toContain('--client-schemas');
      expect(Object.keys(shape.flags), name).not.toContain('--reassign-identity');
    }
  });
});

/**
 * The boundary, not the list.
 *
 * Every assertion in this block is about `run()` — the one door to `invokeDevteam`. The
 * tests above read tables; a table is only a guarantee if something consults it, and
 * before `argvProblem` nothing did: a `credGet()` calling `run(ctx, ['cred','get',key])`
 * typechecked, linted and left all 73 tests green.
 */
describe('the argv boundary refuses before it spawns', () => {
  it('refuses `cred get` from run() itself, without spawning anything', async () => {
    // Shaped exactly like the `credGet()` a future edit would add. The binary does not
    // exist, so a spawn would come back `unavailable`; `refused` with durationMs 0 is
    // proof no process was created.
    const result = await run(unspawnable(), ['cred', 'get', 'OPENAI_API_KEY'], (body) => body);
    expect(result.ok).toBe(false);
    if (result.ok) throw new Error('unreachable');
    expect(result.kind).toBe('refused');
    expect(result.durationMs).toBe(0);
    expect(result.message).toContain('not a command this app is allowed to run');
  });

  it('refuses every mutating command outside the gated list, and `migrate` in particular', async () => {
    // `bind`/`unbind`/`sync`/`pin`/`upgrade` moved into the gated list with this app's
    // write actions, and `prefs set`/`prefs unset` with the project settings screen; these
    // are the ones that remain refused because nothing in this build spawns them yet —
    // `migrate` in particular, because it is the project lifecycle's other mutating
    // command and has no handler.
    for (const args of [['migrate'], ['export'], ['store', 'use'], ['cred', 'list'], ['update'], ['uninstall']]) {
      const result = await run(unspawnable(), args, (body) => body);
      expect(result.ok, args.join(' ')).toBe(false);
      if (result.ok) throw new Error('unreachable');
      expect(result.kind, args.join(' ')).toBe('refused');
    }
  });

  it('refuses a `--project-id`-shaped or `--provider`-shaped flag on a command that does not take it', async () => {
    for (const args of [
      ['list', '--project-id', 'x'],
      ['catalog', '--provider', 'claude'],
      ['doctor', '--all'],
    ]) {
      const result = await run(unspawnable(), args, (body) => body);
      if (result.ok) throw new Error(`expected a refusal for ${args.join(' ')}`);
      expect(result.kind, args.join(' ')).toBe('refused');
      expect(result.message, args.join(' ')).toContain('may not be passed');
    }
  });

  it('refuses a flag no command declares, including --json and --reassign-identity', async () => {
    for (const args of [
      ['doctor', '--reassign-identity'],
      ['catalog', '--json'],
      ['list', '--all'],
      ['catalog', 'show', 'x', '--hint'],
    ]) {
      const result = await run(unspawnable(), args, (body) => body);
      if (result.ok) throw new Error(`expected a refusal for ${args.join(' ')}`);
      expect(result.kind, args.join(' ')).toBe('refused');
      expect(result.message, args.join(' ')).toContain('may not be passed');
    }
  });

  it('refuses an operand a command does not take', () => {
    expect(argvProblem(['list', 'extra'])).toContain('takes 0 operands');
    expect(argvProblem(['catalog', 'bogus'])).toContain('takes 0 operands');
    expect(argvProblem(['catalog', 'show', 'a', 'b'])).toContain('takes 1 operand');
  });

  it('refuses a --path with no value, or one that would read as a flag', () => {
    expect(argvProblem(['catalog', '--path'])).toContain('no value');
    expect(argvProblem(['catalog', '--path', '--json'])).toContain('another flag');
  });

  it('allows exactly the argv the operations build', () => {
    expect(argvProblem(['version'])).toBeNull();
    expect(argvProblem(['compat'])).toBeNull();
    expect(argvProblem(['list'])).toBeNull();
    expect(argvProblem(['catalog', '--path', '/tmp/x'])).toBeNull();
    expect(argvProblem(['catalog', 'agents', '--path', '/tmp/x'])).toBeNull();
    expect(argvProblem(['catalog', 'show', 'backend-developer', '--path', '/tmp/x'])).toBeNull();
    expect(argvProblem(['doctor', '--no-project'])).toBeNull();
  });

  it('refuses an empty argv rather than spawning a bare `devteam --json`', () => {
    expect(argvProblem([])).not.toBeNull();
  });
});

/**
 * The write actions' argv, against `unspawnable()` — the binary does not exist, so
 * `result.command` is the only thing worth reading: it is the exact argv `invokeDevteam`
 * would have spawned, and every assertion below is about what got into it.
 */
describe('the write actions build the argv the CLI documents', () => {
  it('bindProject repeats --provider once per provider, in a single positional path', async () => {
    const result = await bindProject(unspawnable(), '/tmp/project', {
      providers: ['claude', 'codex'],
      mode: 'link',
      pin: '3.0.0',
    });
    expect(result.command).toContain(
      'bind /tmp/project --provider claude --provider codex --mode link --pin 3.0.0 --json',
    );
  });

  it('bindProject omits every flag it was not given', async () => {
    const result = await bindProject(unspawnable(), '/tmp/project');
    expect(result.command).toContain('bind /tmp/project --json');
    expect(result.command).not.toContain('--provider');
    expect(result.command).not.toContain('--mode');
    expect(result.command).not.toContain('--pin');
  });

  it('unbindProject names its target by --project-id, never a path', async () => {
    const result = await unbindProject(unspawnable(), 'proj-1');
    expect(result.command).toContain('unbind --project-id proj-1 --json');
  });

  it('syncProject names its target by --project-id; syncAllProjects passes --all with no id', async () => {
    const one = await syncProject(unspawnable(), 'proj-1');
    expect(one.command).toContain('sync --project-id proj-1 --json');
    const all = await syncAllProjects(unspawnable());
    expect(all.command).toContain('sync --all --json');
    expect(all.command).not.toContain('--project-id');
  });

  it('setPin(id, version) passes the version and --path; setPin(id, null) is --release, never an empty string', async () => {
    const versioned = await setPin(unspawnable(), '/tmp/project', '3.1.0');
    expect(versioned.command).toContain('pin 3.1.0 --path /tmp/project --json');
    const released = await setPin(unspawnable(), '/tmp/project', null);
    expect(released.command).toContain('pin --path /tmp/project --release --json');
    // The one assertion this test exists for: `setPin(id, null)` must never reach the
    // CLI as `pin ''` or `pin ""`, either of which `cmd_pin` would refuse as "pass a
    // version to pin, or --release to clear the pin" rather than releasing anything.
    expect(released.command).not.toContain("pin ''");
    expect(released.command).not.toContain('pin ""');
  });

  it('prefsSet and prefsUnset always write --scope project, with values spelled the way _coerce reads them', async () => {
    const cases: readonly [PreferenceValue, string][] = [
      [true, 'true'],
      [false, 'false'],
      [null, 'null'],
      [24, '24'],
      [1.8, '1.8'],
      ['pt-BR', 'pt-BR'],
    ];
    for (const [value, spelled] of cases) {
      const result = await prefsSet(unspawnable(), '/tmp/project', 'some_key', value);
      expect(result.command).toContain(`prefs set some_key ${spelled} --scope project --path /tmp/project --json`);
      expect(result.command).not.toContain('--scope global');
    }
    const unset = await prefsUnset(unspawnable(), '/tmp/project', 'some_key');
    expect(unset.command).toContain('prefs unset some_key --scope project --path /tmp/project --json');
    const list = await prefsList(unspawnable(), '/tmp/project');
    expect(list.command).toContain('prefs list --path /tmp/project --json');
  });

  it('prefsSet refuses, without spawning, a value _coerce would misread or argparse would take as a flag', async () => {
    for (const [key, value] of [
      ['language', ''],
      ['language', ' en'],
      ['language', 'true'],
      ['language', 'None'],
      ['language', '--scope'],
      ['language', 'a\nb'],
      ['model_max_tokens', -1],
      ['model_max_tokens', Number.NaN],
      ['--scope', 'global'],
      ['Language', 'en'],
    ] as const) {
      const result = await prefsSet(unspawnable(), '/tmp/project', key, value);
      if (result.ok) throw new Error(`expected a refusal for ${key}=${String(value)}`);
      expect(result.kind, `${key}=${String(value)}`).toBe('refused');
      expect(result.durationMs).toBe(0);
    }
  });

  it('planUpgrade and applyUpgrade pass a path, never a project id, with --apply only on apply', async () => {
    const plan = await planUpgrade(unspawnable(), '/tmp/project');
    expect(plan.command).toContain('upgrade /tmp/project --json');
    expect(plan.command).not.toContain('--apply');
    const apply = await applyUpgrade(unspawnable(), '/tmp/project');
    expect(apply.command).toContain('upgrade /tmp/project --apply --json');
  });
});

/**
 * The write-action payload validators, against the real shapes captured from the CLI at
 * store version 2.48.0 (see `shared/api.ts`'s `BindReport` doc comment). Each one is
 * checked three ways: the real shape is accepted, an added key is tolerated (ADR-0014
 * § 2), and a missing required key is reported rather than silently dropped.
 */
describe('the global skills operations build the argv the CLI documents', () => {
  it('list passes the provider filter; show and remove always pass --root', async () => {
    expect((await listSkills(unspawnable(), 'codex')).command).toContain('skills list --provider codex --json');
    expect((await showSkill(unspawnable(), 'alpha', 'claude')).command).toContain('skills show alpha --root claude --json');
    expect((await removeSkill(unspawnable(), ' alpha ', 'claude')).command).toContain('skills remove alpha --root claude --json');
  });

  it('install repeats --provider and passes --replace and --link only when asked', async () => {
    const full = await installSkill(unspawnable(), '/picked/dir', { providers: ['claude', 'codex'], replace: true, link: true });
    expect(full.command).toContain('skills install --source /picked/dir --provider claude --provider codex --replace --link --json');
    const bare = await installSkill(unspawnable(), '/picked/dir', { providers: ['opencode'], replace: false, link: false });
    expect(bare.command).toContain('skills install --source /picked/dir --provider opencode --json');
    expect(bare.command).not.toContain('--replace');
    expect(bare.command).not.toContain('--link');
  });

  it('refuses, without spawning, a flag-shaped name or a root that is not an id', async () => {
    for (const result of [
      await showSkill(unspawnable(), '--json', 'claude'),
      await removeSkill(unspawnable(), 'alpha', '../etc'),
      await removeSkill(unspawnable(), 'alpha', '--root'),
      // Path-shaped names: the CLI refuses them too, but these must not rely on it.
      ...(await Promise.all(
        ['..', '.', '.hidden', 'a/b', 'a\\b', '/etc', 'C:evil', 'a\0b'].flatMap((name) => [
          showSkill(unspawnable(), name, 'claude'),
          removeSkill(unspawnable(), name, 'claude'),
        ]),
      )),
    ]) {
      expect(result.ok).toBe(false);
      if (!result.ok) expect(result.kind).toBe('refused');
    }
  });

  it('refuses flags the skills commands do not declare, including --root on install', () => {
    expect(argvProblem(['skills', 'install', '--source', '/x', '--root', 'claude'])).toContain('--root');
    expect(argvProblem(['skills', 'list', '--path', '/x'])).toContain('--path');
    expect(argvProblem(['skills', 'remove', 'a', 'b'])).toContain('takes 1 operand');
    expect(argvProblem(['skills'])).toContain('not a command');
  });
});

describe('global skills payload validation', () => {
  const record = {
    name: 'alpha',
    description: null,
    root: 'claude',
    root_path: '/h/.claude/skills',
    path: '/h/.claude/skills/alpha',
    providers: ['claude'],
    is_symlink: true,
    link_target: '/elsewhere/alpha',
    managed: false,
    status: 'ok',
    error: null,
  };

  it('reads a list, tolerating an added key, and treats an absent `exists` as present', () => {
    const parsed = asSkillList({
      provider: 'all',
      roots: [{ id: 'claude', path: '/h/.claude/skills', providers: ['claude'], install_target_for: [], surprise: 1 }],
      skills: [{ ...record, surprise: 1 }],
      count: 1,
    });
    expect(parsed).toMatchObject({ roots: [{ id: 'claude', exists: true }], skills: [{ name: 'alpha', is_symlink: true }] });
  });

  it('reports a missing required key rather than rendering nothing', () => {
    expect(asSkillList({ roots: [], count: 0 })).toBe('no `skills` array');
    expect(asSkillList({ roots: [], skills: [omit(record, 'managed')] })).toBe('a skill has no boolean `managed`');
    expect(asSkillList({ roots: [], skills: [{ ...record, status: 'odd' }] })).toContain('status');
  });

  it('reads show, install and remove answers', () => {
    expect(asSkillDetail({ ...record, body: '# hi', files: ['SKILL.md'], files_truncated: true })).toMatchObject({
      body: '# hi',
      files_truncated: true,
    });
    expect(
      asSkillInstallReport({
        name: 'alpha',
        source: '/s',
        linked: false,
        installed: [{ root: 'claude', path: '/p', providers: ['claude'], replaced: true, quarantined_to: '/q' }],
      }),
    ).toMatchObject({ name: 'alpha', installed: [{ replaced: true, quarantined_to: '/q' }] });
    expect(asSkillInstallReport({ name: 'alpha' })).toBe('no `installed` array');
    expect(
      asSkillRemoveReport({ name: 'a', root: 'claude', path: '/p', providers: [], action: 'unlinked', quarantined_to: null }),
    ).toMatchObject({ action: 'unlinked', quarantined_to: null });
    expect(asSkillRemoveReport({ name: 'a', root: 'claude', path: '/p', action: 'deleted' })).toContain('action');
  });
});

describe('bind reports carry preferences_import when the CLI sends it', () => {
  const base = {
    path: '/p',
    project_id: 'p',
    version: '2.48.0',
    mode: 'link',
    providers: ['claude'],
    artifacts: 1,
    identity_created: false,
    gitignore: 'unchanged',
    git_exclude: 'unchanged',
    retired: [],
    merged_project_files: [],
  };

  it('is absent from an older CLI, and null when there was no file', () => {
    const older = asBindReport(base);
    if (typeof older === 'string') throw new Error(older);
    expect('preferences_import' in older).toBe(false);
    const none = asBindReport({ ...base, preferences_import: null });
    if (typeof none === 'string') throw new Error(none);
    expect(none.preferences_import).toBeNull();
  });

  it('reads a real import report, and rejects a malformed one', () => {
    const report = asBindReport({
      ...base,
      preferences_import: {
        source: '.dev-team-agents/user-data/preferences.json',
        imported: ['language'],
        unchanged: [],
        conflicts: [],
        ignored: [{ key: 'x', reason: 'unknown' }, 'junk'],
        quarantined: '/q/preferences.json',
        problem: null,
      },
    });
    if (typeof report === 'string') throw new Error(report);
    expect(report.preferences_import?.imported).toEqual(['language']);
    expect(report.preferences_import?.ignored).toEqual([{ key: 'x', reason: 'unknown' }]);
    expect(asBindReport({ ...base, preferences_import: { source: 'x' } })).toContain('preferences_import');
  });
});

describe('preference payload validation', () => {
  it('reads prefs list and keeps only string origins', () => {
    const parsed = asProjectPreferences({
      project_id: 'p',
      version: '2.48.0',
      values: { language: 'en' },
      origin: { language: 'project', odd: 3 },
      unknown: ['x', 4],
    });
    if (typeof parsed === 'string') throw new Error(parsed);
    expect(parsed.origin).toEqual({ language: 'project' });
    expect(parsed.unknown).toEqual(['x']);
  });

  it('rejects a prefs list without values, origin or version', () => {
    expect(asProjectPreferences({ origin: {}, version: '1' })).toContain('values');
    expect(asProjectPreferences({ values: {}, version: '1' })).toContain('origin');
    expect(asProjectPreferences({ values: {}, origin: {} })).toContain('version');
  });

  it('reads prefs set and unset answers', () => {
    expect(asPreferenceWrite({ key: 'a', scope: 'project', value: 1, file: '/x' })).toEqual({ key: 'a', scope: 'project' });
    expect(asPreferenceWrite({ key: 'a', scope: 'project', removed: false })).toEqual({ key: 'a', scope: 'project', removed: false });
    expect(asPreferenceWrite({ scope: 'project' })).toContain('key');
  });
});

describe('write-action payload validation, against the real shapes', () => {
  const bindBody: Record<string, unknown> = {
    path: '/repo/project',
    project_id: 'abc-123',
    version: '2.48.0',
    mode: 'link',
    providers: ['claude'],
    artifacts: 42,
    identity_created: true,
    gitignore: '.gitignore',
    git_exclude: '.git/info/exclude',
    pin: null,
    fallback_reason: null,
    retired: [],
    merged_project_files: [],
    pruned: { unlinked: [], quarantined: [] },
  };

  it('accepts the real `bind`/single-`sync` shape, worktrees included', () => {
    const result = asBindReport({ ...bindBody, worktrees: [{ path: '/repo/wt' }] });
    if (typeof result === 'string') throw new Error(result);
    expect(result.project_id).toBe('abc-123');
    expect(result.pruned).toEqual({ unlinked: [], quarantined: [] });
    expect(result.worktrees).toEqual([{ path: '/repo/wt' }]);
  });

  it('tolerates a key the CLI added that this app does not know yet', () => {
    const result = asBindReport({ ...bindBody, a_future_field: 'value' });
    expect(typeof result).not.toBe('string');
  });

  it('reports a missing required key on `bind` rather than rendering nothing', () => {
    expect(asBindReport(omit(bindBody, 'artifacts'))).toBe('no numeric `artifacts`');
  });

  it('accepts the real `sync --all` shape', () => {
    const result = asSyncAllReport({ synced: [bindBody], problems: [] });
    if (typeof result === 'string') throw new Error(result);
    expect(result.synced).toHaveLength(1);
    expect(result.synced[0]?.project_id).toBe('abc-123');
  });

  it('reports a missing required key on `sync --all`', () => {
    expect(asSyncAllReport({ synced: [bindBody] })).toBe('no `problems` array');
  });

  it('accepts the real `unbind` shape', () => {
    const result = asUnbindReport({
      path: '/repo/project',
      project_id: 'abc-123',
      unlinked: ['.claude/settings.json'],
      quarantined: [{ to: '/store/quarantine/abc-123' }],
      kept: ['project.json'],
      problems: [],
    });
    if (typeof result === 'string') throw new Error(result);
    expect(result.quarantined).toEqual([{ to: '/store/quarantine/abc-123' }]);
  });

  it('tolerates an added key on `unbind`', () => {
    const result = asUnbindReport({
      path: '/repo/project',
      project_id: 'abc-123',
      unlinked: [],
      quarantined: [],
      kept: [],
      problems: [],
      a_future_field: 'value',
    });
    expect(typeof result).not.toBe('string');
  });

  it('reports a missing required key on `unbind`', () => {
    expect(
      asUnbindReport({ project_id: 'abc-123', unlinked: [], quarantined: [], kept: [], problems: [] }),
    ).toBe('no string `path`');
  });

  it('accepts the real `pin` shape, a set and a release alike', () => {
    const versioned = asPinReport({ project_id: 'abc-123', path: '/repo/project', pin: '3.1.0' });
    if (typeof versioned === 'string') throw new Error(versioned);
    expect(versioned.pin).toBe('3.1.0');
    const released = asPinReport({ project_id: 'abc-123', path: '/repo/project', pin: null });
    if (typeof released === 'string') throw new Error(released);
    expect(released.pin).toBeNull();
  });

  it('reports a missing required key on `pin`', () => {
    expect(asPinReport({ path: '/repo/project', pin: null })).toBe('no string `project_id`');
  });

  const upgradePlanBody: Record<string, unknown> = {
    path: '/repo/project',
    project_id: 'abc-123',
    from_layout: 1,
    to_layout: 2,
    files: 12,
    source: '.dev-team-agents/user-data',
    destination: '/store/data/projects/abc-123',
    state_destination: '/store/data/machines/m1/projects/abc-123',
    machine_local: ['state.json'],
    retained: ['docs/project.md'],
    collisions: [],
    git_tracked: ['.dev-team-agents/user-data/session-summary.md'],
    actions: ['copy 12 file(s)'],
  };

  it('accepts the real `upgrade` plan shape', () => {
    const result = asUpgradePlan(upgradePlanBody);
    if (typeof result === 'string') throw new Error(result);
    expect(result.files).toBe(12);
    expect(result.git_tracked).toEqual(['.dev-team-agents/user-data/session-summary.md']);
  });

  it('tolerates an added key on the `upgrade` plan', () => {
    expect(typeof asUpgradePlan({ ...upgradePlanBody, a_future_field: 'value' })).not.toBe('string');
  });

  it('reports a missing required key on the `upgrade` plan', () => {
    expect(asUpgradePlan(omit(upgradePlanBody, 'files'))).toBe('no numeric `files`');
  });

  it('accepts the real `upgrade --apply` shape', () => {
    const result = asUpgradeReport({
      path: '/repo/project',
      project_id: 'abc-123',
      from_layout: 1,
      to_layout: 2,
      copied: 12,
      retained: ['docs/project.md'],
      destination: '/store/data/projects/abc-123',
      state_destination: '/store/data/machines/m1/projects/abc-123',
      quarantined: null,
      state_pointer: '.dev-team-agents/memory-dir',
      memory_pointer: '.dev-team-agents/memory-dir',
      git_tracked: [],
    });
    if (typeof result === 'string') throw new Error(result);
    expect(result.quarantined).toBeNull();
    expect(result.copied).toBe(12);
  });

  it('reports a missing required key on `upgrade --apply`', () => {
    expect(
      asUpgradeReport({
        path: '/repo/project',
        project_id: 'abc-123',
        from_layout: 1,
        to_layout: 2,
        copied: 12,
        retained: [],
        destination: '/x',
        quarantined: null,
        state_pointer: '/x',
        memory_pointer: '/x',
        git_tracked: [],
      }),
    ).toBe('no string `state_destination`');
  });
});

/**
 * `catalogEntry`'s **call site**, not `validateEntryName`.
 *
 * Replacing `validateEntryName(name)` with `null` inside `catalogEntry` left the whole
 * suite green, because the validator was only ever called directly. These assertions go
 * through `catalogEntry` and pin the validator's own message, so the call site is what is
 * being tested — the argv boundary refuses `--json` too, but with different words.
 */
describe('catalogEntry validates the name it was given', () => {
  it('refuses an empty name without spawning, which only the validator catches', async () => {
    const result = await catalogEntry(unspawnable(), '   ');
    expect(result.ok).toBe(false);
    if (result.ok) throw new Error('unreachable');
    expect(result.kind).toBe('refused');
    expect(result.durationMs).toBe(0);
    expect(result.message).toContain('cannot be empty');
  });

  it('refuses an absurdly long name, which only the validator catches', async () => {
    const result = await catalogEntry(unspawnable(), 'x'.repeat(201));
    if (result.ok) throw new Error('unreachable');
    expect(result.message).toContain('200 characters');
  });

  it('refuses a flag-shaped name with the validator’s own words', async () => {
    const result = await catalogEntry(unspawnable(), '--json');
    if (result.ok) throw new Error('unreachable');
    expect(result.message).toContain('cannot begin with');
  });

  it('spawns the trimmed name, the same string the validator judged', async () => {
    // `validateEntryName` judged `name.trim()` while the argv carried the raw string, so a
    // name with trailing whitespace was validated in one form and sent in another.
    const result = await catalogEntry(fakeContext('ok'), '  backend-developer  ');
    // `command` is the argv as spawned, and both result branches carry it.
    expect(result.command).toContain('catalog show backend-developer');
    expect(result.command).not.toContain('  backend-developer  ');
  });
});

describe('catalog entry names', () => {
  it('accepts an ordinary name', () => {
    expect(validateEntryName('backend-developer')).toBeNull();
  });

  it('refuses a name that would be read as a flag', () => {
    // No shell is involved, so this is not injection — but argparse would read it as a
    // flag, and the renderer must not be able to choose one.
    expect(validateEntryName('--json')).toContain('flag');
    expect(validateEntryName('-h')).toContain('flag');
  });

  it('refuses an empty name, a non-string and an absurd one', () => {
    expect(validateEntryName('')).not.toBeNull();
    expect(validateEntryName('   ')).not.toBeNull();
    expect(validateEntryName(42)).not.toBeNull();
    expect(validateEntryName('x'.repeat(201))).not.toBeNull();
  });
});

describe('payload validation', () => {
  it.skipIf(skipOnWindowsWithoutLauncher)('reports a missing required key as a contract breach rather than rendering nothing', async () => {
    // `ok` emits `{ok, argv, current}` — no `projects`.
    const result = await listProjects(fakeContext('ok'));
    expect(result.ok).toBe(false);
    if (result.ok) throw new Error('unreachable');
    expect(result.kind).toBe('contract-breach');
    expect(result.message).toContain('projects');
  });

  it('refuses an unknown catalog kind without spawning anything', async () => {
    const result = await catalogListing(unspawnable(), 'agent' as never);
    expect(result.ok).toBe(false);
    if (result.ok) throw new Error('unreachable');
    expect(result.kind).toBe('refused');
    expect(result.durationMs).toBe(0);
  });

  it.skipIf(skipOnWindowsWithoutLauncher)('carries a malformed catalog entry’s flag and error into the row', async () => {
    const result = await catalogListing(fakeContext('catalog-malformed'), 'skills');
    if (!result.ok) throw new Error(`expected a payload: ${result.message}`);
    const broken = result.data.entries.find((entry) => entry.name === 'broken');
    expect(broken?.malformed).toBe(true);
    expect(broken?.error).toContain('frontmatter');
    // A well-formed entry must not be tagged.
    expect(result.data.entries.find((entry) => entry.name === 'project-context')?.malformed).toBeUndefined();
  });
});

/**
 * `path_exists`, in all four states the client can be handed.
 *
 * Hardcoding `path_exists: false` in the mapper kept every test green, because the only
 * `list` in the suite ran against an **empty** store — so the whole project-row mapping was
 * validated against zero rows. This block validates it against rows; `real-cli.test.ts`
 * does the same against a real, non-empty listing.
 */
describe.skipIf(skipOnWindowsWithoutLauncher)('the project row mapping', () => {
  it('distinguishes true, false and unknown, and maps the rest of the row', async () => {
    const result = await listProjects(fakeContext('list-projects'));
    if (!result.ok) throw new Error(`expected a payload: ${result.message}`);
    const byId = new Map(result.data.projects.map((project) => [project.project_id, project]));

    expect(result.data.current).toBe('3.0.0');
    expect(byId.get('p-true')?.path_exists).toBe(true);
    expect(byId.get('p-false')?.path_exists).toBe(false);
    // The two that must not become an affirmative `false`.
    expect(byId.get('p-absent')?.path_exists).toBeNull();
    expect(byId.get('p-junk')?.path_exists).toBeNull();

    expect(byId.get('p-true')?.providers).toEqual(['claude']);
    expect(byId.get('p-true')?.mode).toBe('link');
    expect(byId.get('p-false')?.pin).toBe('2.9.0');
    expect(byId.get('p-false')?.resolves_to).toBe('2.9.0');
    expect(byId.get('p-absent')?.mode).toBeNull();
    expect(byId.get('p-absent')?.pin).toBeNull();
    expect(byId.get('p-absent')?.resolves_to).toBeNull();
  });
});

/**
 * `toOperationResult`'s `kind`, per exit code. It had no unit test for any branch, and the
 * ternary fell through to `'environment'` — so an exit-1 error document was titled "The
 * environment is not ready".
 */
describe.skipIf(skipOnWindowsWithoutLauncher)('an error document gets the label its exit code means', () => {
  const cases: readonly [string, string, number][] = [
    ['findings-error-document', 'findings', 1],
    ['usage', 'usage', 2],
    ['environment', 'environment', 3],
    ['conflict', 'conflict', 4],
  ];

  for (const [scenario, kind, exitCode] of cases) {
    it(`maps exit ${exitCode} to \`${kind}\``, async () => {
      const result = await listProjects(fakeContext(scenario));
      expect(result.ok).toBe(false);
      if (result.ok) throw new Error('unreachable');
      expect(result.kind).toBe(kind);
      expect(result.exitCode).toBe(exitCode);
    });
  }

  it('reports an error document carried by exit 0 rather than labelling it', async () => {
    const result = await listProjects(fakeContext('error-document-exit-zero'));
    if (result.ok) throw new Error('unreachable');
    expect(result.kind).toBe('contract-breach');
    expect(result.message).toContain('exited 0 but emitted an error document');
  });

  it('keeps the CLI’s own hint rather than paraphrasing it', async () => {
    const result = await listProjects(fakeContext('environment'));
    if (result.ok) throw new Error('unreachable');
    expect(result.hint).toBe('Run `devteam update`.');
  });

  it('reports a payload arriving with exit 2, 3 or 4 as a breach rather than data', async () => {
    // Nothing in the CLI does this; the point is that the app says so instead of rendering it.
    const result = await listProjects(fakeContext('undocumented-exit'));
    if (result.ok) throw new Error('unreachable');
    expect(result.kind).toBe('contract-breach');
  });
});

describe('the top-level JSON scanner', () => {
  it('counts one object', () => {
    expect(scanTopLevelJson('{"ok": true}').values).toHaveLength(1);
  });

  it('counts two concatenated objects', () => {
    expect(scanTopLevelJson('{"ok":true}\n{"ok":true}\n').values).toHaveLength(2);
  });

  it('is not fooled by braces inside strings', () => {
    const text = '{"ok": true, "hint": "run {devteam} } } bind"}';
    expect(scanTopLevelJson(text).values).toEqual([text]);
  });

  it('is not fooled by escaped quotes', () => {
    const text = '{"ok": true, "error": "she said \\"no\\" }"}';
    expect(scanTopLevelJson(text).values).toEqual([text]);
    expect(parseSingleDocument(text).ok).toBe(true);
  });

  it('does not count a quoted run in a traceback as a document', () => {
    // `File "x", line 1` contains a valid JSON string. Counting it as a document reported
    // a python traceback as `multiple-documents` instead of `not-json`.
    const traceback = 'Traceback (most recent call last):\n  File "x", line 1\n';
    expect(scanTopLevelJson(traceback).values).toHaveLength(0);
    const verdict = parseSingleDocument(traceback);
    expect(verdict.ok).toBe(false);
    if (verdict.ok) throw new Error('unreachable');
    expect(verdict.reason).toBe('not-json');
  });

  it('reports a bare JSON scalar as the wrong shape, not as unparseable', () => {
    const verdict = parseSingleDocument('3\n');
    expect(verdict.ok).toBe(false);
    if (verdict.ok) throw new Error('unreachable');
    expect(verdict.reason).toBe('not-an-object');
  });

  it('separates a document from trailing non-JSON text', () => {
    const scan = scanTopLevelJson('{"ok":true}\ndevteam: a stray print\n');
    expect(scan.values).toHaveLength(1);
    expect(scan.garbage.length).toBeGreaterThan(0);
  });

  it('reports an unterminated value rather than silently dropping it', () => {
    expect(scanTopLevelJson('{"ok": true, "a": [').unterminated).not.toBeNull();
  });
});
