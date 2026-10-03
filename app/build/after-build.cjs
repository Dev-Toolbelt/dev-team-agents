/**
 * Runs after every artifact is built and states, truthfully, what was produced.
 *
 * Signing itself is electron-builder's, driven by the environment (see the header of
 * `electron-builder.yml`). This hook never signs anything. Its job is the opposite one:
 * make sure nobody walks away believing they hold something signed when they do not.
 *
 *   - no signing credentials for a platform  -> the UNSIGNED banner below, exactly as
 *     before, and nothing is claimed;
 *   - credentials present                    -> the artifact is INSPECTED (codesign and
 *     stapler on macOS, Get-AuthenticodeSignature on Windows). The SIGNED line is printed
 *     only for what the inspection confirmed, and credentials that produced an artifact
 *     which does not verify fail the build — they were meant to sign it.
 *
 * `release/signing-status.json` records the verdict per platform for the release workflow,
 * which still re-verifies the final artifacts itself (spctl, stapler, Authenticode)
 * before publishing a cask or winget manifest.
 */
const { spawnSync } = require('node:child_process');
const { existsSync, readdirSync, writeFileSync } = require('node:fs');
const { join } = require('node:path');

const present = (name) => typeof process.env[name] === 'string' && process.env[name].trim() !== '';

/** Credentials for macOS signing; notarisation has its own, so the two are reported apart. */
function macCredentials() {
  const sign = present('CSC_LINK') && present('CSC_KEY_PASSWORD');
  const notarize =
    (present('APPLE_ID') && present('APPLE_APP_SPECIFIC_PASSWORD') && present('APPLE_TEAM_ID')) ||
    (present('APPLE_API_KEY') && present('APPLE_API_KEY_ID') && present('APPLE_API_ISSUER'));
  return { sign, notarize };
}

function winCredentials() {
  const link = present('WIN_CSC_LINK') || present('CSC_LINK');
  const password = present('WIN_CSC_KEY_PASSWORD') || present('CSC_KEY_PASSWORD');
  return { sign: link && password };
}

function run(command, args) {
  const result = spawnSync(command, args, { encoding: 'utf8' });
  return {
    ok: !result.error && result.status === 0,
    output: `${result.stdout || ''}${result.stderr || ''}`,
  };
}

/** The `.app` bundles electron-builder leaves next to the dmg (`mac`, `mac-universal`, ...). */
function macApps(outDir) {
  const apps = [];
  for (const entry of readdirSync(outDir, { withFileTypes: true })) {
    if (!entry.isDirectory() || !entry.name.startsWith('mac')) continue;
    for (const inner of readdirSync(join(outDir, entry.name), { withFileTypes: true })) {
      if (inner.isDirectory() && inner.name.endsWith('.app')) apps.push(join(outDir, entry.name, inner.name));
    }
  }
  return apps;
}

function inspectMac(outDir) {
  const apps = macApps(outDir);
  if (process.platform !== 'darwin' || apps.length === 0) {
    return { state: 'unverified', detail: 'no .app bundle to inspect on this host' };
  }
  for (const app of apps) {
    const info = run('codesign', ['-dvv', app]);
    if (!/Authority=Developer ID Application/.test(info.output)) {
      return { state: 'unsigned', detail: `${app} has no Developer ID Application signature` };
    }
    if (!run('codesign', ['--verify', '--deep', '--strict', app]).ok) {
      return { state: 'unsigned', detail: `${app} fails codesign --verify` };
    }
    if (!run('xcrun', ['stapler', 'validate', app]).ok) {
      return { state: 'signed', detail: `${app} is signed but carries no notarisation ticket` };
    }
  }
  return { state: 'signed-notarised', detail: apps.join(', ') };
}

function inspectWin(artifactPaths) {
  const installers = artifactPaths.filter((path) => path.endsWith('.exe'));
  if (process.platform !== 'win32' || installers.length === 0) {
    return { state: 'unverified', detail: 'no installer to inspect on this host' };
  }
  for (const installer of installers) {
    const script = `(Get-AuthenticodeSignature -LiteralPath '${installer.replace(/'/g, "''")}').Status`;
    const result = run('powershell', ['-NoProfile', '-NonInteractive', '-Command', script]);
    if (result.output.trim() !== 'Valid') {
      return { state: 'unsigned', detail: `${installer}: Authenticode status ${result.output.trim() || 'unknown'}` };
    }
  }
  return { state: 'signed', detail: installers.join(', ') };
}

function unsignedBanner(context, reasons) {
  const bar = '='.repeat(78);
  return [
    '',
    bar,
    'UNSIGNED, UNNOTARISED BUILD — DIRECT-DOWNLOAD BETA ONLY',
    '',
    'No signing credentials were available for the platform(s) below, so nothing here has',
    'been through codesign, notarytool or signtool. ADR-0027 allows publishing it only as',
    'a beta GitHub Release built from an app-v<version> tag, next to SHA256SUMS.txt, with',
    'the download-page text in app/README.md. Never to the Homebrew cask or winget:',
    '`brew audit --cask` would reject it, and both manifests stay placeholders.',
    '',
    ...reasons.map((reason) => '  - ' + reason),
    '',
    'Artifacts: ' + (context.artifactPaths || []).join(', '),
    bar,
    '',
  ].join('\n');
}

module.exports = function afterAllArtifactBuild(context) {
  const outDir = context.outDir;
  const targets = Array.from((context.platformToTargets || new Map()).keys()).map((platform) => platform.name);
  const status = {};
  const unsignedReasons = [];
  const verifiedLines = [];

  if (targets.includes('mac')) {
    const credentials = macCredentials();
    if (!credentials.sign) {
      status.mac = 'unsigned';
      unsignedReasons.push('macOS: CSC_LINK / CSC_KEY_PASSWORD not set — built unsigned');
    } else {
      const verdict = inspectMac(outDir);
      status.mac = verdict.state;
      if (credentials.notarize && verdict.state !== 'signed-notarised') {
        throw new Error(`macOS signing and notarisation credentials were provided, but the build is ${verdict.state}: ${verdict.detail}`);
      }
      if (!credentials.notarize) {
        unsignedReasons.push('macOS: signed but NOT notarised — no APPLE_ID/APPLE_APP_SPECIFIC_PASSWORD/APPLE_TEAM_ID or APPLE_API_KEY/APPLE_API_KEY_ID/APPLE_API_ISSUER; Gatekeeper will still warn');
        if (verdict.state !== 'signed' && verdict.state !== 'signed-notarised') {
          throw new Error(`macOS signing credentials were provided, but the build is ${verdict.state}: ${verdict.detail}`);
        }
      } else {
        verifiedLines.push(`macOS: ${verdict.state} (${verdict.detail})`);
      }
    }
  }

  if (targets.includes('windows')) {
    const credentials = winCredentials();
    if (!credentials.sign) {
      status.win = 'unsigned';
      unsignedReasons.push('Windows: WIN_CSC_LINK / WIN_CSC_KEY_PASSWORD not set — built unsigned');
    } else {
      const verdict = inspectWin(context.artifactPaths || []);
      status.win = verdict.state;
      if (verdict.state !== 'signed') {
        throw new Error(`Windows signing credentials were provided, but the installers are ${verdict.state}: ${verdict.detail}`);
      }
      verifiedLines.push(`Windows: Authenticode Valid (${verdict.detail})`);
    }
  }

  if (existsSync(outDir)) {
    writeFileSync(join(outDir, 'signing-status.json'), JSON.stringify(status, null, 2) + '\n');
  }

  if (unsignedReasons.length > 0) {
    process.stderr.write(unsignedBanner(context, unsignedReasons));
  }
  if (verifiedLines.length > 0) {
    process.stderr.write(['', 'VERIFIED SIGNED:', ...verifiedLines.map((line) => '  - ' + line), ''].join('\n'));
  }
  return [];
};
