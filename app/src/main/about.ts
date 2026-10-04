/**
 * The native About window: the app's name, its build, and which `devteam` it is talking to.
 *
 * ADR-0011 makes the app a client of one CLI, and "which `devteam` is this?" is the
 * question a user cannot answer from the outside. The answer used to crowd the header, then
 * sat on an in-app tab; it now lives where every desktop app keeps this kind of detail —
 * the platform's own About panel. macOS reaches it from the app menu for free; Windows has
 * no such item by default, so `aboutMenu` adds Help → About.
 *
 * `aboutCredits` is pure so a test can assert the text without an Electron runtime.
 */

import type { CliResolution, CliSource } from '../shared/api.js';

/** What the user sees in every menu, title and About panel. Not the package or bundle id. */
export const DISPLAY_NAME = 'Dev Team Agents';

/**
 * `appId` in `electron-builder.yml`, which a test keeps equal. Windows files a toast under
 * the process's AppUserModelID; left unset, Electron's default makes every notification
 * read "electron.app.Dev Team Agents" instead of the app's name and icon.
 */
export const APP_ID = 'com.devtoolbelt.dev-team-agents-app';

const SOURCE_LABEL: Record<CliSource, string> = {
  configured: 'configured path',
  path: 'PATH',
  homebrew: 'Homebrew',
  winget: 'winget',
  installer: 'devteam installer',
};

export interface AboutFacts {
  readonly appVersion: string;
  readonly electronVersion: string;
  readonly packaged: boolean;
  readonly codeSigned: boolean;
  readonly mutatingCommandsRun: readonly string[];
}

/** The multi-line block shown under the name and version. `null` resolution = not asked yet. */
export function aboutCredits(facts: AboutFacts, resolution: CliResolution | null): string {
  const lines: string[] = [];
  if (resolution === null) {
    lines.push('devteam CLI: not resolved yet');
  } else if (!resolution.found) {
    lines.push('devteam CLI: not found on this host');
  } else {
    const { cli } = resolution;
    lines.push(`devteam CLI: ${cli.path} (via ${SOURCE_LABEL[cli.source]})`);
    lines.push(`Store version: ${cli.storeVersion ?? 'not installed'}`);
    lines.push(`JSON contract: ${cli.jsonContract ?? 'unknown'}`);
  }
  lines.push(
    `Write actions: ${facts.mutatingCommandsRun.length > 0 ? facts.mutatingCommandsRun.join(', ') : 'none'}`,
  );
  lines.push(
    `Electron ${facts.electronVersion}${facts.packaged ? '' : ' · development'}${facts.codeSigned ? '' : ' · unsigned build'}`,
  );
  return lines.join('\n');
}
