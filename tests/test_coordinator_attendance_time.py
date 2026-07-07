import unittest

from app.coordinator.routes import format_marked_time


class CoordinatorAttendanceTimeTests(unittest.TestCase):
    def test_format_marked_time_uses_dot_separator_and_lowercase_am_pm(self):
        self.assertEqual(format_marked_time("2026-07-07 08:45:35"), "8.45.35 am")
        self.assertEqual(format_marked_time("2026-07-07 18:16:23"), "6.16.23 pm")
        self.assertEqual(format_marked_time(None), "-")


if __name__ == "__main__":
    unittest.main()
