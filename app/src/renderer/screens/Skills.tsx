import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Hint } from '@/components/ui/tooltip';
import { Empty, Loading, Problem } from '../Problem.js';
import { useAction, useOperation } from '../useOperation.js';
import { Notice, WriteButton } from '../WriteButton.js';
import type {
  EnvironmentReport,
  SkillInstallReport,
  SkillProvider,
  SkillProviderFilter,
  SkillRecord,
  SkillRoot,
} from '../../shared/api.js';

const FILTERS: readonly { readonly value: SkillProviderFilter; readonly label: string }[] = [
  { value: 'all', label: 'All providers' },
  { value: 'claude', label: 'Claude' },
  { value: 'codex', label: 'Codex' },
  { value: 'opencode', label: 'opencode' },
];

const PROVIDER_CHOICES: readonly { readonly value: SkillProvider; readonly label: string }[] = [
  { value: 'claude', label: 'Claude' },
  { value: 'codex', label: 'Codex' },
  { value: 'opencode', label: 'opencode' },
];

/** Fixed locale, so the order is the same on every machine and in CI. */
const collator = new Intl.Collator('en');

const rowKey = (skill: SkillRecord) => `${skill.root}:${skill.name}`;

/**
 * The global (user-level) skills of Claude Code, Codex and opencode — `devteam skills`.
 *
 * Reads through `skills list` / `skills show`; the two writes, install and remove, are
 * `compat.MUTATING` and are withheld like every other write action. Nothing here holds or
 * sends a path: the install picker opens in the main process, and a removal names a skill
 * by the name and root id of a record the CLI just listed.
 */
export function Skills({ environment }: { environment: EnvironmentReport | null }) {
  const [provider, setProvider] = useState<SkillProviderFilter>('all');
  const [selected, setSelected] = useState<SkillRecord | null>(null);
  const [removing, setRemoving] = useState<SkillRecord | null>(null);
  const [installing, setInstalling] = useState(false);
  const { state, refreshing, reload } = useOperation(() => window.devteam.listSkills(provider), [provider]);

  return (
    <section aria-labelledby="skills-heading" className="space-y-4">
      <header className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <h2 id="skills-heading" className="text-base font-semibold">
            Global Skills
          </h2>
          <p className="text-sm text-muted-foreground">
            The skills installed for your user account in each provider&apos;s own directory, not in a project.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={provider}
            onChange={(event) => setProvider(event.target.value as SkillProviderFilter)}
            aria-label="Filter skills by provider"
            className="h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:bg-input/30"
          >
            {FILTERS.map((each) => (
              <option key={each.value} value={each.value}>
                {each.label}
              </option>
            ))}
          </select>
          <Button variant="outline" size="sm" onClick={reload} disabled={refreshing}>
            Refresh
          </Button>
          <WriteButton
            command="skills install"
            environment={environment}
            size="sm"
            tooltip="Install a skill from a folder or an archive"
            onClick={() => setInstalling(true)}
          >
            Install skill
          </WriteButton>
        </div>
      </header>

      {state.phase === 'loading' ? <Loading what="devteam skills list" /> : null}
      {state.phase === 'done' && !state.result.ok ? <Problem problem={state.result} /> : null}
      {state.phase === 'done' && state.result.ok ? (
        <>
          <Roots roots={state.result.data.roots} />
          <SkillTable
            skills={state.result.data.skills}
            environment={environment}
            onOpen={setSelected}
            onRemove={setRemoving}
          />
        </>
      ) : null}

      {selected !== null ? (
        <DetailsDialog
          key={rowKey(selected)}
          skill={selected}
          onOpenChange={(open) => {
            if (!open) setSelected(null);
          }}
        />
      ) : null}
      {removing !== null ? (
        <RemoveDialog
          key={rowKey(removing)}
          skill={removing}
          onRemoved={reload}
          onOpenChange={(open) => {
            if (!open) setRemoving(null);
          }}
        />
      ) : null}
      {installing ? (
        <InstallDialog
          onInstalled={reload}
          onOpenChange={(open) => {
            if (!open) setInstalling(false);
          }}
        />
      ) : null}
    </section>
  );
}

function Roots({ roots }: { roots: readonly SkillRoot[] }) {
  if (roots.length === 0) return null;
  return (
    <div className="space-y-1">
      <h3 className="text-sm font-semibold">Directories</h3>
      <ul className="space-y-1 text-xs">
        {roots.map((root) => (
          <li key={root.id} className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-muted-foreground">{root.path}</span>
            {root.exists ? null : <Badge variant="secondary">absent</Badge>}
            <span className="text-muted-foreground">read by</span>
            {root.providers.length > 0 ? (
              root.providers.map((provider) => (
                <Badge key={provider} variant="outline">
                  {provider}
                </Badge>
              ))
            ) : (
              <span className="text-muted-foreground">no provider</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function SkillTable({
  skills,
  environment,
  onOpen,
  onRemove,
}: {
  skills: readonly SkillRecord[];
  environment: EnvironmentReport | null;
  onOpen: (skill: SkillRecord) => void;
  onRemove: (skill: SkillRecord) => void;
}) {
  if (skills.length === 0) return <Empty>No global skills for this provider.</Empty>;
  const sorted = [...skills].sort((a, b) => collator.compare(a.name, b.name) || collator.compare(a.root, b.root));

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead scope="col">Name</TableHead>
          <TableHead scope="col">Description</TableHead>
          <TableHead scope="col">Root</TableHead>
          <TableHead scope="col">Providers</TableHead>
          <TableHead scope="col">Flags</TableHead>
          <TableHead scope="col">
            <span className="sr-only">Actions</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sorted.map((skill) => (
          <TableRow key={rowKey(skill)} className="cursor-pointer" onClick={() => onOpen(skill)}>
            <TableCell>
              <button
                type="button"
                className="font-mono text-xs text-primary underline-offset-4 hover:underline focus-visible:underline"
                onClick={(event) => {
                  event.stopPropagation();
                  onOpen(skill);
                }}
              >
                {skill.name}
              </button>
            </TableCell>
            <TableCell className="max-w-md truncate text-muted-foreground" title={skill.description ?? undefined}>
              {skill.description ?? '—'}
            </TableCell>
            <TableCell className="font-mono text-xs">{skill.root}</TableCell>
            <TableCell>
              <div className="flex flex-wrap gap-1">
                {skill.providers.map((each) => (
                  <Badge key={each} variant="outline">
                    {each}
                  </Badge>
                ))}
              </div>
            </TableCell>
            <TableCell>
              <div className="flex flex-wrap gap-1">
                {skill.is_symlink ? (
                  <Hint content={skill.link_target !== null ? `Symlink to ${skill.link_target}` : 'A symlink'}>
                    <Badge variant="secondary">link</Badge>
                  </Hint>
                ) : null}
                {skill.managed ? (
                  <Hint content="Managed by dev-team-agents; it is not removed or replaced from here.">
                    <Badge variant="secondary">managed</Badge>
                  </Hint>
                ) : null}
                {skill.status === 'malformed' ? (
                  <Hint content={skill.error ?? 'The CLI could not read this skill and gave no reason.'}>
                    <Badge variant="destructive">malformed</Badge>
                  </Hint>
                ) : null}
              </div>
            </TableCell>
            <TableCell className="text-right">
              {/* No remove for a managed skill: the CLI refuses it at exit 4, so offering the
                  button would only be a way to fail. */}
              {skill.managed ? null : (
                <WriteButton
                  command="skills remove"
                  environment={environment}
                  variant="outline"
                  size="sm"
                  aria-label={`Remove ${skill.name} from ${skill.root}`}
                  onClick={(event) => {
                    event.stopPropagation();
                    onRemove(skill);
                  }}
                >
                  Remove
                </WriteButton>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

// ── details ───────────────────────────────────────────────────────────────────

function DetailsDialog({
  skill,
  onOpenChange,
}: {
  skill: SkillRecord;
  onOpenChange: (open: boolean) => void;
}) {
  const { state } = useOperation(() => window.devteam.showSkill(skill.name, skill.root), [skill.name, skill.root]);

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle className="font-mono">{skill.name}</DialogTitle>
          <DialogDescription>{skill.description ?? 'This skill has no description.'}</DialogDescription>
        </DialogHeader>

        {state.phase === 'loading' ? <Loading what="devteam skills show" /> : null}
        {state.phase === 'done' && !state.result.ok ? <Problem problem={state.result} /> : null}
        {state.phase === 'done' && state.result.ok ? (
          <div className="space-y-4 text-sm">
            <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1">
              <dt className="text-muted-foreground">Root</dt>
              <dd className="font-mono text-xs">{state.result.data.root}</dd>
              <dt className="text-muted-foreground">Path</dt>
              <dd className="break-all font-mono text-xs">{state.result.data.path}</dd>
              <dt className="text-muted-foreground">Providers</dt>
              <dd>{state.result.data.providers.join(', ') || '—'}</dd>
              {state.result.data.is_symlink ? (
                <>
                  <dt className="text-muted-foreground">Symlink to</dt>
                  <dd className="break-all font-mono text-xs">{state.result.data.link_target ?? 'unknown'}</dd>
                </>
              ) : null}
              <dt className="text-muted-foreground">Managed</dt>
              <dd>{state.result.data.managed ? 'yes, by dev-team-agents' : 'no'}</dd>
              {state.result.data.status === 'malformed' ? (
                <>
                  <dt className="text-muted-foreground">Problem</dt>
                  <dd className="text-destructive">{state.result.data.error ?? 'unreadable'}</dd>
                </>
              ) : null}
            </dl>

            <div className="space-y-1">
              <h3 className="text-sm font-semibold">Files</h3>
              {state.result.data.files.length === 0 ? (
                <p className="text-muted-foreground">No files listed.</p>
              ) : (
                <ul className="font-mono text-xs">
                  {state.result.data.files.map((file) => (
                    <li key={file}>{file}</li>
                  ))}
                </ul>
              )}
              {state.result.data.files_truncated ? (
                <p className="text-xs text-muted-foreground">The list was cut short by the CLI.</p>
              ) : null}
            </div>

            <div className="space-y-1">
              <h3 className="text-sm font-semibold">SKILL.md</h3>
              {/* Text, never markup: a skill's body is another party's content. */}
              <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-md border bg-muted/40 p-3 font-mono text-xs">
                {state.result.data.body ?? '(no body)'}
              </pre>
            </div>
          </div>
        ) : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── remove ────────────────────────────────────────────────────────────────────

function RemoveDialog({
  skill,
  onRemoved,
  onOpenChange,
}: {
  skill: SkillRecord;
  onRemoved: () => void;
  onOpenChange: (open: boolean) => void;
}) {
  const remove = useAction(() => window.devteam.removeSkill({ name: skill.name, root: skill.root }));
  const done = remove.state.phase === 'done' ? remove.state.result : null;
  const removed = done !== null && done.ok ? done.data : null;

  async function confirm() {
    const result = await remove.run();
    if (result.ok) onRemoved();
  }

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Remove {skill.name}?</DialogTitle>
          <DialogDescription>
            {skill.is_symlink ? (
              <>
                <span className="font-mono">{skill.path}</span> is a symlink. Only the link is removed; the folder it
                points to is left untouched.
              </>
            ) : (
              <>
                <span className="font-mono">{skill.path}</span> is a folder. It is moved to the store&apos;s
                quarantine, not deleted, so it can be put back by hand.
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        {done !== null && !done.ok ? <Problem problem={done} /> : null}
        {removed !== null ? (
          <p className="text-sm" role="status">
            {removed.action === 'quarantined' ? (
              <>
                Moved to quarantine: <span className="break-all font-mono text-xs">{removed.quarantined_to ?? '(no path reported)'}</span>
              </>
            ) : (
              <>
                The symlink was removed. Nothing else was touched. It pointed at{' '}
                <span className="break-all font-mono text-xs">{removed.link_target ?? '(no target reported)'}</span>
                {' '}— recreate it there to undo.
              </>
            )}
          </p>
        ) : null}
        {done !== null ? <Notice result={done} /> : null}

        <DialogFooter>
          {removed !== null ? (
            <Button onClick={() => onOpenChange(false)}>Done</Button>
          ) : (
            <>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button variant="destructive" disabled={remove.state.phase === 'pending'} onClick={() => void confirm()}>
                {remove.state.phase === 'pending' ? 'Removing…' : 'Remove'}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── install ───────────────────────────────────────────────────────────────────

function InstallDialog({
  onInstalled,
  onOpenChange,
}: {
  onInstalled: () => void;
  onOpenChange: (open: boolean) => void;
}) {
  const [providers, setProviders] = useState<readonly SkillProvider[]>(['claude']);
  const [replace, setReplace] = useState(false);
  const [link, setLink] = useState(false);
  const install = useAction((request: Parameters<typeof window.devteam.installSkill>[0]) =>
    window.devteam.installSkill(request),
  );
  const pending = install.state.phase === 'pending';
  const answer = install.state.phase === 'done' && install.state.result.picked ? install.state.result : null;
  const installed: SkillInstallReport | null = answer !== null && answer.result.ok ? answer.result.data : null;
  // Only an "already exists" conflict can be resolved by replacing; a managed skill cannot.
  const conflict =
    answer !== null && !answer.result.ok && answer.result.kind === 'conflict' && answer.result.reason === 'exists';

  async function start(source: 'pick' | 'previous', replaceExisting: boolean) {
    const result = await install.run({ source, providers, replace: replaceExisting, link });
    if (result.picked && result.result.ok) onInstalled();
  }

  function toggleProvider(provider: SkillProvider, on: boolean) {
    setProviders((current) => (on ? [...current, provider] : current.filter((each) => each !== provider)));
  }

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Install a skill</DialogTitle>
          <DialogDescription>
            Choose where it goes, then select the skill&apos;s folder, its{' '}
            <span className="font-mono">SKILL.md</span>, or a <span className="font-mono">.zip</span> /{' '}
            <span className="font-mono">.skill</span> archive. The file picker opens outside this window.
          </DialogDescription>
        </DialogHeader>

        <fieldset className="space-y-2" disabled={pending}>
          <legend className="text-sm font-medium">Install for</legend>
          {PROVIDER_CHOICES.map((choice) => (
            <div key={choice.value} className="flex items-center gap-2">
              <Checkbox
                id={`skill-provider-${choice.value}`}
                checked={providers.includes(choice.value)}
                onCheckedChange={(checked) => toggleProvider(choice.value, checked === true)}
              />
              <Label htmlFor={`skill-provider-${choice.value}`}>{choice.label}</Label>
            </div>
          ))}
        </fieldset>

        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <Checkbox
              id="skill-replace"
              checked={replace}
              disabled={pending}
              onCheckedChange={(checked) => setReplace(checked === true)}
            />
            <Label htmlFor="skill-replace" className="leading-snug">
              Replace an existing skill of the same name (the old one is moved to quarantine)
            </Label>
          </div>
          <div className="flex items-start gap-2">
            <Checkbox
              id="skill-link"
              checked={link}
              disabled={pending}
              onCheckedChange={(checked) => setLink(checked === true)}
            />
            <Label htmlFor="skill-link" className="leading-snug">
              Link instead of copy (folders only, not archives; edits to the source show up in the installed skill)
            </Label>
          </div>
        </div>

        {answer !== null && !answer.result.ok ? (
          <div className="space-y-2">
            <Problem problem={answer.result} />
            {conflict && !replace ? (
              <Button variant="outline" size="sm" disabled={pending} onClick={() => void start('previous', true)}>
                Replace the existing skill and retry
              </Button>
            ) : null}
          </div>
        ) : null}
        {answer !== null && answer.source !== '' ? (
          <p className="break-all text-xs text-muted-foreground">
            Source: <span className="font-mono">{answer.source}</span>
          </p>
        ) : null}
        {installed !== null ? (
          <div className="space-y-1 text-sm" role="status">
            <p>
              Installed <span className="font-mono">{installed.name}</span>
              {installed.linked ? ' as a link' : ''}:
            </p>
            <ul className="text-xs">
              {installed.installed.map((target) => (
                <li key={target.path} className="break-all">
                  <span className="font-mono">{target.path}</span>
                  {target.replaced && target.quarantined_to !== null ? (
                    <span className="text-muted-foreground">
                      {' '}
                      — the previous copy went to <span className="font-mono">{target.quarantined_to}</span>
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
            {installed.also_present.length > 0 ? (
              <p className="text-xs text-amber-600 dark:text-amber-400">
                A skill with this name also exists in{' '}
                {installed.also_present.map((other) => (
                  <span key={other.path} className="break-all font-mono">
                    {other.path}{' '}
                  </span>
                ))}
                — a provider that reads both will see two copies.
              </p>
            ) : null}
          </div>
        ) : null}
        {answer !== null ? <Notice result={answer.result} /> : null}

        <DialogFooter>
          {installed !== null ? (
            <Button onClick={() => onOpenChange(false)}>Done</Button>
          ) : (
            <>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button disabled={pending || providers.length === 0} onClick={() => void start('pick', replace)}>
                {pending ? 'Installing…' : 'Select file…'}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
