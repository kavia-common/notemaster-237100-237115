"""
NoteMaster Backend API - Main Entry Point.

A FastAPI application providing RESTful endpoints for:
- User authentication (register, login, profile)
- Notes CRUD (create, read, update, delete)
- Note search (full-text search via PostgreSQL)
- Tags management (CRUD, attach to notes)
- Sync (push/pull for offline-first client support)

Title: NoteMaster API
Version: 1.0.0
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes_auth import router as auth_router
from src.api.routes_notes import router as notes_router
from src.api.routes_tags import router as tags_router
from src.api.routes_sync import router as sync_router

# OpenAPI tag definitions for grouped documentation
openapi_tags = [
    {
        "name": "Health",
        "description": "Health check endpoint",
    },
    {
        "name": "Authentication",
        "description": "User registration, login, and profile management with JWT tokens.",
    },
    {
        "name": "Notes",
        "description": "Create, read, update, delete, list, and search notes.",
    },
    {
        "name": "Tags",
        "description": "Create, list, update, and delete tags for organizing notes.",
    },
    {
        "name": "Sync",
        "description": "Push and pull endpoints for offline-first note synchronization.",
    },
]

app = FastAPI(
    title="NoteMaster API",
    description=(
        "Backend API for the NoteMaster notes application. "
        "Supports note CRUD, tagging, full-text search, JWT authentication, "
        "and offline-first synchronization."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# CORS configuration from environment variables
allowed_origins_str = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:4000",
)
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

allowed_methods_str = os.getenv("ALLOWED_METHODS", "GET,POST,PUT,DELETE,PATCH,OPTIONS")
allowed_methods = [m.strip() for m in allowed_methods_str.split(",") if m.strip()]

allowed_headers_str = os.getenv("ALLOWED_HEADERS", "Content-Type,Authorization,X-Requested-With")
allowed_headers = [h.strip() for h in allowed_headers_str.split(",") if h.strip()]

cors_max_age = int(os.getenv("CORS_MAX_AGE", "3600"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
    max_age=cors_max_age,
)

# Register routers
app.include_router(auth_router)
app.include_router(notes_router)
app.include_router(tags_router)
app.include_router(sync_router)


# PUBLIC_INTERFACE
@app.get("/", tags=["Health"], summary="Health check", description="Returns server health status.")
def health_check():
    """
    Health check endpoint.

    Returns:
        JSON object with health status message.
    """
    return {"status": "healthy", "service": "notemaster-api", "version": "1.0.0"}
