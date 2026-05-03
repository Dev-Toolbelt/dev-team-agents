# Loki Configuration Reference

## loki.yml — with retention

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    ring:
      replication_factor: 1

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/index
    cache_location: /loki/index_cache
  filesystem:
    directory: /loki/chunks

limits_config:
  retention_period: 30d    # adjust per compliance requirement
  ingestion_rate_mb: 16
  ingestion_burst_size_mb: 32

compactor:
  working_directory: /loki/compactor
  retention_enabled: true  # required for retention_period to take effect
```

## promtail.yml — Docker container log collection

```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: containers
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: [__meta_docker_container_name]
        target_label: container
      - source_labels: [__meta_docker_container_label_com_docker_compose_service]
        target_label: service
      - source_labels: [__meta_docker_container_label_com_docker_compose_project]
        target_label: project
    pipeline_stages:
      - json:
          expressions:
            level: level
      - labels:
          level:
```

## Label cardinality rules

Labels are indexed in Loki — high-cardinality values cause index bloat and slow queries.

| ✅ Use as labels | ❌ Never use as labels |
|-----------------|----------------------|
| service, environment, container, level | request_id, user_id, trace_id, session_id, ip_address |

Put high-cardinality values inside the log line (JSON field), then query with `| json | field = "value"`.
