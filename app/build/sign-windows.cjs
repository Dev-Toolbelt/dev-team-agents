/**
 * Authenticode signing through SSL.com eSigner (ADR-0055), for every Windows executable this
 * repository ships: the app's (as electron-builder's `win.signtoolOptions.sign` hook) and the
 * CLI installers (run as a script by `.github/workflows/windows-cli.yml`).
 *
 * The private key lives in SSL.com's cloud HSM, so there is no `.pfx` to hand electron-builder:
 * the file is sent to eSigner by CodeSignTool, which signs it in place. CodeSignTool is unpacked
 * by `.github/scripts/release/install-codesigntool.sh`, which exports where the tool and its Java
 * live and whether this is production or the eSigner sandbox.
 *
 *   - no WIN_ESIGNER_* credentials -> the hook does nothing and the build stays unsigned, exactly
 *     as before; `after-build.cjs` prints the UNSIGNED banner;
 *   - all four present            -> each executable is signed, and `after-build.cjs` inspects it;
 *   - some of them present        -> the build fails: a half-configured secret set is a mistake
 *     to report, not an unsigned build to ship quietly.
 *
 * Right before each signing the jar is hashed against the pin below and CodeSignTool's config is
 * written from the endpoints below, so a jar or config changed on disk after the install step
 * fails or is overwritten. That narrows tampering; it does not end it. Everything else that runs
 * in the job (this file, electron-builder, the dependencies `npm ci` installed) is inside the
 * signing trust boundary, and any process in the job can read CodeSignTool's command line, which
 * carries the credentials the way SSL.com's own GitHub Action passes them.
 */
const { spawnSync } = require('node:child_process');
const { createHash } = require('node:crypto');
const { existsSync, readFileSync, writeFileSync } = require('node:fs');
const { join, resolve } = require('node:path');

const CREDENTIALS = Object.freeze({
  username: 'WIN_ESIGNER_USERNAME',
  password: 'WIN_ESIGNER_PASSWORD',
  credential_id: 'WIN_ESIGNER_CREDENTIAL_ID',
  totp_secret: 'WIN_ESIGNER_TOTP_SECRET',
});

// The jar inside the CodeSignTool v1.3.2 zip that install-codesigntool.sh pins. Bump both together.
const JAR = 'code_sign_tool-1.3.2.jar';
const JAR_SHA256 = '312a4a00d21117fadbe1b876cdef8075df94a9d197328b46b7e168b5a5179bb8';

// SSL.com's public OAuth client ids and endpoints (they ship in the zip and in SSL.com's own
// GitHub Action), not secrets.
const ENDPOINTS = Object.freeze({
  PROD: {
    CLIENT_ID: 'kaXTRACNijSWsFdRKg_KAfD3fqrBlzMbWs6TwWHwAn8',
    OAUTH2_ENDPOINT: 'https://login.ssl.com/oauth2/token',
    CSC_API_ENDPOINT: 'https://cs.ssl.com',
  },
  TEST: {
    CLIENT_ID: 'qOUeZCCzSqgA93acB3LYq6lBNjgZdiOxQc-KayC3UMw',
    OAUTH2_ENDPOINT: 'https://oauth-sandbox.ssl.com/oauth2/token',
    CSC_API_ENDPOINT: 'https://cs-try.ssl.com',
  },
});

// CodeSignTool can exit 0 after failing, so its output is read as well (the same markers
// SSL.com's GitHub Action checks).
const FAILURE_MARKERS = /Error|Exception|Missing required option|Unmatched arguments/;

const SIGN_TIMEOUT_MS = 300_000;

const present = (env, name) => typeof env[name] === 'string' && env[name].trim() !== '';

/** `complete`, `none`, or `partial` with the names that are missing. */
function esignerCredentials(env = process.env) {
  const names = Object.values(CREDENTIALS);
  const missing = names.filter((name) => !present(env, name));
  if (missing.length === 0) return { state: 'complete', missing };
  if (missing.length === names.length) return { state: 'none', missing };
  return { state: 'partial', missing };
}

function properties(environment) {
  const endpoints = ENDPOINTS[environment];
  if (!endpoints) throw new Error(`WIN_ESIGNER_ENVIRONMENT must be PROD or TEST, not ${environment}.`);
  const lines = Object.entries(endpoints).map(([key, value]) => `${key}=${value}`);
  return [...lines, 'TSA_URL=http://ts.ssl.com', 'TSA_LEGACY_URL=http://ts.ssl.com/legacy', ''].join('\n');
}

/**
 * The verified jar and the java that runs it. Checks the jar against its pin and rewrites the
 * config for the selected environment every time, immediately before it is used.
 */
function codeSignTool(env = process.env, jarSha256 = JAR_SHA256) {
  const home = env.CODESIGNTOOL_HOME;
  const jar = home ? join(home, 'jar', JAR) : '';
  if (!home || !existsSync(jar)) {
    throw new Error(`No ${JAR} under CODESIGNTOOL_HOME: run .github/scripts/release/install-codesigntool.sh first.`);
  }
  const actual = createHash('sha256').update(readFileSync(jar)).digest('hex');
  if (actual !== jarSha256) {
    throw new Error(`${jar} does not match its pinned SHA-256 (got ${actual}); refusing to hand it the credentials.`);
  }
  writeFileSync(join(home, 'conf', 'code_sign_tool.properties'), properties(env.WIN_ESIGNER_ENVIRONMENT || 'PROD'));
  return { home, java: env.CODESIGNTOOL_JAVA || 'java', jar };
}

function signArgs(file, jar, env = process.env) {
  return [
    '-jar',
    jar,
    'sign',
    ...Object.entries(CREDENTIALS).map(([option, name]) => `-${option}=${env[name]}`),
    `-input_file_path=${resolve(file)}`,
    '-override',
  ];
}

function redact(text, env) {
  return Object.values(CREDENTIALS).reduce((out, name) => (present(env, name) ? out.split(env[name]).join('***') : out), text);
}

/** Signs one file in place, or throws with CodeSignTool's (redacted) output. */
function signFile(file, { env = process.env, spawn = spawnSync, jarSha256 = JAR_SHA256 } = {}) {
  const tool = codeSignTool(env, jarSha256);
  // CodeSignTool reads conf/code_sign_tool.properties relative to its working directory. A stalled
  // OAuth or TOTP exchange fails the signing instead of holding the job until its own timeout.
  const result = spawn(tool.java, signArgs(file, tool.jar, env), {
    cwd: tool.home,
    encoding: 'utf8',
    timeout: SIGN_TIMEOUT_MS,
  });
  const output = `${result.stdout || ''}${result.stderr || ''}`;
  if (result.error || result.status !== 0 || FAILURE_MARKERS.test(output)) {
    const reason = result.error ? result.error.message : redact(output, env).trim();
    throw new Error(`eSigner could not sign ${file}: ${reason || `exit ${result.status}`}`);
  }
}

/** The hook's decisions, with the environment and the process runner injectable for tests. */
function signWith(configuration, { env = process.env, spawn, jarSha256 } = {}) {
  // electron-builder.yml asks for sha256 only; an extra sha1 pass would be a second paid signing.
  if (configuration.hash && configuration.hash !== 'sha256') return;
  const credentials = esignerCredentials(env);
  if (credentials.state === 'partial') {
    throw new Error(`Windows signing is half-configured; missing: ${credentials.missing.join(', ')}.`);
  }
  if (credentials.state === 'none') {
    // Only WIN_CSC_LINK is refused. electron-builder also falls back to CSC_LINK, which on a Mac is the
    // macOS .p12 exported for `dist:all`; that one is left alone and the Windows half stays unsigned.
    if (present(env, 'WIN_CSC_LINK')) {
      throw new Error(
        'WIN_CSC_LINK is set, but Windows signing goes through eSigner only (ADR-0055). Set the WIN_ESIGNER_* variables instead.',
      );
    }
    return;
  }
  signFile(configuration.path, { env, spawn, jarSha256 });
}

/** electron-builder's hook. Its second argument is the Packager, so nothing is read from it. */
async function sign(configuration) {
  signWith(configuration);
}

module.exports = sign;
module.exports.default = sign;
module.exports.esignerCredentials = esignerCredentials;
module.exports.signArgs = signArgs;
module.exports.signFile = signFile;
module.exports.signWith = signWith;

// `node app/build/sign-windows.cjs <file>...` — the CLI installers, signed outside electron-builder.
if (require.main === module) {
  const files = process.argv.slice(2);
  const credentials = esignerCredentials();
  if (files.length === 0 || credentials.state !== 'complete') {
    process.stderr.write(
      files.length === 0 ? 'usage: node app/build/sign-windows.cjs <file>...\n' : `missing: ${credentials.missing.join(', ')}\n`,
    );
    process.exit(2);
  }
  try {
    for (const file of files) {
      signFile(file);
      process.stdout.write(`signed ${file}\n`);
    }
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exit(1);
  }
}
