import sqlite3
import unittest

from app.admin.routes import update_staff_account


class AdminStaffEditTests(unittest.TestCase):
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
                assigned_password TEXT,
                full_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                role_id INTEGER NOT NULL REFERENCES roles(role_id),
                status TEXT NOT NULL DEFAULT 'Active'
            );
            """
        )
        self.db.execute("INSERT INTO roles (role_id, role_name) VALUES (1, 'Teacher'), (2, 'Coordinator')")
        self.db.execute(
            "INSERT INTO users (user_id, username, password_hash, assigned_password, full_name, email, phone, role_id, status) VALUES (1, 'teacher1', 'hash', 'Welcome123', 'Teacher One', 'old@example.com', '111', 1, 'Active')"
        )
        self.db.commit()

    def test_update_staff_account_updates_profile_fields(self):
        update_staff_account(
            self.db,
            1,
            {
                "username": "teacher_updated",
                "full_name": "Teacher Two",
                "email": "new@example.com",
                "phone": "222",
                "role": "Coordinator",
                "password": "",
            },
        )

        updated = self.db.execute("SELECT username, full_name, email, phone, role_id FROM users WHERE user_id = 1").fetchone()
        role = self.db.execute("SELECT role_id FROM roles WHERE role_name = 'Coordinator'").fetchone()["role_id"]

        self.assertEqual(updated["username"], "teacher_updated")
        self.assertEqual(updated["full_name"], "Teacher Two")
        self.assertEqual(updated["email"], "new@example.com")
        self.assertEqual(updated["phone"], "222")
        self.assertEqual(updated["role_id"], role)


if __name__ == "__main__":
    unittest.main()
