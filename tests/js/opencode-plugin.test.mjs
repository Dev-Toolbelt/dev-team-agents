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
  for (const name of ["session-start", "pre-tool-use", "post-tool-use", "user-prompt-submit", "pre-compact", "stop"]) {
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

const load = async (dir) => {
  const logs = []
  const client = {
    app: { log: async ({ body }) => void logs.push(body) },
    session: { messages: async () => ({ data: [] }), get: async () => ({ data: { title: "t" } }) },
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
