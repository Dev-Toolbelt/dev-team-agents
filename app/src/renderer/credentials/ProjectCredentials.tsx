import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FileWarning, KeyRound, RefreshCw } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import {
  CREDENTIALS_ALREADY_EXISTS,
  CREDENTIALS_HASH_CONFLICT,
  CREDENTIALS_SAVED_UNREADABLE,
  type CredentialsLocalView,
  type EnvironmentReport,
  type OperationResult,
  type ProjectRecord,
} from '../../shared/api.js';
import { Loading, Problem } from '../Problem.js';
import { SaveBar } from '../SaveBar.js';
import { toastPartialFailure, toastResult } from '../toasts.js';
import { useOnActivate } from '../useOnDeactivate.js';
import { unreachable } from '../useOperation.js';
import { WriteButton } from '../WriteButton.js';
import { CREDENTIALS_COMMANDS, isWithheld } from '../writeActionGating.js';
import { CredentialsForm } from './CredentialsForm.js';
import { EMPTY_DRAFTS, reportDrafts, type Drafts } from './drafts.js';

type Failure = Extract<OperationResult<never>, { ok: false }>;

/** Why a save is refused because the file moved under the form; the one failure that has its own words. */
export function isHashConflict(failure: Failure): boolean {
  return failure.kind === 'conflict' && failure.reason === CREDENTIALS_HASH_CONFLICT;
}

/**
 * The Credentials tab of one project's screen (ADR-0024 § 5): the project's local credentials
 * file as a form. The file is the source of truth and a developer may still edit it by hand, so
 * the form reloads when the tab is shown and a save sends only the leaves that changed, with the
 * hash it loaded, so a stale form cannot overwrite a hand edit.
 */
export function ProjectCredentials({
  project,
  environment,
  onDirtyChange,
  onRunningChange,
  active = true,
}: {
  project: ProjectRecord;
  environment: EnvironmentReport | null;
  onDirtyChange: (count: number) => void;
  onRunningChange: (count: number) => void;
  /** Whether this tab is the one showing; the file is re-read each time it becomes so. */
  active?: boolean;
}) {
  const projectId = project.project_id;
  const [view, setView] = useState<CredentialsLocalView | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadFailure, setLoadFailure] = useState<Failure | null>(null);
  const [drafts, setDrafts] = useState<Drafts>(EMPTY_DRAFTS);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [saveFailure, setSaveFailure] = useState<Failure | null>(null);
  // The file moved under the form: nothing can be saved against this hash until it is re-read.
  const [stale, setStale] = useState(false);
  const [confirmReload, setConfirmReload] = useState(false);
  const request = useRef(0);
  const changesNow = useRef(0);

  /** `discard`: the user chose to drop unsaved edits, so nothing typed meanwhile is kept either. */
  const load = useCallback(async (discard = false) => {
    const mine = ++request.current;
    const changesAtStart = discard ? Number.POSITIVE_INFINITY : changesNow.current;
    setLoading(true);
    const result = await window.devteam.credentialsLocalShow(projectId).catch(unreachable);
    if (mine !== request.current) return;
    setLoading(false);
    if (result.ok) {
      // Something was typed while the file was being read: keep the view those edits were
      // made against, so the hash they are saved with is the one they were diffed from.
      if (changesNow.current > changesAtStart) return;
      setView(result.data);
      setLoadFailure(null);
      setDrafts(EMPTY_DRAFTS);
      setSaveFailure(null);
      setStale(false);
    } else {
      setLoadFailure(result);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const report = useMemo(
    () => (view !== null && view.valid && view.data !== null ? reportDrafts(view, drafts) : { ops: [], problems: {}, changes: 0 }),
    [view, drafts],
  );

  // Re-read the file when the tab comes back, unless that would discard something typed.
  useOnActivate(active, () => {
    if (report.changes === 0 && !saving && !creating) void load();
  });

  /** Reload on request: through the discard confirmation whenever there is something to lose. */
  function requestReload(): void {
    if (report.changes > 0) setConfirmReload(true);
    else void load(true);
  }

  changesNow.current = report.changes;
  useEffect(() => {
    onDirtyChange(report.changes);
  }, [report.changes, onDirtyChange]);
  const running = saving || creating ? 1 : 0;
  useEffect(() => {
    onRunningChange(running);
  }, [running, onRunningChange]);

  /** A write supersedes any read still in flight: its answer would overwrite the newer view and hash. */
  function supersedeLoads(): void {
    request.current += 1;
    setLoading(false);
  }

  async function create() {
    supersedeLoads();
    setCreating(true);
    setSaveFailure(null);
    const result = await window.devteam.credentialsLocalInit(projectId).catch(unreachable);
    setCreating(false);
    if (result.ok) {
      setView(result.data);
      setLoadFailure(null);
      toastResult(result, 'Created the credentials file', 'credentials-create');
    } else if (result.kind === 'conflict' && result.reason === CREDENTIALS_ALREADY_EXISTS) {
      await load();
    } else {
      setSaveFailure(result);
    }
  }

  async function save() {
    if (view === null || view.hash === null || report.ops.length === 0 || stale) return;
    supersedeLoads();
    setSaving(true);
    setSaveFailure(null);
    const result = await window.devteam.credentialsLocalPatch(projectId, view.hash, report.ops).catch(unreachable);
    setSaving(false);
    if (result.ok) {
      setView(result.data);
      setDrafts(EMPTY_DRAFTS);
      toastResult(result, 'Saved the credentials file', 'credentials-save');
    } else if (result.kind === 'contract-breach' && result.reason === CREDENTIALS_SAVED_UNREADABLE) {
      // The write went through; only the answer was lost. Re-read rather than show a failed save.
      setDrafts(EMPTY_DRAFTS);
      toastPartialFailure('Saved the credentials file, but the response was unreadable', 'The file was reloaded to show what it holds now.');
      await load();
    } else {
      if (isHashConflict(result)) setStale(true);
      setSaveFailure(result);
    }
  }

  const gate = environment === null
    ? { withheld: true as const, reason: 'the app has not finished checking its own preconditions' }
    : isWithheld(environment.withheld, CREDENTIALS_COMMANDS.patch);
  const hasProblems = Object.keys(report.problems).length > 0;
  const busy = saving || creating;
  const reloading = loading && view !== null;
  const status = hasProblems
    ? `${Object.keys(report.problems).length} value needs fixing before you can save`
    : `${report.changes} change${report.changes === 1 ? '' : 's'} not saved yet`;

  const header = (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0 space-y-1">
        <h3 className="flex items-center gap-2 text-base font-semibold">
          <KeyRound className="size-4" aria-hidden="true" />
          Local credentials
        </h3>
        <p className="text-sm text-muted-foreground">
          Staging and production access for the agents. Secrets are write-only: set or replace them here, never read back.
        </p>
        {view !== null ? <p className="break-all font-mono text-xs text-muted-foreground">{view.path}</p> : null}
      </div>
      <Button
        variant="outline"
        size="sm"
        disabled={loading || busy}
        onClick={requestReload}
      >
        <RefreshCw className={loading ? 'animate-spin motion-reduce:animate-none' : undefined} aria-hidden="true" />
        Reload
      </Button>
    </div>
  );

  if (view === null) {
    return (
      <div className="space-y-4">
        {header}
        {loading ? <Loading what="cred local show" /> : loadFailure !== null ? <Problem problem={loadFailure} /> : null}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {header}
      {loadFailure !== null ? <Problem problem={loadFailure} /> : null}

      {!view.exists ? (
        <div className="space-y-3 rounded-xl border border-dashed p-6">
          <p className="text-sm font-medium">There is no credentials file yet.</p>
          <p className="text-sm text-muted-foreground">
            The agents read their staging and production logins from this file. Create it with the standard layout, then fill it in here.
          </p>
          <WriteButton command={CREDENTIALS_COMMANDS.init} environment={environment} disabled={busy} onClick={() => void create()}>
            {creating ? 'Creating…' : 'Create file'}
          </WriteButton>
        </div>
      ) : !view.valid ? (
        <Alert variant="destructive">
          <FileWarning />
          <AlertTitle>The credentials file is not valid JSON</AlertTitle>
          <AlertDescription>
            <p>
              {view.error?.message ?? 'The file could not be parsed.'}
              {view.error?.line != null ? ` (line ${view.error.line}${view.error.column != null ? `, column ${view.error.column}` : ''})` : ''}
              . Fix it in the file, then reload.
            </p>
          </AlertDescription>
        </Alert>
      ) : (
        <>
          <p role="status" aria-live="polite" className="sr-only">
            {report.changes > 0 ? status : ''}
          </p>
          <fieldset disabled={reloading || stale} className="m-0 min-w-0 border-0 p-0" aria-busy={reloading || undefined}>
            <CredentialsForm view={view} drafts={drafts} report={report} disabled={busy || reloading || stale} onDrafts={setDrafts} />
          </fieldset>
        </>
      )}

      {saveFailure !== null ? (
        isHashConflict(saveFailure) ? (
          <Alert variant="destructive">
            <FileWarning />
            <AlertTitle>The file changed on disk</AlertTitle>
            <AlertDescription>
              <p>It changed since it was loaded. Reload to see the latest version; unsaved edits are discarded.</p>
              <Button variant="outline" size="sm" className="mt-2" disabled={loading} onClick={requestReload}>
                Reload
              </Button>
            </AlertDescription>
          </Alert>
        ) : saveFailure.kind === 'conflict' && saveFailure.reason === undefined ? (
          <Alert variant="destructive">
            <FileWarning />
            <AlertTitle>The credentials file is busy</AlertTitle>
            <AlertDescription>
              <p>Another process is using it right now. Your edits are kept: try saving again in a moment.</p>
            </AlertDescription>
          </Alert>
        ) : (
          <Problem problem={saveFailure} />
        )
      ) : null}

      {view.valid ? (
        <SaveBar
          dirtyCount={report.changes}
          invalid={Object.keys(report.problems).length}
          status={status}
          saving={saving}
          canSave={!saving && !reloading && !stale && report.ops.length > 0 && !hasProblems && !gate.withheld}
          withheld={gate.withheld ? gate.reason : stale ? 'the file changed on disk; reload it first' : null}
          shortcut={false}
          label="Unsaved credential changes"
          onDiscard={() => {
            setDrafts(EMPTY_DRAFTS);
            if (!stale) setSaveFailure(null);
          }}
          onSave={() => void save()}
        />
      ) : null}

      <Dialog open={confirmReload} onOpenChange={setConfirmReload}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Discard unsaved changes and reload?</DialogTitle>
            <DialogDescription>
              {report.changes} change{report.changes === 1 ? '' : 's'} not saved yet will be lost when the file is read again.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmReload(false)}>
              Keep editing
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                setConfirmReload(false);
                setDrafts(EMPTY_DRAFTS);
                void load(true);
              }}
            >
              Discard and reload
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
