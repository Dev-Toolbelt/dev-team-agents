import { toast } from 'sonner';

import { summarizeTools } from '../shared/toolsSummary.js';
import { toastFailure, toastPartialFailure, toastResult } from './toasts.js';
import { unreachable } from './useOperation.js';

const TOOLS_TOAST_ID = 'tools-install';

/**
 * The helper-tool install that follows a bind or a first-run start (ADR-0060). Those commands
 * skip tools so they return quickly; this runs after they have succeeded and reports on its own.
 *
 * It never throws and never changes the caller's result: a tool that cannot be installed is a
 * toast, not a failed bind. A failure stays until closed (`toastFailure`); a bind already done is
 * still done.
 */
export async function runToolsInstall(): Promise<void> {
  toast.loading('Installing helper tools — this can take a few minutes', { id: TOOLS_TOAST_ID });
  try {
    const result = await window.devteam.installTools();
    toast.dismiss(TOOLS_TOAST_ID);
    if (!result.ok) {
      toastFailure(result, TOOLS_TOAST_ID);
      return;
    }
    const outcome = summarizeTools(result.data);
    if (outcome.kind === 'installed') toastResult(result, outcome.title, TOOLS_TOAST_ID);
    else if (outcome.kind === 'problem') toastPartialFailure(outcome.title, outcome.detail);
  } catch (error) {
    toast.dismiss(TOOLS_TOAST_ID);
    toastFailure(unreachable(error), TOOLS_TOAST_ID);
  }
}
