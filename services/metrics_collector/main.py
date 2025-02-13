from fastapi import FastAPI
from routers import metrics, logs

app = FastAPI(title="MoniFlow Metrics Collector")

app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
app.include_router(logs.router, prefix="/logs", tags=["logs"])

@app.get("/")
async def root():
    return {"message": "Metrics Collector Service Running"}