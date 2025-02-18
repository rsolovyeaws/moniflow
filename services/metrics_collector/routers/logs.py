from fastapi import APIRouter, HTTPException, Query
from database import group_logs_by_service, group_logs_by_service_and_level, write_log, get_flux_query_for_logs, execute_flux_query
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from enum import Enum

router = APIRouter()

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
class LogEntry(BaseModel):
    message: str = Field(..., example="Service restarted")
    level: str = LogLevel
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
    service: str = Query(None, description="Service name"),
    group_by_level: bool = Query(False, description="Group logs by level inside each service")
):
    """
    Retrieve logs data based on query parameters.
    """
    flux_query = get_flux_query_for_logs(start, end, level, service)
    results = execute_flux_query(flux_query)
    
    if group_by_level:
        grouped_logs = group_logs_by_service_and_level(results)
    else:
        grouped_logs = group_logs_by_service(results)
    return grouped_logs
