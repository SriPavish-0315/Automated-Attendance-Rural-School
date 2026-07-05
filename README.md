# Rural School Attendance Management System

A Flask + SQLite school attendance system with three roles: **Administrator**,
**Coordinator**, and **Teacher**. Built from the project prompt spec, with two
performance/correctness fixes applied (see below).

## Fixes applied from the review

**1. SQLite write-concurrency**
`app/db.py` opens every connection with `PRAGMA journal_mode = WAL` and
`PRAGMA busy_timeout = 5000` (see `config.py`). This lets multiple teachers
submit attendance and the admin/coordinator read data at the same time
without hitting `database is locked` errors.

**2. "Offline-friendly" clarified as LAN deployment**
This is a normal client-server Flask app — the browser needs a live
connection to wherever Flask is running. "Offline-friendly for rural
schools" means: **run the Flask server on a computer inside the school and
access it over the local network** (no internet required), not an
installable offline web app. `run.py` binds to `0.0.0.0` so any device on
the school's Wi-Fi/LAN can open `http://<server-ip>:5000`. See
`config.py`'s `DEPLOYMENT_MODE` for where this is documented in code.

## Setup (VS Code / local machine)

```bash
# 1. Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create and seed the database
python database/seed.py

# 4. Run the app
python run.py
```

Open **http://127.0.0.1:5000** (or `http://<server-ip>:5000` from another
device on the same network).

## Demo logins (created by `database/seed.py`)

| Role          | Username      | Password     |
|---------------|---------------|--------------|
| Administrator | admin         | Admin@123    |
| Coordinator   | coordinator1  | Coord@123    |
| Teacher       | teacher1      | Teacher@123  |

A demo class (Grade 5 - A) with 5 students is pre-loaded so you can log in
as `teacher1` and mark attendance immediately.

## What's implemented

- **Auth**: login/logout, session timeout, remember-me, account lockout
  after 5 failed attempts, audit + login history logging.
- **Administrator**: dashboard with live stats, manage students, manage
  staff (teachers/coordinators), manage classes/sections and assignments.
- **Coordinator**: dashboard of assigned sections with today's marking
  status, drill into any section/date to see per-student attendance.
- **Teacher**: dashboard of assigned sections, mark attendance per student
  (Present/Absent/Half-Day/Late/Medical Leave/Official Leave) for any date,
  30-day attendance history summary.
- **RBAC**: every route is protected with `@role_required(...)`; wrong-role
  access returns 403.

## What's intentionally out of scope

- Parent portal (excluded per project scope — staff-only system).
- Full Reports & Analytics module (charts/PDF/Excel export) and Prompt 8-10
  detail items beyond core attendance — this build focuses on a working
  end-to-end core (auth → admin setup → teacher marks attendance →
  coordinator/admin see it) rather than every UI page in the 125-page spec.
  The structure (blueprints, `app/reports`, etc.) is ready to extend.

## Project structure

```
attendance_system/
├── app/
│   ├── auth/          # login/logout
│   ├── admin/          # student/staff/class management
│   ├── coordinator/    # section monitoring
│   ├── teacher/        # attendance marking
│   ├── templates/       # Jinja templates, organized by role
│   ├── static/css/js
│   ├── db.py            # SQLite connection (WAL mode fix)
│   ├── decorators.py    # login_required / role_required
│   └── __init__.py      # app factory
├── database/
│   ├── schema.sql
│   └── seed.py
├── config.py
├── run.py
└── requirements.txt
```
