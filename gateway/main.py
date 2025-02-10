from fastapi import FastAPI
import httpx

app = FastAPI()

SERVICES = {
    "metrics": "http://metrics_collector:8001",
    "alerts": "http://alert_service:8002",
    "dashboard": "http://dashboard_service:8003",
    "user": "http://user_management:8004"
}

@app.get("/")
async def root():
    return {"message": "API Gateway Running"}

@app.get("/{service}/{endpoint:path}")
async def proxy(service: str, endpoint: str):
    if service not in SERVICES:
        return {"error": "Unknown service"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SERVICES[service]}/{endpoint}")
        return response.json()
