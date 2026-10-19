import calendar
import json
import uuid
from datetime import timedelta
from typing import Any, Optional

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, PyJWTError
from tortoise import timezone

from src.configs.jwt import (
    JWT_ACCESS_EXPIRY,
    JWT_ACCESS_SECRET,
    JWT_ALGORITHM,
    JWT_REFRESH_EXPIRY,
    JWT_REFRESH_SECRET,
)
from src.modules.account.models import Account


class JwtService:
    @staticmethod
    def is_browser(request: Request) -> bool:
        """Heuristic to detect browser-originated requests (including fetch/XHR).
        Uses presence of Origin/Sec-Fetch-* headers or common browser UA tokens.
        """
        if request.headers.get("Origin") or request.headers.get("Sec-Fetch-Site"):
            return True
        ua = request.headers.get("User-Agent", "").lower()
        browser_keywords = ["mozilla", "chrome", "safari", "edge", "opera", "firefox"]
        return any(keyword in ua for keyword in browser_keywords)

    @staticmethod
    def _trim_secret(secret: str) -> str:
        """
        Remove leading/trailing whitespace and newline characters from a secret.
        """
        if secret:
            return secret.strip()
        return secret

    @staticmethod
    def generate_tokens(
        subject: dict, request: Request, response: Optional[Response]
    ) -> dict[str, str]:
        access_expire = timezone.now() + timedelta(minutes=JWT_ACCESS_EXPIRY)
        access_payload = {
            "sub": json.dumps(subject),
            "exp": calendar.timegm(access_expire.utctimetuple()),
        }
        access_token = jwt.encode(
            access_payload,
            JwtService._trim_secret(JWT_ACCESS_SECRET),
            algorithm=JWT_ALGORITHM,
        )

        refresh_expire = timezone.now() + timedelta(days=JWT_REFRESH_EXPIRY)
        refresh_payload = {
            "sub": json.dumps(subject),
            "exp": calendar.timegm(refresh_expire.utctimetuple()),
        }
        refresh_token = jwt.encode(
            refresh_payload,
            JwtService._trim_secret(JWT_REFRESH_SECRET),
            algorithm=JWT_ALGORITHM,
        )
        is_browser = JwtService.is_browser(request)
        if is_browser and response is not None:
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,
                samesite="none",
                max_age=900,
            )
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite="none",
                max_age=604800,
            )
        return {"access_token": access_token, "refresh_token": refresh_token}

    @staticmethod
    def decode_token(token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, JWT_ACCESS_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

    @staticmethod
    async def get_current_user(
        request: Request,
        token: Optional[HTTPAuthorizationCredentials] = Depends(
            HTTPBearer(auto_error=False)
        ),
    ) -> Account:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        access_token = None
        if token is not None:
            access_token = token.credentials.strip()
        else:
            access_token = request.cookies.get("access_token")
        if not access_token:
            raise credentials_exception

        try:
            payload = jwt.decode(
                access_token,
                JwtService._trim_secret(JWT_ACCESS_SECRET),
                algorithms=[JWT_ALGORITHM],
            )
            sub_raw = payload.get("sub")
            if not sub_raw:
                raise credentials_exception
            try:
                sub = json.loads(sub_raw)
            except Exception:
                raise credentials_exception
            if not isinstance(sub, dict):
                raise credentials_exception

            user_id_str = sub.get("id")
            if not user_id_str:
                raise credentials_exception
            try:
                user_id = uuid.UUID(user_id_str)
            except ValueError:
                raise credentials_exception
            user = await Account.get_or_none(id=user_id)
            if not user:
                raise credentials_exception
            return user

        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except PyJWTError:
            raise credentials_exception

    @staticmethod
    async def refresh_tokens(
        refresh_token: Optional[str] = None,
        request: Optional[Request] = None,
        response: Optional[Response] = None,
    ) -> Any:
        """
        Validate a refresh token and issue new access + refresh tokens.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
        token_value = refresh_token.strip() if isinstance(refresh_token, str) else None
        if not token_value and request is not None:
            token_value = request.cookies.get("refresh_token")
        if not token_value:
            raise credentials_exception
        try:
            payload = jwt.decode(
                token_value,
                JwtService._trim_secret(JWT_REFRESH_SECRET),
                algorithms=[JWT_ALGORITHM],
            )
            sub_raw = payload.get("sub")
            if not sub_raw:
                raise credentials_exception
            try:
                sub = json.loads(sub_raw)
            except Exception:
                raise credentials_exception

            if not isinstance(sub, dict):
                raise credentials_exception

            user_id_str = sub.get("id")
            if not user_id_str:
                raise credentials_exception

            try:
                user_id = uuid.UUID(user_id_str)
            except ValueError:
                raise credentials_exception

            user = await Account.get_or_none(id=user_id)
            if not user:
                raise credentials_exception

            if request is None:
                raise credentials_exception

            token_data = {"id": str(user.id)}
            return JwtService.generate_tokens(
                subject=token_data, request=request, response=response
            )
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
            )
        except PyJWTError:
            raise credentials_exception
