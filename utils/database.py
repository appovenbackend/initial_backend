import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime
from core.config import DATABASE_URL, DATABASE_FILE, USE_POSTGRESQL, IST

# Create SQLAlchemy engine
if USE_POSTGRESQL and DATABASE_URL:
    # Railway PostgreSQL with pg8000 (Python 3.13 compatible)
    # Forcefully use pg8000 driver with proper SSL configuration
    db_url = DATABASE_URL.replace('postgresql://', 'postgresql+pg8000://')
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        connect_args={
            "ssl_context": True,  # Enable SSL for pg8000
            "autocommit": True
        }
    )
else:
    # Local SQLite
    engine = create_engine(f"sqlite:///{DATABASE_FILE}", connect_args={"check_same_thread": False})

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()

# Database Models
class UserDB(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=True)
    email = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    google_id = Column(String, unique=True, nullable=True)
    role = Column(String, default="user")
    createdAt = Column(String, nullable=False)

class EventDB(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    city = Column(String, nullable=False)
    venue = Column(String, nullable=False)
    startAt = Column(String, nullable=False)
    endAt = Column(String, nullable=False)
    priceINR = Column(Integer, nullable=False)
    bannerUrl = Column(String, nullable=True)
    isActive = Column(Boolean, default=True)
    createdAt = Column(String, nullable=False)

class TicketDB(Base):
    __tablename__ = "tickets"

    id = Column(String, primary_key=True, index=True)
    eventId = Column(String, nullable=False)
    userId = Column(String, nullable=False)
    qrToken = Column(String, nullable=False)
    issuedAt = Column(String, nullable=False)
    isValidated = Column(Boolean, default=False)
    validatedAt = Column(String, nullable=True)
    validationHistory = Column(Text, nullable=True)  # JSON string
    meta = Column(Text, nullable=True)  # JSON string

class ReceivedQrTokenDB(Base):
    __tablename__ = "received_qr_tokens"

    id = Column(String, primary_key=True, index=True)
    token = Column(String, nullable=False)
    receivedAt = Column(String, nullable=False)
    source = Column(String, nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utility functions to maintain compatibility with existing code
def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_database_session():
    """Get a database session for manual operations"""
    return SessionLocal()

# Legacy compatibility functions
def read_users():
    db = SessionLocal()
    try:
        users = db.query(UserDB).all()
        result = []
        for user in users:
            user_dict = user.__dict__.copy()
            # Remove SQLAlchemy internal fields
            user_dict.pop('_sa_instance_state', None)
            result.append(user_dict)
        return result
    finally:
        SessionLocal.remove()

def write_users(data):
    db = SessionLocal()
    try:
        # Clear existing users
        db.query(UserDB).delete()
        # Add new users
        for user_data in data:
            user = UserDB(**user_data)
            db.add(user)
        db.commit()
    finally:
        SessionLocal.remove()

def read_events():
    db = SessionLocal()
    try:
        events = db.query(EventDB).all()
        result = []
        for event in events:
            event_dict = event.__dict__.copy()
            # Remove SQLAlchemy internal fields
            event_dict.pop('_sa_instance_state', None)
            result.append(event_dict)
        return result
    finally:
        SessionLocal.remove()

def write_events(data):
    db = SessionLocal()
    try:
        # Clear existing events
        db.query(EventDB).delete()
        # Add new events
        for event_data in data:
            # Filter only the fields that exist in EventDB model
            filtered_data = {
                'id': event_data.get('id'),
                'title': event_data.get('title'),
                'description': event_data.get('description'),
                'city': event_data.get('city'),
                'venue': event_data.get('venue'),
                'startAt': event_data.get('startAt'),
                'endAt': event_data.get('endAt'),
                'priceINR': event_data.get('priceINR'),
                'bannerUrl': event_data.get('bannerUrl'),
                'isActive': event_data.get('isActive', True),
                'createdAt': event_data.get('createdAt')
            }
            # Remove None values for required fields
            filtered_data = {k: v for k, v in filtered_data.items() if v is not None}
            event = EventDB(**filtered_data)
            db.add(event)
        db.commit()
    finally:
        SessionLocal.remove()

def read_tickets():
    db = SessionLocal()
    try:
        tickets = db.query(TicketDB).all()
        result = []
        for ticket in tickets:
            ticket_dict = ticket.__dict__.copy()
            ticket_dict.pop('_sa_instance_state', None)
            result.append(ticket_dict)
        return result
    finally:
        SessionLocal.remove()

def write_tickets(data):
    db = SessionLocal()
    try:
        # Clear existing tickets
        db.query(TicketDB).delete()
        # Add new tickets
        for ticket_data in data:
            # Filter only the fields that exist in TicketDB model
            filtered_data = {
                'id': ticket_data.get('id'),
                'eventId': ticket_data.get('eventId'),
                'userId': ticket_data.get('userId'),
                'qrToken': ticket_data.get('qrToken'),
                'issuedAt': ticket_data.get('issuedAt'),
                'isValidated': ticket_data.get('isValidated', False),
                'validatedAt': ticket_data.get('validatedAt'),
                'validationHistory': ticket_data.get('validationHistory'),
                'meta': ticket_data.get('meta')
            }
            # Remove None values for required fields
            filtered_data = {k: v for k, v in filtered_data.items() if k in ['id', 'eventId', 'userId', 'qrToken', 'issuedAt'] or v is not None}
            ticket = TicketDB(**filtered_data)
            db.add(ticket)
        db.commit()
    finally:
        SessionLocal.remove()

def read_received_qr_tokens():
    db = SessionLocal()
    try:
        tokens = db.query(ReceivedQrTokenDB).all()
        result = []
        for token in tokens:
            token_dict = token.__dict__.copy()
            token_dict.pop('_sa_instance_state', None)
            result.append(token_dict)
        return result
    finally:
        SessionLocal.remove()

def write_received_qr_tokens(data):
    db = SessionLocal()
    try:
        # Clear existing tokens
        db.query(ReceivedQrTokenDB).delete()
        # Add new tokens
        for token_data in data:
            # Filter only the fields that exist in ReceivedQrTokenDB model
            filtered_data = {
                'id': token_data.get('id'),
                'token': token_data.get('token'),
                'receivedAt': token_data.get('receivedAt'),
                'source': token_data.get('source')
            }
            # Remove None values for required fields
            filtered_data = {k: v for k, v in filtered_data.items() if k in ['id', 'token', 'receivedAt'] or v is not None}
            token = ReceivedQrTokenDB(**filtered_data)
            db.add(token)
        db.commit()
    finally:
        SessionLocal.remove()

# Initialize database on import
init_db()
