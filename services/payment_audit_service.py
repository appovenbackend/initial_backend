"""
Payment Audit Trail and Database Storage
Replaces in-memory payment tracking with persistent database storage
"""
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from core.config import IST
import json
import logging
from typing import Dict, Any, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

Base = declarative_base()

class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentOrderDB(Base):
    """Database model for payment orders"""
    __tablename__ = "payment_orders"
    
    id = Column(String, primary_key=True, index=True)
    razorpay_order_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    event_id = Column(String, nullable=False, index=True)
    amount_inr = Column(Integer, nullable=False)
    currency = Column(String, default="INR")
    status = Column(String, default=PaymentStatus.PENDING)
    receipt = Column(String, nullable=True)
    notes = Column(Text, nullable=True)  # JSON string
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
    expires_at = Column(String, nullable=True)
    
    # Relationships
    payments = relationship("PaymentDB", back_populates="order")
    tickets = relationship("TicketDB", back_populates="payment_order")

class PaymentDB(Base):
    """Database model for payment transactions"""
    __tablename__ = "payments"
    
    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("payment_orders.id"), nullable=False, index=True)
    razorpay_payment_id = Column(String, unique=True, nullable=True, index=True)
    razorpay_signature = Column(String, nullable=True)
    amount_paid = Column(Integer, nullable=True)
    currency = Column(String, default="INR")
    status = Column(String, nullable=False)
    method = Column(String, nullable=True)
    bank = Column(String, nullable=True)
    wallet = Column(String, nullable=True)
    vpa = Column(String, nullable=True)
    email = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    fee = Column(Integer, nullable=True)
    tax = Column(Integer, nullable=True)
    error_code = Column(String, nullable=True)
    error_description = Column(String, nullable=True)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)
    
    # Relationships
    order = relationship("PaymentOrderDB", back_populates="payments")

class PaymentAuditLogDB(Base):
    """Database model for payment audit logs"""
    __tablename__ = "payment_audit_logs"
    
    id = Column(String, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("payment_orders.id"), nullable=False, index=True)
    payment_id = Column(String, ForeignKey("payments.id"), nullable=True, index=True)
    action = Column(String, nullable=False)  # created, updated, verified, failed, etc.
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    details = Column(Text, nullable=True)  # JSON string with additional details
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(String, nullable=False)
    created_by = Column(String, nullable=True)  # user_id or system

class PaymentAuditService:
    """Service for managing payment audit trail"""
    
    def __init__(self):
        from utils.database import SessionLocal
        self.db = SessionLocal()
    
    def create_payment_order(self, order_data: Dict[str, Any]) -> str:
        """Create a new payment order with audit trail"""
        try:
            order_id = order_data["id"]
            
            # Create payment order record
            order_record = PaymentOrderDB(
                id=order_id,
                razorpay_order_id=order_data["razorpay_order_id"],
                user_id=order_data["user_id"],
                event_id=order_data["event_id"],
                amount_inr=order_data["amount_inr"],
                currency=order_data.get("currency", "INR"),
                status=PaymentStatus.PENDING,
                receipt=order_data.get("receipt"),
                notes=json.dumps(order_data.get("notes", {})),
                created_at=datetime.now(IST).isoformat(),
                updated_at=datetime.now(IST).isoformat(),
                expires_at=order_data.get("expires_at")
            )
            
            self.db.add(order_record)
            self.db.commit()
            
            # Create audit log
            self._create_audit_log(
                order_id=order_id,
                action="order_created",
                details={"order_data": order_data}
            )
            
            logger.info(f"Payment order created: {order_id}")
            return order_id
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create payment order: {e}")
            raise
    
    def update_payment_status(self, order_id: str, new_status: str, 
                            payment_data: Dict[str, Any] = None) -> bool:
        """Update payment status with audit trail"""
        try:
            order = self.db.query(PaymentOrderDB).filter(
                PaymentOrderDB.id == order_id
            ).first()
            
            if not order:
                logger.error(f"Payment order not found: {order_id}")
                return False
            
            old_status = order.status
            order.status = new_status
            order.updated_at = datetime.now(IST).isoformat()
            
            # Create payment record if payment_data provided
            if payment_data:
                payment_record = PaymentDB(
                    id=payment_data.get("id"),
                    order_id=order_id,
                    razorpay_payment_id=payment_data.get("razorpay_payment_id"),
                    razorpay_signature=payment_data.get("razorpay_signature"),
                    amount_paid=payment_data.get("amount_paid"),
                    currency=payment_data.get("currency", "INR"),
                    status=payment_data.get("status"),
                    method=payment_data.get("method"),
                    bank=payment_data.get("bank"),
                    wallet=payment_data.get("wallet"),
                    vpa=payment_data.get("vpa"),
                    email=payment_data.get("email"),
                    contact=payment_data.get("contact"),
                    fee=payment_data.get("fee"),
                    tax=payment_data.get("tax"),
                    error_code=payment_data.get("error_code"),
                    error_description=payment_data.get("error_description"),
                    created_at=datetime.now(IST).isoformat(),
                    updated_at=datetime.now(IST).isoformat()
                )
                self.db.add(payment_record)
            
            self.db.commit()
            
            # Create audit log
            self._create_audit_log(
                order_id=order_id,
                payment_id=payment_data.get("id") if payment_data else None,
                action="status_updated",
                old_status=old_status,
                new_status=new_status,
                details=payment_data
            )
            
            logger.info(f"Payment status updated: {order_id} {old_status} -> {new_status}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update payment status: {e}")
            return False
    
    def get_payment_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get payment order by ID"""
        try:
            order = self.db.query(PaymentOrderDB).filter(
                PaymentOrderDB.id == order_id
            ).first()
            
            if not order:
                return None
            
            return {
                "id": order.id,
                "razorpay_order_id": order.razorpay_order_id,
                "user_id": order.user_id,
                "event_id": order.event_id,
                "amount_inr": order.amount_inr,
                "currency": order.currency,
                "status": order.status,
                "receipt": order.receipt,
                "notes": json.loads(order.notes) if order.notes else {},
                "created_at": order.created_at,
                "updated_at": order.updated_at,
                "expires_at": order.expires_at
            }
            
        except Exception as e:
            logger.error(f"Failed to get payment order: {e}")
            return None
    
    def get_payment_audit_logs(self, order_id: str) -> List[Dict[str, Any]]:
        """Get audit logs for a payment order"""
        try:
            logs = self.db.query(PaymentAuditLogDB).filter(
                PaymentAuditLogDB.order_id == order_id
            ).order_by(PaymentAuditLogDB.created_at.desc()).all()
            
            return [
                {
                    "id": log.id,
                    "order_id": log.order_id,
                    "payment_id": log.payment_id,
                    "action": log.action,
                    "old_status": log.old_status,
                    "new_status": log.new_status,
                    "details": json.loads(log.details) if log.details else {},
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "created_at": log.created_at,
                    "created_by": log.created_by
                }
                for log in logs
            ]
            
        except Exception as e:
            logger.error(f"Failed to get payment audit logs: {e}")
            return []
    
    def _create_audit_log(self, order_id: str, action: str, 
                         payment_id: str = None, old_status: str = None,
                         new_status: str = None, details: Dict[str, Any] = None,
                         ip_address: str = None, user_agent: str = None,
                         created_by: str = None):
        """Create audit log entry"""
        try:
            audit_log = PaymentAuditLogDB(
                id=f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{order_id[:8]}",
                order_id=order_id,
                payment_id=payment_id,
                action=action,
                old_status=old_status,
                new_status=new_status,
                details=json.dumps(details) if details else None,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.now(IST).isoformat(),
                created_by=created_by or "system"
            )
            
            self.db.add(audit_log)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
    
    def cleanup_expired_orders(self) -> int:
        """Clean up expired payment orders"""
        try:
            now = datetime.now(IST).isoformat()
            expired_orders = self.db.query(PaymentOrderDB).filter(
                PaymentOrderDB.expires_at < now,
                PaymentOrderDB.status == PaymentStatus.PENDING
            ).all()
            
            count = 0
            for order in expired_orders:
                order.status = PaymentStatus.CANCELLED
                order.updated_at = now
                count += 1
                
                # Create audit log
                self._create_audit_log(
                    order_id=order.id,
                    action="order_expired",
                    old_status=PaymentStatus.PENDING,
                    new_status=PaymentStatus.CANCELLED
                )
            
            self.db.commit()
            logger.info(f"Cleaned up {count} expired payment orders")
            return count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to cleanup expired orders: {e}")
            return 0

# Global payment audit service instance
payment_audit_service = PaymentAuditService()
