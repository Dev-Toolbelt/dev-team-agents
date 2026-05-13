---
name: sonarqube
description: SonarQube/SonarCloud — quality gates, SAST, CI/CD integration.
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
|--|------------|-------------|
| Hosting | Managed SaaS (sonarcloud.io) | Your infrastructure |
| Config file | `.sonarcloud.properties` | `sonar-project.properties` |
| Auth | `SONAR_TOKEN` → sonarcloud.io | `SONAR_TOKEN` + `SONAR_HOST_URL` |
| `sonar.organization` | Required | Not used |
| Pricing | Free for public repos; paid for private | Free Community Edition |

---

## Quality Gate Summary

The default **Sonar Way** gate checks **New Code** only:

| Metric | Condition |
|--------|-----------|
| Coverage | ≥ 80% |
| Duplicated Lines | < 3% |
| Maintainability / Reliability / Security Rating | A |
| Security Hotspots Reviewed | 100% |

Block CI on gate failure: `-Dsonar.qualitygate.wait=true`

Load `references/quality-gates.md` for: full conditions, issue taxonomy (Bug/Vulnerability/Hotspot/Smell), SAST hotspot workflow, coverage report paths by language, and troubleshooting.

---

## Configuration Quick Reference

| Scan method | Command |
|-------------|---------|
| CLI | `SONAR_TOKEN=xxx sonar-scanner` |
| Maven | `mvn sonar:sonar -Dsonar.token=$SONAR_TOKEN` |
| Gradle | `./gradlew sonar -Dsonar.token=$SONAR_TOKEN` |
| Node.js | `npx sonarqube-scanner` |

Always run tests before the scan so coverage data is available. Use `fetch-depth: 0` in CI checkouts.

Load `references/configuration.md` for: full `sonar-project.properties` template, GitHub Actions / GitLab CI / Bitbucket Pipelines examples, self-hosted Docker Compose setup, Nginx reverse proxy, plugin installation, and backup/upgrade procedures.

---

## Before Declaring Done

- [ ] `SONAR_TOKEN` stored in secret manager — not committed to source
- [ ] Tests run before scanner so coverage is reported (not 0%)
- [ ] `fetch-depth: 0` in CI checkout step
- [ ] Quality gate configured and passing on new code
- [ ] All Security Hotspots reviewed (Fixed / Safe / Acknowledged)
- [ ] Self-hosted: `vm.max_map_count=262144` set on host; backup procedure in place
