import json
import unittest
from email.message import Message
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock

from app.airtable import (
    AUTHORIZED_FIELDS,
    MAX_RATE_LIMIT_RETRIES,
    AirtableAPIError,
    AirtableClient,
    AirtableConfig,
    AirtableConfigurationError,
    AirtableConnectionError,
    AirtableRateLimitError,
)


def config() -> AirtableConfig:
    return AirtableConfig.from_env(
        {
            "AIRTABLE_API_TOKEN": "test-token",
            "AIRTABLE_BASE_ID": "app_test",
            "AIRTABLE_TABLE_ID": "tbl_test",
        }
    )


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.body = json.dumps(payload).encode()

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class AirtableClientTests(unittest.TestCase):
    def test_configuration_requires_values_and_hides_token(self):
        with self.assertRaises(AirtableConfigurationError):
            AirtableConfig.from_env({})

        loaded = config()
        self.assertNotIn(loaded.token, repr(loaded))

    def test_uses_https_bearer_only_authorized_fields_and_paginates(self):
        requests = []
        responses = [
            {"records": [{"fields": {"deal_id": "d-1", "raw_search_results": "private"}}],
             "offset": "next-page"},
            {"records": [{"fields": {"company_name": "Company"}}]},
        ]

        def opener(request, *, timeout):
            requests.append((request, timeout))
            return FakeResponse(responses.pop(0))

        client = AirtableClient(config(), timeout=4.5, opener=opener)
        records = list(client.iter_records())

        self.assertEqual(records, [{"deal_id": "d-1"}, {"company_name": "Company"}])
        self.assertEqual(len(requests), 2)
        first_request, timeout = requests[0]
        self.assertEqual(urlsplit(first_request.full_url).scheme, "https")
        self.assertEqual(first_request.get_method(), "GET")
        self.assertEqual(first_request.get_header("Authorization"), "Bearer test-token")
        self.assertEqual(timeout, 4.5)
        first_query = parse_qs(urlsplit(first_request.full_url).query)
        self.assertEqual(first_query["pageSize"], ["100"])
        self.assertEqual(first_query["fields[]"], list(AUTHORIZED_FIELDS))
        second_query = parse_qs(urlsplit(requests[1][0].full_url).query)
        self.assertEqual(second_query["offset"], ["next-page"])

    def test_rejects_page_sizes_outside_airtable_limit(self):
        client = AirtableClient(config(), opener=Mock())
        for page_size in (0, 101):
            with self.subTest(page_size=page_size), self.assertRaises(ValueError):
                list(client.iter_records(page_size))

    def test_retries_429_using_retry_after_and_stops_after_limit(self):
        headers = Message()
        headers["Retry-After"] = "2"
        throttled = HTTPError(
            "https://api.airtable.com/", 429, "Too Many Requests", headers, None
        )
        opener = Mock(side_effect=[throttled, FakeResponse({"records": []})])
        sleeper = Mock()
        client = AirtableClient(config(), opener=opener, sleeper=sleeper)

        self.assertEqual(list(client.iter_records()), [])
        self.assertEqual(opener.call_count, 2)
        sleeper.assert_called_once_with(2.0)

        exhausted = HTTPError(
            "https://api.airtable.com/",
            429,
            "Too Many Requests",
            headers,
            None,
        )
        exhausted_opener = Mock(side_effect=[exhausted] * (MAX_RATE_LIMIT_RETRIES + 1))
        with self.assertRaises(AirtableRateLimitError):
            list(AirtableClient(config(), opener=exhausted_opener, sleeper=Mock()).iter_records())
        self.assertEqual(exhausted_opener.call_count, MAX_RATE_LIMIT_RETRIES + 1)

    def test_http_and_network_errors_are_safe(self):
        headers = Message()
        forbidden = HTTPError(
            "https://api.airtable.com/",
            403,
            "Forbidden",
            headers,
            None,
        )
        with self.assertRaises(AirtableAPIError) as response_error:
            list(AirtableClient(config(), opener=Mock(side_effect=forbidden)).iter_records())
        self.assertEqual(response_error.exception.status_code, 403)
        self.assertNotIn("test-token", str(response_error.exception))

        with self.assertRaises(AirtableConnectionError) as network_error:
            list(
                AirtableClient(
                    config(), opener=Mock(side_effect=URLError("private network detail"))
                ).iter_records()
            )
        self.assertNotIn("private network detail", str(network_error.exception))


if __name__ == "__main__":
    unittest.main()
