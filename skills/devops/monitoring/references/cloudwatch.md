# AWS CloudWatch

## Key services

| Need | CloudWatch component |
|------|---------------------|
| Application metrics | CloudWatch Metrics (custom via PutMetricData or EMF) |
| Container metrics | Container Insights (ECS/EKS) |
| Log collection | CloudWatch Logs + Log Groups |
| Log-based metrics | Metric Filters |
| Alerting | CloudWatch Alarms → SNS → Email/Slack/PagerDuty |
| Dashboards | CloudWatch Dashboards |

## Log group retention policy (mandatory)

Without a retention policy, logs accumulate indefinitely — the #1 CloudWatch cost driver.

```hcl
resource "aws_cloudwatch_log_group" "app" {
  name              = "/app/${var.service_name}"
  retention_in_days = 30   # never leave as 0 (never expire)
  tags              = var.tags
}
```

CLI: `aws logs put-retention-policy --log-group-name "/app/svc" --retention-in-days 30`

## CloudWatch Agent — custom metrics on EC2

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

## CloudWatch Logs Insights — common queries

Log Insights works best with structured JSON logs. Confirm the application emits JSON to stdout.

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

## Minimum alarms (Terraform)

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

## Cost control

- Set retention on every log group via Terraform `aws_cloudwatch_log_group` to avoid drift
- Use **Metric Filters** to derive metrics from logs instead of PutMetricData in high-frequency paths
- Sample debug logs in high-traffic services; only index `ERROR` and `WARN` fully
