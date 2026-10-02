/**
 * Comparing directory paths the way the host file system does.
 *
 * The renderer holds paths as strings (a picked folder, a project's recorded path) and
 * asks "is this the same folder, or inside it?". A plain string compare answers wrongly on
 * the two platforms whose file systems are case-insensitive by default — `C:\Repo` and
 * `c:\repo` are one folder — and on Windows, where `\` and `/` separate the same way.
 *
 * This is for **display and gating only**. Nothing here is a security check: the CLI makes
 * the authoritative call about what a path is.
 */

type HostPlatform = 'darwin' | 'win32' | 'other';

/**
 * The renderer has no `process`, and exposing the platform over IPC for this would widen
 * the bridge for a hint. `navigator.platform` is enough to pick a comparison mode, and a
 * wrong guess degrades to the old case-sensitive compare.
 */
export function hostPlatformFrom(navigatorPlatform: string | undefined): HostPlatform {
  const value = navigatorPlatform ?? '';
  if (/^win/i.test(value)) return 'win32';
  if (/^mac/i.test(value)) return 'darwin';
  return 'other';
}

/**
 * Separators unified (Windows only), trailing separators dropped, case folded where the
 * file system folds it. A root survives intact: `/` stays `/`, `C:\` stays `c:/`.
 */
export function normalizeDirectory(path: string, platform: HostPlatform = 'other'): string {
  let out = platform === 'win32' ? path.replace(/\\/g, '/') : path;
  out = out.replace(/\/+$/, '');
  if (out === '') out = '/';
  else if (platform === 'win32' && /^[A-Za-z]:$/.test(out)) out = `${out}/`;
  return platform === 'other' ? out : out.toLowerCase();
}

/** `chosen` is `root`, or sits inside it, compared by whole path components. */
export function isSameOrInside(chosen: string, root: string, platform: HostPlatform = 'other'): boolean {
  const target = normalizeDirectory(chosen, platform);
  const base = normalizeDirectory(root, platform);
  return target === base || target.startsWith(base.endsWith('/') ? base : `${base}/`);
}

export function isSameDirectory(a: string, b: string, platform: HostPlatform = 'other'): boolean {
  return normalizeDirectory(a, platform) === normalizeDirectory(b, platform);
}
