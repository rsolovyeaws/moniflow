import logging
from fastapi import APIRouter, Query
from database import write_metric
from typing import Optional
from database import (
    get_flux_query_for_metrics, 
    execute_flux_query_for_metrics, 
    group_metrics_by_tags
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", force=True)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/metrics")
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
    logger.info(f"collect_metrics data: {data}")
    
    measurement = data.get("measurement", "default_metric")
    tags = data.get("tags", {})
    fields = data.get("fields", {})
    
    if not tags:
        return {"status": "error", "message": "At least one tag is required."}

    if not fields:
        return {"status": "error", "message": "At least one field is required."}

    write_metric(measurement, fields, tags)
    return {"status": "success", "message": f"Metric '{measurement}' stored."}


@router.get("/")
async def get_metrics(
    measurement: str = Query(..., description="Metric name (e.g., cpu_usage)"),
    start: str = Query("-1h", description="Start timestamp (ISO format or relative time)"),
    end: str = Query("now()", description="End timestamp (ISO format or relative time)"),
    tags: Optional[str] = Query(None, description="Tag filters in key=value format, comma-separated (e.g., host=server-1,region=us)"),
    group_by_tags: bool = Query(True, description="Group results by tags"),
    limit: int = Query(1000, description="Limit the number of returned results"),
    aggregate: Optional[str] = Query(None, description="Aggregation function (e.g., mean, max, min, sum)"),
    aggregate_window: str = Query("1m", description="Aggregation window (e.g., 1m, 5m, 1h)")
):
    """
    Retrieve metrics data from InfluxDB with filtering, grouping, and aggregation.
    """

    # Convert tags to dictionary format
    tag_dict = {pair.split("=")[0]: pair.split("=")[1] for pair in tags.split(",")} if tags else None

    flux_query = get_flux_query_for_metrics(measurement, start, end, tag_dict, aggregate, aggregate_window,limit)
    results = execute_flux_query_for_metrics(flux_query)

    if group_by_tags:
        results = group_metrics_by_tags(results)

    return {"query": flux_query, "results": results}