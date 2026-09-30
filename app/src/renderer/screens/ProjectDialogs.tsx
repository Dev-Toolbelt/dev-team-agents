/**
 * The two per-project actions that live on the project screen: pin and unbind. They used to
 * be row buttons; a row is for scanning, and unbind in particular should not sit one stray
 * click from a list of a hundred projects.
 */
import { useState } from 'react';

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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Problem } from '../Problem.js';
import { useAction } from '../useOperation.js';
import { Notice } from '../WriteButton.js';
import type { ProjectRecord, UnbindReport } from '../../shared/api.js';

/** Set or release a pin. `setPin(id, null)` releases it — not `setPin(id, '')`. */
export function PinDialog({
  open,
  onOpenChange,
  projectId,
  name,
  currentPin,
  onChanged,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  name: string;
  currentPin: string | null;
  onChanged: () => void;
}) {
  const [version, setVersion] = useState('');
  const pin = useAction((v: string | null) => window.devteam.setPin(projectId, v));

  function close() {
    pin.reset();
    setVersion('');
    onOpenChange(false);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (next) onOpenChange(true);
        else if (pin.state.phase !== 'pending') close();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Pin {name}</DialogTitle>
          <DialogDescription>
            {currentPin !== null
              ? `Currently pinned to ${currentPin}. Set a different version, or release the pin to track the store's current version again.`
              : 'Not pinned — this project tracks the store’s current version. Set a version to pin it.'}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-2">
          <Label htmlFor="pin-version">Version</Label>
          <Input
            id="pin-version"
            value={version}
            onChange={(event) => setVersion(event.target.value)}
            placeholder="e.g. 2.48.0"
          />
        </div>

        {pin.state.phase === 'done' && !pin.state.result.ok ? <Problem problem={pin.state.result} /> : null}
        {pin.state.phase === 'done' && pin.state.result.ok ? (
          <p className="text-sm text-muted-foreground">
            {pin.state.result.data.pin !== null ? `Pinned to ${pin.state.result.data.pin}.` : 'Pin released.'}
          </p>
        ) : null}
        {pin.state.phase === 'done' ? <Notice result={pin.state.result} /> : null}

        <DialogFooter>
          {currentPin !== null ? (
            <Button
              variant="outline"
              disabled={pin.state.phase === 'pending'}
              onClick={() => {
                void pin.run(null).then((result) => {
                  if (result.ok) onChanged();
                });
              }}
            >
              Release pin
            </Button>
          ) : null}
          <Button
            disabled={pin.state.phase === 'pending' || version.trim() === ''}
            onClick={() => {
              void pin.run(version.trim()).then((result) => {
                if (result.ok) onChanged();
              });
            }}
          >
            {pin.state.phase === 'pending' ? 'Setting…' : 'Set pin'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Unbind's explicit confirm step. States what will happen, and keeps the destructive button
 * disabled until the user ticks the acknowledgement — opening the dialog and pressing the
 * button once is not enough.
 */
export function UnbindDialog({
  open,
  onOpenChange,
  project,
  name,
  onUnbound,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  project: ProjectRecord;
  name: string;
  onUnbound: () => void;
}) {
  const unbind = useAction(() => window.devteam.unbindProject(project.project_id));
  const [understood, setUnderstood] = useState(false);
  const pending = unbind.state.phase === 'pending';
  const unbound = unbind.state.phase === 'done' && unbind.state.result.ok;

  // The list reloads when the dialog closes, not when the write lands: a successful unbind
  // takes the user off this project's screen, and with it this dialog and the quarantine
  // report the user has to read. Every way out — Done, Cancel, Esc, a click outside — comes through here, so a
  // dismissal after success cannot leave the list stale.
  function close() {
    if (pending) return;
    unbind.reset();
    setUnderstood(false);
    onOpenChange(false);
    if (unbound) onUnbound();
  }

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? onOpenChange(true) : close())}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Unbind {name}?</DialogTitle>
          <DialogDescription>
            This removes the store&apos;s link to <span className="font-mono">{project.path}</span>.
          </DialogDescription>
        </DialogHeader>

        {unbound ? null : (
          <div className="space-y-3 text-sm">
            <ul className="list-inside list-disc space-y-1 text-muted-foreground">
              <li>Files this store manages in the project are quarantined, not deleted.</li>
              <li>
                <span className="font-mono">project.json</span>, the project&apos;s memory (user-data) and its own
                files are kept.
              </li>
              <li>You can bind the project again at any time.</li>
            </ul>
            <div className="flex items-start gap-2">
              <Checkbox
                id="unbind-confirm"
                checked={understood}
                disabled={pending}
                onCheckedChange={(checked) => setUnderstood(checked === true)}
              />
              <Label htmlFor="unbind-confirm" className="font-normal leading-snug">
                I understand — unbind {name} from the store.
              </Label>
            </div>
          </div>
        )}

        {unbind.state.phase === 'done' && !unbind.state.result.ok ? <Problem problem={unbind.state.result} /> : null}
        {unbind.state.phase === 'done' && unbind.state.result.ok ? (
          <UnbindResultSummary report={unbind.state.result.data} />
        ) : null}
        {unbind.state.phase === 'done' ? <Notice result={unbind.state.result} /> : null}

        <DialogFooter>
          <Button variant="outline" disabled={pending} onClick={close}>
            Cancel
          </Button>
          {unbound ? (
            <Button onClick={close}>Done</Button>
          ) : (
            <Button
              variant="destructive"
              disabled={pending || !understood}
              onClick={() => void unbind.run()}
            >
              {unbind.state.phase === 'pending' ? 'Unbinding…' : 'Unbind'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * `quarantined` is the one the user must read — it names where their files went.
 * `unlinked` is ~159 entries on a claude-only bind, so its length is shown, not the list.
 */

function UnbindResultSummary({ report }: { report: UnbindReport }) {
  return (
    <div className="space-y-1 text-sm">
      <p>{report.unlinked.length} link{report.unlinked.length === 1 ? '' : 's'} removed.</p>
      {report.quarantined.length > 0 ? (
        <div>
          <p className="font-medium">Quarantined to:</p>
          <ul className="list-inside list-disc font-mono text-xs text-muted-foreground">
            {report.quarantined.map((entry, index) => (
              <li key={index}>{entry.to ?? '(no destination reported)'}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {report.problems.length > 0 ? (
        <p className="text-destructive">{report.problems.length} problem{report.problems.length === 1 ? '' : 's'} reported.</p>
      ) : null}
    </div>
  );
}

