import { useCallback, useEffect, useState } from 'react';

import type { OperationResult } from '../shared/api.js';

export type Load<T> =
  | { readonly phase: 'loading' }
  | { readonly phase: 'done'; readonly result: OperationResult<T> };

/**
 * Run one bridge operation and keep its result.
 *
 * There is no error branch beside `done`, because there is no operation that throws:
 * every failure mode the CLI has — exit 2, a malformed document, a missing binary, a
 * timeout — arrives as an `OperationResult` with `ok: false`, and the UI renders it the
 * same way it renders data. A `catch` here would be a second, weaker error path.
 */
export function useOperation<T>(operation: () => Promise<OperationResult<T>>, deps: readonly unknown[] = []): {
  state: Load<T>;
  reload: () => void;
} {
  const [state, setState] = useState<Load<T>>({ phase: 'loading' });
  const [nonce, setNonce] = useState(0);

  // `operation` is a fresh closure on every render, so it cannot be the identity that
  // decides when to re-run; `deps` is what the caller declares as the real one. This is the
  // same contract `useCallback` has, stated here because the argument is passed through.
  const run = useCallback(operation, deps);

  useEffect(() => {
    let live = true;
    setState({ phase: 'loading' });
    void run().then(
      (result) => {
        if (live) setState({ phase: 'done', result });
      },
      (error: unknown) => {
        // Only reachable if IPC itself fails — the handler is gone, or the main process
        // died. Surfaced rather than swallowed: a blank screen is the worse outcome.
        if (!live) return;
        setState({
          phase: 'done',
          result: {
            ok: false,
            kind: 'unavailable',
            message: `the app could not reach its own main process: ${String(error)}`,
            exitCode: null,
            command: '(ipc)',
            durationMs: 0,
          },
        });
      },
    );
    return () => {
      live = false;
    };
  }, [run, nonce]);

  return { state, reload: () => setNonce((n) => n + 1) };
}
