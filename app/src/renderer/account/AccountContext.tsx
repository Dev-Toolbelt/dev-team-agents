import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';

import { DEFAULT_GATE_MODE } from '../../shared/accountRules.js';
import type { AuthGateMode, AuthState, EntitlementStatus, OperationResult } from '../../shared/api.js';
import { unreachable } from '../useOperation.js';

/** What the shell needs to decide between the app, the account screens and a banner. */
export type AccountView =
  | { readonly kind: 'loading' }
  /** Entitled: nothing to say. */
  | { readonly kind: 'entitled'; readonly state: AuthState }
  /** Not entitled; `status` says why. `state` is the CLI's own document. */
  | { readonly kind: 'blocked'; readonly status: EntitlementStatus; readonly state: AuthState }
  /** The check itself failed (no account server, lock…): the account is unknown, not refused. */
  | { readonly kind: 'unknown' };

export interface AccountValue {
  readonly view: AccountView;
  readonly mode: AuthGateMode;
  /** Account whose profile and sign-out the header offers; `null` when signed out or unknown. */
  readonly state: AuthState | null;
  /** Ask the CLI again. Resolves once the answer is in. */
  readonly refresh: () => Promise<void>;
  /** A sign-in just produced this document: take it as the current answer. */
  readonly apply: (state: AuthState) => void;
}

const AccountContext = createContext<AccountValue | null>(null);

export function viewOf(result: OperationResult<AuthState>): AccountView {
  if (!result.ok) return { kind: 'unknown' };
  const state = result.data;
  return state.entitled
    ? { kind: 'entitled', state }
    : { kind: 'blocked', status: state.signed_in ? state.entitlement.status : 'signed_out', state };
}

/**
 * Holds the one answer to "is this account entitled?" (`auth check`), loaded when `enabled`
 * (once a CLI exists to ask) and refreshed on demand. Nothing here keeps a credential: the
 * document has none.
 */
export function AccountProvider({ enabled, children }: { enabled: boolean; children: ReactNode }) {
  const [view, setView] = useState<AccountView>({ kind: 'loading' });
  const [mode, setMode] = useState<AuthGateMode>(DEFAULT_GATE_MODE);
  const generation = useRef(0);

  const take = useCallback((result: OperationResult<AuthState>) => {
    setView(viewOf(result));
    if (result.ok) setMode(result.data.gate_mode);
  }, []);

  const refresh = useCallback(async () => {
    const mine = ++generation.current;
    let result: OperationResult<AuthState>;
    try {
      result = await window.devteam.authCheck();
    } catch (error) {
      result = unreachable(error);
    }
    // A slower, older answer must not overwrite a newer one (a sign-in landed meanwhile).
    if (mine === generation.current) take(result);
  }, [take]);

  const apply = useCallback(
    (state: AuthState) => {
      generation.current += 1;
      take({ ok: true, outcome: state.entitled ? 'success' : 'findings', data: state, command: 'devteam auth', durationMs: 0 });
    },
    [take],
  );

  useEffect(() => {
    if (enabled) void refresh();
  }, [enabled, refresh]);

  const value = useMemo<AccountValue>(
    () => ({
      view,
      mode,
      state: view.kind === 'entitled' || view.kind === 'blocked' ? (view.state.signed_in ? view.state : null) : null,
      refresh,
      apply,
    }),
    [view, mode, refresh, apply],
  );
  return <AccountContext.Provider value={value}>{children}</AccountContext.Provider>;
}

export function useAccount(): AccountValue {
  const value = useContext(AccountContext);
  if (value === null) throw new Error('useAccount needs an <AccountProvider>');
  return value;
}
