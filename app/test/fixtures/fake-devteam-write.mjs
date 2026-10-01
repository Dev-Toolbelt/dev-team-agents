#!/usr/bin/env node
/**
 * A second fake `devteam`, for `test/ipc.test.ts` only.
 *
 * `fake-devteam.mjs` picks its answer from `FAKE_DEVTEAM_SCENARIO`, which works for
 * `test/operations.test.ts` and friends because each of those calls `invokeDevteam`
 * directly and can pass a different `env` per call. `main/ipc.ts`'s real flow cannot:
 * `resolveDevteam`'s probe and every `CliContext` built by `context()` inherit the main
 * process's own environment with no per-call override, and `invoke.ts`'s
 * `PASS_THROUGH_ENV` allowlist does not carry a test-only variable through that
 * inherited environment anyway (only an explicit `env` option bypasses it, by spreading
 * on top). So a single `registerIpc` flow — resolve, `list`, then a write command — would
 * see the same env-selected scenario for all three, which cannot express "compat here,
 * a project row there, a bind report over there" in one value.
 *
 * This fixture reads the subcommand out of argv instead, and needs no environment
 * variable at all. It knows one project, `proj-1` at `/repo/project-1`, and answers
 * `version`, `compat`, `list`, `bind`, `unbind`, `sync`, `pin`, `upgrade` and `prefs
 * list/set/unset`, `plugin list/enable/disable/config set/config unset/run` and
 * `skills list/show/install/remove` each with a
 * shape real enough for their own validators in `cli/operations.ts` to accept — so
 * `test/ipc.test.ts` can assert on `result.data`, not only on `result.command`.
 */

import { readFileSync } from 'node:fs';

const rawArgs = process.argv.slice(2);
const args = [...rawArgs];

// `invokeDevteam` prepends `--client-schemas <path>` once a declaration exists, and
// always appends `--json`. Neither is the subcommand; strip both before reading it.
const clientSchemasIndex = args.indexOf('--client-schemas');
if (clientSchemasIndex !== -1) args.splice(clientSchemasIndex, 2);
const jsonIndex = args.indexOf('--json');
if (jsonIndex !== -1) args.splice(jsonIndex, 1);

const command = args[0];

function emit(object) {
  process.stdout.write(`${JSON.stringify(object)}\n`);
}

function flagValue(name) {
  const index = args.indexOf(name);
  return index === -1 ? undefined : args[index + 1];
}

const STORE_SCHEMAS = { project: 1, project_layout: 2, registry: 1, bind_manifest: 1, credentials: 1 };
// One generic plugin, declared the way a manifest would be. Nothing in the app knows its name.
function pluginView(enabled) {
  return {
    name: 'demo',
    title: 'Demo',
    description: 'A plugin the fixture declares.',
    homepage: null,
    enabled,
    source: enabled ? 'settings' : 'none',
    settings_file: '.dev-team-agents/plugin-settings/demo.json',
    requirements: [{ binary: 'demo-bin', found: true, install_hint: '/devteam:install demo' }],
    ready: true,
    configured: false,
    config_fields: [
      { key: 'paths', type: 'string_list', label: 'Paths', required: true, default: [] },
      { key: 'depth', type: 'integer', label: 'Depth', required: false, default: 3, min: 1, max: 9 },
      { key: 'auto', type: 'boolean', label: 'Auto', required: false, default: false },
      { key: 'mode', type: 'enum', label: 'Mode', required: false, default: 'a', options: [{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }] },
      { key: 'name', type: 'string', label: 'Name', required: false, default: '' },
    ],
    config: { paths: [], depth: 3, auto: false, mode: 'a', name: '' },
    unknown_config: [],
    actions: [
      { id: 'detect', label: 'Detect', help: null, output: 'config', requires_enabled: false, writes: false, timeout_seconds: 60 },
      { id: 'rebuild', label: 'Rebuild', help: null, output: 'log', requires_enabled: true, writes: true, timeout_seconds: 100 },
    ],
    hooks: [],
    status: null,
  };
}

// One generic integration. `stdin_bytes` is what the CLI read from stdin, reported in the summary
// so a test can tell "a token arrived" from "nothing arrived" without the token ever being echoed.
function integrationView(stdinBytes, connected) {
  return {
    name: 'demo',
    title: 'Demo',
    description: 'An integration the fixture declares.',
    homepage: null,
    auth: { kind: 'token', label: 'Token', help: null, has_token: connected, stale: false, backend: connected ? 'keychain' : null },
    fields: [
      { key: 'api_url', scope: 'account', type: 'string', label: 'API URL', help: null, required: true, default: 'https://api.example.test', placeholder: null, options: null, resource: null, visible_when: null },
      { key: 'mode', scope: 'account', type: 'enum', label: 'Mode', help: null, required: false, default: 'a', placeholder: null, options: [{ value: 'a', label: 'A' }], resource: null, visible_when: { key: 'api_url', equals: 'x' } },
      { key: 'repository', scope: 'project', type: 'string', label: 'Repository', help: null, required: false, default: null, placeholder: null, options: null, resource: 'repos', visible_when: null },
    ],
    account: { api_url: 'https://api.example.test' },
    project: flagValue('--path') === PROJECT_PATH ? { repository: 'o/r' } : null,
    detected: {},
    connected,
    project_configured: flagValue('--path') === PROJECT_PATH,
    status: { state: connected ? 'connected' : 'not_connected', checked_at: null, summary: `stdin_bytes=${stdinBytes}`, facts: [{ label: 'Account', value: 'octocat', tone: 'positive' }] },
  };
}

function readStdin() {
  try {
    return readFileSync(0, 'utf8').length;
  } catch {
    return 0;
  }
}

const PROJECT_ID = 'proj-1';
const PROJECT_PATH = process.env.FAKE_PROJECT_PATH ?? '/repo/project-1';

const PROJECT_ROW = {
  project_id: PROJECT_ID,
  path: PROJECT_PATH,
  providers: ['claude'],
  mode: 'link',
  pin: null,
  resolves_to: '3.0.0',
  path_exists: true,
};

switch (command) {
  case 'version':
    emit({
      ok: true,
      current: '3.0.0',
      installed: ['3.0.0'],
      core: '/tmp/core',
      compat: { json_contract: 1, min_app_version: null, store_schemas: STORE_SCHEMAS },
    });
    process.exit(0);
    break;

  case 'compat':
    emit({
      ok: true,
      json_contract: 1,
      min_app_version: null,
      store_schemas: STORE_SCHEMAS,
      client_schemas: STORE_SCHEMAS,
      may_write: true,
      unsupported: {},
    });
    process.exit(0);
    break;

  case 'list':
    emit({ ok: true, current: '3.0.0', projects: [PROJECT_ROW] });
    process.exit(0);
    break;

  case 'bind': {
    const path = args[1] ?? PROJECT_PATH;
    const providers = [];
    for (let i = 0; i < args.length; i += 1) {
      if (args[i] === '--provider') providers.push(args[i + 1]);
    }
    emit({
      ok: true,
      path,
      project_id: PROJECT_ID,
      version: '3.0.0',
      mode: flagValue('--mode') ?? 'auto',
      providers: providers.length > 0 ? providers : ['claude'],
      artifacts: 12,
      identity_created: true,
      gitignore: '.gitignore',
      git_exclude: '.git/info/exclude',
      pin: flagValue('--pin') ?? null,
      fallback_reason: null,
      retired: [],
      merged_project_files: [],
    });
    process.exit(0);
    break;
  }

  case 'unbind':
    emit({
      ok: true,
      path: PROJECT_PATH,
      project_id: flagValue('--project-id') ?? PROJECT_ID,
      unlinked: ['.claude/settings.json'],
      quarantined: [],
      kept: ['project.json'],
      problems: [],
    });
    process.exit(0);
    break;

  case 'sync':
    if (args.includes('--all')) {
      emit({
        ok: true,
        synced: [
          {
            path: PROJECT_PATH,
            project_id: PROJECT_ID,
            version: '3.0.0',
            mode: 'link',
            providers: ['claude'],
            artifacts: 12,
            identity_created: false,
            gitignore: '.gitignore',
            git_exclude: '.git/info/exclude',
            pin: null,
            fallback_reason: null,
            retired: [],
            merged_project_files: [],
          },
        ],
        problems: [],
      });
    } else {
      emit({
        ok: true,
        path: PROJECT_PATH,
        project_id: flagValue('--project-id') ?? PROJECT_ID,
        version: '3.0.0',
        mode: 'link',
        providers: ['claude'],
        artifacts: 12,
        identity_created: false,
        gitignore: '.gitignore',
        git_exclude: '.git/info/exclude',
        pin: null,
        fallback_reason: null,
        retired: [],
        merged_project_files: [],
      });
    }
    process.exit(0);
    break;

  case 'pin': {
    const release = args.includes('--release');
    const version = release ? null : (args[1] ?? null);
    emit({ ok: true, project_id: PROJECT_ID, path: flagValue('--path') ?? PROJECT_PATH, pin: version });
    process.exit(0);
    break;
  }

  case 'upgrade': {
    const path = args[1] ?? PROJECT_PATH;
    if (args.includes('--apply')) {
      emit({
        ok: true,
        path,
        project_id: PROJECT_ID,
        from_layout: 1,
        to_layout: 2,
        copied: 12,
        retained: ['docs/project.md'],
        destination: '/store/data/projects/proj-1',
        state_destination: '/store/data/machines/m1/projects/proj-1',
        quarantined: null,
        state_pointer: '.dev-team-agents/memory-dir',
        memory_pointer: '.dev-team-agents/memory-dir',
        git_tracked: [],
      });
    } else {
      emit({
        ok: true,
        path,
        project_id: PROJECT_ID,
        from_layout: 1,
        to_layout: 2,
        files: 12,
        source: '.dev-team-agents/user-data',
        destination: '/store/data/projects/proj-1',
        state_destination: '/store/data/machines/m1/projects/proj-1',
        machine_local: ['state.json'],
        retained: ['docs/project.md'],
        collisions: [],
        git_tracked: [],
        actions: ['copy 12 file(s)'],
      });
    }
    process.exit(0);
    break;
  }

  case 'prefs': {
    const verb = args[1];
    if (verb === 'list') {
      // Anywhere but the project, the CLI resolves no project: the cascade without its layer.
      if (flagValue('--path') !== PROJECT_PATH) {
        emit({
          ok: true,
          project_id: null,
          version: '3.0.0',
          values: { language: 'pt-BR', worktree_active: true, model_max_tokens: 200000 },
          origin: { language: 'defaults', worktree_active: 'defaults', model_max_tokens: 'global' },
          unknown: [],
        });
        process.exit(0);
      }
      emit({
        ok: true,
        project_id: PROJECT_ID,
        version: '3.0.0',
        values: { language: 'en', worktree_active: true, model_max_tokens: 200000, telemetry: false, mystery_key: 1 },
        origin: { language: 'project', worktree_active: 'defaults', model_max_tokens: 'global', telemetry: 'consent-withheld', mystery_key: 'project' },
        unknown: ['mystery_key'],
      });
      process.exit(0);
    }
    const key = args[2];
    // `model_max_tokens 5000` is the fixture's one refusal, so a batch can fail part-way.
    if (verb === 'set' && key === 'model_max_tokens' && args[3] === '5000') {
      emit({ ok: false, error: 'model_max_tokens is too small', hint: 'Use at least 1000.', exit_code: 2 });
      process.exit(2);
    }
    emit(
      verb === 'unset'
        ? { ok: true, key, scope: flagValue('--scope'), removed: true, file: '/store/prefs.json' }
        : { ok: true, key, value: args[3], scope: flagValue('--scope'), file: '/store/prefs.json' },
    );
    process.exit(0);
    break;
  }

  case 'plugin': {
    const verb = args[1];
    if (verb === 'list') {
      emit({ ok: true, project_id: PROJECT_ID, plugins: [pluginView(false)], invalid: [{ name_or_dir: 'broken-plugin', problem: 'manifest.json: missing name' }] });
      process.exit(0);
    }
    if (verb === 'enable' || verb === 'disable') {
      emit({ ok: true, plugin: pluginView(verb === 'enable'), changed: true, seeded: false });
      process.exit(0);
    }
    if (verb === 'config') {
      const sub = args[2];
      const key = args[4];
      // These are the fixture's refusals, so a batch can fail part-way and the failing
      // write's argv (which carries the serialized value) comes back in the report.
      const refused =
        (key === 'depth' && args[5] === '7') ||
        (key === 'paths' && args[5] === '["fail"]') ||
        (key === 'auto' && args[5] === 'false');
      if (sub === 'set' && refused) {
        emit({ ok: false, error: `${key} ${args[5]} is reserved`, hint: 'Pick another value.', exit_code: 2 });
        process.exit(2);
      }
      emit(sub === 'unset' ? { ok: true, plugin: pluginView(true), key, removed: true } : { ok: true, plugin: pluginView(true), key, value: args[5] });
      process.exit(0);
    }
    if (verb === 'run') {
      emit({ ok: true, plugin: args[2], action: args[3], exit_code: 0, duration_ms: 12, output: args[3] === 'detect' ? { paths: ['src'] } : null, log_tail: 'done' });
      process.exit(0);
    }
    process.exit(64);
    break;
  }

  case 'integration': {
    const verb = args[1];
    if (verb === 'list') {
      emit({ ok: true, project_id: flagValue('--path') === PROJECT_PATH ? PROJECT_ID : null, integrations: [integrationView(0, true)] });
      process.exit(0);
    }
    if (verb === 'show') {
      emit({ ok: true, integration: integrationView(0, true) });
      process.exit(0);
    }
    if (verb === 'connect' || verb === 'test') {
      const stdinBytes = verb === 'connect' ? readStdin() : 0;
      emit({
        ok: true,
        integration: integrationView(stdinBytes, true),
        test: { ok: true, state: 'connected', summary: 'Signed in', facts: [{ label: 'Account', value: 'octocat', tone: 'positive' }], checked_at: '2026-09-30T12:00:00Z' },
      });
      process.exit(0);
    }
    if (verb === 'disconnect') {
      emit({ ok: true, integration: integrationView(0, args.includes('--keep-token')), changed: true });
      process.exit(0);
    }
    if (verb === 'config') {
      emit({ ok: true, integration: integrationView(0, true), key: args[4], ...(args[2] === 'unset' ? { removed: true } : {}) });
      process.exit(0);
    }
    if (verb === 'resources') {
      emit({ ok: true, items: [{ value: 'o/r', label: 'o/r' }], truncated: false });
      process.exit(0);
    }
    process.exit(64);
    break;
  }

  // ADR-0024. `patch` reads its ops from stdin and reports each pointer back in `unknown_paths`, so a test
  // can see that stdin (not argv) carried them. A hash of 64 `f` is the exit-4 conflict, 64 `e` is a
  // refusal whose message echoes the first op's value, to prove the app redacts it.
  case 'cred': {
    const view = (extra = {}) => ({
      ok: true,
      path: `${PROJECT_PATH}/.dev-team-agents/credentials.local.json`,
      exists: true,
      valid: true,
      error: null,
      hash: 'a'.repeat(64),
      data: { jira: { baseUrl: 'https://x.test', token: { secret: true, set: true } } },
      unknown_paths: [],
      ...extra,
    });
    const verb = args[2];
    if (args[1] !== 'local') process.exit(64);
    if (verb === 'show') {
      emit(view());
      process.exit(0);
    }
    if (verb === 'init') {
      if (flagValue('--path') === '/repo/exists') {
        emit({ ok: false, error: 'already exists', exit_code: 4, details: { reason: 'exists' } });
        process.exit(4);
      }
      emit(view({ data: {} }));
      process.exit(0);
    }
    if (verb === 'patch') {
      const expected = flagValue('--expect-hash');
      const ops = (() => {
        try {
          return JSON.parse(readFileSync(0, 'utf8'));
        } catch {
          return [];
        }
      })();
      if (expected === 'f'.repeat(64)) {
        emit({ ok: false, error: 'the file changed on disk', exit_code: 4, details: { reason: 'hash-conflict', expected_hash: expected, actual_hash: 'b'.repeat(64) } });
        process.exit(4);
      }
      if (expected === 'd'.repeat(64)) {
        emit({ ok: false, error: 'the credentials file is locked', exit_code: 4 });
        process.exit(4);
      }
      if (expected === 'b'.repeat(64)) {
        process.stdout.write('written, but not JSON\n');
        process.exit(0);
      }
      if (expected === 'e'.repeat(64)) {
        emit({ ok: false, error: `cannot set ${JSON.stringify(ops[0]?.value)}`, exit_code: 3 });
        process.exit(3);
      }
      emit(view({ hash: 'c'.repeat(64), unknown_paths: ops.map((entry) => entry.pointer) }));
      process.exit(0);
    }
    process.exit(64);
    break;
  }

  case 'skills': {
    const verb = args[1];
    const SKILL = (name, root, extra = {}) => ({
      name,
      description: `${name} skill`,
      root,
      root_path: `/home/u/.${root}/skills`,
      path: `/home/u/.${root}/skills/${name}`,
      providers: ['claude'],
      is_symlink: false,
      link_target: null,
      managed: false,
      status: 'ok',
      error: null,
      ...extra,
    });
    if (verb === 'list') {
      emit({
        ok: true,
        provider: flagValue('--provider') ?? 'all',
        roots: [{ id: 'claude', path: '/home/u/.claude/skills', exists: true, providers: ['claude'], install_target_for: ['claude'] }],
        skills: [SKILL('alpha', 'claude'), SKILL('framework-owned', 'claude', { managed: true })],
        count: 2,
      });
      process.exit(0);
    }
    if (verb === 'show') {
      emit({ ...SKILL(args[2], flagValue('--root') ?? 'claude'), body: '# body', files: ['SKILL.md'], files_truncated: false });
      process.exit(0);
    }
    if (verb === 'install') {
      const source = flagValue('--source') ?? '';
      // A source whose path says `clash` collides with an installed skill until --replace.
      if (source.includes('clash') && !args.includes('--replace')) {
        emit({ ok: false, error: 'skill "clash" already exists in claude', hint: 'Pass --replace.', exit_code: 4 });
        process.exit(4);
      }
      emit({
        ok: true,
        name: 'installed-skill',
        description: 'd',
        source,
        linked: args.includes('--link'),
        installed: [{ root: 'claude', path: '/home/u/.claude/skills/installed-skill', providers: ['claude'], replaced: args.includes('--replace'), quarantined_to: null }],
      });
      process.exit(0);
    }
    emit({
      ok: true,
      name: args[2],
      root: flagValue('--root'),
      path: `/home/u/.${flagValue('--root')}/skills/${args[2]}`,
      providers: ['claude'],
      action: 'quarantined',
      quarantined_to: '/store/quarantine/x',
    });
    process.exit(0);
    break;
  }

  default:
    process.stderr.write(`fake-devteam-write: unknown or missing command ${JSON.stringify(command)}\n`);
    process.exit(64);
}
