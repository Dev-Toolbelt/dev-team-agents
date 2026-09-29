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
  /**
   * A re-run is in flight over a result that is still on screen.
   *
   * Separate from `phase: 'loading'` because a **reload must not blank the screen**, and
   * that is a correctness property here, not a preference. Every write action reloads the
   * project list on success; when a reload reset the state to `loading`, the whole table was
   * replaced by a spinner, which unmounted every row — including the row whose success
   * notice had just been set. The notice was therefore unreadable by construction: the
   * thing that produced it also destroyed the component that showed it. A render test
   * caught it. So the first load blanks, a reload does not, and a caller that wants to
   * indicate the refresh reads this flag.
   */
  refreshing: boolean;
  reload: () => void;
} {
  const [state, setState] = useState<Load<T>>({ phase: 'loading' });
  const [refreshing, setRefreshing] = useState(false);
  const [nonce, setNonce] = useState(0);

  // `operation` is a fresh closure on every render, so it cannot be the identity that
  // decides when to re-run; `deps` is what the caller declares as the real one. This is the
  // same contract `useCallback` has, stated here because the argument is passed through.
  const run = useCallback(operation, deps);

  useEffect(() => {
    let live = true;
    // Keep a result that is already on screen; only the first load shows nothing.
    setState((previous) => (previous.phase === 'done' ? previous : { phase: 'loading' }));
    setRefreshing(true);
    void run().then(
      (result) => {
        if (!live) return;
        setState({ phase: 'done', result });
        setRefreshing(false);
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
        setRefreshing(false);
      },
    );
    return () => {
      live = false;
    };
  }, [run, nonce]);

  return { state, refreshing, reload: () => setNonce((n) => n + 1) };
}

/** One imperative mutation's state: idle until `run` is called, then its last result. */
export type ActionState<T> =
  | { readonly phase: 'idle' }
  | { readonly phase: 'pending' }
  | { readonly phase: 'done'; readonly result: T };

/**
 * An imperative write action, as opposed to `useOperation`'s load-on-mount read.
 *
 * Every write in `Projects.tsx` needs the same three things — a pending flag while the CLI
 * process runs, the last result to render, and a way to clear both when a dialog closes —
 * and hand-rolling that per button is exactly the kind of state that drifts (one row
 * forgets to reset on close, another double-fires while pending). `run` returns the result
 * too, so a caller that needs to act on success (closing a dialog, reloading the project
 * list) does not have to wait for a re-render to read it back out of state.
 *
 * Generic over the resolved type `T` rather than pinned to `OperationResult` — every write
 * action returns one *except* `chooseProjectDirectory`, which answers with a bare
 * `DirectoryChoice` because it spawns nothing for the framework's gate to refuse. Pinning
 * this hook to `OperationResult` would have made that one action unusable with it.
 */
export function useAction<Args extends unknown[], T>(action: (...args: Args) => Promise<T>): {
  state: ActionState<T>;
  run: (...args: Args) => Promise<T>;
  reset: () => void;
} {
  const [state, setState] = useState<ActionState<T>>({ phase: 'idle' });

  const run = useCallback(
    async (...args: Args) => {
      setState({ phase: 'pending' });
      const result = await action(...args);
      setState({ phase: 'done', result });
      return result;
    },
    [action],
  );

  const reset = useCallback(() => setState({ phase: 'idle' }), []);

  return { state, run, reset };
}
