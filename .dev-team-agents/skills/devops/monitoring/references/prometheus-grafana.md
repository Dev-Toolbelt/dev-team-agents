# Prometheus + Grafana (Self-Hosted)

## docker-compose.yml

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

## prometheus.yml

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

## Mandatory exporters

| What to monitor | Exporter |
|----------------|---------|
| Host CPU/mem/disk/net | `prom/node-exporter` |
| Docker containers | `gcr.io/cadvisor/cadvisor` |
| PostgreSQL | `prometheuscommunity/postgres-exporter` |
| MySQL | `prom/mysqld-exporter` |
| Redis | `oliver006/redis_exporter` |
| Nginx | `nginx/nginx-prometheus-exporter` |

## AlertManager

AlertManager receives fired alerts and routes them to notification channels. Without it, rules fire internally but are never delivered.

Key principle: route `severity: critical` to a paging channel and `severity: warning` to lower-urgency. Always set `send_resolved: true`.

Base alert set (ServiceDown, HighErrorRate, HighLatencyP95, DiskUsageHigh, HighMemoryUsage): see `prometheus-alerts.md`. Place rule files under `alerts/` and reference them in `prometheus.yml` `rule_files`.

## Grafana Provisioning

Mount `grafana/provisioning/` to `/etc/grafana/provisioning`. Auto-configures datasources and dashboards on restart.

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

Place dashboard JSON files under `grafana/provisioning/dashboards/` with a matching `dashboards.yml` provider. Use [Grafana Dashboard 1860](https://grafana.com/grafana/dashboards/1860) (Node Exporter Full) as the baseline.

## Retention sizing

`retention_days × 86400s / scrape_interval × active_series × 2 bytes ≈ disk needed`

Example: 15 days, 15s scrape, 10 000 series ≈ 2.6 GB. Allocate ≥ 20 GB and monitor `prometheus_tsdb_storage_blocks_bytes`.

## Loki (log aggregation companion)

Loki + Promtail is the low-cost companion for logging. Use when already running Prometheus + Grafana.

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

### Label strategy

Labels in Loki are indexed — high-cardinality values cause index bloat.

- Use at most 5 static labels: `service`, `environment`, `container`, `level`, `region`
- Never use as labels: `request_id`, `user_id`, `trace_id`, `session_id`, `ip_address`
- Put high-cardinality values inside the log line (JSON), then filter with `| json | field = "value"`

### Grafana Loki datasource

```yaml
  - name: Loki
    type: loki
    url: http://loki:3100
    editable: false
```
