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
 *     (stdin carries a synthetic transcript_path built from the SDK's
 *     per-message token usage — see buildContextPayload below — so the
 *     context-window notifier in stop/04-notifier.sh gets real numbers
 *     instead of always falling back to the turn-count heuristic)
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
import { writeFile, mkdtemp, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"

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

  // Builds the stdin payload for stop.sh's context-window estimation.
  // 04-notifier.sh reads `transcript_path` from stdin JSON and parses the
  // LAST usage entry's cache_read_input_tokens + cache_creation_input_tokens
  // + input_tokens as the exact current context size (see that script for
  // why: prompt caching means those fields, summed, equal what was actually
  // sent on the last API call). opencode has no Claude-style transcript
  // JSONL on disk, but the SDK exposes the same numbers per-message as
  // `tokens: {input, output, cache: {read, write}}` — this maps that shape
  // onto the same key names 04-notifier.sh already parses, so no bash-side
  // change is needed to support opencode. Without this, the plugin used to
  // call stop.sh with no stdin at all, so the transcript-based method could
  // never activate on opencode — it silently fell back to the much coarser
  // turn-count heuristic on every session.
  const buildContextPayload = async (
    sessionID: string,
  ): Promise<{ stdin?: string; cleanup?: () => Promise<void> }> => {
    try {
      const res = await client.session.messages({ path: { id: sessionID } })
      const messages = res.data ?? []
      for (let i = messages.length - 1; i >= 0; i--) {
        const info: any = messages[i]?.info
        if (info?.role !== "assistant" || !info.tokens) continue
        const t = info.tokens
        const dir = await mkdtemp(join(tmpdir(), "devteam-transcript-"))
        const file = join(dir, "transcript.jsonl")
        const line = JSON.stringify({
          usage: {
            input_tokens: t.input ?? 0,
            output_tokens: t.output ?? 0,
            cache_read_input_tokens: t.cache?.read ?? 0,
            cache_creation_input_tokens: t.cache?.write ?? 0,
          },
        })
        await writeFile(file, `${line}\n`)
        return {
          stdin: JSON.stringify({ transcript_path: file }),
          cleanup: () => rm(dir, { recursive: true, force: true }),
        }
      }
    } catch {
      // Fall through with no stdin — stop.sh's notifier falls back to the
      // turn-count heuristic, same as it does today.
    }
    return {}
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
        await safe("stop", async () => {
          const { stdin, cleanup } = await buildContextPayload(event.properties.sessionID)
          try {
            await runHook(`${HOOKS}/stop.sh`, stdin)
          } finally {
            if (cleanup) await cleanup()
          }
        })
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