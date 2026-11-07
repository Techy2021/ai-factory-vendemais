import os
import subprocess
import sys
import unittest
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]


class EnvironmentTests(unittest.TestCase):
    def run_case(self, environment, code):
        variables = {
            key: os.environ[key]
            for key in ("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP")
            if key in os.environ
        }
        variables.update({
            "PYTHONDONTWRITEBYTECODE": "1",
            "VENDEMAIS_ADMIN_PASSWORD": "synthetic-password-for-tests",
            "VENDEMAIS_ALLOWED_ORIGIN": "https://dashboard.example.test",
            "VENDEMAIS_COOKIE_SECURE": "true",
        })
        variables.update(environment)
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=BACKEND,
            env=variables,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_development_docs_and_local_insecure_cookie(self):
        self.run_case({"VENDEMAIS_ENV": "development"}, """
import sys
sys.path.insert(0, "tests")
from test_auth import request
from unittest.mock import patch
for path in ("/docs", "/redoc", "/openapi.json"):
    assert request("GET", path)[0] == 200
with patch.dict("os.environ", {"VENDEMAIS_ALLOWED_ORIGIN": "http://localhost:5173", "VENDEMAIS_COOKIE_SECURE": "false"}):
    status, headers, _ = request("POST", "/auth/login", body={"password": "synthetic-password-for-tests"}, headers={"origin": "http://localhost:5173"})
    assert status == 204 and "HttpOnly" in headers["set-cookie"] and "Secure" not in headers["set-cookie"]
    assert "SameSite=strict" in headers["set-cookie"]
""")

    def test_production_and_default_disable_docs_and_secure_auth(self):
        for environment in ({"VENDEMAIS_ENV": "production"}, {}):
            with self.subTest(environment=environment):
                self.run_case(environment, """
import sys
sys.path.insert(0, "tests")
from test_auth import request
from http.cookies import SimpleCookie
from unittest.mock import patch
origin = "https://dashboard.example.test"
for path in ("/docs", "/redoc", "/openapi.json"):
    assert request("GET", path)[0] == 404
    assert request("HEAD", path)[0] == 404
assert request("GET", "/health")[0] == 200
for path in ("/api/leads", "/api/metrics"):
    assert request("GET", path)[0] == 401
status, _, _ = request("POST", "/auth/login", body={"password": "synthetic-password-for-tests"}, headers={"origin": "https://other.example.test"})
assert status == 403
status, headers, _ = request("POST", "/auth/login", body={"password": "synthetic-password-for-tests"}, headers={"origin": origin})
assert status == 204 and headers.get("access-control-allow-origin") == origin
cookie = SimpleCookie()
cookie.load(headers["set-cookie"])
for source, expected in ((origin, 200), ("https://other.example.test", 400)):
    status, headers, _ = request("OPTIONS", "/auth/login", headers={"origin": source, "access-control-request-method": "POST"})
    assert status == expected
    assert headers.get("access-control-allow-origin") == (origin if source == origin else None)
morsel = cookie["vendemais_session"]
assert morsel["secure"] and morsel["httponly"] and morsel["samesite"].lower() == "strict"
cookie_header = "vendemais_session=" + morsel.value
with patch("app.main._filtered_records", return_value=[]):
    for path in ("/api/leads", "/api/metrics"):
        assert request("GET", path, headers={"cookie": cookie_header})[0] == 200
status, headers, _ = request("GET", "/api/leads", headers={"origin": "https://other.example.test"})
assert status == 401 and "access-control-allow-origin" not in headers
assert request("POST", "/auth/logout", headers={"origin": origin, "cookie": cookie_header})[0] == 204
assert request("GET", "/api/leads", headers={"cookie": cookie_header})[0] == 401
with patch.dict("os.environ", {"VENDEMAIS_ALLOWED_ORIGIN": "http://localhost:5173", "VENDEMAIS_COOKIE_SECURE": "false"}):
    status, headers, body = request("POST", "/auth/login", body={"password": "synthetic-password-for-tests"}, headers={"origin": "http://localhost:5173"})
    assert status == 503 and "set-cookie" not in headers and b"synthetic-password-for-tests" not in body
    assert request("POST", "/auth/logout", headers={"origin": "http://localhost:5173"})[0] == 503
""")

    def test_invalid_environment_fails_closed_without_echo(self):
        for value in ("invalid-synthetic-value", "", "Production", " production"):
            with self.subTest(value=value):
                self.run_case({"VENDEMAIS_ENV": value}, """
try:
    import app.main
except RuntimeError as exc:
    assert "VENDEMAIS_ENV" in str(exc)
    assert "invalid-synthetic-value" not in str(exc)
else:
    raise AssertionError("invalid environment was accepted")
""")


if __name__ == "__main__":
    unittest.main()
