"""Deriv WebSocket client.

Deriv's API is a req/resp protocol over a single WebSocket. For our low-frequency
agent/MCP use we open a short-lived connection per operation: connect, authorize,
send request, read response, close. Simpler than maintaining a persistent
connection with reconnect logic.

For streaming (ticks subscription) we'd want a long-lived connection; add later
if needed.
"""

from __future__ import annotations

import json
from typing import Any

import websockets

from src.configs.data import DERIV_API_TOKEN, DERIV_WS_URL


class DerivError(RuntimeError):
    """Deriv API returned an error in the response envelope."""


async def _send_recv(
    ws: Any, payload: dict[str, Any], req_id: int = 1
) -> dict[str, Any]:
    """Send one request and return the matching response. Deriv echoes req_id."""
    payload = {**payload, "req_id": req_id}
    await ws.send(json.dumps(payload))
    # Deriv may send unrelated messages (e.g. late ticks); skip until our req_id
    while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("req_id") == req_id:
            if "error" in msg:
                err = msg["error"]
                raise DerivError(f"{err.get('code')}: {err.get('message')}")
            return msg


async def deriv_call(
    payload: dict[str, Any], token: str | None = None
) -> dict[str, Any]:
    """One-shot authorized call. Opens WS, authorizes, sends, returns response."""
    auth_token = token or DERIV_API_TOKEN
    if not auth_token:
        raise RuntimeError("DERIV_API_TOKEN not set in environment")

    async with websockets.connect(DERIV_WS_URL) as ws:
        # Authorize first; req_id=0
        await _send_recv(ws, {"authorize": auth_token}, req_id=0)
        return await _send_recv(ws, payload, req_id=1)


async def deriv_calls(
    payloads: list[dict[str, Any]], token: str | None = None
) -> list[dict[str, Any]]:
    """Run several calls on one connection (saves authorize round-trips)."""
    auth_token = token or DERIV_API_TOKEN
    if not auth_token:
        raise RuntimeError("DERIV_API_TOKEN not set in environment")

    async with websockets.connect(DERIV_WS_URL) as ws:
        await _send_recv(ws, {"authorize": auth_token}, req_id=0)
        out: list[dict[str, Any]] = []
        for i, p in enumerate(payloads, start=1):
            out.append(await _send_recv(ws, p, req_id=i))
        return out
