import asyncio
import json
import unittest
from urllib.parse import urlencode

from pydantic import ValidationError

from app.auth import require_authentication
from app.main import app
from app.models import Lead


def request(path: str, params: dict[str, str] | None = None) -> tuple[int, bytes]:
    messages = []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": urlencode(params or {}).encode("ascii"),
        "root_path": "",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(app(scope, receive, send))
    status = next(
        message["status"] for message in messages if message["type"] == "http.response.start"
    )
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return status, body


class APIContractTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[require_authentication] = lambda: None
        self.addCleanup(app.dependency_overrides.pop, require_authentication)

    def test_health(self):
        status, body = request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ok"})

    def test_business_endpoints_are_unavailable(self):
        cases = [
            ("/api/leads", {}),
            ("/api/leads", {
                "page": "1",
                "page_size": "100",
                "start_date": "2026-01-01",
                "end_date": "2026-01-01",
            }),
            ("/api/metrics", {}),
            ("/api/metrics", {"start_date": "2026-01-01", "end_date": "2026-01-31"}),
        ]
        for path, params in cases:
            with self.subTest(path=path, params=params):
                status, body = request(path, params)
                self.assertEqual(status, 503)
                self.assertEqual(
                    json.loads(body),
                    {
                        "code": "DATA_SOURCE_NOT_CONFIGURED",
                        "message": "Fonte de dados nao configurada.",
                    },
                )

    def test_invalid_queries(self):
        cases = [
            ("/api/leads", {"page": "0"}),
            ("/api/leads", {"page": "abc"}),
            ("/api/leads", {"page_size": "0"}),
            ("/api/leads", {"page_size": "101"}),
            ("/api/leads", {"start_date": "not-a-date"}),
            ("/api/leads", {"start_date": "2026-02-01", "end_date": "2026-01-31"}),
            ("/api/metrics", {"end_date": "2026-02-30"}),
            ("/api/metrics", {"start_date": "2026-02-01", "end_date": "2026-01-31"}),
        ]
        for path, params in cases:
            with self.subTest(path=path, params=params):
                status, _ = request(path, params)
                self.assertEqual(status, 422)

    def test_docs_and_openapi_contract(self):
        status, _ = request("/docs")
        self.assertEqual(status, 200)
        status, body = request("/openapi.json")
        self.assertEqual(status, 200)
        schema = json.loads(body)
        for path in ("/api/leads", "/api/metrics"):
            operation = schema["paths"][path]["get"]
            self.assertIn("503", operation["responses"])
            self.assertIn("200", operation["responses"])
            self.assertEqual(
                operation["responses"]["503"]["content"]["application/json"]["schema"]["$ref"],
                "#/components/schemas/ErrorResponse",
            )
            self.assertTrue({"start_date", "end_date"}.issubset(
                {parameter["name"] for parameter in operation["parameters"]}
            ))
        self.assertEqual(
            set(schema["components"]["schemas"]["Lead"]["properties"]),
            {
                "deal_id", "company_name", "industry", "size_employees",
                "tech_stack", "icp_match_score", "enriched_at",
            },
        )
        deal_id = schema["components"]["schemas"]["Lead"]["properties"]["deal_id"]
        self.assertEqual(
            {entry["type"] for entry in deal_id["anyOf"]}, {"string", "null"}
        )
        score = schema["components"]["schemas"]["Lead"]["properties"]["icp_match_score"]
        self.assertEqual(
            {entry["type"] for entry in score["anyOf"]}, {"integer", "number", "null"}
        )
        for variant in score["anyOf"]:
            if variant["type"] != "null":
                self.assertEqual(variant["minimum"], 0)
                self.assertEqual(variant["maximum"], 100)
        self.assertEqual(
            set(schema["components"]["schemas"]["LeadsResponse"]["properties"]),
            {"items", "total", "page", "page_size"},
        )
        self.assertEqual(
            set(schema["components"]["schemas"]["MetricsResponse"]["properties"]),
            {
                "leads_total",
                "average_score",
                "missing_score_count",
                "unique_deals",
            },
        )

    def test_lead_score_bounds_and_optional_id(self):
        for score in (-1, 101):
            with self.subTest(score=score), self.assertRaises(ValidationError):
                Lead(deal_id="test", icp_match_score=score)
        self.assertIsNone(Lead.model_validate({}).deal_id)
        self.assertIsNone(Lead.model_validate({"deal_id": None}).deal_id)
        with self.assertRaises(ValidationError):
            Lead.model_validate({"deal_id": 123})
        for score in (0, 100, 60.5, 0.00001, 99.99999):
            self.assertEqual(Lead(deal_id="test", icp_match_score=score).icp_match_score, score)


if __name__ == "__main__":
    unittest.main()
