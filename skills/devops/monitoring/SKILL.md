---
name: monitoring
description: Observability stack setup — Prometheus/Grafana (self-hosted), CloudWatch (AWS), Google Cloud Monitoring, Azure Monitor, Datadog. Covers metrics collection, log aggregation, alerting rules, and dashboards.
---

# Monitoring & Observability

## Core Principle

Instrument first → aggregate second → alert third. Never set up alerts before you know what to measure.

---

## Decision Framework — Self-Hosted vs. Managed

| Scenario | Recommended |
|----------|-------------|
| VPS / single server, cost-sensitive | Prometheus + Grafana (self-hosted via Docker) |
| AWS-native stack | CloudWatch (Metrics + Logs + Alarms) |
| GCP-native stack | Cloud Monitoring + Cloud Logging |
| Azure-native stack | Azure Monitor + Log Analytics |
| Multi-cloud or mixed stack | Datadog (SaaS) or Grafana Cloud |
| High log volume, self-hosted | Loki + Grafana (avoid ELK unless already invested) |

---

## Option 1 — Prometheus + Grafana (Self-Hosted)

### docker-compose.yml

```yaml
services:
  prometheus:
    image: prom/prometheus:v2.51.0
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./alerts:/etc/prometheus/alerts:ro
      - prometheus_data:/prometheus
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.retention.time=15d
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager:v0.27.0
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    ports:
      - "9093:9093"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.4.0
    environment:
      GF_SECURITY_ADMIN_PASSWORD: $GRAFANA_ADMIN_PASSWORD
      GF_USERS_ALLOW_SIGN_UP: "false"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    ports:
      - "3000:3000"
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:v1.7.0
    pid: host
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    command:
      - --path.procfs=/host/proc
      - --path.sysfs=/host/sys
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
```

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]

rule_files:
  - /etc/prometheus/alerts/*.yml

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["localhost:9090"]
  - job_name: app
    static_configs:
      - targets: ["app:8080"]   # app must expose /metrics
  - job_name: node
    static_configs:
      - targets: ["node-exporter:9100"]
```

### Mandatory exporters

| What to monitor | Exporter |
|----------------|---------|
| Host CPU/mem/disk/net | `prom/node-exporter` (included above) |
| Docker containers | `gcr.io/cadvisor/cadvisor` |
| PostgreSQL | `prometheuscommunity/postgres-exporter` |
| MySQL | `prom/mysqld-exporter` |
| Redis | `oliver006/redis_exporter` |
| Nginx | `nginx/nginx-prometheus-exporter` |

### AlertManager

AlertManager receives fired alerts from Prometheus and routes them to notification channels. Without it, rules fire internally but are never delivered. Full `alertmanager.yml` with Slack and PagerDuty routing: `references/prometheus-alerts.md`.

Key principle: route `severity: critical` to a paging channel and `severity: warning` to a lower-urgency channel. Always set `send_resolved: true` so the team knows when an alert clears.

### Alert rules

Full base alert set (ServiceDown, HighErrorRate, HighLatencyP95, DiskUsageHigh, HighMemoryUsage): `references/prometheus-alerts.md`. Place rule files under `alerts/` and reference them in `prometheus.yml` `rule_files`.

### Grafana Provisioning

Mount `grafana/provisioning/` to `/etc/grafana/provisioning` (already in the compose above). This auto-configures datasources and dashboards on every restart — no manual UI setup.

**grafana/provisioning/datasources/prometheus.yml**
```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

Place dashboard JSON files under `grafana/provisioning/dashboards/` with a matching `dashboards.yml` provider. Use [Grafana Dashboard 1860](https://grafana.com/grafana/dashboards/1860) (Node Exporter Full) as the host metrics baseline.

### Retention sizing

`retention_days × 86400s / scrape_interval × active_series × 2 bytes ≈ disk needed`

Example: 15 days, 15 s scrape, 10 000 series ≈ 2.6 GB. Allocate ≥ 20 GB and monitor `prometheus_tsdb_storage_blocks_bytes`.

---

## Option 2 — Log Aggregation with Loki

Loki + Promtail is the low-cost companion to Grafana. Use when already running Option 1.

### docker-compose.yml additions

```yaml
  loki:
    image: grafana/loki:2.9.0
    volumes:
      - ./loki.yml:/etc/loki/config.yml:ro
      - loki_data:/loki
    command: -config.file=/etc/loki/config.yml
    restart: unless-stopped

  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - ./promtail.yml:/etc/promtail/config.yml:ro
    command: -config.file=/etc/promtail/config.yml
    restart: unless-stopped

volumes:
  loki_data:
```

Full `loki.yml` (with 30-day retention and compactor) and `promtail.yml` (Docker container autodiscovery): `references/loki-config.md`.

### Label strategy

Labels in Loki are indexed — high-cardinality values cause index bloat and slow queries.

- Use at most 5 static labels: `service`, `environment`, `container`, `level`, `region`
- Never use as labels: `request_id`, `user_id`, `trace_id`, `session_id`, `ip_address`
- Put high-cardinality values inside the log line (JSON), then filter with `| json | field = "value"`

### Grafana Loki datasource

Add to the existing `grafana/provisioning/datasources/prometheus.yml`:

```yaml
  - name: Loki
    type: loki
    url: http://loki:3100
    editable: false
```

---

## Option 3 — AWS CloudWatch

### Key services

| Need | CloudWatch component |
|------|---------------------|
| Application metrics | CloudWatch Metrics (custom via PutMetricData or EMF) |
| Container metrics | Container Insights (ECS/EKS) |
| Log collection | CloudWatch Logs + Log Groups |
| Log-based metrics | Metric Filters |
| Alerting | CloudWatch Alarms → SNS → Email/Slack/PagerDuty |
| Dashboards | CloudWatch Dashboards |

### Log group retention policy (mandatory)

Without a retention policy, logs accumulate indefinitely. This is the #1 CloudWatch cost driver.

```hcl
resource "aws_cloudwatch_log_group" "app" {
  name              = "/app/${var.service_name}"
  retention_in_days = 30   # never leave as 0 (never expire)
  tags              = var.tags
}
```

CLI equivalent: `aws logs put-retention-policy --log-group-name "/app/svc" --retention-in-days 30`

### CloudWatch Agent — custom metrics on EC2

Place `amazon-cloudwatch-agent.json` in `/opt/aws/amazon-cloudwatch-agent/etc/` and run via SSM or startup script.

```json
{
  "metrics": {
    "namespace": "MyApp",
    "metrics_collected": {
      "mem": { "measurement": ["mem_used_percent"] },
      "disk": { "measurement": ["disk_used_percent"], "resources": ["/"] }
    },
    "append_dimensions": {
      "InstanceId": "${aws:InstanceId}",
      "Environment": "${var.environment}"
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [{
          "file_path": "/var/log/app/*.log",
          "log_group_name": "/app/${var.service_name}",
          "log_stream_name": "{instance_id}"
        }]
      }
    }
  }
}
```

### CloudWatch Logs Insights — common queries

Log Insights only works well with structured JSON logs. Confirm the application emits JSON to stdout.

```
# Error rate by 5-minute window
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() as errors by bin(5m)

# Slow requests (> 1000ms) — requires structured JSON
fields @timestamp, requestId, duration
| filter duration > 1000
| sort duration desc | limit 50
```

### Minimum alarms (Terraform)

```hcl
resource "aws_cloudwatch_metric_alarm" "service_down" {
  alarm_name          = "${var.service_name}-unhealthy-tasks"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 60
  statistic           = "Average"
  threshold           = 1
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "${var.service_name}-5xx-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

### Cost control

- Set retention on every log group — use a Terraform `aws_cloudwatch_log_group` resource for all groups to avoid drift
- Use **Metric Filters** to derive metrics from logs instead of PutMetricData in high-frequency code paths
- Sample debug logs in high-traffic services; only index `ERROR` and `WARN` fully

---

## Option 4 — Datadog (SaaS, Multi-Cloud)

Use when: multi-cloud, team has a Datadog contract, or unified APM + logs + metrics is needed.

### Agent install with Unified Service Tagging

`DD_ENV`, `DD_SERVICE`, and `DD_VERSION` are required for log-metric-trace correlation in Datadog. Without them, you cannot link a latency spike in metrics to the trace that caused it.

```yaml
services:
  datadog-agent:
    image: datadog/agent:7
    environment:
      DD_API_KEY: $DATADOG_API_KEY
      DD_SITE: datadoghq.com
      DD_ENV: $APP_ENV          # production | staging | development
      DD_SERVICE: $APP_NAME
      DD_VERSION: $APP_VERSION
      DD_LOGS_ENABLED: "true"
      DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL: "true"
      DD_APM_ENABLED: "true"
      DD_CONTAINER_EXCLUDE: "name:datadog-agent"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /proc/:/host/proc/:ro
      - /sys/fs/cgroup/:/host/sys/fs/cgroup:ro
    restart: unless-stopped
```

Propagate the same tags to application services:

```yaml
# add to every app service
environment:
  DD_AGENT_HOST: datadog-agent
  DD_TRACE_AGENT_PORT: 8126
  DD_ENV: $APP_ENV
  DD_SERVICE: $APP_NAME
  DD_VERSION: $APP_VERSION
```

### APM — install tracing library

The agent listens on port `8126`. Install the tracing library — no changes to routing needed:

| Language | Install | Init |
|----------|---------|------|
| Node.js | `npm install dd-trace` | `node -r dd-trace/init app.js` |
| Python | `pip install ddtrace` | `ddtrace-run python app.py` |
| Go | `go get gopkg.in/DataDog/dd-trace-go.v1` | `tracer.Start()` in main |
| PHP | `composer require datadog/dd-trace` | auto-instrumented |
| Java | download `dd-java-agent.jar` | `-javaagent:/path/dd-java-agent.jar` |

### Integration autodiscovery

Datadog reads Docker labels to configure integrations automatically — no static config files needed.

```yaml
db:
  image: postgres:16
  labels:
    com.datadoghq.ad.check_names: '["postgres"]'
    com.datadoghq.ad.init_configs: '[{}]'
    com.datadoghq.ad.instances: >
      [{"host":"%%host%%","port":"5432","username":"datadog","password":"%%env_DD_PG_PASSWORD%%"}]

redis:
  image: redis:7
  labels:
    com.datadoghq.ad.check_names: '["redisdb"]'
    com.datadoghq.ad.init_configs: '[{}]'
    com.datadoghq.ad.instances: '[{"host":"%%host%%","port":"6379"}]'
```

For PostgreSQL: `CREATE USER datadog WITH PASSWORD '…'; GRANT pg_monitor TO datadog;`

### Minimum monitors

- Service health check (container running)
- Error rate > 5% (5-minute window)
- P95 latency > 1 s
- Disk usage > 80%
- Memory usage > 90%
- Enable **Watchdog** for automatic anomaly detection (no manual monitor needed)

### Cost control

Datadog bills on log ingestion + indexing. Reduce cost without losing visibility:

| Strategy | How |
|----------|-----|
| Index only errors | Log Index that filters `status:error`; archive the rest to S3/GCS |
| Exclude health checks | Exclusion Filter for `/health`, `/ping`, static-asset paths |
| Sample traces | `DD_TRACE_SAMPLE_RATE=0.1` for high-volume, low-value endpoints |

---

## Application Instrumentation Requirements

Confirm with the backend developer before setting up any monitoring stack:

| Language | Library |
|----------|---------|
| Node.js | `prom-client` |
| Python | `prometheus-client` |
| Go | `prometheus/client_golang` |
| Java | Micrometer |
| PHP | `promphp/prometheus_client_php` |

Minimum metrics every app must expose:
- HTTP request count (by method, path, status)
- HTTP request duration (histogram — P50/P95/P99)
- Active connections or queue depth
- Error count (by type)

---

## Before Declaring Done

- [ ] Application exposes `/metrics` with the minimum metrics above
- [ ] All critical services have a `ServiceDown` alert
- [ ] Error rate and latency alerts defined and routing to a notification channel
- [ ] Disk usage alert on every host > 80%
- [ ] Dashboard created: request rate, error rate, latency P95, CPU, memory
- [ ] Log aggregation collecting from all services
- [ ] Log retention policy set — never unlimited
- [ ] Runbook URL in alert annotations
- [ ] **If Prometheus**: AlertManager configured and test alert delivered to Slack/PagerDuty
- [ ] **If Loki**: label cardinality reviewed — no high-cardinality labels on streams
- [ ] **If Datadog**: Unified Service Tagging applied; APM traces visible for at least one critical flow
- [ ] **If CloudWatch**: retention policy on every log group; Log Insights tested with a sample query
