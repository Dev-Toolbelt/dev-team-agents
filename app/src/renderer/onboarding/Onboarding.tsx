import { useCallback, useState } from 'react';
import { Check } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { AccountGate } from '../account/AccountGate.js';
import { useAccount } from '../account/AccountContext.js';
import { InstallCliButton } from '../InstallCliButton.js';
import { useFocusOnMount } from './CopyButton.js';
import { MachineStep } from './MachineStep.js';
import { ConfirmStep, DoneStep, FolderStep, StartStep, type Project, type Started } from './ProjectSteps.js';
import { COPY } from './copy.js';
import { defaultChoices, type Choices, type StepId } from './model.js';
import { STEP_ORDER, currentStep, type Facts } from './steps.js';

/**
 * The first run (ADR-0030): install → sign in → this computer → folder → confirm → first task.
 *
 * Each step is one screen with one thing to do. The account step is the existing sign-in
 * (`AccountGate` and `SignIn`), not a second one; the rest are small panels over named bridge
 * operations. Which screen shows is not stored: it is derived from facts (`steps.ts`), so a
 * step the person already satisfied (a CLI already installed, an account already signed in)
 * never appears.
 *
 * Finishing records the app-local flag (`onFinished`); until then the tabbed app, which is
 * where "Advanced settings" live, is not shown.
 */
export function Onboarding({
  cliFound,
  onRetry,
  onFinished,
  onOpenAccount,
}: {
  cliFound: boolean;
  onRetry: () => void;
  onFinished: () => void;
  onOpenAccount: () => void;
}) {
  const account = useAccount();
  const [machineReady, setMachineReady] = useState(false);
  const [project, setProject] = useState<Project | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [started, setStarted] = useState<Started | null>(null);

  // Signed in, or the framework is not yet refusing an account-less person (warn mode).
  const signedIn = account.view.kind === 'entitled' || (account.view.kind !== 'loading' && account.mode !== 'enforce');
  const facts: Facts = {
    completed: false,
    hasProjects: false,
    cliFound,
    signedIn,
    machineReady,
    folder: project?.path ?? null,
    confirmed,
    started: started !== null,
  };
  const step = currentStep(facts);

  const onReady = useCallback(() => setMachineReady(true), []);
  const onChoices = (choices: Choices) => setProject((previous) => (previous === null ? previous : { ...previous, choices }));

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 py-4">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold">{COPY.title}</h1>
        <p className="text-muted-foreground">{COPY.lead}</p>
      </header>

      <Progress current={step} />

      <div>
        {step === 'cli' ? <CliPanel onRetry={onRetry} /> : null}
        {step === 'signin' ? (
          <AccountGate onOpenAccount={onOpenAccount}>
            <></>
          </AccountGate>
        ) : null}
        {step === 'machine' ? <MachineStep onReady={onReady} /> : null}
        {step === 'folder' ? (
          <FolderStep
            onChosen={(path, detect) => {
              setProject({ path, detect, choices: defaultChoices(detect) });
              setConfirmed(false);
            }}
          />
        ) : null}
        {step === 'confirm' && project !== null ? (
          <ConfirmStep
            project={project}
            onChange={onChoices}
            onConfirm={() => setConfirmed(true)}
            onBack={() => setProject(null)}
          />
        ) : null}
        {step === 'start' && project !== null ? (
          <StartStep project={project} onStarted={setStarted} onBack={() => setConfirmed(false)} />
        ) : null}
        {step === null && project !== null && started !== null ? (
          <DoneStep project={project} started={started} onFinish={onFinished} />
        ) : null}
      </div>
    </div>
  );
}

/** Where the person is: an ordered list, the current step marked for assistive technology. */
function Progress({ current }: { current: StepId | null }) {
  const at = current === null ? STEP_ORDER.length : STEP_ORDER.indexOf(current);
  return (
    <ol aria-label={COPY.progressLabel} className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
      {STEP_ORDER.map((id, index) => {
        const done = index < at;
        const here = index === at;
        return (
          <li
            key={id}
            aria-current={here ? 'step' : undefined}
            className={here ? 'font-semibold' : done ? 'text-muted-foreground' : 'text-muted-foreground/70'}
          >
            {done ? <Check className="mr-1 inline size-3.5" aria-hidden="true" /> : null}
            {here ? <span className="sr-only">{COPY.stepWord(index + 1, STEP_ORDER.length)}: </span> : null}
            {COPY.steps[id]}
          </li>
        );
      })}
    </ol>
  );
}

function CliPanel({ onRetry }: { onRetry: () => void }) {
  const heading = useFocusOnMount<HTMLHeadingElement>();
  return (
    <section aria-labelledby="cli-heading" className="flex flex-col gap-4">
      <h2 id="cli-heading" ref={heading} tabIndex={-1} className="text-lg font-semibold outline-hidden">
        {COPY.cli.heading}
      </h2>
      <p>{COPY.cli.body}</p>
      <div className="flex flex-wrap items-center gap-2">
        <InstallCliButton onInstalled={onRetry} />
        <Button variant="outline" size="sm" onClick={onRetry}>
          {COPY.cli.lookAgain}
        </Button>
      </div>
    </section>
  );
}
