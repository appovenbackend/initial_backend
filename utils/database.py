import os
import json
import time
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import OperationalError, DisconnectionError
from datetime import datetime
from core.config import (
    DATABASE_URL,
    DATABASE_FILE,
    USE_POSTGRESQL,
    IST,
    DB_POOL_SIZE,
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE,
    DB_POOL_TIMEOUT,
    DB_POOL_PRE_PING,
    DB_POOL_USE_LIFO,
    DB_CONNECT_TIMEOUT,
    DB_STATEMENT_TIMEOUT_MS,
    USE_PGBOUNCER,
)

# Create SQLAlchemy engine
if USE_POSTGRESQL and DATABASE_URL:
    # Railway PostgreSQL with psycopg2
    db_url = DATABASE_URL
    # Convert Railway's postgres:// to postgresql+psycopg2://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif "postgresql+asyncpg://" in db_url:
        # Convert asyncpg to psycopg2 for sync operations
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)

    engine_kwargs = {
        "echo": False,
        "connect_args": {
            "connect_timeout": DB_CONNECT_TIMEOUT,
            "options": f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}",
        },
    }

    if USE_PGBOUNCER:
        # When using PgBouncer in transaction mode, it's recommended to disable pooling at the client
        engine = create_engine(db_url, poolclass=None, **engine_kwargs)
    else:
        engine = create_engine(
            db_url,
            pool_pre_ping=DB_POOL_PRE_PING,
            pool_recycle=DB_POOL_RECYCLE,
            pool_size=DB_POOL_SIZE,
            max_overflow=DB_MAX_OVERFLOW,
            pool_timeout=DB_POOL_TIMEOUT,
            # SQLAlchemy 2.x allows pool_use_lifo to reduce contention
            pool_use_lifo=DB_POOL_USE_LIFO,
            **engine_kwargs,
        )
else:
    # Local SQLite
    engine = create_engine(
        f"sqlite:///{DATABASE_FILE}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()

# Database Models
class UserDB(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=True, index=True)
    email = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    google_id = Column(String, unique=True, nullable=True, index=True)
    role = Column(String, default="user")
    bio = Column(String, nullable=True)
    strava_link = Column(String, nullable=True)
    instagram_id = Column(String, nullable=True)
    is_private = Column(Boolean, default=False)
    createdAt = Column(String, nullable=False)

class EventDB(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    city = Column(String, nullable=False)
    venue = Column(String, nullable=False)
    startAt = Column(String, nullable=False)
    endAt = Column(String, nullable=False, index=True)
    priceINR = Column(Integer, nullable=False)
    bannerUrl = Column(String, nullable=True)
    isActive = Column(Boolean, default=True, index=True)
    createdAt = Column(String, nullable=False)
    organizerName = Column(String, nullable=True, default="bhag")
    organizerLogo = Column(String, nullable=True, default="https://example.com/default-logo.png")
    coordinate_lat = Column(String, nullable=True)
    coordinate_long = Column(String, nullable=True)
    address_url = Column(String, nullable=True)
    registration_link = Column(String, nullable=True)

class TicketDB(Base):
    __tablename__ = "tickets"

    id = Column(String, primary_key=True, index=True)
    eventId = Column(String, nullable=False, index=True)
    userId = Column(String, nullable=False, index=True)
    qrToken = Column(String, nullable=False)
    issuedAt = Column(String, nullable=False)
    isValidated = Column(Boolean, default=False, index=True)
    validatedAt = Column(String, nullable=True)
    validationHistory = Column(Text, nullable=True)  # JSON string
    meta = Column(Text, nullable=True)  # JSON string

class ReceivedQrTokenDB(Base):
    __tablename__ = "received_qr_tokens"

    id = Column(String, primary_key=True, index=True)
    token = Column(String, nullable=False)
    eventId = Column(String, nullable=False, index=True)
    receivedAt = Column(String, nullable=False)
    source = Column(String, nullable=True)

class UserFollowDB(Base):
    __tablename__ = "user_connections"  # renamed from user_follows

    id = Column(String, primary_key=True, index=True)
    follower_id = Column(String, nullable=False, index=True)  # requester
    following_id = Column(String, nullable=False, index=True)  # target
    status = Column(String, nullable=False, default="pending")  # 'pending', 'accepted', 'blocked'
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)

class UserPointsDB(Base):
    __tablename__ = "user_points"

    id = Column(String, primary_key=True, index=True)  # user_id
    total_points = Column(Integer, nullable=False, default=0)
    transaction_history = Column(Text, nullable=True)  # JSON string of transactions

# Create tables
Base.metadata.create_all(bind=engine)

def retry_db_operation(max_retries=3, delay=1):
    """Decorator to retry database operations on connection failures"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DisconnectionError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
                        # Reset session on connection error
                        SessionLocal.remove()
                    else:
                        raise e
                except Exception as e:
                    # For non-connection errors, don't retry
                    raise e
            if last_exception:
                raise last_exception
        return wrapper
    return decorator

def execute_with_transaction(operation_func):
    """Execute database operation within a transaction with proper rollback"""
    db = SessionLocal()
    try:
        with db.begin():
            result = operation_func(db)
        return result
    except Exception as e:
        db.rollback()
        raise e
    finally:
        SessionLocal.remove()

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
@retry_db_operation()
def read_users():
    db = SessionLocal()
    try:
        users = db.query(UserDB).all()
        result = []
        for user in users:
            user_dict = user.__dict__.copy()
            # Remove SQLAlchemy internal fields
            user_dict.pop('_sa_instance_state', None)

            # Deserialize subscribedEvents from JSON to list
            if user_dict.get('subscribedEvents') is not None:
                try:
                    user_dict['subscribedEvents'] = json.loads(user_dict['subscribedEvents'])
                except (json.JSONDecodeError, TypeError):
                    user_dict['subscribedEvents'] = []
            else:
                user_dict['subscribedEvents'] = []

            result.append(user_dict)
        return result
    finally:
        SessionLocal.remove()

@retry_db_operation()
def write_users(data):
    db = SessionLocal()
    try:
        # Use transaction for atomicity
        with db.begin():
            # Instead of deleting all, upsert each user to prevent data loss
            for user_data in data:
                # Filter to only include fields that exist in UserDB
                user_dict = {k: v for k, v in user_data.items() if k in UserDB.__table__.columns.keys()}

                # Serialize subscribedEvents to JSON if it's a list
                if 'subscribedEvents' in user_dict and isinstance(user_dict['subscribedEvents'], list):
                    user_dict['subscribedEvents'] = json.dumps(user_dict['subscribedEvents'])

                user_id = user_dict.get('id')
                user_phone = user_dict.get('phone')

                # Check if user exists by ID first
                existing_user = db.query(UserDB).filter(UserDB.id == user_id).first()

                if existing_user:
                    # Update existing user
                    for key, value in user_dict.items():
                        setattr(existing_user, key, value)
                else:
                    # Check if phone number already exists (to avoid unique constraint violation)
                    if user_phone:
                        phone_exists = db.query(UserDB).filter(UserDB.phone == user_phone).first()
                        if phone_exists:
                            # Update the existing user with the same phone number
                            for key, value in user_dict.items():
                                setattr(phone_exists, key, value)
                            continue

                    # Add new user
                    user = UserDB(**user_dict)
                    db.add(user)
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
        # Use transaction for atomicity
        with db.begin():
            # Add new events WITHOUT clearing existing ones
            for event_data in data:
                # Check if event already exists
                existing_event = db.query(EventDB).filter(EventDB.id == event_data.get('id')).first()
                if existing_event:
                    # Update existing event
                    for key, value in event_data.items():
                        if hasattr(existing_event, key):
                            setattr(existing_event, key, value)
                else:
                    # Add new event
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
                        'createdAt': event_data.get('createdAt'),
                        'organizerName': event_data.get('organizerName', 'bhag'),
                        'organizerLogo': event_data.get('organizerLogo', 'https://example.com/default-logo.png'),
                        'coordinate_lat': event_data.get('coordinate_lat'),
                        'coordinate_long': event_data.get('coordinate_long'),
                        'address_url': event_data.get('address_url'),
                        'registration_link': event_data.get('registration_link')
                    }
                    # Remove None values for required fields
                    filtered_data = {k: v for k, v in filtered_data.items() if v is not None}
                    event = EventDB(**filtered_data)
                    db.add(event)
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

            # Deserialize JSON fields back to Python objects for PostgreSQL compatibility
            if USE_POSTGRESQL:
                if ticket_dict.get('validationHistory') is not None:
                    try:
                        ticket_dict['validationHistory'] = json.loads(ticket_dict['validationHistory'])
                    except (json.JSONDecodeError, TypeError):
                        ticket_dict['validationHistory'] = []
                else:
                    ticket_dict['validationHistory'] = []

                if ticket_dict.get('meta') is not None:
                    try:
                        ticket_dict['meta'] = json.loads(ticket_dict['meta'])
                    except (json.JSONDecodeError, TypeError):
                        ticket_dict['meta'] = {}
                else:
                    ticket_dict['meta'] = {}

            result.append(ticket_dict)
        return result
    finally:
        SessionLocal.remove()

def write_tickets(data):
    db = SessionLocal()
    try:
        # Use transaction for atomicity
        with db.begin():
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

                # Serialize dict/list fields to JSON strings for PostgreSQL compatibility
                if USE_POSTGRESQL:
                    if filtered_data.get('validationHistory') is not None:
                        filtered_data['validationHistory'] = json.dumps(filtered_data['validationHistory'])
                    if filtered_data.get('meta') is not None:
                        filtered_data['meta'] = json.dumps(filtered_data['meta'])

                # Remove None values for required fields
                filtered_data = {k: v for k, v in filtered_data.items() if k in ['id', 'eventId', 'userId', 'qrToken', 'issuedAt'] or v is not None}
                ticket = TicketDB(**filtered_data)
                db.add(ticket)
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
        # Use transaction for atomicity
        with db.begin():
            # Clear existing tokens
            db.query(ReceivedQrTokenDB).delete()
            # Add new tokens
            for token_data in data:
                # Filter only the fields that exist in ReceivedQrTokenDB model
                filtered_data = {
                    'id': token_data.get('id'),
                    'token': token_data.get('token'),
                    'eventId': token_data.get('eventId'),
                    'receivedAt': token_data.get('receivedAt'),
                    'source': token_data.get('source')
                }
                # Remove None values for required fields
                filtered_data = {k: v for k, v in filtered_data.items() if k in ['id', 'token', 'eventId', 'receivedAt'] or v is not None}
                token = ReceivedQrTokenDB(**filtered_data)
                db.add(token)
    finally:
        SessionLocal.remove()

def read_user_follows():
    db = SessionLocal()
    try:
        follows = db.query(UserFollowDB).all()
        result = []
        for follow in follows:
            follow_dict = follow.__dict__.copy()
            follow_dict.pop('_sa_instance_state', None)
            result.append(follow_dict)
        return result
    finally:
        SessionLocal.remove()

def write_user_follows(data):
    db = SessionLocal()
    try:
        # Use transaction for atomicity
        with db.begin():
            # Clear existing follows
            db.query(UserFollowDB).delete()
            # Add new follows
            for follow_data in data:
                # Filter only the fields that exist in UserFollowDB model
                filtered_data = {
                    'id': follow_data.get('id'),
                    'follower_id': follow_data.get('follower_id'),
                    'following_id': follow_data.get('following_id'),
                    'status': follow_data.get('status', 'pending'),
                    'created_at': follow_data.get('created_at'),
                    'updated_at': follow_data.get('updated_at')
                }
                # Remove None values for required fields
                filtered_data = {k: v for k, v in filtered_data.items() if k in ['id', 'follower_id', 'following_id', 'status', 'created_at', 'updated_at'] or v is not None}
                follow = UserFollowDB(**filtered_data)
                db.add(follow)
    finally:
        SessionLocal.remove()

def read_user_points():
    """Read user points for all users"""
    db = SessionLocal()
    try:
        points = db.query(UserPointsDB).all()
        result = []
        for point in points:
            point_dict = point.__dict__.copy()
            point_dict.pop('_sa_instance_state', None)

            # Deserialize JSON transaction_history
            if USE_POSTGRESQL:
                if point_dict.get('transaction_history') is not None:
                    try:
                        point_dict['transaction_history'] = json.loads(point_dict['transaction_history'])
                    except (json.JSONDecodeError, TypeError):
                        point_dict['transaction_history'] = []
                else:
                    point_dict['transaction_history'] = []

            result.append(point_dict)
        return result
    finally:
        SessionLocal.remove()

def write_user_points(data):
    """Write user points (upsert)"""
    db = SessionLocal()
    try:
        with db.begin():
            for points_data in data:
                # Filter only the fields that exist in UserPointsDB model
                filtered_data = {
                    'id': points_data.get('id'),
                    'total_points': points_data.get('total_points', 0),
                    'transaction_history': points_data.get('transaction_history')
                }

                # Serialize dict/list fields to JSON strings for PostgreSQL compatibility
                if USE_POSTGRESQL and filtered_data.get('transaction_history') is not None:
                    filtered_data['transaction_history'] = json.dumps(filtered_data['transaction_history'])

                user_id = filtered_data.get('id')

                # Check if user points exist
                existing_points = db.query(UserPointsDB).filter(UserPointsDB.id == user_id).first()

                if existing_points:
                    # Update existing
                    for key, value in filtered_data.items():
                        setattr(existing_points, key, value)
                else:
                    # Add new
                    points = UserPointsDB(**filtered_data)
                    db.add(points)
    finally:
        SessionLocal.remove()

def get_user_points(user_id: str):
    """Get points for a specific user"""
    db = SessionLocal()
    try:
        points = db.query(UserPointsDB).filter(UserPointsDB.id == user_id).first()
        if points:
            point_dict = points.__dict__.copy()
            point_dict.pop('_sa_instance_state', None)

            # Deserialize JSON transaction_history
            if USE_POSTGRESQL:
                if point_dict.get('transaction_history') is not None:
                    try:
                        point_dict['transaction_history'] = json.loads(point_dict['transaction_history'])
                    except (json.JSONDecodeError, TypeError):
                        point_dict['transaction_history'] = []
                else:
                    point_dict['transaction_history'] = []

            return point_dict
        else:
            # Return default points object for new users
            return {
                'id': user_id,
                'total_points': 0,
                'transaction_history': []
            }
    finally:
        SessionLocal.remove()

def award_points_to_user(user_id: str, points: int, reason: str):
    """Award points to a user and record the transaction"""
    db = SessionLocal()
    try:
        with db.begin():
            # Get or create user points
            user_points = db.query(UserPointsDB).filter(UserPointsDB.id == user_id).first()

            from datetime import datetime
            from core.config import IST
            timestamp = datetime.now(IST).isoformat()

            transaction = {
                "type": "earned",
                "points": points,
                "reason": reason,
                "timestamp": timestamp
            }

            if user_points:
                # Update existing
                user_points.total_points += points
                current_history = []
                if USE_POSTGRESQL and user_points.transaction_history:
                    try:
                        current_history = json.loads(user_points.transaction_history)
                    except:
                        current_history = []
                elif user_points.transaction_history:
                    current_history = user_points.transaction_history

                current_history.append(transaction)
                user_points.transaction_history = json.dumps(current_history) if USE_POSTGRESQL else current_history
            else:
                # Create new
                user_points = UserPointsDB(
                    id=user_id,
                    total_points=points,
                    transaction_history=json.dumps([transaction]) if USE_POSTGRESQL else [transaction]
                )
                db.add(user_points)

        return True
    except Exception as e:
        print(f"Error awarding points: {e}")
        return False
    finally:
        SessionLocal.remove()

# Initialize database on import
try:
    init_db()
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    if USE_POSTGRESQL:
        print("   Check your DATABASE_URL configuration and PostgreSQL connection")
    else:
        print("   Check file permissions for SQLite database")
    raise
