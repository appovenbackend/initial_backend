"""
Structured Logging and Error Tracking System
Provides comprehensive logging with structured data and error tracking
"""
import logging
import json
import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import Request
from core.config import IST
import sys
import os

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(IST).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'event_id'):
            log_entry["event_id"] = record.event_id
        if hasattr(record, 'payment_id'):
            log_entry["payment_id"] = record.payment_id
        if hasattr(record, 'ip_address'):
            log_entry["ip_address"] = record.ip_address
        if hasattr(record, 'user_agent'):
            log_entry["user_agent"] = record.user_agent
        if hasattr(record, 'duration'):
            log_entry["duration"] = record.duration
        if hasattr(record, 'status_code'):
            log_entry["status_code"] = record.status_code
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_entry, ensure_ascii=False)

class ErrorTracker:
    """Centralized error tracking and monitoring"""
    
    def __init__(self):
        self.error_counts = {}
        self.recent_errors = []
        self.max_recent_errors = 100
    
    def track_error(self, error_type: str, error_message: str, 
                   context: Dict[str, Any] = None, request: Request = None):
        """Track error occurrence"""
        error_id = str(uuid.uuid4())
        timestamp = datetime.now(IST).isoformat()
        
        error_data = {
            "error_id": error_id,
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": timestamp,
            "context": context or {},
        }
        
        if request:
            error_data.update({
                "request_id": getattr(request.state, 'request_id', None),
                "user_id": getattr(request.state, 'user_id', None),
                "method": request.method,
                "url": str(request.url),
                "ip_address": request.client.host,
                "user_agent": request.headers.get("user-agent"),
            })
        
        # Add to recent errors
        self.recent_errors.append(error_data)
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors.pop(0)
        
        # Update error counts
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Log the error
        logger = logging.getLogger("error_tracker")
        logger.error(f"Error tracked: {error_type}", extra={
            "error_id": error_id,
            "error_type": error_type,
            "error_message": error_message,
            "context": context,
            "request_id": getattr(request.state, 'request_id', None) if request else None,
            "user_id": getattr(request.state, 'user_id', None) if request else None,
        })
        
        return error_id
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "error_counts": self.error_counts,
            "recent_errors_count": len(self.recent_errors),
            "total_errors": sum(self.error_counts.values()),
        }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors"""
        return self.recent_errors[-limit:]

class RequestLogger:
    """Request logging with structured data"""
    
    def __init__(self):
        self.logger = logging.getLogger("request_logger")
    
    def log_request(self, request: Request, response_status: int, 
                   duration: float, user_id: str = None):
        """Log request with structured data"""
        request_id = getattr(request.state, 'request_id', None)
        
        self.logger.info(f"Request completed", extra={
            "request_id": request_id,
            "user_id": user_id,
            "method": request.method,
            "url": str(request.url),
            "status_code": response_status,
            "duration": duration,
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
        })
    
    def log_security_event(self, event_type: str, request: Request, 
                          details: Dict[str, Any] = None):
        """Log security-related events"""
        request_id = getattr(request.state, 'request_id', None)
        
        self.logger.warning(f"Security event: {event_type}", extra={
            "request_id": request_id,
            "user_id": getattr(request.state, 'user_id', None),
            "event_type": event_type,
            "method": request.method,
            "url": str(request.url),
            "ip_address": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "details": details or {},
        })

class BusinessLogger:
    """Business event logging"""
    
    def __init__(self):
        self.logger = logging.getLogger("business_logger")
    
    def log_user_registration(self, user_id: str, registration_method: str, 
                            request: Request = None):
        """Log user registration event"""
        self.logger.info(f"User registered: {user_id}", extra={
            "event_type": "user_registration",
            "user_id": user_id,
            "registration_method": registration_method,
            "request_id": getattr(request.state, 'request_id', None) if request else None,
        })
    
    def log_event_creation(self, event_id: str, user_id: str, event_title: str,
                          request: Request = None):
        """Log event creation event"""
        self.logger.info(f"Event created: {event_id}", extra={
            "event_type": "event_creation",
            "event_id": event_id,
            "user_id": user_id,
            "event_title": event_title,
            "request_id": getattr(request.state, 'request_id', None) if request else None,
        })
    
    def log_payment_attempt(self, payment_id: str, user_id: str, amount: int,
                           status: str, request: Request = None):
        """Log payment attempt event"""
        self.logger.info(f"Payment attempted: {payment_id}", extra={
            "event_type": "payment_attempt",
            "payment_id": payment_id,
            "user_id": user_id,
            "amount": amount,
            "status": status,
            "request_id": getattr(request.state, 'request_id', None) if request else None,
        })
    
    def log_ticket_purchase(self, ticket_id: str, user_id: str, event_id: str,
                           amount: int, request: Request = None):
        """Log ticket purchase event"""
        self.logger.info(f"Ticket purchased: {ticket_id}", extra={
            "event_type": "ticket_purchase",
            "ticket_id": ticket_id,
            "user_id": user_id,
            "event_id": event_id,
            "amount": amount,
            "request_id": getattr(request.state, 'request_id', None) if request else None,
        })

def setup_logging():
    """Setup structured logging configuration"""
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with structured formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)
    
    # File handler for all logs
    file_handler = logging.FileHandler("logs/app.log")
    file_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.FileHandler("logs/errors.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(error_handler)
    
    # Security file handler
    security_handler = logging.FileHandler("logs/security.log")
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(StructuredFormatter())
    security_logger = logging.getLogger("request_logger")
    security_logger.addHandler(security_handler)
    
    # Business file handler
    business_handler = logging.FileHandler("logs/business.log")
    business_handler.setFormatter(StructuredFormatter())
    business_logger = logging.getLogger("business_logger")
    business_logger.addHandler(business_handler)
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# Global instances
error_tracker = ErrorTracker()
request_logger = RequestLogger()
business_logger = BusinessLogger()

# Convenience functions
def track_error(error_type: str, error_message: str, context: Dict[str, Any] = None, 
               request: Request = None) -> str:
    """Track error occurrence"""
    return error_tracker.track_error(error_type, error_message, context, request)

def log_request(request: Request, response_status: int, duration: float, user_id: str = None):
    """Log request with structured data"""
    request_logger.log_request(request, response_status, duration, user_id)

def log_security_event(event_type: str, request: Request, details: Dict[str, Any] = None):
    """Log security-related events"""
    request_logger.log_security_event(event_type, request, details)

def log_user_registration(user_id: str, registration_method: str, request: Request = None):
    """Log user registration event"""
    business_logger.log_user_registration(user_id, registration_method, request)

def log_event_creation(event_id: str, user_id: str, event_title: str, request: Request = None):
    """Log event creation event"""
    business_logger.log_event_creation(event_id, user_id, event_title, request)

def log_payment_attempt(payment_id: str, user_id: str, amount: int, status: str, request: Request = None):
    """Log payment attempt event"""
    business_logger.log_payment_attempt(payment_id, user_id, amount, status, request)

def log_ticket_purchase(ticket_id: str, user_id: str, event_id: str, amount: int, request: Request = None):
    """Log ticket purchase event"""
    business_logger.log_ticket_purchase(ticket_id, user_id, event_id, amount, request)

def get_performance_metrics() -> Dict[str, Any]:
    """Get application performance metrics"""
    import psutil
    import time

    # Get system metrics
    memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=1)
    disk = psutil.disk_usage('/')

    # Get process metrics
    process = psutil.Process()
    process_memory = process.memory_info()
    process_cpu = process.cpu_percent()

    # Get uptime (approximate)
    uptime_seconds = time.time() - process.create_time()

    return {
        "system": {
            "cpu_percent": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            },
            "disk": {
                "total": disk.total,
                "free": disk.free,
                "percent": disk.percent
            }
        },
        "process": {
            "cpu_percent": process_cpu,
            "memory_rss": process_memory.rss,
            "memory_vms": process_memory.vms,
            "uptime_seconds": uptime_seconds,
            "threads": process.num_threads(),
            "open_files": len(process.open_files())
        },
        "timestamp": datetime.now(IST).isoformat()
    }
