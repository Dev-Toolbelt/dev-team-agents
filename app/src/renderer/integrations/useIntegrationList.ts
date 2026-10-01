import { useCallback, useEffect, useRef, useState } from 'react';

import type { IntegrationList, IntegrationView, ProjectId } from '../../shared/api.js';
import { useOperation } from '../useOperation.js';

/**
 * Loads `integration list` and keeps it current without a second round trip: every write
 * answers with the updated `IntegrationView`, so a card hands that back (`replace`) and the
 * list changes in place. A fresh load from the CLI wins over any local patch.
 *
 * Also aggregates the per-card unsaved-edit and running counts a screen reports upward.
 */
export function useIntegrationList(
  projectId: ProjectId | null,
  onDirtyChange?: (count: number) => void,
  onRunningChange?: (count: number) => void,
  /** The screen showing this list is visible; it reloads on each return, as `Projects` does. */
  active = true,
  /** Bumped by the owner whenever an account write succeeded elsewhere; a change reloads. */
  refreshNonce = 0,
) {
  const { state, refreshing, reload: rawReload } = useOperation(() => window.devteam.integrationList(projectId), [projectId]);
  // Each patch carries the write's sequence number, and each reload remembers the number it
  // started at: a reload that began before a write cannot know about it, so it only drops
  // the patches it can vouch for.
  const [patches, setPatches] = useState<Readonly<Record<string, { readonly view: IntegrationView; readonly seq: number }>>>({});
  const writeSeq = useRef(0);
  const reloadFrom = useRef(0);
  const reload = useCallback(() => {
    reloadFrom.current = writeSeq.current;
    rawReload();
  }, [rawReload]);
  const lastGood = useRef<IntegrationList | null>(null);
  const seen = useRef<unknown>(null);
  const subject = useRef(projectId);
  if (subject.current !== projectId) {
    // Another project's list (or none): neither its last answer nor its local patches apply.
    subject.current = projectId;
    lastGood.current = null;
    seen.current = null;
    setPatches({});
  }
  const reloadRef = useRef(reload);
  reloadRef.current = reload;
  const handled = useRef({ active, refreshNonce });
  useEffect(() => {
    const previous = handled.current;
    handled.current = { active, refreshNonce };
    if (active && (!previous.active || previous.refreshNonce !== refreshNonce)) reloadRef.current();
  }, [active, refreshNonce]);
  if (state.phase === 'done' && state.result.ok && seen.current !== state) {
    seen.current = state;
    lastGood.current = state.result.data;
  }
  useEffect(() => {
    if (state.phase !== 'done' || !state.result.ok) return;
    const covered = reloadFrom.current;
    setPatches((previous) => {
      const kept = Object.fromEntries(Object.entries(previous).filter(([, patch]) => patch.seq > covered));
      return Object.keys(kept).length === Object.keys(previous).length ? previous : kept;
    });
  }, [state]);

  const replace = useCallback((view: IntegrationView) => {
    writeSeq.current += 1;
    const seq = writeSeq.current;
    setPatches((previous) => ({ ...previous, [view.name]: { view, seq } }));
  }, []);

  const [openCards, setOpenCards] = useState<Readonly<Record<string, boolean>>>({});
  const setCardOpen = useCallback((name: string, open: boolean) => {
    setOpenCards((previous) => (previous[name] === open ? previous : { ...previous, [name]: open }));
  }, []);

  const [dirty, setDirty] = useState<Readonly<Record<string, number>>>({});
  const [running, setRunning] = useState<Readonly<Record<string, number>>>({});
  const track = useCallback(
    (set: React.Dispatch<React.SetStateAction<Readonly<Record<string, number>>>>) => (name: string, count: number) => {
      if (count > 0) setCardOpen(name, true);
      set((previous) => {
        if ((previous[name] ?? 0) === count) return previous;
        const next = { ...previous };
        if (count === 0) delete next[name];
        else next[name] = count;
        return next;
      });
    },
    [setCardOpen],
  );
  const cardDirty = useCallback((name: string, count: number) => track(setDirty)(name, count), [track]);
  const cardRunning = useCallback((name: string, count: number) => track(setRunning)(name, count), [track]);
  const dirtyTotal = Object.values(dirty).reduce((sum, count) => sum + count, 0);
  const runningTotal = Object.values(running).reduce((sum, count) => sum + count, 0);
  useEffect(() => onDirtyChange?.(dirtyTotal), [dirtyTotal, onDirtyChange]);
  useEffect(() => onRunningChange?.(runningTotal), [runningTotal, onRunningChange]);

  const list = lastGood.current;
  const views = list === null ? [] : list.integrations.map((view) => patches[view.name]?.view ?? view);
  const reloadProblem = state.phase === 'done' && !state.result.ok ? state.result : null;
  const lockedReason = (name: string): string | null =>
    (dirty[name] ?? 0) > 0 ? 'Save or discard changes first' : (running[name] ?? 0) > 0 ? 'An operation is running' : null;

  return { state, list, views, refreshing, reload, reloadProblem, replace, openCards, setCardOpen, cardDirty, cardRunning, lockedReason };
}
