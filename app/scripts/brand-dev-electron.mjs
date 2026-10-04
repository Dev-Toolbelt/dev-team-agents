/**
 * Give the development Electron bundle the app's name and icon. macOS only.
 *
 * `npm start` and `npm run dev:app` run the stock `Electron.app` from `node_modules`, and
 * macOS reads the menu-bar title, the ⌘-Tab name, Activity Monitor and a notification's
 * sender from that bundle's `Info.plist` and `electron.icns` — `app.setName` and
 * `dock.setIcon` cannot reach them. So the copy in `node_modules` is rewritten in place:
 * `CFBundleName` / `CFBundleDisplayName`, the icon from `build/icon.icns`, then an ad-hoc
 * re-sign, because the edit breaks the bundle's seal and Apple Silicon refuses to launch an
 * invalid one. A packaged build never runs this: electron-builder brands its own bundle.
 *
 * Idempotent and silent on success. Every failure is a warning, never an exit code: an
 * unbranded development app is what ran before this script existed. A fresh `npm ci`
 * restores the stock bundle, and the next start brands it again.
 */
import { execFileSync } from 'node:child_process';
import { copyFileSync, existsSync, readFileSync, utimesSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const NAME = 'Dev Team Agents';
const APP_DIR = join(dirname(fileURLToPath(import.meta.url)), '..');
const ELECTRON_DIR = join(APP_DIR, 'node_modules', 'electron');
const BUNDLE = join(ELECTRON_DIR, 'dist', 'Electron.app');
const PLIST = join(BUNDLE, 'Contents', 'Info.plist');
const BUNDLE_ICON = join(BUNDLE, 'Contents', 'Resources', 'electron.icns');
const BRAND_ICON = join(APP_DIR, 'build', 'icon.icns');

const warn = (message) => console.warn(`brand-dev-electron: ${message} The app still starts, with Electron's name and icon.`);
const run = (file, args) => execFileSync(file, args, { stdio: ['ignore', 'pipe', 'pipe'] }).toString().trim();

function plistValue(key) {
  try {
    return run('/usr/libexec/PlistBuddy', ['-c', `Print :${key}`, PLIST]);
  } catch {
    return null;
  }
}

function brand() {
  if (process.platform !== 'darwin') return;
  // Electron fetches its binary on first use, not at install time (see README § Install);
  // fetching it here is what `electron .` would otherwise do a moment later.
  if (!existsSync(BUNDLE)) execFileSync(process.execPath, [join(ELECTRON_DIR, 'install.js')], { stdio: 'inherit' });
  if (!existsSync(PLIST)) return warn('no Electron.app was found under node_modules.');

  const iconCurrent = existsSync(BUNDLE_ICON) && readFileSync(BUNDLE_ICON).equals(readFileSync(BRAND_ICON));
  if (plistValue('CFBundleName') === NAME && plistValue('CFBundleDisplayName') === NAME && iconCurrent) return;

  for (const key of ['CFBundleName', 'CFBundleDisplayName']) run('plutil', ['-replace', key, '-string', NAME, PLIST]);
  copyFileSync(BRAND_ICON, BUNDLE_ICON);
  run('codesign', ['--force', '--deep', '--sign', '-', BUNDLE]);
  // A new mtime is what makes LaunchServices and the Dock read the bundle again.
  const now = new Date();
  utimesSync(BUNDLE, now, now);
}

try {
  brand();
} catch (error) {
  warn(`branding failed (${error instanceof Error ? error.message.split('\n')[0] : String(error)}).`);
}
