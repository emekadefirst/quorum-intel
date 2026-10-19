from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from tortoise.contrib.fastapi import register_tortoise

from src.configs.app import (
    ACCEPTED_CORE_ORIGIN,
    DEBUG,
    DOCS_URL,
    OPENAPI_URL,
    REDOC_URL,
    VERSION,
)
from src.core import TORTOISE_ORM, routes

app = FastAPI(
    title="Quorum",
    version=VERSION,
    debug=DEBUG,
    docs_url=DOCS_URL,
    redoc_url=REDOC_URL,
    openapi_url=OPENAPI_URL,
)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
app.mount("/ui/assets", StaticFiles(directory=TEMPLATES_DIR), name="ui-assets")


@app.get("/", include_in_schema=False)
@app.get("/ui", include_in_schema=False)
async def home_page():
    return FileResponse(TEMPLATES_DIR / "index.html")


app.add_middleware(
    CORSMiddleware,
    allow_origins=ACCEPTED_CORE_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for route in routes:
    app.include_router(route)

register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=False,
    add_exception_handlers=True,
)
