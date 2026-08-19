# Worktree Docker Isolation

Spin up a **fully isolated Docker Compose stack per worktree** so worktree work
never touches the main project's containers, volumes, networks, or host ports.

> Unified naming rule (see `../SKILL.md` → Key Rules): the Docker project name
> derived here must stay in lockstep with the worktree directory and branch name,
> both built from the same `<context>/<brief-title>` slug.

Applies only when **both** hold:
- `worktree_docker_isolate` is `true` in `.dev-team-agents/user-data/preferences.json`, and
- the project uses Docker Compose (a compose file exists and `docker` is running).

The isolation primitive is Docker Compose's **project name** (`-p` /
`COMPOSE_PROJECT_NAME`), which automatically namespaces containers, networks, and
named volumes. We do **not** rename services by hand.

---

## Step 1 — Detect Docker

```bash
# Compose file present?
ls docker-compose.yml docker-compose.yaml compose.yml compose.yaml 2>/dev/null | head -1
# Docker daemon reachable?
docker info >/dev/null 2>&1 && echo "docker-ok"
```

If either check fails, skip isolation and work without a stack (report why).

---

## Step 2 — Derive the isolated project name

Build a clear, identifiable name from the base project name + the worktree name:

```
<base-project>-wt-<context>-<brief-title>
```

- `<base-project>` = the main compose project name (default: the repo directory
  name, lowercased). Detect the current default:
  ```bash
  basename "$(git rev-parse --show-toplevel)" | tr '[:upper:]' '[:lower:]'
  ```
- Sanitize the whole string to Compose's allowed set: lowercase, `[a-z0-9-]`,
  replace `/` and `_` with `-`.

Example: repo `myapp`, worktree `auth/add-oauth` →
`myapp-wt-auth-add-oauth`. Containers become `myapp-wt-auth-add-oauth-<service>-1`
and volumes `myapp-wt-auth-add-oauth_<volume>` — instantly identifiable and fully
separate from the main stack.

> This name is derived directly from the `<context>/<brief-title>` worktree slug
> (see `../SKILL.md` → Name Format). Never shorten it into an acronym or letter
> code — an isolated stack whose name doesn't say what task it belongs to defeats
> the point of this section.

Export it for every command in this worktree:

```bash
export COMPOSE_PROJECT_NAME="myapp-wt-auth-add-oauth"
```

---

## Step 3 — Generate a ports-off override

Two stacks cannot publish the same host ports. Generate an override **inside the
worktree** that drops published ports for every service, so the isolated stack is
reachable only through its own internal network / `exec`:

```bash
WT=<wt-path>/<context>/<brief-title>
SERVICES=$(docker compose -f "$WT"/docker-compose.yml config --services 2>/dev/null)

{
  echo "# Auto-generated for worktree isolation — do not commit."
  echo "services:"
  for s in $SERVICES; do
    printf '  %s:\n    ports: []\n' "$s"
  done
} > "$WT"/docker-compose.worktree.yml
```

> If a service genuinely must expose a host port, assign a non-conflicting
> offset instead of `[]` — but default to no published ports.

---

## Step 4 — Bring up the isolated stack

Run from inside the worktree, with both files and the isolated project name:

```bash
docker compose \
  -p "$COMPOSE_PROJECT_NAME" \
  -f "$WT"/docker-compose.yml \
  -f "$WT"/docker-compose.worktree.yml \
  up -d
```

Verify:

```bash
docker compose -p "$COMPOSE_PROJECT_NAME" ps
```

---

## Step 5 — Run commands against the isolated stack

```bash
docker compose -p "$COMPOSE_PROJECT_NAME" exec <service> <command>
```

Always pass `-p "$COMPOSE_PROJECT_NAME"`. Never `docker exec` a main-stack
container name for worktree work.

---

## Step 6 — Teardown (finalization only)

Run as part of the worktree finalize flow (`branch-flow.md` → Step 8), **after**
the merge. Tear down **only** the isolated project, including its namespaced
volumes:

```bash
docker compose -p "$COMPOSE_PROJECT_NAME" down -v
rm -f "$WT"/docker-compose.worktree.yml
```

> **Safety — non-negotiable:**
> - Always include `-p "$COMPOSE_PROJECT_NAME"`. A bare `docker compose down`
>   targets the default project and can stop the **main** stack.
> - `down -v` here removes only the isolated, namespaced volumes — never the
>   main project's data volumes.
> - Never stop, remove, or prune containers/volumes that lack the isolated
>   project prefix.
