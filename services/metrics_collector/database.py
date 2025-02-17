import os
import time
import queue
import threading
from datetime import datetime, timezone
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.flux_table import FluxRecord
from typing import List, Dict
from collections import defaultdict


# Load environment variables
load_dotenv()

# InfluxDB Configuration
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_ADMIN_TOKEN", "my-secret-token")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "my-org")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_DB", "moniflow")

# Log and Metric Processing Configuration
LOG_BATCH_SIZE = int(os.getenv("LOG_BATCH_SIZE", 10))
LOG_FLUSH_INTERVAL = int(os.getenv("LOG_FLUSH_INTERVAL", 5))
METRIC_BATCH_SIZE = int(os.getenv("METRIC_BATCH_SIZE", 10))
METRIC_FLUSH_INTERVAL = int(os.getenv("METRIC_FLUSH_INTERVAL", 5))

# Initialize InfluxDB client
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

# Queues for logs and metrics
log_queue = queue.Queue()
metric_queue = queue.Queue()

# Stop flag for graceful shutdown
stop_thread = False


# Log Processing
def process_logs():
    """Background thread to batch process log writes with time-based flushing."""
    last_flush_time = time.time()

    while not stop_thread:
        batch = []
        try:
            for _ in range(LOG_BATCH_SIZE):
                log_entry = log_queue.get(timeout=1)
                if log_entry:
                    point = (
                        Point("logs")
                        .tag("level", log_entry["level"])
                        .field("message", log_entry["message"])
                    )
                    for key, value in log_entry["tags"].items():
                        point = point.tag(key, value)

                    point = point.time(log_entry["timestamp"])
                    batch.append(point)
        except queue.Empty:
            pass  # No new logs, continue waiting

        # Check if batch is full OR if it's time to flush
        if batch or (time.time() - last_flush_time > LOG_FLUSH_INTERVAL):
            if batch:
                try:
                    write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=batch)
                    last_flush_time = time.time()
                except Exception as e:
                    print(f"Error writing logs to InfluxDB: {e}")

# Start log processing thread
log_thread = threading.Thread(target=process_logs, daemon=True)
log_thread.start()


# Metric Processing
def process_metrics():
    """Background thread to batch process metric writes with time-based flushing."""
    last_flush_time = time.time()

    while not stop_thread:
        batch = []
        try:
            for _ in range(METRIC_BATCH_SIZE):
                metric_entry = metric_queue.get(timeout=1)
                if metric_entry:
                    point = Point(metric_entry["measurement"])
                    for key, value in metric_entry["fields"].items():
                        point = point.field(key, value)
                    for key, value in metric_entry["tags"].items():
                        point = point.tag(key, value)
                    point = point.time(metric_entry["timestamp"])
                    batch.append(point)
        except queue.Empty:
            pass  # No new metrics, continue waiting

        # Check if batch is full OR if it's time to flush
        if batch or (time.time() - last_flush_time > METRIC_FLUSH_INTERVAL):
            if batch:
                try:
                    write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=batch)
                    last_flush_time = time.time()
                except Exception as e:
                    print(f"Error writing metrics to InfluxDB: {e}")

# Start metric processing thread
metric_thread = threading.Thread(target=process_metrics, daemon=True)
metric_thread.start()


# Metric Collection
def write_metric(measurement: str, fields: dict, tags: dict = None, timestamp: str = None):
    """
    Write a metric to InfluxDB asynchronously.
    """
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()
    if tags is None:
        tags = {}

    # Convert all numeric fields to float to avoid type conflicts
    for key in fields:
        if isinstance(fields[key], int):
            fields[key] = float(fields[key])

    metric_entry = {
        "measurement": measurement,
        "fields": fields,
        "tags": tags,
        "timestamp": timestamp
    }
    metric_queue.put(metric_entry)


# Log Collection
def write_log(message: str, level: str, tags: dict, timestamp: str = None):
    """
    Write a log entry to InfluxDB asynchronously.
    """
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()

    log_entry = {"message": message, "level": level, "tags": tags, "timestamp": timestamp}
    log_queue.put(log_entry)


# Flux for logs
def get_flux_query_for_logs(start: str = None, end: str = None, level: str = None, service: str = None) -> str:
    """
    Generate a Flux query to fetch logs from InfluxDB based on query parameters.
    """
    # Ensure start and end are in proper Flux string format
    start = f'"{start}"' if start else '"-1h"'
    end = f'"{end}"' if end else 'now()'

    # Start the base query
    base_query = f'from(bucket: "moniflow") |> range(start: {start}, stop: {end})'

    # Filter by measurement (logs)
    base_query += ' |> filter(fn: (r) => r["_measurement"] == "logs")'

    # Apply optional filters only if values are provided
    if level:
        base_query += f' |> filter(fn: (r) => r["level"] == "{level}")'
    if service:
        base_query += f' |> filter(fn: (r) => r["service"] == "{service}")'

    # Select relevant columns
    base_query += ' |> keep(columns: ["_time", "level", "service", "message"])'

    
    base_query = '''from(bucket: "moniflow")
  |> range(start: -1h, stop: now())
  |> filter(fn: (r) => r["_measurement"] == "logs")'''
    return base_query

def parse_flux_record(record: FluxRecord) -> Dict:
    """
    Converts an InfluxDB FluxRecord into a dictionary.
    Ensures that field values are extracted dynamically.
    """
    log_entry = {
        "time": record["_time"].isoformat(),
        "service": record["service"],  
        "level": record["level"]
    }

    # Extract message from `_value` when `_field` is "message"
    if record["_field"] == "message":
        log_entry["message"] = record["_value"]

    return log_entry


def execute_flux_query(query: str) -> List[Dict]:
    """
    Executes a Flux query in InfluxDB and returns the results as a list of dictionaries.
    """
    try:
        # Execute the query
        tables = client.query_api().query(query, org=INFLUXDB_ORG)

        results = []
        for table in tables:
            for record in table.records:
                results.append(parse_flux_record(record))

        return results

    except Exception as e:
        print(f"Error executing query: {e}")
        return []

def group_logs_by_service(logs: List[Dict]) -> Dict:
    """
    Groups logs by service name.
    """
    grouped_logs = defaultdict(list)

    for log in logs:
        service_name = log["service"]
        grouped_logs[service_name].append(log)

    return dict(grouped_logs)