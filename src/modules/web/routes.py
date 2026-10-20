"""Server-rendered Jinja pages.

Auth model: every page except /login and /register requires a valid access
cookie. Protected pages use `require_web_auth` which redirects to /login
(preserving `next=`) instead of raising 401. The API side still uses
JwtService.get_current_user which returns proper JSON 401s.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jwt import PyJWTError

from src.configs.jwt import JWT_ACCESS_SECRET, JWT_ALGORITHM
from src.modules.account.models import Account

TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(include_in_schema=False)


class _RedirectToLogin(Exception):
    def __init__(self, next_url: str) -> None:
        self.next_url = next_url


async def require_web_auth(request: Request) -> Account:
    """Validate the access-cookie; redirect to /login if invalid.

    We raise an exception that the handler catches and converts to a redirect
    rather than raising RedirectResponse directly, so FastAPI's dependency
    machinery stays clean.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise _RedirectToLogin(request.url.path)

    try:
        payload = jwt.decode(
            token.strip(),
            JWT_ACCESS_SECRET.strip(),
            algorithms=[JWT_ALGORITHM],
        )
        sub_raw = payload.get("sub")
        if not sub_raw:
            raise _RedirectToLogin(request.url.path)
        sub = json.loads(sub_raw)
        user_id = uuid.UUID(sub["id"])
    except (PyJWTError, ValueError, KeyError, TypeError):
        raise _RedirectToLogin(request.url.path)

    user = await Account.get_or_none(id=user_id)
    if user is None:
        raise _RedirectToLogin(request.url.path)
    return user


def _render(request: Request, template: str, page: str, user: Account):
    return templates.TemplateResponse(
        request, template, {"page": page, "user_name": user.name}
    )


# -- Public pages ------------------------------------------------------------


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"page": "login"})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request, "register.html", {"page": "register"}
    )


# -- Protected pages --------------------------------------------------------


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user: Account = Depends(require_web_auth)):
    return _render(request, "dashboard.html", "dashboard", user)


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, user: Account = Depends(require_web_auth)):
    return _render(request, "chat.html", "chat", user)


@router.get("/signals", response_class=HTMLResponse)
async def signals_page(request: Request, user: Account = Depends(require_web_auth)):
    return _render(request, "signals.html", "signals", user)


@router.get("/news", response_class=HTMLResponse)
async def news_page(request: Request, user: Account = Depends(require_web_auth)):
    return _render(request, "news.html", "news", user)


# -- Redirect-to-login error handler ----------------------------------------


def register_auth_redirect(app) -> None:
    """Attach the exception handler to the FastAPI app."""

    @app.exception_handler(_RedirectToLogin)
    async def _handle(request: Request, exc: _RedirectToLogin):
        return RedirectResponse(url=f"/login?next={exc.next_url}", status_code=303)
