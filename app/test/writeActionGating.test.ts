import { describe, expect, it } from 'vitest';

import { isWithheld } from '../src/renderer/writeActionGating.js';

describe('isWithheld', () => {
  it('reports not withheld when the list is empty', () => {
    expect(isWithheld([], 'bind')).toEqual({ withheld: false });
  });

  it('reports withheld with the reason on an exact match', () => {
    const entries = [{ command: 'bind', reason: 'it can change the store and no schema declaration could be written' }];
    expect(isWithheld(entries, 'bind')).toEqual({
      withheld: true,
      reason: 'it can change the store and no schema declaration could be written',
    });
  });

  it('does not match a different command', () => {
    const entries = [{ command: 'doctor', reason: 'unrelated' }];
    expect(isWithheld(entries, 'bind')).toEqual({ withheld: false });
  });

  // Regression: a prefix match would let `pin` cover a future two-word leaf like
  // `pin release` withheld for an unrelated reason, silently hiding the wrong action.
  it('does not match on a shared prefix', () => {
    const entries = [{ command: 'pin release', reason: 'unrelated two-word leaf' }];
    expect(isWithheld(entries, 'pin')).toEqual({ withheld: false });
  });

  it('matches a two-word leaf exactly', () => {
    const entries = [{ command: 'store gc', reason: 'store is locked' }];
    expect(isWithheld(entries, 'store gc')).toEqual({ withheld: true, reason: 'store is locked' });
  });
});
