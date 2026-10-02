import { ChevronDown, ChevronRight, FolderInput, FolderPlus, KeyRound, Lock, LockOpen, Pencil, Plus, Search, ShieldAlert, Trash2 } from 'lucide-react';
import { useEffect, useState, type ComponentProps, type ReactNode } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Hint } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { SELECT_CLASS } from '../formStyles.js';
import {
  coerce,
  editProblem,
  isContainer,
  isRecord,
  isReserved,
  isSecretLeaf,
  markedIn,
  moveTargets,
  pointerOf,
  productionAt,
  scalarText,
  searchHits,
  valueAt,
  type Doc,
  type Edit,
  type Path,
} from './document.js';

/** A DOM id for a pointer. Injective: `/` reads as `-` and every other symbol is spelled out. */
const slug = (pointer: string): string =>
  `cred${pointer.replace(/[^A-Za-z0-9/]/g, (char) => `_${char.charCodeAt(0).toString(16)}_`).replace(/\//g, '-')}`;

const labelOf = (path: Path): string => path.map(String).join(' › ') || 'the file';

/**
 * A ghost button with a tooltip. `label` is the accessible name, naming the row it acts on;
 * `hint` is the shorter text the tooltip shows. `danger` paints it red.
 */
function IconAction({
  label,
  hint,
  disabled,
  danger = false,
  className,
  children,
  onClick,
  ...rest
}: {
  label: string;
  hint: string;
  disabled?: boolean;
  danger?: boolean;
  className?: string;
  children: ReactNode;
  onClick: () => void;
} & Pick<ComponentProps<'button'>, 'aria-expanded' | 'aria-controls'>) {
  return (
    <Hint content={hint}>
      {/* A disabled button gets no pointer events, so the tooltip hangs on this wrapper. */}
      <span className="inline-flex">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={disabled}
          aria-label={label}
          className={cn(danger && 'text-destructive hover:bg-destructive/10 hover:text-destructive', className)}
          onClick={onClick}
          {...rest}
        >
          {children}
        </Button>
      </span>
    </Hint>
  );
}

interface Ctx {
  doc: Doc;
  disabled: boolean;
  hits: ReadonlySet<string> | null;
  onEdit: (edit: Edit) => void;
  onProblem: (pointer: string, problem: string | null) => void;
}

/**
 * The credentials file as a free-form tree (ADR-0024): any group or field can be added, renamed,
 * nested or removed. Two reserved keys are drawn as controls, never as fields: `$secrets` (which
 * keys of an object are secret, toggled per field) and `$production` (set per group, inherited).
 */
export function CredentialsEditor({
  doc,
  disabled,
  onEdit,
  onProblem,
}: {
  doc: Doc;
  disabled: boolean;
  onEdit: (edit: Edit) => void;
  onProblem: (pointer: string, problem: string | null) => void;
}) {
  const [query, setQuery] = useState('');
  const hits = searchHits(doc, query);
  const ctx: Ctx = { doc, disabled, hits, onEdit, onProblem };
  const empty = hits !== null && hits.size === 0;
  return (
    <div className="space-y-4">
      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <Input
          type="search"
          value={query}
          placeholder="Search keys and visible values"
          aria-label="Search credentials"
          className="pl-8"
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>
      {empty ? <p className="text-sm text-muted-foreground">Nothing matches “{query.trim()}”. Secret values are never searched.</p> : null}
      <Children ctx={ctx} path={[]} node={doc} depth={0} />
      {hits === null ? <AddControls ctx={ctx} parent={[]} /> : null}
    </div>
  );
}

function Children({ ctx, path, node, depth }: { ctx: Ctx; path: Path; node: unknown; depth: number }) {
  const entries: [string | number, unknown][] = Array.isArray(node)
    ? node.map((item, index) => [index, item])
    : isRecord(node)
      ? Object.entries(node).filter(([key]) => !isReserved(key))
      : [];
  const shown = entries.filter(([key]) => ctx.hits === null || ctx.hits.has(pointerOf([...path, key])));
  if (shown.length === 0 && ctx.hits === null) return <p className="text-sm text-muted-foreground">Empty.</p>;
  return (
    <ul className="space-y-2" role="list">
      {shown.map(([key, value]) => (
        <li key={String(key)}>
          {isContainer(value) ? (
            <Group ctx={ctx} path={[...path, key]} node={value} depth={depth} />
          ) : (
            <Field ctx={ctx} path={[...path, key]} value={value} />
          )}
        </li>
      ))}
    </ul>
  );
}

function Group({ ctx, path, node, depth }: { ctx: Ctx; path: Path; node: Record<string, unknown> | unknown[]; depth: number }) {
  const [open, setOpen] = useState(depth < 2);
  const expanded = open || ctx.hits !== null;
  const id = slug(pointerOf(path));
  const production = productionAt(ctx.doc, path);
  const isList = Array.isArray(node);
  return (
    <section aria-labelledby={`${id}-name`} className="rounded-lg border">
      <div className="flex flex-wrap items-center gap-2 px-3 py-2">
        <IconAction
          label={`${expanded ? 'Collapse' : 'Expand'} ${labelOf(path)}`}
          hint={expanded ? 'Collapse' : 'Expand'}
          className="h-7 px-1"
          aria-expanded={expanded}
          aria-controls={`${id}-body`}
          onClick={() => setOpen(!open)}
        >
          {expanded ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
        </IconAction>
        <KeyName path={path} id={`${id}-name`} />
        <span className="text-xs text-muted-foreground">{isList ? `list · ${node.length}` : 'group'}</span>
        {production.own || production.inherited ? (
          <Badge variant="destructive">{production.own ? 'Production' : 'Production (inherited)'}</Badge>
        ) : null}
        <div className="ml-auto flex items-center gap-2">
          {!isList ? (
            <label className="flex items-center gap-1.5 text-xs">
              <Switch
                checked={production.own}
                disabled={ctx.disabled}
                aria-label={`${labelOf(path)} is production`}
                onCheckedChange={(on) => ctx.onEdit({ kind: 'production', path, on })}
              />
              Production
            </label>
          ) : null}
          <RowActions ctx={ctx} path={path} />
        </div>
      </div>
      {expanded ? (
        <div id={`${id}-body`} className="space-y-3 border-t px-3 py-3">
          <Children ctx={ctx} path={path} node={node} depth={depth + 1} />
          {ctx.hits === null ? <AddControls ctx={ctx} parent={path} /> : null}
        </div>
      ) : null}
    </section>
  );
}

function Field({ ctx, path, value }: { ctx: Ctx; path: Path; value: unknown }) {
  const id = slug(pointerOf(path));
  const key = path[path.length - 1];
  const markedHere = typeof key === 'string' && markedIn(valueAt(ctx.doc, path.slice(0, -1))).has(key);
  const hidden = isSecretLeaf(value) || markedHere;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="w-48 min-w-0 shrink-0">
        <KeyName path={path} id={`${id}-name`} />
      </div>
      <div className="min-w-0 flex-1">
        {hidden ? (
          <SecretField ctx={ctx} path={path} id={id} isSet={isSecretLeaf(value) ? value.set : value !== '' && value !== null} />
        ) : typeof value === 'boolean' ? (
          <Switch
            id={id}
            checked={value}
            disabled={ctx.disabled}
            aria-labelledby={`${id}-name`}
            onCheckedChange={(checked) => ctx.onEdit({ kind: 'value', path, value: checked })}
          />
        ) : (
          <TextField ctx={ctx} path={path} id={id} value={value} />
        )}
      </div>
      <SecretToggle ctx={ctx} path={path} value={value} markedHere={markedHere} />
      <RowActions ctx={ctx} path={path} />
    </div>
  );
}

function TextField({ ctx, path, id, value }: { ctx: Ctx; path: Path; id: string; value: unknown }) {
  const shown = scalarText(value);
  const [text, setText] = useState(shown);
  const [problem, setProblem] = useState<string | null>(null);
  const pointer = pointerOf(path);
  // A reload or an undo changes the value from outside: follow it unless the field holds an error.
  useEffect(() => {
    if (problem === null) setText(shown);
  }, [shown, problem]);
  return (
    <div className="space-y-1">
      <Input
        id={id}
        value={text}
        disabled={ctx.disabled}
        spellCheck={false}
        placeholder={value === null ? 'null' : undefined}
        aria-labelledby={`${id}-name`}
        aria-invalid={problem !== null || undefined}
        aria-describedby={problem !== null ? `${id}-error` : undefined}
        className="font-mono"
        onChange={(event) => {
          const next = event.target.value;
          setText(next);
          const parsed = coerce(next, value);
          setProblem(parsed.problem);
          ctx.onProblem(pointer, parsed.problem);
          if (parsed.problem === null) ctx.onEdit({ kind: 'value', path, value: parsed.value });
        }}
      />
      {problem !== null ? (
        <p id={`${id}-error`} role="alert" className="text-xs text-destructive">
          {problem}
        </p>
      ) : null}
    </div>
  );
}

/** Write-only: the stored value is never shown. Typing is offered only after Replace (or Set). */
function SecretField({ ctx, path, id, isSet }: { ctx: Ctx; path: Path; id: string; isSet: boolean }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState('');
  if (editing) {
    return (
      <div className="flex flex-wrap gap-2">
        <Input
          id={id}
          type="password"
          value={text}
          autoFocus
          disabled={ctx.disabled}
          autoComplete="new-password"
          spellCheck={false}
          placeholder={isSet ? 'Enter the new value' : 'Enter a value'}
          aria-labelledby={`${id}-name`}
          className="min-w-0 flex-1 font-mono"
          onChange={(event) => {
            setText(event.target.value);
            ctx.onEdit({ kind: 'value', path, value: event.target.value });
          }}
        />
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="flex items-center gap-1.5 text-sm">
        <KeyRound className="size-4 text-muted-foreground" aria-hidden="true" />
        {isSet ? 'Set' : 'Not set'}
      </span>
      <Button
        type="button"
        variant="outline"
        size="sm"
        disabled={ctx.disabled}
        aria-label={`${isSet ? 'Replace' : 'Set'} ${labelOf(path)}`}
        onClick={() => setEditing(true)}
      >
        {isSet ? 'Replace' : 'Set'}
      </Button>
    </div>
  );
}

/**
 * Mark or unmark a field as secret. A value hidden only because it looks secret can be marked but
 * never revealed from here; unmarking a marked one asks first, since the value shows after saving.
 */
function SecretToggle({ ctx, path, value, markedHere }: { ctx: Ctx; path: Path; value: unknown; markedHere: boolean }) {
  const [confirm, setConfirm] = useState(false);
  if (typeof path[path.length - 1] !== 'string') return null;
  const looksSecret = isSecretLeaf(value) && !value.marked && !markedHere;
  if (markedHere) {
    return (
      <>
        <IconAction
          label={`Secret: unmark ${labelOf(path)}`}
          hint="Secret: write-only here and hidden from command output. Click to stop treating it as one"
          disabled={ctx.disabled}
          onClick={() => setConfirm(true)}
        >
          <Lock aria-hidden="true" />
          Secret
        </IconAction>
        <Dialog open={confirm} onOpenChange={setConfirm}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Stop treating {labelOf(path)} as a secret?</DialogTitle>
              <DialogDescription>After you save, its value is shown here and in the command output.</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setConfirm(false)}>
                Keep it secret
              </Button>
              <Button
                variant="destructive"
                onClick={() => {
                  setConfirm(false);
                  ctx.onEdit({ kind: 'secret', path, marked: false });
                }}
              >
                Show the value
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </>
    );
  }
  return (
    <IconAction
      label={`${looksSecret ? 'Mark secret' : 'Not secret'}: mark ${labelOf(path)} as secret`}
      hint={
        looksSecret
          ? 'Hidden because it looks like a secret. Mark it to keep it hidden on purpose'
          : 'Visible value. Click to mark it as a secret'
      }
      disabled={ctx.disabled}
      onClick={() => ctx.onEdit({ kind: 'secret', path, marked: true })}
    >
      {looksSecret ? <ShieldAlert aria-hidden="true" /> : <LockOpen aria-hidden="true" />}
      {looksSecret ? 'Mark secret' : 'Not secret'}
    </IconAction>
  );
}

function KeyName({ path, id }: { path: Path; id: string }) {
  const key = path[path.length - 1];
  return typeof key === 'number' ? (
    <span id={id} className="font-mono text-sm text-muted-foreground">
      #{key + 1}
    </span>
  ) : (
    <span id={id} className="break-all font-mono text-sm font-medium">
      {key}
    </span>
  );
}

function RowActions({ ctx, path }: { ctx: Ctx; path: Path }) {
  const key = path[path.length - 1];
  return (
    <div className="flex items-center">
      {typeof key === 'string' ? <RenameButton ctx={ctx} path={path} /> : null}
      {typeof key === 'string' ? <MoveButton ctx={ctx} path={path} /> : null}
      <IconAction label={`Remove ${labelOf(path)}`} hint="Remove" danger disabled={ctx.disabled} onClick={() => ctx.onEdit({ kind: 'remove', path })}>
        <Trash2 aria-hidden="true" />
      </IconAction>
    </div>
  );
}

/** Renaming happens in a small dialog, so the row keeps one layout whatever its type. */
function RenameButton({ ctx, path }: { ctx: Ctx; path: Path }) {
  const key = String(path[path.length - 1]);
  const [open, setOpen] = useState(false);
  const [text, setText] = useState(key);
  const edit: Edit = { kind: 'rename', path, to: text };
  const problem = text.trim() === key ? null : editProblem(ctx.doc, edit);
  return (
    <>
      <IconAction
        label={`Rename ${labelOf(path)}`}
        hint="Rename"
        disabled={ctx.disabled}
        onClick={() => {
          setText(key);
          setOpen(true);
        }}
      >
        <Pencil aria-hidden="true" />
      </IconAction>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (problem !== null) return;
              ctx.onEdit(edit);
              setOpen(false);
            }}
          >
            <DialogHeader>
              <DialogTitle>Rename {labelOf(path)}</DialogTitle>
              <DialogDescription>A secret keeps its value: it is renamed in the file, never read.</DialogDescription>
            </DialogHeader>
            <div className="my-4 space-y-1">
              <Label htmlFor={`${slug(pointerOf(path))}-rename`}>New name</Label>
              <Input
                id={`${slug(pointerOf(path))}-rename`}
                value={text}
                autoFocus
                className="font-mono"
                aria-invalid={problem !== null || undefined}
                onChange={(event) => setText(event.target.value)}
              />
              {problem !== null ? <p role="alert" className="text-xs text-destructive">{problem}</p> : null}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={problem !== null}>
                Rename
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}

/** Move a field or group into another group, or to the top of the file. A secret keeps its mark. */
function MoveButton({ ctx, path }: { ctx: Ctx; path: Path }) {
  const [open, setOpen] = useState(false);
  const targets = open ? moveTargets(ctx.doc, path) : [];
  const [choice, setChoice] = useState('');
  const selected = targets.find((target) => pointerOf(target) === choice) ?? targets[0];
  const id = `${slug(pointerOf(path))}-move`;
  return (
    <>
      <IconAction
        label={`Move ${labelOf(path)}`}
        hint="Move to another group"
        disabled={ctx.disabled}
        onClick={() => {
          setChoice('');
          setOpen(true);
        }}
      >
        <FolderInput aria-hidden="true" />
      </IconAction>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (selected === undefined) return;
              ctx.onEdit({ kind: 'move', path, into: selected });
              setOpen(false);
            }}
          >
            <DialogHeader>
              <DialogTitle>Move {labelOf(path)}</DialogTitle>
              <DialogDescription>It keeps its name and value; a secret stays a secret where it lands.</DialogDescription>
            </DialogHeader>
            <div className="my-4 space-y-1">
              <Label htmlFor={id}>Move into</Label>
              {targets.length > 0 ? (
                <select
                  id={id}
                  className={SELECT_CLASS}
                  value={selected === undefined ? '' : pointerOf(selected)}
                  onChange={(event) => setChoice(event.target.value)}
                >
                  {targets.map((target) => (
                    <option key={pointerOf(target)} value={pointerOf(target)}>
                      {target.length === 0 ? 'The top of the file' : labelOf(target)}
                    </option>
                  ))}
                </select>
              ) : (
                <p role="status" className="text-sm text-muted-foreground">
                  No other group can take it: create one first, or rename the key that clashes.
                </p>
              )}
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={selected === undefined}>
                Move
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}

/** "Add field" and "Add group" for an object; "Add item" and "Add group" for a list. */
function AddControls({ ctx, parent }: { ctx: Ctx; parent: Path }) {
  const [adding, setAdding] = useState<'field' | 'group' | null>(null);
  const [name, setName] = useState('');
  const [value, setValue] = useState('');
  const [secret, setSecret] = useState(false);
  const isList = Array.isArray(valueAt(ctx.doc, parent));
  const id = `${slug(pointerOf(parent))}-add`;
  const reset = (): void => {
    setAdding(null);
    setName('');
    setValue('');
    setSecret(false);
  };
  if (adding === null) {
    return (
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={ctx.disabled}
          aria-label={`${isList ? 'Add item' : 'Add field'} to ${labelOf(parent)}`}
          onClick={() => setAdding('field')}
        >
          <Plus aria-hidden="true" />
          {isList ? 'Add item' : 'Add field'}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={ctx.disabled}
          aria-label={`Add group to ${labelOf(parent)}`}
          onClick={() => setAdding('group')}
        >
          <FolderPlus aria-hidden="true" />
          Add group
        </Button>
      </div>
    );
  }
  const edit: Edit = { kind: 'add', parent, key: isList ? null : name, value: adding === 'group' ? {} : value };
  const problem = editProblem(ctx.doc, edit);
  return (
    <form
      className="flex flex-wrap items-end gap-2 rounded-md border border-dashed p-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (problem !== null) return;
        ctx.onEdit(edit);
        if (secret && !isList) ctx.onEdit({ kind: 'secret', path: [...parent, name.trim()], marked: true });
        reset();
      }}
    >
      {!isList ? (
        <div className="space-y-1">
          <Label htmlFor={`${id}-name`} className="text-xs">
            {adding === 'group' ? 'Group name' : 'Field name'}
          </Label>
          <Input id={`${id}-name`} value={name} autoFocus className="h-8 w-44 font-mono" onChange={(event) => setName(event.target.value)} />
        </div>
      ) : null}
      {adding === 'field' ? (
        <div className="min-w-40 flex-1 space-y-1">
          <Label htmlFor={`${id}-value`} className="text-xs">
            Value
          </Label>
          <Input
            id={`${id}-value`}
            type={secret ? 'password' : 'text'}
            value={value}
            autoComplete="off"
            spellCheck={false}
            className="h-8 font-mono"
            onChange={(event) => setValue(event.target.value)}
          />
        </div>
      ) : null}
      {adding === 'field' && !isList ? (
        <label className="flex h-8 items-center gap-1.5 text-xs">
          <Checkbox checked={secret} onCheckedChange={(checked) => setSecret(checked === true)} />
          Secret
        </label>
      ) : null}
      <Button type="submit" size="sm" disabled={problem !== null || ctx.disabled}>
        Add
      </Button>
      <Button type="button" variant="ghost" size="sm" onClick={reset}>
        Cancel
      </Button>
      {problem !== null && name !== '' ? (
        <p role="alert" className="w-full text-xs text-destructive">
          {problem}
        </p>
      ) : null}
    </form>
  );
}
