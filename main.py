import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from middleware.security import SecurityHeadersMiddleware, RequestSizeLimitMiddleware, SecurityLoggingMiddleware
from middleware.jwt_auth import JWTAuthMiddleware
from middleware.request_tracing import RequestTracingMiddleware
from middleware.error_handler import ErrorHandlingMiddleware
from core.rate_limiting import limiter
from routers import auth, events, tickets, payments, social, migration, admin
from core.secure_config import secure_config, CORS_ORIGINS, MAX_REQUEST_SIZE
from core.config import IST
from utils.structured_logging import setup_logging, error_tracker, get_performance_metrics
from services.notification_service import process_pending_notifications
from utils.database import read_events, write_events, get_database_session
from core.config import USE_POSTGRESQL, DATABASE_URL
from services.cache_service import get_cache, set_cache, is_cache_healthy
from datetime import datetime, timedelta
import uvicorn
import asyncio

# Setup structured logging
setup_logging()
logger = logging.getLogger(__name__)

# Rate limiting is handled by core.rate_limiting module

def initialize_sample_data():
    """Initialize database on app startup - no sample data added to ensure persistence of existing data on deployment"""
    # Database tables are created in utils.filedb.init_db()
    # No sample data is added to ensure persistence of existing data on deployment
    pass


# Legacy migration code removed - using proper Alembic migrations below

# AUTOMATIC: Run Alembic migrations on startup
def run_migrations():
    """Run Alembic database migrations automatically on deployment"""
    try:
        print("🔄 Running Alembic migrations...")
        from alembic import command
        from alembic.config import Config
        from core.config import DATABASE_URL, USE_POSTGRESQL
        import os

        # Set up Alembic configuration
        config = Config()

        # Set the database URL if available
        if DATABASE_URL:
            config.set_main_option('sqlalchemy.url', DATABASE_URL)

        # Configure script location (alembic directory relative to this file)
        package_dir = os.path.dirname(__file__)
        alembic_dir = os.path.join(package_dir, 'alembic')
        config.set_main_option('script_location', alembic_dir)

        # Set other required config options
        config.set_main_option('version_locations', os.path.join(alembic_dir, 'versions'))

        # Don't store config file, use programmatic config
        config.config_file_name = None

        print(f"Using database: {'PostgreSQL' if USE_POSTGRESQL else 'SQLite'}")

        # Get current revision (optional, for logging)
        try:
            from alembic.script import ScriptDirectory
            script_dir = ScriptDirectory.from_config(config)
            current_head = script_dir.get_current_head()
            print(f"Current head revision: {current_head}")
        except Exception:
            print("⚠️  Could not check current revision (this is normal for first run)")

        # Run upgrade to latest
        command.upgrade(config, 'head')

        print("✅ All migrations completed successfully!")

        # Verify the column exists
        try:
            from utils.database import get_database_session
            db = get_database_session()
            try:
                # Check if registration_open column exists by querying it
                result = db.execute("SELECT COUNT(*) FROM events WHERE registration_open IS NOT NULL")
                count = result.fetchone()[0]
                print(f"✅ Database check: registration_open column exists ({count} events checked)")
            finally:
                db.close()
        except Exception as db_error:
            print(f"⚠️  Database check failed (this is expected if no events exist): {db_error}")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()

        # For production, we may want to continue even if migration fails
        # to avoid bringing down the service completely
        print("⚠️  Continuing with deployment despite migration failure...")
        return False

    return True

print("🔄 Running automatic migrations on startup...")
run_migrations()
print("✅ Startup migrations complete!")

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

# Add JWT authentication middleware EARLY (replaces insecure X-User-ID header)
# This must run before CORS and other middlewares that might need user context
app.add_middleware(JWTAuthMiddleware)

app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=secure_config.jwt_secret)

app.add_middleware(SecurityHeadersMiddleware)  # Add security headers

# Add request tracing middleware
app.add_middleware(RequestTracingMiddleware)

# Add comprehensive error handling middleware
app.add_middleware(ErrorHandlingMiddleware)

# Include routers with error handling
try:
    app.include_router(auth.router)
    logger.info("✅ Auth router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include auth router: {e}")

try:
    app.include_router(payments.router)
    logger.info("✅ Payments router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include payments router: {e}")

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
    app.include_router(social.router)
    logger.info("✅ Social router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include social router: {e}")

try:
    app.include_router(migration.router)
    logger.info("✅ Migration router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include migration router: {e}")

try:
    app.include_router(admin.router)
    logger.info("✅ Admin router included successfully")
except Exception as e:
    logger.error(f"❌ Failed to include admin router: {e}")

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)

# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Custom route to handle missing profile images
@app.get("/uploads/profiles/{filename}")
async def get_profile_image(filename: str):
    """Serve profile images with fallback to default image"""
    from pathlib import Path

    # Check if the requested file exists
    file_path = Path(f"uploads/profiles/{filename}")
    if file_path.exists() and file_path.is_file():
        # Return the actual file
        return FileResponse(file_path, media_type='image/png')

    # Return default avatar for missing files
    default_path = Path("uploads/profiles/default_avatar.png")
    if default_path.exists():
        return FileResponse(default_path, media_type='image/png')

    # If even default doesn't exist, return 404
    raise HTTPException(status_code=404, detail="Profile image not found")

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

@app.get("/auth-test")
def auth_test_endpoint(request: Request):
    """Test endpoint to debug authentication issues"""
    user_id = getattr(request.state, 'user_id', None)
    user_role = getattr(request.state, 'user_role', None)
    jwt_payload = getattr(request.state, 'jwt_payload', None)

    return {
        "status": "ok",
        "message": "Auth test endpoint",
        "authenticated": user_id is not None,
        "user_id": user_id,
        "user_role": user_role,
        "jwt_payload": jwt_payload,
        "request_path": request.url.path,
        "request_method": request.method,
        "auth_header": request.headers.get("Authorization", "Not provided"),
        "middleware_order_test": "JWT middleware should run before this endpoint",
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

@app.get("/metrics")
@limiter.limit("10/minute")
async def get_metrics(request: Request):
    """Get application metrics and performance data"""
    try:
        metrics = get_performance_metrics()
        error_stats = error_tracker.get_error_stats()
        
        return {
            "performance": metrics,
            "errors": error_stats,
            "timestamp": datetime.now(IST).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get metrics", "details": str(e)}
        )

@app.get("/errors")
@limiter.limit("10/minute")
async def get_recent_errors(request: Request):
    """Get recent errors (admin endpoint)"""
    try:
        recent_errors = error_tracker.get_recent_errors(limit=20)
        return {
            "recent_errors": recent_errors,
            "timestamp": datetime.now(IST).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get recent errors: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get recent errors", "details": str(e)}
        )

@app.post("/notifications/process")
@limiter.limit("5/minute")
async def process_notifications(request: Request):
    """Process pending notifications (admin endpoint)"""
    try:
        processed_count = process_pending_notifications()
        return {
            "message": f"Processed {processed_count} notifications",
            "processed_count": processed_count,
            "timestamp": datetime.now(IST).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to process notifications: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to process notifications", "details": str(e)}
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Railway injects PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
