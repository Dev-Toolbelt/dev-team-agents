# SonarQube — Configuration Reference

## sonar-project.properties

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

# Coverage report paths — set the key matching your language
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

# Override host for self-hosted
sonar-scanner \
  -Dsonar.host.url=https://sonar.yourdomain.com \
  -Dsonar.token=$SONAR_TOKEN
```

Build-tool scanners:

```bash
mvn sonar:sonar -Dsonar.token=$SONAR_TOKEN   # Maven
./gradlew sonar -Dsonar.token=$SONAR_TOKEN   # Gradle
npx sonarqube-scanner                         # Node.js
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
          fetch-depth: 0       # required — shallow clones break blame data

      - name: Run tests with coverage
        run: npm test -- --coverage

      - name: SonarQube Scan
        uses: SonarSource/sonarqube-scan-action@v5
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}   # omit for SonarCloud
```

For SonarCloud, use `SonarSource/sonarcloud-github-action@v2`.

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

## Self-Hosted Setup

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 2 GB | 4 GB+ |
| CPU | 2 vCPUs | 4 vCPUs |
| Disk | 10 GB | 20 GB+ SSD |
| Java | JRE 17 | JRE 17 (bundled in image) |

Host must have `vm.max_map_count ≥ 262144` (Elasticsearch requirement).

```bash
sysctl -w vm.max_map_count=262144
sysctl -w fs.file-max=65536
echo "vm.max_map_count=262144" >> /etc/sysctl.d/99-sonarqube.conf
sysctl --system
```

### Docker Compose

```yaml
services:
  sonarqube:
    image: sonarqube:community
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
      nofile: { soft: 65536, hard: 65536 }
    restart: unless-stopped

  sonarqube-db:
    image: postgres:15-alpine
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

Required `.env`:

```env
SONAR_DB_PASSWORD=change-me-strong-password
SONAR_JWT_SECRET=   # openssl rand -base64 32
```

### Server Properties (via environment variables)

| Property | Env override | Description |
|----------|-------------|-------------|
| `sonar.jdbc.url` | `SONAR_JDBC_URL` | Database connection string |
| `sonar.web.host` | `SONAR_WEB_HOST` | Bind address (default: `0.0.0.0`) |
| `sonar.web.port` | `SONAR_WEB_PORT` | HTTP port (default: `9000`) |
| `sonar.web.context` | `SONAR_WEB_CONTEXT` | Context path — avoid if possible |
| `sonar.auth.jwtBase64Hs256Secret` | `SONAR_AUTH_JWTBASE64HS256SECRET` | JWT secret — **required in production** |

### First Boot

1. Navigate to `http://localhost:9000`
2. Login with `admin` / `admin` — **change the password immediately**
3. Create a project → generate a project token under **My Account → Security**
4. Store token as `SONAR_TOKEN` in secret manager — never commit it

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
        proxy_set_header   X-Forwarded-Proto https;
    }
}
```

### Plugins (Self-Hosted)

```bash
docker cp my-plugin.jar sonarqube:/opt/sonarqube/extensions/plugins/
docker restart sonarqube
```

Or use **Administration → Marketplace**.

Languages bundled in Community Edition: Java, JavaScript/TypeScript, Python, PHP, C#, Go, Ruby, Kotlin, Scala, XML, HTML, CSS.

### Backup & Upgrades

```bash
# Database dump
docker exec sonarqube-db pg_dump -U sonar sonar > sonar_backup_$(date +%Y%m%d).sql

# Extensions backup
docker cp sonarqube:/opt/sonarqube/extensions ./sonarqube_extensions_backup
```

**Upgrade procedure**: stop → pull new image → start with same volumes → monitor logs.

**Never skip major versions** — upgrade sequentially (e.g., 9.x → 10.x). Check upgrade notes at `https://docs.sonarsource.com/sonarqube`.
