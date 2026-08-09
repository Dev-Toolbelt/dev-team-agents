---
name: tool-installers
description: Cross-OS install/verify knowledge base for the closed tool set /devteam:install supports.
---

# Tool Installers

Cross-OS knowledge base backing `/devteam:install`. Covers **exactly** the tools in the table below — this is a closed list, not a general "install anything" reference. Adding a tool here is a deliberate change to the command's allowlist (`commands/install.md`), never an implicit one.

Every entry follows the same shape: **detect** (already installed?) → **install** (per OS) → **verify** (re-run detect). Windows always routes through WSL — no native-Windows package manager commands are used for the dev-tool set, keeping one Linux code path instead of two.

---

## Supported Tools

| Tool | Gain | Depends on |
|------|------|------------|
| `rg` (ripgrep) | Faster, lower-token alternative to `grep -r` — smaller output, respects `.gitignore` | — |
| `fd` | Faster, `.gitignore`-aware alternative to `find` | — |
| `jq` | JSON field extraction without reading whole files; also required by Graphify | — |
| `ast-grep` | Structural code search/rewrite by AST pattern instead of regex — targets exact syntax nodes for large refactors | — |
| `tokei` | Instant codebase size/complexity stats without an agent reading the whole tree | — |
| `delta` | Readable git diff pager for human review of agent-generated diffs/PRs | — |
| `graphify` | Knowledge-graph codebase navigation — the largest single token-economy win in this repo's toolset | `jq` |

---

## OS Detection

```bash
uname -s
```

| Output | OS |
|--------|-----|
| `Darwin` | macOS |
| `Linux` | Linux or WSL |
| `MINGW*` / `MSYS*` / other | Windows — see below |

**Windows handling:** check for WSL first —

```bash
wsl --status 2>/dev/null || echo "WSL_NOT_FOUND"
```

- **WSL active** → run every install/verify command inside it (`wsl bash -c "<command>"`); follow the Linux column below for everything.
- **WSL not found** → stop and tell the user: "Windows without WSL is not supported for these installs. Activate WSL first: https://learn.microsoft.com/en-us/windows/wsl/install — then re-run `/devteam:install`."

Also distinguish Debian/Ubuntu (`apt`) from Fedora/RHEL (`dnf`) on Linux:

```bash
command -v apt-get >/dev/null 2>&1 && echo "Linux: apt" || { command -v dnf >/dev/null 2>&1 && echo "Linux: dnf" || echo "Linux: unknown package manager"; }
```

---

## rg (ripgrep)

- **Detect:** `command -v rg >/dev/null 2>&1 && rg --version || echo NOT_FOUND`
- **Install:**

| OS | Command |
|----|---------|
| macOS | `brew install ripgrep` |
| Debian/Ubuntu (WSL incl.) | `sudo apt-get install -y ripgrep` |
| Fedora/RHEL | `sudo dnf install -y ripgrep` |

- **Verify:** re-run detect.

## fd

- **Detect:** `command -v fd >/dev/null 2>&1 && fd --version || (command -v fdfind >/dev/null 2>&1 && echo "found as fdfind")|| echo NOT_FOUND`
- **Install:**

| OS | Command |
|----|---------|
| macOS | `brew install fd` |
| Debian/Ubuntu (WSL incl.) | `sudo apt-get install -y fd-find` |
| Fedora/RHEL | `sudo dnf install -y fd-find` |

- **Note:** apt/dnf install the binary as `fdfind`, not `fd` (name clash with an existing Debian package). After install, offer to create `~/.local/bin/fd` as a symlink to `fdfind` so it matches the tool's usual invocation: `mkdir -p ~/.local/bin && ln -s "$(command -v fdfind)" ~/.local/bin/fd` — ask before writing to the user's `PATH`-adjacent directory, do not do it silently.
- **Verify:** re-run detect.

## jq

- **Detect:** `command -v jq >/dev/null 2>&1 && jq --version || echo NOT_FOUND`
- **Install:**

| OS | Command |
|----|---------|
| macOS | `brew install jq` |
| Debian/Ubuntu (WSL incl.) | `sudo apt-get install -y jq` |
| Fedora/RHEL | `sudo dnf install -y jq` |

- **Verify:** re-run detect.

## ast-grep

- **Detect:** `command -v ast-grep >/dev/null 2>&1 && ast-grep --version || echo NOT_FOUND`
- **Install:**

| OS | Command |
|----|---------|
| macOS | `brew install ast-grep` |
| Debian/Ubuntu (WSL incl.) | No apt package — `cargo install ast-grep --locked` (requires Rust/cargo; if missing, point the user at https://rustup.rs first and wait for confirmation) |
| Fedora/RHEL | No dnf package — same `cargo install ast-grep --locked` path |

- **Verify:** re-run detect.

## tokei

- **Detect:** `command -v tokei >/dev/null 2>&1 && tokei --version || echo NOT_FOUND`
- **Install:**

| OS | Command |
|----|---------|
| macOS | `brew install tokei` |
| Debian/Ubuntu 22.04+ (WSL incl.) | `sudo apt-get install -y tokei` — on older releases without the package, fall back to `cargo install tokei` |
| Fedora/RHEL | `sudo dnf install -y tokei` |

- **Verify:** re-run detect.

## delta (git-delta)

- **Detect:** `command -v delta >/dev/null 2>&1 && delta --version || echo NOT_FOUND`
- **Install:**

| OS | Command |
|----|---------|
| macOS | `brew install git-delta` |
| Debian 12+ / Ubuntu 23.04+ (WSL incl.) | `sudo apt-get install -y git-delta` — on older releases, download the `.deb` from https://github.com/dandavison/delta/releases and `sudo dpkg -i <file>.deb` |
| Fedora/RHEL | `sudo dnf install -y git-delta` |

- **Post-install (optional):** offer to wire it into git — `git config --global core.pager delta` — but only after explicit confirmation, since it changes a global git setting outside the project.
- **Verify:** re-run detect.

## graphify

- **Detect:** `command -v graphify >/dev/null 2>&1 && graphify --version || echo NOT_FOUND`
- **Install:**

| OS | Command |
|----|---------|
| macOS | `brew install graphify` |
| Linux/WSL | `npm install -g graphify` — fallback `pip install graphify` if npm is unavailable |

- **Dependency:** `jq` must also be installed (see above) — install it first if missing.
- **Verify:** re-run detect, then confirm `jq` is present too.
- **After the binary is confirmed working:** hand off to `skills/devops/graphify-setup/SKILL.md` starting at its Step 4 (Infer Project Structure) — that skill owns `graphify.json` generation, hook wiring, `.gitignore` entries, the first build, and the `CLAUDE.md` injection. This skill's job stops at "the binary and its dependency are installed and on PATH."

---

## Elevated Privileges

Any `sudo`/elevated command in the tables above: run it directly first. If it fails on a permission prompt or `sudo` is unavailable non-interactively, report the exact command to the user and wait for their confirmation that they ran it before re-verifying. Never attempt to work around a permission failure by escalating differently (e.g., switching to a root shell) — that decision belongs to the user.
