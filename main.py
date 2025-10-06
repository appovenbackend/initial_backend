import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from middleware.security import SecurityHeadersMiddleware, RequestSizeLimitMiddleware, SecurityLoggingMiddleware
from core.rate_limiting import limiter
from routers import auth, events, tickets, payments, social, migration
from core.config import SECRET_KEY, IST, MAX_REQUEST_SIZE
from utils.database import read_events, write_events, get_database_session
from core.config import USE_POSTGRESQL, DATABASE_URL
from services.cache_service import get_cache, set_cache, is_cache_healthy
from datetime import datetime, timedelta
import uvicorn
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Rate limiting is handled by core.rate_limiting module

def initialize_sample_data():
    """Initialize database on app startup - no sample data added to ensure persistence of existing data on deployment"""
    # Database tables are created in utils.filedb.init_db()
    # No sample data is added to ensure persistence of existing data on deployment
    pass

# TEMPORARY: Run migration on startup (remove after migration completes)
def run_migration():
    """Run database migration to add missing columns"""
    try:
        from migrate_db import migrate_events_table, migrate_received_qr_tokens_table, migrate_users_table
        print("🔄 Running database migration on startup...")
        migrate_events_table()
        migrate_received_qr_tokens_table()
        migrate_users_table()
        print("✅ Migration completed successfully!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")

run_migration()

# Initialize database on startup
initialize_sample_data()

app = FastAPI(
    title="Fitness Event Booking API (IST)",
    description="Comprehensive API for fitness event booking, user management, and social features",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_prefix=""  # Ensure OpenAPI works at root level
)

# Rate limiting setup with enhanced security
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Security middleware (order matters!)
app.add_middleware(SecurityLoggingMiddleware)  # First - log all requests
app.add_middleware(RequestSizeLimitMiddleware, max_size=MAX_REQUEST_SIZE)  # Configurable limit
app.add_middleware(SecurityHeadersMiddleware)  # Add security headers

app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Include routers with error handling
try:
    app.include_router(auth.router)
    logger.info("✅ Auth router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include auth router: {e}")

try:
    app.include_router(events.router)
    logger.info("✅ Events router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include events router: {e}")

try:
    app.include_router(tickets.router)
    logger.info("✅ Tickets router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include tickets router: {e}")

try:
    app.include_router(payments.router)
    logger.info("✅ Payments router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include payments router: {e}")

try:
    app.include_router(social.router)
    logger.info("✅ Social router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include social router: {e}")

try:
    app.include_router(migration.router)
    logger.info("✅ Migration router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include migration router: {e}")

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)

# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def root():
    return {"msg": "Fitness Event Booking API running (times shown in IST)."}

@app.get("/test")
def test_endpoint():
    """Simple test endpoint that doesn't require authentication"""
    return {
        "status": "ok",
        "message": "Test endpoint working",
        "timestamp": datetime.now(IST).isoformat()
    }

@app.get("/openapi-test")
def openapi_test():
    """Test OpenAPI schema generation"""
    try:
        schema = app.openapi()
        return {
            "status": "success",
            "routes_count": len(schema.get("paths", {})),
            "title": schema.get("info", {}).get("title")
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# Custom exception handlers with better error handling for high concurrency
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP exception: {exc.detail} for {request.method} {request.url}")

    # Add request ID for tracking
    request_id = getattr(request.state, 'request_id', 'unknown')

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Request failed",
            "detail": exc.detail,
            "status_code": exc.status_code,
            "request_id": request_id,
            "timestamp": datetime.now(IST).isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)} for {request.method} {request.url}", exc_info=True)

    # Add request ID for tracking
    request_id = getattr(request.state, 'request_id', 'unknown')

    # Determine if this is a database-related error
    error_type = "unknown"
    if "connection" in str(exc).lower() or "database" in str(exc).lower():
        error_type = "database_connection"
    elif "timeout" in str(exc).lower():
        error_type = "timeout"
    elif "memory" in str(exc).lower():
        error_type = "memory"

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "error_type": error_type,
            "request_id": request_id,
            "timestamp": datetime.now(IST).isoformat()
        }
    )

@app.get("/health")
async def health_check(request: Request):
    """Enhanced health check endpoint with comprehensive monitoring"""
    try:
        logger.info("Health check initiated")

        # Test database connection with a simple query
        from sqlalchemy import text
        db = get_database_session()
        result = db.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        db.close()

        # Test user table exists and can be queried
        from utils.database import read_users
        users_count = len(read_users())

        # Test file system access
        try:
            with open("data/test.txt", "w") as f:
                f.write("test")
            os.remove("data/test.txt")
            file_system_status = "accessible"
        except Exception as fs_error:
            file_system_status = f"error: {str(fs_error)}"
            logger.warning(f"File system access issue: {fs_error}")

        # Check memory usage (basic)
        import psutil
        memory = psutil.virtual_memory()
        memory_usage = {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent
        }

        # Check cache health
        cache_health = is_cache_healthy()

        health_status = {
            "status": "healthy",
            "database": {
                "type": "PostgreSQL" if USE_POSTGRESQL else "SQLite",
                "postgresql_enabled": USE_POSTGRESQL,
                "database_url_present": bool(DATABASE_URL),
                "connection_test": "passed",
                "users_count": users_count
            },
            "file_system": file_system_status,
            "memory": memory_usage,
            "cache": {"healthy": cache_health},
            "timestamp": datetime.now(IST).isoformat(),
            "uptime": "N/A"  # Could be enhanced with process start time
        }

        logger.info(f"Health check completed: {health_status['status']}")
        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e),
                "database": {
                    "type": "PostgreSQL" if USE_POSTGRESQL else "SQLite",
                    "postgresql_enabled": USE_POSTGRESQL,
                    "database_url_present": bool(DATABASE_URL),
                    "connection_test": "failed"
                },
                "timestamp": datetime.now(IST).isoformat()
            }
        )

@app.get("/cache-stats")
@limiter.limit("50/minute")
async def get_cache_stats(request: Request):
    """Get cache statistics"""
    try:
        from services.cache_service import get_cache_stats
        stats = get_cache_stats()
        return {"cache_stats": stats}
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get cache stats", "details": str(e)}
        )

@app.post("/cache-clear")
@limiter.limit("10/minute")
async def clear_cache(request: Request):
    """Clear cache (admin endpoint)"""
    try:
        from services.cache_service import clear_cache_pattern
        cleared_count = clear_cache_pattern("*")
        return {"message": f"Cleared {cleared_count} cache entries"}
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to clear cache", "details": str(e)}
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Railway injects PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
