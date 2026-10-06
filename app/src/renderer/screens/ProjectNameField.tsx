import { useId, useState, type FormEvent } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { PROJECT_NAME_MAX_LENGTH, projectNameProblem } from '../../shared/api.js';

/**
 * The project's display name, editable. App-local (see `BindRequest.name`): saving never
 * runs a CLI command, so it works even when the write gate refuses the store's writes.
 *
 * `storedName` is the name the app holds, absent when the row shows the folder's name.
 * Reset is offered only when there is something to reset.
 */
export function ProjectNameField({
  projectId,
  folderName,
  storedName,
  onRenamed,
}: {
  projectId: string;
  folderName: string;
  storedName: string | undefined;
  /** The new stored name, or `undefined` once reset to the folder's name. */
  onRenamed: (projectId: string, name: string | undefined) => void;
}) {
  const inputId = useId();
  const errorId = useId();
  const [draft, setDraft] = useState(storedName ?? '');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmed = draft.trim();
  const unchanged = trimmed === (storedName ?? '');
  // An empty field is not an error to shout about: it is the folder's name, and Reset is
  // the explicit way to get there.
  const invalid = trimmed !== '' ? projectNameProblem(draft) : null;
  const shownError = error ?? invalid;

  async function apply(name: string | null) {
    setPending(true);
    setError(null);
    try {
      const answer = await window.devteam.renameProject(projectId, name);
      if (!answer.ok) {
        setError(answer.message);
        return;
      }
      if (name === null) {
        setDraft('');
        onRenamed(projectId, undefined);
        toast.success(`Name reset to “${folderName}”`, { duration: 4_000 });
      } else {
        setDraft(name);
        onRenamed(projectId, name);
        toast.success(`Renamed to “${name}”`, { duration: 4_000 });
      }
    } catch (caught) {
      setError(`The name could not be saved: ${caught instanceof Error ? caught.message : String(caught)}`);
    } finally {
      setPending(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (unchanged || trimmed === '' || invalid !== null || pending) return;
    void apply(trimmed);
  }

  return (
    <form onSubmit={submit} className="space-y-1.5" noValidate>
      <Label htmlFor={inputId}>Name</Label>
      <div className="flex flex-wrap items-center gap-2">
        <Input
          id={inputId}
          value={draft}
          placeholder={folderName}
          maxLength={PROJECT_NAME_MAX_LENGTH + 40}
          disabled={pending}
          aria-invalid={shownError !== null}
          aria-describedby={shownError !== null ? errorId : undefined}
          onChange={(event) => {
            setDraft(event.target.value);
            setError(null);
          }}
          className="max-w-sm"
        />
        <Button type="submit" size="sm" disabled={pending || unchanged || trimmed === '' || invalid !== null}>
          {pending ? 'Saving…' : 'Save name'}
        </Button>
        {storedName !== undefined ? (
          <Button type="button" variant="outline" size="sm" disabled={pending} onClick={() => void apply(null)}>
            Reset to folder name
          </Button>
        ) : null}
      </div>
      <p className="text-xs text-muted-foreground">Shown in this app only. The folder on disk keeps its name.</p>
      <p id={errorId} role="alert" className="text-xs text-destructive">
        {shownError}
      </p>
    </form>
  );
}
