import { useEffect, useId, useMemo, useState } from 'react';
import { CheckCircle2, CircleAlert, GitBranch, Info } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Hint } from '@/components/ui/tooltip';
import type { EnvironmentReport, IntegrationTestResult, IntegrationView, OperationResult, ProjectId } from '../../shared/api.js';
import { CardShell } from '../cards/CardShell.js';
import { gateFor } from '../cards/gate.js';
import { StatusFacts } from '../cards/StatusFacts.js';
import { Problem } from '../Problem.js';
import { SaveBar } from '../SaveBar.js';
import { unreachable, useAction } from '../useOperation.js';
import { INTEGRATION_COMMANDS } from '../writeActionGating.js';
import { FieldRow } from './FieldRow.js';
import { changedValues, fieldStates, standingOf, type FieldDrafts } from './model.js';
import { TokenInput } from './TokenInput.js';

export type IntegrationMode = 'account' | 'project';

type Failure = Extract<OperationResult<never>, { ok: false }>;
/** A project save is a run of config writes; it stops at the first failure and says which keys landed. */
interface WriteOutcome {
  readonly applied: readonly string[];
  readonly view: IntegrationView | null;
  readonly failed: { readonly key: string; readonly problem: Failure } | null;
}

/** A timestamp in the reader's locale; the ISO value stays machine-readable in the element. */
function CheckedAt({ iso }: { iso: string }) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return <time dateTime={iso}>{iso}</time>;
  return (
    <time dateTime={iso} title={iso}>
      {new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date)}
    </time>
  );
}

const GOOD = 'flex items-center gap-2 rounded-md border border-green-600 bg-green-50 px-3 py-2 text-sm text-green-900 dark:border-green-500 dark:bg-green-950 dark:text-green-200';
const BAD = 'flex items-center gap-2 rounded-md border border-amber-500/60 px-3 py-2 text-sm text-amber-800 dark:text-amber-300';

/**
 * One integration, drawn from its `IntegrationView` alone — nothing here knows an integration
 * by name. `account` mode is the top-level tab: the write-only token, account fields, Test
 * connection and Disconnect. `project` mode is the project tab: the account standing read-only
 * and the project-scope fields, each written with `integration config set/unset`.
 *
 * Edits are staged in drafts and written only by this card's Save. Every write answers with the
 * updated view, which goes back to the screen through `onView`; nothing re-reads the list.
 */
export function IntegrationCard({
  mode,
  projectId,
  view,
  environment,
  onView,
  onDirtyChange,
  onRunningChange,
  open,
  onOpenChange,
  lockedReason,
  onConnectAccount,
}: {
  mode: IntegrationMode;
  projectId: ProjectId | null;
  view: IntegrationView;
  environment: EnvironmentReport | null;
  onView: (view: IntegrationView) => void;
  onDirtyChange: (name: string, count: number) => void;
  onRunningChange: (name: string, count: number) => void;
  open: boolean;
  onOpenChange: (name: string, open: boolean) => void;
  lockedReason: string | null;
  /** Project mode: take the person to the account tab to connect. */
  onConnectAccount?: (() => void) | undefined;
}) {
  const uid = useId();
  const name = view.name;
  const isAccount = mode === 'account';
  const [drafts, setDrafts] = useState<FieldDrafts>({});
  const [token, setToken] = useState('');
  const [replacing, setReplacing] = useState(false);
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const [lastTest, setLastTest] = useState<IntegrationTestResult | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [partial, setPartial] = useState<WriteOutcome['failed']>(null);

  const connector = useAction(
    (fields: Record<string, string>, secret: string | null) => window.devteam.integrationConnect(name, fields, secret, projectId),
  );
  const tester = useAction(() => window.devteam.integrationTest(name, projectId));
  const disconnector = useAction(() => window.devteam.integrationDisconnect(name, false));
  const writer = useAction(async (changes: Record<string, string>): Promise<WriteOutcome> => {
    let last: IntegrationView | null = null;
    const applied: string[] = [];
    for (const [key, value] of Object.entries(changes)) {
      const result = await (value === ''
        ? window.devteam.integrationConfigUnset(name, key, projectId)
        : window.devteam.integrationConfigSet(name, key, value, projectId)
      ).catch(unreachable);
      if (!result.ok) return { applied, view: last, failed: { key, problem: result } };
      last = result.data.integration;
      applied.push(key);
    }
    return { applied, view: last, failed: null };
  });

  const states = useMemo(() => fieldStates(view, mode, drafts), [view, mode, drafts]);
  const changes = useMemo(() => changedValues(states), [states]);
  const changedCount = Object.keys(changes).length;
  const tokenTyped = isAccount && token !== '';
  const dirtyCount = changedCount + (tokenTyped ? 1 : 0);
  const invalid = states.filter((state) => state.error !== null).length;

  useEffect(() => {
    onDirtyChange(name, dirtyCount);
    return () => onDirtyChange(name, 0);
  }, [name, dirtyCount, onDirtyChange]);

  const saving = connector.state.phase === 'pending' || writer.state.phase === 'pending';
  const testing = tester.state.phase === 'pending';
  const disconnecting = disconnector.state.phase === 'pending';
  const running = saving || testing || disconnecting;
  useEffect(() => {
    onRunningChange(name, running ? 1 : 0);
    return () => onRunningChange(name, 0);
  }, [name, running, onRunningChange]);

  const saveGate = gateFor(environment, isAccount ? [INTEGRATION_COMMANDS.connect] : [INTEGRATION_COMMANDS.configSet, INTEGRATION_COMMANDS.configUnset]);
  const testGate = gateFor(environment, [INTEGRATION_COMMANDS.test]);
  const disconnectGate = gateFor(environment, [INTEGRATION_COMMANDS.disconnect]);

  // The stored token is bound to the origin of the field(s) the descriptor marks `binds_token`:
  // changing one, or an origin that already changed under it, means the old token must not
  // travel to the new address. Other account fields save without it, as on the CLI.
  const staleToken = view.auth.stale;
  const bindingChanged = states.some((state) => state.field.binds_token && state.field.key in changes);
  const retypeToken = isAccount && view.auth.has_token && !tokenTyped && (staleToken || bindingChanged);
  const needsToken = isAccount && !view.auth.has_token && !tokenTyped;
  const projectUnbound = !isAccount && view.project === null;
  const canSave = dirtyCount > 0 && invalid === 0 && !needsToken && !retypeToken && !saveGate.withheld && !running && !projectUnbound;
  const status =
    invalid > 0
      ? `${invalid} value${invalid === 1 ? ' needs' : 's need'} fixing before you can save`
      : needsToken
        ? 'Enter a token to connect'
        : retypeToken
          ? 'Changing the address requires re-entering the token'
          : dirtyCount > 0
          ? `${dirtyCount} unsaved change${dirtyCount === 1 ? '' : 's'}`
          : '';

  const lastSave = isAccount ? (connector.state.phase === 'done' ? connector.state.result : null) : null;
  const lastTestRun = tester.state.phase === 'done' ? tester.state.result : null;
  const lastDisconnect = disconnector.state.phase === 'done' ? disconnector.state.result : null;

  function reportTest(result: IntegrationTestResult) {
    setLastTest(result);
  }

  async function save() {
    if (!canSave) return;
    setSaved(null);
    setWarning(null);
    setPartial(null);
    setLastTest(null);
    if (isAccount) {
      // The token leaves state the moment it is submitted, whether or not the write succeeds.
      const secret = tokenTyped ? token : null;
      setToken('');
      setReplacing(false);
      const result = await connector.run(changes, secret);
      if (!result.ok) return;
      setDrafts({});
      onView(result.data.integration);
      reportTest(result.data.test);
      setSaved('Settings saved.');
      setWarning(result.data.warning);
      return;
    }
    const outcome = await writer.run(changes);
    if (outcome.view !== null) onView(outcome.view);
    setDrafts((previous) => Object.fromEntries(Object.entries(previous).filter(([key]) => !outcome.applied.includes(key))));
    if (outcome.failed !== null) setPartial(outcome.failed);
    else setSaved(`Saved ${outcome.applied.length} change${outcome.applied.length === 1 ? '' : 's'} to this project. It is committed with the project, so commit the file to share it.`);
  }

  async function test() {
    setSaved(null);
    setLastTest(null);
    const result = await tester.run();
    if (!result.ok) return;
    onView(result.data.integration);
    reportTest(result.data.test);
  }

  async function disconnect() {
    setConfirmDisconnect(false);
    setSaved(null);
    setLastTest(null);
    const result = await disconnector.run();
    if (!result.ok) return;
    setToken('');
    setReplacing(false);
    onView(result.data.integration);
    setSaved(`${view.title} is disconnected. The token was removed; the settings are kept.`);
  }

  const reasonFor = (gate: ReturnType<typeof gateFor>) => (gate.withheld ? `Withheld: ${gate.reason}` : null);
  const testReason =
    reasonFor(testGate) ?? (!view.auth.has_token ? 'Connect first: there is no token to test.' : dirtyCount > 0 ? 'Save or discard changes first.' : null);
  const removeReason = reasonFor(disconnectGate) ?? (dirtyCount > 0 ? 'Save or discard changes first.' : null);
  const standing = standingOf(view);
  const shownResult = lastTest;
  const accountReadout = view.status.checked_at !== null || view.status.facts.length > 0 || view.status.summary !== '';

  const notices = (
    <p aria-live="polite" className="sr-only">
      {saving ? 'Saving…' : testing ? 'Testing the connection…' : disconnecting ? 'Disconnecting…' : (saved ?? status)}
    </p>
  );

  const testButton = (
    <Button variant="outline" size="sm" disabled={testReason !== null || running} onClick={() => void test()}>
      {testing ? 'Testing…' : 'Test connection'}
    </Button>
  );
  const disconnectButton = (
    <Button
      variant="outline"
      size="sm"
      disabled={removeReason !== null || !view.auth.has_token || running}
      onClick={() => setConfirmDisconnect(true)}
    >
      Disconnect
    </Button>
  );

  return (
    <CardShell
      titleId={`${uid}-title`}
      title={view.title}
      description={view.description}
      standing={standing}
      notices={notices}
      dataAttr={{ 'data-integration': name }}
      open={open}
      onOpenChange={(next) => onOpenChange(name, next)}
      lockedReason={lockedReason}
    >
      <div className="space-y-2 border-t px-5 py-4">
        <h4 className="text-sm font-medium">{isAccount ? 'Connection' : 'Account'}</h4>
        {accountReadout ? <StatusFacts summary={view.status.summary} facts={view.status.facts} /> : null}
        {view.status.checked_at !== null ? (
          <p className="text-xs text-muted-foreground">
            Last checked <CheckedAt iso={view.status.checked_at} />.
          </p>
        ) : null}
        {isAccount && staleToken ? (
          <div className={BAD} role="status">
            <CircleAlert className="size-4 shrink-0" aria-hidden="true" />
            <span>The account address changed since the token was stored. Enter a new token to reconnect.</span>
          </div>
        ) : null}
        <p className="flex items-start gap-2 text-xs text-muted-foreground">
          <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
          <span>
            {isAccount
              ? 'The token and these settings belong to you and apply to every project on this machine.'
              : 'The account is connected once, in the Integrations tab, and shared by every project.'}
          </span>
        </p>
        {!isAccount && (!view.connected || staleToken) ? (
          <div className={BAD} role="status">
            <CircleAlert className="size-4 shrink-0" aria-hidden="true" />
            <span className="flex-1">
              {view.title} is not connected{staleToken ? ' (its token needs reconnecting)' : ''}. Connect it in the Integrations tab first.
            </span>
            {onConnectAccount !== undefined ? (
              <Button variant="outline" size="sm" onClick={onConnectAccount}>
                Open Integrations
              </Button>
            ) : null}
          </div>
        ) : null}
        {isAccount && shownResult !== null ? (
          <div role="status" className={shownResult.ok ? GOOD : BAD}>
            {shownResult.ok ? <CheckCircle2 className="size-4 shrink-0" aria-hidden="true" /> : <CircleAlert className="size-4 shrink-0" aria-hidden="true" />}
            {shownResult.summary}
          </div>
        ) : null}
        {lastTestRun !== null && !lastTestRun.ok ? <Problem problem={lastTestRun} /> : null}
        {lastDisconnect !== null && !lastDisconnect.ok ? <Problem problem={lastDisconnect} /> : null}
        {isAccount && testGate.withheld ? (
          <p className="text-xs text-muted-foreground">Testing is unavailable right now: {testGate.reason}.</p>
        ) : null}
      </div>

      <div className="border-t">
        <div className="px-5 pt-4">
          <h4 className="text-sm font-medium">{isAccount ? 'Account settings' : 'Project settings'}</h4>
          {!isAccount ? (
            <p className="flex items-start gap-2 pt-1 text-xs text-muted-foreground">
              <GitBranch className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
              <span>These settings are committed to the repository and apply to everyone on the project.</span>
            </p>
          ) : null}
          {projectUnbound ? <p className="pt-1 text-xs text-muted-foreground">This project is not bound, so it has no project settings to edit.</p> : null}
          {!isAccount && view.project_problem !== null ? (
            <div className={`${BAD} mt-2`} role="status">
              <CircleAlert className="size-4 shrink-0" aria-hidden="true" />
              <span>The committed settings file could not be read, so it is treated as empty: {view.project_problem}</span>
            </div>
          ) : null}
        </div>
        <fieldset disabled={running} aria-busy={saving} className="min-w-0 divide-y px-5">
          <legend className="sr-only">
            {view.title} {isAccount ? 'account' : 'project'} settings
          </legend>
          {isAccount ? (
            <TokenInput
              id={`${uid}-token`}
              auth={view.auth}
              value={token}
              replacing={replacing}
              disabled={running}
              onChange={setToken}
              onReplace={() => setReplacing(true)}
              onCancelReplace={() => {
                setToken('');
                setReplacing(false);
              }}
              onRemove={() => setConfirmDisconnect(true)}
              removeDisabledReason={removeReason}
            />
          ) : null}
          {states.map((state) => (
            <FieldRow
              key={state.field.key}
              idPrefix={`${uid}-f`}
              state={state}
              disabled={running || projectUnbound}
              detected={isAccount ? undefined : view.detected[state.field.key]}
              loadOptions={isAccount ? undefined : (kind) => window.devteam.integrationResources(name, kind, projectId)}
              loadDisabledReason={view.connected ? null : 'Connect the account first.'}
              onDraft={(value) => {
                setSaved(null);
                setDrafts((previous) => ({ ...previous, [state.field.key]: value }));
              }}
              onUndo={() => setDrafts((previous) => Object.fromEntries(Object.entries(previous).filter(([key]) => key !== state.field.key)))}
            />
          ))}
        </fieldset>
        <div className="space-y-2 px-5 pb-2">
          {saved !== null ? (
            <div role="status" className={GOOD}>
              <CheckCircle2 className="size-4 shrink-0" aria-hidden="true" />
              {saved}
            </div>
          ) : null}
          {warning !== null ? (
            <div role="alert" className={BAD}>
              <CircleAlert className="size-4 shrink-0" aria-hidden="true" />
              {warning}
            </div>
          ) : null}
          {lastSave !== null && !lastSave.ok ? <Problem problem={lastSave} /> : null}
          {partial !== null ? (
            <div className="space-y-2">
              <p className="text-sm">
                <span className="font-medium">{partial.key}</span> and anything after it are still unsaved.
              </p>
              <Problem problem={partial.problem} />
            </div>
          ) : null}
        </div>
        <SaveBar
          inline
          shortcut={false}
          label={`${view.title} unsaved changes`}
          dirtyCount={dirtyCount}
          invalid={invalid}
          status={status}
          saving={saving}
          canSave={canSave}
          withheld={saveGate.withheld ? saveGate.reason : null}
          onDiscard={() => {
            setDrafts({});
            setToken('');
            setReplacing(false);
            setPartial(null);
          }}
          onSave={() => void save()}
        />
      </div>

      {isAccount ? (
        <div className="flex flex-wrap items-center gap-2 border-t px-5 py-3">
          {testReason !== null ? (
            <Hint content={testReason}>
              <span className="inline-flex">{testButton}</span>
            </Hint>
          ) : (
            testButton
          )}
          {removeReason !== null && view.auth.has_token ? (
            <Hint content={removeReason}>
              <span className="inline-flex">{disconnectButton}</span>
            </Hint>
          ) : (
            disconnectButton
          )}
        </div>
      ) : null}

      <Dialog open={confirmDisconnect} onOpenChange={setConfirmDisconnect}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disconnect {view.title}?</DialogTitle>
            <DialogDescription>
              The stored token is deleted from this machine. Your account and project settings are kept, so connecting again only needs a new token.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDisconnect(false)}>
              Keep connected
            </Button>
            <Button variant="destructive" onClick={() => void disconnect()}>
              Disconnect
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </CardShell>
  );
}
