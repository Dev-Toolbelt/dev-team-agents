# Prometheus Alert Rules Reference

## Base Alert Set — alerts/base.yml

Minimum alerts every production deployment must have. Add to the `rule_files` path defined in `prometheus.yml`.

```yaml
groups:
  - name: base
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.job }} is down"
          runbook: "https://wiki.example.com/runbooks/service-down"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Error rate above 5% on {{ $labels.job }}"

      - alert: HighLatencyP95
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency above 1s on {{ $labels.job }}"

      - alert: DiskUsageHigh
        expr: (node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes > 0.80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Disk usage above 80% on {{ $labels.instance }}"

      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Memory usage above 90% on {{ $labels.instance }}"
```

## AlertManager Routing — alertmanager.yml

```yaml
global:
  slack_api_url: $SLACK_WEBHOOK_URL
  resolve_timeout: 5m

route:
  receiver: slack-critical
  group_by: [alertname, job]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - match:
        severity: warning
      receiver: slack-warning

receivers:
  - name: slack-critical
    slack_configs:
      - channel: "#alerts-critical"
        title: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        send_resolved: true

  - name: slack-warning
    slack_configs:
      - channel: "#alerts-warning"
        title: '[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'
        send_resolved: true
```

For PagerDuty: replace `slack_configs` with `pagerduty_configs` + `routing_key: $PAGERDUTY_ROUTING_KEY`.
