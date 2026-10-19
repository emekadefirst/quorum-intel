"""Fetching with Scrapling.

Scrapling's AsyncFetcher does the HTTP work (browser-like TLS/headers, retries, timeouts,
SSRF-safe redirects). Feeds are parsed from the raw bytes with defusedxml, because RSS
<link> elements are unreliable under an HTML parser. Article text is extracted with
Scrapling's CSS selectors.

Politeness: feeds are meant for machines. Article pages are only fetched when the site's
robots.txt allows it, with a minimum delay per domain.
"""

from __future__ import annotations

import asyncio
import email.utils
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib import robotparser
from urllib.parse import urlparse

from defusedxml import ElementTree as ET
from scrapling.fetchers import AsyncFetcher
from scrapling.parser import Selector

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
USER_AGENT_NOTE = "quant_layer-news/0.1"


@dataclass
class RawItem:
    source: str
    category: str
    title: str
    url: str
    published: datetime | None
    summary: str


def clean_text(s: str | None, limit: int | None = None) -> str:
    s = _CTRL.sub(" ", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit].rstrip() if limit else s


def html_to_text(fragment: str | None) -> str:
    if not fragment:
        return ""
    try:
        return clean_text(
            Selector(f"<div>{fragment}</div>").get_all_text(separator=" ", strip=True)
        )
    except Exception:  # noqa: BLE001
        return clean_text(re.sub(r"<[^>]+>", " ", fragment))


def parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    try:
        dt = email.utils.parsedate_to_datetime(s)  # RFC 822 (RSS)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))  # ISO 8601 (Atom)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(el, *names: str) -> str:
    for c in el:
        if _local(c.tag) in names and (c.text or "").strip():
            return c.text.strip()
    return ""


def parse_feed(body: bytes, source: str, category: str) -> list[RawItem]:
    """Parse RSS 2.0 or Atom bytes into RawItems. Raises on malformed XML."""
    root = ET.fromstring(body)
    items: list[RawItem] = []
    for el in root.iter():
        kind = _local(el.tag)
        if kind not in ("item", "entry"):
            continue
        title = clean_text(_child_text(el, "title"), 300)
        url = _child_text(el, "link") if kind == "item" else ""
        if kind == "entry" or not url:
            for c in el:  # Atom: <link href="..."/>
                if (
                    _local(c.tag) == "link"
                    and c.get("href")
                    and c.get("rel", "alternate") == "alternate"
                ):
                    url = c.get("href")
                    break
        if not title or not url:
            continue
        date = parse_date(_child_text(el, "pubDate", "published", "updated", "date"))
        summary = html_to_text(_child_text(el, "description", "summary", "content"))
        items.append(
            RawItem(
                source, category, title, url.strip(), date, clean_text(summary, 600)
            )
        )
    return items


async def fetch_feed(
    src: dict, sem: asyncio.Semaphore, timeout: int = 15, retries: int = 2
):
    """Return (items, health). Never raises: a dead source must not kill the digest."""
    t0 = time.monotonic()
    health = {
        "name": src["name"],
        "url": src["url"],
        "ok": False,
        "status": None,
        "n_items": 0,
        "error": None,
    }
    try:
        async with sem:
            page = await AsyncFetcher.get(src["url"], timeout=timeout, retries=retries)
        health["status"] = int(page.status)
        if page.status != 200:
            raise RuntimeError(f"HTTP {page.status}")
        items = parse_feed(bytes(page.body), src["name"], src.get("category", "news"))
        health.update(ok=True, n_items=len(items))
        return items, health | {"seconds": round(time.monotonic() - t0, 2)}
    except Exception as e:  # noqa: BLE001
        health["error"] = f"{type(e).__name__}: {str(e)[:160]}"
        return [], health | {"seconds": round(time.monotonic() - t0, 2)}


class Politeness:
    """robots.txt check (cached per host) plus a minimum delay between hits to one host."""

    def __init__(self, min_delay: float = 1.0):
        self.min_delay = min_delay
        self._robots: dict[str, robotparser.RobotFileParser | None] = {}
        self._last: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def allowed(self, url: str) -> bool:
        u = urlparse(url)
        host = f"{u.scheme}://{u.netloc}"
        if host not in self._robots:
            rp = robotparser.RobotFileParser()
            try:
                page = await AsyncFetcher.get(
                    f"{host}/robots.txt", timeout=10, retries=1
                )
                if page.status == 200:
                    rp.parse(bytes(page.body).decode("utf-8", "ignore").splitlines())
                    self._robots[host] = rp
                elif page.status in (401, 403):
                    self._robots[host] = None  # treat as disallow-all
                else:
                    rp.parse([])  # no robots.txt: allow
                    self._robots[host] = rp
            except Exception:  # noqa: BLE001
                self._robots[host] = None  # cannot verify -> do not fetch
        rp = self._robots[host]
        return bool(rp and rp.can_fetch("*", url))

    async def wait(self, url: str):
        host = urlparse(url).netloc
        async with self._lock:
            gap = self._last.get(host, 0) + self.min_delay - time.monotonic()
            self._last[host] = time.monotonic() + max(gap, 0)
        if gap > 0:
            await asyncio.sleep(gap)


async def fetch_article_excerpt(
    url: str, polite: Politeness, limit: int = 1500
) -> dict:
    """Best-effort main text. Returns {"status": ..., "excerpt": ...}."""
    try:
        if not await polite.allowed(url):
            return {"status": "blocked_by_robots_or_unverifiable", "excerpt": ""}
        await polite.wait(url)
        page = await AsyncFetcher.get(url, timeout=20, retries=1)
        if page.status != 200:
            return {"status": f"http_{page.status}", "excerpt": ""}
        paras: list[str] = []
        for sel in (
            "article p",
            "main p",
            "[role=main] p",
            "p",
        ):  # most specific container first
            paras = [
                clean_text(n.get_all_text(separator=" ", strip=True))
                for n in page.css(sel)
            ]
            paras = [p for p in paras if len(p) > 40]
            if len(" ".join(paras)) > 300:
                break
        text = clean_text(" ".join(paras), limit)
        return {"status": "ok" if text else "no_text_found", "excerpt": text}
    except Exception as e:  # noqa: BLE001
        return {"status": f"error:{type(e).__name__}", "excerpt": ""}
