import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, Response
from starlette.requests import Request

from src import app as activities_app
from src.teacher_auth import (
    create_session_token,
    hash_password,
    save_teacher,
    verify_password,
    verify_session_token,
)


class TeacherAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.teachers_file = Path(self.temp_dir.name) / "teachers.json"
        save_teacher("teacher", "a-long-test-password", self.teachers_file)
        self.original_activities = activities_app.activities
        activities_app.activities = {
            "Test Club": {
                "description": "A test activity",
                "schedule": "Mondays",
                "max_participants": 2,
                "participants": [],
            }
        }
        self.teachers_patch = patch.object(activities_app, "TEACHERS_FILE", self.teachers_file)
        self.teachers_patch.start()

    def tearDown(self):
        self.teachers_patch.stop()
        activities_app.activities = self.original_activities
        self.temp_dir.cleanup()

    @staticmethod
    def request_with_cookie(token=None):
        headers = [] if token is None else [(b"cookie", f"teacher_session={token}".encode())]
        return Request(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": "/",
                "raw_path": b"/",
                "query_string": b"",
                "headers": headers,
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
            }
        )

    def test_password_hash_is_salted_and_verifiable(self):
        first = hash_password("a-long-test-password")
        second = hash_password("a-long-test-password")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("a-long-test-password", first))
        self.assertFalse(verify_password("wrong-password", first))

    def test_activity_list_is_public_but_changes_require_teacher_login(self):
        self.assertIn("Test Club", activities_app.get_activities())
        request = self.request_with_cookie()
        with self.assertRaises(HTTPException) as signup_error:
            activities_app.signup_for_activity("Test Club", "student@school.edu", request)
        self.assertEqual(signup_error.exception.status_code, 401)

        with self.assertRaises(HTTPException) as unregister_error:
            activities_app.unregister_from_activity("Test Club", "student@school.edu", request)
        self.assertEqual(unregister_error.exception.status_code, 401)

    def test_teacher_can_login_register_and_unregister(self):
        response = Response()
        login_result = activities_app.teacher_login(
            activities_app.TeacherLogin(
                username=" TEACHER ", password="a-long-test-password"
            ),
            response,
        )
        self.assertTrue(login_result["authenticated"])
        cookie_header = next(value.decode() for name, value in response.raw_headers if name == b"set-cookie")
        token = cookie_header.split(";", 1)[0].split("=", 1)[1]
        self.assertEqual(verify_session_token(token, activities_app.session_secret), "teacher")
        request = self.request_with_cookie(token)

        signup = activities_app.signup_for_activity(
            "Test Club", "student@school.edu", request
        )
        self.assertIn("Signed up", signup["message"])

        unregister = activities_app.unregister_from_activity(
            "Test Club", "student@school.edu", request
        )
        self.assertIn("Unregistered", unregister["message"])

        activities_app.teacher_logout(Response())
        with self.assertRaises(HTTPException) as logout_error:
            activities_app.signup_for_activity(
                "Test Club", "other@school.edu", self.request_with_cookie()
            )
        self.assertEqual(logout_error.exception.status_code, 401)

    def test_invalid_login_is_rejected(self):
        with self.assertRaises(HTTPException) as login_error:
            activities_app.teacher_login(
                activities_app.TeacherLogin(username="teacher", password="incorrect"),
                Response(),
            )
        self.assertEqual(login_error.exception.status_code, 401)

    def test_session_token_expires_and_rejects_tampering(self):
        token = create_session_token("teacher", "secret", now=1000)
        self.assertEqual(verify_session_token(token, "secret", now=4599), "teacher")
        self.assertIsNone(verify_session_token(token, "secret", now=4601))
        self.assertIsNone(verify_session_token(token + "x", "secret", now=1000))


if __name__ == "__main__":
    unittest.main()