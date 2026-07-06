-- Automated Attendance Management System for Rural Schools
-- SQLite schema (core tables, condensed from the full project spec)

CREATE TABLE IF NOT EXISTS roles (
    role_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name   TEXT UNIQUE NOT NULL   -- Administrator, Coordinator, Teacher
);

CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    assigned_password TEXT,
    full_name       TEXT NOT NULL,
    email           TEXT,
    phone           TEXT,
    role_id         INTEGER NOT NULL REFERENCES roles(role_id),
    status          TEXT NOT NULL DEFAULT 'Active',   -- Active/Inactive/Suspended/Deleted
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS academic_years (
    academic_year_id INTEGER PRIMARY KEY AUTOINCREMENT,
    year_label        TEXT UNIQUE NOT NULL,   -- e.g. 2025-2026
    is_current         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS classes (
    class_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    grade_name  TEXT NOT NULL          -- e.g. "Grade 5"
);

CREATE TABLE IF NOT EXISTS sections (
    section_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id    INTEGER NOT NULL REFERENCES classes(class_id),
    section_name TEXT NOT NULL,        -- e.g. "A"
    teacher_id  INTEGER REFERENCES users(user_id),   -- assigned class teacher
    coordinator_id INTEGER REFERENCES users(user_id) -- assigned coordinator
);

CREATE TABLE IF NOT EXISTS students (
    student_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    admission_no  TEXT UNIQUE NOT NULL,
    full_name     TEXT NOT NULL,
    roll_number   TEXT NOT NULL,
    section_id    INTEGER NOT NULL REFERENCES sections(section_id),
    parent_name   TEXT,
    parent_contact TEXT,
    student_contact TEXT,
    status        TEXT NOT NULL DEFAULT 'Active',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS holidays (
    holiday_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    holiday_date TEXT NOT NULL,
    description  TEXT
);

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL REFERENCES students(student_id),
    section_id    INTEGER NOT NULL REFERENCES sections(section_id),
    marked_by     INTEGER NOT NULL REFERENCES users(user_id),
    attendance_date TEXT NOT NULL,
    status        TEXT NOT NULL,   -- Present/Absent/Half-Day/Late/Medical Leave/Official Leave
    remarks       TEXT,
    locked        INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(student_id, attendance_date)   -- one attendance record per student per day
);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(user_id),
    action      TEXT NOT NULL,
    details     TEXT,
    ip_address  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS login_history (
    login_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(user_id),
    login_time  TEXT NOT NULL DEFAULT (datetime('now')),
    logout_time TEXT,
    ip_address  TEXT,
    status      TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(user_id),
    message     TEXT NOT NULL,
    is_read     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes (performance)
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(attendance_date);
CREATE INDEX IF NOT EXISTS idx_attendance_section ON attendance(section_id);
CREATE INDEX IF NOT EXISTS idx_students_section ON students(section_id);
CREATE INDEX IF NOT EXISTS idx_sections_teacher ON sections(teacher_id);
CREATE INDEX IF NOT EXISTS idx_sections_coordinator ON sections(coordinator_id);
