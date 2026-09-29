/**
 * `selfCheck` derives `AppHealth` from four already-observable inputs. Table-driven per
 * category so the six `AppFinding.category` values and their branches are each asserted
 * on their own, plus the `status` roll-up across a mixed set.
 */
import { describe, expect, it } from 'vitest';

import { selfCheck, type SelfCheckInput } from '../src/cli/selfCheck.js';
import type { BuildInfo, CliResolution, EnvironmentReport, HandshakeView, OperationResult } from '../src/shared/api.js';

function build(overrides: Partial<BuildInfo> = {}): BuildInfo {
  return {
    appVersion: '1.0.0',
    electronVersion: '30.0.0',
    packaged: false,
    codeSigned: false,
    hasWriteActions: false,
    mutatingCommandsRun: [],
    ...overrides,
  };
}

function environment(overrides: Partial<EnvironmentReport> = {}): EnvironmentReport {
  return {
    declaration: { state: 'written', path: '/app/schemas.json' },
    settings: { path: '/app/settings.json', problem: null, cliPathConfigured: true },
    workingDirectory: '/repo',
    withheld: [],
    ...overrides,
  };
}

function foundResolution(): CliResolution {
  return {
    found: true,
    rejected: [],
    cli: {
      path: '/opt/homebrew/bin/devteam',
      source: 'homebrew',
      sourceDetail: 'Homebrew bin',
      storeVersion: '2.48.0',
      jsonContract: 1,
      minAppVersion: null,
      storeSchemas: {},
    },
  };
}

function notFoundResolution(remedy: readonly string[] = ['Install the CLI: `brew install dev-toolbelt/devteam/devteam`.']): CliResolution {
  return {
    found: false,
    rejected: [],
    searchedCount: 7,
    searchedBySource: [],
    remedy,
  };
}

function answeredHandshake(overrides: Partial<Extract<HandshakeView, { state: 'answered' }>> = {}): OperationResult<HandshakeView> {
  return {
    ok: true,
    outcome: 'success',
    command: 'devteam compat',
    durationMs: 1,
    data: {
      state: 'answered',
      mayWrite: true,
      jsonContract: 1,
      minAppVersion: null,
      storeSchemas: {},
      clientSchemas: {},
      unsupported: {},
      summary: 'compatible',
      ...overrides,
    },
  };
}

function unknownHandshake(detail = 'no answer parsed'): OperationResult<HandshakeView> {
  return {
    ok: true,
    outcome: 'success',
    command: 'devteam compat',
    durationMs: 1,
    data: { state: 'unknown', summary: 'unknown', detail },
  };
}

function failedHandshake(message = 'the store could not be reached'): OperationResult<HandshakeView> {
  return { ok: false, kind: 'unavailable', message, exitCode: null, command: 'devteam compat', durationMs: 1 };
}

function input(overrides: Partial<SelfCheckInput> = {}): SelfCheckInput {
  return {
    build: build(),
    environment: environment(),
    resolution: foundResolution(),
    handshake: answeredHandshake(),
    ...overrides,
  };
}

function findingFor(result: ReturnType<typeof selfCheck>, category: string) {
  const finding = result.findings.find((f) => f.category === category);
  expect(finding).toBeDefined();
  return finding!;
}

describe('selfCheck — cli', () => {
  it('reports ok, naming the path and resolution step, when found', () => {
    const result = selfCheck(input({ resolution: foundResolution() }));
    const finding = findingFor(result, 'cli');
    expect(finding.level).toBe('ok');
    expect(finding.message).toContain('/opt/homebrew/bin/devteam');
    expect(finding.message).toContain('Homebrew bin');
  });

  it('reports fail, carrying the main process\'s own remedy, when not found', () => {
    const remedy = ['Install the CLI.', 'Or set DEVTEAM_CLI_PATH.'];
    const result = selfCheck(input({ resolution: notFoundResolution(remedy) }));
    const finding = findingFor(result, 'cli');
    expect(finding.level).toBe('fail');
    expect(finding.hint).toBe(remedy.join(' '));
  });
});

describe('selfCheck — version', () => {
  it('is ok when the store asserts no minimum', () => {
    const result = selfCheck(input({ handshake: answeredHandshake({ minAppVersion: null }) }));
    const finding = findingFor(result, 'version');
    expect(finding.level).toBe('ok');
    expect(finding.message).toMatch(/no minimum/i);
  });

  it('is ok when the app version meets the minimum', () => {
    const result = selfCheck(
      input({ build: build({ appVersion: '2.0.0' }), handshake: answeredHandshake({ minAppVersion: '2.0.0' }) }),
    );
    expect(findingFor(result, 'version').level).toBe('ok');
  });

  it('is fail, with an exit-4 hint, when the app version is older than the minimum', () => {
    const result = selfCheck(
      input({ build: build({ appVersion: '1.0.0' }), handshake: answeredHandshake({ minAppVersion: '2.0.0' }) }),
    );
    const finding = findingFor(result, 'version');
    expect(finding.level).toBe('fail');
    expect(finding.hint).toMatch(/exit 4/);
  });

  it('is warn when the handshake state is unknown', () => {
    const result = selfCheck(input({ handshake: unknownHandshake('probe timed out') }));
    const finding = findingFor(result, 'version');
    expect(finding.level).toBe('warn');
    expect(finding.hint).toBe('probe timed out');
  });

  it('is warn when the handshake operation itself failed', () => {
    const result = selfCheck(input({ handshake: failedHandshake('no devteam on PATH') }));
    const finding = findingFor(result, 'version');
    expect(finding.level).toBe('warn');
    expect(finding.hint).toBe('no devteam on PATH');
  });

  it('is warn, never a silent pass or fail, when a version string cannot be parsed', () => {
    const result = selfCheck(
      input({ build: build({ appVersion: '1.0.0-beta.1' }), handshake: answeredHandshake({ minAppVersion: '2.0.0' }) }),
    );
    expect(findingFor(result, 'version').level).toBe('warn');
  });

  it('is warn when the store minimum itself cannot be parsed', () => {
    const result = selfCheck(input({ handshake: answeredHandshake({ minAppVersion: 'not-a-version' }) }));
    expect(findingFor(result, 'version').level).toBe('warn');
  });
});

describe('selfCheck — declaration', () => {
  it('is ok, naming the path, when written', () => {
    const result = selfCheck(input({ environment: environment({ declaration: { state: 'written', path: '/x/schemas.json' } }) }));
    const finding = findingFor(result, 'declaration');
    expect(finding.level).toBe('ok');
    expect(finding.message).toContain('/x/schemas.json');
  });

  it('is fail, carrying the detail and the gate consequence, when the write failed', () => {
    const result = selfCheck(
      input({
        environment: environment({
          declaration: { state: 'failed', path: '/x/schemas.json', detail: 'EACCES: permission denied' },
        }),
      }),
    );
    const finding = findingFor(result, 'declaration');
    expect(finding.level).toBe('fail');
    expect(finding.hint).toContain('EACCES: permission denied');
    expect(finding.hint).toMatch(/mutating commands are refused/i);
  });
});

describe('selfCheck — settings', () => {
  it('is warn, saying the search ran without the configured path, when there is a problem', () => {
    const result = selfCheck(
      input({ environment: environment({ settings: { path: '/x/settings.json', problem: 'invalid JSON', cliPathConfigured: true } }) }),
    );
    const finding = findingFor(result, 'settings');
    expect(finding.level).toBe('warn');
    expect(finding.message).toContain('invalid JSON');
    expect(finding.hint).toMatch(/ran without the configured path/i);
  });

  it('is ok, stating whether a cliPath is configured, when clean', () => {
    const result = selfCheck(
      input({ environment: environment({ settings: { path: '/x/settings.json', problem: null, cliPathConfigured: false } }) }),
    );
    const finding = findingFor(result, 'settings');
    expect(finding.level).toBe('ok');
    expect(finding.message).toMatch(/no cli path/i);
  });
});

describe('selfCheck — schemas', () => {
  it('is ok when nothing is unsupported', () => {
    const result = selfCheck(input({ handshake: answeredHandshake({ unsupported: {} }) }));
    expect(findingFor(result, 'schemas').level).toBe('ok');
  });

  it('is fail, naming each shape and rendering a null client version as "not declared"', () => {
    const result = selfCheck(
      input({
        handshake: answeredHandshake({
          unsupported: { project: { store: 3, client: 2 }, catalog: { store: 5, client: null } },
        }),
      }),
    );
    const finding = findingFor(result, 'schemas');
    expect(finding.level).toBe('fail');
    expect(finding.message).toContain('project (store v3, client v2)');
    expect(finding.message).toContain('catalog (store v5, client not declared)');
    expect(finding.message).not.toContain('null');
    expect(finding.hint).toMatch(/exit 4/);
  });

  it('is warn when the handshake did not answer', () => {
    const result = selfCheck(input({ handshake: unknownHandshake() }));
    expect(findingFor(result, 'schemas').level).toBe('warn');
  });
});

describe('selfCheck — actions', () => {
  it('is ok when nothing is withheld', () => {
    const result = selfCheck(input({ environment: environment({ withheld: [] }) }));
    const finding = findingFor(result, 'actions');
    expect(finding.level).toBe('ok');
    expect(finding.message).toMatch(/no command is being withheld/i);
  });

  it('is warn, listing command and reason, when something is withheld', () => {
    const result = selfCheck(
      input({ environment: environment({ withheld: [{ command: 'bind', reason: 'declaration failed' }] }) }),
    );
    const finding = findingFor(result, 'actions');
    expect(finding.level).toBe('warn');
    expect(finding.message).toContain('bind');
    expect(finding.message).toContain('declaration failed');
  });
});

describe('selfCheck — status roll-up', () => {
  it('is ok when every finding is ok', () => {
    expect(selfCheck(input()).status).toBe('ok');
  });

  it('is warn when the worst finding present is a warn', () => {
    const result = selfCheck(input({ handshake: unknownHandshake() }));
    expect(result.status).toBe('warn');
  });

  it('is fail when one fail is present among otherwise-ok findings', () => {
    const result = selfCheck(input({ resolution: notFoundResolution() }));
    expect(result.status).toBe('fail');
    // Confirms the mix: the other categories stayed ok around the one fail.
    expect(findingFor(result, 'declaration').level).toBe('ok');
    expect(findingFor(result, 'actions').level).toBe('ok');
  });
});
