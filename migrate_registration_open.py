#!/usr/bin/env python3
"""
Manual migration script to add registration_open column to events table
"""
import sqlite3
import os

def add_registration_open_column():
    """Add registration_open column to events table"""
    db_path = "data/app.db"

    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return False

    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("PRAGMA table_info(events)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'registration_open' in columns:
            print("Column 'registration_open' already exists in events table")
            return True

        # Add the registration_open column with default value True
        cursor.execute("ALTER TABLE events ADD COLUMN registration_open BOOLEAN DEFAULT 1")

        # Verify the column was added
        cursor.execute("PRAGMA table_info(events)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'registration_open' in columns:
            print("✅ Successfully added 'registration_open' column to events table")
            conn.commit()
            return True
        else:
            print("❌ Failed to add 'registration_open' column")
            conn.rollback()
            return False

    except Exception as e:
        print(f"❌ Error adding column: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 Starting manual migration to add registration_open column...")
    success = add_registration_open_column()
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
