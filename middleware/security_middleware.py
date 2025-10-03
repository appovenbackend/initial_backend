import time
import logging
from typing import Callable, Dict, Any
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from services.audit_service import audit_service, AuditEventType, AuditSeverity
from core.rate_limits import get_rate_limit_config
from services.auth_service import auth_service, Permission

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware for audit logging and monitoring"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        endpoint = str(request.url.path)
        method = request.method

        # Get user ID if available
        user_id = request.headers.get("X-User-ID")

        # Log incoming request
        await self._log_request(request, client_ip, user_id)

        # Check for suspicious patterns
        await self._check_suspicious_activity(request, client_ip)

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log successful response
            await self._log_response(
                request, response, client_ip, user_id, process_time, success=True
            )

            # Add security headers to response
            self._add_security_headers(response)

            return response

        except HTTPException as http_exc:
            # Log HTTP exceptions (4xx, 5xx)
            process_time = time.time() - start_time
            await self._log_response(
                request, http_exc, client_ip, user_id, process_time, success=False, error=str(http_exc.detail)
            )

            # Re-raise the exception
            raise

        except Exception as exc:
            # Log unexpected exceptions
            process_time = time.time() - start_time
            await self._log_response(
                request, None, client_ip, user_id, process_time, success=False, error=str(exc)
            )

            # Log as security event if it looks suspicious
            if self._is_suspicious_error(exc):
                audit_service.log_security_event(
                    f"Unexpected error in {method} {endpoint}",
                    AuditSeverity.HIGH,
                    client_ip,
                    {
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                        "endpoint": endpoint,
                        "method": method,
                        "user_id": user_id
                    }
                )

            # Re-raise the exception
            raise

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Check for forwarded IP (behind proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fallback to client host
        return request.client.host if request.client else "unknown"

    async def _log_request(self, request: Request, client_ip: str, user_id: str):
        """Log incoming request for audit purposes"""
        endpoint = str(request.url.path)
        method = request.method

        # Get request body for POST/PUT requests (limit size for security)
        body = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if body_bytes and len(body_bytes) < 10000:  # Limit body logging size
                    body = body_bytes.decode('utf-8', errors='ignore')
            except Exception:
                body = "[Unable to read body]"

        # Log based on endpoint sensitivity
        if self._is_sensitive_endpoint(endpoint):
            audit_service.log_event(
                AuditEventType.DATA_ACCESS,
                AuditSeverity.MEDIUM,
                f"Incoming {method} request to {endpoint}",
                user_id=user_id,
                ip_address=client_ip,
                endpoint=endpoint,
                details={
                    "method": method,
                    "query_params": dict(request.query_params),
                    "body_size": len(body) if body else 0
                }
            )
        else:
            # Log less sensitive endpoints at lower level
            logger.info(f"Request: {method} {endpoint} from {client_ip}")

    async def _log_response(self, request: Request, response, client_ip: str, user_id: str, process_time: float, success: bool, error: str = None):
        """Log response for audit purposes"""
        endpoint = str(request.url.path)
        method = request.method

        # Determine severity based on response
        if not success:
            if response and hasattr(response, 'status_code'):
                status_code = response.status_code
            else:
                status_code = 500

            if status_code >= 500:
                severity = AuditSeverity.HIGH
            elif status_code >= 400:
                severity = AuditSeverity.MEDIUM
            else:
                severity = AuditSeverity.LOW
        else:
            severity = AuditSeverity.LOW

        # Prepare log details
        details = {
            "method": method,
            "status_code": response.status_code if response and hasattr(response, 'status_code') else "unknown",
            "process_time_ms": round(process_time * 1000, 2),
            "success": success
        }

        if error:
            details["error"] = error

        # Log the response
        audit_service.log_event(
            AuditEventType.DATA_ACCESS,
            severity,
            f"Response for {method} {endpoint}",
            user_id=user_id,
            ip_address=client_ip,
            endpoint=endpoint,
            details=details,
            status_code=response.status_code if response and hasattr(response, 'status_code') else None,
            error_message=error
        )

    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

    def _is_sensitive_endpoint(self, endpoint: str) -> bool:
        """Check if endpoint contains sensitive operations"""
        sensitive_patterns = [
            "/auth/",
            "/payments/",
            "/admin/",
            "/users/",
            "/social/connection-requests/",
            "/validate"
        ]

        return any(pattern in endpoint for pattern in sensitive_patterns)

    def _is_suspicious_error(self, error: Exception) -> bool:
        """Check if error pattern looks suspicious"""
        error_str = str(error).lower()

        suspicious_patterns = [
            "sql",
            "injection",
            "script",
            "eval",
            "exec",
            "import",
            "system",
            "os.",
            "subprocess"
        ]

        return any(pattern in error_str for pattern in suspicious_patterns)

    async def _check_suspicious_activity(self, request: Request, client_ip: str):
        """Check for suspicious activity patterns"""
        endpoint = str(request.url.path)
        method = request.method

        # Check for potential security threats
        suspicious_indicators = []

        # Check for SQL injection patterns in query parameters
        for key, value in request.query_params.items():
            if self._contains_sql_injection(str(value)):
                suspicious_indicators.append(f"Potential SQL injection in param '{key}'")

        # Check for XSS patterns in query parameters
        for key, value in request.query_params.items():
            if self._contains_xss(str(value)):
                suspicious_indicators.append(f"Potential XSS in param '{key}'")

        # Check for rapid requests from same IP (basic DDoS detection)
        if self._is_rapid_request_pattern(client_ip, endpoint):
            suspicious_indicators.append("Rapid request pattern detected")

        # Log suspicious activity if found
        if suspicious_indicators:
            audit_service.log_security_event(
                f"Suspicious activity detected: {'; '.join(suspicious_indicators)}",
                AuditSeverity.HIGH,
                client_ip,
                {
                    "endpoint": endpoint,
                    "method": method,
                    "indicators": suspicious_indicators,
                    "user_agent": request.headers.get("User-Agent", "unknown")
                }
            )

    def _contains_sql_injection(self, value: str) -> bool:
        """Check for basic SQL injection patterns"""
        sql_patterns = [
            "'", "\"", ";", "--", "/*", "*/", "union", "select", "drop", "insert", "update", "delete"
        ]

        value_lower = value.lower()
        return any(pattern in value_lower for pattern in sql_patterns)

    def _contains_xss(self, value: str) -> bool:
        """Check for basic XSS patterns"""
        xss_patterns = [
            "<script", "</script>", "javascript:", "vbscript:", "onload=", "onerror=", "onclick="
        ]

        value_lower = value.lower()
        return any(pattern in value_lower for pattern in xss_patterns)

    def _is_rapid_request_pattern(self, client_ip: str, endpoint: str) -> bool:
        """Basic check for rapid request patterns (simplified)"""
        # In a production system, you'd want to implement proper rate limiting
        # and track request patterns in Redis or a similar store

        # For now, just return False - this would be enhanced with proper tracking
        return False

# Factory function to create middleware instance
def create_security_middleware(app) -> SecurityMiddleware:
    """Create and return security middleware instance"""
    return SecurityMiddleware(app)
