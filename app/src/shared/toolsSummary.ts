/**
 * How a `tools install` answer is reported (ADR-0060). Pure, so the wording is tested without a
 * renderer. The CLI exits 0 when a tool fails, so "the command succeeded" and "every tool is in
 * place" are different questions and this is where they are told apart.
 */

import type { ToolRecord, ToolsReport } from './api.js';

export type ToolsOutcome =
  /** Nothing was missing, or the install was switched off: nothing worth a toast. */
  | { readonly kind: 'quiet' }
  | { readonly kind: 'installed'; readonly title: string }
  | { readonly kind: 'problem'; readonly title: string; readonly detail: string };

function names(tools: readonly ToolRecord[]): string {
  return tools.map((tool) => tool.name).join(', ');
}

export function summarizeTools(report: ToolsReport): ToolsOutcome {
  const installed = report.tools.filter((tool) => tool.status === 'installed');
  const failed = report.tools.filter((tool) => tool.status === 'failed');
  const skipped = report.tools.filter((tool) => tool.status === 'skipped');

  if (failed.length > 0 || skipped.length > 0) {
    const lines = [...failed, ...skipped].map(
      (tool) => `${tool.name} (${tool.status}): ${tool.reason ?? 'no reason given'}`,
    );
    const title =
      failed.length > 0
        ? `${failed.length} helper tool${failed.length === 1 ? '' : 's'} could not be installed`
        : `${skipped.length} helper tool${skipped.length === 1 ? ' was' : 's were'} skipped`;
    return { kind: 'problem', title, detail: lines.join('\n') };
  }
  if (installed.length > 0) {
    const onPath = report.on_path === false && report.bin_dir !== null ? ` Add ${report.bin_dir} to your PATH to use them.` : '';
    return { kind: 'installed', title: `Installed helper tools: ${names(installed)}.${onPath}` };
  }
  return { kind: 'quiet' };
}
