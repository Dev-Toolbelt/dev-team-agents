/**
 * The one outbound link path of the board and the canvas: ids only, never a URL. The main
 * process finds the URL in its own snapshot and validates it before the OS browser sees it.
 */
import { toastLinkRefused } from './toasts.js';
import type { OpenTaskLinkRequest } from '../shared/api.js';

export async function openTaskLink(request: OpenTaskLinkRequest): Promise<void> {
  try {
    const answer = await window.devteam.openTaskLink(request);
    if (!answer.ok) toastLinkRefused(answer.message);
  } catch {
    toastLinkRefused('That link could not be opened.');
  }
}

/** `host/path` of a link, for its tooltip: where the click goes, without the scheme. Empty when unparseable. */
export function destinationOf(url: string): string {
  try {
    const parsed = new URL(url);
    return `${parsed.hostname}${parsed.pathname}`;
  } catch {
    return '';
  }
}
