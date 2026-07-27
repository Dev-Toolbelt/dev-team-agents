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
import { exec } from "node:child_process"
import { promisify } from "node:util"

const execAsync = promisify(exec)

// Hook timeout: 5 seconds max. Prevents slow/broken hooks from freezing opencode.
const HOOK_TIMEOUT_MS = 5000

export const DevTeamAgents: Plugin = async ({ client, directory }) => {
  const HOOKS = `${directory}/.dev-team-agents/scripts/hooks`

  const runHook = async (script: string, stdin?: string): Promise<string> => {
    try {
      const { stdout } = await execAsync(`bash ${script}`, {
        input: stdin,
        maxBuffer: 1024 * 1024,
        timeout: HOOK_TIMEOUT_MS,
      })
      return stdout
    } catch (err) {
      // Timeout or error — log but don't block
      await client.app.log({
        body: {
          service: "dev-team-agents",
          level: "warn",
          message: `hook timeout/error: ${script} — ${String(err)}`,
        },
      })
      return ""
    }
  }

  const safe = async (label: string, fn: () => Promise<unknown>) => {
    try {
      await fn()
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
    event: async ({ event }) => {
      if (event.type === "session.created") {
        await safe("session-start", () => runHook(`${HOOKS}/session-start.sh`))
      }
      if (event.type === "session.idle") {
        await safe("stop", () => runHook(`${HOOKS}/stop.sh`))
      }
    },

    "tool.execute.before": async (input, output) => {
      const payload = JSON.stringify({ tool: input.tool, args: output.args })
      await safe("pre-tool-use", () => runHook(`${HOOKS}/pre-tool-use.sh`, payload))
    },

    "experimental.session.compacting": async (_input, output) => {
      const r = await runHook(`${HOOKS}/pre-compact.sh`)
      if (r && r.trim()) {
        output.context.push(`## dev-team-agents session summary\n${r.trim()}`)
      }
    },
  }
}