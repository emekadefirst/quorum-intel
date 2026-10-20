# Quorum

Multi-signal FX trading intelligence. Combines quantitative analysis, news sentiment, and an LLM-driven agent to help a human trader think through decisions on GBP/USD. Several independent "voters" (quant signal, news, model, user) have to agree before a trade — that's the quorum.

> Status: pre-alpha. Demo-account only. Nothing here constitutes financial advice.

## Architecture

```
Dukascopy (history) ──┐
                      ├──> src/data ──> src/quant ──┐
Deriv (live + exec) ──┘                             ├──> src/intelligence (LLM agent)
                                                    │        │
RSS feeds (Fed/BoE/BBC) ───> src/news ──────────────┤        ├──> FastAPI (/api/*)
                                                    │        │        │
                                                    │        │        ├──> Jinja UI (/, /chat, …)
                                                    │        │        └──> MCP server (Claude Desktop)
                                                    │        │
                               Account + Trades ────┴────────┘
                               (Tortoise ORM + SQLite)
```

## Layers

| Layer | Purpose | Status |
|---|---|---|
| `src/data` | Unified OHLC adapters. Dukascopy for history, Deriv for live + execution | ✅ |
| `src/quant` | Features, regime, levels, patterns, directional model, insights JSON | ✅ |
| `src/news` | RSS fetch, GBP/USD-tuned relevance scoring, dedup, time-decayed digest | ✅ |
| `src/intelligence` | LLM adapter (5 providers), trading agent, LangChain tools, MCP server | ✅ |
| `src/modules/account` | Users, JWT auth, cookie refresh, Argon2 passwords | ✅ |
| `src/modules/signals` | HTTP wrapper + TTL cache around quant insights | ✅ |
| `src/modules/news` | HTTP wrapper + TTL cache around the news digest | ✅ |
| `src/modules/trades` | Trade persistence + broker orchestration (snapshot context on every trade) | ✅ |
| `src/modules/chat` | Chat endpoint feeding the trading agent | ✅ |
| `src/modules/web` | Jinja routes, server-side auth guard | ✅ |
| `templates/`, `static/` | Dark-mode UI: Tailwind + Alpine + HTMX | ✅ |
| Charts, order management UI | TODO | 🟡 |
| Streaming chat (SSE) | TODO | 🟡 |

## Quick start

Requires Python 3.13+, [uv](https://docs.astral.sh/uv/).

```cmd
git clone <this-repo> Quorum
cd Quorum
uv sync
copy .env.example .env     :: edit with your credentials
uv run db-migrate --name init
uv run db-upgrade
uv run dev
```

Open http://localhost:8000 → register → you're in.

## .env

```env
# Core
MODE=development
PORT=8000
VERSION=1.0.0
DATABASE_NAME=quorum.db
ACCEPTED_CORE_ORIGIN=http://localhost:8000

# JWT (generate with: python -c "import secrets; print(secrets.token_hex(32))")
JWT_ACCESS_SECRET=...
JWT_REFRESH_SECRET=...
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRY=15        # minutes
JWT_REFRESH_EXPIRY=7        # days

# Broker: Deriv (free demo at https://app.deriv.com)
DERIV_API_TOKEN=...
DERIV_APP_ID=1089           # sandbox app_id; fine for dev
DERIV_DEFAULT_MULTIPLIER=10
DERIV_MAX_STAKE=100         # hard cap per trade (USD)

# LLM: pick one provider
LLM_PROVIDER=anthropic      # anthropic | google-gemini | openai | deepseek | qwen
LLM_API_KEY=sk-ant-...
LLM_MODEL=                  # optional; sensible default per provider
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=2048
```

## Data pipeline

- **History**: Dukascopy, free, no API key, back to ~2003. Cached to `data_cache/dukascopy/*.parquet` per day.
- **Live + execution**: Deriv, WebSocket API, works in Nigeria. Multiplier contracts (`units` = stake, not base-currency units).
- **Legacy adapters**: OANDA code is kept in `src/data/oanda*.py` for when it accepts your region. Flip one import to switch back.

## LLM providers

Any of the five is a one-env-var switch — the agent and tools don't change:

| Provider | Module | Default model |
|---|---|---|
| `anthropic` | `langchain_anthropic` | `claude-sonnet-4-5` |
| `google-gemini` | `langchain_google_genai` | `gemini-2.5-flash` |
| `openai` | `langchain_openai` | `gpt-4o-mini` |
| `deepseek` | `langchain_openai` (compat) | `deepseek-chat` |
| `qwen` | `langchain_openai` (compat) | `qwen-plus` |

## Agent & tools

The trading agent (`src/intelligence/agents.py`) has access to these tools:

| Tool | What it does |
|---|---|
| `get_market_insights(pair, interval)` | Quant insights (snapshot, regime, model, levels) |
| `get_news_digest(lookback_hours, max_items)` | Scored, deduped news |
| `get_current_price(pairs)` | Latest ticks |
| `get_account_summary()` | Balance + status |
| `get_open_positions()` / `get_open_trades()` | Open contracts |
| `get_trade_history(count)` | Closed trades |
| `place_trade(pair, side, units, take_profit, stop_loss)` | Opens a Deriv multiplier contract |
| `close_trade(trade_id)` | Closes a contract |

Place-trade is hard-capped by `DERIV_MAX_STAKE`. The system prompt requires the agent to restate intent and get user confirmation before calling it.

## MCP server (Claude Desktop etc.)

Same tools, exposed over the Model Context Protocol:

```cmd
uv run quorum-mcp                      :: stdio (for Claude Desktop)
uv run quorum-mcp --transport sse      :: HTTP SSE
```

Claude Desktop config:
```json
{
  "mcpServers": {
    "quorum": {
      "command": "uv",
      "args": ["--directory", "C:/absolute/path/to/Quorum", "run", "quorum-mcp"]
    }
  }
}
```

## HTTP API

Auth is JWT cookie (set on login, refreshed via `/accounts/refresh`). All `/api/*` endpoints below require auth.

| Method | Path | Purpose |
|---|---|---|
| POST | `/accounts` | Register |
| POST | `/accounts/login` | Login (sets cookies) |
| POST | `/accounts/logout` | Clear cookies |
| POST | `/accounts/refresh` | Rotate access + refresh cookies |
| GET | `/accounts/me` | Current user |
| GET | `/api/signals/current?pair=GBPUSD&interval=1h` | Quant insights (cached 5 min) |
| GET | `/api/news/digest?lookback_hours=48&max_items=25` | News digest (cached 10 min) |
| GET | `/api/trades/account` | Broker account summary |
| GET | `/api/trades/positions` | Open positions |
| GET | `/api/trades/open` | Open trades |
| GET | `/api/trades` | DB-persisted trade history (paginated) |
| POST | `/api/trades` | Place a trade (persists w/ quant + news snapshot) |
| POST | `/api/trades/{id}/close` | Close a tracked trade |
| POST | `/api/chat/message` | Send a message to the trading agent |

Interactive docs at `/docs` in dev mode.

## Dev commands

```cmd
uv run dev                                    :: FastAPI with reload
uv run start                                  :: production server

uv run db-init                                :: aerich init
uv run db-init-db                             :: first schema
uv run db-migrate --name <desc>               :: new migration from model changes
uv run db-upgrade                             :: apply pending migrations
uv run db-downgrade                           :: roll back one
uv run db-history                             :: list applied

uv run quorum-mcp                             :: MCP server (stdio)
uv run quorum-mcp --transport sse             :: MCP server (SSE/HTTP)

uv run python -m src.data._check              :: verify data adapters
uv run python -m src.news                     :: dump news digest to stdout
uv run python -m src.quant.main --yfinance    :: dump quant insights to stdout

uv run pytest                                 :: tests
uv run ruff check                             :: lint
uv run ruff format                            :: format
```

## Honesty built in (from the quant layer)

- Walk-forward only, with a purge gap of `horizon` bars between train and test.
- OOS stats use non-overlapping samples and report z-score / stderr.
- Costs are subtracted (`cost_bps`, default 1.0 bps round-trip).
- `model.signal_quality ∈ {no_edge_detected, weak, modest}` — never "strong" by design.
- On random-walk data the model reports `no_edge_detected`. Verify your own data the same way.
- News items in the digest are explicitly flagged UNTRUSTED. The agent prompt forbids following instructions found inside headlines.

## Known limits

- No economic calendar (CPI/payroll/rate dates) — relevance scoring doesn't know what's scheduled.
- Deriv contracts close whole; partial close isn't supported.
- Cache is in-memory per process. Restart = cold cache. Fine for dev; swap for Redis when scaling.
- Charts not implemented in the UI yet.
- No streaming for chat — the agent spins silently until the final answer.
- News relevance keywords are tuned for GBP/USD. Add other pairs = add keyword sets in `src/news/relevance.py`.

## Project naming

The source tree uses the historical name `intel` in `pyproject.toml` and keeps a few OANDA-prefixed files (`oanda.py`, `oanda_trading.py`) as reference adapters. Rename when stable.
