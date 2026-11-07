import math
import posixpath
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from .airtable import (
    AirtableClient,
    AirtableConfig,
    AirtableConfigurationError,
    AirtableError,
)
from .auth import LoginRequest, _configuration, login, logout, require_authentication
from .models import ErrorResponse, Lead, LeadsResponse, MetricsResponse
from .settings import IS_PRODUCTION

_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
_RESERVED_FRONTEND_PATHS = ("/api", "/auth", "/health", "/docs", "/redoc", "/openapi.json")


class FrontendStaticMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"GET", "HEAD"}:
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        normalized_path = "/" + posixpath.normpath(path.replace("\\", "/")).lstrip("/")
        if any(
            candidate == prefix or candidate.startswith(prefix + "/")
            for candidate in (path, normalized_path)
            for prefix in _RESERVED_FRONTEND_PATHS
        ):
            await self.app(scope, receive, send)
            return

        if not _FRONTEND_DIST.is_dir():
            response = JSONResponse(
                status_code=503 if path == "/" else 404,
                content={"detail": "Frontend indisponivel." if path == "/" else "Not Found"},
            )
            await response(scope, receive, send)
            return

        static_scope = dict(scope)
        if path == "/":
            static_scope["path"] = "/index.html"
        static = StaticFiles(directory=_FRONTEND_DIST, check_dir=False)
        try:
            await static(static_scope, receive, send)
        except StarletteHTTPException as exc:
            response = JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers,
            )
            await response(scope, receive, send)


class ConfiguredOriginCORSMiddleware(CORSMiddleware):
    def is_allowed_origin(self, origin: str) -> bool:
        try:
            _, allowed_origin, _ = _configuration()
        except HTTPException:
            return False
        return origin == allowed_origin


app = FastAPI(
    title="VendeMais Dashboard API",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)
app.add_middleware(FrontendStaticMiddleware)
app.add_middleware(
    ConfiguredOriginCORSMiddleware,
    allow_origins=[],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
_DATETIME_ADAPTER = TypeAdapter(datetime)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> Response:
    if request.url.path == "/auth/login":
        return JSONResponse(
            status_code=422,
            content={"detail": "Requisicao invalida."},
            headers={"Cache-Control": "no-store"},
        )
    response = await request_validation_exception_handler(request, exc)
    if request.url.path in {"/api/leads", "/api/metrics"}:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(request: Request, exc: StarletteHTTPException) -> Response:
    response = await http_exception_handler(request, exc)
    if request.url.path.startswith("/auth/") or request.url.path in {
        "/api/leads",
        "/api/metrics",
    }:
        response.headers["Cache-Control"] = "no-store"
    return response


def validate_period(
    start_date: Annotated[
        date | None, Query(description="Data inicial inclusiva de enriched_at (UTC).")
    ] = None,
    end_date: Annotated[
        date | None, Query(description="Data final inclusiva de enriched_at (UTC).")
    ] = None,
) -> tuple[date | None, date | None]:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date deve ser anterior ou igual a end_date.",
        )
    return start_date, end_date


def data_source_not_configured() -> JSONResponse:
    error = ErrorResponse(
        code="DATA_SOURCE_NOT_CONFIGURED",
        message="Fonte de dados nao configurada.",
    )
    return JSONResponse(
        status_code=503,
        content=error.model_dump(),
        headers={"Cache-Control": "no-store"},
    )


def data_source_unavailable() -> JSONResponse:
    error = ErrorResponse(
        code="DATA_SOURCE_UNAVAILABLE",
        message="Fonte de dados indisponivel.",
    )
    return JSONResponse(
        status_code=503,
        content=error.model_dump(),
        headers={"Cache-Control": "no-store"},
    )


def _record_matches_period(
    record: dict[str, object],
    start_date: date | None,
    end_date: date | None,
) -> bool:
    if start_date is None and end_date is None:
        return True
    enriched_at_value = record.get("enriched_at")
    if enriched_at_value is None:
        return False

    enriched_at = _DATETIME_ADAPTER.validate_python(enriched_at_value)
    if enriched_at.tzinfo is None:
        enriched_at = enriched_at.replace(tzinfo=timezone.utc)
    enriched_date = enriched_at.astimezone(timezone.utc).date()
    if start_date is not None and enriched_date < start_date:
        return False
    if end_date is not None and enriched_date > end_date:
        return False
    return True


def _valid_score(value: object) -> int | float | None:
    """Treat booleans, strings, non-finite, and out-of-range values as missing."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 0 <= value <= 100 else None
    if isinstance(value, float) and math.isfinite(value) and 0 <= value <= 100:
        return value
    return None


def _score_for_lead(value: object) -> int | float | None:
    return _valid_score(value)


def _filtered_records(
    period: tuple[date | None, date | None],
) -> list[dict[str, object]]:
    client = AirtableClient(AirtableConfig.from_env())
    records: list[dict[str, object]] = []
    for record in client.iter_records():
        if _record_matches_period(record, *period):
            records.append(record)
    return records


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/auth/login",
    status_code=204,
    responses={
        401: {"description": "Credenciais invalidas"},
        403: {"description": "Origem nao autorizada"},
        429: {"description": "Limite de tentativas excedido"},
        503: {"description": "Autenticacao indisponivel"},
    },
)
def auth_login(request: Request, response: Response, credentials: LoginRequest) -> None:
    login(request, response, credentials)


@app.post(
    "/auth/logout",
    status_code=204,
    responses={
        403: {"description": "Origem nao autorizada"},
        503: {"description": "Autenticacao indisponivel"},
    },
)
def auth_logout(request: Request, response: Response) -> None:
    logout(request, response)


@app.get(
    "/api/leads",
    response_model=LeadsResponse,
    dependencies=[Depends(require_authentication)],
    responses={
        401: {"description": "Autenticacao necessaria"},
        503: {"model": ErrorResponse, "description": "Fonte de dados indisponivel"},
    },
)
def get_leads(
    response: Response,
    page: Annotated[int, Query(ge=1, description="Pagina a partir de 1.")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    period: tuple[date | None, date | None] = Depends(validate_period),
) -> LeadsResponse | JSONResponse:
    try:
        filtered = []
        for record in _filtered_records(period):
            normalized_record = dict(record)
            normalized_record["icp_match_score"] = _score_for_lead(
                record.get("icp_match_score")
            )
            filtered.append(Lead.model_validate(normalized_record))
    except AirtableConfigurationError:
        unavailable = data_source_not_configured()
        unavailable.headers["Cache-Control"] = "no-store"
        return unavailable
    except (AirtableError, ValidationError):
        return data_source_unavailable()

    response.headers["Cache-Control"] = "no-store"
    start = (page - 1) * page_size
    return LeadsResponse(
        items=filtered[start : start + page_size],
        total=len(filtered),
        page=page,
        page_size=page_size,
    )


@app.get(
    "/api/metrics",
    response_model=MetricsResponse,
    dependencies=[Depends(require_authentication)],
    responses={
        401: {"description": "Autenticacao necessaria"},
        503: {"model": ErrorResponse, "description": "Fonte de dados indisponivel"},
    },
)
def get_metrics(
    response: Response,
    period: tuple[date | None, date | None] = Depends(validate_period),
) -> MetricsResponse | JSONResponse:
    try:
        filtered = _filtered_records(period)
    except AirtableConfigurationError:
        return data_source_not_configured()
    except (AirtableError, ValidationError):
        return data_source_unavailable()

    scores = [
        score
        for record in filtered
        if (score := _valid_score(record.get("icp_match_score"))) is not None
    ]
    response.headers["Cache-Control"] = "no-store"
    return MetricsResponse(
        leads_total=len(filtered),
        average_score=sum(scores) / len(scores) if scores else None,
        missing_score_count=len(filtered) - len(scores),
        unique_deals=len(
            {
                record["deal_id"].strip()
                for record in filtered
                if isinstance(record.get("deal_id"), str)
                and record["deal_id"].strip()
            }
        ),
    )
