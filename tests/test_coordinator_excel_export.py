import unittest

from app.coordinator.routes import build_attendance_excel_rows


class CoordinatorExcelExportTests(unittest.TestCase):
    def test_build_attendance_excel_rows_includes_student_and_status(self):
        rows = build_attendance_excel_rows([
            {"full_name": "Alice", "roll_number": "1", "status": "Present", "remarks": "On time", "formatted_time": "8.45.35 am"},
            {"full_name": "Bob", "roll_number": "2", "status": "Absent", "remarks": "", "formatted_time": "-"},
        ])

        self.assertEqual(rows[0][0], "Alice")
        self.assertEqual(rows[0][2], "Present")
        self.assertEqual(rows[1][3], "-")


if __name__ == "__main__":
    unittest.main()
