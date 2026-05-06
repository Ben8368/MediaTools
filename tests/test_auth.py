import unittest
from unittest.mock import patch

from fastapi import HTTPException

from core import auth


class TestAuthHelpers(unittest.IsolatedAsyncioTestCase):
    def test_api_key_error_allows_when_secret_is_empty(self):
        self.assertIsNone(auth.api_key_error(None, ""))
        self.assertTrue(auth.is_api_key_valid(None, ""))

    def test_api_key_error_rejects_missing_and_invalid_keys(self):
        self.assertEqual(auth.api_key_error("", "secret"), (401, "Missing API key"))
        self.assertEqual(auth.api_key_error("wrong", "secret"), (403, "Invalid API key"))

    def test_api_key_error_accepts_matching_key(self):
        self.assertIsNone(auth.api_key_error("secret", "secret"))

    @patch("core.auth.API_SECRET_KEY", "secret")
    async def test_verify_api_key_raises_http_exception(self):
        with self.assertRaises(HTTPException) as ctx:
            await auth.verify_api_key("wrong")
        self.assertEqual(ctx.exception.status_code, 403)

    @patch("core.auth.API_SECRET_KEY", "secret")
    async def test_verify_api_key_returns_valid_key(self):
        self.assertEqual(await auth.verify_api_key("secret"), "secret")

    @patch("core.auth.API_SECRET_KEY", "secret")
    def test_optional_api_key(self):
        self.assertEqual(auth.get_optional_api_key("secret"), "secret")
        self.assertIsNone(auth.get_optional_api_key("wrong"))


if __name__ == "__main__":
    unittest.main()
