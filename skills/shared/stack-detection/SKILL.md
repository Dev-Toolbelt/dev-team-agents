---
name: stack-detection
description: Canonical signal-to-stack detection table. Agents load this skill to identify project technology stack from file signals rather than maintaining divergent inline heuristics.
---

# Stack Detection

Use file signals to infer the project's primary stack before making technology decisions.

## Signal → Stack Table

| Signal file(s) | Inferred stack |
|----------------|----------------|
| `pyproject.toml`, `requirements.txt`, `setup.py`, `*.py` in root | Python |
| `package.json` + `tsconfig.json`, or `*.ts`/`*.tsx` in `src/` | TypeScript/Node.js |
| `package.json` (no tsconfig), `*.js` in `src/` | JavaScript/Node.js |
| `Cargo.toml` | Rust |
| `composer.json`, `*.php` in root or `src/` | PHP |
| `Gemfile`, `*.rb` in `app/` | Ruby |
| `go.mod` | Go |
| `pom.xml`, `build.gradle`, `*.java` in `src/` | Java |
| `build.gradle.kts`, `*.kt` in `src/` | Kotlin |
| `*.csproj`, `*.sln`, `Program.cs` | C#/.NET |
| `pubspec.yaml`, `*.dart` in `lib/` | Flutter/Dart |
| `app.json` with `expo` OR `package.json` with `react-native` | React Native |

## Multi-stack Projects

If multiple signals coexist (e.g., `package.json` + `go.mod`), identify the PRIMARY stack:
1. Check `CLAUDE.md` or project README for explicit stack declaration
2. Count files: largest language directory is likely primary
3. Check for API/service separation (e.g., `backend/` in Go, `frontend/` in TS)

## Tooling Detection

Some facts cannot be read from a file signal — they depend on what is installed on the machine. Probe once, record the answer, and never re-detect.

### Docker Compose command form

Compose v2 is a Docker CLI plugin (`docker compose`); v1 is a standalone binary (`docker-compose`). The two are not interchangeable in scripts.

```bash
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE=""
fi
```

| Result | Meaning | Action |
|--------|---------|--------|
| `docker compose` | Compose v2 plugin available | Use this form in all commands and docs |
| `docker-compose` | Legacy v1 standalone binary | Use this form; note the version in project docs |
| empty | Compose not installed | Do not emit compose commands; tell the user what to install |

Record the result in the project's `CLAUDE.md` as `DOCKER_COMPOSE: docker compose` (or `docker-compose`) so every agent uses the correct form without re-probing.

## Usage

After detecting the stack, load the appropriate platform-specific skills (e.g., `skills/devops/`, `skills/integrations/`).
