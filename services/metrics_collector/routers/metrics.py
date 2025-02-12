from fastapi import APIRouter

router = APIRouter()

@router.post("/")
async def collect_metrics(data: dict):
    """
    Ingest metrics data.
    """
    return {"status": "success", "data": data}