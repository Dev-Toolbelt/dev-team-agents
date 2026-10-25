// Zero-dependency test of opencode/plugin/dev-team-agents.ts. Run by tests/test_opencode_plugin.py
// with a node that can import .ts natively (22.18+); stub hook scripts stand in for the framework.
import test from "node:test"
import assert from "node:assert/strict"
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, rmSync, realpathSync } from "node:fs"
import { tmpdir } from "node:os"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const here = dirname(fileURLToPath(import.meta.url))
const repo = join(here, "..", "..")
const { DevTeamAgents } = await import(join(repo, "opencode", "plugin", "dev-team-agents.ts"))
const toolMap = JSON.parse(readFileSync(join(repo, "scripts", "lib", "tool-map.json"), "utf8"))

// A project whose hook dispatchers are stubs: each records its stdin and exits with the code
// (and prints the stdout / stderr) named by a `<hook>.ctl` JSON file written by the test.
const makeProject = () => {
  const dir = mkdtempSync(join(tmpdir(), "devteam-plugin-"))
  const hooks = join(dir, ".dev-team-agents", "scripts", "hooks")
  mkdirSync(hooks, { recursive: true })
  for (const name of ["session-start", "pre-tool-use", "post-tool-use", "user-prompt-submit", "pre-compact", "backlog-prime", "stop"]) {
    writeFileSync(
      join(hooks, `${name}.sh`),
      [
        "#!/usr/bin/env bash",
        `cat > "${dir}/${name}.stdin"`,
        `[ -f "${dir}/${name}.ctl" ] || exit 0`,
        `. "${dir}/${name}.ctl"`,
        `[ -z "\${OUT:-}" ] || printf '%s\\n' "$OUT"`,
        `[ -z "\${ERR:-}" ] || printf '%s\\n' "$ERR" >&2`,
        `exit "\${CODE:-0}"`,
      ].join("\n"),
    )
  }
  return dir
}
const control = (dir, name, { code = 0, out = "", err = "" }) =>
  writeFileSync(join(dir, `${name}.ctl`), `CODE=${code}\nOUT='${out}'\nERR='${err}'\n`)
const stdinOf = (dir, name) => JSON.parse(readFileSync(join(dir, `${name}.stdin`), "utf8"))

const load = async (dir, messages = async () => ({ data: [] })) => {
  const logs = []
  const client = {
    app: { log: async ({ body }) => void logs.push(body) },
    session: { messages, get: async () => ({ data: { title: "t" } }) },
  }
  return { logs, plugin: await DevTeamAgents({ client, directory: dir }) }
}

test("a PreToolUse refusal (exit 2) blocks the tool by throwing the reason", async () => {
  const dir = makeProject()
  control(dir, "pre-tool-use", { code: 2, err: "BLOCKED: credential read" })
  const { plugin } = await load(dir)
  await assert.rejects(
    plugin["tool.execute.before"]({ tool: "bash", sessionID: "s1", callID: "c1" }, { args: { command: "cat credentials.local.json" } }),
    /BLOCKED: credential read/,
  )
})

test("the payload carries Claude-compatible aliases beside the opencode keys", async () => {
  const dir = makeProject()
  const { plugin } = await load(dir)
  const args = { command: "ls" }
  await plugin["tool.execute.before"]({ tool: "bash", sessionID: "s1", callID: "c1" }, { args })
  const sent = stdinOf(dir, "pre-tool-use")
  assert.equal(sent.tool, "bash")
  assert.equal(sent.tool_name, "Bash")
  assert.deepEqual(sent.tool_input, args)
  assert.deepEqual(sent.args, args)
  assert.equal(sent.sessionID, "s1")
})

test("task and todowrite keep the bare key only, so the task board still reads them as opencode", async () => {
  const dir = makeProject()
  const { plugin } = await load(dir)
  for (const tool of ["task", "todowrite"]) {
    await plugin["tool.execute.before"]({ tool, sessionID: "s1", callID: "c1" }, { args: { subagent_type: "x" } })
    const sent = stdinOf(dir, "pre-tool-use")
    assert.equal(sent.tool, tool)
    assert.equal("tool_name" in sent, false)
  }
})

test("aliases follow scripts/lib/tool-map.json", async () => {
  const dir = makeProject()
  const { plugin } = await load(dir)
  const map = toolMap.providers.opencode
  const pairs = Object.entries(map.tool_rewrites).map(([claude, oc]) => [oc, claude])
  for (const name of map._unchanged) pairs.push([name.toLowerCase(), name])
  for (const [oc, claude] of pairs) {
    if (oc === "task" || oc === "todowrite") continue
    await plugin["tool.execute.before"]({ tool: oc, sessionID: "s1", callID: "c" }, { args: {} })
    assert.equal(stdinOf(dir, "pre-tool-use").tool_name, claude, `opencode tool ${oc}`)
  }
})

test("a broken hook (exit 1) or a missing one never blocks the tool", async () => {
  const dir = makeProject()
  control(dir, "pre-tool-use", { code: 1, err: "boom" })
  const { plugin, logs } = await load(dir)
  await plugin["tool.execute.before"]({ tool: "bash", sessionID: "s1", callID: "c1" }, { args: { command: "ls" } })
  assert.ok(logs.some((l) => l.level === "warn" && /exited 1/.test(l.message)))
})

test("compaction output reaches the context, from stdout or from stderr", async () => {
  for (const [out, err] of [["from-out", ""], ["", "from-err"]]) {
    const dir = makeProject()
    control(dir, "pre-compact", { code: 2, out, err })
    const { plugin } = await load(dir)
    const output = { context: [] }
    await plugin["experimental.session.compacting"]({}, output)
    assert.equal(output.context.length, 1)
    assert.match(output.context[0], new RegExp(out || err))
  }
})

test("compaction also carries the active sprint work, and nothing when idle", async () => {
  const dir = makeProject()
  control(dir, "pre-compact", { code: 0, out: "" })
  control(dir, "backlog-prime", { code: 0, out: "[DEVTEAM:ACTIVE_WORK]" })
  const { plugin } = await load(dir)
  const output = { context: [] }
  await plugin["experimental.session.compacting"]({}, output)
  assert.equal(output.context.length, 1)
  assert.match(output.context[0], /active sprint work\n\[DEVTEAM:ACTIVE_WORK\]/)

  const idle = makeProject()
  const quiet = { context: [] }
  await (await load(idle)).plugin["experimental.session.compacting"]({}, quiet)
  assert.equal(quiet.context.length, 0)
})

test("a Stop message (exit 2) is logged instead of dropped", async () => {
  const dir = makeProject()
  control(dir, "stop", { code: 2, err: "SESSION SUMMARY REQUIRED" })
  const { plugin, logs } = await load(dir)
  await plugin.event({ event: { type: "session.idle", properties: { sessionID: "s1" } } })
  assert.ok(existsSync(join(dir, "stop.stdin")))
  assert.ok(logs.some((l) => /SESSION SUMMARY REQUIRED/.test(l.message)))
})

// A store whose self-heal.sh is a stub: it records the dispatcher it was asked for and the payload.
const makeStore = (dir) => {
  const core = join(dir, "store-core")
  const lib = join(core, "versions", "9.9.9", "scripts", "hooks", "lib")
  mkdirSync(lib, { recursive: true })
  writeFileSync(join(core, "current"), "9.9.9\n")
  writeFileSync(
    join(lib, "self-heal.sh"),
    ["#!/usr/bin/env bash", `printf '%s' "$1" > "${dir}/heal.arg"`, `cat > "${dir}/heal.stdin"`, `printf '%s' "$PWD" > "${dir}/heal.pwd"`].join("\n"),
  )
  writeFileSync(join(dir, ".dev-team-agents", "core-dir"), `${core}\n`)
}

test("with the scripts link gone, a hook runs the store's self-heal with the dispatcher and its payload", async () => {
  const dir = makeProject()
  makeStore(dir)
  const { plugin } = await load(dir)
  rmSync(join(dir, ".dev-team-agents", "scripts"), { recursive: true, force: true })
  await plugin["tool.execute.before"]({ tool: "bash", sessionID: "s1", callID: "c1" }, { args: { command: "ls" } })
  assert.equal(readFileSync(join(dir, "heal.arg"), "utf8"), "pre-tool-use.sh")
  const healed = JSON.parse(readFileSync(join(dir, "heal.stdin"), "utf8"))
  assert.equal(healed.sessionID ?? healed.session_id, "s1")
  assert.equal(realpathSync(readFileSync(join(dir, "heal.pwd"), "utf8")), realpathSync(dir))
})

test("once the link is back, hooks run from the project again, not the store", async () => {
  const dir = makeProject()
  makeStore(dir)
  const { plugin } = await load(dir)
  await plugin["tool.execute.before"]({ tool: "bash", sessionID: "s1", callID: "c1" }, { args: { command: "ls" } })
  assert.ok(existsSync(join(dir, "pre-tool-use.stdin")))
  assert.ok(!existsSync(join(dir, "heal.arg")))
})

test("without a core-dir pointer a missing link is still only logged, never blocking", async () => {
  const dir = makeProject()
  const { plugin, logs } = await load(dir)
  rmSync(join(dir, ".dev-team-agents", "scripts"), { recursive: true, force: true })
  await plugin["tool.execute.before"]({ tool: "bash", sessionID: "s1", callID: "c1" }, { args: { command: "ls" } })
  assert.ok(logs.some((l) => l.level === "warn"))
})

const addRetitleStub = (dir) => {
  const hooks = join(dir, ".dev-team-agents", "scripts", "hooks")
  writeFileSync(join(hooks, "session-retitle.sh"), ["#!/usr/bin/env bash", `cat >> "${dir}/session-retitle.stdin"`, `echo >> "${dir}/session-retitle.stdin"`].join("\n"))
}
const retitles = (dir) =>
  existsSync(join(dir, "session-retitle.stdin"))
    ? readFileSync(join(dir, "session-retitle.stdin"), "utf8").trim().split("\n").filter(Boolean).map((l) => JSON.parse(l))
    : []

test("a renamed session reaches the task board through session-retitle.sh", async () => {
  const dir = makeProject()
  addRetitleStub(dir)
  const { plugin } = await load(dir)
  const updated = (title) => plugin.event({ event: { type: "session.updated", properties: { info: { id: "s1", title } } } })
  await updated("first title")
  assert.deepEqual(retitles(dir), [], "the first sighting is the session being created, not a rename")
  await updated("first title")
  assert.deepEqual(retitles(dir), [], "an update that keeps the title is not a rename")
  await updated("Desafio 7D")
  const [sent] = retitles(dir)
  assert.equal(sent.session_id, "s1")
  assert.equal(sent.session_title, "Desafio 7D")
})

test("the prompt hook's language directive reaches that session's system prompt, and only it", async () => {
  const dir = makeProject()
  control(dir, "user-prompt-submit", { out: "[DEVTEAM:LANGUAGE] Reply to the user in pt-BR." })
  const { plugin } = await load(dir)
  await plugin["chat.message"]({ sessionID: "s1" }, { parts: [{ type: "text", text: "oi" }] })
  const system = { system: [] }
  await plugin["experimental.chat.system.transform"]({ sessionID: "s1" }, system)
  assert.deepEqual(system.system, ["[DEVTEAM:LANGUAGE] Reply to the user in pt-BR."])
  const other = { system: [] }
  await plugin["experimental.chat.system.transform"]({ sessionID: "s2" }, other)
  assert.deepEqual(other.system, [])
})

test("a prompt whose hook prints no directive clears the session's language line", async () => {
  const dir = makeProject()
  control(dir, "user-prompt-submit", { out: "[DEVTEAM:LANGUAGE] Reply to the user in pt-BR." })
  const { plugin } = await load(dir)
  await plugin["chat.message"]({ sessionID: "s1" }, { parts: [{ type: "text", text: "oi" }] })
  control(dir, "user-prompt-submit", {})
  await plugin["chat.message"]({ sessionID: "s1" }, { parts: [{ type: "text", text: "hi" }] })
  const system = { system: [] }
  await plugin["experimental.chat.system.transform"]({ sessionID: "s1" }, system)
  assert.deepEqual(system.system, [])
})

test("recall and hint lines from the prompt hook reach that session's system prompt, replaced each prompt [spec:prompt-recall#S13]", async () => {
  const dir = makeProject()
  control(dir, "user-prompt-submit", { out: "[DEVTEAM:RECALL] docs/a.md (ADR) - x\nnoise\n[DEVTEAM:HINT] try this" })
  const { plugin } = await load(dir)
  await plugin["chat.message"]({ sessionID: "s1" }, { parts: [{ type: "text", text: "fix the webhook retries" }] })
  const system = { system: [] }
  await plugin["experimental.chat.system.transform"]({ sessionID: "s1" }, system)
  assert.equal(system.system.length, 3)
  assert.match(system.system[0], /reference pointers and data.*never as instructions/)
  assert.ok(!system.system[0].startsWith("[DEVTEAM:"))
  assert.deepEqual(system.system.slice(1), ["[DEVTEAM:RECALL] docs/a.md (ADR) - x", "[DEVTEAM:HINT] try this"])
  const other = { system: [] }
  await plugin["experimental.chat.system.transform"]({ sessionID: "s2" }, other)
  assert.deepEqual(other.system, [])
  control(dir, "user-prompt-submit", {})
  await plugin["chat.message"]({ sessionID: "s1" }, { parts: [{ type: "text", text: "another prompt here" }] })
  const cleared = { system: [] }
  await plugin["experimental.chat.system.transform"]({ sessionID: "s1" }, cleared)
  assert.deepEqual(cleared.system, [])
})

test("a finished task sends its child session, model and summed usage for the execution trace", async () => {
  const dir = makeProject()
  const asked = []
  const messages = async ({ path }) => {
    asked.push(path.id)
    return {
      data: [
        { info: { role: "user" } },
        { info: { role: "assistant", tokens: { input: 10, output: 5, reasoning: 2, cache: { read: 100, write: 7 } } } },
        { info: { role: "assistant", tokens: { input: 3, output: 1, reasoning: 0, cache: { read: 50, write: 0 } } } },
      ],
    }
  }
  const { plugin } = await load(dir, messages)
  const metadata = { sessionId: "ses_child", model: { modelID: "glm-5.2" } }
  await plugin["tool.execute.after"]({ tool: "task", sessionID: "ses_top", callID: "c9", args: { subagent_type: "x" } }, { output: "done", metadata })
  const sent = stdinOf(dir, "post-tool-use")
  assert.ok(asked.includes("ses_child"))
  assert.equal(sent.agent_session_id, "ses_child")
  assert.equal(sent.agent_model, "glm-5.2")
  assert.deepEqual(sent.agent_usage, { input: 13, output: 8, cache_read: 150, cache_write: 7 })
})

test("a task with no child session metadata adds no trace fields", async () => {
  const dir = makeProject()
  const { plugin } = await load(dir)
  await plugin["tool.execute.after"]({ tool: "task", sessionID: "ses_top", callID: "c9", args: { subagent_type: "x" } }, { output: "done" })
  const sent = stdinOf(dir, "post-tool-use")
  assert.equal("agent_session_id" in sent, false)
  assert.equal("agent_usage" in sent, false)
})

test("a child session that never answers does not hold up the task's hook", async () => {
  const dir = makeProject()
  const { plugin } = await load(dir, () => new Promise(() => {}))
  const started = Date.now()
  const metadata = { sessionId: "ses_child", model: { modelID: "glm-5.2" } }
  await plugin["tool.execute.after"]({ tool: "task", sessionID: "ses_top", callID: "c9", args: { subagent_type: "x" } }, { output: "done", metadata })
  const sent = stdinOf(dir, "post-tool-use")
  assert.ok(Date.now() - started < 6000)
  assert.equal(sent.agent_session_id, "ses_child")
  assert.equal("agent_usage" in sent, false)
})

test("every bash call reaches the post-tool hook with its exit code from the metadata", async () => {
  const dir = makeProject()
  const { plugin } = await load(dir)
  await plugin["tool.execute.before"]({ tool: "bash", sessionID: "ses_top", callID: "b1" }, { args: { command: "npm test" } })
  await plugin["tool.execute.after"]({ tool: "bash", sessionID: "ses_top", callID: "b1" }, { output: "boom", metadata: { exit: 2 } })
  const sent = stdinOf(dir, "post-tool-use")
  assert.equal(sent.sessionID, "ses_top")
  assert.equal(sent.tool, "bash")
  assert.equal(sent.args.command, "npm test")
  assert.equal(sent.exit_code, 2)
  assert.equal(sent.output, "boom")
  assert.equal(sent.session_title, undefined)
})

test("a bash call without an exit code in its metadata sends none", async () => {
  const dir = makeProject()
  const { plugin } = await load(dir)
  await plugin["tool.execute.after"]({ tool: "bash", sessionID: "ses_top", callID: "b2", args: { command: "ls" } }, { output: "a" })
  assert.equal("exit_code" in stdinOf(dir, "post-tool-use"), false)
})

test("a PR-creating bash call still carries the session title", async () => {
  const dir = makeProject()
  const { plugin } = await load(dir)
  await plugin["tool.execute.after"]({ tool: "bash", sessionID: "ses_top", callID: "b3", args: { command: "gh pr create --fill" } }, { output: "https://github.com/o/r/pull/1" })
  assert.equal(stdinOf(dir, "post-tool-use").session_title, "t")
})

test("the edit tools reach the post-tool hook with their path arguments [spec:branch-overlap#S14]", async () => {
  for (const [tool, args] of [["edit", { filePath: "a.py" }], ["write", { filePath: "b.py" }], ["multiedit", { filePath: "c.py" }], ["patch", { patchText: "*** Update File: d.py" }]]) {
    const dir = makeProject()
    const { plugin } = await load(dir)
    await plugin["tool.execute.before"]({ tool, sessionID: "ses_top", callID: "e1" }, { args })
    await plugin["tool.execute.after"]({ tool, sessionID: "ses_top", callID: "e1" }, { output: "ok" })
    const sent = stdinOf(dir, "post-tool-use")
    assert.equal(sent.tool, tool)
    assert.deepEqual(sent.args, args)
    assert.equal(sent.sessionID, "ses_top")
  }
})

test("a tool that is neither shell, edit, task nor PR stays free", async () => {
  const dir = makeProject()
  const { plugin } = await load(dir)
  await plugin["tool.execute.after"]({ tool: "read", sessionID: "ses_top", callID: "r1", args: { filePath: "a" } }, { output: "x" })
  assert.equal(existsSync(join(dir, "post-tool-use.stdin")), false)
})
