from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from src.core import routes, TORTOISE_ORM
from src.quant.main import run_quant



# from src.modules import signals as _jd_signals
# from src.modules import signals as application_signal
from tortoise.contrib.fastapi import register_tortoise
from src.configs.app import (
    DEBUG, 
    DOCS_URL, 
    OPENAPI_URL, 
    REDOC_URL, 
    VERSION,
    ACCEPTED_CORE_ORIGIN
)



app = FastAPI(
    title="Inbox Helper",
    version=VERSION,
    debug=DEBUG,
    docs_url=DOCS_URL,
    redoc_url=REDOC_URL,
    openapi_url=OPENAPI_URL,
)

app.on_event(
run_quant()
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

register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=False,
    add_exception_handlers=True,
)
for route in routes:
    app.include_router(route)

register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=False,
    add_exception_handlers=True,
)