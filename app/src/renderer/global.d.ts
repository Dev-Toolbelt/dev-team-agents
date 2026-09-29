import type { DevteamBridge } from '../shared/api.js';

/**
 * The only thing the preload puts on the window. Declared here so the renderer's
 * compile fails if it reaches for a capability the bridge does not expose, rather than
 * failing at runtime in a packaged build.
 */
declare global {
  interface Window {
    readonly devteam: DevteamBridge;
  }
}
