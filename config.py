import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

    DATABASE_PATH = os.path.join(BASE_DIR, "database", "attendance.db")

    # Session behaviour (matches Prompt 5 spec: 30 min inactivity timeout)
    PERMANENT_SESSION_LIFETIME_MINUTES = 30
    REMEMBER_ME_DAYS = 7

    # ---------------------------------------------------------------
    # FIX #1 - SQLite write-concurrency
    # ---------------------------------------------------------------
    # Multiple teachers/coordinators/admin can write at the same time
    # (attendance submissions, audit log entries, CRUD actions). Plain
    # SQLite locks the whole file on write and will raise
    # "database is locked" errors under concurrent access. WAL mode lets
    # readers and a writer work at the same time, and the busy_timeout
    # makes a second writer wait briefly instead of failing immediately.
    SQLITE_JOURNAL_MODE = "WAL"
    SQLITE_BUSY_TIMEOUT_MS = 5000

    # ---------------------------------------------------------------
    # FIX #2 - "Offline-friendly" clarification
    # ---------------------------------------------------------------
    # This is a normal client-server Flask app (REST APIs + session
    # auth), so a browser needs a live connection to wherever Flask is
    # running. "Offline-friendly for rural schools" means: run the
    # Flask server on a local machine inside the school (LAN), so the
    # school does NOT need internet access - only a local network.
    # It is NOT a service-worker / installable offline web app.
    # See README.md "Deployment model" section for details.
    DEPLOYMENT_MODE = "LAN"  # 'LAN' (local school server) or 'CLOUD'
