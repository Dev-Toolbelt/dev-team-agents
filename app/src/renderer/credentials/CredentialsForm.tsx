import { Plus, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { CredentialsLocalView } from '../../shared/api.js';
import { ListEditor } from '../plugins/ListEditor.js';
import {
  DATABASE_FIELDS,
  SECRET_KEYS,
  WORK_FEEDBACK_ACTIVE,
  WORK_FEEDBACK_INTERVAL,
  addDatabase,
  editAddedDatabase,
  existingRows,
  isRecord,
  isSecretLeaf,
  isSecretSet,
  listValue,
  pointerOf,
  segmentsOf,
  removeAddedDatabase,
  removeDatabase,
  setSecret,
  setValue,
  switchValue,
  textValue,
  valueAt,
  type DatabaseField,
  type Drafts,
  type DraftReport,
} from './drafts.js';
import { SecretInput } from './SecretInput.js';

const KNOWN_ENVIRONMENTS = ['staging', 'production'] as const;

const CATEGORY_NOTES: Readonly<Record<string, string>> = {
  devops: 'Servers, databases and Docker the agents may reach.',
  app: 'The application URL and login the agents use to check a running app.',
};

const FIELD_LABELS: Readonly<Record<string, string>> = {
  user: 'SSH user',
  host: 'Host',
  privateKeyPath: 'Private key path',
  path: 'Remote path',
  appUrl: 'Application URL',
  username: 'Username',
  password: 'Password',
  type: 'Type',
  port: 'Port',
  database: 'Database name',
};

/**
 * A DOM id for a pointer. Injective: `/` reads as `-` and every other symbol is spelled out, so
 * two different keys (`a-b` and `a/b`) never share an id.
 */
const slug = (pointer: string): string =>
  `cred${pointer.replace(/[^A-Za-z0-9/]/g, (char) => `_${char.charCodeAt(0).toString(16)}_`).replace(/\//g, '-')}`;

const KNOWN_CATEGORIES = ['devops', 'app'];

/** `{secret, set}` is a secret leaf, not a nested group. */
const isGroup = (value: unknown): boolean => isRecord(value) && !isSecretLeaf(value);

/** An object that looks like a category: an `agents` list, or at least one environment-like object inside. */
function looksLikeCategory(value: Readonly<Record<string, unknown>>): boolean {
  return Array.isArray(value['agents']) || Object.values(value).some(isGroup);
}

/** `devops` and `app` always, then any other top-level object that looks like a category. */
export function categoriesOf(data: Readonly<Record<string, unknown>>): string[] {
  const present = Object.keys(data).filter((key) => {
    const value = data[key];
    return isRecord(value) && !KNOWN_CATEGORIES.includes(key) && looksLikeCategory(value);
  });
  return [...KNOWN_CATEGORIES, ...present];
}

/** Environments of a category: staging and production, then any other object it holds. */
export function environmentsOf(category: unknown): string[] {
  const extra = isRecord(category) ? Object.keys(category).filter((key) => isGroup(category[key]) && !KNOWN_ENVIRONMENTS.includes(key as 'staging')) : [];
  return [...KNOWN_ENVIRONMENTS, ...extra];
}

/** An environment is laid out as infrastructure when the file says so; otherwise as an application login. */
export function isInfrastructure(category: string, environment: unknown): boolean {
  if (category === 'devops') return true;
  if (category === 'app') return false;
  return isRecord(environment) && ('ssh' in environment || 'database' in environment || 'docker' in environment);
}

interface Context {
  view: CredentialsLocalView;
  report: DraftReport;
  drafts: Drafts;
  onDrafts: (next: Drafts) => void;
  disabled: boolean;
}

function TextField({
  ctx,
  pointer,
  label,
  placeholder,
  inputMode,
}: {
  ctx: Context;
  pointer: string;
  label: string;
  placeholder?: string;
  inputMode?: 'numeric' | 'url';
}) {
  const id = slug(pointer);
  return (
    <div className="min-w-0 space-y-1.5">
      <Label htmlFor={id} className="text-sm">
        {label}
      </Label>
      <Input
        id={id}
        value={textValue(ctx.view, ctx.drafts, pointer)}
        disabled={ctx.disabled}
        placeholder={placeholder}
        inputMode={inputMode}
        autoComplete="off"
        spellCheck={false}
        className="font-mono"
        onChange={(event) => ctx.onDrafts(setValue(ctx.drafts, pointer, event.target.value))}
      />
    </div>
  );
}

function SecretField({ ctx, pointer, label }: { ctx: Context; pointer: string; label: string }) {
  const saved = valueAt(ctx.view.data, segmentsOf(pointer));
  return (
    <SecretInput
      id={slug(pointer)}
      label={label}
      isSet={isSecretSet(saved)}
      draft={ctx.drafts.secrets[pointer]}
      disabled={ctx.disabled}
      onChange={(draft) => ctx.onDrafts(setSecret(ctx.drafts, pointer, draft))}
    />
  );
}

/** A leaf is a secret by name, or because the file says so. */
function Leaf({ ctx, segments, label }: { ctx: Context; segments: readonly string[]; label?: string }) {
  const pointer = pointerOf(...segments);
  const key = segments[segments.length - 1] as string;
  const text = label ?? FIELD_LABELS[key] ?? key;
  if (SECRET_KEYS.has(key) || isSecretLeaf(valueAt(ctx.view.data, segments))) {
    return <SecretField ctx={ctx} pointer={pointer} label={text} />;
  }
  return <TextField ctx={ctx} pointer={pointer} label={text} {...(key === 'appUrl' ? { inputMode: 'url' as const } : {})} />;
}

function DatabaseRow({
  ctx,
  listPointer,
  index,
  n,
  environment,
}: {
  ctx: Context;
  listPointer: string;
  index: number;
  n: number;
  environment: string;
}) {
  const segments = [...segmentsOf(listPointer), String(index)];
  const saved = valueAt(ctx.view.data, segments);
  const hint = isRecord(saved) ? [saved['type'], saved['host']].filter((part): part is string => typeof part === 'string' && part !== '') : [];
  return (
    <fieldset className="space-y-3 rounded-md border p-3">
      <legend className="px-1 text-sm font-medium">{hint.length > 0 ? `Database ${n} (${hint.join(', ')})` : `Database ${n}`}</legend>
      <div className="grid gap-3 sm:grid-cols-2">
        {DATABASE_FIELDS.map((field) => (
          <Leaf key={field} ctx={ctx} segments={[...segments, field]} />
        ))}
      </div>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        disabled={ctx.disabled}
        onClick={() => ctx.onDrafts(removeDatabase(ctx.drafts, listPointer, index))}
      >
        <Trash2 aria-hidden="true" />
        Remove<span className="sr-only"> database {n} from {environment}</span>
      </Button>
    </fieldset>
  );
}

function AddedDatabaseRow({
  ctx,
  listPointer,
  row,
  n,
  environment,
}: {
  ctx: Context;
  listPointer: string;
  row: { readonly id: number; readonly values: Readonly<Record<DatabaseField, string>> };
  n: number;
  environment: string;
}) {
  return (
    <fieldset className="space-y-3 rounded-md border border-dashed p-3">
      <legend className="px-1 text-sm font-medium">Database {n} (new)</legend>
      <div className="grid gap-3 sm:grid-cols-2">
        {DATABASE_FIELDS.map((field) => {
          const id = `${slug(listPointer)}-new-${row.id}-${field}`;
          const secret = field === 'password';
          return (
            <div key={field} className="min-w-0 space-y-1.5">
              <Label htmlFor={id} className="text-sm">
                {FIELD_LABELS[field] ?? field}
              </Label>
              <Input
                id={id}
                type={secret ? 'password' : 'text'}
                value={row.values[field]}
                disabled={ctx.disabled}
                autoComplete={secret ? 'new-password' : 'off'}
                spellCheck={false}
                className="font-mono"
                onChange={(event) => ctx.onDrafts(editAddedDatabase(ctx.drafts, listPointer, row.id, field, event.target.value))}
              />
            </div>
          );
        })}
      </div>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        disabled={ctx.disabled}
        onClick={() => ctx.onDrafts(removeAddedDatabase(ctx.drafts, listPointer, row.id))}
      >
        <Trash2 aria-hidden="true" />
        Remove<span className="sr-only"> new database {n} from {environment}</span>
      </Button>
    </fieldset>
  );
}

function InfrastructureEnvironment({
  ctx,
  category,
  environment,
}: {
  ctx: Context;
  category: string;
  environment: string;
}) {
  const base = [category, environment];
  const listPointer = pointerOf(...base, 'database');
  const rows = existingRows(ctx.view, ctx.drafts, listPointer);
  const added = ctx.drafts.added[listPointer] ?? [];
  const docker = valueAt(ctx.view.data, [...base, 'docker']);
  const dockerKeys = isRecord(docker) ? Object.keys(docker) : [];
  const savedList = valueAt(ctx.view.data, segmentsOf(listPointer));
  const listProblem =
    ctx.report.problems[listPointer] ??
    (savedList !== undefined && !Array.isArray(savedList)
      ? 'The file keeps something here that is not a list of databases. Fix it in the file before adding one.'
      : undefined);
  return (
    <div className="space-y-5">
      <fieldset className="space-y-3">
        <legend className="text-sm font-medium">SSH</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          {['user', 'host', 'privateKeyPath', 'path'].map((field) => (
            <Leaf key={field} ctx={ctx} segments={[...base, 'ssh', field]} />
          ))}
        </div>
      </fieldset>
      <section aria-label={`Databases in ${environment}`} className="space-y-3">
        <h4 className="text-sm font-medium">Databases</h4>
        {rows.length === 0 && added.length === 0 ? (
          <p className="text-xs italic text-muted-foreground">No databases listed.</p>
        ) : null}
        {rows.map((index, position) => (
          <DatabaseRow key={index} ctx={ctx} listPointer={listPointer} index={index} n={position + 1} environment={environment} />
        ))}
        {added.map((row, position) => (
          <AddedDatabaseRow
            key={row.id}
            ctx={ctx}
            listPointer={listPointer}
            row={row}
            n={rows.length + position + 1}
            environment={environment}
          />
        ))}
        {listProblem !== undefined ? (
          <p role="alert" className="text-xs text-destructive">
            {listProblem}
          </p>
        ) : null}
        <Button type="button" variant="outline" size="sm" disabled={ctx.disabled || listProblem !== undefined} onClick={() => ctx.onDrafts(addDatabase(ctx.drafts, listPointer))}>
          <Plus aria-hidden="true" />
          Add database<span className="sr-only"> to {environment}</span>
        </Button>
      </section>
      <section aria-label={`Docker in ${environment}`} className="space-y-2">
        <h4 className="text-sm font-medium">Docker</h4>
        {dockerKeys.length > 0 ? (
          <div className="space-y-1">
            <p className="text-xs">
              {dockerKeys.length} setting{dockerKeys.length === 1 ? '' : 's'} in the file; values are not shown here.
            </p>
            <ul aria-label={`Docker keys in ${environment}`} className="flex flex-wrap gap-1.5">
              {dockerKeys.map((key) => (
                <li key={key} className="rounded border bg-muted/40 px-1.5 py-0.5 font-mono text-xs">
                  {key}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-xs italic text-muted-foreground">Nothing configured.</p>
        )}
        <p className="text-xs text-muted-foreground">Docker settings are free-form: edit them in the file.</p>
      </section>
    </div>
  );
}

function ApplicationEnvironment({ ctx, category, environment }: { ctx: Context; category: string; environment: string }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <Leaf ctx={ctx} segments={[category, environment, 'appUrl']} />
      </div>
      <Leaf ctx={ctx} segments={[category, environment, 'username']} />
      <Leaf ctx={ctx} segments={[category, environment, 'password']} />
    </div>
  );
}

function CategoryCard({ ctx, category }: { ctx: Context; category: string }) {
  const data = valueAt(ctx.view.data, [category]);
  const environments = environmentsOf(data);
  const agentsPointer = pointerOf(category, 'agents');
  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-mono text-base">{category}</CardTitle>
        <CardDescription>{CATEGORY_NOTES[category] ?? 'Custom category from the file.'}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <Label htmlFor={slug(agentsPointer)} className="text-sm font-medium">
            Agents allowed to use these credentials
          </Label>
          <ListEditor
            id={slug(agentsPointer)}
            label={`${category} agents`}
            value={listValue(ctx.view, ctx.drafts, agentsPointer)}
            disabled={ctx.disabled}
            placeholder="e.g. devops-specialist"
            onChange={(next) => ctx.onDrafts(setValue(ctx.drafts, agentsPointer, next))}
          />
        </div>
        <Tabs defaultValue={environments[0] ?? 'staging'}>
          <TabsList aria-label={`${category} environments`}>
            {environments.map((environment) => (
              <TabsTrigger key={environment} value={environment}>
                {environment}
              </TabsTrigger>
            ))}
          </TabsList>
          {environments.map((environment) => (
            <TabsContent key={environment} value={environment} className="mt-4">
              {isInfrastructure(category, valueAt(data, [environment])) ? (
                <InfrastructureEnvironment ctx={ctx} category={category} environment={environment} />
              ) : (
                <ApplicationEnvironment ctx={ctx} category={category} environment={environment} />
              )}
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
}

/** The form for a valid file; every control reads from the view and writes into the drafts. */
export function CredentialsForm({
  view,
  drafts,
  report,
  disabled,
  onDrafts,
}: {
  view: CredentialsLocalView;
  drafts: Drafts;
  report: DraftReport;
  disabled: boolean;
  onDrafts: (next: Drafts) => void;
}) {
  const ctx: Context = { view, report, drafts, onDrafts, disabled };
  const data = view.data ?? {};
  const intervalError = report.problems[WORK_FEEDBACK_INTERVAL];
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Work feedback</CardTitle>
          <CardDescription>Whether agents post a progress check-in while they work, and how often.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="flex items-center gap-3">
            <Switch
              id={slug(WORK_FEEDBACK_ACTIVE)}
              checked={switchValue(view, drafts, WORK_FEEDBACK_ACTIVE)}
              disabled={disabled}
              onCheckedChange={(next) => onDrafts(setValue(drafts, WORK_FEEDBACK_ACTIVE, next))}
            />
            <Label htmlFor={slug(WORK_FEEDBACK_ACTIVE)} className="text-sm">
              Work feedback active
            </Label>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor={slug(WORK_FEEDBACK_INTERVAL)} className="text-sm">
              Check-in interval (minutes)
            </Label>
            <Input
              id={slug(WORK_FEEDBACK_INTERVAL)}
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              value={textValue(view, drafts, WORK_FEEDBACK_INTERVAL)}
              disabled={disabled}
              aria-invalid={intervalError !== undefined || undefined}
              aria-describedby={intervalError !== undefined ? `${slug(WORK_FEEDBACK_INTERVAL)}-error` : undefined}
              className="max-w-32"
              onChange={(event) => onDrafts(setValue(drafts, WORK_FEEDBACK_INTERVAL, event.target.value))}
            />
            {intervalError !== undefined ? (
              <p id={`${slug(WORK_FEEDBACK_INTERVAL)}-error`} role="alert" className="text-xs text-destructive">
                {intervalError}
              </p>
            ) : null}
          </div>
        </CardContent>
      </Card>

      {categoriesOf(data).map((category) => (
        <CategoryCard key={category} ctx={ctx} category={category} />
      ))}

      {view.unknown_paths.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Other keys</CardTitle>
            <CardDescription>The form does not edit these. Change them in the file.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul aria-label="Keys only the file can change" className="space-y-1">
              {view.unknown_paths.map((pointer) => (
                <li key={pointer} className="font-mono text-xs">
                  {pointer}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
