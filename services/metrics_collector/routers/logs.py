from fastapi import APIRouter, HTTPException
from database import write_log
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
