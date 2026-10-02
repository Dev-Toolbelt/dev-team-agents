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
 *   `tool.execute.after`              → scripts/hooks/post-tool-use.sh
 *     (`task`: a review agent's report, whose review-result marker the task board reads;
 *     `bash` when its command could create or merge a PR/MR, and the MCP tools ending in
 *     `create_pull_request` / `merge_pull_request`: the board records the PR/MR their RESULT
 *     confirms. Every other tool stays free.)
 *   `chat.message`                    → scripts/hooks/user-prompt-submit.sh
 *     (the user's prompt text, for review commands and requests and issue references on the task board)
 *   `experimental.session.compacting` → scripts/hooks/pre-compact.sh
 *   `session.idle` (event bus)        → scripts/hooks/stop.sh
 *   `session.updated` (a rename)      → scripts/hooks/session-retitle.sh
 *     (stdin carries a synthetic transcript_path built from the SDK's
 *     per-message token usage — see buildContextPayload below — so the
 *     context-window notifier in stop/04-notifier.sh gets real numbers
 *     instead of always falling back to the turn-count heuristic)
 *
 * Failures inside a hook (timeout, crash, an unexpected exit code) are logged but
 * NON-blocking: the opencode flow must continue. The one deliberate exception is
 * a PreToolUse refusal: the dispatcher exits 2 and prints the reason on stderr
 * (credential guard, full-suite guard), and `tool.execute.before` turns that into
 * a thrown Error, which is how opencode blocks a tool call. Stop and compaction
 * output (stderr + exit 2 in the bash hooks) is surfaced rather than dropped: the
 * compaction text joins the compaction context, a Stop message goes to the
 * opencode log via `client.app.log`.
 *
 * Placement: this file is copied by scripts/install-opencode.sh into
 * <project>/.opencode/plugins/dev-team-agents.ts. The framework install path
 * (.dev-team-agents/) is the project-local reference location for
 * hook scripts.
 */

import type { Plugin } from "@opencode-ai/plugin"
import { spawn } from "node:child_process"
import { writeFile, mkdtemp, rm } from "node:fs/promises"
import { existsSync, readFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { basename, join } from "node:path"

// Hook timeout: 5 seconds max. Prevents slow/broken hooks from freezing opencode.
const HOOK_TIMEOUT_MS = 5000
// The task-board hooks may wait on a session's record lock for up to 10 s (LOCK_TIMEOUT in
// scripts/lib/devteam/tasks.py); killing the hook first would lose the write it was waiting to
// make. Their budget therefore outlasts the lock. The lock stays at 10 s.
const TASK_BOARD_HOOK_TIMEOUT_MS = 12000
// `tool.execute.before` remembers a `task` call's `subagent_type` here, keyed by callID, for the
// matching `after` when opencode does not repeat the args. Bounded: an unmatched call is evicted.
const SUBAGENT_CALLS_KEPT = 256
// `bash` and pull-request MCP calls: a call whose command (or tool name) could not create or merge a
// PR/MR is never forwarded, so an ordinary shell command costs no process. The detector that decides
// what a forwarded call means is scripts/lib/devteam/pr_refs.py; this is only the cheap filter.
const PR_COMMAND_RE = /gh\s+pr\s+(create|merge)|glab\s+mr\s+(create|merge)|git\s[^|;&\n]*merge/
const PR_TOOL_RE = /(create|merge)_pull_request$/
// The output tail forwarded to the hook: a result sits at the end of a long command chain.
const OUTPUT_KEPT = 200000
// Session titles the plugin has looked up, for the task board's notifications. Bounded likewise.
const SESSION_TITLES_KEPT = 256

type HookResult = { code: number; stdout: string; stderr: string }

// opencode tool id -> the Claude Code name the guards' payload gate matches, the inverse of
// `providers.opencode.tool_rewrites` in scripts/lib/tool-map.json (its `_unchanged` names are
// the same word capitalized). `task` and `todowrite` are left out on purpose: the task board
// detects them by the bare `tool` key, and a Claude-named `tool_name` beside it would make it
// read them as Claude Code calls. An id not listed (patch, multiedit, MCP tools) sends no alias.
const CLAUDE_TOOL_NAMES: Record<string, string> = {
  bash: "Bash",
  read: "Read",
  write: "Write",
  edit: "Edit",
  glob: "Glob",
  grep: "Grep",
  question: "AskUserQuestion",
  websearch: "WebSearch",
  webfetch: "WebFetch",
}

export const DevTeamAgents: Plugin = async ({ client, directory }) => {
  // One path for both layouts: a v2 install vendors `scripts/` here and a v3 bind
  // links it here. A project bound before the link replaced the `core` pointer, and
  // not synced since, still has only the pointer — kept as the fallback.
  const SCRIPTS_HOOKS = `${directory}/.dev-team-agents/scripts/hooks`
  const CORE_POINTER_HOOKS = `${directory}/.dev-team-agents/core/scripts/hooks`
  // Looked up on every call, not once at load: the link can vanish mid-session (a `git rebase`
  // onto a commit that still vendored `.dev-team-agents/scripts` deletes it) and come back.
  const hooksDir = (): string => (existsSync(SCRIPTS_HOOKS) ? SCRIPTS_HOOKS : CORE_POINTER_HOOKS)

  // With neither directory present, the `core-dir` pointer names the store, whose
  // `scripts/hooks/lib/self-heal.sh` re-binds the project and runs the dispatcher (from the store
  // when the re-bind cannot restore the link) — the same recovery the Claude and Codex wrappers do.
  const selfHeal = (): string | null => {
    try {
      const core = readFileSync(join(directory, ".dev-team-agents", "core-dir"), "utf8").trim()
      const current = readFileSync(join(core, "current"), "utf8").trim()
      if (!core || !current) return null
      const heal = join(core, "versions", current, "scripts", "hooks", "lib", "self-heal.sh")
      return existsSync(heal) ? heal : null
    } catch {
      return null
    }
  }
  const bashArgs = (script: string): string[] => {
    if (existsSync(script)) return [script]
    const heal = selfHeal()
    return heal ? [heal, basename(script)] : [script]
  }

  // `exec` has no stdin option (only the sync variants do), so the payload is written to a
  // spawned child; a hook that reads stdin would otherwise wait for it until the timeout.
  // stderr is captured (and capped) because it carries a refusal's reason, and an unread pipe
  // would fill and block the script. The child leads its own process group, so a timeout kills the python children the dispatcher
  // forked too, not just bash. `cwd` is the project root every hook assumes it runs in; left
  // unset, the child inherits whatever directory the opencode process happens to be in.
  const runScript = (script: string, stdin?: string, timeoutMs: number = HOOK_TIMEOUT_MS): Promise<HookResult> =>
    new Promise((resolve, reject) => {
      const posix = process.platform !== "win32"
      const child = spawn("bash", bashArgs(script), { cwd: directory, stdio: ["pipe", "pipe", "pipe"], detached: posix })
      let stdout = ""
      let stderr = ""
      const timer = setTimeout(() => {
        try {
          if (posix && child.pid) process.kill(-child.pid, "SIGKILL")
          else child.kill("SIGKILL")
        } catch {
          child.kill("SIGKILL")
        }
        reject(new Error(`timed out after ${timeoutMs}ms`))
      }, timeoutMs)
      child.stdout.on("data", (chunk) => {
        if (stdout.length < 1024 * 1024) stdout += String(chunk)
      })
      child.stderr.on("data", (chunk) => {
        if (stderr.length < 1024 * 1024) stderr += String(chunk)
      })
      child.on("error", (err) => {
        clearTimeout(timer)
        reject(err)
      })
      child.on("close", (code) => {
        clearTimeout(timer)
        resolve({ code: code ?? 1, stdout, stderr })
      })
      child.stdin.on("error", () => {})
      child.stdin.end(stdin ?? "")
    })

  // A logging failure must not escape runHook: its result decides whether a tool is blocked.
  const warn = async (message: string): Promise<void> => {
    try {
      await client.app.log({ body: { service: "dev-team-agents", level: "warn", message } })
    } catch {}
  }

  const runHook = async (script: string, stdin?: string, timeoutMs?: number): Promise<HookResult> => {
    try {
      const result = await runScript(script, stdin, timeoutMs)
      // Exit 2 is a message the hook meant to be seen (the caller decides how); any other
      // non-zero exit is a hook that broke, which is logged and never blocks.
      if (result.code !== 0 && result.code !== 2) {
        await warn(`hook exited ${result.code}: ${script} — ${result.stderr.trim().slice(0, 2000)}`)
      }
      return result
    } catch (err) {
      // Timeout or error — log but don't block
      await warn(`hook timeout/error: ${script} — ${String(err)}`)
      return { code: 0, stdout: "", stderr: "" }
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
  // The text of an assistant message, for the task board's review-result scan at Stop.
  const textOf = (message: any): string =>
    (message?.parts ?? [])
      .filter((p: any) => p?.type === "text" && typeof p.text === "string")
      .map((p: any) => p.text)
      .join("\n")

  const buildContextPayload = async (
    sessionID: string,
  ): Promise<{ stdin?: string; cleanup?: () => Promise<void> }> => {
    let lastText = ""
    try {
      const res = await client.session.messages({ path: { id: sessionID } })
      const messages = res.data ?? []
      // The final text of THIS turn: stop at the last user message, never reach into an
      // earlier turn's report.
      for (let i = messages.length - 1; i >= 0; i--) {
        const role = messages[i]?.info?.role
        if (role === "user") break
        if (role === "assistant") {
          lastText = textOf(messages[i])
          if (lastText.trim()) break
        }
      }
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
          stdin: JSON.stringify({
            transcript_path: file,
            session_id: sessionID,
            session_title: await sessionTitle(sessionID),
            last_assistant_message: lastText,
          }),
          cleanup: () => rm(dir, { recursive: true, force: true }),
        }
      }
    } catch {
      // Fall through with no stdin — stop.sh's notifier falls back to the
      // turn-count heuristic, same as it does today.
    }
    // No token usage yet: still name the session, so stop/04b-task-board.sh can mark it idle.
    return {
      stdin: JSON.stringify({
        session_id: sessionID,
        session_title: await sessionTitle(sessionID),
        last_assistant_message: lastText,
      }),
    }
  }

  const prArgsByCall = new Map<string, any>()
  const subagentByCall = new Map<string, string>()
  const rememberSubagent = (callID: unknown, type: unknown) => {
    if (typeof callID !== "string" || typeof type !== "string" || !callID || !type) return
    subagentByCall.set(callID, type)
    while (subagentByCall.size > SUBAGENT_CALLS_KEPT) {
      const oldest = subagentByCall.keys().next().value
      if (oldest === undefined) break
      subagentByCall.delete(oldest)
    }
  }

  // The title opencode shows for a session, sent to the hooks as `session_title` so a task-board
  // notification can name the session rather than its id. Claude Code and Codex keep theirs where
  // the CLI can read it (transcript, session index); opencode only has it through the SDK.
  // Looked up once per session and refreshed by `session.updated`; "" when unavailable.
  const titleBySession = new Map<string, string>()
  // A child session's parent, sent as `parent_id`: a subagent's edits are its agent task's, so the
  // task board's "Direct work" card counts only the top session's. Kept beside the title, same cap.
  const parentBySession = new Map<string, string>()
  const rememberTitle = (sessionID: unknown, title: unknown, parentID?: unknown) => {
    if (typeof sessionID !== "string" || !sessionID) return
    // Known even when the title is not: `session.updated` carries the whole session.
    if (typeof parentID === "string" && parentID) parentBySession.set(sessionID, parentID)
    if (typeof title !== "string") return
    titleBySession.delete(sessionID)
    titleBySession.set(sessionID, title)
    while (titleBySession.size > SESSION_TITLES_KEPT) {
      const oldest = titleBySession.keys().next().value
      if (oldest === undefined) break
      titleBySession.delete(oldest)
      parentBySession.delete(oldest)
    }
  }
  const sessionTitle = async (sessionID: string): Promise<string> => {
    if (titleBySession.has(sessionID)) return titleBySession.get(sessionID) ?? ""
    try {
      const res = await client.session.get({ path: { id: sessionID } })
      const title = typeof res.data?.title === "string" ? res.data.title : ""
      rememberTitle(sessionID, title, (res.data as any)?.parentID)
      return title
    } catch {
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
      if (event.type === "session.updated") {
        const info: any = (event as any).properties?.info
        const known = typeof info?.id === "string" && titleBySession.has(info.id)
        const before = known ? titleBySession.get(info.id) : undefined
        rememberTitle(info?.id, info?.title, info?.parentID)
        // A rename reaches the task board now, not at the next turn: opencode keeps the title in
        // its own storage, out of the CLI's reach (Claude Code and Codex are read at view time).
        // Only a change of a title already seen: the first sighting is the session being created.
        if (known && typeof info?.title === "string" && info.title && info.title !== before) {
          const payload = JSON.stringify({ session_id: info.id, sessionID: info.id, session_title: info.title })
          await safe("session-retitle", () => runHook(`${hooksDir()}/session-retitle.sh`, payload, TASK_BOARD_HOOK_TIMEOUT_MS))
        }
      }
      if (event.type === "session.created") {
        await safe("session-start", () => runHook(`${hooksDir()}/session-start.sh`))
      }
      if (event.type === "session.idle") {
        await safe("stop", async () => {
          const { stdin, cleanup } = await buildContextPayload(event.properties.sessionID)
          try {
            const r = await runHook(`${hooksDir()}/stop.sh`, stdin, TASK_BOARD_HOOK_TIMEOUT_MS)
            // Exit 2 is a prompt for the model (session summary, ADR gap, agent lint). opencode's
            // idle event cannot continue the turn, so the message is logged rather than lost.
            const message = (r.stderr.trim() || r.stdout.trim()).slice(0, 4000)
            if (r.code === 2 && message) {
              await client.app.log({ body: { service: "dev-team-agents", level: "warn", message: `stop hook: ${message}` } })
            }
          } finally {
            if (cleanup) await cleanup()
          }
        })
      }
    },

    "tool.execute.before": async (input, output) => {
      if (input.tool === "task") rememberSubagent((input as any).callID, output.args?.subagent_type)
      const before: any = input
      if (typeof before.callID === "string" && (input.tool === "bash" || PR_TOOL_RE.test(input.tool))) {
        prArgsByCall.set(before.callID, output.args)
        while (prArgsByCall.size > SUBAGENT_CALLS_KEPT) {
          const oldest = prArgsByCall.keys().next().value
          if (oldest === undefined) break
          prArgsByCall.delete(oldest)
        }
      }
      // `sessionID` first: the bash gates take the first session key in the payload, and
      // `args` is whatever the model or the user put there.
      // `cwd`: the board records the worktree a task was started in, as Claude Code and Codex
      // payloads already allow (their hooks carry the session's working directory).
      // `tool_name` / `tool_input`: the Claude Code spelling of the same call, which the guards
      // (credential, full-suite) gate on. `tool` and `args` stay for the task board.
      const claudeName = CLAUDE_TOOL_NAMES[input.tool]
      const payload = JSON.stringify({
        sessionID: input.sessionID,
        tool: input.tool,
        ...(claudeName ? { tool_name: claudeName, tool_input: output.args } : {}),
        tool_use_id: (input as any).callID,
        cwd: directory,
        session_title: await sessionTitle(input.sessionID),
        // A subagent runs in a child session: its edits are its agent task's, not direct work.
        parent_id: parentBySession.get(input.sessionID),
        args: output.args,
      })
      // Outside `safe()`: a refusal must reach opencode. runHook never throws, so a broken or
      // timed-out hook still lets the call through.
      const r = await runHook(`${hooksDir()}/pre-tool-use.sh`, payload, TASK_BOARD_HOOK_TIMEOUT_MS)
      if (r.code === 2) throw new Error(r.stderr.trim() || r.stdout.trim() || "blocked by a dev-team-agents PreToolUse hook")
    },

    "tool.execute.after": async (input, output) => {
      const callID = (input as any).callID
      if (input.tool === "bash" || PR_TOOL_RE.test(input.tool)) {
        const known: any = (input as any).args ?? (typeof callID === "string" ? prArgsByCall.get(callID) : undefined)
        if (typeof callID === "string") prArgsByCall.delete(callID)
        const isPrTool = input.tool !== "bash"
        if (!isPrTool && !(typeof known?.command === "string" && PR_COMMAND_RE.test(known.command))) return
        const text = typeof output.output === "string" ? output.output.slice(-OUTPUT_KEPT) : output.output
        // Same key order as the `task` payload below: `sessionID` first, the call's args before its output.
        const payload = JSON.stringify({
          sessionID: input.sessionID,
          tool: input.tool,
          tool_use_id: callID,
          cwd: directory,
          session_title: await sessionTitle(input.sessionID),
          args: known,
          output: text,
        })
        await safe("post-tool-use", () => runHook(`${hooksDir()}/post-tool-use.sh`, payload, TASK_BOARD_HOOK_TIMEOUT_MS))
        return
      }
      // Only a subagent's report can carry a review result; every other tool stays free.
      if (input.tool !== "task") return
      const args: any = { ...((input as any).args ?? {}) }
      // The spawn's `subagent_type` names the agent whose report this is; opencode may not
      // repeat the args in `after`, so it is taken from the matching `before`.
      if (!args.subagent_type && typeof callID === "string" && subagentByCall.has(callID)) {
        args.subagent_type = subagentByCall.get(callID)
      }
      if (typeof callID === "string") subagentByCall.delete(callID)
      const payload = JSON.stringify({
        sessionID: input.sessionID,
        tool: input.tool,
        tool_use_id: callID,
        cwd: directory,
        session_title: await sessionTitle(input.sessionID),
        args,
        output: output.output,
      })
      await safe("post-tool-use", () => runHook(`${hooksDir()}/post-tool-use.sh`, payload, TASK_BOARD_HOOK_TIMEOUT_MS))
    },

    "chat.message": async (input, output) => {
      let text = (output.parts ?? [])
        .filter((p: any) => p?.type === "text" && typeof p.text === "string")
        .map((p: any) => p.text)
        .join("\n")
      // A slash command reaches this hook either raw (`/devteam:review`) or already expanded into
      // its template; the detector matches the raw form only. When the raw text is not in the
      // parts but opencode names the command, rebuild it. Uncertain: see docs/providers.md.
      const named: any = input
      if (typeof named.command === "string" && named.command && !text.trimStart().startsWith("/")) {
        const args = typeof named.arguments === "string" ? named.arguments : ""
        text = `/${named.command.replace(/^\//, "")}${args ? ` ${args}` : ""}\n${text}`
      }
      if (!text.trim()) return
      // `prompt` last: the bash gate only looks at what follows that key.
      const payload = JSON.stringify({ session_id: input.sessionID, prompt: text })
      await safe("user-prompt-submit", () =>
        runHook(`${hooksDir()}/user-prompt-submit.sh`, payload, TASK_BOARD_HOOK_TIMEOUT_MS),
      )
    },

    "experimental.session.compacting": async (_input, output) => {
      const r = await runHook(`${hooksDir()}/pre-compact.sh`)
      const text = r.stdout.trim() || r.stderr.trim()
      if (text) {
        output.context.push(`## dev-team-agents session summary\n${text}`)
      }
    },
  }
}