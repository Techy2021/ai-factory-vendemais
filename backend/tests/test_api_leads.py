import asyncio
import json
import os
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from app.airtable import AirtableConnectionError
from app.auth import require_authentication
from app.main import app


def request(
    path: str, params: dict[str, str] | None = None
) -> tuple[int, dict[bytes, bytes], bytes]:
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
    start = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return start["status"], dict(start["headers"]), body


class FakeAirtableClient:
    def __init__(self, records: list[dict[str, object]]) -> None:
        self.records = records

    def iter_records(self):
        return iter(self.records)


class LeadsEndpointTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[require_authentication] = lambda: None
        self.addCleanup(app.dependency_overrides.pop, require_authentication)
        self.env = patch.dict(
            os.environ,
            {
                "AIRTABLE_API_TOKEN": "test-token",
                "AIRTABLE_BASE_ID": "app_test",
                "AIRTABLE_TABLE_ID": "tbl_test",
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_authentication_is_preserved_and_response_is_not_cached(self):
        app.dependency_overrides.pop(require_authentication)
        status, headers, _ = request("/api/leads")
        app.dependency_overrides[require_authentication] = lambda: None

        self.assertEqual(status, 401)
        self.assertEqual(headers[b"cache-control"], b"no-store")

    def test_period_filter_then_page_and_page_size(self):
        records = [
            {"deal_id": "d1", "icp_match_score": None, "enriched_at": "2026-03-01T12:00:00Z"},
            {"deal_id": "d2", "enriched_at": "2026-03-02T12:00:00Z"},
            {"deal_id": "old", "enriched_at": "2026-02-28T23:59:59Z"},
            {"deal_id": "missing-date"},
        ]
        with patch("app.main.AirtableClient", return_value=FakeAirtableClient(records)):
            status, headers, body = request(
                "/api/leads",
                {
                    "start_date": "2026-03-01",
                    "end_date": "2026-03-02",
                    "page": "2",
                    "page_size": "1",
                },
            )

        self.assertEqual(status, 200)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertEqual(
            json.loads(body),
            {
                "items": [
                    {
                        "deal_id": "d2",
                        "company_name": None,
                        "industry": None,
                        "size_employees": None,
                        "tech_stack": None,
                        "icp_match_score": None,
                        "enriched_at": "2026-03-02T12:00:00Z",
                    }
                ],
                "total": 2,
                "page": 2,
                "page_size": 1,
            },
        )

    def test_without_period_allows_missing_date_and_null_score(self):
        with patch(
            "app.main.AirtableClient",
            return_value=FakeAirtableClient([{"deal_id": "d1", "icp_match_score": None}]),
        ):
            status, _, body = request("/api/leads")

        self.assertEqual(status, 200)
        result = json.loads(body)
        self.assertEqual(result["total"], 1)
        self.assertIsNone(result["items"][0]["icp_match_score"])
        self.assertIsNone(result["items"][0]["enriched_at"])

    def test_missing_deal_id_and_text_tech_stack_preserve_records(self):
        records = [
            {"tech_stack": "alpha, beta", "company_name": "Example"},
            {"deal_id": "d1", "tech_stack": ["alpha", "beta"]},
            {"deal_id": None, "tech_stack": ""},
            {"deal_id": "d2", "tech_stack": None},
        ]
        with patch("app.main.AirtableClient", return_value=FakeAirtableClient(records)):
            status, headers, body = request("/api/leads", {"page_size": "10"})
            page_status, _, page_body = request(
                "/api/leads", {"page": "2", "page_size": "1"}
            )
            metrics_status, _, metrics_body = request("/api/metrics")

        self.assertEqual(status, 200)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        result = json.loads(body)
        self.assertEqual(result["total"], 4)
        self.assertEqual(len(result["items"]), 4)
        self.assertIsNone(result["items"][0]["deal_id"])
        self.assertEqual(result["items"][0]["company_name"], "Example")
        self.assertEqual(result["items"][0]["tech_stack"], ["alpha, beta"])
        self.assertEqual(result["items"][1]["tech_stack"], ["alpha", "beta"])
        self.assertIsNone(result["items"][2]["deal_id"])
        self.assertEqual(result["items"][2]["tech_stack"], [""])
        self.assertIsNone(result["items"][3]["tech_stack"])
        self.assertEqual(page_status, 200)
        self.assertEqual(json.loads(page_body)["total"], 4)
        self.assertEqual(json.loads(page_body)["items"][0]["deal_id"], "d1")
        self.assertEqual(metrics_status, 200)
        self.assertEqual(json.loads(metrics_body)["unique_deals"], 2)

    def test_unsupported_tech_stack_returns_safe_503(self):
        for value in (42, {"name": "alpha"}, ["alpha", 42]):
            with self.subTest(value=value), patch(
                "app.main.AirtableClient",
                return_value=FakeAirtableClient([{"tech_stack": value}]),
            ):
                status, headers, body = request("/api/leads")
            self.assertEqual(status, 503)
            self.assertEqual(headers[b"cache-control"], b"no-store")
            self.assertEqual(json.loads(body)["code"], "DATA_SOURCE_UNAVAILABLE")

    def test_invalid_period_returns_422(self):
        status, headers, _ = request(
            "/api/leads",
            {"start_date": "2026-03-02", "end_date": "2026-03-01"},
        )

        self.assertEqual(status, 422)
        self.assertEqual(headers[b"cache-control"], b"no-store")

    def test_unconfigured_and_unavailable_source_return_503(self):
        with patch.dict(os.environ, {}, clear=True):
            status, headers, body = request("/api/leads")
        self.assertEqual(status, 503)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertEqual(json.loads(body)["code"], "DATA_SOURCE_NOT_CONFIGURED")

        with patch(
            "app.main.AirtableClient",
            side_effect=AirtableConnectionError("safe error"),
        ):
            status, _, body = request("/api/leads")
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body)["code"], "DATA_SOURCE_UNAVAILABLE")

    def test_metrics_calculate_valid_scores_missing_scores_and_unique_deals(self):
        records = [
            {"deal_id": "d1", "icp_match_score": 80},
            {"deal_id": "d1 ", "icp_match_score": 60.5},
            {"deal_id": "  ", "icp_match_score": None},
            {"deal_id": "d2", "icp_match_score": "75"},
            {"deal_id": "d3", "icp_match_score": True},
            {"deal_id": "d4", "icp_match_score": 101},
            {"deal_id": "d5", "icp_match_score": -1},
            {"deal_id": None, "icp_match_score": 50},
        ]
        with patch("app.main.AirtableClient", return_value=FakeAirtableClient(records)):
            status, headers, body = request("/api/metrics")

        self.assertEqual(status, 200)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertEqual(
            json.loads(body),
            {
                "leads_total": 8,
                "average_score": 63.5,
                "missing_score_count": 5,
                "unique_deals": 5,
            },
        )

    def test_leads_and_metrics_share_score_normalization(self):
        values = [
            0, 100, 50, 60.5, 0.125, 99.875, 100.0,
            None, "75", True, False, -0.01, 100.01,
            float("nan"), float("inf"), float("-inf"), [], {},
        ]
        records = [{"deal_id": f"d{index}", "icp_match_score": value}
                   for index, value in enumerate(values)]
        records.append({"deal_id": "missing"})
        with patch("app.main.AirtableClient", return_value=FakeAirtableClient(records)):
            leads_status, _, leads_body = request("/api/leads", {"page_size": "100"})
            metrics_status, _, metrics_body = request("/api/metrics")

        self.assertEqual((leads_status, metrics_status), (200, 200))
        leads = json.loads(leads_body)
        metrics = json.loads(metrics_body)
        actual_scores = [item["icp_match_score"] for item in leads["items"]]
        expected_scores = [0, 100, 50, 60.5, 0.125, 99.875, 100.0] + [None] * 12
        self.assertEqual(actual_scores, expected_scores)
        self.assertEqual(leads["total"], len(records))
        self.assertEqual(metrics["leads_total"], len(records))
        self.assertEqual(metrics["missing_score_count"], actual_scores.count(None))
        self.assertAlmostEqual(metrics["average_score"], sum(expected_scores[:7]) / 7)

    def test_metrics_return_none_average_when_no_valid_scores_or_no_records(self):
        cases = [
            [{"deal_id": "d1", "icp_match_score": None}],
            [],
        ]
        for records in cases:
            with self.subTest(records=records), patch(
                "app.main.AirtableClient",
                return_value=FakeAirtableClient(records),
            ):
                status, _, body = request("/api/metrics")

            self.assertEqual(status, 200)
            result = json.loads(body)
            self.assertIsNone(result["average_score"])
            self.assertEqual(result["missing_score_count"], len(records))

    def test_metrics_period_uses_same_filtered_records_as_leads(self):
        records = [
            {"deal_id": "included", "icp_match_score": 90, "enriched_at": "2026-03-01T10:00:00Z"},
            {"deal_id": "excluded", "icp_match_score": 10, "enriched_at": "2026-02-28T10:00:00Z"},
            {"deal_id": "missing-date", "icp_match_score": 50},
        ]
        params = {"start_date": "2026-03-01", "end_date": "2026-03-01"}
        with patch("app.main.AirtableClient", return_value=FakeAirtableClient(records)):
            leads_status, _, leads_body = request("/api/leads", params)
            metrics_status, _, metrics_body = request("/api/metrics", params)

        self.assertEqual((leads_status, metrics_status), (200, 200))
        self.assertEqual(json.loads(leads_body)["total"], 1)
        self.assertEqual(json.loads(metrics_body)["leads_total"], 1)
        self.assertEqual(json.loads(metrics_body)["average_score"], 90.0)

    def test_metrics_preserve_authentication_and_validation_responses(self):
        app.dependency_overrides.pop(require_authentication)
        status, headers, _ = request("/api/metrics")
        app.dependency_overrides[require_authentication] = lambda: None
        self.assertEqual(status, 401)
        self.assertEqual(headers[b"cache-control"], b"no-store")

        status, headers, _ = request(
            "/api/metrics",
            {"start_date": "2026-03-02", "end_date": "2026-03-01"},
        )
        self.assertEqual(status, 422)
        self.assertEqual(headers[b"cache-control"], b"no-store")

    def test_metrics_source_errors_return_503_without_fabricated_values(self):
        with patch(
            "app.main.AirtableClient",
            side_effect=AirtableConnectionError("safe error"),
        ):
            status, headers, body = request("/api/metrics")

        self.assertEqual(status, 503)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertEqual(
            json.loads(body),
            {
                "code": "DATA_SOURCE_UNAVAILABLE",
                "message": "Fonte de dados indisponivel.",
            },
        )


if __name__ == "__main__":
    unittest.main()
