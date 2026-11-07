import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import deque
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import APIKeyCookie
from pydantic import BaseModel, Field, SecretStr

from .settings import IS_PRODUCTION

COOKIE_NAME = "vendemais_session"
SESSION_SECONDS = 8 * 60 * 60
LOGIN_WINDOW_SECONDS = 5 * 60
LOGIN_ATTEMPTS = 5
MAX_SESSIONS = 1000

_lock = threading.Lock()
_sessions: dict[bytes, float] = {}
_attempts: deque[float] = deque()
session_cookie = APIKeyCookie(name=COOKIE_NAME, auto_error=False)


class LoginRequest(BaseModel):
    password: SecretStr = Field(min_length=1, max_length=1024)


def _configuration() -> tuple[str, str, bool]:
    password = os.environ.get("VENDEMAIS_ADMIN_PASSWORD", "")
    origin = os.environ.get("VENDEMAIS_ALLOWED_ORIGIN", "")
    secure_value = os.environ.get("VENDEMAIS_COOKIE_SECURE", "true").lower()
    if not password.strip() or len(password) > 1024 or secure_value not in {"true", "false"}:
        raise HTTPException(status_code=503, detail="Autenticacao nao configurada.")
    try:
        parsed = urlsplit(origin)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        raise HTTPException(status_code=503, detail="Autenticacao nao configurada.")
    secure = secure_value == "true"
    local_http = (
        not IS_PRODUCTION
        and not secure
        and parsed.scheme == "http"
        and hostname in {"localhost", "127.0.0.1", "::1"}
    )
    if (
        not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.netloc != (f"[{hostname}]" if ":" in hostname else hostname)
        + (f":{port}" if port is not None else "")
        or (not local_http and not (secure and parsed.scheme == "https"))
    ):
        raise HTTPException(status_code=503, detail="Autenticacao nao configurada.")
    return password, origin, secure


def check_origin(request: Request, allowed_origin: str) -> None:
    origins = request.headers.getlist("origin")
    if len(origins) != 1 or origins[0] != allowed_origin:
        raise HTTPException(status_code=403, detail="Origem nao autorizada.")


def _token_digest(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def _purge_expired(now: float) -> None:
    for token, expiry in list(_sessions.items()):
        if expiry <= now:
            del _sessions[token]


def login(request: Request, response: Response, credentials: LoginRequest) -> None:
    password, origin, secure = _configuration()
    check_origin(request, origin)
    with _lock:
        now = time.monotonic()
        while _attempts and _attempts[0] <= now - LOGIN_WINDOW_SECONDS:
            _attempts.popleft()
        if len(_attempts) >= LOGIN_ATTEMPTS:
            raise HTTPException(
                status_code=429,
                detail="Limite de tentativas excedido.",
                headers={"Retry-After": str(max(1, int(_attempts[0] + LOGIN_WINDOW_SECONDS - now) + 1))},
            )
        _attempts.append(now)
        if not hmac.compare_digest(
            credentials.password.get_secret_value().encode("utf-8"),
            password.encode("utf-8"),
        ):
            raise HTTPException(status_code=401, detail="Credenciais invalidas.")
        _purge_expired(now)
        old_token = request.cookies.get(COOKIE_NAME)
        if old_token:
            _sessions.pop(_token_digest(old_token), None)
        if len(_sessions) >= MAX_SESSIONS:
            raise HTTPException(status_code=503, detail="Limite de sessoes atingido.")
        token = secrets.token_urlsafe(32)
        _sessions[_token_digest(token)] = now + SESSION_SECONDS
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=secure,
        samesite="strict",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"


def require_authentication(token: str | None = Depends(session_cookie)) -> None:
    if token:
        with _lock:
            now = time.monotonic()
            _purge_expired(now)
            if _sessions.get(_token_digest(token), 0) > now:
                _configuration()
                return
    raise HTTPException(status_code=401, detail="Autenticacao necessaria.")


def logout(request: Request, response: Response) -> None:
    _, origin, secure = _configuration()
    check_origin(request, origin)
    token = request.cookies.get(COOKIE_NAME)
    if token:
        with _lock:
            _sessions.pop(_token_digest(token), None)
    response.delete_cookie(
        key=COOKIE_NAME, path="/", httponly=True, secure=secure, samesite="strict"
    )
    response.headers["Cache-Control"] = "no-store"
