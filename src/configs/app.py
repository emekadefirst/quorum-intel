import os

from dotenv import load_dotenv

load_dotenv()

MODE = os.getenv("MODE", "development").strip().lower()
if MODE not in {"development", "production"}:
    raise ValueError("MODE must be either 'development' or 'production'")

PORT = int(os.getenv("PORT") or 8000)
VERSION = os.getenv("VERSION", "1.0.0")
DEBUG = MODE == "development"
DOCS_URL = "/docs" if DEBUG else None
REDOC_URL = "/redoc" if DEBUG else None
OPENAPI_URL = "/json" if DEBUG else None

ACCEPTED_CORE_ORIGIN = list(os.getenv("ACCEPTED_CORE_ORIGIN", "").split(","))
