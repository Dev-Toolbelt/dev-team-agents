import { useEffect, useRef } from 'react';

/**
 * Runs `callback` once each time `active` goes from true to false — the tab holding a screen
 * was left. Tabs here stay mounted (they hold drafts and live feeds), so leaving one does not
 * unmount it; this is the one place a screen hears that it is no longer on show.
 *
 * The callback is read through a ref, so it sees the render in which the tab was left (its
 * unsaved count, for instance) and a caller need not memoise it.
 */
export function useOnDeactivate(active: boolean, callback: () => void): void {
  const wasActive = useRef(active);
  const latest = useRef(callback);
  latest.current = callback;
  useEffect(() => {
    if (wasActive.current && !active) latest.current();
    wasActive.current = active;
  }, [active]);
}

/**
 * Runs `callback` once each time `active` goes from false to true — the tab holding a screen
 * was shown again. The mirror of {@link useOnDeactivate}, read through a ref the same way.
 */
export function useOnActivate(active: boolean, callback: () => void): void {
  const wasActive = useRef(active);
  const latest = useRef(callback);
  latest.current = callback;
  useEffect(() => {
    if (active && !wasActive.current) latest.current();
    wasActive.current = active;
  }, [active]);
}
