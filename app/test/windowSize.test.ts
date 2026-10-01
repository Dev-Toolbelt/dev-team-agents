import { describe, expect, it } from 'vitest';

import { windowSize } from '../src/main/windowSize.js';

describe('the main window size', () => {
  it('opens at most of a laptop work area, with a minimum the screens are laid out for', () => {
    expect(windowSize({ width: 1512, height: 944 })).toEqual({ width: 1285, height: 831, minWidth: 1024, minHeight: 680 });
  });

  it('caps the opening size on a large monitor', () => {
    expect(windowSize({ width: 3008, height: 1667 })).toMatchObject({ width: 1600, height: 1000 });
  });

  it('never asks for more than a small screen has', () => {
    const size = windowSize({ width: 900, height: 600 });
    expect(size).toEqual({ width: 900, height: 600, minWidth: 900, minHeight: 600 });
  });

  it('never opens below the minimum on a screen just above it', () => {
    const size = windowSize({ width: 1100, height: 720 });
    expect(size.width).toBeGreaterThanOrEqual(size.minWidth);
    expect(size.height).toBeGreaterThanOrEqual(size.minHeight);
  });
});
