import os
import secrets
import sqlite3

from datetime import date

from werkzeug.security import generate_password_hash

# db.py lives in database/, so go up one level to reach the project root —
# keeps the db path correct regardless of the process's cwd.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "expense_tracker.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # not persisted across connections — set every time
    return conn


def generate_user_id():
    """Random 8-byte (16 hex char) primary key for users.

    Generated in Python, not read back via cursor.lastrowid: since users.id
    is TEXT rather than INTEGER PRIMARY KEY, SQLite still tracks an internal
    rowid separate from the id column's actual value, so lastrowid would
    return that meaningless internal number instead of the id we stored.
    """
    return secrets.token_hex(8)


def init_db():
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return  # already seeded

        password_hash = generate_password_hash("demo123")
        user_id = generate_user_id()
        conn.execute(
            "INSERT INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)",
            (user_id, "Demo User", "demo@spendly.com", password_hash),
        )

        # day-of-month capped at 21 so it's valid in every month (incl. Feb)
        first_of_month = date.today().replace(day=1)
        sample_expenses = [
            (25.50, "Food", 1, "Weekly groceries"),
            (12.00, "Transport", 3, "Bus pass top-up"),
            (60.00, "Bills", 5, "Electricity bill"),
            (45.75, "Health", 8, "Pharmacy"),
            (30.00, "Entertainment", 11, "Movie night"),
            (89.99, "Shopping", 14, "New shoes"),
            (15.00, "Other", 18, "Miscellaneous"),
            (8.50, "Food", 21, "Coffee"),
        ]
        rows = [
            (user_id, amount, category,
             first_of_month.replace(day=day).strftime("%Y-%m-%d"), description)
            for amount, category, day, description in sample_expenses
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
