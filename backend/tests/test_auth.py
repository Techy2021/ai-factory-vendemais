import asyncio
import json
import unittest
from http.cookies import SimpleCookie
from unittest.mock import patch

from fastapi import HTTPException

from app import auth
from app.main import app


ORIGIN = "https://dashboard.example.test"
PASSWORD = "a-test-password-not-a-credential"
ENVIRONMENT = {
    "VENDEMAIS_ADMIN_PASSWORD": PASSWORD,
    "VENDEMAIS_ALLOWED_ORIGIN": ORIGIN,
    "VENDEMAIS_COOKIE_SECURE": "true",
}


def request(method, path, *, body=None, headers=None, query=b""):
    messages = []
    raw_body = json.dumps(body).encode() if body is not None else b""
    raw_headers = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]
    if body is not None:
        raw_headers.append((b"content-type", b"application/json"))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "https",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": query,
        "root_path": "",
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
        "server": ("dashboard.example.test", 443),
    }

    async def run():
        delivered = False

        async def receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": raw_body, "more_body": False}
            await asyncio.Event().wait()

        async def send(message):
            messages.append(message)

        await app(scope, receive, send)

    asyncio.run(run())
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_headers = {key.decode().lower(): value.decode() for key, value in start["headers"]}
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return start["status"], response_headers, response_body


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        auth._sessions.clear()
        auth._attempts.clear()
        environment = patch.dict("os.environ", ENVIRONMENT, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.addCleanup(auth._sessions.clear)
        self.addCleanup(auth._attempts.clear)

    def login(self, password=PASSWORD, origin=ORIGIN, cookie=None):
        headers = {"origin": origin} if origin is not None else {}
        if cookie:
            headers["cookie"] = cookie
        return request("POST", "/auth/login", body={"password": password}, headers=headers)

    def login_cookie(self):
        status, headers, _ = self.login()
        self.assertEqual(status, 204)
        cookie = SimpleCookie()
        cookie.load(headers["set-cookie"])
        return f"{auth.COOKIE_NAME}={cookie[auth.COOKIE_NAME].value}", cookie[auth.COOKIE_NAME]

    def test_public_health_and_unauthenticated_business_routes(self):
        self.assertEqual(request("GET", "/health")[0], 200)
        for path in ("/api/leads", "/api/metrics"):
            self.assertEqual(request("GET", path)[0], 401)
            self.assertEqual(request("GET", path, query=b"start_date=invalid")[0], 401)
            self.assertEqual(
                request("GET", path, headers={"cookie": f"{auth.COOKIE_NAME}=invalid"})[0],
                401,
            )

    def test_login_cookie_and_business_routes(self):
        cookie, morsel = self.login_cookie()
        self.assertTrue(morsel["httponly"])
        self.assertTrue(morsel["secure"])
        self.assertEqual(morsel["samesite"].lower(), "strict")
        self.assertEqual(morsel["path"], "/")
        for path in ("/api/leads", "/api/metrics"):
            status, _, body = request("GET", path, headers={"cookie": cookie})
            self.assertEqual(status, 503)
            self.assertEqual(json.loads(body)["code"], "DATA_SOURCE_NOT_CONFIGURED")
        self.assertEqual(
            request("GET", "/api/leads", headers={"cookie": cookie}, query=b"page=0")[0],
            422,
        )

    def test_wrong_password_and_rate_limit(self):
        for _ in range(auth.LOGIN_ATTEMPTS):
            self.assertEqual(self.login("incorrect")[0], 401)
        status, headers, _ = self.login()
        self.assertEqual(status, 429)
        self.assertGreater(int(headers["retry-after"]), 0)
        with patch("app.auth.time.monotonic", return_value=auth._attempts[0] + auth.LOGIN_WINDOW_SECONDS):
            self.assertEqual(self.login()[0], 204)

    def test_csrf_rejects_missing_or_foreign_origin(self):
        cookie, _ = self.login_cookie()
        for origin in (None, "https://attacker.example", "null"):
            with self.subTest(origin=origin):
                self.assertEqual(self.login(origin=origin)[0], 403)
                headers = {"cookie": cookie}
                if origin is not None:
                    headers["origin"] = origin
                self.assertEqual(request("POST", "/auth/logout", headers=headers)[0], 403)
                self.assertEqual(request("GET", "/api/leads", headers={"cookie": cookie})[0], 503)

    def test_cors_preflight_allows_only_configured_origin(self):
        headers = {
            "origin": ORIGIN,
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        }
        status, response_headers, _ = request("OPTIONS", "/auth/login", headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(response_headers.get("access-control-allow-origin"), ORIGIN)
        self.assertEqual(response_headers.get("access-control-allow-credentials"), "true")
        for origin in ("https://attacker.example", "null"):
            with self.subTest(origin=origin):
                status, response_headers, _ = request(
                    "OPTIONS", "/auth/login", headers={**headers, "origin": origin}
                )
                self.assertEqual(status, 400)
                self.assertNotIn("access-control-allow-origin", response_headers)
        with patch.dict("os.environ", {"VENDEMAIS_ALLOWED_ORIGIN": "*"}):
            status, response_headers, _ = request("OPTIONS", "/auth/login", headers=headers)
            self.assertEqual(status, 400)
            self.assertNotIn("access-control-allow-origin", response_headers)

    def test_cors_response_headers_on_login_logout_and_protected_errors(self):
        status, headers, _ = self.login("incorrect")
        self.assertEqual(status, 401)
        self.assertEqual(headers.get("access-control-allow-origin"), ORIGIN)
        self.assertEqual(headers.get("access-control-allow-credentials"), "true")
        cookie, _ = self.login_cookie()
        status, headers, _ = request("GET", "/api/metrics", headers={"origin": ORIGIN, "cookie": cookie})
        self.assertEqual(status, 503)
        self.assertEqual(headers.get("access-control-allow-origin"), ORIGIN)
        status, headers, _ = request("POST", "/auth/logout", headers={"origin": ORIGIN, "cookie": cookie})
        self.assertEqual(status, 204)
        self.assertEqual(headers.get("access-control-allow-origin"), ORIGIN)
        status, headers, _ = request("GET", "/api/metrics", headers={"origin": "https://attacker.example"})
        self.assertEqual(status, 401)
        self.assertNotIn("access-control-allow-origin", headers)

    def test_localhost_browser_authentication_and_cors(self):
        local_origin = "http://localhost:5173"
        with patch.dict("os.environ", {
            "VENDEMAIS_ALLOWED_ORIGIN": local_origin,
            "VENDEMAIS_COOKIE_SECURE": "false",
        }):
            status, headers, _ = request(
                "OPTIONS", "/auth/login",
                headers={
                    "origin": local_origin,
                    "access-control-request-method": "POST",
                    "access-control-request-headers": "content-type",
                },
            )
            self.assertEqual(status, 200)
            self.assertEqual(headers.get("access-control-allow-origin"), local_origin)
            self.assertEqual(headers.get("access-control-allow-credentials"), "true")
            status, headers, _ = self.login(origin=local_origin)
            self.assertEqual(status, 204)
            self.assertEqual(headers.get("access-control-allow-origin"), local_origin)
            cookie = SimpleCookie()
            cookie.load(headers["set-cookie"])
            morsel = cookie[auth.COOKIE_NAME]
            self.assertTrue(morsel["httponly"])
            self.assertFalse(morsel["secure"])
            self.assertEqual(morsel["samesite"].lower(), "strict")
            status, headers, _ = request(
                "POST", "/auth/logout",
                headers={"origin": local_origin, "cookie": f"{auth.COOKIE_NAME}={morsel.value}"},
            )
            self.assertEqual(status, 204)
            self.assertEqual(headers.get("access-control-allow-origin"), local_origin)

    def test_localhost_session_round_trip_with_mocked_data(self):
        origin = "http://localhost:5173"
        with patch.dict("os.environ", {
            "VENDEMAIS_ALLOWED_ORIGIN": origin,
            "VENDEMAIS_COOKIE_SECURE": "false",
        }):
            status, headers, _ = self.login("incorrect", origin=origin)
            self.assertEqual(status, 401)
            self.assertEqual(headers.get("access-control-allow-origin"), origin)
            status, headers, _ = self.login(origin=origin)
            self.assertEqual(status, 204)
            self.assertEqual(headers.get("access-control-allow-origin"), origin)
            self.assertEqual(headers.get("access-control-allow-credentials"), "true")
            cookie = SimpleCookie()
            cookie.load(headers["set-cookie"])
            morsel = cookie[auth.COOKIE_NAME]
            self.assertTrue(morsel["httponly"])
            self.assertFalse(morsel["secure"])
            self.assertEqual(morsel["samesite"].lower(), "strict")
            cookie_header = f"{auth.COOKIE_NAME}={morsel.value}"

            with patch("app.main._filtered_records", return_value=[]):
                for path in ("/api/leads", "/api/metrics"):
                    status, headers, _ = request(
                        "GET", path, headers={"origin": origin, "cookie": cookie_header}
                    )
                    self.assertEqual(status, 200)
                    self.assertEqual(headers.get("access-control-allow-origin"), origin)
                    self.assertEqual(headers.get("access-control-allow-credentials"), "true")
            expiry = next(iter(auth._sessions.values()))
            with patch("app.auth.time.monotonic", return_value=expiry):
                status, headers, _ = request(
                    "GET", "/api/leads", headers={"origin": origin, "cookie": cookie_header}
                )
                self.assertEqual(status, 401)
                self.assertEqual(headers.get("access-control-allow-origin"), origin)
                status, headers, _ = request(
                    "POST", "/auth/logout", headers={"origin": origin, "cookie": cookie_header}
                )
                self.assertEqual(status, 204)
                self.assertEqual(headers.get("access-control-allow-origin"), origin)
                self.assertIn("Max-Age=0", headers["set-cookie"])

    def test_authorized_origin_receives_cors_on_403(self):
        with patch("app.auth.check_origin", side_effect=HTTPException(status_code=403)):
            status, headers, _ = self.login()
        self.assertEqual(status, 403)
        self.assertEqual(headers.get("access-control-allow-origin"), ORIGIN)
        self.assertEqual(headers.get("access-control-allow-credentials"), "true")

    def test_logout_revokes_session(self):
        cookie, _ = self.login_cookie()
        status, headers, _ = request(
            "POST", "/auth/logout", headers={"origin": ORIGIN, "cookie": cookie}
        )
        self.assertEqual(status, 204)
        self.assertIn("Max-Age=0", headers["set-cookie"])
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(request("GET", "/api/leads", headers={"cookie": cookie})[0], 401)

    def test_relogin_rotates_existing_session(self):
        cookie, _ = self.login_cookie()
        status, headers, _ = self.login(cookie=cookie)
        self.assertEqual(status, 204)
        self.assertEqual(request("GET", "/api/leads", headers={"cookie": cookie})[0], 401)
        self.assertIn(auth.COOKIE_NAME, headers["set-cookie"])

    def test_expired_session_is_rejected(self):
        cookie, _ = self.login_cookie()
        expiry = next(iter(auth._sessions.values()))
        with patch("app.auth.time.monotonic", return_value=expiry):
            self.assertEqual(request("GET", "/api/metrics", headers={"cookie": cookie})[0], 401)

    def test_openapi_documents_cookie_security(self):
        status, _, body = request("GET", "/openapi.json")
        self.assertEqual(status, 200)
        schema = json.loads(body)
        for path in ("/api/leads", "/api/metrics"):
            self.assertEqual(schema["paths"][path]["get"]["security"], [{"APIKeyCookie": []}])
            self.assertIn("401", schema["paths"][path]["get"]["responses"])
        self.assertEqual(schema["components"]["securitySchemes"]["APIKeyCookie"]["in"], "cookie")

    def test_session_limit_and_relogin_at_capacity(self):
        cookie, _ = self.login_cookie()
        with patch("app.auth.MAX_SESSIONS", 1):
            self.assertEqual(self.login()[0], 503)
            self.assertEqual(self.login(cookie=cookie)[0], 204)

    def test_missing_or_invalid_configuration_fails_closed(self):
        cookie, _ = self.login_cookie()
        for changes in (
            {"VENDEMAIS_ADMIN_PASSWORD": ""},
            {"VENDEMAIS_ALLOWED_ORIGIN": ""},
            {"VENDEMAIS_ALLOWED_ORIGIN": "https://dashboard.example.test/path"},
            {"VENDEMAIS_ALLOWED_ORIGIN": "http://dashboard.example.test"},
            {"VENDEMAIS_COOKIE_SECURE": "false"},
            {"VENDEMAIS_COOKIE_SECURE": "invalid"},
        ):
            with self.subTest(changes=changes), patch.dict("os.environ", changes):
                self.assertEqual(self.login()[0], 503)
                self.assertEqual(request("GET", "/api/leads", headers={"cookie": cookie})[0], 503)

    def test_local_insecure_cookie_requires_loopback_origin(self):
        with patch.dict("os.environ", {
            "VENDEMAIS_COOKIE_SECURE": "false",
            "VENDEMAIS_ALLOWED_ORIGIN": "http://127.0.0.1:8000",
        }):
            status, headers, _ = self.login(origin="http://127.0.0.1:8000")
            self.assertEqual(status, 204)
            cookie = SimpleCookie()
            cookie.load(headers["set-cookie"])
            self.assertFalse(cookie[auth.COOKIE_NAME]["secure"])

    def test_auth_validation_does_not_echo_password(self):
        secret = "x" * 1025
        status, headers, body = self.login(password=secret)
        self.assertEqual(status, 422)
        self.assertNotIn(secret.encode(), body)
        self.assertEqual(headers["cache-control"], "no-store")


if __name__ == "__main__":
    unittest.main()
