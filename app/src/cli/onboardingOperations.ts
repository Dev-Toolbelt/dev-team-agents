/**
 * The first-run operations (ADR-0030): `devteam detect` and `devteam start`.
 *
 * Same discipline as `operations.ts`, whose `run()` they go through: the argument vector is
 * built here from validated values, `COMMAND_SHAPES` is consulted before anything is spawned,
 * and the payload is checked for the keys the screen reads. The folder is always a path the
 * main process handed back through the picker; this file does not know that, it only refuses
 * a value that could be read as a flag.
 */

import { PROJECT_TYPES, type DetectReport, type FirstTask, type OperationResult, type ProjectType, type StartReport } from '../shared/api.js';
import { PROVIDERS } from '../shared/providers.js';
import { run, type CliContext } from './operations.js';

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === 'string') : [];
}

function nullableString(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

function refused<T>(command: string, message: string): Promise<OperationResult<T>> {
  return Promise.resolve({ ok: false, kind: 'refused', message, exitCode: null, command: `devteam ${command}`, durationMs: 0 });
}

/** A folder path that is a non-empty absolute-looking string and cannot be read as a flag. */
export function folderProblem(path: unknown): string | null {
  if (typeof path !== 'string' || path.trim() === '') return 'a folder must be a non-empty string';
  if (path.startsWith('-')) return 'a folder cannot begin with "-"; it would be read as a flag';
  if (path.includes('\0')) return 'a folder cannot contain a NUL byte';
  return null;
}

function parseFirstTask(value: unknown): FirstTask | null | string {
  if (value === null || value === undefined) return null;
  if (!isRecord(value)) return '`first_task` is not an object';
  const kind = value['kind'];
  if (kind !== 'audit' && kind !== 'review') return '`first_task.kind` is not audit or review';
  if (typeof value['target'] !== 'string' || typeof value['label'] !== 'string') {
    return '`first_task` has no string `target` and `label`';
  }
  let launch: FirstTask['launch'] = null;
  const raw = value['launch'];
  if (raw !== null && raw !== undefined) {
    if (!isRecord(raw) || typeof raw['provider'] !== 'string' || !Array.isArray(raw['argv'])) {
      return '`first_task.launch` has no string `provider` and `argv` array';
    }
    // Every element must be a string: a launch with a hole in it is refused, not repaired.
    const argv = raw['argv'];
    if (argv.length === 0 || !argv.every((entry) => typeof entry === 'string')) {
      return '`first_task.launch.argv` must be a non-empty array of strings';
    }
    launch = { provider: raw['provider'], argv };
  }
  return { kind, target: value['target'], label: value['label'], read_only: true, launch };
}

export function parseDetect(body: Record<string, unknown>): DetectReport | string {
  if (typeof body['path'] !== 'string') return 'no string `path`';
  const providers = body['providers'];
  if (!isRecord(providers)) return 'no `providers` object';
  const installed: DetectReport['providers']['installed'][number][] = [];
  for (const raw of Array.isArray(providers['installed']) ? providers['installed'] : []) {
    if (!isRecord(raw) || typeof raw['name'] !== 'string') return 'an installed provider has no string `name`';
    installed.push({
      name: raw['name'],
      binary: typeof raw['binary'] === 'string' ? raw['binary'] : raw['name'],
      version: nullableString(raw['version']),
    });
  }
  const stack = body['stack'];
  if (!isRecord(stack)) return 'no `stack` object';
  const projectType = body['project_type'];
  if (!isRecord(projectType)) return 'no `project_type` object';
  const suggested = projectType['suggested'];
  if (!PROJECT_TYPES.includes(suggested as ProjectType)) return '`project_type.suggested` is not a project type';
  const firstTask = parseFirstTask(body['first_task']);
  if (typeof firstTask === 'string') return firstTask;
  return {
    path: body['path'],
    providers: {
      installed,
      in_project: strings(providers['in_project']),
      suggested: nullableString(providers['suggested']),
    },
    stack: { primary: nullableString(stack['primary']), all: strings(stack['all']), signals: strings(stack['signals']) },
    project_type: {
      suggested: suggested as ProjectType,
      confidence: projectType['confidence'] === 'high' ? 'high' : 'low',
      reasons: strings(projectType['reasons']),
    },
    first_task: firstTask,
  };
}

export function detect(context: CliContext, path: string): Promise<OperationResult<DetectReport>> {
  const problem = folderProblem(path);
  if (problem !== null) return refused('detect', problem);
  return run(context, ['detect', '--path', path], parseDetect);
}

export interface StartOptions {
  readonly provider?: string;
  readonly type?: ProjectType;
}

export function start(context: CliContext, path: string, options: StartOptions = {}): Promise<OperationResult<StartReport>> {
  const problem = folderProblem(path);
  if (problem !== null) return refused('start', problem);
  const args = ['start', '--path', path];
  if (options.provider !== undefined) {
    if (!PROVIDERS.includes(options.provider as (typeof PROVIDERS)[number])) {
      return refused('start', `\`${options.provider}\` is not a provider this app knows`);
    }
    args.push('--provider', options.provider);
  }
  if (options.type !== undefined) {
    if (!PROJECT_TYPES.includes(options.type)) return refused('start', `\`${String(options.type)}\` is not a project type`);
    args.push('--type', options.type);
  }
  return run(context, args, (body) => {
    if (typeof body['bound'] !== 'boolean') return 'no boolean `bound`';
    if (typeof body['project_id'] !== 'string') return 'no string `project_id`';
    const detectBody = body['detect'];
    if (!isRecord(detectBody)) return 'no `detect` object';
    const detected = parseDetect(detectBody);
    if (typeof detected === 'string') return `\`detect\`: ${detected}`;
    const firstTask = parseFirstTask(body['first_task']);
    if (typeof firstTask === 'string') return firstTask;
    return {
      bound: body['bound'],
      project_id: body['project_id'],
      detect: detected,
      featured_commands: strings(body['featured_commands']),
      first_task: firstTask,
    };
  });
}
