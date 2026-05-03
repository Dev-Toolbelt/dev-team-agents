---
name: docker-dev
description: Docker configuration best practices for development environments. Use when creating or reviewing docker-compose files, Dockerfiles for local development, or debugging container issues in dev.
---

# Docker for Development Environments

## Core Principles

- Dev containers should **mirror production** as closely as possible without overcomplicating setup
- Use **bind mounts** for source code so changes reflect instantly without rebuilding
- Never install project dependencies on the host — always inside the container
- Every developer runs the same environment regardless of their OS

---

## docker-compose.yml Structure

```yaml
services:
  app:
    build:
      context: .
      dockerfile: docker/dev/Dockerfile
    container_name: myproject-app
    restart: unless-stopped
    volumes:
      - .:/app                          # bind mount for live code
      - /app/vendor                     # anonymous volume to prevent host override
      - /app/node_modules
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=local
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_started
    networks:
      - myproject

  db:
    image: postgres:16-alpine
    container_name: myproject-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: myproject
      POSTGRES_USER: myproject
      POSTGRES_PASSWORD: secret
    volumes:
      - db_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U myproject"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - myproject

  cache:
    image: redis:7-alpine
    container_name: myproject-cache
    restart: unless-stopped
    networks:
      - myproject

volumes:
  db_data:

networks:
  myproject:
    driver: bridge
```

## Development Dockerfile

```dockerfile
FROM node:20-alpine AS base
# or php:8.3-fpm-alpine, python:3.12-slim, etc.

WORKDIR /app

# Install system dependencies (rarely changes — cache this layer)
RUN apk add --no-cache git curl bash

# Copy dependency manifests only (cache layer)
COPY package*.json ./
RUN npm ci

# In dev: source code comes from bind mount, not COPY
# No COPY . . here

EXPOSE 3000
CMD ["npm", "run", "dev"]
```

## Common Patterns

### Healthchecks
Always add healthchecks to databases and services that have startup latency:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 10s
  timeout: 5s
  retries: 3
  start_period: 15s
```

### Override File for Personal Config
Use `docker-compose.override.yml` (git-ignored) for per-developer customizations:
```yaml
# docker-compose.override.yml (gitignored)
services:
  app:
    ports:
      - "8001:8000"  # different port if 8000 is taken locally
```

### Useful Commands
```bash
# Start
docker compose up -d

# Rebuild after Dockerfile change
docker compose up -d --build app

# Run one-off command
docker compose exec app bash
docker compose exec app npm run test

# See logs
docker compose logs -f app

# Stop and remove volumes (full reset)
docker compose down -v
```

## Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Permission errors on bind mount | Host/container user mismatch | Add `user: "${UID}:${GID}"` to service |
| Changes not reflected | Bind mount not set up | Check volume path in docker-compose.yml |
| DB not ready on start | Race condition | Use `depends_on` with `condition: service_healthy` |
| `node_modules` override | Bind mount covers it | Add anonymous volume for node_modules |
