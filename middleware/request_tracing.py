"""
Request Tracing Middleware
Provides comprehensive request tracing and correlation ID management
"""
import uuid
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any, Optional
from datetime import datetime
from core.config import IST
from utils.structured_logging import request_logger, track_error

logger = logging.getLogger(__name__)

class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracing and correlation"""
    
    def __init__(self, app, trace_headers: bool = True, trace_body: bool = False):
        super().__init__(app)
        self.trace_headers = trace_headers
        self.trace_body = trace_body
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Log request start
        await self._log_request_start(request)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log request completion
            await self._log_request_completion(request, response, duration)
            
            # Add tracing headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            
            return response
            
        except Exception as e:
            # Calculate duration for failed requests
            duration = time.time() - start_time
            
            # Log request failure
            await self._log_request_failure(request, e, duration)
            
            # Track error
            error_id = track_error(
                error_type="request_failure",
                error_message=str(e),
                context={
                    "method": request.method,
                    "url": str(request.url),
                    "duration": duration,
                    "request_id": request_id
                },
                request=request
            )
            
            # Re-raise the exception
            raise
    
    async def _log_request_start(self, request: Request):
        """Log request start"""
        try:
            request_data = {
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent"),
                "content_type": request.headers.get("content-type"),
                "content_length": request.headers.get("content-length"),
            }
            
            if self.trace_headers:
                request_data["headers"] = dict(request.headers)
            
            if self.trace_body and request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.body()
                    if body:
                        request_data["body"] = body.decode("utf-8")[:1000]  # Limit body size
                except Exception:
                    request_data["body"] = "[Unable to read body]"
            
            logger.info(f"Request started: {request.method} {request.url.path}", extra={
                "request_id": request.state.request_id,
                "request_data": request_data
            })
            
        except Exception as e:
            logger.error(f"Failed to log request start: {e}")
    
    async def _log_request_completion(self, request: Request, response: Response, duration: float):
        """Log request completion"""
        try:
            user_id = getattr(request.state, 'user_id', None)
            
            request_logger.log_request(
                request=request,
                response_status=response.status_code,
                duration=duration,
                user_id=user_id
            )
            
            # Log additional details for slow requests
            if duration > 5.0:  # Requests taking more than 5 seconds
                logger.warning(f"Slow request detected: {duration:.3f}s", extra={
                    "request_id": request.state.request_id,
                    "user_id": user_id,
                    "method": request.method,
                    "url": str(request.url),
                    "duration": duration,
                    "status_code": response.status_code
                })
            
        except Exception as e:
            logger.error(f"Failed to log request completion: {e}")
    
    async def _log_request_failure(self, request: Request, exception: Exception, duration: float):
        """Log request failure"""
        try:
            logger.error(f"Request failed: {request.method} {request.url.path}", extra={
                "request_id": request.state.request_id,
                "user_id": getattr(request.state, 'user_id', None),
                "method": request.method,
                "url": str(request.url),
                "duration": duration,
                "exception_type": type(exception).__name__,
                "exception_message": str(exception)
            })
            
        except Exception as e:
            logger.error(f"Failed to log request failure: {e}")

class CorrelationContext:
    """Context manager for correlation ID propagation"""
    
    def __init__(self, correlation_id: str = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self._previous_correlation_id = None
    
    def __enter__(self):
        # Store previous correlation ID if any
        self._previous_correlation_id = getattr(logging, '_correlation_id', None)
        
        # Set new correlation ID
        logging._correlation_id = self.correlation_id
        
        return self.correlation_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous correlation ID
        if self._previous_correlation_id:
            logging._correlation_id = self._previous_correlation_id
        else:
            delattr(logging, '_correlation_id')

class RequestContext:
    """Request context manager for storing request-specific data"""
    
    def __init__(self, request: Request):
        self.request = request
        self.request_id = getattr(request.state, 'request_id', None)
        self.user_id = getattr(request.state, 'user_id', None)
        self.user_role = getattr(request.state, 'user_role', None)
    
    def get_context_data(self) -> Dict[str, Any]:
        """Get context data for logging"""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "user_role": self.user_role,
            "method": self.request.method,
            "url": str(self.request.url),
            "client_ip": self.request.client.host,
            "user_agent": self.request.headers.get("user-agent")
        }
    
    def log_with_context(self, level: str, message: str, extra_data: Dict[str, Any] = None):
        """Log message with request context"""
        context_data = self.get_context_data()
        if extra_data:
            context_data.update(extra_data)
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.log(log_level, message, extra=context_data)

class PerformanceTracker:
    """Track performance metrics for requests"""
    
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0,
            "slow_requests": 0,
            "endpoint_stats": {}
        }
    
    def record_request(self, endpoint: str, duration: float, status_code: int):
        """Record request metrics"""
        self.metrics["total_requests"] += 1
        
        if 200 <= status_code < 400:
            self.metrics["successful_requests"] += 1
        else:
            self.metrics["failed_requests"] += 1
        
        if duration > 5.0:
            self.metrics["slow_requests"] += 1
        
        # Update average response time
        total_time = self.metrics["average_response_time"] * (self.metrics["total_requests"] - 1)
        self.metrics["average_response_time"] = (total_time + duration) / self.metrics["total_requests"]
        
        # Update endpoint stats
        if endpoint not in self.metrics["endpoint_stats"]:
            self.metrics["endpoint_stats"][endpoint] = {
                "count": 0,
                "total_time": 0,
                "average_time": 0,
                "success_count": 0,
                "error_count": 0
            }
        
        stats = self.metrics["endpoint_stats"][endpoint]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["average_time"] = stats["total_time"] / stats["count"]
        
        if 200 <= status_code < 400:
            stats["success_count"] += 1
        else:
            stats["error_count"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return self.metrics.copy()
    
    def reset_metrics(self):
        """Reset metrics"""
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0,
            "slow_requests": 0,
            "endpoint_stats": {}
        }

# Global instances
performance_tracker = PerformanceTracker()

# Convenience functions
def get_correlation_id() -> str:
    """Get current correlation ID"""
    return getattr(logging, '_correlation_id', str(uuid.uuid4()))

def set_correlation_id(correlation_id: str):
    """Set correlation ID"""
    logging._correlation_id = correlation_id

def with_correlation_id(correlation_id: str = None):
    """Context manager for correlation ID"""
    return CorrelationContext(correlation_id)

def get_request_context(request: Request) -> RequestContext:
    """Get request context"""
    return RequestContext(request)

def track_performance(endpoint: str, duration: float, status_code: int):
    """Track performance metrics"""
    performance_tracker.record_request(endpoint, duration, status_code)

def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics"""
    return performance_tracker.get_metrics()
