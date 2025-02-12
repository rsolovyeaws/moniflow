from contextlib import asynccontextmanager
from http.client import HTTPException
from fastapi import FastAPI, Request, Response
import httpx
import logging
import os
import asyncio
from auth import verify_token
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient
import traceback


load_dotenv()

GATEWAY_RATE_LIMIT=os.getenv("GATEWAY_RATE_LIMIT", "10")
REQUEST_TIMEOUT_SEC = int(os.getenv("REQUEST_TIMEOUT_SEC", 5))
limiter = Limiter(key_func=get_remote_address)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", force=True)
logger = logging.getLogger(__name__)
logger.info("API Gateway Starting...") 

# Store the shared HTTPX client
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

# Apply rate limiting to FastAPI
app.state.limiter = limiter

# WIP: Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to catch RateLimitExceeded errors and return 429
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {str(exc)}"}
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
    "metrics_collector": "http://metrics_collector:8002",
    "alert_service": "http://alert_service:8003",
    "dashboard_service": "http://dashboard_service:8001",
}

# Endpoints that do not require authentication
EXCLUDED_PATHS = [
    "user_management/token",
    "user_management/refresh",
    "health"
]

@app.get("/health", include_in_schema=False)
@app.get("/health/", include_in_schema=False)
async def health_check():
    """Health check endpoint for monitoring."""
    return JSONResponse(status_code=200, content={"status": "ok", "message": "Gateway is healthy"})

async def forward_request(service: str, path: str, request: Request, token_payload: dict = None):
    """Forward requests to microservices, ensuring proper JSON and form data forwarding."""

    if service not in MICROSERVICES:
        return {"error": "Service not found"}

    url = f"{MICROSERVICES[service]}/{path}"
    method = request.method
    headers = dict(request.headers)
    # Add user identity if token is verified
    if token_payload:
        headers["user"] = token_payload["sub"]

    # Detect content type
    content_type = headers.get("content-type", "")
    data = None

    # Read request body correctly
    try:
        body_bytes = await request.body()
        if body_bytes:
            if "application/x-www-form-urlencoded" in content_type:
                form_data = await request.form()
                data = dict(form_data)
            elif "application/json" in content_type:
                data = await request.json()
    except Exception:
        logger.warning("Failed to read request body. Ignoring it.")
        data = None

    logger.info(f"Forwarding {method} request to {url} with headers: {headers} and data: {data}")

    async with http_client as client:
        headers.pop("content-length", None)

        try:
            response = await asyncio.wait_for(
                client.request(
                    method,
                    url,
                    headers=headers,
                    params=request.query_params,
                    json=data if "application/json" in content_type else None,
                    data=data if "application/x-www-form-urlencoded" in content_type else None,
                ),
                timeout=REQUEST_TIMEOUT_SEC
            )

            logger.info(f"Response from {url}: {response.status_code} - {response.text}")
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

        except asyncio.TimeoutError:
            logger.error(f"Request to {url} timed out after {REQUEST_TIMEOUT_SEC} seconds")
            return Response(
                content='{"error": "Request timed out"}',
                status_code=504,
                media_type="application/json",
            )

        except httpx.RequestError as e:
            logger.error(f"Error communicating with {url}: {str(e)}")
            return Response(
                content='{"error": "Upstream service unreachable"}',
                status_code=502,
                media_type="application/json",
            )


@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
@limiter.limit(f"{GATEWAY_RATE_LIMIT}/minute") 
async def proxy_request(service: str, path: str, request: Request):
    """API Gateway: Debugging request handling."""
    if path.endswith("/"):
        path = path[:-1]
        
    full_path = f"{service}/{path}"
    
    # Allow public access to authentication endpoints
    if any(full_path.startswith(ep) for ep in EXCLUDED_PATHS):
        logger.info(f"Skipping authentication for {full_path}")
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
    
    # Verify token using `verify_token()`
    token_payload = verify_token(token)  

    return await forward_request(service, path, request, token_payload)
