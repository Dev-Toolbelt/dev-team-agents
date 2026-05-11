---
name: cicd-github
description: GitHub Actions — build, test, lint, deploy, and release workflows.
---

# GitHub Actions

## Workflow File Location

```
.github/
  workflows/
    ci.yml          ← lint + test on every PR
    deploy.yml      ← deploy on merge to main
    release.yml     ← tag-based release
```

## Standard CI Pipeline

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main, master, develop]
  push:
    branches: [main, master]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm run lint

  test:
    name: Test
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
      - run: npm ci
      - run: npm test
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/test
```

## Deploy on Merge

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: |
          docker build -t ${{ vars.REGISTRY }}/${{ vars.IMAGE_NAME }}:${{ github.sha }} .

      - name: Login to registry
        uses: docker/login-action@v3
        with:
          registry: ${{ vars.REGISTRY }}
          username: ${{ secrets.REGISTRY_USER }}
          password: ${{ secrets.REGISTRY_PASSWORD }}

      - name: Push image
        run: docker push ${{ vars.REGISTRY }}/${{ vars.IMAGE_NAME }}:${{ github.sha }}

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_KEY }}
          script: |
            cd /opt/myapp
            IMAGE_TAG=${{ github.sha }} docker compose pull app
            IMAGE_TAG=${{ github.sha }} docker compose up -d
            docker image prune -f
```

## Secrets Management

- Store secrets in **GitHub Environments** (not repo-level) for production
- Use `vars` for non-sensitive config, `secrets` for credentials
- Never echo secrets in run steps — GitHub masks them but it's bad practice
- Rotate secrets via repository settings, not by editing workflow files

## Best Practices

- Pin action versions to a commit SHA for security: `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af68`
- Use `concurrency` to cancel outdated runs on the same branch
- Cache dependencies (npm, pip, composer) to speed up builds
- Use `environment` for production deployments — enables approval gates
- Add `timeout-minutes` to jobs to prevent runaway workflows
- Use matrix strategy for multi-version testing: `matrix: { node: [18, 20, 22] }`

## Reusable Workflows

```yaml
# .github/workflows/reusable-test.yml
on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
      - run: npm ci && npm test
```
