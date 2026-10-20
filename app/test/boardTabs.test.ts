/**
 * The board's tab strip as data: opening, closing, reordering and pruning project tabs.
 */
import { describe, expect, it } from 'vitest';

import { NO_TABS, closeTab, moveTab, openTab, pruneTabs, type BoardTabs } from '../src/renderer/boardTabs.js';

const tabs = (order: string[], active: string | null): BoardTabs => ({ order, active });

describe('openTab', () => {
  it('appends a new tab and shows it', () => {
    expect(openTab(NO_TABS, 'a')).toEqual(tabs(['a'], 'a'));
    expect(openTab(tabs(['a'], 'a'), 'b')).toEqual(tabs(['a', 'b'], 'b'));
  });

  it('shows an open tab without moving or duplicating it', () => {
    expect(openTab(tabs(['a', 'b'], null), 'a')).toEqual(tabs(['a', 'b'], 'a'));
  });
});

describe('closeTab', () => {
  it('closing the tab on show moves to the right-hand neighbour, else the left, else the overview', () => {
    expect(closeTab(tabs(['a', 'b', 'c'], 'b'), 'b')).toEqual(tabs(['a', 'c'], 'c'));
    expect(closeTab(tabs(['a', 'b', 'c'], 'c'), 'c')).toEqual(tabs(['a', 'b'], 'b'));
    expect(closeTab(tabs(['a'], 'a'), 'a')).toEqual(tabs([], null));
  });

  it('closing another tab keeps the one on show', () => {
    expect(closeTab(tabs(['a', 'b'], 'b'), 'a')).toEqual(tabs(['b'], 'b'));
    expect(closeTab(tabs(['a', 'b'], null), 'a')).toEqual(tabs(['b'], null));
  });

  it('ignores a tab that is not open', () => {
    const before = tabs(['a'], 'a');
    expect(closeTab(before, 'x')).toBe(before);
  });
});

describe('moveTab', () => {
  it('moves a tab to the given index, keeping the others in order and the active tab', () => {
    expect(moveTab(tabs(['a', 'b', 'c'], 'b'), 'a', 2)).toEqual(tabs(['b', 'c', 'a'], 'b'));
    expect(moveTab(tabs(['a', 'b', 'c'], 'b'), 'c', 0)).toEqual(tabs(['c', 'a', 'b'], 'b'));
  });

  it('clamps the index and returns the same value when nothing moves', () => {
    expect(moveTab(tabs(['a', 'b'], null), 'a', 99)).toEqual(tabs(['b', 'a'], null));
    expect(moveTab(tabs(['a', 'b'], null), 'b', -5)).toEqual(tabs(['b', 'a'], null));
    const before = tabs(['a', 'b'], null);
    expect(moveTab(before, 'a', 0)).toBe(before);
    expect(moveTab(before, 'x', 1)).toBe(before);
  });
});

describe('pruneTabs', () => {
  it('closes tabs of projects that are gone and shows the overview when the one on show went', () => {
    expect(pruneTabs(tabs(['a', 'b'], 'a'), new Set(['b']))).toEqual({ tabs: tabs(['b'], null), closedActive: true });
  });

  it('keeps the tab on show when only others went', () => {
    expect(pruneTabs(tabs(['a', 'b'], 'b'), new Set(['b']))).toEqual({ tabs: tabs(['b'], 'b'), closedActive: false });
  });

  it('returns the same value when every project is still there', () => {
    const before = tabs(['a'], 'a');
    expect(pruneTabs(before, new Set(['a', 'z'])).tabs).toBe(before);
  });
});
