import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from routers import auth, events, tickets, payments, social
from core.config import SECRET_KEY, IST
from utils.database import read_events, write_events, get_database_session
from core.config import USE_POSTGRESQL, DATABASE_URL
from services.cache_service import get_cache, set_cache, is_cache_healthy
from services.audit_service import audit_service, AuditSeverity
from core.rate_limits import get_rate_limit_config
from middleware.security_middleware import create_security_middleware
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

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

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

app = FastAPI(title="Fitness Event Booking API (IST)")

# Rate limiting setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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

# Add security middleware for audit logging and monitoring
app.add_middleware(create_security_middleware)

app.include_router(auth.router)
app.include_router(events.router)
app.include_router(tickets.router)
app.include_router(payments.router)
app.include_router(social.router)

# Ensure uploads directory exists
os.makedirs("uploads", exist_ok=True)

# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def root():
    return {"msg": "Fitness Event Booking API running (times shown in IST)."}

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
@limiter.limit("100/minute")
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

        # Audit admin action
        user_id = request.headers.get("X-User-ID")
        client_ip = request.client.host if request.client else "unknown"
        audit_service.log_admin_action(
            admin_user_id=user_id or "system",
            action="cache_clear",
            target="all_cache",
            ip_address=client_ip,
            details={"cleared_entries": cleared_count}
        )

        return {"message": f"Cleared {cleared_count} cache entries"}
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to clear cache", "details": str(e)}
        )

@app.get("/admin/audit-logs")
@limiter.limit("20/minute")
async def get_audit_logs(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    event_type: str = None,
    severity: str = None,
    user_id: str = None
):
    """Get audit logs (admin endpoint)"""
    try:
        # Check admin permissions
        current_user_id = request.headers.get("X-User-ID")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        from services.auth_service import auth_service, Permission
        if not auth_service.has_permission(current_user_id, Permission.VIEW_AUDIT_LOGS):
            raise HTTPException(status_code=403, detail="Admin access required")

        # Query audit events from database
        db = get_database_session()

        # Build query dynamically based on filters
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        if severity:
            query += " AND severity = ?"
            params.append(severity)

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        from sqlalchemy import text
        result = db.execute(text(query), params)
        rows = result.fetchall()
        db.close()

        # Convert to list of dictionaries
        audit_events = []
        for row in rows:
            audit_events.append({
                "id": row[0],
                "timestamp": row[1],
                "event_type": row[2],
                "severity": row[3],
                "user_id": row[4],
                "ip_address": row[5],
                "endpoint": row[6],
                "message": row[7],
                "details": row[8],
                "status_code": row[9],
                "error_message": row[10]
            })

        # Audit the admin action
        client_ip = request.client.host if request.client else "unknown"
        audit_service.log_admin_action(
            admin_user_id=current_user_id,
            action="view_audit_logs",
            target="audit_logs",
            ip_address=client_ip,
            details={
                "filters": {"event_type": event_type, "severity": severity, "user_id": user_id},
                "limit": limit,
                "offset": offset,
                "results_count": len(audit_events)
            }
        )

        return {
            "audit_events": audit_events,
            "total": len(audit_events),
            "filters_applied": {
                "event_type": event_type,
                "severity": severity,
                "user_id": user_id
            },
            "pagination": {
                "limit": limit,
                "offset": offset
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audit logs retrieval error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to retrieve audit logs", "details": str(e)}
        )

@app.get("/admin/security-events")
@limiter.limit("30/minute")
async def get_security_events(
    request: Request,
    limit: int = 50,
    hours: int = 24
):
    """Get recent security events (admin endpoint)"""
    try:
        # Check admin permissions
        current_user_id = request.headers.get("X-User-ID")
        if not current_user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        from services.auth_service import auth_service, Permission
        if not auth_service.has_permission(current_user_id, Permission.VIEW_AUDIT_LOGS):
            raise HTTPException(status_code=403, detail="Admin access required")

        # Query security events from database
        db = get_database_session()

        # Calculate time threshold
        from datetime import datetime, timedelta
        time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()

        query = """
            SELECT * FROM audit_events
            WHERE event_type = 'security'
            AND timestamp > ?
            ORDER BY timestamp DESC
            LIMIT ?
        """

        from sqlalchemy import text
        result = db.execute(text(query), (time_threshold, limit))
        rows = result.fetchall()
        db.close()

        # Convert to list of dictionaries
        security_events = []
        for row in rows:
            security_events.append({
                "id": row[0],
                "timestamp": row[1],
                "event_type": row[2],
                "severity": row[3],
                "user_id": row[4],
                "ip_address": row[5],
                "endpoint": row[6],
                "message": row[7],
                "details": row[8],
                "status_code": row[9],
                "error_message": row[10]
            })

        # Audit the admin action
        client_ip = request.client.host if request.client else "unknown"
        audit_service.log_admin_action(
            admin_user_id=current_user_id,
            action="view_security_events",
            target="security_events",
            ip_address=client_ip,
            details={
                "time_window_hours": hours,
                "limit": limit,
                "results_count": len(security_events)
            }
        )

        return {
            "security_events": security_events,
            "total": len(security_events),
            "time_window_hours": hours,
            "generated_at": datetime.now(IST).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Security events retrieval error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to retrieve security events", "details": str(e)}
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Railway injects PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
