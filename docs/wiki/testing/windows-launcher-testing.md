# Windows fixtures need a compiled PE, and a hand-escaped command line

**Origin:** closing the Windows CI leg for the app suite | 2026-09-29
**Tags:** windows, launcher, fixture, spawn, shell false, CreateProcessA, _spawnv, argv quoting, PE, .exe, .scenario, PASS_THROUGH_ENV, CVE-2024-27980

> A POSIX shebang fixture can never be the spawn target on Windows, so the fake CLI is a real PE compiled at test time. Four things about it are not guessable, and each one cost a CI round.

---

## Why a compiled binary at all

`app/src/cli/invoke.ts` spawns the resolved CLI with `shell: false`. That is a security
property, not a convenience — see its header and CVE-2024-27980 — and it is never relaxed
for a test. Windows honours no `#!` line and has no association for an extensionless file
or a `.mjs`, so the POSIX fixture script the suite uses everywhere else cannot be the thing
Windows executes.

`app/test/fixtures/launcher.c` is that thing: a real PE whose only job is to run
`node <script> <args…>` and hand back the child's exit code. It is compiled at test time by
`launcher-build.ts` (probe order `cc`, `gcc`, `clang`, `cl` — `cc` is what wins on
`windows-latest`) and **never checked in**. No compiler on the host means those tests skip;
it never turns the suite red for a toolchain reason.

## The four traps

### `CreateProcessA` over a hand-escaped command line, not `_spawnv`

`_spawnv` re-joins the argument vector into one command line **without escaping an embedded
double quote**. `performHandshake` passes `compat --client {"project":1,…}`, so the child
received mangled JSON, `JSON.parse` threw, and the fixture died writing nothing — which the
handshake could only report as `state: 'unknown'`. The launcher now builds the command line
itself, quoting by the documented CRT rule (quote only when empty or holding space/tab/quote;
double the backslashes preceding a quote or the closing quote; escape the quote), and passes
it to `CreateProcessA` with `lpApplicationName` set to the absolute node path.

**What named the cause:** the two failing scenarios were precisely and only the two that
read an argv element. Every scenario that ignores argv passed.

### `lpApplicationName` must carry the extension

`CreateProcess` "must include the file name extension; no default extension is assumed" — a
valid PE named `devteam` is simply not executable. `plant()` in `resolve.test.ts` therefore
writes `devteam.exe` on a real Windows host, which is also what `executableNames('win32')`
lists first. Note that most resolver tests still *simulate* `platform: 'win32'` while running
on POSIX, so the planted name and the simulated platform are two different decisions in the
same test.

### The environment must be `NULL` — inherit

Passing an explicit environment block to `CreateProcessA` was tried, on the assumption that
inheritance was not working. It took the Windows leg from 8 failures to **18**: the suites
that regressed were exactly the argv-scenario ones. The launcher passes `NULL` and carries a
comment saying not to reintroduce a block.

This is why the scenario cannot travel as an environment variable in the first place:
`PASS_THROUGH_ENV` in `invoke.ts` is a strict allowlist and a security boundary, and it is
never widened to carry a test-only variable. `resolveDevteam`'s `probe()` forwards no
environment at all.

### The `.scenario` name appends to the *whole* filename

`plant()` writes `${path}.scenario`, so `devteam.exe` looks for **`devteam.exe.scenario`** —
not `devteam.scenario`. The launcher's first version stripped the extension before appending,
and the mismatch meant no scenario was ever found. Two rules that must agree are better
written as the one rule that needs no parsing.

The file is read by the **launcher**, not by the app: `applyScenarioOverride()` puts its
trimmed contents into `FAKE_DEVTEAM_SCENARIO` (via both `_putenv_s` and
`SetEnvironmentVariableA`) before spawning node. Nothing in `src/` knows this file exists.

## The method lesson

Two of these fixes were made by inferring from documentation, and **both were wrong** — one
doubled the failure count. What worked was extracting the pure logic, the argv quoting, into
a standalone C file and exercising it on macOS against the real JSON case plus four edge
cases before pushing. Prefer that over reasoning about a platform you cannot run.

## One remaining gap that is not a platform absence

Of the 26 tests still skipped on Windows, all but one are genuine platform absences (POSIX
mode bits, SIGTERM, `HOMEBREW_PREFIX`, the python-shebang real-CLI test). The exception:
`resolve.ts` refuses a `.cmd`/`.bat` candidate because Node will not spawn one without a
shell, and that refusal has **never been exercised against a real winget shim** — which is
exactly what a winget install produces.

## References

- `app/test/fixtures/launcher.c` — the source; its header carries the same warnings at the call sites
- `app/test/fixtures/launcher-build.ts` — compiler probe, and the manifest the workers read
- `app/test/resolve.test.ts` — `plant()`, the `.exe` name and the `.scenario` sibling
- `app/test/handshake.test.ts` — the same planting, for the scenarios that read argv
- `app/README.md` — running the suite locally
