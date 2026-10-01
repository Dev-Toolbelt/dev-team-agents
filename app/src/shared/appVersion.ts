/**
 * Whether an app version is a pre-release — a build for testing, not one to rely on.
 *
 * Derived from the version rather than kept as a flag, so the header's "beta" badge cannot
 * outlive the beta: semver puts every `0.x` release and every version with a pre-release
 * suffix (`1.0.0-beta.1`) before a stable API, and the first plain `1.0.0` the release step
 * stamps into `app/package.json` drops the badge with no other change. A string that is not
 * a version at all is treated as a pre-release: claiming stability for it would be the
 * wrong way to be wrong.
 *
 * Pure, no imports: safe for the main process, the preload and the renderer alike.
 */
export function isPrerelease(version: string): boolean {
  const match = /^v?(\d+)\.(\d+)\.(\d+)(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$/.exec(version.trim());
  if (match === null) return true;
  return match[1] === '0' || match[4] !== undefined;
}
