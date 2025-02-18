from fastapi import APIRouter
from database import write_metric

router = APIRouter()

@router.post("/")
async def collect_metrics(data: dict):
    """
    Collects incoming metrics and stores them in InfluxDB.
    Example request:
    {
        "measurement": "cpu_usage",
        "tags": {"host": "server-1"},
        "fields": {"usage": 75.3}
    }
    """
    measurement = data.get("measurement", "default_metric")
    tags = data.get("tags", {})
    fields = data.get("fields", {})
    
    if not tags:
        return {"status": "error", "message": "At least one tag is required."}

    if not fields:
        return {"status": "error", "message": "At least one field is required."}

    write_metric(measurement, fields, tags)
    return {"status": "success", "message": f"Metric '{measurement}' stored."}
