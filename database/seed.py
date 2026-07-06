"""Run once to populate default roles, an admin login, and demo class data."""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from werkzeug.security import generate_password_hash  # noqa: E402

DB_PATH = os.path.join(os.path.dirname(__file__), "attendance.db")


def seed():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    cur = conn.cursor()

    # Roles
    for role in ("Administrator", "Coordinator", "Teacher"):
        cur.execute("INSERT OR IGNORE INTO roles (role_name) VALUES (?)", (role,))
    conn.commit()

    role_ids = {r: rid for rid, r in cur.execute("SELECT role_id, role_name FROM roles")}

    # Default admin user (username: admin / password: Admin@123)
    cur.execute("SELECT user_id FROM users WHERE username = ?", ("admin",))
    if cur.fetchone() is None:
        cur.execute(
            """INSERT INTO users (username, password_hash, assigned_password, full_name, email, role_id, status)
               VALUES (?, ?, ?, ?, ?, ?, 'Active')""",
            ("admin", generate_password_hash("Admin@123"), "Admin@123", "School Administrator",
             "admin@school.local", role_ids["Administrator"]),
        )

    # Demo coordinator
    cur.execute("SELECT user_id FROM users WHERE username = ?", ("coordinator1",))
    if cur.fetchone() is None:
        cur.execute(
            """INSERT INTO users (username, password_hash, assigned_password, full_name, email, role_id, status)
               VALUES (?, ?, ?, ?, ?, ?, 'Active')""",
            ("coordinator1", generate_password_hash("Coord@123"), "Coord@123", "Ravi Kumar (Coordinator)",
             "coordinator1@school.local", role_ids["Coordinator"]),
        )

    # Demo teacher
    cur.execute("SELECT user_id FROM users WHERE username = ?", ("teacher1",))
    if cur.fetchone() is None:
        cur.execute(
            """INSERT INTO users (username, password_hash, assigned_password, full_name, email, role_id, status)
               VALUES (?, ?, ?, ?, ?, ?, 'Active')""",
            ("teacher1", generate_password_hash("Teacher@123"), "Teacher@123", "Anitha S (Class Teacher)",
             "teacher1@school.local", role_ids["Teacher"]),
        )
    conn.commit()

    teacher_id = cur.execute("SELECT user_id FROM users WHERE username='teacher1'").fetchone()[0]
    coord_id = cur.execute("SELECT user_id FROM users WHERE username='coordinator1'").fetchone()[0]

    # Demo class/section
    cur.execute("SELECT class_id FROM classes WHERE grade_name = ?", ("Grade 5",))
    row = cur.fetchone()
    if row is None:
        cur.execute("INSERT INTO classes (grade_name) VALUES ('Grade 5')")
        class_id = cur.lastrowid
    else:
        class_id = row[0]

    cur.execute("SELECT section_id FROM sections WHERE class_id=? AND section_name='A'", (class_id,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO sections (class_id, section_name, teacher_id, coordinator_id) VALUES (?, 'A', ?, ?)",
            (class_id, teacher_id, coord_id),
        )
        section_id = cur.lastrowid
    else:
        section_id = row[0]
    conn.commit()

    # Demo students
    demo_students = [
        ("ADM1001", "Arjun R", "1"),
        ("ADM1002", "Divya M", "2"),
        ("ADM1003", "Karthik S", "3"),
        ("ADM1004", "Lakshmi P", "4"),
        ("ADM1005", "Mohan V", "5"),
    ]
    for adm_no, name, roll in demo_students:
        cur.execute("SELECT student_id FROM students WHERE admission_no=?", (adm_no,))
        if cur.fetchone() is None:
            cur.execute(
                """INSERT INTO students (admission_no, full_name, roll_number, section_id,
                   parent_name, parent_contact, student_contact, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')""",
                (adm_no, name, roll, section_id, f"Parent of {name}", "9999999999", "8888888888"),
            )
    conn.commit()
    conn.close()
    print("Seed complete.")
    print("Login credentials:")
    print("  Administrator -> admin / Admin@123")
    print("  Coordinator   -> coordinator1 / Coord@123")
    print("  Teacher       -> teacher1 / Teacher@123")


if __name__ == "__main__":
    seed()
