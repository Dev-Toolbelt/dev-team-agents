/*
 * Windows launcher for the POSIX-shebang fake `devteam` CLI fixtures.
 *
 * `app/src/cli/invoke.ts` spawns the resolved CLI path directly with `shell: false` —
 * a security property, not a preference (see that file's header and CVE-2024-27980) —
 * and Windows honours no `#!` line and has no association for an extensionless file or
 * a `.mjs`. A POSIX fixture script can therefore never be the spawn target on Windows.
 * This is a real Windows PE, compiled from source at test time (never checked in —
 * see `launcher-build.ts`), whose only job is to run `node <script> <args...>` and
 * hand back the child's exit code, so `spawn(path, args, { shell: false })` has
 * something it can actually execute.
 *
 * `NODE_PATH` and `SCRIPT_PATH` are baked in at compile time via -D defines, not
 * looked up on PATH or in the environment: this binary is copied into many
 * directories by `resolve.test.ts`, and it inherits only the minimal, allowlisted
 * environment `invoke.ts`'s `PASS_THROUGH_ENV` lets through (that allowlist is a
 * security boundary and is never patched to carry a test-only variable) — so a PATH
 * lookup here would make the fixture depend on the very PATH some tests deliberately
 * empty or reorder.
 *
 * argv[1..] and the process environment are forwarded unchanged, which is what lets
 * `FAKE_DEVTEAM_SCENARIO` — passed by tests that call `invokeDevteam` with an explicit
 * `env` option, which bypasses the allowlist by design — reach the fixture. One
 * exception: `resolve.test.ts`'s `plant()` cannot inject an env var at all, because its
 * candidate is probed by `resolveDevteam`, which never forwards one (see `resolve.ts`'s
 * `probe()`). So `plant()` instead writes a sibling `<this-exe-without-extension>
 * .scenario` text file next to the copied launcher; if one is found, its trimmed
 * contents become `FAKE_DEVTEAM_SCENARIO` before the child is spawned. This mirrors
 * what the POSIX fixture does with a `#!/bin/sh` wrapper that bakes the scenario into
 * its own `exec` line — the same idea, as a file next to the binary instead of shell
 * syntax.
 */

#include <windows.h>
#include <process.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

#ifndef NODE_PATH
#error "NODE_PATH must be defined at compile time (-DNODE_PATH=\"...\")"
#endif
#ifndef SCRIPT_PATH
#error "SCRIPT_PATH must be defined at compile time (-DSCRIPT_PATH=\"...\")"
#endif

/* `GetModuleFileNameA`, not argv[0]: argv[0] reflects however the caller chose to
   invoke this process, which is not a promise worth depending on, while this always
   names the actual running executable. */
static void applyScenarioOverride(void) {
  char self[MAX_PATH];
  DWORD n = GetModuleFileNameA(NULL, self, sizeof(self));
  if (n == 0 || n >= sizeof(self)) return;

  /* Appended to the whole name — `devteam.exe` looks for `devteam.exe.scenario` — and
     not to the name with its extension stripped. Stripping was the first version and it
     was wrong in a way that cost a CI round: `plant()` writes `${path}.scenario` from
     the path it planted, so the two rules have to be the same rule, and the one that
     needs no parsing is the one that cannot disagree. */
  char path[MAX_PATH + 16];
  size_t len = strlen(self);
  memcpy(path, self, len + 1);
  strcat(path, ".scenario");

  FILE *f = fopen(path, "rb");
  if (f == NULL) return; /* no override — the ordinary case */

  char value[4096];
  size_t read = fread(value, 1, sizeof(value) - 1, f);
  fclose(f);
  value[read] = '\0';
  while (read > 0 && (value[read - 1] == '\n' || value[read - 1] == '\r' || value[read - 1] == ' ')) {
    value[--read] = '\0';
  }
  if (read == 0) return;

  /* Both: `_putenv_s` for anything in this process that reads the CRT copy, and
     `SetEnvironmentVariableA` for the OS block `CreateProcess` actually hands the child.
     Whether the first updates the second is a CRT implementation detail, and this is one
     round of CI per wrong guess. */
  _putenv_s("FAKE_DEVTEAM_SCENARIO", value);
  SetEnvironmentVariableA("FAKE_DEVTEAM_SCENARIO", value);
}

/* Append one argument, quoted the way the CRT's command-line parser expects.
   Straight out of the documented rule: quote only when the argument is empty or holds a
   space, tab or quote; double every backslash that immediately precedes a quote (or the
   closing quote); escape an embedded quote itself. Getting this subtly wrong is the
   classic Windows argv bug, and a JSON argument — quotes on every key — hits every branch
   of it at once. */
static void appendQuoted(char *out, size_t *len, const char *arg) {
  size_t n = strlen(arg);
  int needsQuotes = (n == 0);
  for (size_t i = 0; i < n && !needsQuotes; i++) {
    if (arg[i] == ' ' || arg[i] == '\t' || arg[i] == '"') needsQuotes = 1;
  }
  if (!needsQuotes) {
    memcpy(out + *len, arg, n);
    *len += n;
    return;
  }
  out[(*len)++] = '"';
  for (size_t i = 0; i < n; i++) {
    size_t slashes = 0;
    while (i < n && arg[i] == '\\') { slashes++; i++; }
    if (i == n) {
      /* Trailing backslashes would otherwise escape the closing quote. */
      for (size_t s = 0; s < slashes * 2; s++) out[(*len)++] = '\\';
      break;
    }
    if (arg[i] == '"') {
      for (size_t s = 0; s < slashes * 2 + 1; s++) out[(*len)++] = '\\';
    } else {
      for (size_t s = 0; s < slashes; s++) out[(*len)++] = '\\';
    }
    out[(*len)++] = arg[i];
  }
  out[(*len)++] = '"';
}

/* `node <script> <args...>`, escaped. Caller frees. */
static char *buildCommandLine(int argc, char **argv) {
  size_t budget = strlen(NODE_PATH) + strlen(SCRIPT_PATH);
  for (int i = 1; i < argc; i++) budget += strlen(argv[i]);
  /* Every character can at worst double, plus two quotes and a separator per argument. */
  budget = budget * 2 + (size_t)(argc + 2) * 4 + 1;

  char *out = (char *)malloc(budget);
  if (out == NULL) return NULL;
  size_t len = 0;
  appendQuoted(out, &len, NODE_PATH);
  out[len++] = ' ';
  appendQuoted(out, &len, SCRIPT_PATH);
  for (int i = 1; i < argc; i++) {
    out[len++] = ' ';
    appendQuoted(out, &len, argv[i]);
  }
  out[len] = '\0';
  return out;
}

int main(int argc, char **argv) {
  applyScenarioOverride();

  /* Built by hand, and this is the whole reason `_spawnv` is not used below.
     `_spawnv` re-joins the vector into one command line without escaping an embedded
     double quote, so an argument that carries JSON — `--client {"project":1,…}`, which
     is exactly what `performHandshake` passes — reached the child mangled. The child
     then threw on `JSON.parse` and died writing nothing, which the handshake could only
     report as "no answer". The two tests that failed were precisely and only the two
     that parse an argv element; every scenario that ignores argv passed, which is what
     named the cause.

     The escaping below is the algorithm the CRT's own parser is the inverse of: quote
     only when needed, double the backslashes that precede a quote, and escape the quote
     itself. */
  char *commandLine = buildCommandLine(argc, argv);
  if (commandLine == NULL) return 70; /* EX_SOFTWARE */

  /* No shell, ever — the same rule `invoke.ts` states for its own spawn.
     `lpApplicationName` is the absolute NODE_PATH, so nothing resolves a name through
     PATH or a command interpreter; only the already-escaped `commandLine` is parsed, and
     only by the child's own CRT.

     `bInheritHandles` must be TRUE: Node hands this process piped stdio, and the child is
     what actually writes the JSON the test reads. The environment is NULL, which means
     inherit — measured, not assumed: passing an explicit block was tried and broke the
     suites that had been passing. `applyScenarioOverride` above has already put its value
     into that inherited block. */
  STARTUPINFOA si;
  PROCESS_INFORMATION pi;
  memset(&si, 0, sizeof(si));
  si.cb = sizeof(si);
  memset(&pi, 0, sizeof(pi));

  if (!CreateProcessA(NODE_PATH, commandLine, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi)) {
    fprintf(stderr, "launcher: CreateProcess failed for %s (error %lu)\n", NODE_PATH,
            (unsigned long)GetLastError());
    free(commandLine);
    return 70;
  }
  free(commandLine);

  WaitForSingleObject(pi.hProcess, INFINITE);
  DWORD code = 1;
  GetExitCodeProcess(pi.hProcess, &code);
  CloseHandle(pi.hProcess);
  CloseHandle(pi.hThread);
  return (int)code;
}
