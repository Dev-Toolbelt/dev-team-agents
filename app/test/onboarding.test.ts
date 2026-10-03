/**
 * The first-run model (ADR-0030): the step machine, the words the screens may use, and the
 * operations that carry `detect` and `start`.
 */
import { describe, expect, it } from 'vitest';

import { argvProblem, ALLOWED_COMMANDS, GATED_COMMANDS, READ_ONLY_COMMANDS } from '../src/cli/operations.js';
import { folderProblem, parseDetect } from '../src/cli/onboardingOperations.js';
import { allCopy } from '../src/renderer/onboarding/copy.js';
import { commandLabel, defaultChoices, firstTaskCopyText, needsAttention, providerChoices } from '../src/renderer/onboarding/model.js';
import { CLICK_STEPS, STEP_ORDER, clicksRemaining, currentStep, shouldRun, type Facts } from '../src/renderer/onboarding/steps.js';
import { detectReport } from './renderer/support.js';

const FRESH: Facts = {
  completed: false,
  hasProjects: false,
  cliFound: false,
  signedIn: false,
  machineReady: false,
  folder: null,
  confirmed: false,
  started: false,
};

describe('the step machine', () => {
  it('is CLI, sign-in, this computer, folder, confirm, first task — in that order', () => {
    expect(STEP_ORDER).toEqual(['cli', 'signin', 'machine', 'folder', 'confirm', 'start']);
  });

  it('puts the person on the first step whose fact is not yet true, never skipping ahead', () => {
    let facts = FRESH;
    const seen: (string | null)[] = [currentStep(facts)];
    for (const patch of [
      { cliFound: true },
      { signedIn: true },
      { machineReady: true },
      { folder: '/work/app' },
      { confirmed: true },
      { started: true },
    ] as const) {
      facts = { ...facts, ...patch };
      seen.push(currentStep(facts));
    }
    expect(seen).toEqual(['cli', 'signin', 'machine', 'folder', 'confirm', 'start', null]);
  });

  it('does not ask for sign-in before the CLI exists, whatever else is true', () => {
    expect(currentStep({ ...FRESH, signedIn: true, machineReady: true, folder: '/x', confirmed: true })).toBe('cli');
  });

  it('skips for a returning user: a finished wizard or any project at all', () => {
    expect(shouldRun({ completed: false, hasProjects: false })).toBe(true);
    expect(shouldRun({ completed: true, hasProjects: false })).toBe(false);
    expect(shouldRun({ completed: false, hasProjects: true })).toBe(false);
    expect(shouldRun({ completed: true, hasProjects: true })).toBe(false);
  });

  it('costs exactly three clicks after sign-in: choose the folder, confirm, start', () => {
    expect(CLICK_STEPS).toEqual(['folder', 'confirm', 'start']);

    // Signed in with the machine already fine: the machine step passes by itself.
    let facts: Facts = { ...FRESH, cliFound: true, signedIn: true, machineReady: true };
    expect(clicksRemaining(facts)).toBe(3);

    let clicks = 0;
    const clicksToDo: Partial<Facts>[] = [{ folder: '/work/app' }, { confirmed: true }, { started: true }];
    for (const click of clicksToDo) {
      expect(currentStep(facts)).not.toBeNull();
      facts = { ...facts, ...click };
      clicks += 1;
    }
    expect(clicks).toBe(3);
    expect(currentStep(facts)).toBeNull();
    expect(clicksRemaining(facts)).toBe(0);
  });

  it('counts the remaining clicks down as the person moves through', () => {
    const base: Facts = { ...FRESH, cliFound: true, signedIn: true, machineReady: true };
    expect(clicksRemaining({ ...base, folder: '/x' })).toBe(2);
    expect(clicksRemaining({ ...base, folder: '/x', confirmed: true })).toBe(1);
  });
});

describe('the words on the first-run screens', () => {
  // The framework's own vocabulary (ADR-0030 section 3). `\bbind\w*` covers bind, binds, binding;
  // `bound` is its past form.
  const FORBIDDEN = /\b(bind\w*|bound|layouts?|stores?|stored|preference layers?|preferences? layer)\b/i;

  it('never says bind, layout, store or preference layers', () => {
    const strings = allCopy();
    expect(strings.length).toBeGreaterThan(40);
    for (const text of strings) expect(text, text).not.toMatch(FORBIDDEN);
  });

  it('the check itself catches each forbidden word', () => {
    for (const bad of ['bind this folder', 'Binding…', 'the layout', 'in the store', 'preference layers', 'it is bound']) {
      expect(bad).toMatch(FORBIDDEN);
    }
    expect(['Restore', 'Boundary', 'Storage ready'].some((ok) => FORBIDDEN.test(ok))).toBe(false);
  });
});

describe('the first-run operations', () => {
  it('admits detect as a read and start as a gated write, each with only its own flags', () => {
    const flat = (list: readonly (readonly string[])[]) => list.map((c) => c.join(' '));
    expect(flat(READ_ONLY_COMMANDS)).toContain('detect');
    expect(flat(GATED_COMMANDS)).toContain('start');
    expect(flat(ALLOWED_COMMANDS)).toEqual(expect.arrayContaining(['detect', 'start']));

    expect(argvProblem(['detect', '--path', '/p'])).toBeNull();
    expect(argvProblem(['start', '--path', '/p', '--provider', 'claude', '--type', 'new'])).toBeNull();
    expect(argvProblem(['doctor', '--machine'])).toBeNull();
    expect(argvProblem(['detect', '/p'])).not.toBeNull();
    expect(argvProblem(['start', '--path', '/p', '--force'])).not.toBeNull();
    expect(argvProblem(['doctor', '--reassign-identity'])).not.toBeNull();
  });

  it('refuses a folder that could be read as a flag, or is empty, before spawning anything', () => {
    expect(folderProblem('/work/app')).toBeNull();
    expect(folderProblem('--json')).not.toBeNull();
    expect(folderProblem('')).not.toBeNull();
    expect(folderProblem(5)).not.toBeNull();
  });

  it('reads a detect answer and refuses one missing what the screens need', () => {
    const full = {
      path: '/work/app',
      providers: { installed: [{ name: 'claude', binary: 'claude', version: null }], in_project: ['claude'], suggested: 'claude' },
      stack: { primary: 'node', all: ['node'], signals: ['package.json'] },
      project_type: { suggested: 'new', confidence: 'low', reasons: ['empty folder'] },
      first_task: { kind: 'audit', target: 'src', label: 'Audit', read_only: true, launch: { provider: 'claude', argv: ['claude', 'x'] } },
    };
    expect(parseDetect(full)).toMatchObject({ path: '/work/app', project_type: { suggested: 'new', confidence: 'low' } });
    expect(parseDetect({ ...full, first_task: null })).toMatchObject({ first_task: null });
    expect(parseDetect({ ...full, first_task: { ...full.first_task, launch: null } })).toMatchObject({ first_task: { launch: null } });

    expect(typeof parseDetect({ ...full, project_type: { suggested: 'weird' } })).toBe('string');
    expect(typeof parseDetect({ ...full, first_task: { ...full.first_task, launch: { provider: 'claude', argv: ['claude', 1] } } })).toBe('string');
    expect(typeof parseDetect({ ...full, first_task: { ...full.first_task, kind: 'delete' } })).toBe('string');
    expect(typeof parseDetect({ ...full, providers: undefined })).toBe('string');
  });
});

describe('the confirm-screen model', () => {
  it('preselects what was detected, and a provider that is installed', () => {
    const report = detectReport();
    expect(defaultChoices(report)).toEqual({ provider: 'claude', type: 'maintenance', stack: 'node' });
    const noSuggestion = detectReport({ providers: { installed: [{ name: 'codex', binary: 'codex', version: null }], in_project: [], suggested: null } });
    expect(defaultChoices(noSuggestion).provider).toBe('codex');
  });

  it('lists every provider, marking the installed ones', () => {
    const choices = providerChoices(detectReport());
    expect(choices.find((c) => c.name === 'claude')?.installed).toBe(true);
    expect(choices.find((c) => c.name === 'codex')?.installed).toBe(false);
  });

  it('types commands the way each provider does', () => {
    expect(commandLabel('claude', 'plan')).toBe('/devteam:plan');
    expect(commandLabel('opencode', 'plan')).toBe('/devteam:plan');
    expect(commandLabel('codex', 'plan')).toBe('$devteam-plan');
  });

  it('copies the launch argv, quoted, when there is one, and the typed command when there is not', () => {
    const task = detectReport().first_task!;
    expect(firstTaskCopyText(task, 'claude', '/work/my app', 'posix')).toBe(
      "cd '/work/my app' && claude --permission-mode plan '/devteam:audit src --report-only'",
    );
    expect(firstTaskCopyText({ ...task, launch: null }, 'claude', '/work/my app', 'posix')).toBe('/devteam:audit src');
  });

  it('calls a finding a problem only when the CLI said warn, fail or error', () => {
    expect(needsAttention({ level: 'warn', category: 'git', message: 'x' })).toBe(true);
    expect(needsAttention({ level: 'fail', category: 'git', message: 'x' })).toBe(true);
    expect(needsAttention({ level: 'ok', category: 'git', message: 'x' })).toBe(false);
    expect(needsAttention({ level: 'info', category: 'git', message: 'x' })).toBe(false);
  });
});
