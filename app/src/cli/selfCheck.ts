/**
 * Evaluates this app's own preconditions into an `AppHealth` report.
 *
 * `devteam doctor` diagnoses the store, the machine, the registry and a project — never
 * the app, and it must not (ADR-0015: the app is a pure client of the CLI; teaching the
 * CLI to check its callers would invert that dependency). The values this module reads —
 * `BuildInfo`, `EnvironmentReport`, `CliResolution`, the `compat` handshake — were already
 * observable through the bridge before this file existed; nothing *evaluated* them, so
 * "is this app healthy, and is it too old for this store?" had no answer anywhere in the
 * UI. This is that evaluation.
 *
 * Pure and synchronous on purpose: no IPC, no `window`, no `process`. It adds no channel
 * and no spawn — everything it needs, the bridge already returns for other screens — so it
 * lives in `src/cli/` (importable from a Node test without a DOM) rather than beside the
 * renderer that calls it.
 */

import type {
  AppFinding,
  AppHealth,
  BuildInfo,
  CliResolution,
  DeclarationState,
  EnvironmentReport,
  HandshakeView,
  OperationResult,
} from '../shared/api.js';

export interface SelfCheckInput {
  readonly build: BuildInfo;
  readonly environment: EnvironmentReport;
  readonly resolution: CliResolution;
  readonly handshake: OperationResult<HandshakeView>;
}

const LEVEL_RANK: Readonly<Record<AppFinding['level'], number>> = { ok: 0, warn: 1, fail: 2 };

export function selfCheck(input: SelfCheckInput): AppHealth {
  const findings: readonly AppFinding[] = [
    cliFinding(input.resolution),
    versionFinding(input.build, input.handshake),
    declarationFinding(input.environment.declaration),
    settingsFinding(input.environment.settings),
    schemasFinding(input.handshake),
    actionsFinding(input.environment.withheld),
  ];

  const status = findings.reduce<AppFinding['level']>(
    (worst, finding) => (LEVEL_RANK[finding.level] > LEVEL_RANK[worst] ? finding.level : worst),
    'ok',
  );

  return { status, findings };
}

function cliFinding(resolution: CliResolution): AppFinding {
  if (resolution.found) {
    return {
      level: 'ok',
      category: 'cli',
      message: `Found devteam at ${resolution.cli.path} (resolved via ${resolution.cli.sourceDetail}).`,
    };
  }
  return {
    level: 'fail',
    category: 'cli',
    message: `No devteam CLI could be found — searched ${resolution.searchedCount} location(s).`,
    // The main process already computed this; inventing a second remedy here would risk
    // it drifting from the one `resolve.ts` maintains next to the search order itself.
    hint: resolution.remedy.join(' '),
  };
}

function versionFinding(build: BuildInfo, handshake: OperationResult<HandshakeView>): AppFinding {
  if (!handshake.ok) {
    return {
      level: 'warn',
      category: 'version',
      message: "Could not compare this app's version against the store's minimum — the handshake did not answer.",
      hint: handshake.message,
    };
  }
  if (handshake.data.state === 'unknown') {
    return {
      level: 'warn',
      category: 'version',
      message: "Could not compare this app's version against the store's minimum — the handshake did not answer.",
      hint: handshake.data.detail,
    };
  }

  const { minAppVersion } = handshake.data;
  // `compat.MIN_APP_VERSION` is `None` until an app is released — this is today's state,
  // on purpose, and it is not a problem to report as one.
  if (minAppVersion === null) {
    return {
      level: 'ok',
      category: 'version',
      message: `The store asserts no minimum app version yet — v${build.appVersion} is accepted.`,
    };
  }

  const comparison = compareVersions(build.appVersion, minAppVersion);
  if (comparison === null) {
    return {
      level: 'warn',
      category: 'version',
      message: `Could not compare this app's version (${build.appVersion}) against the store's minimum (${minAppVersion}) — at least one is not a plain X.Y.Z release.`,
    };
  }

  if (comparison >= 0) {
    return {
      level: 'ok',
      category: 'version',
      message: `This app (v${build.appVersion}) meets the store's minimum (v${minAppVersion}).`,
    };
  }

  return {
    level: 'fail',
    category: 'version',
    message: `This app (v${build.appVersion}) is older than the store's minimum (v${minAppVersion}).`,
    hint: 'Update the app. Until then, the framework refuses every mutating command from it at exit 4.',
  };
}

function declarationFinding(declaration: DeclarationState): AppFinding {
  if (declaration.state === 'written') {
    return {
      level: 'ok',
      category: 'declaration',
      message: `Client schema declaration written to ${declaration.path}.`,
    };
  }
  return {
    level: 'fail',
    category: 'declaration',
    message: `Could not write the client schema declaration to ${declaration.path}.`,
    hint: `${declaration.detail} Without a written declaration the framework's client gate has nothing to compare against, so mutating commands are refused.`,
  };
}

function settingsFinding(settings: EnvironmentReport['settings']): AppFinding {
  if (settings.problem !== null) {
    return {
      level: 'warn',
      category: 'settings',
      message: `The settings file at ${settings.path} could not be used: ${settings.problem}`,
      hint: 'The CLI search ran without the configured path.',
    };
  }
  return {
    level: 'ok',
    category: 'settings',
    message: settings.cliPathConfigured
      ? `Settings at ${settings.path} configure a CLI path.`
      : `Settings at ${settings.path} configure no CLI path.`,
  };
}

function schemasFinding(handshake: OperationResult<HandshakeView>): AppFinding {
  // Mirrors `versionFinding`'s unknown-handshake branch: there is no `unsupported` to
  // read yet, and that is itself worth a warning rather than a silent `ok`.
  if (!handshake.ok || handshake.data.state === 'unknown') {
    return {
      level: 'warn',
      category: 'schemas',
      message: 'Could not check schema compatibility — the handshake did not answer.',
    };
  }

  const shapes = Object.entries(handshake.data.unsupported);
  if (shapes.length === 0) {
    return { level: 'ok', category: 'schemas', message: 'Every store schema this app uses is supported.' };
  }

  const detail = shapes
    .map(([shape, { store, client }]) => `${shape} (store v${store}, client ${client === null ? 'not declared' : `v${client}`})`)
    .join(', ');
  return {
    level: 'fail',
    category: 'schemas',
    message: `The store is ahead of what this app declares for: ${detail}.`,
    hint: 'Mutating commands are refused at exit 4 for exactly this reason.',
  };
}

function actionsFinding(withheld: EnvironmentReport['withheld']): AppFinding {
  if (withheld.length === 0) {
    return { level: 'ok', category: 'actions', message: 'No command is being withheld.' };
  }
  const detail = withheld.map((one) => `${one.command} — ${one.reason}`).join('; ');
  return { level: 'warn', category: 'actions', message: `This app is withholding: ${detail}` };
}

/**
 * Parses a plain `X.Y.Z` release, optionally prefixed with `v`. Returns `null` for
 * anything else — including a pre-release suffix such as `1.2.3-beta.1`. Ordering a
 * pre-release against a plain release is not a total order either side has committed to
 * here, so the honest cheap rule is: a suffix that cannot be ordered makes the version
 * not comparable, reported as `warn`, never guessed at as a silent pass or fail.
 */
function parseVersion(raw: string): readonly [number, number, number] | null {
  const match = /^v?(\d+)\.(\d+)\.(\d+)$/.exec(raw.trim());
  if (match === null) return null;
  return [Number(match[1]), Number(match[2]), Number(match[3])];
}

/** `-1` / `0` / `1`, or `null` when either side could not be parsed as `X.Y.Z`. */
function compareVersions(a: string, b: string): -1 | 0 | 1 | null {
  const left = parseVersion(a);
  const right = parseVersion(b);
  if (left === null || right === null) return null;
  const [leftMajor, leftMinor, leftPatch] = left;
  const [rightMajor, rightMinor, rightPatch] = right;
  if (leftMajor !== rightMajor) return leftMajor < rightMajor ? -1 : 1;
  if (leftMinor !== rightMinor) return leftMinor < rightMinor ? -1 : 1;
  if (leftPatch !== rightPatch) return leftPatch < rightPatch ? -1 : 1;
  return 0;
}
