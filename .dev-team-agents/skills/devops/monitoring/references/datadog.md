# Datadog (SaaS, Multi-Cloud)

Use when: multi-cloud, team has a Datadog contract, or unified APM + logs + metrics is needed.

## Agent install with Unified Service Tagging

`DD_ENV`, `DD_SERVICE`, and `DD_VERSION` are required for log-metric-trace correlation. Without them, you cannot link a latency spike in metrics to the trace that caused it.

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

## APM — install tracing library

The agent listens on port `8126`. Install the tracing library — no routing changes needed:

| Language | Install | Init |
|----------|---------|------|
| Node.js | `npm install dd-trace` | `node -r dd-trace/init app.js` |
| Python | `pip install ddtrace` | `ddtrace-run python app.py` |
| Go | `go get gopkg.in/DataDog/dd-trace-go.v1` | `tracer.Start()` in main |
| PHP | `composer require datadog/dd-trace` | auto-instrumented |
| Java | download `dd-java-agent.jar` | `-javaagent:/path/dd-java-agent.jar` |

## Integration autodiscovery

Datadog reads Docker labels to configure integrations automatically:

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

## Minimum monitors

- Service health check (container running)
- Error rate > 5% (5-minute window)
- P95 latency > 1s
- Disk usage > 80%
- Memory usage > 90%
- Enable **Watchdog** for automatic anomaly detection

## Cost control

| Strategy | How |
|----------|-----|
| Index only errors | Log Index that filters `status:error`; archive the rest to S3/GCS |
| Exclude health checks | Exclusion Filter for `/health`, `/ping`, static-asset paths |
| Sample traces | `DD_TRACE_SAMPLE_RATE=0.1` for high-volume, low-value endpoints |
