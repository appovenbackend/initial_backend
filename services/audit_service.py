import logging
import json
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from core.config import IST
from utils.database import get_database_session
from sqlalchemy import text
import os

class AuditEventType(Enum):
    """Types of auditable events"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    PAYMENT = "payment"
    ADMIN_ACTION = "admin_action"
    SECURITY = "security"
    SYSTEM = "system"

class AuditSeverity(Enum):
    """Severity levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AuditService:
    """Structured audit logging service"""

    def __init__(self):
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        # Create audit log file handler
        if not os.path.exists("logs"):
            os.makedirs("logs")

        file_handler = logging.FileHandler("logs/audit.log")
        file_handler.setLevel(logging.INFO)

        # Create formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s | %(event_type)s | %(severity)s | %(user_id)s | %(ip_address)s | %(endpoint)s | %(message)s | %(details)s'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Also log to main app logger for monitoring
        self.app_logger = logging.getLogger("app")

    def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        message: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """Log a structured audit event"""

        # Prepare log data
        log_data = {
            'timestamp': datetime.now(IST).isoformat(),
            'event_type': event_type.value,
            'severity': severity.value,
            'user_id': user_id or 'anonymous',
            'ip_address': ip_address or 'unknown',
            'endpoint': endpoint or 'unknown',
            'message': message,
            'details': json.dumps(details) if details else '{}',
            'status_code': status_code,
            'error_message': error_message
        }

        # Log to audit file
        self.logger.info(
            f"AUDIT_EVENT | {log_data['event_type']} | {log_data['severity']} | "
            f"{log_data['user_id']} | {log_data['ip_address']} | {log_data['endpoint']} | "
            f"{log_data['message']} | {log_data['details']}",
            extra=log_data
        )

        # Also log to main app logger with appropriate level
        if severity == AuditSeverity.CRITICAL:
            self.app_logger.critical(f"AUDIT_CRITICAL: {message}", extra=log_data)
        elif severity == AuditSeverity.HIGH:
            self.app_logger.error(f"AUDIT_HIGH: {message}", extra=log_data)
        elif severity == AuditSeverity.MEDIUM:
            self.app_logger.warning(f"AUDIT_MEDIUM: {message}", extra=log_data)
        else:
            self.app_logger.info(f"AUDIT_LOW: {message}", extra=log_data)

        # Store in database for admin access
        self._store_audit_event(log_data)

    def _store_audit_event(self, log_data: Dict[str, Any]):
        """Store audit event in database for admin access"""
        try:
            db = get_database_session()

            # Create audit_events table if it doesn't exist
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    user_id TEXT,
                    ip_address TEXT,
                    endpoint TEXT,
                    message TEXT NOT NULL,
                    details TEXT,
                    status_code INTEGER,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Insert audit event
            db.execute(text("""
                INSERT INTO audit_events
                (timestamp, event_type, severity, user_id, ip_address, endpoint, message, details, status_code, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """), (
                log_data['timestamp'],
                log_data['event_type'],
                log_data['severity'],
                log_data['user_id'],
                log_data['ip_address'],
                log_data['endpoint'],
                log_data['message'],
                log_data['details'],
                log_data['status_code'],
                log_data['error_message']
            ))

            db.commit()
            db.close()

        except Exception as e:
            # Don't let audit logging break the application
            self.app_logger.error(f"Failed to store audit event: {str(e)}")

    # Convenience methods for common audit events
    def log_authentication(self, user_id: str, success: bool, ip_address: str, endpoint: str, details: Optional[Dict] = None):
        """Log authentication events"""
        severity = AuditSeverity.LOW if success else AuditSeverity.MEDIUM
        message = f"User {'logged in successfully' if success else 'failed to log in'}"

        self.log_event(
            AuditEventType.AUTHENTICATION,
            severity,
            message,
            user_id=user_id,
            ip_address=ip_address,
            endpoint=endpoint,
            details=details,
            status_code=200 if success else 401
        )

    def log_payment_event(self, user_id: str, event_type: str, amount: float, ip_address: str, details: Optional[Dict] = None):
        """Log payment-related events"""
        self.log_event(
            AuditEventType.PAYMENT,
            AuditSeverity.MEDIUM,
            f"Payment {event_type}",
            user_id=user_id,
            ip_address=ip_address,
            details={**details, 'amount': amount} if details else {'amount': amount}
        )

    def log_admin_action(self, admin_user_id: str, action: str, target: str, ip_address: str, details: Optional[Dict] = None):
        """Log administrative actions"""
        self.log_event(
            AuditEventType.ADMIN_ACTION,
            AuditSeverity.HIGH,
            f"Admin action: {action} on {target}",
            user_id=admin_user_id,
            ip_address=ip_address,
            details=details
        )

    def log_security_event(self, event: str, severity: AuditSeverity, ip_address: str, details: Optional[Dict] = None):
        """Log security-related events"""
        self.log_event(
            AuditEventType.SECURITY,
            severity,
            f"Security event: {event}",
            ip_address=ip_address,
            details=details
        )

    def log_data_modification(self, user_id: str, operation: str, table_name: str, record_id: str, ip_address: str, details: Optional[Dict] = None):
        """Log data modification events"""
        self.log_event(
            AuditEventType.DATA_MODIFICATION,
            AuditSeverity.MEDIUM,
            f"Data {operation} in {table_name}",
            user_id=user_id,
            ip_address=ip_address,
            details={**details, 'table': table_name, 'record_id': record_id} if details else {'table': table_name, 'record_id': record_id}
        )

# Global audit service instance
audit_service = AuditService()
