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

  _putenv_s("FAKE_DEVTEAM_SCENARIO", value);
}

int main(int argc, char **argv) {
  applyScenarioOverride();

  char **childArgv = (char **)malloc(sizeof(char *) * (size_t)(argc + 2));
  if (childArgv == NULL) return 70; /* EX_SOFTWARE */
  childArgv[0] = NODE_PATH;
  childArgv[1] = SCRIPT_PATH;
  for (int i = 1; i < argc; i++) childArgv[i + 1] = argv[i];
  childArgv[argc + 1] = NULL;

  /* No shell, ever — the same rule `invoke.ts` states for its own spawn. The `v` in
     `_spawnve` is an argv vector, so nothing here is ever parsed by a command
     interpreter.

     The `e` is the environment, passed **explicitly** as `_environ` rather than left to
     `_spawnv`'s documented inheritance. That inheritance is what the first version
     relied on, and the scenarios that travel by environment variable — the handshake's
     — arrived unset at the fixture while the ones that travel by argv arrived fine. The
     difference between "documented to inherit" and "observably inherited" is not worth
     re-litigating inside a test fixture: naming the block leaves nothing to a CRT
     startup detail. `applyScenarioOverride` above has already mutated `_environ` if a
     sibling file asked it to. */
  intptr_t status = _spawnve(_P_WAIT, NODE_PATH, (const char *const *)childArgv,
                             (const char *const *)_environ);
  free(childArgv);

  if (status == -1) {
    fprintf(stderr, "launcher: failed to run node (%s): %s\n", NODE_PATH, strerror(errno));
    return 70;
  }
  return (int)status;
}
