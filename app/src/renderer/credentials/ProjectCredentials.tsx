import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FileWarning, KeyRound, RefreshCw, ShieldCheck } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import {
  CREDENTIALS_ALREADY_EXISTS,
  CREDENTIALS_HASH_CONFLICT,
  CREDENTIALS_INSECURE_IN_PRODUCTION,
  CREDENTIALS_MAX_SECURE_POINTERS,
  CREDENTIALS_PLAINTEXT_IN_PRODUCTION,
  CREDENTIALS_SAVED_UNREADABLE,
  type CredentialsLocalView,
  type CredentialsPatchOp,
  type CredentialsPlaintextSecret,
  type EnvironmentReport,
  type OperationResult,
  type ProjectRecord,
} from '../../shared/api.js';
import { Loading, Problem } from '../Problem.js';
import { SaveBar } from '../SaveBar.js';
import { toastFailure, toastPartialFailure, toastResult } from '../toasts.js';
import { useOnActivate } from '../useOnDeactivate.js';
import { unreachable } from '../useOperation.js';
import { WriteButton } from '../WriteButton.js';
import { CREDENTIALS_COMMANDS, isWithheld } from '../writeActionGating.js';
import { CredentialsEditor } from './CredentialsEditor.js';
import {
  MAX_OPS,
  applyOps,
  forgetSecretWrite,
  forgetSecretWritesUnder,
  opsFor,
  pendingSecretPointers,
  plaintextSecrets,
  pointerOf,
  record,
  valueAt,
  type Edit,
} from './document.js';

type Failure = Extract<OperationResult<never>, { ok: false }>;

/** Why a save is refused because the file moved under the form; the one failure that has its own words. */
export function isHashConflict(failure: Failure): boolean {
  return failure.kind === 'conflict' && failure.reason === CREDENTIALS_HASH_CONFLICT;
}

const REFUSALS: Readonly<Record<string, { title: string; body: string }>> = {
  [CREDENTIALS_PLAINTEXT_IN_PRODUCTION]: {
    title: 'Production secrets cannot be plain text',
    body: 'A group marked Production does not accept a secret written in the file. Enter the value with Set or Replace so it is stored securely, or use a password manager reference.',
  },
  [CREDENTIALS_INSECURE_IN_PRODUCTION]: {
    title: 'No secure store on this machine',
    body: 'This machine has no keychain to hold production secrets, and the unencrypted fallback is refused for them. Use a password manager reference (op:// or bw://) instead, or save the secret from a machine with a keychain.',
  },
  'tracked-file': {
    title: 'The credentials file is tracked by git',
    body: 'References are not resolved while credentials.local.json is tracked by git, so a value could leak into the repository. Stop tracking the file (git rm --cached) and try again.',
  },
  'tracked-file-unknown': {
    title: 'Git could not say whether the file is tracked',
    body: 'References are not resolved until git can confirm credentials.local.json is not tracked. Check that this folder is a working git repository and try again.',
  },
  'invalid-ref': {
    title: 'A reference is malformed',
    body: 'Use op://vault/item/field for 1Password or bw://item-uuid/field for Bitwarden.',
  },
  'value-too-large': {
    title: 'A secret is too large',
    body: 'A secret holds at most 3072 bytes. Shorten it, or keep it in a password manager and use a reference.',
  },
  'invalid-secret-value': {
    title: 'A secret value is not valid',
    body: 'A secret cannot contain a line break or NUL. Enter it again without them.',
  },
};

/** The words for a refusal that has its own reason (ADR-0053), or `null`. */
export function productionRefusal(failure: Failure): { title: string; body: string } | null {
  return failure.reason !== undefined ? (REFUSALS[failure.reason] ?? null) : null;
}

/** A confirmation the user must give before plaintext secrets move out of the file. */
interface SecureRequest {
  /** Exactly what is sent: the pointers the listing named, or the one field asked about. */
  readonly found: readonly CredentialsPlaintextSecret[];
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
  // Edits since the file was loaded, as `cred local patch` ops in the order they were made.
  const [ops, setOps] = useState<readonly CredentialsPatchOp[]>([]);
  // Fields holding text that is not a valid value yet (a number field with letters), by pointer.
  const [problems, setProblems] = useState<Readonly<Record<string, string>>>({});
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [saveFailure, setSaveFailure] = useState<Failure | null>(null);
  // The file moved under the form: nothing can be saved against this hash until it is re-read.
  const [stale, setStale] = useState(false);
  const [confirmReload, setConfirmReload] = useState(false);
  const [secureRequest, setSecureRequest] = useState<SecureRequest | null>(null);
  const [securing, setSecuring] = useState(false);
  const [secureNote, setSecureNote] = useState<string | null>(null);
  const [secureFailure, setSecureFailure] = useState<Failure | null>(null);
  const request = useRef(0);
  const changesNow = useRef(0);
  const copying = useRef(false);

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
      clearEdits();
      setSaveFailure(null);
      setStale(false);
    } else {
      setLoadFailure(result);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const data = view !== null && view.valid ? view.data : null;
  const doc = useMemo(() => (data !== null ? applyOps(data, ops) : null), [data, ops]);
  const report = { ops, problems, changes: ops.length };

  function clearEdits(): void {
    setOps([]);
    setProblems({});
  }

  const onEdit = useCallback(
    (edit: Edit) => {
      if (data === null) return;
      // Functional: two edits in one event (add a field, then mark it secret) each see the first.
      setOps((previous) => {
        if (edit.kind !== 'remove') return record(previous, ...opsFor(applyOps(data, previous), edit));
        // Removing a field that only exists as an unsaved secret: forget that write, there is nothing on disk to unset.
        const kept = forgetSecretWritesUnder(previous, pointerOf(edit.path));
        if (kept.length === previous.length) return record(previous, ...opsFor(applyOps(data, previous), edit));
        return valueAt(applyOps(data, kept), edit.path) === undefined ? kept : record(kept, ...opsFor(applyOps(data, kept), edit));
      });
    },
    [data],
  );
  const onProblem = useCallback((pointer: string, problem: string | null) => {
    setProblems((previous) => {
      if (problem === null) {
        if (!(pointer in previous)) return previous;
        return Object.fromEntries(Object.entries(previous).filter(([key]) => key !== pointer));
      }
      return previous[pointer] === problem ? previous : { ...previous, [pointer]: problem };
    });
  }, []);

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
    const result = await window.devteam.credentialsLocalPatch(projectId, view.hash, [...report.ops]).catch(unreachable);
    setSaving(false);
    if (result.ok) {
      setView(result.data);
      clearEdits();
      toastResult(result, 'Saved the credentials file', 'credentials-save');
    } else if (result.kind === 'contract-breach' && result.reason === CREDENTIALS_SAVED_UNREADABLE) {
      // The write went through; only the answer was lost. Re-read rather than show a failed save.
      clearEdits();
      toastPartialFailure('Saved the credentials file, but the response was unreadable', 'The file was reloaded to show what it holds now.');
      await load();
    } else {
      if (isHashConflict(result)) setStale(true);
      setSaveFailure(result);
    }
  }

  /**
   * Copy one hidden value (ADR-0046). The main process puts it on the clipboard; this answer
   * carries only when it is cleared. Not offered over unsaved edits: a renamed or moved field's
   * pointer would no longer match the file the hash names.
   */
  async function copySecret(pointer: string): Promise<boolean> {
    // One copy at a time across the tab: the clipboard holds one value, and a second copy
    // racing the first would leave which one is on it to chance.
    if (view === null || view.hash === null || stale || copying.current) return false;
    copying.current = true;
    const result = await window.devteam
      .credentialsLocalCopySecret(projectId, view.hash, pointer)
      .catch(unreachable)
      .finally(() => {
        copying.current = false;
      });
    if (result.ok) {
      toastResult(result, `Copied. The clipboard is cleared in ${result.data.clearsInSeconds} s`, 'credentials-copy');
      return true;
    }
    if (isHashConflict(result)) setStale(true);
    const refusal = productionRefusal(result);
    toastFailure(refusal !== null ? { ...result, message: `${refusal.title}. ${refusal.body}` } : result, 'credentials-copy');
    return false;
  }
  const copyBlocked =
    stale ? 'The file changed on disk: reload to copy' : report.changes > 0 ? 'Save or discard your edits to copy a value' : null;

  /** List what would move (the CLI is the judge of what looks secret), then ask. Nothing moves yet. */
  async function reviewPlaintext(): Promise<void> {
    if (secureBlocked !== null || securing) return;
    setSecuring(true);
    setSecureFailure(null);
    setSecureNote(null);
    const result = await window.devteam.credentialsLocalSecureList(projectId).catch(unreachable);
    setSecuring(false);
    if (!result.ok) {
      setSecureFailure(result);
      return;
    }
    if (result.data.secrets.length === 0) {
      toastResult(result, 'No plain text secrets in the file', 'credentials-secure');
      return;
    }
    if (result.data.secrets.length > CREDENTIALS_MAX_SECURE_POINTERS) {
      setSecureNote(
        `${result.data.secrets.length} secrets are in plain text. Secure at most ${CREDENTIALS_MAX_SECURE_POINTERS} at a time: use Secure now on some of them first.`,
      );
      return;
    }
    setSecureRequest({ found: result.data.secrets });
  }

  /** One field's "Secure now": the confirmation names just that field. */
  function secureOne(pointer: string): void {
    if (secureBlocked !== null) return;
    setSecureFailure(null);
    setSecureNote(null);
    setSecureRequest({ found: plaintext.filter((entry) => entry.pointer === pointer) });
  }

  function closeSecure(): void {
    setSecureRequest(null);
    setSecureFailure(null);
  }

  async function applySecure(): Promise<void> {
    if (secureRequest === null || secureRequest.found.length === 0 || secureGate.withheld) return;
    supersedeLoads();
    setSecuring(true);
    setSecureFailure(null);
    const result = await window.devteam
      .credentialsLocalSecureApply(projectId, secureRequest.found.map((entry) => entry.pointer))
      .catch(unreachable);
    setSecuring(false);
    if (result.ok) {
      setSecureRequest(null);
      setSecureNote(null);
      toastResult(result, 'Moved the secrets out of the file', 'credentials-secure');
      await load();
    } else {
      setSecureFailure(result);
    }
  }

  const gate = environment === null
    ? { withheld: true as const, reason: 'the app has not finished checking its own preconditions' }
    : isWithheld(environment.withheld, CREDENTIALS_COMMANDS.patch);
  const plaintext = useMemo(() => (doc !== null ? plaintextSecrets(doc) : []), [doc]);
  const secureGate = environment === null
    ? { withheld: true as const, reason: 'the app has not finished checking its own preconditions' }
    : isWithheld(environment.withheld, CREDENTIALS_COMMANDS.secure);
  const secureBlocked = secureGate.withheld
    ? `Securing is unavailable: ${secureGate.reason}`
    : stale
      ? 'The file changed on disk: reload first'
      : report.changes > 0
        ? 'Save or discard your edits first'
        : null;
  const pendingSecrets = useMemo(() => pendingSecretPointers(ops), [ops]);
  const onForget = useCallback((pointer: string) => setOps((previous) => forgetSecretWrite(previous, pointer)), []);
  const saveRefusal = saveFailure !== null ? productionRefusal(saveFailure) : null;
  const secureRefusal = secureFailure !== null ? productionRefusal(secureFailure) : null;
  const hasProblems = Object.keys(report.problems).length > 0;
  const busy = saving || creating;
  const reloading = loading && view !== null;
  const status = hasProblems
    ? `${Object.keys(report.problems).length} value needs fixing before you can save`
    : report.changes > MAX_OPS
      ? `${report.changes} changes: save at most ${MAX_OPS} at a time`
      : `${report.changes} change${report.changes === 1 ? '' : 's'} not saved yet`;

  const header = (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0 space-y-1">
        <h3 className="flex items-center gap-2 text-base font-semibold">
          <KeyRound className="size-4" aria-hidden="true" />
          Local credentials
        </h3>
        <p className="text-sm text-muted-foreground">
          Settings, tokens and secrets the agents use, organised any way you like. Values marked secret are write-only.
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
          {plaintext.length > 0 ? (
            <Alert role="group" aria-label="Plain text secrets" variant={plaintext.some((entry) => entry.production) ? 'destructive' : 'default'}>
              <ShieldCheck />
              <AlertTitle>
                {plaintext.length} secret{plaintext.length === 1 ? ' is' : 's are'} stored as plain text in this file
              </AlertTitle>
              <AlertDescription>
                <p>
                  Anyone or anything that can read the file can read them
                  {plaintext.some((entry) => entry.production) ? ', and some belong to a Production group' : ''}. Move them out of the file; the
                  file keeps a reference in their place.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  disabled={securing || busy || reloading || secureBlocked !== null}
                  aria-describedby={secureBlocked !== null ? 'credentials-secure-why' : undefined}
                  onClick={() => void reviewPlaintext()}
                >
                  {securing ? 'Checking…' : 'Secure plaintext secrets'}
                </Button>
                {secureBlocked !== null ? (
                  <p id="credentials-secure-why" className="mt-1 text-xs text-muted-foreground">
                    {secureBlocked}
                  </p>
                ) : null}
              </AlertDescription>
            </Alert>
          ) : null}
          {secureNote !== null ? (
            <Alert variant="destructive">
              <FileWarning />
              <AlertTitle>Too many to move at once</AlertTitle>
              <AlertDescription>
                <p>{secureNote}</p>
              </AlertDescription>
            </Alert>
          ) : null}
          {secureFailure !== null && secureRequest === null ? <Problem problem={secureFailure} /> : null}
          <fieldset disabled={reloading || stale} className="m-0 min-w-0 border-0 p-0" aria-busy={reloading || undefined}>
            {doc !== null ? (
              <CredentialsEditor
                doc={doc}
                disabled={busy || reloading || stale}
                onEdit={onEdit}
                onProblem={onProblem}
                onCopySecret={copySecret}
                copyBlocked={copyBlocked}
                onSecureNow={secureOne}
                secureBlocked={secureBlocked}
                pending={pendingSecrets}
                onForget={onForget}
              />
            ) : null}
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
        ) : saveRefusal !== null ? (
          <Alert variant="destructive">
            <FileWarning />
            <AlertTitle>{saveRefusal.title}</AlertTitle>
            <AlertDescription>
              <p>{saveRefusal.body} Your edits are kept.</p>
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
          canSave={!saving && !reloading && !stale && report.ops.length > 0 && report.ops.length <= MAX_OPS && !hasProblems && !gate.withheld}
          withheld={gate.withheld ? gate.reason : stale ? 'the file changed on disk; reload it first' : null}
          shortcut={false}
          label="Unsaved credential changes"
          onDiscard={() => {
            clearEdits();
            if (!stale) setSaveFailure(null);
          }}
          onSave={() => void save()}
        />
      ) : null}

      <Dialog open={secureRequest !== null} onOpenChange={(open) => (open || securing ? undefined : closeSecure())}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Move {secureRequest?.found.length ?? 0} secret{secureRequest?.found.length === 1 ? '' : 's'} out of the file?</DialogTitle>
            <DialogDescription>
              Each value is stored outside the file and the file keeps a reference in its place. Nothing else in
              the file changes, and the values are not shown.
            </DialogDescription>
          </DialogHeader>
          <ul className="max-h-48 space-y-1 overflow-auto text-sm" role="list">
            {secureRequest?.found.map((entry) => (
              <li key={entry.pointer} className="flex items-center justify-between gap-2">
                <span className="break-all font-mono">{entry.pointer}</span>
                {entry.production ? <span className="text-xs text-destructive">Production</span> : null}
              </li>
            ))}
          </ul>
          {secureFailure !== null ? (
            secureRefusal !== null ? (
              <Alert variant="destructive">
                <FileWarning />
                <AlertTitle>{secureRefusal.title}</AlertTitle>
                <AlertDescription>
                  <p>{secureRefusal.body} The file was not changed.</p>
                </AlertDescription>
              </Alert>
            ) : (
              <Problem problem={secureFailure} />
            )
          ) : null}
          <DialogFooter>
            <Button variant="outline" disabled={securing} onClick={closeSecure}>
              Cancel
            </Button>
            <Button disabled={securing || secureGate.withheld} onClick={() => void applySecure()}>
              {securing ? 'Moving…' : 'Move out of the file'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
                clearEdits();
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
