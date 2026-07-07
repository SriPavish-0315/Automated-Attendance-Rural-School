import sqlite3
import unittest

from app.admin.routes import update_staff_section_assignment


class AdminStaffAssignmentTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE roles (
                role_id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_name TEXT UNIQUE NOT NULL
            );
            CREATE TABLE users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role_id INTEGER NOT NULL REFERENCES roles(role_id),
                status TEXT NOT NULL DEFAULT 'Active'
            );
            CREATE TABLE classes (
                class_id INTEGER PRIMARY KEY AUTOINCREMENT,
                grade_name TEXT NOT NULL
            );
            CREATE TABLE sections (
                section_id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER NOT NULL REFERENCES classes(class_id),
                section_name TEXT NOT NULL,
                teacher_id INTEGER REFERENCES users(user_id),
                coordinator_id INTEGER REFERENCES users(user_id)
            );
            """
        )
        self.db.execute("INSERT INTO roles (role_id, role_name) VALUES (1, 'Teacher'), (2, 'Coordinator')")
        self.db.execute(
            "INSERT INTO users (user_id, username, password_hash, full_name, role_id, status) VALUES (1, 'teacher1', 'x', 'Teacher One', 1, 'Active')"
        )
        self.db.execute(
            "INSERT INTO users (user_id, username, password_hash, full_name, role_id, status) VALUES (2, 'coordinator1', 'x', 'Coordinator One', 2, 'Active')"
        )
        self.db.execute("INSERT INTO classes (class_id, grade_name) VALUES (1, 'Grade 5')")
        self.db.execute(
            "INSERT INTO sections (section_id, class_id, section_name, teacher_id, coordinator_id) VALUES (1, 1, 'A', NULL, NULL), (2, 1, 'B', 1, NULL)"
        )
        self.db.commit()

    def test_assigning_teacher_to_new_section_replaces_previous_assignment(self):
        update_staff_section_assignment(self.db, 1, "Teacher", 1)

        section_one = self.db.execute("SELECT teacher_id FROM sections WHERE section_id = 1").fetchone()
        section_two = self.db.execute("SELECT teacher_id FROM sections WHERE section_id = 2").fetchone()

        self.assertEqual(section_one["teacher_id"], 1)
        self.assertIsNone(section_two["teacher_id"])

    def test_unassigning_staff_clears_assignment(self):
        update_staff_section_assignment(self.db, 1, "Teacher", None)

        section_two = self.db.execute("SELECT teacher_id FROM sections WHERE section_id = 2").fetchone()
        self.assertIsNone(section_two["teacher_id"])


if __name__ == "__main__":
    unittest.main()
