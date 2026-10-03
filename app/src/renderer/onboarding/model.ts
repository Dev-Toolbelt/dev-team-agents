import type { DetectReport, DoctorFinding, FirstTask, ProjectType } from '../../shared/api.js';
import { PROVIDERS } from '../../shared/providers.js';
import { copyableCommand, type CopyPlatform } from '../../shared/shellQuote.js';

export type StepId = 'cli' | 'signin' | 'machine' | 'folder' | 'confirm' | 'start';

/** What the person can change before the first task starts. Each starts at what was detected. */
export interface Choices {
  readonly provider: string;
  readonly type: ProjectType;
  /** Display only: `devteam start` takes no stack, it is what was detected or what the person picked. */
  readonly stack: string | null;
}

/** The provider to preselect: what the CLI suggested, else an installed one, else one the project uses. */
export function defaultProvider(detect: DetectReport): string {
  return (
    detect.providers.suggested ??
    detect.providers.installed[0]?.name ??
    detect.providers.in_project[0] ??
    PROVIDERS[0]
  );
}

export function defaultChoices(detect: DetectReport): Choices {
  return {
    provider: defaultProvider(detect),
    type: detect.project_type.suggested,
    stack: detect.stack.primary,
  };
}

/** Every provider the app knows, with whether it is installed; detected-but-unknown names are kept too. */
export function providerChoices(detect: DetectReport): readonly { readonly name: string; readonly installed: boolean }[] {
  const installed = new Set(detect.providers.installed.map((entry) => entry.name));
  const names = [...new Set<string>([...detect.providers.installed.map((entry) => entry.name), ...PROVIDERS])];
  return names.map((name) => ({ name, installed: installed.has(name) }));
}

/** How a command is typed in each provider. Codex uses `$devteam-<name>`; the others `/devteam:<name>`. */
export function commandLabel(provider: string | null, name: string): string {
  return provider === 'codex' ? `$devteam-${name}` : `/devteam:${name}`;
}

/** A finding the person has to look at: anything the CLI did not call fine. */
export function needsAttention(finding: DoctorFinding): boolean {
  return finding.level === 'warn' || finding.level === 'fail' || finding.level === 'error';
}

/**
 * The text to paste into a terminal for the first task. The launch map's argv when there is
 * one; otherwise the command typed inside the tool (assumption: `<command> <target>`, since the
 * contract gives the target but not a prompt for a provider with no launch).
 */
export function firstTaskCopyText(
  task: FirstTask,
  provider: string,
  folder: string,
  platform: CopyPlatform,
): string {
  if (task.launch !== null) {
    const line = copyableCommand(platform, folder, task.launch.argv);
    if (line !== null) return line;
  }
  return `${commandLabel(provider, task.kind)} ${task.target}`.trim();
}
