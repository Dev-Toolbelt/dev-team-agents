# SonarQube — Quality Gates & Issue Taxonomy

## Default Quality Gate: Sonar Way

Conditions are evaluated against the **New Code** period only.

| Metric | Condition |
|--------|-----------|
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

Or use `-Dsonar.qualitygate.wait=true` in the scanner — exits non-zero if the gate fails, blocking CI/CD.

---

## Issue Taxonomy

| Type | Meaning | Example |
|------|---------|---------|
| **Bug** | Code that will definitely break at runtime | NullPointerException risk, incorrect boolean logic |
| **Vulnerability** | Exploitable security weakness | SQL injection, hardcoded credential |
| **Security Hotspot** | Code to review — may or may not be a real risk | `Math.random()` in a non-crypto context |
| **Code Smell** | Maintainability problem | Too-complex method, duplicated block |

**Severity**: Blocker → Critical → Major → Minor → Info

**Clean Code attributes** (SonarQube 10+): Reliability, Security, Maintainability.

---

## SAST — Security Hotspots Workflow

Security Hotspots require human review:

1. Navigate to **Security Hotspots** in the project dashboard
2. For each hotspot: assess whether the flagged code is exploitable in context
3. Mark as **Fixed** (code changed), **Safe** (reviewed — not exploitable), or **Acknowledged** (known accepted risk)

Common hotspot categories:

| Category | Example |
|----------|---------|
| Weak cryptography | `MD5`, `SHA-1`, `Math.random()` |
| SQL construction | String concatenation in queries |
| Command injection | Unvalidated input passed to shell |
| Path traversal | User-supplied file paths |
| CORS misconfiguration | Wildcard `Access-Control-Allow-Origin` |
| JWT algorithm | `alg: none` accepted |

All hotspots must be reviewed before the quality gate passes (`Security Hotspots Reviewed = 100%`).

---

## Coverage Reporting

Coverage only appears if the report is generated **before** the scan and the correct path is configured.

| Language | Test runner command | Output artifact | sonar-project.properties key |
|----------|---------------------|-----------------|------------------------------|
| JavaScript / TypeScript | `jest --coverage --coverageReporters=lcov` | `coverage/lcov.info` | `sonar.javascript.lcov.reportPaths` |
| JavaScript / TypeScript | `vitest run --coverage --coverage.reporter=lcov` | `coverage/lcov.info` | `sonar.javascript.lcov.reportPaths` |
| Python | `pytest --cov --cov-report=xml` | `coverage.xml` | `sonar.python.coverage.reportPaths` |
| PHP | `phpunit --coverage-clover coverage/clover.xml` | Clover XML | `sonar.php.coverage.reportPaths` |
| Java | JaCoCo plugin (`mvn verify` / `gradle test jacocoTestReport`) | `target/site/jacoco/jacoco.xml` | `sonar.coverage.jacoco.xmlReportPaths` |
| Go | `go test -coverprofile=coverage.out ./...` | `coverage.out` | `sonar.go.coverage.reportPaths` |
| Ruby | SimpleCov (configured in `spec_helper`) | `coverage/.resultset.json` | `sonar.ruby.coverage.reportPaths` |
| .NET | `dotnet test --collect:"XPlat Code Coverage"` (Coverlet) | `**/coverage.cobertura.xml` | `sonar.cs.vscoveragexml.reportsPaths` |

Test the path before running the scanner — a misconfigured path results in 0% coverage with no error.

**Coverage quality rules**

- Do **not** pad coverage: an assertion that exists only to raise the number provides no safety net and hides the real gap.
- Focus coverage on logic-bearing code — branches, error paths, state transitions — not on pure rendering or plain data holders.
- If new code cannot reach the gate threshold, flag the remaining gap explicitly rather than silently lowering the gate.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| SonarQube fails to start (Elasticsearch error) | `vm.max_map_count` too low | Run `sysctl -w vm.max_map_count=262144` on host |
| Scanner reports 0% coverage | Wrong report path or tests not run before scan | Verify path and that test runner generates the report before `sonar-scanner` |
| New code period shows unexpected scope | Shallow clone in CI | Add `fetch-depth: 0` to checkout step |
| Quality gate always `NONE` | Project not yet analyzed or gate not assigned | Run at least one full analysis; assign quality gate in project settings |
| "Invalid token" error | Token expired or wrong scope | Regenerate token with `Execute Analysis` permission |
