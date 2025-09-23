import asyncio
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, update, delete, insert
from sqlalchemy.exc import OperationalError, DisconnectionError
from core.config import (
    DATABASE_URL,
    DATABASE_FILE,
    USE_POSTGRESQL,
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
import logging

logger = logging.getLogger(__name__)

# Create async SQLAlchemy engine
if USE_POSTGRESQL and DATABASE_URL:
    # Railway PostgreSQL with asyncpg
    db_url = DATABASE_URL
    # Convert Railway's postgres:// to postgresql+asyncpg://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

    engine_kwargs = {
        "echo": False,
        "connect_args": {
            "connect_timeout": DB_CONNECT_TIMEOUT,
            "options": f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}",
        },
    }

    if USE_PGBOUNCER:
        # When using PgBouncer in transaction mode, it's recommended to disable pooling at the client
        async_engine = create_async_engine(db_url, poolclass=None, **engine_kwargs)
    else:
        async_engine = create_async_engine(
            db_url,
            pool_pre_ping=DB_POOL_PRE_PING,
            pool_recycle=DB_POOL_RECYCLE,
            pool_size=DB_POOL_SIZE,
            max_overflow=DB_MAX_OVERFLOW,
            pool_timeout=DB_POOL_TIMEOUT,
            pool_use_lifo=DB_POOL_USE_LIFO,
            **engine_kwargs,
        )
else:
    # Local SQLite with aiosqlite
    async_engine = create_async_engine(
        f"sqlite+aiosqlite:///{DATABASE_FILE}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class AsyncDatabaseManager:
    def __init__(self):
        self.async_engine = async_engine
        self.AsyncSessionLocal = AsyncSessionLocal

    async def get_session(self) -> AsyncSession:
        """Get an async database session"""
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                raise e

    async def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile with new fields"""
        async def _update():
            async with self.AsyncSessionLocal() as session:
                async with session.begin():
                    from models.user import UserDB

                    # Get user
                    result = await session.execute(
                        select(UserDB).where(UserDB.id == user_id)
                    )
                    user = result.scalar_one_or_none()

                    if not user:
                        return {"error": "User not found"}

                    # Update fields
                    update_fields = ['name', 'phone', 'email', 'bio', 'starva_link', 'instagram_id']
                    updated = False

                    for field in update_fields:
                        if field in update_data:
                            setattr(user, field, update_data[field])
                            updated = True

                    if not updated:
                        return {"error": "No valid fields to update"}

                    return {
                        "success": True,
                        "user": {
                            "id": user.id,
                            "name": user.name,
                            "phone": user.phone,
                            "email": user.email,
                            "bio": user.bio,
                            "starva_link": user.starva_link,
                            "instagram_id": user.instagram_id
                        }
                    }

        return await self.execute_with_retry(_update)

    async def execute_with_retry(self, operation, max_retries=3, delay=1):
        """Execute database operation with retry logic"""
        last_exception = None
        for attempt in range(max_retries):
            try:
                return await operation()
            except (OperationalError, DisconnectionError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
                    logger.warning(f"Database operation failed, retrying... (attempt {attempt + 1})")
                else:
                    logger.error(f"Database operation failed after {max_retries} attempts: {e}")
                    raise e
            except Exception as e:
                # For non-connection errors, don't retry
                logger.error(f"Database operation failed: {e}")
                raise e
        if last_exception:
            raise last_exception

    async def read_users(self) -> List[Dict[str, Any]]:
        """Read all users asynchronously"""
        async def _read():
            async with self.AsyncSessionLocal() as session:
                from models.user import UserDB
                result = await session.execute(select(UserDB))
                users = result.scalars().all()

                user_list = []
                for user in users:
                    user_dict = {c.name: getattr(user, c.name) for c in user.__table__.columns}

                    # Deserialize subscribedEvents from JSON to list
                    if user_dict.get('subscribedEvents') is not None:
                        try:
                            user_dict['subscribedEvents'] = json.loads(user_dict['subscribedEvents'])
                        except (json.JSONDecodeError, TypeError):
                            user_dict['subscribedEvents'] = []
                    else:
                        user_dict['subscribedEvents'] = []

                    user_list.append(user_dict)
                return user_list

        return await self.execute_with_retry(_read)

    async def write_users(self, users: List[Dict[str, Any]]) -> None:
        """Write users with transaction support"""
        async def _write():
            async with self.AsyncSessionLocal() as session:
                async with session.begin():
                    from models.user import UserDB

                    for user_data in users:
                        # Filter to only include fields that exist in UserDB
                        user_dict = {k: v for k, v in user_data.items() if k in UserDB.__table__.columns.keys()}

                        # Serialize subscribedEvents to JSON if it's a list
                        if 'subscribedEvents' in user_dict and isinstance(user_dict['subscribedEvents'], list):
                            user_dict['subscribedEvents'] = json.dumps(user_dict['subscribedEvents'])

                        # Check if user exists
                        result = await session.execute(
                            select(UserDB).where(UserDB.id == user_dict.get('id'))
                        )
                        existing_user = result.scalar_one_or_none()

                        if existing_user:
                            # Update existing user
                            for key, value in user_dict.items():
                                setattr(existing_user, key, value)
                        else:
                            # Add new user
                            new_user = UserDB(**user_dict)
                            session.add(new_user)

        await self.execute_with_retry(_write)

    async def read_events(self) -> List[Dict[str, Any]]:
        """Read all events asynchronously"""
        async def _read():
            async with self.AsyncSessionLocal() as session:
                from models.event import EventDB
                result = await session.execute(select(EventDB))
                events = result.scalars().all()

                event_list = []
                for event in events:
                    event_dict = {c.name: getattr(event, c.name) for c in event.__table__.columns}
                    event_list.append(event_dict)
                return event_list

        return await self.execute_with_retry(_read)

    async def write_events(self, events: List[Dict[str, Any]]) -> None:
        """Write events with transaction support"""
        async def _write():
            async with self.AsyncSessionLocal() as session:
                async with session.begin():
                    from models.event import EventDB

                    # Clear existing events
                    await session.execute(delete(EventDB))

                    # Add new events
                    for event_data in events:
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
                            'organizerLogo': event_data.get('organizerLogo', 'https://example.com/default-logo.png')
                        }
                        # Remove None values for required fields
                        filtered_data = {k: v for k, v in filtered_data.items() if v is not None}

                        new_event = EventDB(**filtered_data)
                        session.add(new_event)

        await self.execute_with_retry(_write)

    async def read_tickets(self) -> List[Dict[str, Any]]:
        """Read all tickets asynchronously"""
        async def _read():
            async with self.AsyncSessionLocal() as session:
                from models.ticket import TicketDB
                result = await session.execute(select(TicketDB))
                tickets = result.scalars().all()

                ticket_list = []
                for ticket in tickets:
                    ticket_dict = {c.name: getattr(ticket, c.name) for c in ticket.__table__.columns}

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

                    ticket_list.append(ticket_dict)
                return ticket_list

        return await self.execute_with_retry(_read)

    async def write_tickets(self, tickets: List[Dict[str, Any]]) -> None:
        """Write tickets with transaction support"""
        async def _write():
            async with self.AsyncSessionLocal() as session:
                async with session.begin():
                    from models.ticket import TicketDB

                    # Clear existing tickets
                    await session.execute(delete(TicketDB))

                    # Add new tickets
                    for ticket_data in tickets:
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

                        new_ticket = TicketDB(**filtered_data)
                        session.add(new_ticket)

        await self.execute_with_retry(_write)

    async def validate_ticket_transaction(self, ticket_id: str, event_id: str, user_id: str) -> Dict[str, Any]:
        """Validate a ticket with full transaction support"""
        async def _validate():
            async with self.AsyncSessionLocal() as session:
                async with session.begin():
                    from models.ticket import TicketDB
                    from models.event import EventDB
                    from models.user import UserDB
                    from datetime import datetime
                    from core.config import IST
                    from dateutil import parser

                    # Get ticket
                    result = await session.execute(
                        select(TicketDB).where(TicketDB.id == ticket_id)
                    )
                    ticket = result.scalar_one_or_none()

                    if not ticket:
                        return {"status": "invalid", "reason": "ticket_not_found"}

                    # Check if already validated
                    if ticket.isValidated:
                        # Get user info
                        result = await session.execute(
                            select(UserDB).where(UserDB.id == ticket.userId)
                        )
                        user = result.scalar_one_or_none()

                        return {
                            "status": "already_scanned",
                            "ticket_id": ticket_id,
                            "user": {"id": user.id, "name": user.name, "phone": user.phone} if user else None,
                            "issuedAt": ticket.issuedAt,
                            "validatedAt": ticket.validatedAt,
                            "validationHistory": ticket.validationHistory or []
                        }

                    # Get event
                    result = await session.execute(
                        select(EventDB).where(EventDB.id == event_id)
                    )
                    event = result.scalar_one_or_none()

                    if not event:
                        return {"status": "invalid", "reason": "event_not_found"}

                    # Check event expiry
                    try:
                        event_end = parser.isoparse(event.endAt)
                        if event_end <= datetime.now(IST):
                            return {"status": "invalid", "reason": "event_expired"}
                    except Exception:
                        pass

                    # Get user info
                    result = await session.execute(
                        select(UserDB).where(UserDB.id == user_id)
                    )
                    user = result.scalar_one_or_none()

                    # Mark as validated
                    ticket.isValidated = True
                    ticket.validatedAt = datetime.now(IST).isoformat()
                    hist = ticket.validationHistory or []
                    hist.append({"ts": ticket.validatedAt})
                    ticket.validationHistory = hist

                    return {
                        "status": "valid",
                        "ticket_id": ticket_id,
                        "user": {"id": user.id, "name": user.name, "phone": user.phone} if user else None,
                        "event": {c.name: getattr(event, c.name) for c in event.__table__.columns},
                        "issuedAt": ticket.issuedAt,
                        "validatedAt": ticket.validatedAt,
                        "validationHistory": ticket.validationHistory
                    }

        return await self.execute_with_retry(_validate)

# Global async database manager instance
async_db_manager = AsyncDatabaseManager()
