import json
import math
import os
import re
import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlunsplit
from urllib.request import Request, urlopen

AUTHORIZED_FIELDS = (
    "deal_id",
    "company_name",
    "industry",
    "size_employees",
    "tech_stack",
    "icp_match_score",
    "enriched_at",
)
MAX_PAGE_SIZE = 100
DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_RATE_LIMIT_RETRIES = 3
MAX_RETRY_AFTER_SECONDS = 30
_AIRTABLE_API_HOST = "api.airtable.com"
_SAFE_ID = re.compile(r"[A-Za-z0-9_-]+")


class AirtableError(Exception):
    """Base class for safe Airtable client errors."""


class AirtableConfigurationError(AirtableError):
    """Raised when required Airtable settings are missing or invalid."""


class AirtableConnectionError(AirtableError):
    """Raised when Airtable cannot be reached."""


class AirtableAPIError(AirtableError):
    """Raised when Airtable returns an unsuccessful or invalid response."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AirtableRateLimitError(AirtableAPIError):
    """Raised when Airtable continues rate limiting after the retry limit."""


@dataclass(frozen=True)
class AirtableConfig:
    token: str = field(repr=False)
    base_id: str
    table_id: str

    def __post_init__(self) -> None:
        if (
            not self.token.strip()
            or not _is_safe_id(self.base_id)
            or not _is_safe_id(self.table_id)
        ):
            raise AirtableConfigurationError(
                "Airtable configuration is missing or invalid."
            )

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "AirtableConfig":
        source = os.environ if environ is None else environ
        token = source.get("AIRTABLE_API_TOKEN", "").strip()
        base_id = source.get("AIRTABLE_BASE_ID", "").strip()
        table_id = source.get("AIRTABLE_TABLE_ID", "").strip()
        return cls(token=token, base_id=base_id, table_id=table_id)


class _Response(Protocol):
    def __enter__(self) -> "_Response": ...

    def __exit__(self, *args: object) -> object: ...

    def read(self) -> bytes: ...


class _Opener(Protocol):
    def __call__(self, request: Request, *, timeout: float) -> _Response: ...


def _is_safe_id(value: str) -> bool:
    return bool(value and _SAFE_ID.fullmatch(value))


def _retry_delay(value: str | None) -> float:
    if value:
        try:
            delay = float(min(MAX_RETRY_AFTER_SECONDS, max(0, int(value))))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                delay = (retry_at - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                delay = 1.0
    else:
        delay = 1.0
    return min(MAX_RETRY_AFTER_SECONDS, max(0.0, delay))


class AirtableClient:
    def __init__(
        self,
        config: AirtableConfig,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        opener: _Opener | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a finite positive number.")
        self._config = config
        self._timeout = timeout
        self._opener = urlopen if opener is None else opener
        self._sleep = sleeper
        self._url = urlunsplit(
            (
                "https",
                _AIRTABLE_API_HOST,
                f"/v0/{quote(config.base_id, safe='')}/{quote(config.table_id, safe='')}",
                "",
                "",
            )
        )

    def iter_records(self, page_size: int = MAX_PAGE_SIZE) -> Iterator[dict[str, object]]:
        if not 1 <= page_size <= MAX_PAGE_SIZE:
            raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}.")

        offset: str | None = None
        seen_offsets: set[str] = set()
        while True:
            records, next_offset = self._fetch_page(page_size, offset)
            for record in records:
                yield record
            if next_offset is None:
                return
            if not next_offset or next_offset in seen_offsets:
                raise AirtableAPIError("Airtable returned an invalid pagination offset.")
            seen_offsets.add(next_offset)
            offset = next_offset

    def _fetch_page(
        self, page_size: int, offset: str | None
    ) -> tuple[list[dict[str, object]], str | None]:
        params = [("pageSize", str(page_size))]
        params.extend(("fields[]", field_name) for field_name in AUTHORIZED_FIELDS)
        if offset is not None:
            params.append(("offset", offset))
        url = f"{self._url}?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._config.token}",
            },
            method="GET",
        )

        for retry in range(MAX_RATE_LIMIT_RETRIES + 1):
            try:
                with self._opener(request, timeout=self._timeout) as response:
                    body = response.read()
            except HTTPError as error:
                status_code = error.code
                retry_after = error.headers.get("Retry-After") if error.headers else None
                error.close()
                if status_code == 429:
                    if retry < MAX_RATE_LIMIT_RETRIES:
                        self._sleep(_retry_delay(retry_after))
                        continue
                    raise AirtableRateLimitError(
                        "Airtable rate limit exceeded after retries.", status_code
                    ) from None
                raise AirtableAPIError(
                    f"Airtable returned HTTP {status_code}.", status_code
                ) from None
            except (URLError, TimeoutError, OSError):
                raise AirtableConnectionError(
                    "Airtable could not be reached."
                ) from None

            try:
                payload = json.loads(body)
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise AirtableAPIError("Airtable returned an invalid response.") from None
            return self._parse_page(payload)

        raise AirtableRateLimitError(
            "Airtable rate limit exceeded after retries.", 429
        )

    @staticmethod
    def _parse_page(
        payload: object,
    ) -> tuple[list[dict[str, object]], str | None]:
        if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
            raise AirtableAPIError("Airtable returned an invalid response.")

        records: list[dict[str, object]] = []
        for record in payload["records"]:
            if not isinstance(record, dict) or not isinstance(record.get("fields"), dict):
                raise AirtableAPIError("Airtable returned an invalid response.")
            fields = record["fields"]
            records.append(
                {
                    field_name: fields[field_name]
                    for field_name in AUTHORIZED_FIELDS
                    if field_name in fields
                }
            )

        offset = payload.get("offset")
        if offset is not None and not isinstance(offset, str):
            raise AirtableAPIError("Airtable returned an invalid pagination offset.")
        return records, offset
