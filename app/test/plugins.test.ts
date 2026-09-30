/**
 * Plugins (ADR-0018), the parts that need no process and no DOM: the answers the app
 * accepts and refuses, the argv it may build, and the rules a config value must pass.
 */
import { describe, expect, it } from 'vitest';

import {
  argvProblem,
  asPluginConfigWrite,
  asPluginList,
  asPluginRunResult,
  asPluginToggle,
  asPluginView,
  pluginConfigSet,
  pluginConfigUnset,
  pluginDisable,
  pluginEnable,
  pluginRun,
  pluginRunTimeoutMs,
  type CliContext,
} from '../src/cli/operations.js';
import {
  isBlank,
  listItemProblem,
  pluginValueProblem,
  samePluginValue,
  serializePluginValue,
} from '../src/shared/pluginRules.js';
import { draftBatch, fieldDraftState, proposalToDrafts } from '../src/renderer/plugins/drafts.js';
import { pluginField, pluginView } from './renderer/support.js';

/** A context that would fail loudly if anything tried to spawn: every case below must refuse first. */
const NO_SPAWN: CliContext = { binary: '/nonexistent/devteam', cwd: '/tmp' };

function raw(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return JSON.parse(JSON.stringify({ ...pluginView(), ...overrides })) as Record<string, unknown>;
}

describe('parsing a PluginView', () => {
  it('accepts the ADR shape and keeps what the card needs', () => {
    const view = asPluginView(
      raw({
        status: { summary: 'Graph built', facts: [{ label: 'Nodes', value: '12' }, { label: 'Files', value: 3 }] },
        homepage: 'https://example.test',
      }),
    );
    if (typeof view === 'string') throw new Error(view);
    expect(view.name).toBe('graphify');
    expect(view.config_fields.map((field) => field.key)).toEqual(['targetPaths', 'auto_refresh']);
    expect(view.actions.map((action) => action.output)).toEqual(['config', 'log']);
    expect(view.actions[1]?.timeout_seconds).toBe(1800);
    expect(view.status?.facts).toEqual([
      { label: 'Nodes', value: '12' },
      { label: 'Files', value: '3' },
    ]);
  });

  it.each([
    ['a non-object', 'nope', 'not an object'],
    ['a name no manifest could have', { ...raw(), name: 'Bad Name' }, 'valid string `name`'],
    ['no `enabled`', { ...raw(), enabled: 'yes' }, 'boolean `enabled`'],
    ['no `ready`', { ...raw(), ready: undefined }, 'boolean `ready`'],
    ['no `configured`', { ...raw(), configured: 1 }, 'boolean `configured`'],
    ['no config_fields array', { ...raw(), config_fields: {} }, '`config_fields` array'],
    ['no actions array', { ...raw(), actions: null }, '`actions` array'],
    ['a config that is not an object', { ...raw(), config: [] }, '`config` that is not an object'],
    ['a field with no key', { ...raw(), config_fields: [{ type: 'boolean' }] }, 'no string `key`'],
    ['a field with no type', { ...raw(), config_fields: [{ key: 'x' }] }, 'no string `type`'],
    ['an action with no id', { ...raw(), actions: [{ label: 'x' }] }, 'no string `id`'],
    ['a requirement with no binary', { ...raw(), requirements: [{ found: true }] }, 'no string `binary`'],
  ])('refuses %s', (_label, body, message) => {
    const result = asPluginView(body);
    expect(typeof result).toBe('string');
    expect(result as string).toContain(message);
  });

  it('treats a requirement that does not say it was found as missing, and an unknown output as a log', () => {
    const view = asPluginView(
      raw({
        requirements: [{ binary: 'x' }],
        actions: [{ id: 'go', label: 'Go', output: 'sparkles', requires_enabled: false, writes: false }],
      }),
    );
    if (typeof view === 'string') throw new Error(view);
    expect(view.requirements[0]?.found).toBe(false);
    expect(view.actions[0]?.output).toBe('log');
  });

  it('keeps a field type it does not know, so a newer CLI does not break the screen', () => {
    const view = asPluginView(raw({ config_fields: [{ key: 'blob', type: 'matrix', label: 'Blob' }] }));
    if (typeof view === 'string') throw new Error(view);
    expect(view.config_fields[0]?.type).toBe('matrix');
  });

  it('reads the list, the toggle, the config write and the run', () => {
    const list = asPluginList({ project_id: 'p', plugins: [raw()] });
    if (typeof list === 'string') throw new Error(list);
    expect(list.plugins).toHaveLength(1);
    expect(asPluginList({ plugins: 'x' })).toContain('no `plugins` array');
    expect(asPluginList({ plugins: [{ name: 'graphify' }] })).toContain('boolean');

    const toggle = asPluginToggle({ plugin: raw(), changed: true, seeded: true });
    expect(toggle).toMatchObject({ changed: true, seeded: true });
    expect(asPluginToggle({ plugin: raw() })).toContain('boolean `changed`');

    expect(asPluginConfigWrite({ plugin: raw(), key: 'auto_refresh', removed: true })).toMatchObject({ key: 'auto_refresh', removed: true });
    expect(asPluginConfigWrite({ plugin: raw() })).toContain('string `key`');

    const ran = asPluginRunResult({ plugin: 'graphify', action: 'detect', ok: true, exit_code: 0, duration_ms: 5, output: { a: 1 }, log_tail: 'x' });
    expect(ran).toMatchObject({ ok: true, output: { a: 1 }, log_tail: 'x' });
  });

  it.each([
    [{ action: 'a', ok: true, exit_code: 0, duration_ms: 1 }, 'string `plugin`'],
    [{ plugin: 'p', ok: true, exit_code: 0, duration_ms: 1 }, 'string `action`'],
    [{ plugin: 'p', action: 'a', ok: 'true', exit_code: 0, duration_ms: 1 }, 'boolean `ok`'],
    [{ plugin: 'p', action: 'a', ok: true, exit_code: '0', duration_ms: 1 }, 'numeric `exit_code`'],
    [{ plugin: 'p', action: 'a', ok: true, exit_code: 0 }, 'numeric `duration_ms`'],
    [{ plugin: 'p', action: 'a', ok: true, exit_code: 0, duration_ms: 1, output: [] }, 'neither an object nor null'],
  ])('refuses a malformed RunResult %#', (body, message) => {
    expect(asPluginRunResult(body as Record<string, unknown>)).toContain(message);
  });

  it('defaults a missing output and log_tail rather than refusing a failed script’s answer', () => {
    expect(asPluginRunResult({ plugin: 'p', action: 'a', ok: false, exit_code: 3, duration_ms: 1 })).toMatchObject({
      output: null,
      log_tail: '',
    });
  });
});

describe('the argv the plugin commands may have', () => {
  it.each([
    [['plugin', 'list', '--path', '/p']],
    [['plugin', 'enable', 'graphify', '--path', '/p']],
    [['plugin', 'disable', 'graphify', '--path', '/p']],
    [['plugin', 'config', 'set', 'graphify', 'targetPaths', '["src"]', '--path', '/p']],
    [['plugin', 'config', 'unset', 'graphify', 'targetPaths', '--path', '/p']],
    [['plugin', 'run', 'graphify', 'detect', '--path', '/p']],
  ])('allows %j', (args) => {
    expect(argvProblem(args)).toBeNull();
  });

  it.each([
    [['plugin', 'enable', 'graphify', '--force'], '--force'],
    [['plugin', 'show', 'graphify'], 'not a command'],
    [['plugin', 'config', 'get', 'graphify'], 'not a command'],
    [['plugin', 'run', 'graphify', 'detect', 'extra'], 'takes 2 operands'],
    [['plugin', 'config', 'set', 'a', 'b', 'c', 'd'], 'takes 3 operands'],
    [['plugin', 'list', '--json'], '--json'],
  ])('refuses %j', (args, message) => {
    expect(argvProblem(args)).toContain(message);
  });
});

describe('the plugin operations refuse before spawning', () => {
  it('refuses a plugin name, key, value or action id no manifest could carry', async () => {
    const results = await Promise.all([
      pluginEnable(NO_SPAWN, '/p', '--force'),
      pluginDisable(NO_SPAWN, '/p', 'Has Spaces'),
      pluginConfigSet(NO_SPAWN, '/p', 'graphify', 'bad-key', 'x'),
      pluginConfigSet(NO_SPAWN, '/p', 'graphify', 'key', '--flag'),
      pluginConfigSet(NO_SPAWN, '/p', 'graphify', 'key', ''),
      pluginConfigUnset(NO_SPAWN, '/p', 'graphify', '--all'),
      pluginRun(NO_SPAWN, '/p', 'graphify', '--x', 60),
      pluginRun(NO_SPAWN, '/p', '../etc', 'detect', 60),
    ]);
    for (const result of results) {
      expect(result.ok).toBe(false);
      if (result.ok) continue;
      expect(result.kind).toBe('refused');
      expect(result.durationMs).toBe(0);
    }
  });

  it('gives a run its action’s own timeout plus a margin, capped at the manifest maximum', () => {
    expect(pluginRunTimeoutMs(60)).toBe(90_000);
    expect(pluginRunTimeoutMs(1800)).toBe(1_830_000);
    expect(pluginRunTimeoutMs(999_999)).toBe(1_830_000);
    expect(pluginRunTimeoutMs(null)).toBe(1_830_000);
    expect(pluginRunTimeoutMs(-5)).toBe(1_830_000);
    expect(pluginRunTimeoutMs(Number.NaN)).toBe(1_830_000);
  });
});

describe('config value rules', () => {
  const list = pluginField();
  const integer = pluginField({ key: 'depth', type: 'integer', min: 1, max: 9, required: false });
  const text = pluginField({ key: 'name', type: 'string', required: false });
  const choice = pluginField({ key: 'mode', type: 'enum', options: [{ value: 'a', label: 'A' }] });
  const flag = pluginField({ key: 'auto', type: 'boolean' });

  it('accepts a value of the right type and refuses the wrong one', () => {
    expect(pluginValueProblem(list, ['src', 'lib'])).toBeNull();
    expect(pluginValueProblem(list, 'src')).not.toBeNull();
    expect(pluginValueProblem(list, ['src', 'src'])).toContain('twice');
    expect(pluginValueProblem(list, ['src', ''])).not.toBeNull();
    expect(pluginValueProblem(list, [1])).not.toBeNull();
    expect(pluginValueProblem(flag, true)).toBeNull();
    expect(pluginValueProblem(flag, 'true')).not.toBeNull();
    expect(pluginValueProblem(choice, 'a')).toBeNull();
    expect(pluginValueProblem(choice, 'z')).not.toBeNull();
  });

  it('bounds an integer, and refuses a fraction, a string and a negative', () => {
    expect(pluginValueProblem(integer, 5)).toBeNull();
    expect(pluginValueProblem(integer, 0)).toContain('at least 1');
    expect(pluginValueProblem(integer, 10)).toContain('at most 9');
    expect(pluginValueProblem(integer, 1.5)).not.toBeNull();
    expect(pluginValueProblem(integer, '5')).not.toBeNull();
    expect(pluginValueProblem(integer, -1)).toContain('Negative');
  });

  it('refuses text that would read as a flag or as nothing', () => {
    expect(pluginValueProblem(text, 'ok')).toBeNull();
    expect(pluginValueProblem(text, '-rf')).toContain('"-"');
    expect(pluginValueProblem(text, '')).not.toBeNull();
    expect(pluginValueProblem(text, ' padded ')).not.toBeNull();
    expect(pluginValueProblem(text, 'a\nb')).not.toBeNull();
    expect(pluginValueProblem(pluginField({ type: 'matrix' }), 1)).toContain('cannot edit');
  });

  it('serializes the way `plugin config set` parses (ADR-0018 § 3)', () => {
    expect(serializePluginValue(list, ['src', 'lib'])).toBe('["src","lib"]');
    expect(serializePluginValue(list, [])).toBe('[]');
    expect(serializePluginValue(flag, true)).toBe('true');
    expect(serializePluginValue(flag, false)).toBe('false');
    expect(serializePluginValue(integer, 5)).toBe('5');
    expect(serializePluginValue(text, 'hello')).toBe('hello');
    expect(serializePluginValue(choice, 'a')).toBe('a');
  });

  it('compares lists by content and knows what blank is', () => {
    expect(samePluginValue(['a'], ['a'])).toBe(true);
    expect(samePluginValue(['a'], ['b'])).toBe(false);
    expect(samePluginValue(['a', 'b'], ['b', 'a'])).toBe(false);
    expect(isBlank([])).toBe(true);
    expect(isBlank('  ')).toBe(true);
    expect(isBlank(false)).toBe(false);
    expect(isBlank(0)).toBe(false);
    expect(listItemProblem('src')).toBeNull();
    expect(listItemProblem('')).not.toBeNull();
  });
});

describe('a config form’s drafts', () => {
  const fields = [
    pluginField(),
    pluginField({ key: 'depth', type: 'integer', min: 1, max: 9, required: false, default: 3, label: 'Depth' }),
    pluginField({ key: 'name', type: 'string', required: false, default: '', label: 'Name' }),
  ];
  const config = { targetPaths: ['src'], depth: 3, name: 'kept' };

  it('counts only drafts that differ from the saved value', () => {
    const batch = draftBatch(fields, config, { targetPaths: ['src'], depth: '3', name: 'kept' });
    expect(batch.dirtyKeys).toEqual([]);
    expect(batch.changes).toEqual([]);
  });

  it('turns a list edit into a set, an emptied string into an unset, and a typed integer into a number', () => {
    const batch = draftBatch(fields, config, { targetPaths: ['src', 'lib'], depth: '7', name: '' });
    expect(batch.changes).toEqual([
      { key: 'targetPaths', action: 'set', value: ['src', 'lib'] },
      { key: 'depth', action: 'set', value: 7 },
      { key: 'name', action: 'unset' },
    ]);
    expect(batch.invalid).toEqual([]);
  });

  it('flags an invalid integer and a required list left empty, and blocks nothing else', () => {
    const batch = draftBatch(fields, config, { targetPaths: [], depth: '12x' });
    expect([...batch.invalid].sort()).toEqual(['depth', 'targetPaths']);
    expect(fieldDraftState(fields[1] as (typeof fields)[number], config, { depth: '12x' }).error).toContain('whole number');
    expect(fieldDraftState(fields[1] as (typeof fields)[number], config, { depth: '99' }).error).toContain('at most 9');
    expect(fieldDraftState(fields[0] as (typeof fields)[number], config, { targetPaths: [] }).error).toContain('required');
  });

  it('fills a proposal into drafts without saving, ignoring keys and values the form cannot hold', () => {
    const proposal = proposalToDrafts(fields, config, {
      targetPaths: ['src', 'app'],
      depth: 3,
      name: 42,
      rogue: 'x',
    });
    expect(proposal.drafts).toEqual({ targetPaths: ['src', 'app'] });
    expect(proposal.filled).toEqual(['targetPaths']);
    expect([...proposal.skipped].sort()).toEqual(['name', 'rogue']);
  });

  it('spells an integer proposal as the text a person would have typed', () => {
    expect(proposalToDrafts(fields, config, { depth: 8 }).drafts).toEqual({ depth: '8' });
  });
});
