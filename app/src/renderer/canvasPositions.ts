/**
 * Where the user dragged canvas nodes, per project (ADR-0063 § 6). App-local and renderer-only:
 * kept in `localStorage`, never sent to the CLI. Node ids already carry their session id, so one
 * record per project, keyed by node id, covers the (project, session, node) scope. Every read is
 * validated, and a storage that throws (quota, disabled) degrades to "no overrides".
 */
import type { Overrides, XY } from './canvasModel.js';

const PREFIX = 'devteam.canvas.positions.v1:';
/** A ceiling on stored ids per project, so a long-lived project cannot grow the record forever. */
const MAX_ENTRIES = 2000;

function storage(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage;
  } catch {
    return null;
  }
}

function isXY(value: unknown): value is XY {
  if (typeof value !== 'object' || value === null) return false;
  const { x, y } = value as Record<string, unknown>;
  return typeof x === 'number' && typeof y === 'number' && Number.isFinite(x) && Number.isFinite(y);
}

export function loadPositions(projectId: string): Overrides {
  const store = storage();
  if (store === null) return {};
  try {
    const raw = store.getItem(PREFIX + projectId);
    if (raw === null) return {};
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return {};
    // No prototype, so a stored `__proto__` key is just a key.
    const out: Record<string, XY> = Object.create(null) as Record<string, XY>;
    for (const [id, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (id !== '__proto__' && isXY(value)) out[id] = { x: value.x, y: value.y };
    }
    return out;
  } catch {
    return {};
  }
}

function write(projectId: string, positions: Overrides): void {
  const store = storage();
  if (store === null) return;
  try {
    if (Object.keys(positions).length === 0) store.removeItem(PREFIX + projectId);
    else store.setItem(PREFIX + projectId, JSON.stringify(positions));
  } catch {
    // Not persisted; the in-memory overrides still apply for this session.
  }
}

/** Stores one node's position and returns the project's new overrides. */
export function savePosition(projectId: string, nodeId: string, at: XY): Overrides {
  if (!isXY(at)) return loadPositions(projectId);
  if (nodeId === '__proto__') return loadPositions(projectId);
  const current: Record<string, XY> = Object.assign(Object.create(null) as Record<string, XY>, loadPositions(projectId));
  delete current[nodeId];
  const ids = Object.keys(current);
  for (const stale of ids.slice(0, Math.max(0, ids.length - (MAX_ENTRIES - 1)))) delete current[stale];
  current[nodeId] = { x: Math.round(at.x), y: Math.round(at.y) };
  const next = current;
  write(projectId, next);
  return next;
}

/** "Reset layout": forgets every dragged position of the project. */
export function clearPositions(projectId: string): void {
  write(projectId, {});
}
