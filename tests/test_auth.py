import unittest

from app.auth.routes import normalize_username, verify_password


class AuthHelpersTestCase(unittest.TestCase):
    def test_normalize_username_is_case_insensitive(self):
        self.assertEqual(normalize_username(" SATHHIYA "), "sathhiya")

    def test_verify_password_accepts_assigned_password_for_existing_accounts(self):
        self.assertTrue(verify_password("unused-hash", "Welcome123", "Welcome123"))


if __name__ == "__main__":
    unittest.main()
