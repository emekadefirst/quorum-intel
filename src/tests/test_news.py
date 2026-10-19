import functools
import http.server
import threading
from datetime import datetime, timezone

import pytest
from quant_layer.news.digest import build_news_digest
from quant_layer.news.fetch import parse_feed
from quant_layer.news.relevance import tag_and_score

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>BoE holds rates as inflation cools</title><link>{base}/a1.html</link>
<pubDate>Mon, 19 Oct 2026 08:30:00 GMT</pubDate>
<description><![CDATA[<p>The <b>Bank of England</b> kept Bank Rate unchanged.</p>]]></description></item>
<item><title>Oil jumps on Middle East tensions</title><link>{base}/a2.html</link>
<pubDate>Mon, 19 Oct 2026 07:10:00 GMT</pubDate><description>Brent rose 3%</description></item>
<item><title>Local bake sale raises funds</title><link>{base}/a3.html</link>
<pubDate>Mon, 19 Oct 2026 07:00:00 GMT</pubDate><description>Cakes.</description></item>
<item><title>Old story about sterling</title><link>{base}/a4.html</link>
<pubDate>Mon, 12 Oct 2026 07:00:00 GMT</pubDate><description>Stale.</description></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Fed signals patience on rate cuts</title><link rel="alternate" href="https://x.test/fed"/>
<updated>2026-10-19T10:00:00Z</updated><summary>FOMC minutes</summary></entry></feed>"""

ARTICLE = b"""<html><body><nav>menu</nav><article>
<p>The MPC voted seven to two to hold Bank Rate, citing sticky services inflation across the economy.</p>
<p>Governor remarks suggested policy would stay restrictive for longer than markets had priced in.</p>
<p>Sterling edged higher against the dollar after the decision was announced on Monday morning.</p>
</article></body></html>"""


@pytest.fixture()
def site(tmp_path):
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(tmp_path)
    )
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    handler.func.log_message = lambda *a, **k: None
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    (tmp_path / "feed.xml").write_bytes(RSS.replace(b"{base}", base.encode()))
    (tmp_path / "a1.html").write_bytes(ARTICLE)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield base, tmp_path
    srv.shutdown()


def test_parse_rss_strips_html_and_dates():
    items = parse_feed(RSS.replace(b"{base}", b"http://h"), "T", "news")
    assert len(items) == 4
    assert items[0].summary == "The Bank of England kept Bank Rate unchanged."
    assert items[0].published.tzinfo is not None


def test_parse_atom():
    (it,) = parse_feed(ATOM, "Fed", "central_bank")
    assert it.url == "https://x.test/fed" and it.published.hour == 10


def test_malformed_and_entity_bombs_rejected():
    with pytest.raises(Exception):
        parse_feed(b"<rss><item>", "T", "news")
    bomb = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;">]><rss><channel><item><title>&b;</title><link>u</link></item></channel></rss>'
    with pytest.raises(Exception):
        parse_feed(bomb, "T", "news")


def test_relevance_case_sensitive_acronyms():
    assert "central_banks" in tag_and_score("Fed holds rates steady")[0]
    assert "central_banks" not in tag_and_score("Kids were fed up with the queue")[0]
    topics, score = tag_and_score("Sterling slides as BoE cuts Bank Rate")
    assert {"gbp_usd_direct", "central_banks"} <= set(topics) and score >= 9


def test_digest_end_to_end_with_scrapling(site):
    base, _ = site
    d = build_news_digest(
        sources=[
            {"name": "Local", "url": f"{base}/feed.xml", "category": "news"},
            {"name": "Dead", "url": "http://127.0.0.1:9/feed.xml", "category": "news"},
        ],
        now=NOW,
        lookback_hours=48,
    )
    assert d["meta"]["sources_ok"] == 1 and d["meta"]["sources_total"] == 2
    titles = [i["title"] for i in d["items"]]
    assert titles[0].startswith("BoE holds")  # highest priority first
    assert "Oil jumps on Middle East tensions" in titles
    assert not any("bake sale" in t for t in titles)  # irrelevant filtered
    assert not any("Old story" in t for t in titles)  # outside lookback
    dead = next(h for h in d["source_health"] if h["name"] == "Dead")
    assert dead["ok"] is False and dead["error"]


def test_article_excerpt_and_robots(site):
    base, root = site
    src = [{"name": "Local", "url": f"{base}/feed.xml", "category": "news"}]
    d = build_news_digest(sources=src, now=NOW, article_excerpts=2)
    first = d["items"][0]
    assert first["article_status"] == "ok" and "Bank Rate" in first["article_excerpt"]
    # now forbid crawling: excerpt must be skipped
    (root / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    d2 = build_news_digest(sources=src, now=NOW, article_excerpts=1)
    assert d2["items"][0]["article_status"].startswith("blocked")


def test_dedupe_same_story_two_sources():
    from quant_layer.news.digest import _dedupe

    a = {
        "title": "BoE holds rates as inflation cools",
        "url": "http://a/1",
        "source": "A",
        "_final": 5,
    }
    b = {
        "title": "BoE holds rates as inflation cools sharply",
        "url": "http://b/9",
        "source": "B",
        "_final": 4,
    }
    out = _dedupe([a, b])
    assert len(out) == 1 and out[0]["also_reported_by"] == ["B"]
