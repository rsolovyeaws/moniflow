import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

load_dotenv()

# InfluxDB Configuration
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_ADMIN_TOKEN", "my-secret-token")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "my-org")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_DB", "moniflow")

# Create a client connection
client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)

def write_metric(measurement: str, fields: dict, tags: dict = None):
    """
    Write a metric to InfluxDB.
    """
    point = Point(measurement)
    
    # Add tags if available
    if tags:
        for key, value in tags.items():
            point = point.tag(key, value)
    
    # Add fields
    for key, value in fields.items():
        point = point.field(key, value)
    
    write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)

def write_log(message: str, level: str, tags: dict, timestamp: str):
    """
    Write a log entry to InfluxDB.
    """
    point = Point("logs").tag("level", level).field("message", message)
    
    if tags:
        for key, value in tags.items():
            point = point.tag(key, value)
    
    if timestamp:
        point = point.time(timestamp)
    
    write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)