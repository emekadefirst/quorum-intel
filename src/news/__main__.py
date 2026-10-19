"""CLI: python -m quant_layer.news --hours 48 --excerpts 3 --out news.json"""

import argparse
import json

from .digest import build_news_digest, load_sources


def main():
    p = argparse.ArgumentParser(
        description="Fetch and score GBP/USD-relevant news with Scrapling"
    )
    p.add_argument(
        "--sources", default=None, help="path to a sources.json (default: bundled)"
    )
    p.add_argument("--hours", type=float, default=48)
    p.add_argument("--max-items", type=int, default=25)
    p.add_argument("--min-score", type=float, default=2.0)
    p.add_argument(
        "--excerpts",
        type=int,
        default=0,
        help="fetch article text for top N items (robots.txt respected)",
    )
    p.add_argument("--out", default=None)
    a = p.parse_args()
    d = build_news_digest(
        sources=load_sources(a.sources),
        lookback_hours=a.hours,
        max_items=a.max_items,
        min_score=a.min_score,
        article_excerpts=a.excerpts,
    )
    js = json.dumps(d, indent=2)
    if a.out:
        open(a.out, "w").write(js)
        print(
            f"wrote {a.out}  ({d['meta']['sources_ok']}/{d['meta']['sources_total']} sources ok, "
            f"{d['meta']['relevant_items_returned']} items)"
        )
    else:
        print(js)


if __name__ == "__main__":
    main()
