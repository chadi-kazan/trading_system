from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import api_router

app = FastAPI(
    title="Small-Cap Growth Dashboard API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Default allowed origins for local development
default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Allow additional origins from environment variable (comma-separated)
# Example: CORS_ORIGINS="https://example.com,https://app.example.com"
env_origins = os.getenv("CORS_ORIGINS", "")
if env_origins:
    additional_origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
    default_origins.extend(additional_origins)

# Default regex pattern for Vercel deployments
default_regex = r"https://trading-system.*\.vercel\.app"

# Allow custom regex pattern from environment variable
# Example: CORS_ORIGIN_REGEX="https://.*\.yourdomain\.com"
cors_regex = os.getenv("CORS_ORIGIN_REGEX", default_regex)

app.add_middleware(
    CORSMiddleware,
    allow_origins=default_origins,
    allow_origin_regex=cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", tags=["Meta"])
def index() -> dict[str, str]:
    return {
        "message": "Small-Cap Growth dashboard API",
        "docs": "/api/docs",
    }
