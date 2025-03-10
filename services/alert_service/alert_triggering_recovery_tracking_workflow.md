# 🚀 Complete Workflow: Alert Triggering & Recovery Tracking

## **1️⃣ Alert Rule Creation**
A **new alert rule** is created with the following conditions:
- **Trigger Condition:** `cpu_usage > 85% for 5 minutes`
- **Recovery Condition:** `cpu_usage ≤ 85% for 10 minutes`

### **📥 Alert Rule in JSON**
```json
{
    "rule_id": "alert_123",
    "metric_name": "cpu_usage",
    "tags": { "host": "server-1" },
    "field_name": "usage",
    "threshold": 85.0,
    "duration": 300,  // 5 minutes in seconds
    "comparison": ">",
    "notification_channels": ["telegram"],
    "recipients": { "telegram": ["@admin"] },
    "use_recovery_alert": true,
    "recovery_time": 600  // 10 minutes in seconds
}
```
✅ **Stored in MongoDB.**  

---

## **2️⃣ Incoming Metrics (Below Threshold, No Alert)**
**Incoming metrics:**
```json
[
    { "timestamp": "2025-03-10T12:00:00Z", "cpu_usage": 80.0 },
    { "timestamp": "2025-03-10T12:01:00Z", "cpu_usage": 83.0 },
    { "timestamp": "2025-03-10T12:02:00Z", "cpu_usage": 82.5 }
]
```
### **🚀 Evaluation:**
- All values are **≤ 85.0%**.
- ✅ **No alert triggered.**

---

## **3️⃣ Metrics Exceed Threshold, Alert is Triggered**
**New incoming metrics:**
```json
[
    { "timestamp": "2025-03-10T12:03:00Z", "cpu_usage": 86.0 },
    { "timestamp": "2025-03-10T12:04:00Z", "cpu_usage": 90.5 },
    { "timestamp": "2025-03-10T12:05:00Z", "cpu_usage": 88.0 },
    { "timestamp": "2025-03-10T12:06:00Z", "cpu_usage": 87.5 },
    { "timestamp": "2025-03-10T12:07:00Z", "cpu_usage": 89.0 }
]
```
### **🚀 Evaluation:**
- **All values in the last 5 minutes exceed 85.0%**.
- ✅ **Alert is triggered**.
- 🔥 **Stored in Redis:** `"moniflow:alert_state:alert_123" = "triggered"`
- 📜 **Logged in MongoDB as a triggered event**.

### **📜 Alert History Entry in MongoDB**
```json
{
    "rule_id": "alert_123",
    "metric_name": "cpu_usage",
    "tags": { "host": "server-1" },
    "field_name": "usage",
    "status": "triggered",
    "timestamp": "2025-03-10T12:07:00Z"
}
```
🚀 **Telegram Notification Sent!**  
**Message:** _"🚨 Alert! CPU usage has exceeded 85% on server-1."_

---

## **4️⃣ Metrics Stay Above Threshold (No Duplicate Alert)**
✅ **Prevents duplicate notifications**.

---

## **5️⃣ Metrics Drop Below Threshold, Recovery is Triggered**
**New incoming metrics drop below threshold:**
```json
[
    { "timestamp": "2025-03-10T12:11:00Z", "cpu_usage": 84.0 },
    { "timestamp": "2025-03-10T12:12:00Z", "cpu_usage": 80.5 },
    { "timestamp": "2025-03-10T12:13:00Z", "cpu_usage": 79.0 },
    { "timestamp": "2025-03-10T12:14:00Z", "cpu_usage": 78.5 },
    { "timestamp": "2025-03-10T12:15:00Z", "cpu_usage": 77.0 }
]
```
### **🚀 Evaluation:**
- **Last 5 minutes are all below 85.0%.**
- ✅ **Alert is marked as "recovered"**.
- 🔥 **Stored in Redis:** `"moniflow:alert_state:alert_123" = "recovered"`
- 📜 **Logged in MongoDB as a recovery event**.

### **📜 Recovery History Entry in MongoDB**
```json
{
    "rule_id": "alert_123",
    "metric_name": "cpu_usage",
    "tags": { "host": "server-1" },
    "field_name": "usage",
    "status": "recovered",
    "timestamp": "2025-03-10T12:15:00Z"
}
```
🚀 **Telegram Notification Sent!**  
**Message:** _"✅ CPU usage has returned to normal on server-1."_

---

## **6️⃣ Metrics Stay Normal, Recovery Alert is Reset**
✅ **No new recovery alert is sent.**

---

## **🔥 Final Summary**
| **Step** | **What Happens?** | **Where It's Stored?** |
|----------|----------------|----------------|
| **1️⃣ Alert Rule is Created** | Rule stored in MongoDB | ✅ `mongo_alert_rules` collection |
| **2️⃣ Metrics Are Below Threshold** | No alert triggered | ✅ No action |
| **3️⃣ Metrics Exceed Threshold** | Alert is **triggered** | ✅ Redis (`alert_state`), MongoDB (log entry), Telegram Notification |
| **4️⃣ Metrics Stay Above Threshold** | No duplicate alerts | ✅ Redis prevents spam |
| **5️⃣ Metrics Drop Below Threshold** | Recovery alert sent | ✅ Redis (`recovered`), MongoDB (log entry), Telegram Notification |
| **6️⃣ Metrics Stay Normal** | No duplicate recovery alerts | ✅ System is reset, waiting for new alerts |

