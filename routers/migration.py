from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine, text
from core.config import DATABASE_URL
import os

from migrate_db import migrate_events_table, migrate_received_qr_tokens_table

router = APIRouter(prefix="/migration", tags=["Migration"])

@router.post("/fix-registration-link")
async def fix_registration_link_column():
    """
    Manually add the registration_link column to the events table.
    This endpoint can be called to fix the production database issue.
    """

    if not DATABASE_URL:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL environment variable not set"
        )

    try:
        # Create engine
        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'events' AND column_name = 'registration_link';
            """))

            if result.fetchone():
                return {
                    "message": "registration_link column already exists",
                    "status": "already_fixed"
                }

            # Add the missing column
            conn.execute(text("ALTER TABLE events ADD COLUMN registration_link VARCHAR;"))
            conn.commit()

            # Verify the column was added
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'events' AND column_name = 'registration_link';
            """))

            if result.fetchone():
                return {
                    "message": "registration_link column added successfully",
                    "status": "fixed"
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to verify column addition"
                )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

@router.post("/fix-subscribed-events")
async def fix_subscribed_events_column():
    """
    Manually add the subscribedEvents column to the users table.
    This fixes the database schema mismatch causing 500 errors.
    """

    if not DATABASE_URL:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL environment variable not set"
        )

    try:
        # Create engine
        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'subscribedEvents';
            """))

            if result.fetchone():
                return {
                    "message": "subscribedEvents column already exists",
                    "status": "already_fixed"
                }

            # Add the missing column
            conn.execute(text("ALTER TABLE users ADD COLUMN \"subscribedEvents\" TEXT;"))
            conn.commit()

            # Verify the column was added
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'subscribedEvents';
            """))

            if result.fetchone():
                return {
                    "message": "subscribedEvents column added successfully",
                    "status": "fixed"
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to verify column addition"
                )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

@router.get("/status")
async def get_migration_status():
    """
    Check the current status of the database migration.
    """

    if not DATABASE_URL:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL environment variable not set"
        )

    try:
        engine = create_engine(DATABASE_URL)

        with engine.connect() as conn:
            # Check if columns exist
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'events' AND column_name = 'registration_link';
            """))
            registration_link_exists = result.fetchone() is not None

            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'subscribedEvents';
            """))
            subscribed_events_exists = result.fetchone() is not None

            return {
                "registration_link_column_exists": registration_link_exists,
                "subscribed_events_column_exists": subscribed_events_exists,
                "database_url_configured": True,
                "status": "ready" if (registration_link_exists and subscribed_events_exists) else "needs_fix"
            }

    except Exception as e:
        return {
            "registration_link_column_exists": False,
            "subscribed_events_column_exists": False,
            "database_url_configured": True,
            "error": str(e),
            "status": "error"
        }
if __name__ == "__main__":
    migrate_events_table()
    migrate_received_qr_tokens_table()
