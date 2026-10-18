---
name: monorepo-patterns
description: Monorepo — workspace tooling, package boundaries, CI optimization.
---

## Tooling Options

| Tool | Key Features | Best For |
|------|-------------|---------|
| Turborepo | Remote caching, task pipelines, incremental builds | JS/TS monorepos, fast CI |
| Nx | Affected-build detection, generators, plugin ecosystem | Large orgs, polyglot repos |
| pnpm workspaces | Built-in workspace protocol, disk-efficient hoisting | JS/TS, lean setup |
| Yarn workspaces | Mature, broad compatibility | Teams already on Yarn |
| Lerna | Package publishing, changelog automation | Library monorepos with many npm packages |

Turborepo + pnpm workspaces is the recommended default for new JS/TS monorepos. For polyglot (JS + Go + Python), prefer Nx or Bazel.

## Package Boundary Rules

- One package per bounded domain: `packages/auth`, `packages/billing`, `packages/notifications`
- Shared TypeScript types, interfaces, and constants live in `packages/shared` (or `packages/types`)
- No circular dependencies between packages — enforce with linting (see Boundary Enforcement below)
- Apps (`apps/web`, `apps/api`) depend on packages, never on each other
- Internal packages use `private: true` in `package.json` — they are not published to npm

```
monorepo/
  apps/
    web/           ← Next.js / React app
    api/           ← Node.js / Express API
  packages/
    shared/        ← types, constants, utilities
    ui/            ← design system, primitives
    auth/          ← auth logic, shared between apps
    config/        ← ESLint, TypeScript, Prettier configs
```

## Dependency Management

- Use workspace protocol for internal packages: `"@acme/shared": "workspace:*"`
- Pin exact versions (`"react": "18.3.1"`) for leaf apps to ensure reproducible builds
- Use a version range (`"^18.0.0"`) only for published library packages
- Hoist shared dependencies to the root `package.json` to avoid duplicate installs
- Run `pnpm dedupe` periodically to collapse duplicate transitive dependencies

## CI Optimization

- Use affected-build strategies — only run tasks for packages changed since the last commit:

```bash
# Turborepo
turbo run build test --filter=...[HEAD^1]

# Nx
nx affected --target=build --base=HEAD~1
```

- Never run all pipelines on every commit — this breaks as the repo grows
- Cache build outputs remotely (Turborepo Remote Cache, Nx Cloud) for cross-machine reuse
- Run `lint` and `typecheck` in parallel with `test`; gate `deploy` on both passing
- Use path filters in GitHub Actions / GitLab CI to restrict job triggers to relevant package paths

## Versioning Strategy

| Package type | Strategy | Tool |
|-------------|----------|------|
| Published libraries (`packages/*`) | Independent — each has its own semver | Changesets, Lerna |
| Internal apps (`apps/*`) | Fixed / date-based, not published | Git tags per app |
| Shared internal packages | Follow apps that consume them; no independent publish | — |

Use [Changesets](https://github.com/changesets/changesets) for automated changelog generation and version bumps on published packages.

## Code Sharing Rules

- Utilities used by more than one package must live in `packages/shared` — never copy-paste
- UI primitives (Button, Modal, Input) belong in `packages/ui`; app-specific components stay in `apps/web`
- Configuration packages (`packages/config/eslint`, `packages/config/tsconfig`) keep shared tooling config DRY
- Never import from another app's `src/` directory — only from published/workspace packages

## Boundary Enforcement

- Use ESLint `eslint-plugin-import` `no-restricted-paths` to block cross-app imports:

```js
// .eslintrc — prevent apps/web from importing apps/api internals
"import/no-restricted-paths": ["error", {
  "zones": [{ "target": "apps/web", "from": "apps/api/src" }]
}]
```

- For Nx repos, use `@nx/enforce-module-boundaries` with `depConstraints` to declare allowed dependency directions
- Run boundary checks as a required CI step — fail the build on violations

## Docker in a Monorepo

- Always build from the monorepo root context so shared packages are available:

```dockerfile
# Build from root
COPY pnpm-workspace.yaml ./
COPY packages/shared ./packages/shared
COPY apps/api ./apps/api
RUN pnpm install --frozen-lockfile --filter api...
```

- Use multi-stage builds: install + build in one stage, copy only `dist/` and `node_modules` to the final image
- Tag images by app name and git SHA: `acme/api:abc1234`
- Cache the `pnpm store` layer in Docker BuildKit cache mounts to speed up dependency installs
