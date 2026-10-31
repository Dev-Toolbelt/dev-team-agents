/**
 * `build/sign-windows.cjs` (ADR-0055): the electron-builder hook and script that sign Windows
 * executables through SSL.com eSigner. CodeSignTool itself is replaced by a fake `spawn` and a
 * fake jar, so these cover the decisions the hook makes — when to sign, when to refuse, what it
 * checks, writes and runs, and what it prints — not the signature, which the sandbox workflow
 * checks on a real runner.
 */
import { createHash } from 'node:crypto';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

type Env = Record<string, string | undefined>;
type SpawnResult = { status: number | null; stdout: string; stderr: string; error?: Error };
type Spawn = (command: string, args: string[], options: { cwd: string }) => SpawnResult;
type SignOptions = { env?: Env; spawn?: Spawn; jarSha256?: string };
type Configuration = { path: string; hash?: string; cscInfo?: unknown };

interface SignWindows {
  (configuration: Configuration, packager?: unknown): Promise<void>;
  esignerCredentials(env: Env): { state: 'complete' | 'none' | 'partial'; missing: string[] };
  signFile(file: string, options?: SignOptions): void;
  signWith(configuration: Configuration, options?: SignOptions): void;
}

const require = createRequire(import.meta.url);
const signWindows = require('../build/sign-windows.cjs') as SignWindows;

const CREDENTIALS = {
  WIN_ESIGNER_USERNAME: 'user@example.com',
  WIN_ESIGNER_PASSWORD: 'pa55-word',
  WIN_ESIGNER_CREDENTIAL_ID: '00000000-cred',
  WIN_ESIGNER_TOTP_SECRET: 'totp-secret-value',
};

const JAR_BYTES = 'fake CodeSignTool jar';
const JAR_SHA256 = createHash('sha256').update(JAR_BYTES).digest('hex');

type SpawnCall = { command: string; args: string[]; cwd: string };

let home: string;
let calls: SpawnCall[];

const fakeSpawn =
  (result: Partial<SpawnResult> = {}): Spawn =>
  (command, args, options) => {
    calls.push({ command, args, cwd: options.cwd });
    return { status: 0, stdout: 'Code signed successfully', stderr: '', ...result };
  };

beforeEach(() => {
  calls = [];
  home = mkdtempSync(join(tmpdir(), 'codesigntool-'));
  mkdirSync(join(home, 'jar'));
  mkdirSync(join(home, 'conf'));
  writeFileSync(join(home, 'jar', 'code_sign_tool-1.3.2.jar'), JAR_BYTES);
  writeFileSync(join(home, 'conf', 'code_sign_tool.properties'), 'CSC_API_ENDPOINT=https://attacker.example\n');
});

afterEach(() => {
  rmSync(home, { recursive: true, force: true });
});

const env = (extra: Record<string, string> = {}) => ({ CODESIGNTOOL_HOME: home, CODESIGNTOOL_JAVA: 'java17', ...extra });
const options = (extra: Record<string, string> = {}, spawn: Spawn = fakeSpawn()): SignOptions => ({
  env: env(extra),
  spawn,
  jarSha256: JAR_SHA256,
});
const properties = () => readFileSync(join(home, 'conf', 'code_sign_tool.properties'), 'utf8');

describe('esignerCredentials', () => {
  it('is complete only when all four are set', () => {
    expect(signWindows.esignerCredentials(CREDENTIALS).state).toBe('complete');
    expect(signWindows.esignerCredentials({}).state).toBe('none');
  });

  it('names what is missing from a partial set, treating blank as missing', () => {
    const result = signWindows.esignerCredentials({ ...CREDENTIALS, WIN_ESIGNER_TOTP_SECRET: '  ' });
    expect(result).toEqual({ state: 'partial', missing: ['WIN_ESIGNER_TOTP_SECRET'] });
  });
});

describe('the hook', () => {
  it('reads nothing from the Packager electron-builder passes second', async () => {
    const packager = { env: CREDENTIALS, spawn: fakeSpawn() };
    const saved = { ...process.env };
    for (const name of Object.keys(CREDENTIALS)) delete process.env[name];
    delete process.env.WIN_CSC_LINK;
    try {
      await signWindows({ path: 'app.exe', hash: 'sha256' }, packager);
    } finally {
      Object.assign(process.env, saved);
    }
    expect(calls).toHaveLength(0);
  });

  it('does nothing without credentials, so the build stays unsigned', () => {
    signWindows.signWith({ path: 'app.exe', hash: 'sha256', cscInfo: null }, options());
    expect(calls).toHaveLength(0);
  });

  it('refuses a half-configured set instead of building unsigned', () => {
    expect(() => signWindows.signWith({ path: 'app.exe', hash: 'sha256' }, options({ WIN_ESIGNER_USERNAME: 'u' }))).toThrow(
      /half-configured.*WIN_ESIGNER_PASSWORD/,
    );
  });

  it('refuses WIN_CSC_LINK, the .pfx path this repository no longer signs with', () => {
    const cscInfo = { file: 'cert.pfx', password: 'x' };
    expect(() => signWindows.signWith({ path: 'app.exe', hash: 'sha256', cscInfo }, options({ WIN_CSC_LINK: 'cert.pfx' }))).toThrow(
      /eSigner only/,
    );
  });

  it("leaves a Mac's CSC_LINK alone: the Windows half of dist:all stays unsigned", () => {
    const cscInfo = { file: 'developer-id.p12', password: 'x' };
    signWindows.signWith({ path: 'app.exe', hash: 'sha256', cscInfo }, options({ CSC_LINK: 'developer-id.p12' }));
    expect(calls).toHaveLength(0);
  });

  it('skips the sha1 pass, which would be a second billed signing', () => {
    signWindows.signWith({ path: 'app.exe', hash: 'sha1' }, options(CREDENTIALS));
    expect(calls).toHaveLength(0);
  });

  it('signs the file in place with CodeSignTool, from its own directory', () => {
    signWindows.signWith({ path: 'app.exe', hash: 'sha256' }, options(CREDENTIALS));
    expect(calls).toEqual([
      {
        command: 'java17',
        cwd: home,
        args: [
          '-jar',
          join(home, 'jar', 'code_sign_tool-1.3.2.jar'),
          'sign',
          '-username=user@example.com',
          '-password=pa55-word',
          '-credential_id=00000000-cred',
          '-totp_secret=totp-secret-value',
          `-input_file_path=${resolve('app.exe')}`,
          '-override',
        ],
      },
    ]);
  });
});

describe('signFile', () => {
  it('refuses a jar that no longer matches its pin, before the credentials reach it', () => {
    writeFileSync(join(home, 'jar', 'code_sign_tool-1.3.2.jar'), 'swapped');
    expect(() => signWindows.signFile('app.exe', options(CREDENTIALS))).toThrow(/pinned SHA-256/);
    expect(calls).toHaveLength(0);
  });

  it('rewrites the config for production, whatever was on disk', () => {
    signWindows.signFile('app.exe', options(CREDENTIALS));
    expect(properties()).toContain('CSC_API_ENDPOINT=https://cs.ssl.com\n');
    expect(properties()).not.toContain('attacker');
  });

  it('writes the sandbox endpoints only when the environment says TEST', () => {
    signWindows.signFile('app.exe', options({ ...CREDENTIALS, WIN_ESIGNER_ENVIRONMENT: 'TEST' }));
    expect(properties()).toContain('CSC_API_ENDPOINT=https://cs-try.ssl.com\n');
  });

  it('refuses an environment it does not know', () => {
    expect(() => signWindows.signFile('app.exe', options({ ...CREDENTIALS, WIN_ESIGNER_ENVIRONMENT: 'STAGING' }))).toThrow(
      /PROD or TEST/,
    );
  });

  it('fails on an error CodeSignTool reports with exit 0, without echoing a credential', () => {
    const spawn = fakeSpawn({ stdout: 'Error: invalid credentials for user@example.com / pa55-word' });
    expect(() => signWindows.signFile('app.exe', options(CREDENTIALS, spawn))).toThrow(/could not sign app\.exe/);
    expect(() => signWindows.signFile('app.exe', options(CREDENTIALS, spawn))).not.toThrow(/pa55-word|user@example\.com/);
  });

  it('fails on a non-zero exit', () => {
    expect(() => signWindows.signFile('app.exe', options(CREDENTIALS, fakeSpawn({ status: 1, stdout: '' })))).toThrow(/exit 1/);
  });

  it('fails a signing that times out', () => {
    const spawn = fakeSpawn({ status: null, stdout: '', error: new Error('spawnSync java17 ETIMEDOUT') });
    expect(() => signWindows.signFile('app.exe', options(CREDENTIALS, spawn))).toThrow(/ETIMEDOUT/);
  });

  it('asks for the install script when CodeSignTool is not there', () => {
    expect(() => signWindows.signFile('app.exe', { env: { ...CREDENTIALS }, spawn: fakeSpawn() })).toThrow(/install-codesigntool\.sh/);
  });
});
