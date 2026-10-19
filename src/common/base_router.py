from collections.abc import Sequence

from fastapi import APIRouter


def base_router(prefix: str, tags: Sequence[str]) -> APIRouter:
    return APIRouter(prefix=prefix, tags=list(tags))
