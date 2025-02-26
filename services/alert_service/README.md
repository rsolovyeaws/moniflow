## Sample metric
```json
{
    "measurement": "cpu_usage",
    "tags": {"host": "server-1"},
    "fields": {"usage": 90.3},
    "timestamp": "2025-02-26T12:00:00Z"
}
```

Users must explicitly create a rule for each tag (e.g., one rule for server-1, another for server-2).

## Sample rule

```json
{
    "metric_name": "cpu_usage",
    "threshold": 85.0,
    "duration_value": 5,
    "duration_unit": "minutes",
    "comparison": ">",
    "notification_channels": ["telegram"],
    "recipients": {
        "telegram": ["@your_telegram_username"]
    },
    "use_recovery_alert": false,
    "tags": {
        "host": "server-1"
    }
}
```