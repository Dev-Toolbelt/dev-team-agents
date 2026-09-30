import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, GitBranch, Info } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Hint } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type {
  EnvironmentReport,
  PluginConfigUpdateReport,
  PluginView,
  ProjectRecord,
} from '../../shared/api.js';
import { Problem } from '../Problem.js';
import { SaveBar } from '../SaveBar.js';
import { useAction } from '../useOperation.js';
import { PLUGIN_COMMANDS, isAnyWithheld, type Withheld } from '../writeActionGating.js';
import { ActionRow } from './ActionRow.js';
import { ConfigField } from './ConfigField.js';
import { draftBatch, fieldDraftState, proposalToDrafts, type Drafts } from './drafts.js';

type Standing = { readonly label: string; readonly variant: 'default' | 'secondary' | 'destructive' | 'outline'; readonly className?: string };

/** The one badge a card leads with. Missing requirements outrank everything: nothing else can be acted on. */
export function standingOf(plugin: PluginView): Standing {
  if (!plugin.ready) return { label: 'Missing requirements', variant: 'destructive' };
  if (!plugin.enabled) return { label: 'Disabled', variant: 'secondary' };
  if (!plugin.configured) {
    return { label: 'Needs setup', variant: 'outline', className: 'border-amber-500/60 text-amber-800 dark:text-amber-300' };
  }
  return { label: 'Enabled', variant: 'outline', className: 'border-green-600 text-green-800 dark:text-green-300' };
}

const NOT_CHECKED: Withheld = { withheld: true, reason: 'the app has not finished checking its own preconditions' };

function gateFor(environment: EnvironmentReport | null, commands: readonly string[]): Withheld {
  return environment === null ? NOT_CHECKED : isAnyWithheld(environment.withheld, commands);
}

/**
 * One plugin, drawn from its `PluginView` alone: standing, requirements, the enable switch,
 * a config form from `config_fields`, the status facts, and a button per action. Nothing in
 * here knows a plugin by name.
 *
 * Config edits are staged in `drafts` and written only by this card's Save, in one batch.
 * An `output: "config"` action fills the same drafts — it proposes, a person saves.
 */
export function PluginCard({
  projectId,
  plugin,
  environment,
  refreshing,
  reloadFailed,
  listVersion,
  onChanged,
  onDirtyChange,
  onRunningChange,
}: {
  projectId: ProjectRecord['project_id'];
  plugin: PluginView;
  environment: EnvironmentReport | null;
  /** The list is being re-read; see the reload effect below. */
  refreshing: boolean;
  /** The last re-read of the list failed; the card is still drawn from the previous list. */
  reloadFailed: boolean;
  /** Bumped each time a re-read of the list finishes, whether it succeeded or not. */
  listVersion: number;
  /** A write landed (or an action ran) — re-read the list. */
  onChanged: () => void;
  onDirtyChange: (name: string, count: number) => void;
  onRunningChange: (name: string, count: number) => void;
}) {
  const uid = useId();
  const titleId = `${uid}-title`;
  const [drafts, setDrafts] = useState<Drafts>({});
  const [awaiting, setAwaiting] = useState<{ written: ReadonlySet<string>; snapshot: Drafts; before: PluginView; version: number } | null>(null);
  const [saved, setSaved] = useState<PluginConfigUpdateReport | null>(null);
  const [toggleNote, setToggleNote] = useState<string | null>(null);
  // The write landed but the list that would confirm it did not arrive: the drafts stay, as
  // the values that were written, until a list that actually arrives replaces them.
  const [unconfirmed, setUnconfirmed] = useState(false);
  const runningActions = useRef(new Set<string>());
  const actionRunning = useCallback(
    (actionId: string, running: boolean) => {
      if (running) runningActions.current.add(actionId);
      else runningActions.current.delete(actionId);
      onRunningChange(plugin.name, runningActions.current.size);
    },
    [plugin.name, onRunningChange],
  );
  useEffect(() => () => onRunningChange(plugin.name, 0), [plugin.name, onRunningChange]);

  const toggler = useAction((enabled: boolean) => window.devteam.setPluginEnabled(projectId, plugin.name, enabled));
  const saver = useAction((changes: Parameters<typeof window.devteam.updatePluginConfig>[2]) =>
    window.devteam.updatePluginConfig(projectId, plugin.name, changes),
  );

  const batch = useMemo(() => draftBatch(plugin.config_fields, plugin.config, drafts), [plugin.config_fields, plugin.config, drafts]);
  // Values already written are not "unsaved", even while the form still shows them as drafts;
  // an edit made since (a different draft) still is.
  const unsavedKeys =
    awaiting === null
      ? batch.dirtyKeys
      : batch.dirtyKeys.filter((key) => !(awaiting.written.has(key) && drafts[key] === awaiting.snapshot[key]));
  const unsavedCount = unsavedKeys.length;

  useEffect(() => {
    onDirtyChange(plugin.name, unsavedCount);
    return () => onDirtyChange(plugin.name, 0);
  }, [plugin.name, unsavedCount, onDirtyChange]);

  // A saved draft is dropped only once the reload has brought the value back from the CLI, so
  // the form never flashes the old value between the save and the reload. A reload that
  // finished without changing anything (it failed) also ends the wait: the form must not
  // stay disabled behind a list that will not update — but the drafts are then kept, not
  // dropped, so the form shows what was written instead of silently reverting to the old
  // values; the screen's Problem offers Try again, and a list that arrives ends the wait.
  useEffect(() => {
    if (awaiting === null) return;
    if (refreshing) {
      setUnconfirmed(false);
      return;
    }
    const answered = listVersion > awaiting.version;
    const arrived = plugin !== awaiting.before || (answered && !reloadFailed);
    if (arrived) {
      setDrafts((previous) =>
        Object.fromEntries(Object.entries(previous).filter(([key, value]) => !(awaiting.written.has(key) && value === awaiting.snapshot[key]))),
      );
      setUnconfirmed(false);
      setAwaiting(null);
    } else if (answered && reloadFailed) {
      setUnconfirmed(true);
    }
  }, [awaiting, plugin, refreshing, reloadFailed, listVersion]);

  const toggleGate = gateFor(environment, [plugin.enabled ? PLUGIN_COMMANDS.disable : PLUGIN_COMMANDS.enable]);
  const saveGate = gateFor(environment, [PLUGIN_COMMANDS.configSet, PLUGIN_COMMANDS.configUnset]);
  const runGate = gateFor(environment, [PLUGIN_COMMANDS.run]);

  const saving = saver.state.phase === 'pending' || (awaiting !== null && !unconfirmed);
  const busy = saving;
  const toggling = toggler.state.phase === 'pending';
  const canSave = unsavedCount > 0 && batch.invalid.length === 0 && !saveGate.withheld && !busy;

  // Turning a plugin on needs its requirements; turning it off never does.
  const enableBlocked = !plugin.enabled && !plugin.ready;
  const switchReason = toggleGate.withheld
    ? `Withheld: ${toggleGate.reason}`
    : enableBlocked
      ? 'Install the missing requirements before enabling this plugin.'
      : null;

  const standing = standingOf(plugin);
  const missing = plugin.requirements.filter((requirement) => !requirement.found);
  const lastSave = saver.state.phase === 'done' ? saver.state.result : null;
  const lastToggle = toggler.state.phase === 'done' ? toggler.state.result : null;

  async function toggle(next: boolean) {
    setToggleNote(null);
    setSaved(null);
    const result = await toggler.run(next);
    if (!result.ok) return;
    setToggleNote(
      next
        ? result.data.seeded
          ? `${plugin.title} is on for this project. Its settings were filled in from what the plugin detected; review them below.`
          : `${plugin.title} is on for this project.`
        : `${plugin.title} is off for this project. Its settings are kept.`,
    );
    onChanged();
  }

  async function save() {
    if (!canSave) return;
    const before = plugin;
    const result = await saver.run(batch.changes);
    if (!result.ok) return;
    setSaved(result.data.failed === null ? result.data : null);
    setAwaiting({ written: new Set(result.data.applied.map((change) => change.key)), snapshot: drafts, before, version: listVersion });
    onChanged();
  }

  function fillFromProposal(output: Readonly<Record<string, unknown>>): string {
    const proposal = proposalToDrafts(plugin.config_fields, plugin.config, output);
    setSaved(null);
    if (proposal.filled.length > 0) setDrafts((previous) => ({ ...previous, ...proposal.drafts }));
    const skipped =
      proposal.skipped.length > 0 ? ` Ignored ${proposal.skipped.length} value${proposal.skipped.length === 1 ? '' : 's'} the form cannot hold (${proposal.skipped.join(', ')}).` : '';
    return proposal.filled.length > 0
      ? `Proposed values filled in — review and save. Nothing has been written yet.${skipped}`
      : `The proposal matches the current settings; there is nothing new to fill in.${skipped}`;
  }

  const status =
    batch.invalid.length > 0
      ? `${batch.invalid.length} value${batch.invalid.length === 1 ? ' needs' : 's need'} fixing before you can save`
      : unsavedCount > 0
        ? `${unsavedCount} unsaved change${unsavedCount === 1 ? '' : 's'}`
        : '';

  function actionReason(action: PluginView['actions'][number]): string | null {
    if (runGate.withheld) return `Withheld: ${runGate.reason}`;
    if (!plugin.ready) return 'This plugin is missing a requirement; install it first.';
    if (action.requires_enabled && !plugin.enabled) return 'Enable this plugin to run this action.';
    if (busy) return 'Wait for the save to finish.';
    return null;
  }

  const switchNode = (
    <Switch
      id={`${uid}-enabled`}
      checked={plugin.enabled}
      disabled={switchReason !== null || toggling}
      aria-describedby={`${uid}-commit`}
      onCheckedChange={(next) => void toggle(next)}
    />
  );

  return (
    <section aria-labelledby={titleId} className="rounded-xl border bg-card text-card-foreground shadow-sm" data-plugin={plugin.name}>
      <header className="space-y-3 border-b px-5 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 id={titleId} className="font-semibold">
                {plugin.title}
              </h3>
              <Badge variant={standing.variant} className={cn('font-normal', standing.className)}>
                {standing.label}
              </Badge>
              {plugin.source === 'legacy' ? (
                <Badge variant="outline" className="font-normal text-muted-foreground">
                  legacy config
                </Badge>
              ) : null}
            </div>
            <p className="text-sm text-muted-foreground">{plugin.description}</p>
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor={`${uid}-enabled`} className="text-sm font-medium">
              Enable<span className="sr-only"> {plugin.title}</span>
            </label>
            {switchReason !== null ? (
              <Hint content={switchReason}>
                <span className="inline-flex">{switchNode}</span>
              </Hint>
            ) : (
              switchNode
            )}
          </div>
        </div>
        <p id={`${uid}-commit`} className="flex items-start gap-2 text-xs text-muted-foreground">
          <GitBranch className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
          <span>
            This setting is committed to the repository and applies to everyone on the project. Stored in{' '}
            <code className="font-mono">{plugin.settings_file}</code>.
          </span>
        </p>
        {plugin.source === 'legacy' ? (
          <p className="flex items-start gap-2 text-xs text-muted-foreground">
            <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
            <span>
              This plugin still reads a legacy config file. It moves to <code className="font-mono">{plugin.settings_file}</code>{' '}
              the next time the project is bound or synced.
            </span>
          </p>
        ) : null}
      </header>

      <div className="space-y-4 px-5 py-4">
        <p aria-live="polite" className="sr-only">
          {toggling ? 'Updating…' : saving ? 'Saving…' : unconfirmed ? 'Saved; the list could not be reloaded.' : (toggleNote ?? status)}
        </p>

        {missing.length > 0 ? (
          <Alert variant="destructive">
            <AlertTriangle />
            <AlertTitle>Missing requirements</AlertTitle>
            <AlertDescription>
              <ul className="space-y-1">
                {missing.map((requirement) => (
                  <li key={requirement.binary}>
                    <code className="font-mono">{requirement.binary}</code> was not found on this machine.
                    {requirement.install_hint !== null ? (
                      <>
                        {' '}
                        Install it with <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">{requirement.install_hint}</code>.
                      </>
                    ) : null}
                  </li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        ) : null}

        {toggleGate.withheld ? (
          <p className="text-xs text-muted-foreground">Changing this plugin is unavailable right now: {toggleGate.reason}.</p>
        ) : null}
        {lastToggle !== null && !lastToggle.ok ? <Problem problem={lastToggle} /> : null}
        {toggleNote !== null ? (
          <div
            role="status"
            className="flex items-center gap-2 rounded-md border border-green-600 bg-green-50 px-3 py-2 text-sm text-green-900 dark:border-green-500 dark:bg-green-950 dark:text-green-200"
          >
            <CheckCircle2 className="size-4 shrink-0" aria-hidden="true" />
            {toggleNote}
          </div>
        ) : null}

        {plugin.status !== null ? (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Status</h4>
            <p className="text-sm text-muted-foreground">{plugin.status.summary}</p>
            {plugin.status.facts.length > 0 ? (
              <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-4 gap-y-1 text-sm">
                {plugin.status.facts.map((fact) => (
                  <div key={fact.label} className="contents">
                    <dt className="text-muted-foreground">{fact.label}</dt>
                    <dd className="min-w-0 break-words font-mono text-xs leading-5">{fact.value}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </div>
        ) : null}
      </div>

      {plugin.config_fields.length > 0 ? (
        <div className="border-t">
          <div className="px-5 pt-4">
            <h4 className="text-sm font-medium">Settings</h4>
            {!plugin.configured ? (
              <p className="text-xs text-muted-foreground">Fill in the required settings to finish setting this plugin up.</p>
            ) : null}
          </div>
          <fieldset disabled={busy} aria-busy={saving} className="min-w-0 divide-y px-5">
            <legend className="sr-only">{plugin.title} settings</legend>
            {plugin.config_fields.map((field) => (
              <ConfigField
                key={field.key}
                idPrefix={`${uid}-cfg`}
                field={field}
                state={fieldDraftState(field, plugin.config, drafts)}
                disabled={busy}
                onDraft={(value) => {
                  setSaved(null);
                  setDrafts((previous) => ({ ...previous, [field.key]: value }));
                }}
                onUndo={() => setDrafts((previous) => Object.fromEntries(Object.entries(previous).filter(([key]) => key !== field.key)))}
              />
            ))}
          </fieldset>
          <div className="space-y-2 px-5 pb-2">
            {plugin.unknown_config.length > 0 ? (
              <p className="text-xs text-muted-foreground">
                Kept but no longer declared by this plugin: <span className="font-mono">{plugin.unknown_config.join(', ')}</span>.
              </p>
            ) : null}
            {saved !== null ? (
              <div
                role="status"
                className="flex items-center gap-2 rounded-md border border-green-600 bg-green-50 px-3 py-2 text-sm text-green-900 dark:border-green-500 dark:bg-green-950 dark:text-green-200"
              >
                <CheckCircle2 className="size-4 shrink-0" aria-hidden="true" />
                Saved {saved.applied.length} change{saved.applied.length === 1 ? '' : 's'} to this project. It is committed with the
                project, so commit the file to share it.
              </div>
            ) : null}
            {unconfirmed ? (
              <p role="status" className="text-sm">
                Saved. The updated settings could not be read back, so the form shows what you saved; use Try again above to reload.
              </p>
            ) : null}
            {lastSave !== null && !lastSave.ok ? <Problem problem={lastSave} /> : null}
            {lastSave !== null && lastSave.ok && lastSave.data.failed !== null ? (
              <div className="space-y-2">
                <p className="text-sm">
                  {lastSave.data.applied.length === 0
                    ? 'Nothing was saved.'
                    : `${lastSave.data.applied.length} change${lastSave.data.applied.length === 1 ? ' was' : 's were'} saved before one failed.`}{' '}
                  <span className="font-medium">{lastSave.data.failed.change.key}</span> and anything after it are still unsaved.
                </p>
                <Problem problem={lastSave.data.failed.problem} />
              </div>
            ) : null}
          </div>
          <SaveBar
            inline
            shortcut={false}
            label={`${plugin.title} unsaved changes`}
            dirtyCount={unsavedCount}
            invalid={batch.invalid.length}
            status={status}
            saving={saving}
            canSave={canSave}
            withheld={saveGate.withheld ? saveGate.reason : null}
            onDiscard={() => {
              setDrafts({});
              saver.reset();
            }}
            onSave={() => void save()}
          />
        </div>
      ) : null}

      {plugin.actions.length > 0 ? (
        <div className="border-t px-5 py-2">
          <h4 className="pt-2 text-sm font-medium">Actions</h4>
          <div className="divide-y">
            {plugin.actions.map((action) => (
              <ActionRow
                key={action.id}
                projectId={projectId}
                pluginName={plugin.name}
                action={action}
                disabledReason={actionReason(action)}
                onProposal={fillFromProposal}
                onRan={onChanged}
                onRunningChange={actionRunning}
              />
            ))}
          </div>
        </div>
      ) : null}

      {plugin.hooks.length > 0 ? (
        <p className="border-t px-5 py-3 text-xs text-muted-foreground">
          While enabled, this plugin also runs at: {plugin.hooks.join(', ')}.
        </p>
      ) : null}
    </section>
  );
}
