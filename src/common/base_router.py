from fastapi import APIRouter

def base_router(prefix: str, tags: list[str]) -> APIRouter:
    return APIRouter(prefix=prefix, tags=tags)