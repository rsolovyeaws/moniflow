from fastapi import APIRouter

router = APIRouter()

@router.post("/")
async def collect_logs(log_entry: dict):
    """
    Ingest logs data.
    """
    return {"status": "success", "log": log_entry}