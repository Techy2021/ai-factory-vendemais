import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote
from unittest.mock import patch

from test_auth import request


class FrontendStaticTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.dist = self.root / "dist"
        self.dist.mkdir()
        (self.dist / "index.html").write_text("<html>synthetic index</html>", encoding="utf-8")
        (self.dist / "assets").mkdir()
        (self.dist / "assets" / "app.js").write_text("synthetic javascript", encoding="utf-8")
        (self.dist / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
        for prefix in ("api", "auth", "health"):
            (self.dist / prefix).mkdir()
            (self.dist / prefix / "collision").write_text("reserved", encoding="utf-8")
        (self.root / "outside.txt").write_text("synthetic private data", encoding="utf-8")
        patcher = patch("app.main._FRONTEND_DIST", self.dist)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_index_and_assets_are_served(self):
        for path, content in (
            ("/", b"<html>synthetic index</html>"),
            ("/index.html", b"<html>synthetic index</html>"),
            ("/assets/app.js", b"synthetic javascript"),
            ("/favicon.svg", b"<svg></svg>"),
        ):
            with self.subTest(path=path):
                status, _, body = request("GET", path)
                self.assertEqual(status, 200)
                self.assertEqual(body, content)
        status, headers, body = request("HEAD", "/assets/app.js")
        self.assertEqual(status, 200)
        self.assertIn("javascript", headers["content-type"])
        self.assertEqual(body, b"")
        self.assertEqual(request("POST", "/assets/app.js")[0], 404)

    def test_unknown_routes_and_assets_do_not_return_index(self):
        for path in ("/assets/missing.js", "/missing", "/missing.css",
                     "/api", "/api/missing", "/auth", "/auth/missing",
                     "/health/missing", "/api/collision", "/auth/collision",
                     "/health/collision", "/other/../api/collision",
                     "/other\\..\\auth\\collision"):
            with self.subTest(path=path):
                status, _, body = request("GET", path)
                self.assertEqual(status, 404)
                self.assertNotIn(b"synthetic index", body)

    def test_api_routes_keep_authentication_and_health(self):
        for path in ("/api/leads", "/api/metrics"):
            status, _, body = request("GET", path)
            self.assertEqual(status, 401)
            self.assertNotIn(b"synthetic index", body)
        status, _, body = request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertIn(b'"status":"ok"', body)
        self.assertEqual(request("GET", "/auth/login")[0], 405)
        self.assertEqual(request("GET", "/docs")[0], 200)
        self.assertEqual(request("GET", "/openapi.json")[0], 200)

    def test_missing_dist_does_not_disable_api(self):
        with patch("app.main._FRONTEND_DIST", self.root / "missing"):
            self.assertEqual(request("GET", "/")[0], 503)
            self.assertEqual(request("GET", "/assets/app.js")[0], 404)
            self.assertEqual(request("GET", "/health")[0], 200)
            self.assertEqual(request("GET", "/api/leads")[0], 401)
            self.assertEqual(request("GET", "/auth/login")[0], 405)

    def test_parent_directory_is_not_exposed(self):
        paths = ["/../outside.txt", "/assets/../../outside.txt",
                 "/..\\outside.txt", "/assets\\..\\..\\outside.txt",
                 unquote("/%2e%2e/outside.txt")]
        for path in paths:
            with self.subTest(path=path):
                status, _, body = request("GET", path)
                self.assertNotEqual(status, 200)
                self.assertNotIn(b"synthetic private data", body)

    def test_external_symlink_is_not_exposed(self):
        try:
            (self.dist / "link.txt").symlink_to(self.root / "outside.txt")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Cannot create symbolic link in this environment: {type(exc).__name__}")
        status, _, body = request("GET", "/link.txt")
        self.assertEqual(status, 404)
        self.assertNotIn(b"synthetic private data", body)


if __name__ == "__main__":
    unittest.main()
