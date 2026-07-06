import sqlite3
import os
from flask import current_app, g


def get_db():
    """Return a request-scoped SQLite connection with WAL mode + busy timeout.

    FIX #1 (performance): journal_mode=WAL + busy_timeout prevent
    'database is locked' errors when multiple teachers/coordinators/
    admin write at the same time.
    """
    if "db" not in g:
        db_path = current_app.config["DATABASE_PATH"]
        conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(f"PRAGMA journal_mode = {current_app.config['SQLITE_JOURNAL_MODE']}")
        conn.execute(f"PRAGMA busy_timeout = {current_app.config['SQLITE_BUSY_TIMEOUT_MS']}")
        g.db = conn
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create tables from schema.sql if they don't exist, and seed default data."""
    db_path = app.config["DATABASE_PATH"]
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    schema_path = os.path.join(os.path.dirname(db_path), "schema.sql")

    conn = sqlite3.connect(db_path)
    conn.execute(f"PRAGMA journal_mode = {app.config['SQLITE_JOURNAL_MODE']}")
    with open(schema_path, "r") as f:
        conn.executescript(f.read())

    columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "assigned_password" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN assigned_password TEXT")

    student_columns = {row[1] for row in conn.execute("PRAGMA table_info(students)").fetchall()}
    if "student_contact" not in student_columns:
        conn.execute("ALTER TABLE students ADD COLUMN student_contact TEXT")

    conn.execute(
        "UPDATE students SET student_contact = parent_contact WHERE (student_contact IS NULL OR student_contact = '') AND parent_contact IS NOT NULL"
    )

    conn.execute(
        "UPDATE users SET assigned_password = username WHERE assigned_password IS NULL AND username IS NOT NULL"
    )

    conn.commit()
    conn.close()


def log_audit(db, user_id, action, details=None, ip_address=None):
    db.execute(
        "INSERT INTO audit_log (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)",
        (user_id, action, details, ip_address),
    )
    db.commit()
