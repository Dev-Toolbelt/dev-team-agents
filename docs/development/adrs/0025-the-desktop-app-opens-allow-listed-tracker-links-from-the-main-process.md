# ADR-0025: The desktop app opens allow-listed tracker links from the main process

**Date:** 2026-10-01  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers

## Context

The task board displays PR/MR badges and issue references. Users expect to open them in a browser. The desktop app is untrusted code (ADR-0015): the renderer cannot be trusted to build URLs, and Electron's IPC layer must be the narrowest possible gate. The app also needs to ensure users cannot be tricked into opening arbitrary URLs through a compromised or malicious recorded link.

Qualifies ADR-0015 ("The desktop app runs as a CLI client") and security.ts window-open rules: links are opened only through one IPC handler with an allow-list, not through renderer `<a href>` tags or the unrestricted `setWindowOpenHandler`.

## Decision

**IPC endpoint takes only ids, main process looks up and validates.** The renderer sends `{project_id, session_id, task_key|null, link: {type:"pr"|"ref", index}}` (all strings/integers) — never a URL. The main process looks the link up in its own snapshot (taskBoard supervisor), parses it with `new URL()`, and validates:

- Protocol exactly `https:`
- Hostname canonical form (lowercase, no username/password, default port only)
- Hostname matches a configured kind in the project's `link_hosts` allow-list
- Path matches the exact regex shape for that kind:
  - GitHub PR/issue: `^/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/([A-Za-z0-9._-]{1,100})/(pull|issues)/([1-9][0-9]{0,9})$`
  - GitLab MR: `^/((?:[A-Za-z0-9_.-]{1,255}/){1,20}[A-Za-z0-9_.-]{1,255})/-/merge_requests/([1-9][0-9]{0,9})$`
  - Jira: `^<escaped site path>/browse/([A-Z][A-Z0-9_]{1,9})-([1-9][0-9]{0,9})$` (site path is the configured Jira `base_path` from `link_hosts`)
- Number/key in path matches the snapshot's `pr.number` / `ref.key`
- No query string or fragment

Only valid URLs are passed to `shell.openExternal(canonical)` with `activate: true`. Invalid links are silently refused (logged).

**`link_hosts` is dynamic, checked on every IPC.** It combines:
- GitHub: configured web host (derived from account `api_url`) + github.com
- Jira: configured site host
- GitLab: gitlab.com + any self-hosted host that is a git remote's hostname at read time

A mark (PR/MR/ref) never adds a host to the list — it is a consistency check inside the CLI trust boundary, not a second trust anchor. If a remote is deleted or a Jira site is reconfigured, links to it stop validating.

**Renderer security contract.** IPC handler enforces:
- Sender is the app's main frame only
- Ids are strings matching existing id patterns, safe integers 0..63, no extra keys
- `setWindowOpenHandler` stays deny — the renderer cannot open any window

## Consequences

### Positive
- Users can click badges to open tracker links in their browser without copy-pasting
- All link validation happens in trusted code (the main process)
- Configuration changes (removing a remote, updating Jira site) are immediately reflected — no stale links in the recorded state
- No second URL source: the link is built from parts, validated once, and used once

### Negative
- Renderer cannot open links directly — adds IPC overhead for a common action (mitigation: single call, no back-and-forth)

### Neutral
- Breadth of validation regex is wider than a URL scheme check alone, catching more false-positives (mitigation: recorded links are verified before storing)

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Scheme test (`https:` prefix) | Accepts `https://github.com@evil.tld/issue` and `https://evil.tld/…` if the domain spoofs github.com; hostname validation is mandatory |
| Renderer builds and supplies URL | Untrusted code; violates ADR-0015's principle that the app never trusts renderer input for external actions |
| `<a target=_blank>` in the task card | Still requires `setWindowOpenHandler` to be enabled, which means any link anywhere can escape the app; one handler for all external links is the right gate |
| Flat allow-list of full URLs | Does not adapt when config changes (remote removed, Jira site updated); forces the CLI to store URLs, which limits the ability to detect stale references |
| Store URLs as-is, validate shape on read only | Does not guard against a compromised record; the app must validate even recorded links |

## Further Reading

- ADR-0015: The desktop app's stack and its operating rules as a CLI client
- ADR-0018 § SECURITY AMENDMENTS: PR/MR Created column security rules (URL parsing, parts-not-URLs, path shapes, repo check)
