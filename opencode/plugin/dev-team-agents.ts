/**
 * dev-team-agents — opencode plugin
 *
 * Wires the framework's existing bash hook dispatchers (authored originally
 * for Claude Code, lives at scripts/hooks/*.sh in the framework install at
 * `.dev-team-agents/`) to opencode's plugin hook surface.
 *
 * Design: the bash scripts are the SINGLE SOURCE of hook behavior. They own
 * session-summary detection, orphan-skill scans, agent-lint, update checks,
 * notifier output, and telemetry. This plugin only binds opencode events to
 * those scripts; it contains no business logic of its own.
 *
 * Bindings:
 *   opencode event                    → bash dispatcher
 *   ─────────────────────────────────────────────────────────────
 *   `session.created`                 → scripts/hooks/session-start.sh
 *   `tool.execute.before`             → scripts/hooks/pre-tool-use.sh
 *   `experimental.session.compacting` → scripts/hooks/pre-compact.sh
 *   `session.idle` (event bus)        → scripts/hooks/stop.sh
 *
 * Failures inside any hook are logged but NON-blocking: the opencode flow
 * must continue. The bash dispatchers already honor set -euo pipefail and
 * write structured warnings to stderr; anything that returns non-zero is
 * surfaced in the opencode log via `client.app.log` (warn level) and
 * swallowed.
 *
 * Placement: this file is copied by scripts/install-opencode.sh into
 * <project>/.opencode/plugins/dev-team-agents.ts. The framework install path
 * (.dev-team-agents/) is the project-local reference location for
 * hook scripts.
 */

import type { Plugin } from "@opencode-ai/plugin"

export const DevTeamAgents: Plugin = async ({ client, directory, $ }) => {
  const HOOKS = `${directory}/.dev-team-agents/scripts/hooks`

  const safe = async (label: string, p: Promise<unknown>) => {
    try {
      await p
    } catch (err) {
      await client.app.log({
        body: {
          service: "dev-team-agents",
          level: "warn",
          message: `${label} hook failed: ${String(err)}`,
        },
      })
    }
  }

  return {
    // SessionStart equivalent — fires when opencode creates a new session.
    event: async ({ event }) => {
      if (event.type === "session.created") {
        await safe("session-start", $`bash ${HOOKS}/session-start.sh`.quiet())
      }
      // Stop equivalent — fires when the session goes idle (turn complete).
      if (event.type === "session.idle") {
        await safe("stop", $`bash ${HOOKS}/stop.sh`.quiet())
      }
    },

    // PreToolUse equivalent — fires before any tool runs.
    "tool.execute.before": async (input, output) => {
      const payload = JSON.stringify({ tool: input.tool, args: output.args })
      await safe(
        "pre-tool-use",
        $`bash ${HOOKS}/pre-tool-use.sh`.stdin(payload).quiet(),
      )
    },

    // PreCompact equivalent — fires before the model generates a compaction
    // continuation summary. May inject additional context into the compaction
    // prompt via `output.context`.
    "experimental.session.compacting": async (_input, output) => {
      const r = await $`bash ${HOOKS}/pre-compact.sh`.quiet().text().catch(() => "")
      if (r && r.trim()) {
        output.context.push(`## dev-team-agents session summary
${r.trim()}`)
      }
    },
  }
}