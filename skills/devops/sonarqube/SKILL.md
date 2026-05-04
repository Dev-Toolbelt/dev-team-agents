---
name: sonarqube
description: SonarQube and SonarCloud integration — static analysis, quality gates, SAST, coverage reporting, self-hosted Docker setup, server configuration, CI/CD integration, and plugin management. Load when sonar-project.properties, .sonarcloud.properties, or SONAR_TOKEN are detected in the project.
---

# SonarQube / SonarCloud

## Detection Signals

Load this skill when any of the following are present:

| Signal | Location |
|--------|----------|
| `sonar-project.properties` | project root |
| `.sonarcloud.properties` | project root |
| `SONAR_TOKEN` or `SONAR_HOST_URL` | `.env`, `.env.example`, CI/CD config |
| `sonar-scanner`, `mvn sonar:sonar`, `./gradlew sonar` | CI/CD pipeline files |
| `sonarqube` service | `docker-compose.yml` |
| `sonarqube-scanner` or `sonar-scanner` | `package.json`, `pom.xml`, `build.gradle` |

---

## SonarCloud vs Self-Hosted

| | SonarCloud | Self-Hosted |
|---|---|---|
| Hosting | Managed SaaS (sonarcloud.io) | Your infrastructure |
| Config file | `.sonarcloud.properties` | `sonar-project.properties` |
| Auth | `SONAR_TOKEN` → sonarcloud.io | `SONAR_TOKEN` + `SONAR_HOST_URL` |
| `sonar.organization` | Required | Not used |
| Pricing | Free for public repos; paid for private | Free Community Edition; paid editions for advanced features |
| Updates | Automatic | Manual — follow upgrade path |

---

## Self-Hosted Setup

### System Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| RAM | 2 GB | 4 GB+ |
| CPU | 2 vCPUs | 4 vCPUs |
| Disk | 10 GB | 20 GB+ SSD |
| OS | Linux 64-bit | Linux 64-bit |
| Java | JRE 17 | JRE 17 (bundled in the image) |

SonarQube uses Elasticsearch internally — the host must have `vm.max_map_count ≥ 262144`.

### Required Host Configuration

```bash
# Apply before starting containers
sysctl -w vm.max_map_count=262144
sysctl -w fs.file-max=65536

# Make persistent — create /etc/sysctl.d/99-sonarqube.conf
echo "vm.max_map_count=262144" >> /etc/sysctl.d/99-sonarqube.conf
echo "fs.file-max=65536"       >> /etc/sysctl.d/99-sonarqube.conf
sysctl --system
```

### Docker Compose

```yaml
# docker-compose.yml
services:
  sonarqube:
    image: sonarqube:community   # or sonarqube:developer / sonarqube:enterprise
    container_name: sonarqube
    depends_on:
      sonarqube-db:
        condition: service_healthy
    environment:
      SONAR_JDBC_URL: jdbc:postgresql://sonarqube-db:5432/sonar
      SONAR_JDBC_USERNAME: sonar
      SONAR_JDBC_PASSWORD: ${SONAR_DB_PASSWORD}
      SONAR_AUTH_JWTBASE64HS256SECRET: ${SONAR_JWT_SECRET}
    ports:
      - "9000:9000"
    volumes:
      - sonarqube_data:/opt/sonarqube/data
      - sonarqube_extensions:/opt/sonarqube/extensions
      - sonarqube_logs:/opt/sonarqube/logs
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
    restart: unless-stopped

  sonarqube-db:
    image: postgres:15-alpine
    container_name: sonarqube-db
    environment:
      POSTGRES_USER: sonar
      POSTGRES_PASSWORD: ${SONAR_DB_PASSWORD}
      POSTGRES_DB: sonar
    volumes:
      - sonarqube_db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sonar"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  sonarqube_data:
  sonarqube_extensions:
  sonarqube_logs:
  sonarqube_db:
```

Required `.env` variables:

```env
SONAR_DB_PASSWORD=change-me-strong-password
SONAR_JWT_SECRET=   # generate: openssl rand -base64 32
```

### First Boot

1. Navigate to `http://localhost:9000`
2. Login with `admin` / `admin` — **change the password immediately**
3. Create a project → generate a project token under **My Account → Security → Generate Token**
4. Store the token as `SONAR_TOKEN` in your secret manager — never commit it

### sonar.properties (Server Configuration)

Located at `/opt/sonarqube/conf/sonar.properties` inside the container. Override via environment variables using the `SONAR_*` prefix (dots → underscores, all uppercase):

| Property | Env override | Description |
|---|---|---|
| `sonar.jdbc.url` | `SONAR_JDBC_URL` | Database connection string |
| `sonar.jdbc.username` | `SONAR_JDBC_USERNAME` | DB user |
| `sonar.jdbc.password` | `SONAR_JDBC_PASSWORD` | DB password |
| `sonar.web.host` | `SONAR_WEB_HOST` | Bind address (default: `0.0.0.0`) |
| `sonar.web.port` | `SONAR_WEB_PORT` | HTTP port (default: `9000`) |
| `sonar.web.context` | `SONAR_WEB_CONTEXT` | Context path (e.g., `/sonar`) — avoid if possible |
| `sonar.auth.jwtBase64Hs256Secret` | `SONAR_AUTH_JWTBASE64HS256SECRET` | JWT secret — **required in production** |

Generate the JWT secret:

```bash
openssl rand -base64 32
```

### Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl;
    server_name sonar.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/sonar.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sonar.yourdomain.com/privkey.pem;

    location / {
        proxy_pass         http://localhost:9000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;
    }
}
```

Avoid `sonar.web.context` (sub-path) unless required — the WebSocket connection used by the scanner is simpler with root context.

---

## Project Configuration (sonar-project.properties)

```properties
# sonar-project.properties — place at project root
sonar.projectKey=my-project
sonar.projectName=My Project
sonar.projectVersion=1.0

# Source and test paths (comma-separated)
sonar.sources=src
sonar.tests=tests

# Exclusions — never analyze generated, vendor, or test files as sources
sonar.exclusions=\
  **/node_modules/**,\
  **/vendor/**,\
  **/*.min.js,\
  **/dist/**,\
  **/build/**,\
  **/__mocks__/**

# Coverage report paths — set the key matching your language (see Coverage section)
sonar.javascript.lcov.reportPaths=coverage/lcov.info
# sonar.python.coverage.reportPaths=coverage.xml
# sonar.php.coverage.reportPaths=coverage/clover.xml
# sonar.coverage.jacoco.xmlReportPaths=target/site/jacoco/jacoco.xml
# sonar.go.coverage.reportPaths=coverage.out

sonar.sourceEncoding=UTF-8
```

**SonarCloud** — use `.sonarcloud.properties` with the same keys plus:

```properties
sonar.organization=your-org-slug
```

---

## sonar-scanner CLI

```bash
# Install
brew install sonar-scanner    # macOS
# or download: https://docs.sonarsource.com/sonarqube/latest/analyzing-source-code/scanners/sonarscanner/

# Run (reads sonar-project.properties automatically)
SONAR_TOKEN=xxx sonar-scanner

# Override host for self-hosted (if not set in sonar-project.properties)
sonar-scanner \
  -Dsonar.host.url=https://sonar.yourdomain.com \
  -Dsonar.token=$SONAR_TOKEN
```

Build-tool scanners (preferred when available):

```bash
# Maven
mvn sonar:sonar -Dsonar.token=$SONAR_TOKEN

# Gradle
./gradlew sonar -Dsonar.token=$SONAR_TOKEN

# Node.js
npx sonarqube-scanner
```

---

## CI/CD Integration

### GitHub Actions

```yaml
jobs:
  sonar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0       # required — shallow clones break blame data and new-code detection

      - name: Run tests with coverage
        run: npm test -- --coverage    # adjust to your test runner

      - name: SonarQube Scan
        uses: SonarSource/sonarqube-scan-action@v5
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}   # omit for SonarCloud
```

For SonarCloud, use `SonarSource/sonarcloud-github-action@v2` instead.

**Always run tests before the scan** so coverage data is available to the scanner.

`fetch-depth: 0` is mandatory — without it, blame annotations and new-code detection are broken.

### GitLab CI

```yaml
sonarqube:
  image: sonarsource/sonar-scanner-cli:latest
  variables:
    SONAR_HOST_URL: $SONAR_HOST_URL
    SONAR_TOKEN: $SONAR_TOKEN
  script:
    - sonar-scanner -Dsonar.qualitygate.wait=true
  only:
    - merge_requests
    - main
```

### Bitbucket Pipelines

```yaml
pipelines:
  default:
    - step:
        name: SonarQube Analysis
        image: sonarsource/sonar-scanner-cli:latest
        script:
          - sonar-scanner
            -Dsonar.host.url=$SONAR_HOST_URL
            -Dsonar.token=$SONAR_TOKEN
            -Dsonar.qualitygate.wait=true
```

---

## Issue Taxonomy

| Type | Meaning | Example |
|---|---|---|
| **Bug** | Code that will definitely break at runtime | NullPointerException risk, incorrect boolean logic |
| **Vulnerability** | Exploitable security weakness | SQL injection, hardcoded credential |
| **Security Hotspot** | Code to review — may or may not be a real risk | `Math.random()` in a non-crypto context |
| **Code Smell** | Maintainability problem | Too-complex method, duplicated block |

**Severity**: Blocker → Critical → Major → Minor → Info

**Clean Code attributes** (SonarQube 10+): Reliability, Security, Maintainability — replaces the legacy characteristics model.

---

## Quality Gates

A Quality Gate is a set of pass/fail conditions evaluated against the **New Code** period. The default **Sonar Way** gate:

| Metric | Condition (New Code) |
|---|---|
| Coverage | ≥ 80% |
| Duplicated Lines | < 3% |
| Maintainability Rating | A |
| Reliability Rating | A |
| Security Rating | A |
| Security Hotspots Reviewed | 100% |

**New Code vs Overall**: focus on not degrading new code. Don't let technical debt grow on code you touch.

### Checking Quality Gate Status via API

```bash
curl -s -u $SONAR_TOKEN: \
  "$SONAR_HOST_URL/api/qualitygates/project_status?projectKey=my-project" \
  | jq '.projectStatus.status'
# Returns: OK | WARN | ERROR | NONE
```

Or use `-Dsonar.qualitygate.wait=true` in the scanner — the process exits non-zero if the gate fails, blocking the CI/CD pipeline.

---

## SAST — Security Hotspots

Security Hotspots require human review. Workflow:

1. Navigate to **Security Hotspots** in the project dashboard
2. For each hotspot: assess whether the flagged code is exploitable in context
3. Mark as **Fixed** (code changed), **Safe** (reviewed — not exploitable), or **Acknowledged** (known accepted risk)

Common hotspot categories:

| Category | Example |
|---|---|
| Weak cryptography | `MD5`, `SHA-1`, `Math.random()` |
| SQL construction | String concatenation in queries |
| Command injection | Unvalidated input passed to shell |
| Path traversal | User-supplied file paths |
| CORS misconfiguration | Wildcard `Access-Control-Allow-Origin` |
| JWT algorithm | `alg: none` accepted |

All hotspots must be reviewed before the quality gate passes (`Security Hotspots Reviewed = 100%`).

---

## Coverage Reporting

Coverage only appears in SonarQube if the report is generated **before** the scan and the correct path is configured.

| Language | Tool | sonar-project.properties key |
|---|---|---|
| JavaScript / TypeScript | Jest (`--coverage`), Vitest | `sonar.javascript.lcov.reportPaths` |
| Python | pytest-cov | `sonar.python.coverage.reportPaths` |
| PHP | PHPUnit (Clover XML) | `sonar.php.coverage.reportPaths` |
| Java | JaCoCo | `sonar.coverage.jacoco.xmlReportPaths` |
| Go | `go test -coverprofile=coverage.out` | `sonar.go.coverage.reportPaths` |
| Ruby | SimpleCov | `sonar.ruby.coverage.reportPaths` |
| .NET | Coverlet / dotnet-coverage | `sonar.cs.vscoveragexml.reportsPaths` |

Test the path before running the scanner — a misconfigured path results in 0% coverage with no error.

---

## Plugins (Self-Hosted)

Install by placing `.jar` files in `/opt/sonarqube/extensions/plugins/` and restarting:

```bash
# Via Docker
docker cp my-plugin.jar sonarqube:/opt/sonarqube/extensions/plugins/
docker restart sonarqube
```

Or use **Administration → Marketplace** (requires internet access from the server).

Languages bundled in Community Edition: Java, JavaScript/TypeScript, Python, PHP, C#, Go, Ruby, Kotlin, Scala, XML, HTML, CSS.

---

## Backup & Upgrades (Self-Hosted)

**Always back up before upgrading:**

```bash
# Database dump
docker exec sonarqube-db pg_dump -U sonar sonar > sonar_backup_$(date +%Y%m%d).sql

# Extensions backup
docker cp sonarqube:/opt/sonarqube/extensions ./sonarqube_extensions_backup
```

**Upgrade procedure:**

1. Stop SonarQube: `docker stop sonarqube`
2. Pull new image: `docker pull sonarqube:community`
3. Start with the same volumes — DB migrations run automatically on first boot
4. Monitor: `docker logs -f sonarqube`
5. Verify the web UI is healthy before re-enabling CI/CD pipelines

**Never skip major versions** — upgrade sequentially (e.g., 9.x → 10.x → 10.latest). Check the upgrade notes at `https://docs.sonarsource.com/sonarqube` for each version.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| SonarQube fails to start (Elasticsearch error) | `vm.max_map_count` too low | Run `sysctl -w vm.max_map_count=262144` on host |
| Scanner reports 0% coverage | Wrong report path or tests not run before scan | Verify path and that test runner generates the report before `sonar-scanner` |
| New code period shows unexpected scope | Shallow clone in CI | Add `fetch-depth: 0` to checkout step |
| Quality gate always `NONE` | Project not yet analyzed or gate not assigned | Run at least one full analysis; assign quality gate in project settings |
| "Invalid token" error | Token expired or wrong scope | Regenerate token with `Execute Analysis` permission |
