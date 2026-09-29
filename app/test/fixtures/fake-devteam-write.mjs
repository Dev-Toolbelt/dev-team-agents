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
 * `version`, `compat`, `list`, `bind`, `unbind`, `sync`, `pin` and `upgrade` each with a
 * shape real enough for their own validators in `cli/operations.ts` to accept — so
 * `test/ipc.test.ts` can assert on `result.data`, not only on `result.command`.
 */

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
const PROJECT_ID = 'proj-1';
const PROJECT_PATH = '/repo/project-1';

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

  default:
    process.stderr.write(`fake-devteam-write: unknown or missing command ${JSON.stringify(command)}\n`);
    process.exit(64);
}
