import sqlite3
import json
import os
from threading import Lock
from core.config import DATABASE_FILE

lock = Lock()

def get_db():
    return sqlite3.connect(DATABASE_FILE)

def init_db():
    with lock:
        conn = get_db()
        cursor = conn.cursor()
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT,
                phone TEXT UNIQUE,
                role TEXT DEFAULT 'user',
                createdAt TEXT
            )
        ''')
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                city TEXT,
                venue TEXT,
                startAt TEXT,
                endAt TEXT,
                priceINR INTEGER,
                capacity INTEGER,
                reserved INTEGER DEFAULT 0,
                bannerUrl TEXT,
                isActive INTEGER DEFAULT 1,
                createdAt TEXT
            )
        ''')
        # Tickets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                eventId TEXT,
                userId TEXT,
                qrToken TEXT,
                issuedAt TEXT,
                isValidated INTEGER DEFAULT 0,
                validatedAt TEXT,
                validationHistory TEXT,
                meta TEXT,
                FOREIGN KEY (eventId) REFERENCES events (id),
                FOREIGN KEY (userId) REFERENCES users (id)
            )
        ''')
        conn.commit()
        conn.close()

# Initialize DB on import
init_db()

def read_users():
    with lock:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(['id', 'name', 'phone', 'role', 'createdAt'], row)) for row in rows]

def write_users(data):
    with lock:
        conn = get_db()
        cursor = conn.cursor()
        for item in data:
            cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?)",
                           (item['id'], item['name'], item['phone'], item.get('role', 'user'), item['createdAt']))
        conn.commit()
        conn.close()

def read_events():
    with lock:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events")
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(zip(['id', 'title', 'description', 'city', 'venue', 'startAt', 'endAt', 'priceINR', 'capacity', 'reserved', 'bannerUrl', 'isActive', 'createdAt'], row))
            d['isActive'] = bool(d['isActive'])
            result.append(d)
        return result

def write_events(data):
    with lock:
        conn = get_db()
        cursor = conn.cursor()
        for item in data:
            cursor.execute("INSERT OR REPLACE INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (item['id'], item['title'], item['description'], item['city'], item['venue'], item['startAt'], item['endAt'], item['priceINR'], item['capacity'], item.get('reserved', 0), item.get('bannerUrl'), 1 if item.get('isActive', True) else 0, item['createdAt']))
        conn.commit()
        conn.close()

def read_tickets():
    with lock:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets")
        rows = cursor.fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(zip(['id', 'eventId', 'userId', 'qrToken', 'issuedAt', 'isValidated', 'validatedAt', 'validationHistory', 'meta'], row))
            d['isValidated'] = bool(d['isValidated'])
            if d['validationHistory']:
                d['validationHistory'] = json.loads(d['validationHistory'])
            else:
                d['validationHistory'] = []
            if d['meta']:
                d['meta'] = json.loads(d['meta'])
            else:
                d['meta'] = {}
            result.append(d)
        return result

def write_tickets(data):
    with lock:
        conn = get_db()
        cursor = conn.cursor()
        for item in data:
            cursor.execute("INSERT OR REPLACE INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (item['id'], item['eventId'], item['userId'], item['qrToken'], item['issuedAt'], 1 if item.get('isValidated', False) else 0, item.get('validatedAt'), json.dumps(item.get('validationHistory', [])), json.dumps(item.get('meta', {}))))
        conn.commit()
        conn.close()

# For backward compatibility, but we'll update routers
def read_json(path):
    if "users" in path:
        return read_users()
    elif "events" in path:
        return read_events()
    elif "tickets" in path:
        return read_tickets()
    return []

def write_json(path, data):
    if "users" in path:
        write_users(data)
    elif "events" in path:
        write_events(data)
    elif "tickets" in path:
        write_tickets(data)
