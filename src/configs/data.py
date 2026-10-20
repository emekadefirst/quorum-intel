import os

from dotenv import load_dotenv

load_dotenv()

# -- Deriv (active broker) --------------------------------------------------
# Get an API token from https://app.deriv.com/account/api-token (demo first).
# app_id 1089 is Deriv's open sandbox app_id; replace with your own for prod.
DERIV_API_TOKEN = os.getenv("DERIV_API_TOKEN", "")
DERIV_APP_ID = os.getenv("DERIV_APP_ID", "1089")
DERIV_WS_URL = os.getenv(
    "DERIV_WS_URL", f"wss://ws.derivws.com/websockets/v3?app_id={DERIV_APP_ID}"
)
# Default leverage used when placing multiplier contracts. 10x is conservative.
DERIV_DEFAULT_MULTIPLIER = int(os.getenv("DERIV_DEFAULT_MULTIPLIER", "10"))
# Hard safety cap: never let the agent stake more than this per trade.
DERIV_MAX_STAKE = float(os.getenv("DERIV_MAX_STAKE", "100"))

# -- OANDA (legacy; kept for when the account becomes available) ------------
OANDA_API_TOKEN = os.getenv("OANDA_API_TOKEN", "")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "")
OANDA_ENV = os.getenv("OANDA_ENV", "practice")
OANDA_MAX_ORDER_UNITS = int(os.getenv("OANDA_MAX_ORDER_UNITS", "10000"))
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
