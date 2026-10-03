import { useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { PROJECT_TYPES, type DetectReport, type LaunchFirstTaskAnswer, type OperationResult, type ProjectType, type StartReport } from '../../shared/api.js';
import type { Provider } from '../../shared/providers.js';
import { hostPlatformFrom } from '../../shared/directoryPaths.js';
import { SELECT_CLASS } from '../formStyles.js';
import { Problem } from '../Problem.js';
import { unreachable } from '../useOperation.js';
import { Busy, CommandBox, useFocusOnMount } from './CopyButton.js';
import { COPY } from './copy.js';
import { commandLabel, firstTaskCopyText, providerChoices, type Choices } from './model.js';

/** The folder the person chose, what was found in it and what they will start with. */
export interface Project {
  readonly path: string;
  readonly detect: DetectReport;
  readonly choices: Choices;
}

function Heading({ id, children }: { id: string; children: string }) {
  const ref = useFocusOnMount<HTMLHeadingElement>();
  return (
    <h2 id={id} ref={ref} tabIndex={-1} className="text-lg font-semibold outline-hidden">
      {children}
    </h2>
  );
}

/** Click 1: choose the folder. The picker is the main process's; what is inside is the CLI's to say. */
export function FolderStep({ onChosen }: { onChosen: (path: string, detect: DetectReport) => void }) {
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<Extract<OperationResult<never>, { ok: false }> | null>(null);

  async function choose() {
    setProblem(null);
    setBusy(true);
    try {
      const choice = await window.devteam.chooseProjectDirectory();
      if (!choice.chosen) return;
      const result = await window.devteam.detectProject(choice.path);
      if (result.ok) onChosen(choice.path, result.data);
      else setProblem(result);
    } catch (error) {
      setProblem(unreachable(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="folder-heading" className="flex flex-col gap-4">
      <Heading id="folder-heading">{COPY.folder.heading}</Heading>
      <p>{COPY.folder.body}</p>
      {problem !== null ? <Problem problem={problem} /> : null}
      {busy ? <Busy text={COPY.folder.looking} /> : null}
      <div>
        <Button disabled={busy} onClick={() => void choose()}>
          {COPY.folder.choose}
        </Button>
      </div>
    </section>
  );
}

/** Click 2: check what was found. Every value is preselected and changeable with one select. */
export function ConfirmStep({
  project,
  onChange,
  onConfirm,
  onBack,
}: {
  project: Project;
  onChange: (choices: Choices) => void;
  onConfirm: () => void;
  onBack: () => void;
}) {
  const { detect, choices } = project;
  const providers = providerChoices(detect);
  const stacks = detect.stack.all.length > 0 ? detect.stack.all : detect.stack.primary !== null ? [detect.stack.primary] : [];
  const noneInstalled = detect.providers.installed.length === 0;

  return (
    <section aria-labelledby="confirm-heading" className="flex flex-col gap-4">
      <Heading id="confirm-heading">{COPY.confirm.heading}</Heading>
      <p>{COPY.confirm.body}</p>
      <dl className="grid gap-1 text-sm">
        <dt className="text-muted-foreground">{COPY.confirm.folder}</dt>
        <dd className="font-mono break-all">{project.path}</dd>
      </dl>

      <div className="grid max-w-md gap-4">
        <div className="grid gap-1.5">
          <Label htmlFor="onboarding-provider">{COPY.confirm.provider}</Label>
          <select
            id="onboarding-provider"
            className={SELECT_CLASS}
            value={choices.provider}
            onChange={(event) => onChange({ ...choices, provider: event.target.value })}
          >
            {providers.map((entry) => (
              <option key={entry.name} value={entry.name}>
                {entry.installed ? COPY.confirm.providerInstalled(entry.name) : COPY.confirm.providerMissing(entry.name)}
              </option>
            ))}
          </select>
          {noneInstalled ? <p className="text-xs text-muted-foreground">{COPY.confirm.noProvider}</p> : null}
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor="onboarding-stack">{COPY.confirm.stack}</Label>
          {stacks.length > 1 ? (
            <select
              id="onboarding-stack"
              className={SELECT_CLASS}
              value={choices.stack ?? ''}
              onChange={(event) => onChange({ ...choices, stack: event.target.value })}
            >
              {stacks.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          ) : (
            <p id="onboarding-stack" className="text-sm">
              {choices.stack ?? COPY.confirm.stackUnknown}
            </p>
          )}
        </div>

        <div className="grid gap-1.5">
          <Label htmlFor="onboarding-type">{COPY.confirm.projectType}</Label>
          <select
            id="onboarding-type"
            className={SELECT_CLASS}
            value={choices.type}
            aria-describedby={detect.project_type.confidence === 'low' ? 'onboarding-type-note' : undefined}
            onChange={(event) => onChange({ ...choices, type: event.target.value as ProjectType })}
          >
            {PROJECT_TYPES.map((type) => (
              <option key={type} value={type}>
                {COPY.types[type]}
              </option>
            ))}
          </select>
          {detect.project_type.confidence === 'low' ? (
            <p id="onboarding-type-note" className="text-xs text-muted-foreground">
              {COPY.confirm.lowConfidence}
            </p>
          ) : null}
        </div>
      </div>

      <div className="flex gap-2">
        <Button variant="outline" onClick={onBack}>
          {COPY.confirm.back}
        </Button>
        <Button onClick={onConfirm}>{COPY.confirm.looksRight}</Button>
      </div>
    </section>
  );
}

export interface Started {
  readonly report: StartReport;
  /** `null` when there was nothing to open (no launch for this provider). */
  readonly launch: LaunchFirstTaskAnswer | null;
}

/** Click 3: start the first task. Sets the folder up, then opens the provider in a terminal. */
export function StartStep({
  project,
  onStarted,
  onBack,
}: {
  project: Project;
  onStarted: (started: Started) => void;
  onBack: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<Extract<OperationResult<never>, { ok: false }> | null>(null);
  const task = project.detect.first_task;

  async function start() {
    setProblem(null);
    setBusy(true);
    try {
      const result = await window.devteam.startProject({
        path: project.path,
        provider: project.choices.provider as Provider,
        type: project.choices.type,
      });
      if (!result.ok) {
        setProblem(result);
        return;
      }
      let launch: LaunchFirstTaskAnswer | null = null;
      if (result.data.first_task?.launch != null) launch = await window.devteam.launchFirstTask(project.path);
      onStarted({ report: result.data, launch });
    } catch (error) {
      setProblem(unreachable(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="start-heading" className="flex flex-col gap-4">
      <Heading id="start-heading">{COPY.start.heading}</Heading>
      {task !== null ? (
        <>
          <p className="font-medium">{task.label}</p>
          <p>{COPY.start.body}</p>
        </>
      ) : (
        <p>{COPY.start.noTask}</p>
      )}
      {problem !== null ? <Problem problem={problem} /> : null}
      {busy ? <Busy text={COPY.start.starting} /> : null}
      <div className="flex gap-2">
        <Button variant="outline" disabled={busy} onClick={onBack}>
          {COPY.start.back}
        </Button>
        <Button disabled={busy} onClick={() => void start()}>
          {COPY.start.startButton}
        </Button>
      </div>
    </section>
  );
}

/** The result: the terminal opened (or the command to copy), and the five commands to try next. */
export function DoneStep({ project, started, onFinish }: { project: Project; started: Started; onFinish: () => void }) {
  const [launch, setLaunch] = useState<LaunchFirstTaskAnswer | null>(started.launch);
  const { report } = started;
  const task = report.first_task;
  const platform = hostPlatformFrom(typeof navigator === 'undefined' ? undefined : navigator.platform) === 'win32' ? 'win32' : 'posix';

  async function openAgain() {
    try {
      setLaunch(await window.devteam.launchFirstTask(project.path));
    } catch (error) {
      setLaunch({ launched: false, message: String(error) });
    }
  }

  return (
    <section aria-labelledby="done-heading" className="flex flex-col gap-4">
      <Heading id="done-heading">{COPY.done.heading}</Heading>

      {task === null ? (
        <p>{COPY.done.noTerminalTask}</p>
      ) : (
        <>
          <p role="status">{launch !== null && launch.launched ? COPY.done.opened : COPY.done.notOpened}</p>
          {launch !== null && !launch.launched ? (
            <Alert>
              <AlertDescription>{launch.message}</AlertDescription>
            </Alert>
          ) : null}
          <h3 className="font-medium">{COPY.done.copyHeading}</h3>
          <CommandBox
            text={firstTaskCopyText(task, project.choices.provider, project.path, platform)}
            label={COPY.done.copy}
          />
          {task.launch !== null ? (
            <div>
              <Button variant="outline" size="sm" onClick={() => void openAgain()}>
                {COPY.done.openAgain}
              </Button>
            </div>
          ) : null}
        </>
      )}

      {report.featured_commands.length > 0 ? (
        <>
          <h3 className="font-medium">{COPY.done.commandsHeading}</h3>
          <p className="text-sm text-muted-foreground">{COPY.done.commandsHint}</p>
          <ul className="flex flex-wrap gap-2">
            {report.featured_commands.map((name) => (
              <li key={name} className="rounded-md border bg-muted px-2 py-1 font-mono text-xs">
                {commandLabel(project.choices.provider, name)}
              </li>
            ))}
          </ul>
        </>
      ) : null}

      <p className="text-sm text-muted-foreground">{COPY.done.advanced}</p>
      <div>
        <Button onClick={onFinish}>{COPY.done.finish}</Button>
      </div>
    </section>
  );
}
