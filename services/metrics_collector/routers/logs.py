from fastapi import APIRouter, HTTPException, Query
from database import group_logs_by_service, write_log, get_flux_query_for_logs, execute_flux_query
from pydantic import BaseModel, Field
from datetime import datetime, timezone

router = APIRouter()

class LogEntry(BaseModel):
    message: str = Field(..., example="Service restarted")
    level: str = Field(..., example="INFO")
    tags: dict = Field(default={}, example={"service": "user_management"})
    timestamp: datetime = Field(default=None, example="2025-02-13T12:30:00.000Z")

@router.post("/")
async def collect_logs(log_entry: LogEntry):
    """
    Ingest logs data.
    {
        "message": "Service restarted",
        "level": "INFO",
        "tags": {"service": "user_management"},
        "timestamp": "2025-02-13T12:30:00.000Z"
    }

    """
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if log_entry.level not in valid_levels:
        raise HTTPException(status_code=400, detail="Invalid log level provided.")
    
    timestamp = log_entry.timestamp or datetime.now(timezone.utc).isoformat()
    
    try:
        write_log(log_entry.message, log_entry.level, log_entry.tags, timestamp)
        return {"status": "success", "log": log_entry.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/")
async def get_logs(
    start: str = Query(None, description="Start timestamp in ISO format or relative time (e.g. -1h)"),
    end: str = Query(None, description="End timestamp in ISO format or relative time (e.g. -1h)"),
    level: str = Query(None, description="Log level"),
    service: str = Query(None, description="Service name")
):
    """
    Retrieve logs data based on query parameters.
    """
    filters = {
        "start": start,
        "end": end,
        "level": level,
        "service": service
    }
    flux_query = get_flux_query_for_logs(start, end, level, service)
    results = execute_flux_query(flux_query)
    grouped_logs = group_logs_by_service(results)
    return {"filters": filters, "flux_query": flux_query, "results": results, "grouped_logs": grouped_logs}
    
