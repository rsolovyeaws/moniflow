Testing is done in the separate redis container
## Sample metric
```json
{
    "measurement": "cpu_usage",
    "tags": {"host": "server-1"},
    "fields": {"usage": 90.3},
    "timestamp": "2025-02-26T12:00:00Z"
}
```

Users must explicitly create a rule for each tag and field_name(e.g., one rule for server-1, another for server-2).


## Sample rule

```json
{
    "metric_name": "cpu_usage",
    "tags": {"host": "server1"},
    "field_name": "usage",
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

-------------------------------
# **Complete Process for Metric Processing with Multiple Fields & Tags**

## **🚀 Step-by-Step Process**

### **1️⃣ Metric is Sent to the API**
A metric is sent to the **`/metrics/`** endpoint:

```json
{
    "measurement": "cpu_usage",
    "tags": {"host": "server-1", "group": "alpha"},
    "fields": {"usage": 90.3, "temperature": 60.0},
    "timestamp": "2025-02-26T12:00:00Z"
}
```
---

## Supported Timestamp Formats

The function accepts timestamps in the following formats:

| Format Type                          | Example                        | Description                                      |
|--------------------------------------|--------------------------------|--------------------------------------------------|
| Unix Timestamp (int)                 | `1645555200`                   | Already in Unix format, returned as is.        |
| ISO 8601 with "Z" (UTC time)         | `"2022-02-22T12:00:00Z"`      | Standard ISO format representing UTC time.      |
| ISO 8601 with microseconds + "Z"     | `"2022-02-22T12:00:00.123456Z"` | Includes fractional seconds (microseconds).    |
| ISO 8601 with explicit timezone      | `"2022-02-22T14:00:00+02:00"`  | Timezone-aware, properly converted to UTC.     |
| ISO 8601 with offset (-/+)           | `"2022-02-22T10:00:00-02:00"`  | Adjusts time based on timezone offset.        |

✅ All timestamps are converted to UTC before returning a Unix timestamp (seconds).



---

### **2️⃣ Storage in Redis**
We store the metric **separately for each field** while keeping **all tags**.

#### **Key Format for Redis**
```
moniflow:metrics:{measurement}:{sorted_tags}:{field_name}
```

#### **Actual Redis Keys Created**
```
moniflow:metrics:cpu_usage:group=alpha:host=server-1:usage
moniflow:metrics:cpu_usage:group=alpha:host=server-1:temperature
```

#### **Storing in Redis (`ZADD`)**
Each field is stored in **a sorted set** using `ZADD`:

```sh
ZADD moniflow:metrics:cpu_usage:group=alpha:host=server-1:usage 1700000000 90.3
ZADD moniflow:metrics:cpu_usage:group=alpha:host=server-1:temperature 1700000000 60.0
```

---

### **3️⃣ Alert Rules Are Checked**
A user may have **multiple alert rules**:

#### **Rule 1**: **Trigger if `cpu_usage.usage` is > 85.0 for 5 minutes**
```json
{
    "metric_name": "cpu_usage",
    "tags": {"host": "server-1"},
    "field_name": "usage",
    "threshold": 85.0,
    "duration_value": 5,
    "duration_unit": "minutes",
    "comparison": ">",
    "notification_channels": ["telegram"],
    "recipients": {
        "telegram": ["@admin"]
    },
    "use_recovery_alert": true,
    "recovery_time_value": 10,
    "recovery_time_unit": "seconds"
}
```

#### **Rule 2**: **Trigger if `cpu_usage.temperature` is > 70.0 for 10 minutes**
```json
{
    "metric_name": "cpu_usage",
    "tags": {"group": "alpha"},
    "field_name": "temperature",
    "threshold": 70.0,
    "duration_value": 10,
    "duration_unit": "minutes",
    "comparison": ">",
    "notification_channels": ["email"],
    "recipients": {
        "email": ["admin@example.com"]
    }
}
```

---

### **4️⃣ Query Redis for Metrics in the Last N Minutes**
Each alert rule checks **only its corresponding field and tags**.

#### **Finding Matching Redis Keys**
1. Convert **alert rule tags** to Redis **key pattern**:
   - Rule 1 (`host=server-1`):
     ```
     moniflow:metrics:cpu_usage:host=server-1:usage
     ```
   - Rule 2 (`group=alpha`):
     ```
     moniflow:metrics:cpu_usage:group=alpha:temperature
     ```

2. **Retrieve metrics from Redis** for the last `N` minutes:
```sh
ZRANGEBYSCORE moniflow:metrics:cpu_usage:host=server-1:usage 1700000000 1700000300
ZRANGEBYSCORE moniflow:metrics:cpu_usage:group=alpha:temperature 1700000000 1700000600
```

---

### **5️⃣ Evaluating Alerts**
The `Celery` task **processes the stored metrics** to see if an alert **should be triggered**.

#### **Python Code for Fetching Metrics from Redis**
```python
import redis
import time

def get_recent_metric_values(metric_name, field_name, rule_tags, duration_seconds):
    redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    sorted_tags = ":".join([f"{k}={v}" for k, v in sorted(rule_tags.items())])
    redis_key = f"moniflow:metrics:{metric_name}:{sorted_tags}:{field_name}"
    current_time = int(time.time())
    min_time = current_time - duration_seconds
    values = redis_client.zrangebyscore(redis_key, min_time, current_time)
    return [float(v) for v in values]
```

#### **Checking the Condition**
```python
def evaluate_alert(rule, recent_values):
    comparison = rule["comparison"]
    threshold = rule["threshold"]
    if not recent_values:
        return False
    return all(
        (comparison == ">" and v > threshold) or
        (comparison == "<" and v < threshold) or
        (comparison == "==" and v == threshold)
        for v in recent_values
    )
```

#### **Sending an Alert**
```python
if evaluate_alert(rule, recent_values):
    send_alert(rule, recent_values)
```

---

### **6️⃣ Removing Old Metrics from Redis**
#### **Python Code for Cleaning Redis**
```python
def remove_old_metrics(metric_name, field_name, rule_tags, max_age_seconds):
    redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    sorted_tags = ":".join([f"{k}={v}" for k, v in sorted(rule_tags.items())])
    redis_key = f"moniflow:metrics:{metric_name}:{sorted_tags}:{field_name}"
    current_time = int(time.time())
    cutoff_time = current_time - max_age_seconds
    redis_client.zremrangebyscore(redis_key, "-inf", cutoff_time)
```

---

## **📌 Summary of the Full Process**

| **Step** | **Action** |
|----------|-----------|
| **1️⃣ Metric Ingestion** | The `/metrics/` endpoint receives the metric with multiple fields & tags. |
| **2️⃣ Storage in Redis** | Each **field** is stored separately in a **sorted set (`ZADD`)**. |
| **3️⃣ Fetching Alert Rules** | The **Celery worker** retrieves active alert rules. |
| **4️⃣ Querying Redis for Recent Metrics** | Uses `ZRANGEBYSCORE` to get recent values **within the rule duration**. |
| **5️⃣ Evaluating Alert Conditions** | Checks if **all values exceed the threshold** using `evaluate_alert()`. |
| **6️⃣ Sending Notifications** | If conditions are met, sends a **Telegram / Email alert**. |
| **7️⃣ Cleaning Old Data** | Periodically **removes old metrics** using `ZREMRANGEBYSCORE`. |

---

# 🌊 Logs vs. Metrics – Their Role in MoniFlow

MoniFlow's Metrics Collector gathers both logs and metrics, but they serve different purposes:

| Data Type | Purpose in MoniFlow | Used by Alert Service? | Used by Dashboard? |
|-----------|---------------------|------------------------|---------------------|
| **Metrics** | Performance & health tracking (e.g., CPU, memory, request latency) | ✅ Yes (for threshold-based alerting) | ✅ Yes (for visualization) |
| **Logs** | Debugging & error tracking (e.g., stack traces, HTTP failures) | ❌ No (not directly used for alerts) | ✅ Yes (for log visualization) |

## 1️⃣ Metrics → Alert Service (Threshold-Based Alerting)
Metrics are numerical values over time (e.g., `cpu_usage=85%`, `response_time=200ms`).

- Alert Service listens for metric updates and triggers alerts if thresholds are exceeded.
- Redis is used to track time-based conditions before firing alerts.

### ✅ Examples of Alerts Based on Metrics:
- "CPU usage > 80% for 5 minutes"
- "Memory usage < 20% for 10 minutes"
- "Response time > 500ms for 3 minutes"

## 2️⃣ Logs → Dashboard Service (Observability & Debugging)
Logs contain text-based messages (e.g., error messages, event descriptions).

- Logs don’t have numerical thresholds, so they are not used for alerts.
- Instead, logs are forwarded to Dashboard Service, which provides:
  - **Log search & filtering**
  - **Log visualization** (e.g., recent errors)
  - **Tracing for debugging issues**

### ✅ Examples of Logs in Dashboard:
- `[ERROR] Service X failed due to database timeout.`
- `[INFO] User X logged in successfully.`
- `[WARN] High number of failed requests detected.`

## 🚀 Summary of Responsibilities

| Service | Responsibilities |
|---------|-----------------|
| **Metrics Collector** | Collects both metrics and logs, then forwards them to the appropriate services. |
| **Alert Service** | Uses metrics to trigger alerts (based on thresholds & duration). |
| **Dashboard Service** | Displays both logs and metrics for monitoring & debugging (but doesn’t generate alerts). |





| State           | Key Format                          | Value        | Expires    | Purpose                                      |
|-----------------|-------------------------------------|--------------|------------|----------------------------------------------|
| Active Alert    | `moniflow:alert_state:{rule_id}`    | "triggered"  | 5 minutes  | Prevents duplicate alerts                    |
| Recovery Alert  | `moniflow:recovery_state:{rule_id}` | "recovered"  | 10 minutes | Ensures recovery alerts are only sent once   |


📖 Strict Timestamp Rules
| Timestamp Format               | Valid? | Reason                                    |
|--------------------------------|--------|-------------------------------------------|
| "2025-02-26T12:00:00Z"         | ✅ YES | UTC timezone explicitly provided          |
| "2025-02-26T14:00:00+02:00"    | ✅ YES | Explicit timezone, converted to UTC       |
| "2025-02-26T10:00:00-02:00"    | ✅ YES | Explicit timezone, converted to UTC       |
| "2025-02-26T12:00:00.123456Z"  | ✅ YES | Microseconds supported                    |
| "2025-02-26T12:00:00"          | ❌ NO  | Missing timezone (Ambiguous)              |
| "2025-02-26"                   | ❌ NO  | Date only, no time provided               |
| "not-a-timestamp"              | ❌ NO  | Completely invalid format                 |
| 1645531200                     | ❌ NO  | Unix timestamp not accepted (must be ISO 8601) |
