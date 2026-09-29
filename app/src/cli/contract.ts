/**
 * The `devteam --json` contract, as this app understands it.
 *
 * Sources of truth, not restated from memory:
 *   - `CLAUDE-md/cli.md` § The `--json` contract (exit-code table, one-document rule)
 *   - `scripts/lib/devteam/errors.py` (the same table, as constants)
 *   - `scripts/lib/devteam/output.py` (`Emitter.emit` / `Emitter.fail` — the two shapes)
 *   - `tests/test_json_contract.py` → `AppFacingKeySetContractTest.EXPECTED` (payload keys)
 *
 * Nothing in this file imports `electron`. The whole invocation layer is deliberately
 * runnable under plain node so it can be tested without a display; see
 * `test/invoke.test.ts` and `test/real-cli.test.ts`.
 */

/**
 * The documented exit codes, and the one place that states the set.
 *
 * `1` is **not** a failure: it means the command ran and reported a finding —
 * `devteam doctor` on a store with problems exits 1 with a complete payload, and
 * `devteam compat` exits 1 to say "this client may not write". Conflating 1 with
 * failure is the single most likely way this layer goes wrong, so each code gets its
 * own named outcome rather than a boolean.
 *
 * This was previously stated three times — this table, a separate `EXIT` object with
 * no runtime consumer, and `invoke.ts`'s `isDocumentedExit()` hardcoding the same five
 * numbers — so a sixth exit code required finding and updating all three, and
 * TypeScript caught only some of the drift. `ExitCode` and `isDocumentedExit()` are
 * now both derived from this object's keys; there is nothing else to keep in sync
 * within this app. (`scripts/lib/devteam/errors.py` states the same set on the Python
 * side; nothing cross-checks the two languages against each other today.)
 */
export const OUTCOME_BY_EXIT = {
  0: 'success',
  1: 'findings',
  2: 'usage',
  3: 'environment',
  4: 'conflict',
} as const;

export type ExitCode = keyof typeof OUTCOME_BY_EXIT;

export type DocumentOutcome = (typeof OUTCOME_BY_EXIT)[ExitCode];

/** `Emitter.emit`: a successful payload. Always carries `ok`. */
export interface SuccessDocument {
  readonly kind: 'payload';
  readonly ok: boolean;
  readonly body: Readonly<Record<string, unknown>>;
}

/** `Emitter.fail`: `DevteamError.payload()`. `hint` and `details` are optional. */
export interface ErrorDocument {
  readonly kind: 'error';
  readonly ok: false;
  readonly error: string;
  readonly exitCode: number;
  readonly hint?: string;
  readonly details?: Readonly<Record<string, unknown>>;
  readonly body: Readonly<Record<string, unknown>>;
}

export type CliDocument = SuccessDocument | ErrorDocument;

/**
 * Why a response was not usable. Every one of these is reported as a defect rather
 * than smoothed into an empty success — an app that renders "no projects" because the
 * CLI printed nothing is worse than one that says the CLI printed nothing.
 */
export type ContractBreachReason =
  /** stdout was empty or whitespace. The contract permits it in general; for a
   *  `--json` invocation of one of our named operations it is always a defect. */
  | 'empty-stdout'
  /** stdout held text that is not a JSON value at all. */
  | 'not-json'
  /** stdout held more than one top-level JSON document. */
  | 'multiple-documents'
  /** stdout held one JSON value that is not an object (`3`, `"x"`, `[]`). */
  | 'not-an-object'
  /** the object carried no `ok` field, which the contract says every document has. */
  | 'missing-ok'
  /** one document followed by trailing text that is not a JSON value. */
  | 'trailing-output'
  /** exit code outside the documented `{0,1,2,3,4}`. */
  | 'undocumented-exit-code'
  /** the child wrote more than `invoke.ts`'s `MAX_STREAM_BYTES` and was killed. */
  | 'stream-overflow';

export interface CommandDescription {
  /** The resolved binary, as spawned. */
  readonly binary: string;
  /** The argument vector, as spawned. Never joined into a shell string. */
  readonly args: readonly string[];
  /** A human-readable rendering, for messages only. Never executed. */
  readonly display: string;
}

/**
 * The result of one invocation. A discriminated union rather than throw/return,
 * because "exit 1 with a payload" and "exit 4 with an error document" are both
 * ordinary results the UI renders, not exceptions.
 */
export type CliResult =
  | {
      readonly outcome: DocumentOutcome;
      readonly exitCode: ExitCode;
      readonly document: CliDocument;
      readonly stderr: string;
      readonly command: CommandDescription;
      readonly durationMs: number;
    }
  | {
      /** The response did not conform. Reported, never treated as an empty success. */
      readonly outcome: 'contract-breach';
      readonly reason: ContractBreachReason;
      readonly detail: string;
      readonly exitCode: number | null;
      readonly stdout: string;
      readonly stderr: string;
      readonly command: CommandDescription;
      readonly durationMs: number;
    }
  | {
      /** The binary could not be run at all. */
      readonly outcome: 'unavailable';
      readonly reason: 'not-found' | 'not-executable' | 'spawn-failed';
      readonly detail: string;
      readonly command: CommandDescription;
      readonly durationMs: number;
    }
  | {
      /** The process outlived its budget and was killed. */
      readonly outcome: 'timeout';
      readonly timeoutMs: number;
      readonly signal: NodeJS.Signals;
      readonly stdout: string;
      readonly stderr: string;
      readonly command: CommandDescription;
      readonly durationMs: number;
    };

/** True for the two outcomes that carry a document the UI can render. */
export function ranAndAnswered(
  result: CliResult,
): result is Extract<CliResult, { document: CliDocument }> {
  return result.outcome !== 'contract-breach' && result.outcome !== 'unavailable' && result.outcome !== 'timeout';
}

/**
 * The one-line explanation shown to the user for anything that is not a plain
 * success. Kept beside the union so a new outcome cannot be added without a message.
 */
export function explain(result: CliResult): string {
  switch (result.outcome) {
    case 'success':
      return `${result.command.display} succeeded`;
    case 'findings':
      return `${result.command.display} ran and reported findings (exit 1)`;
    case 'usage':
      return `${result.command.display} rejected the request as malformed (exit 2)`;
    case 'environment':
      return `${result.command.display} cannot run in this environment (exit 3)`;
    case 'conflict':
      return `${result.command.display} was refused (exit 4)`;
    case 'contract-breach':
      return `${result.command.display} did not honour the --json contract: ${result.reason} — ${result.detail}`;
    case 'unavailable':
      return `${result.command.display} could not be started: ${result.detail}`;
    case 'timeout':
      return `${result.command.display} did not finish within ${result.timeoutMs} ms and was stopped with ${result.signal}`;
  }
}
