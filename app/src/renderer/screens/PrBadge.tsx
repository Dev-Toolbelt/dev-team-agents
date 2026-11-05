import { ExternalLink } from 'lucide-react';

import { Hint } from '@/components/ui/tooltip';
import { destinationOf, openTaskLink } from '../taskLinks.js';
import type { BoardTaskPr, OpenTaskLinkRequest } from '../../shared/api.js';

export const LINK_BUTTON_CLASS =
  'inline-flex items-center gap-0.5 rounded-sm font-mono text-info underline-offset-2 hover:underline focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-hidden';

/** `#45` for a pull request, `!45` for a merge request. The accessible name says what pressing it does. */
export function PrBadge({ pr, request, className }: { pr: BoardTaskPr; request: OpenTaskLinkRequest; className?: string }) {
  const label = pr.kind === 'pr' ? `#${pr.number}` : `!${pr.number}`;
  const name = `Open ${pr.kind === 'pr' ? 'pull' : 'merge'} request ${label} in browser`;
  const destination = destinationOf(pr.url);
  return (
    <Hint content={destination === '' ? name : `${name} (${destination})`}>
      <button
        type="button"
        aria-label={name}
        onClick={() => void openTaskLink(request)}
        className={className === undefined ? LINK_BUTTON_CLASS : `${LINK_BUTTON_CLASS} ${className}`}
      >
        {label}
        <ExternalLink className="size-3" aria-hidden="true" />
      </button>
    </Hint>
  );
}
