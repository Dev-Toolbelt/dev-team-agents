import { useState } from 'react';

import { Button } from '@/components/ui/button';
import type { CliInstallResult } from '../shared/api.js';
import { CommandBox } from './onboarding/CopyButton.js';
import { COPY } from './onboarding/copy.js';

/**
 * "Install the CLI" (ADR-0028), on Windows and macOS. The main process does the work: on
 * Windows it downloads the newest CLI installer from GitHub, checks its SHA-256 and runs its
 * wizard; on macOS it runs `brew install` from the tap. When it cannot (no Homebrew), the answer
 * carries the exact command and this shows it with a copy button, since the published script
 * has no checksum of its own and the app does not download it. On success the app looks again,
 * which finds the CLI in the installer's directory even though this process started with the
 * old PATH.
 */
export function InstallCliButton({ onInstalled }: { onInstalled: () => void }) {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<CliInstallResult | null>(null);

  const install = async () => {
    setRunning(true);
    setResult(null);
    try {
      const outcome = await window.devteam.installCli();
      setResult(outcome);
      if (outcome.outcome === 'installed') onInstalled();
    } catch (error) {
      setResult({ outcome: 'failed', message: `The install could not be started: ${String(error)}` });
    } finally {
      setRunning(false);
    }
  };

  return (
    <>
      <Button size="sm" onClick={() => void install()} disabled={running}>
        {running ? COPY.cli.installing : COPY.cli.install}
      </Button>
      {/* Still on this screen after an install means the CLI was not found: say so, rather
          than letting a successful install look like nothing happened. */}
      {result !== null ? (
        <div role="status" className="basis-full">
          <p>{result.outcome === 'installed' ? `${result.message} ${COPY.cli.foundAfter}` : result.message}</p>
          {result.command !== undefined ? <CommandBox text={result.command} label={COPY.cli.copy} /> : null}
        </div>
      ) : null}
    </>
  );
}
