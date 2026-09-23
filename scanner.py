#!/usr/bin/env python3
"""Clean, read-only Kalshi market feed."""

import json
import urllib.parse
import urllib.request

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"


def fetch_open_markets(scan_limit=10000):
    markets = []
    cursor = None
    while len(markets) < scan_limit:
        params = {"status": "open", "limit": min(1000, scan_limit - len(markets))}
        if cursor:
            params["cursor"] = cursor
        req = urllib.request.Request(
            BASE_URL + "?" + urllib.parse.urlencode(params),
            headers={"User-Agent": "fringe-edge/0.4"},
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = json.load(response)
        batch = payload.get("markets", [])
        markets.extend(batch)
        cursor = payload.get("cursor")
        if not batch or not cursor:
            break
    return markets


def number(market, *keys):
    for key in keys:
        value = market.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return 0.0


def is_combo(market):
    # KXMV tickers are Kalshi multivariate/combo markets.
    # Do NOT use mve_collection_ticker as a boolean combo flag: it can be
    # populated broadly enough to incorrectly discard ordinary markets.
    ticker = str(market.get("ticker", "")).upper()
    return ticker.startswith("KXMV")


def money(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "-"
    if value > 1:
        value /= 100
    return f"{value:.2f}"


def main():
    raw = fetch_open_markets()
    standalone = [m for m in raw if not is_combo(m)]
    active = [
        m for m in standalone
        if number(m, "volume_fp", "volume") > 0
        or number(m, "open_interest_fp", "open_interest") > 0
    ]
    active.sort(
        key=lambda m: (
            number(m, "volume_fp", "volume"),
            number(m, "open_interest_fp", "open_interest"),
        ),
        reverse=True,
    )

    print(f"Kalshi open markets scanned: {len(raw)}")
    kxmv = sum(1 for m in raw if str(m.get("ticker", "")).upper().startswith("KXMV"))
    print(f"KXMV combo markets removed: {kxmv}")
    print(f"Standalone markets found: {len(standalone)}")
    print(f"Active standalone markets: {len(active)}")
    print("=" * 90)

    for market in active[:50]:
        bid = market.get("yes_bid_dollars", market.get("yes_bid"))
        ask = market.get("yes_ask_dollars", market.get("yes_ask"))
        print(f"\n{market.get('ticker', '-')}")
        print(f"  {market.get('title', '-')}")
        print(
            f"  YES bid {money(bid)} | ask {money(ask)}"
            f" | vol {market.get('volume_fp', market.get('volume', 0))}"
            f" | OI {market.get('open_interest_fp', market.get('open_interest', 0))}"
        )
        print(f"  closes: {market.get('close_time', '-')}")


if __name__ == "__main__":
    main()
