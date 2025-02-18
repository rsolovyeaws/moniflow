from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, HTTPException
import httpx
import logging
import os
import asyncio
from auth import verify_token
from starlette.responses import JSONResponse
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient
import traceback


load_dotenv()

REQUEST_TIMEOUT_SEC = int(os.getenv("REQUEST_TIMEOUT_SEC", 5))

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", force=True)
logger = logging.getLogger(__name__)
logger.info("API Gateway Starting...") 

# shared HTTPX client
http_client = None  

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event for setting up and tearing down resources."""
    global http_client
    http_client = httpx.AsyncClient()
    logger.info("HTTPX connection pool initialized")
    
    yield 
    
    await http_client.aclose()
    logger.info("HTTPX connection pool closed")


app = FastAPI(lifespan=lifespan)

client = AsyncClient()

# TODO: Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url} Headers: {dict(request.headers)}")
    try:
        response = await call_next(request)
        return response
    except Exception:
        logger.error(f"Error processing request: {traceback.format_exc()}")
        return JSONResponse(content={"detail": "Internal Server Error"}, status_code=500)

# Microservices URLs
MICROSERVICES = {
    "user_management": "http://user_management:8004",
    "collector": "http://collector:8001",   
    "alert_service": "http://alert_service:8003",
    "dashboard_service": "http://dashboard_service:8002",
}

# Endpoints that do not require authentication
EXCLUDED_PATHS = [
    "user_management/token",
    "user_management/refresh",
    "health"
]

@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint for monitoring."""
    return JSONResponse(status_code=200, content={"status": "ok", "message": "Gateway is healthy"})

async def forward_request(service: str, path: str, request: Request, token_payload: dict = None):
    """Forward requests to microservices, ensuring authentication and correct forwarding."""

    logger.info(f"Forwarding request to {service} with path {path}")
    if service not in MICROSERVICES:
        return JSONResponse(status_code=404, content={"error": f"Service {service} not found"})

    url = f"{MICROSERVICES[service]}/{path}"
    method = request.method
    headers = dict(request.headers)

    # Remove the host header so that the target service's hostname is used.
    headers.pop("host", None)
    
    if token_payload:
        headers["user"] = token_payload["sub"]

    try:
        body_bytes = await request.body()
        data = None
        content_type = headers.get("content-type", "")

        if body_bytes:
            if "application/json" in content_type:
                data = await request.json()
            elif "application/x-www-form-urlencoded" in content_type:
                form_data = await request.form()
                data = dict(form_data)
    except Exception:
        data = None

    headers.pop("content-length", None)

    try:
        response = await http_client.request(
            method,
            url,
            headers=headers,
            params=request.query_params,
            json=data if "application/json" in content_type else None,
            data=data if "application/x-www-form-urlencoded" in content_type else None,
            follow_redirects=True
        )

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )

    except asyncio.TimeoutError:
        return Response(content='{"error": "Request timed out"}', status_code=504, media_type="application/json")

    except httpx.RequestError:
        return Response(content='{"error": "Upstream service unreachable"}', status_code=502, media_type="application/json")


@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"]) 
async def proxy_request(service: str, path: str, request: Request):
    """API Gateway: Debugging request handling."""
    
    if path.endswith("/"):
        path = path[:-1]
    
    full_path = f"{service}/{path}"
    
    # Allow public access to authentication endpoints
    if any(full_path.startswith(ep) for ep in EXCLUDED_PATHS):
        return await forward_request(service, path, request)

    logger.info(f"Authenticating request for {full_path}")
    
    # Extract Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        logger.warning("No Authorization header provided.")
        raise HTTPException(status_code=401, detail="Authorization header missing")

    # Ensure header follows "Bearer <token>" format
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.error(f"Invalid Authorization header format: {auth_header}")
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    token = parts[1]
    token_payload = verify_token(token)  

    return await forward_request(service, path, request, token_payload)
