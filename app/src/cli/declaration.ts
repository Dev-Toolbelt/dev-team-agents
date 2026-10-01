/**
 * What this app declares it understands, and the handshake that checks it.
 *
 * `APP_STORE_SCHEMAS` is **this app's own constant**. It is not read from the store,
 * and must never be: deriving the declaration from the thing it is being compared
 * against makes the comparison vacuous — it would report "compatible" against every
 * store, including one whose shapes this build has never seen. When a store shape
 * changes, a human edits the number here, in the same change that teaches the app to
 * read the new shape.
 *
 * Names and values come from `scripts/lib/devteam/compat.py` → `store_schemas()`, which
 * reads them from the modules that own them. Silence is not neutral: `compat.unsupported_by`
 * treats a shape this object omits as unsupported, so every key the store declares has
 * to be present here.
 */

import { randomBytes } from 'node:crypto';
import { rm, rename, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { invokeDevteam, type InvokeOptions } from './invoke.js';
import { ranAndAnswered, type CliResult } from './contract.js';
import type { HandshakeView, UnsupportedShape } from '../shared/api.js';

export const APP_STORE_SCHEMAS: Readonly<Record<string, number>> = Object.freeze({
  project: 1,
  project_layout: 2,
  registry: 1,
  bind_manifest: 1,
  credentials: 1,
  plugin_settings: 1,
  integrations: 1,
  integration_settings: 1,
});

/** The name of the declaration file this app writes, inside its own user-data dir. */
export const DECLARATION_FILE_NAME = 'client-schemas.json';

/**
 * Write the declaration where `--client-schemas` can read it, and return the path.
 *
 * A file rather than the `DEVTEAM_CLIENT_SCHEMAS` variable: the variable is ambient and
 * inherited, and `compat.client_declaration` documents the flag as winning precisely
 * because an inherited variable is the thing most likely to be stale. A flag on each
 * invocation says what *that* call believes.
 *
 * Written to a temp name in the same directory and then renamed into place, rather than
 * `writeFile(path, …)` directly. A direct write follows a symlink at `path` — a
 * pre-planted one would have been written through and truncated — and `{ mode: 0o600 }`
 * is a no-op when the file already exists, so a pre-planted world-writable file would
 * have kept its permissions. The temp file is created fresh (so its mode is honoured)
 * and `rename()` replaces whatever is at `path` — symlink or not — as a single
 * directory-entry swap rather than writing through it.
 */
export async function writeDeclarationFile(directory: string): Promise<string> {
  const path = join(directory, DECLARATION_FILE_NAME);
  const tempPath = join(directory, `.${DECLARATION_FILE_NAME}.${randomBytes(8).toString('hex')}.tmp`);
  await writeFile(tempPath, `${JSON.stringify(APP_STORE_SCHEMAS, null, 2)}\n`, {
    encoding: 'utf8',
    mode: 0o600,
    flag: 'wx', // exclusive create: refuse to follow anything already at the temp name too.
  });
  try {
    await rename(tempPath, path);
  } catch (error) {
    await rm(tempPath, { force: true });
    throw error;
  }
  return path;
}

// `UnsupportedShape` and the handshake view itself are declared once, in `shared/api.ts`
// — the type-only surface main, preload and renderer all import — and re-exported here
// under this module's own name so its callers need not change. Restating an identical
// shape here is what let it drift from `HandshakeView` with no import connecting them;
// `ipc.ts` bridged the two by direct assignment, relying on structural compatibility.
export type { UnsupportedShape };
export type Handshake = HandshakeView;

/**
 * Ask the framework whether this app may write, and translate the answer.
 *
 * `may_write` is read from the payload rather than derived from whether `unsupported`
 * is empty. `cmd_compat`'s own comment gives the reason: inference "is how a client
 * gets exactly this backwards".
 *
 * An incompatible client is **exit 1** here — a finding, not a failure. The question ran
 * and answered "no". Treating that as an error would be the classic misreading of this
 * CLI's exit table, and it would put the app into an error state on the one code path
 * whose whole job is to hand it a usable verdict.
 */
export async function performHandshake(
  options: Pick<InvokeOptions, 'binary' | 'cwd' | 'env' | 'timeoutMs'>,
): Promise<Handshake> {
  return (await performHandshakeCall(options)).view;
}

/**
 * The same handshake, with the two facts the caller has to state truthfully.
 *
 * `main/ipc.ts` renders the command it ran and how long it took. It used to fabricate them
 * — a literal `'devteam compat --json'` and `durationMs: 0` — while the real argument
 * vector (which carries `--client <inline declaration>`) and the real duration were right
 * here. A rendered claim that is not true is worse than no claim, so they are returned.
 */
export async function performHandshakeCall(
  options: Pick<InvokeOptions, 'binary' | 'cwd' | 'env' | 'timeoutMs'>,
): Promise<{ readonly view: Handshake; readonly command: string; readonly durationMs: number }> {
  const result = await invokeDevteam({
    ...options,
    // `--client` takes the declaration inline, so the handshake needs no file on disk
    // and cannot ask about a stale one. The `--client-schemas` file is for the gate on
    // every *other* call; here the question is about this build, right now.
    args: ['compat', '--client', JSON.stringify(APP_STORE_SCHEMAS)],
  });
  return { view: interpret(result), command: result.command.display, durationMs: result.durationMs };
}

function interpret(result: CliResult): Handshake {
  if (!ranAndAnswered(result)) {
    return {
      state: 'unknown',
      summary: 'The framework could not be asked whether this app is compatible, so the app stays read-only.',
      detail: describeFailure(result.outcome),
    };
  }

  if (result.outcome !== 'success' && result.outcome !== 'findings') {
    const message = result.document.kind === 'error' ? result.document.error : 'the command did not succeed';
    return {
      state: 'unknown',
      summary: 'The compatibility check did not complete, so the app stays read-only.',
      detail: `${result.command.display} exited ${result.exitCode}: ${message}`,
    };
  }

  if (result.document.kind === 'error') {
    return {
      state: 'unknown',
      summary: 'The compatibility check reported an error, so the app stays read-only.',
      detail: result.document.error,
    };
  }

  const body = result.document.body;
  const mayWrite = body['may_write'];
  if (typeof mayWrite !== 'boolean') {
    return {
      state: 'unknown',
      summary: 'The compatibility answer did not carry a verdict, so the app stays read-only.',
      detail: '`compat --json` returned no boolean `may_write`; the app will not guess one from `unsupported`.',
    };
  }

  const storeSchemas = asNumberMap(body['store_schemas']);
  const unsupported = asUnsupportedMap(body['unsupported']);
  const names = Object.keys(unsupported).sort();

  return {
    state: 'answered',
    mayWrite,
    jsonContract: typeof body['json_contract'] === 'number' ? body['json_contract'] : null,
    minAppVersion: typeof body['min_app_version'] === 'string' ? body['min_app_version'] : null,
    storeSchemas,
    clientSchemas: asNumberMap(body['client_schemas']) ?? APP_STORE_SCHEMAS,
    unsupported,
    // States what the *handshake* established and nothing else. It used to close with
    // "this build has no write actions yet", which was true when it was written and
    // became false the moment six of them landed — leaving the app contradicting itself
    // on one screen, the header listing every write action beside a card saying there
    // were none. What this build offers is `BuildInfo.hasWriteActions`' fact and the
    // header renders it; a fact with two homes eventually disagrees with itself, so this
    // one now has one.
    summary: mayWrite
      ? 'This app understands every shape the store uses, so the framework\'s write gate allows it to write.'
      : `The store keeps ${names.length === 1 ? 'a record' : 'records'} in ${names.length} shape${names.length === 1 ? '' : 's'} this app does not understand (${names
          .map((name) => `${name}: store ${unsupported[name]?.store ?? '?'}, this app ${unsupported[name]?.client ?? 'does not know it'}`)
          .join('; ')}). The app stays read-only — upgrade the app to write to this store.`,
  };
}

function describeFailure(outcome: 'contract-breach' | 'unavailable' | 'timeout'): string {
  switch (outcome) {
    case 'contract-breach':
      return '`devteam compat --json` did not return exactly one JSON document.';
    case 'unavailable':
      return 'The `devteam` CLI could not be started.';
    case 'timeout':
      return '`devteam compat --json` did not finish in time.';
  }
}

function asNumberMap(value: unknown): Readonly<Record<string, number>> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return {};
  const out: Record<string, number> = {};
  for (const [key, raw] of Object.entries(value as Record<string, unknown>)) {
    if (typeof raw === 'number') out[key] = raw;
  }
  return out;
}

function asUnsupportedMap(value: unknown): Readonly<Record<string, UnsupportedShape>> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return {};
  const out: Record<string, UnsupportedShape> = {};
  for (const [key, raw] of Object.entries(value as Record<string, unknown>)) {
    if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) continue;
    const entry = raw as Record<string, unknown>;
    out[key] = {
      store: typeof entry['store'] === 'number' ? entry['store'] : -1,
      client: typeof entry['client'] === 'number' ? entry['client'] : null,
    };
  }
  return out;
}
