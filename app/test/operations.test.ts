/**
 * The named operations: their validation, and the claim that this slice writes nothing.
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
  catalogEntry,
  catalogListing,
  listProjects,
  run,
} from '../src/cli/operations.js';
import { scanTopLevelJson, parseSingleDocument } from '../src/cli/parse.js';
import type { CliContext } from '../src/cli/operations.js';

const FAKE = fileURLToPath(new URL('./fixtures/fake-devteam.mjs', import.meta.url));
const REPO_ROOT = fileURLToPath(new URL('../..', import.meta.url));

/** A context whose binary does not exist, so a spawn is unmistakable in the result. */
function unspawnable(): CliContext {
  return { binary: join(REPO_ROOT, 'no-such-devteam-binary'), cwd: REPO_ROOT };
}

function fakeContext(scenario = 'ok'): CliContext {
  return { binary: FAKE, cwd: REPO_ROOT, env: { FAKE_DEVTEAM_SCENARIO: scenario } };
}

/**
 * The classification tables, read out of `compat.py` rather than restated here. A command
 * moved between them in the framework has to fail this test — which is the whole reason to
 * parse the source file instead of keeping a copy of the answer.
 */
function classificationTables() {
  const source = readFileSync(join(REPO_ROOT, 'scripts', 'lib', 'devteam', 'compat.py'), 'utf8');
  return {
    mutating: source.slice(source.indexOf('MUTATING = {'), source.indexOf('READ_ONLY = {')),
    readOnly: source.slice(source.indexOf('READ_ONLY = {'), source.indexOf('NEEDS_MACHINE_LAYOUT = {')),
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

  it('declares `doctor` as gated, because the framework classifies it as mutating', () => {
    // The tension the brief left open: the slice is "read-only" and the diagnosis screen
    // is `devteam doctor`, which `compat.MUTATING` lists because it repairs what it finds.
    // This asserts the app admits that rather than filing `doctor` under read-only.
    const { mutating, readOnly } = classificationTables();
    expect(GATED_COMMANDS.map((command) => command.join(' '))).toEqual(['doctor']);
    expect(mutating).toContain('("doctor",)');
    expect(readOnly).not.toContain('("doctor",)');
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

  it('refuses every mutating command outside the gated list, and `bind` in particular', async () => {
    for (const args of [['bind'], ['unbind'], ['prefs', 'set'], ['cred', 'list'], ['update'], ['uninstall']]) {
      const result = await run(unspawnable(), args, (body) => body);
      expect(result.ok, args.join(' ')).toBe(false);
      if (result.ok) throw new Error('unreachable');
      expect(result.kind, args.join(' ')).toBe('refused');
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
  it('reports a missing required key as a contract breach rather than rendering nothing', async () => {
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

  it('carries a malformed catalog entry’s flag and error into the row', async () => {
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
describe('the project row mapping', () => {
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
describe('an error document gets the label its exit code means', () => {
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
