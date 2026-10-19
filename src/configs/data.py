import os

from dotenv import load_dotenv

load_dotenv()

# OANDA (practice or live). Create a free practice account at https://developer.oanda.com
OANDA_API_TOKEN = os.getenv("OANDA_API_TOKEN", "")
OANDA_ENV = os.getenv("OANDA_ENV", "practice")  # "practice" or "live"
OANDA_BASE_URL = (
    "https://api-fxpractice.oanda.com"
    if OANDA_ENV == "practice"
    else "https://api-fxtrade.oanda.com"
)
OANDA_STREAM_URL = (
    "https://stream-fxpractice.oanda.com"
    if OANDA_ENV == "practice"
    else "https://stream-fxtrade.oanda.com"
)

# Where to cache downloaded candles. Dukascopy pulls can take a while.
DATA_CACHE_DIR = os.getenv("DATA_CACHE_DIR", "./data_cache")
