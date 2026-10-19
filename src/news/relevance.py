"""Cheap, transparent topic tagging and relevance scoring for GBP/USD.

Deliberately keyword-based: it only decides what is worth showing the LLM, and which
topics each headline touches. Reading the news and judging direction is the LLM's job.
(?-i:...) makes acronyms case-sensitive so "Fed" does not match "fed up".
"""
from __future__ import annotations

import re

# topic -> (weight, regex)
TOPICS: dict[str, tuple[float, str]] = {
    "gbp_usd_direct": (3.0, r"\b(sterling|pound|GBP|GBP/USD|cable)\b|(?-i:\bpound sterling\b)"),
    "central_banks": (3.0, r"\b(bank of england|bank rate|federal reserve|rate (cut|hike|decision)s?|interest rates?|monetary policy|monetary policy committee)\b|(?-i:\b(BoE|MPC|FOMC|Fed)\b)"),
    "inflation": (2.0, r"\b(inflation|consumer prices?|CPI|PCE|PPI|price pressures?)\b"),
    "labour": (2.0, r"\b(payrolls?|unemployment|jobless|jobs report|labou?r market|wage growth|wages)\b|(?-i:\bNFP\b)"),
    "growth": (1.5, r"\b(GDP|PMI|retail sales|recession|economic growth|economy shrank|economy grew)\b"),
    "uk_fiscal_politics": (2.0, r"\b(gilts?|chancellor|budget|autumn statement|treasury|downing street|uk government|prime minister|OBR)\b"),
    "us_fiscal_politics": (2.0, r"\b(treasury yields?|debt ceiling|government shutdown|tariffs?|white house|congress|trade deal|sanctions)\b"),
    "geopolitics": (2.0, r"\b(war|ceasefire|missiles?|invasion|nato|ukraine|russia|middle east|gaza|israel|iran|taiwan|conflict|escalat\w+)\b"),
    "energy_commodities": (1.0, r"\b(oil|brent|crude|natural gas|opec|energy prices?)\b"),
    "fx_rates_markets": (2.0, r"\b(dollar|currency|currencies|forex|FX|yields?|bond market|DXY)\b"),
    "risk_sentiment": (1.0, r"\b(stocks?|equities|sell-?off|risk-off|safe haven|volatility|VIX|markets? (fall|slump|rally|tumble))\b"),
}
_COMPILED = {k: (w, re.compile(p, re.I)) for k, (w, p) in TOPICS.items()}


def tag_and_score(title: str, summary: str = "") -> tuple[list[str], float]:
    """Return (topics, relevance). A topic hit in the title counts 1.5x; each topic counts once."""
    topics, score = [], 0.0
    for name, (w, rx) in _COMPILED.items():
        in_title = bool(rx.search(title))
        in_body = bool(summary) and bool(rx.search(summary))
        if in_title or in_body:
            topics.append(name)
            score += w * (1.5 if in_title else 1.0)
    return topics, round(score, 2)
