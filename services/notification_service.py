"""
Notification System
Provides comprehensive notification functionality for events, payments, and user activities
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import exc as sa_exc
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from core.config import IST
import json
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
import asyncio
import httpx
from core.config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET

logger = logging.getLogger(__name__)

Base = declarative_base()

class NotificationType(str, Enum):
    """Notification type enumeration"""
    EVENT_REMINDER = "event_reminder"
    EVENT_UPDATE = "event_update"
    EVENT_CANCELLED = "event_cancelled"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    TICKET_CONFIRMED = "ticket_confirmed"
    TICKET_CANCELLED = "ticket_cancelled"
    USER_WELCOME = "user_welcome"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_UPDATE = "account_update"

class NotificationChannel(str, Enum):
    """Notification channel enumeration"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"

class NotificationStatus(str, Enum):
    """Notification status enumeration"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"

class NotificationDB(Base):
    """Database model for notifications"""
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    notification_type = Column(String, nullable=False, index=True)
    channel = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    data = Column(Text, nullable=True)  # JSON string with additional data
    status = Column(String, default=NotificationStatus.PENDING, index=True)
    scheduled_at = Column(String, nullable=True)
    sent_at = Column(String, nullable=True)
    delivered_at = Column(String, nullable=True)
    read_at = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

class NotificationTemplateDB(Base):
    """Database model for notification templates"""
    __tablename__ = "notification_templates"
    
    id = Column(String, primary_key=True, index=True)
    template_name = Column(String, unique=True, nullable=False, index=True)
    notification_type = Column(String, nullable=False, index=True)
    channel = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=True)
    title = Column(String, nullable=False)
    message_template = Column(Text, nullable=False)
    variables = Column(Text, nullable=True)  # JSON string with template variables
    is_active = Column(Boolean, default=True)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

class NotificationService:
    """Service for managing notifications"""
    
    def __init__(self):
        from utils.database import SessionLocal
        self.db = SessionLocal()
        # Initialize templates only if the templates table exists; otherwise, continue startup
        try:
            self._initialize_templates()
        except (sa_exc.ProgrammingError, sa_exc.OperationalError) as e:
            # Most likely the table doesn't exist yet (e.g., before migrations). Skip initialization.
            self.db.rollback()
            logger.warning(
                "Skipping notification templates initialization; table may not exist yet",
                extra={"error": str(e)}
            )
    
    def _initialize_templates(self):
        """Initialize default notification templates"""
        templates = [
            {
                "template_name": "event_reminder_email",
                "notification_type": NotificationType.EVENT_REMINDER,
                "channel": NotificationChannel.EMAIL,
                "subject": "Event Reminder: {event_title}",
                "title": "Event Reminder",
                "message_template": "Hi {user_name},\n\nThis is a reminder that your event '{event_title}' is starting soon.\n\nEvent Details:\n- Date: {event_date}\n- Time: {event_time}\n- Venue: {venue}\n- Address: {address}\n\nWe look forward to seeing you there!\n\nBest regards,\nThe Event Team",
                "variables": json.dumps(["user_name", "event_title", "event_date", "event_time", "venue", "address"])
            },
            {
                "template_name": "payment_success_sms",
                "notification_type": NotificationType.PAYMENT_SUCCESS,
                "channel": NotificationChannel.SMS,
                "subject": None,
                "title": "Payment Successful",
                "message_template": "Hi {user_name}, your payment of ₹{amount} for {event_title} has been processed successfully. Your ticket is confirmed!",
                "variables": json.dumps(["user_name", "amount", "event_title"])
            },

            {
                "template_name": "user_welcome_email",
                "notification_type": NotificationType.USER_WELCOME,
                "channel": NotificationChannel.EMAIL,
                "subject": "Welcome to Our Event Platform!",
                "title": "Welcome!",
                "message_template": "Hi {user_name},\n\nWelcome to our event platform! We're excited to have you join our community.\n\nYou can now:\n- Browse and book events\n- Connect with other fitness enthusiasts\n- Track your event history\n- Manage your profile\n\nIf you have any questions, feel free to reach out to us.\n\nHappy eventing!\nThe Team",
                "variables": json.dumps(["user_name"])
            }
        ]
        
        try:
            for template_data in templates:
                existing = self.db.query(NotificationTemplateDB).filter(
                    NotificationTemplateDB.template_name == template_data["template_name"]
                ).first()
                
                if not existing:
                    template = NotificationTemplateDB(
                        id=f"template_{template_data['template_name']}",
                        template_name=template_data["template_name"],
                        notification_type=template_data["notification_type"],
                        channel=template_data["channel"],
                        subject=template_data["subject"],
                        title=template_data["title"],
                        message_template=template_data["message_template"],
                        variables=template_data["variables"],
                        created_at=datetime.now(IST).isoformat(),
                        updated_at=datetime.now(IST).isoformat()
                    )
                    self.db.add(template)
            
            self.db.commit()
        except (sa_exc.ProgrammingError, sa_exc.OperationalError) as e:
            # Table missing or not migrated yet
            self.db.rollback()
            logger.warning(
                "Notification templates not initialized; table missing",
                extra={"error": str(e)}
            )
    
    def create_notification(self, user_id: str, notification_type: NotificationType,
                           channel: NotificationChannel, title: str, message: str,
                           data: Dict[str, Any] = None, scheduled_at: str = None) -> str:
        """Create a new notification"""
        try:
            notification_id = f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id[:8]}"
            
            notification = NotificationDB(
                id=notification_id,
                user_id=user_id,
                notification_type=notification_type,
                channel=channel,
                title=title,
                message=message,
                data=json.dumps(data) if data else None,
                scheduled_at=scheduled_at,
                created_at=datetime.now(IST).isoformat(),
                updated_at=datetime.now(IST).isoformat()
            )
            
            self.db.add(notification)
            self.db.commit()
            
            logger.info(f"Notification created: {notification_id}")
            return notification_id
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create notification: {e}")
            raise
    
    def send_notification_from_template(self, user_id: str, template_name: str,
                                     variables: Dict[str, Any], scheduled_at: str = None) -> str:
        """Send notification using a template"""
        try:
            template = self.db.query(NotificationTemplateDB).filter(
                NotificationTemplateDB.template_name == template_name,
                NotificationTemplateDB.is_active == True
            ).first()
            
            if not template:
                raise ValueError(f"Template not found: {template_name}")
            
            # Replace variables in template
            message = template.message_template
            title = template.title
            subject = template.subject
            
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                message = message.replace(placeholder, str(value))
                title = title.replace(placeholder, str(value))
                if subject:
                    subject = subject.replace(placeholder, str(value))
            
            # Create notification
            notification_id = self.create_notification(
                user_id=user_id,
                notification_type=template.notification_type,
                channel=template.channel,
                title=title,
                message=message,
                data={"template_name": template_name, "variables": variables},
                scheduled_at=scheduled_at
            )
            
            return notification_id
            
        except Exception as e:
            logger.error(f"Failed to send notification from template: {e}")
            raise
    
    def send_event_reminder(self, user_id: str, event_data: Dict[str, Any], 
                           reminder_hours: int = 24) -> str:
        """Send event reminder notification"""
        try:
            # Calculate reminder time
            from dateutil import parser
            event_start = parser.isoparse(event_data["startAt"])
            reminder_time = event_start - timedelta(hours=reminder_hours)
            
            if reminder_time <= datetime.now(IST):
                logger.warning(f"Event reminder time has passed for event {event_data['id']}")
                return None
            
            variables = {
                "user_name": event_data.get("user_name", "User"),
                "event_title": event_data["title"],
                "event_date": event_start.strftime("%B %d, %Y"),
                "event_time": event_start.strftime("%I:%M %p"),
                "venue": event_data["venue"],
                "address": event_data.get("address", "Check event details")
            }
            
            return self.send_notification_from_template(
                user_id=user_id,
                template_name="event_reminder_email",
                variables=variables,
                scheduled_at=reminder_time.isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to send event reminder: {e}")
            raise
    
    def send_payment_confirmation(self, user_id: str, payment_data: Dict[str, Any]) -> str:
        """Send payment confirmation notification"""
        try:
            variables = {
                "user_name": payment_data.get("user_name", "User"),
                "amount": payment_data["amount"],
                "event_title": payment_data["event_title"]
            }

            # Send SMS notification
            sms_id = self.send_notification_from_template(
                user_id=user_id,
                template_name="payment_success_sms",
                variables=variables
            )

            return sms_id

        except Exception as e:
            logger.error(f"Failed to send payment confirmation: {e}")
            raise
    
    def send_welcome_notification(self, user_id: str, user_name: str) -> str:
        """Send welcome notification to new user"""
        try:
            variables = {"user_name": user_name}
            
            return self.send_notification_from_template(
                user_id=user_id,
                template_name="user_welcome_email",
                variables=variables
            )
            
        except Exception as e:
            logger.error(f"Failed to send welcome notification: {e}")
            raise
    
    def process_pending_notifications(self) -> int:
        """Process pending notifications"""
        try:
            now = datetime.now(IST).isoformat()
            
            pending_notifications = self.db.query(NotificationDB).filter(
                NotificationDB.status == NotificationStatus.PENDING,
                NotificationDB.scheduled_at <= now
            ).limit(50).all()
            
            processed_count = 0
            
            for notification in pending_notifications:
                try:
                    success = self._send_notification(notification)
                    if success:
                        notification.status = NotificationStatus.SENT
                        notification.sent_at = now
                        processed_count += 1
                    else:
                        notification.status = NotificationStatus.FAILED
                        notification.retry_count += 1
                    
                    notification.updated_at = now
                    
                except Exception as e:
                    logger.error(f"Failed to process notification {notification.id}: {e}")
                    notification.status = NotificationStatus.FAILED
                    notification.error_message = str(e)
                    notification.retry_count += 1
                    notification.updated_at = now
            
            self.db.commit()
            logger.info(f"Processed {processed_count} notifications")
            return processed_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to process pending notifications: {e}")
            return 0
    
    def _send_notification(self, notification: NotificationDB) -> bool:
        """Send notification via appropriate channel"""
        try:
            if notification.channel == NotificationChannel.EMAIL:
                return self._send_email(notification)
            elif notification.channel == NotificationChannel.SMS:
                return self._send_sms(notification)
            elif notification.channel == NotificationChannel.IN_APP:
                return self._send_in_app(notification)
            else:
                logger.error(f"Unsupported notification channel: {notification.channel}")
                return False

        except Exception as e:
            logger.error(f"Failed to send notification {notification.id}: {e}")
            return False
    
    def _send_email(self, notification: NotificationDB) -> bool:
        """Send email notification (placeholder implementation)"""
        # TODO: Implement actual email sending (e.g., using SendGrid, AWS SES)
        logger.info(f"Email notification sent: {notification.id}")
        return True
    
    def _send_sms(self, notification: NotificationDB) -> bool:
        """Send SMS notification (placeholder implementation)"""
        # TODO: Implement actual SMS sending (e.g., using Twilio, AWS SNS)
        logger.info(f"SMS notification sent: {notification.id}")
        return True
    

    
    def _send_in_app(self, notification: NotificationDB) -> bool:
        """Send in-app notification"""
        # In-app notifications are stored in database and retrieved by client
        logger.info(f"In-app notification stored: {notification.id}")
        return True
    
    def get_user_notifications(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get notifications for a user"""
        try:
            notifications = self.db.query(NotificationDB).filter(
                NotificationDB.user_id == user_id
            ).order_by(NotificationDB.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": notif.id,
                    "type": notif.notification_type,
                    "channel": notif.channel,
                    "title": notif.title,
                    "message": notif.message,
                    "status": notif.status,
                    "created_at": notif.created_at,
                    "sent_at": notif.sent_at,
                    "read_at": notif.read_at,
                    "data": json.loads(notif.data) if notif.data else {}
                }
                for notif in notifications
            ]
            
        except Exception as e:
            logger.error(f"Failed to get user notifications: {e}")
            return []
    
    def mark_notification_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read"""
        try:
            notification = self.db.query(NotificationDB).filter(
                NotificationDB.id == notification_id,
                NotificationDB.user_id == user_id
            ).first()
            
            if not notification:
                return False
            
            notification.status = NotificationStatus.READ
            notification.read_at = datetime.now(IST).isoformat()
            notification.updated_at = datetime.now(IST).isoformat()
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to mark notification as read: {e}")
            return False

# Global notification service instance
notification_service = NotificationService()

# Convenience functions
def send_event_reminder(user_id: str, event_data: Dict[str, Any], reminder_hours: int = 24) -> str:
    """Send event reminder notification"""
    return notification_service.send_event_reminder(user_id, event_data, reminder_hours)

def send_payment_confirmation(user_id: str, payment_data: Dict[str, Any]) -> str:
    """Send payment confirmation notification"""
    return notification_service.send_payment_confirmation(user_id, payment_data)

def send_welcome_notification(user_id: str, user_name: str) -> str:
    """Send welcome notification to new user"""
    return notification_service.send_welcome_notification(user_id, user_name)

def process_pending_notifications() -> int:
    """Process pending notifications"""
    return notification_service.process_pending_notifications()
