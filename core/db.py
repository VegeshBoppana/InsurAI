import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "insurai.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Users
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT NOT NULL UNIQUE
    )
    """)

    # Company Policies
    c.execute("""
    CREATE TABLE IF NOT EXISTS policies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        type TEXT NOT NULL,          -- 'health' or 'vehicle'
        premium REAL NOT NULL,
        benefits TEXT NOT NULL,
        coverage_limit REAL NOT NULL,
        is_custom INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )
    """)

    # User Health Insurance
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_health_insurance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        policy_id INTEGER NOT NULL,
        start_date TEXT DEFAULT CURRENT_TIMESTAMP,
        end_date TEXT,
        status TEXT DEFAULT 'active',
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(policy_id) REFERENCES policies(id)
    )
    """)

    # User Vehicle Insurance
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_vehicle_insurance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        policy_id INTEGER NOT NULL,
        number_plate TEXT NOT NULL,
        vehicle_type TEXT NOT NULL,
        brand_model TEXT,
        age INTEGER,
        kms_driven INTEGER,
        wheels INTEGER,
        start_date TEXT DEFAULT CURRENT_TIMESTAMP,
        end_date TEXT,
        status TEXT DEFAULT 'active',
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(policy_id) REFERENCES policies(id)
    )
    """)

    # Claims
    c.execute("""
    CREATE TABLE IF NOT EXISTS claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_number TEXT UNIQUE,
        user_id INTEGER NOT NULL,
        insurance_type TEXT NOT NULL,
        insurance_ref_id INTEGER NOT NULL,
        claim_reason TEXT,
        document_text TEXT,
        document_info TEXT,
        claim_amount REAL,
        reimbursement REAL,
        status TEXT DEFAULT 'initiated',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()
