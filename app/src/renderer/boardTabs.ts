/**
 * The board's tab strip as plain data: which project kanbans are open, in what order, and which
 * one is on show. `active` is `null` when the overview is on show; the overview tab is fixed and
 * never part of `order`. Every function returns a new value and leaves its input alone.
 */
export interface BoardTabs {
  readonly order: readonly string[];
  readonly active: string | null;
}

export const NO_TABS: BoardTabs = { order: [], active: null };

/** Shows the project's tab, appending it to the strip when it is not open yet. */
export function openTab(tabs: BoardTabs, projectId: string): BoardTabs {
  const order = tabs.order.includes(projectId) ? tabs.order : [...tabs.order, projectId];
  return { order, active: projectId };
}

/**
 * Closes a tab. Closing the one on show moves to its right-hand neighbour, else its left-hand
 * one, else the overview — what a browser does.
 */
export function closeTab(tabs: BoardTabs, projectId: string): BoardTabs {
  const index = tabs.order.indexOf(projectId);
  if (index === -1) return tabs;
  const order = tabs.order.filter((each) => each !== projectId);
  if (tabs.active !== projectId) return { order, active: tabs.active };
  return { order, active: order[index] ?? order[index - 1] ?? null };
}

/** Moves a tab to `toIndex` in the strip (clamped), the others keeping their relative order. */
export function moveTab(tabs: BoardTabs, projectId: string, toIndex: number): BoardTabs {
  const from = tabs.order.indexOf(projectId);
  if (from === -1) return tabs;
  const rest = tabs.order.filter((each) => each !== projectId);
  const to = Math.max(0, Math.min(rest.length, Math.trunc(toIndex)));
  if (to === from) return tabs;
  return { order: [...rest.slice(0, to), projectId, ...rest.slice(to)], active: tabs.active };
}

/**
 * Closes every tab whose project is not in `present`. When the tab on show is among them the
 * overview is shown instead of a neighbour — the user did not choose to leave, and the overview
 * is where the caller tells them why — and `closedActive` says so.
 */
export function pruneTabs(tabs: BoardTabs, present: ReadonlySet<string>): { tabs: BoardTabs; closedActive: boolean } {
  const order = tabs.order.filter((each) => present.has(each));
  if (order.length === tabs.order.length) return { tabs, closedActive: false };
  const closedActive = tabs.active !== null && !present.has(tabs.active);
  return { tabs: { order, active: closedActive ? null : tabs.active }, closedActive };
}
