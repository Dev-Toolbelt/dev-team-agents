import { toast } from 'sonner';

import { problemTitle } from './Problem.js';
import type { OperationResult } from '../shared/api.js';

/** How long a success stays up. A notice gets longer: it is a sentence the user has to read. */
const SUCCESS_MS = 4_000;
const NOTICE_MS = 12_000;

/**
 * A write action's outcome, reported as a toast rather than written into the screen.
 *
 * Results used to render inline beside the button that started them — inside a table cell,
 * which pushed the row's height and width around. A toast is out of the layout, and it goes
 * away, so a stale result is never waiting on screen when the user comes back to the tab.
 *
 * A failure stays until it is closed: a toast that fades on its own is how a failed write
 * goes unread. A success that carried a stderr `notice` keeps that notice verbatim — see
 * `Notice` in `WriteButton.tsx` for why it matters.
 */
export function toastResult(result: OperationResult<unknown>, success: string, id?: string): void {
  if (!result.ok) {
    toastFailure(result, id);
    return;
  }
  if (result.notice !== undefined) {
    toast.warning(`${success} — the command reported this`, {
      ...idOf(id),
      description: <p className="whitespace-pre-wrap font-mono text-xs">{result.notice}</p>,
      duration: NOTICE_MS,
      closeButton: true,
    });
    return;
  }
  toast.success(success, { ...idOf(id), duration: SUCCESS_MS });
}

/**
 * A failed operation, kept until it is closed. `id` lets a retry of the same action replace
 * its earlier failure instead of stacking a second one under it.
 */
export function toastFailure(result: Extract<OperationResult<unknown>, { ok: false }>, id?: string): void {
  toast.error(problemTitle(result), {
    ...idOf(id),
    description: (
      <>
        <p>{result.message}</p>
        {result.hint !== undefined ? <p className="opacity-80">{result.hint}</p> : null}
      </>
    ),
    duration: Infinity,
    closeButton: true,
  });
}

/**
 * A command that succeeded but could not do all of it — `sync --all` with problems. Reported
 * as a failure: a green toast that fades is how "3 could not be synced" goes unread.
 */
export function toastPartialFailure(title: string, notice?: string): void {
  toast.error(title, {
    description: notice !== undefined ? <p className="whitespace-pre-wrap font-mono text-xs">{notice}</p> : undefined,
    duration: Infinity,
    closeButton: true,
  });
}

/** Sonner's options are exact: an `id` key set to `undefined` is not the same as no key. */
function idOf(id: string | undefined): { id?: string } {
  return id === undefined ? {} : { id };
}

/** A batch with per-item failures: one toast, failures listed, kept until closed when any failed. */
export function toastBatch(title: string, failures: readonly { readonly id: string; readonly name: string; readonly message: string }[]): void {
  if (failures.length === 0) {
    toast.success(title, { duration: SUCCESS_MS });
    return;
  }
  toast.error(title, {
    description: (
      <ul className="list-disc pl-4">
        {failures.map((failure) => (
          <li key={failure.id}>
            <span className="font-medium">{failure.name}</span>: {failure.message}
          </li>
        ))}
      </ul>
    ),
    duration: Infinity,
    closeButton: true,
  });
}
