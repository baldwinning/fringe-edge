#!/usr/bin/env python3
"""Clean, read-only Kalshi market feed."""

import json
import urllib.parse
import urllib.request

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"


def fetch_open_markets(page_limit=1000):
    markets = []
    cursor = None

    while len(markets) < page_limit:
        params = {"status": "open", "limit": min(1000, page_limit - len(markets))}
        if cursor:
            params["cursor"] = cursor

        url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "fringe-edge/0.2"})

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
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return 0.0


def is_clean_market(market):
    # Kalshi combo/parlay tickers commonly use generated KXMV... identifiers.
    ticker = str(market.get("ticker", "")).upper()
    if ticker.startswith("KXMV"):
        return False

    bid = number(market, "yes_bid_dollars", "yes_bid")
    ask = number(market, "yes_ask_dollars", "yes_ask")
    volume = number(market, "volume_fp", "volume")
    open_interest = number(market, "open_interest_fp", "open_interest")

    # Require an actual two-sided YES market and some evidence of activity.
    if bid <= 0 or ask <= 0 or ask <= bid:
        return False
    if volume <= 0 and open_interest <= 0:
        return False

    return True


def money(value):
    if value is None:
        return "-"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "-"
    # Dollar fields arrive as decimals; legacy fields may arrive as cents.
    if value > 1:
        value /= 100
    return f"{value:.2f}"


def main():
    raw = fetch_open_markets()
    clean = [m for m in raw if is_clean_market(m)]

    # Most active first so the initial board is useful on mobile.
    clean.sort(
        key=lambda m: (
            number(m, "volume_fp", "volume"),
            number(m, "open_interest_fp", "open_interest"),
        ),
        reverse=True,
    )

    print(f"Kalshi open markets scanned: {len(raw)}")
    print(f"Clean standalone markets: {len(clean)}")
    print("=" * 90)

    for market in clean[:50]:
        bid = market.get("yes_bid_dollars", market.get("yes_bid"))
        ask = market.get("yes_ask_dollars", market.get("yes_ask"))
        spread = None
        try:
            b, a = float(bid), float(ask)
            if b > 1:
                b /= 100
            if a > 1:
                a /= 100
            spread = a - b
        except (TypeError, ValueError):
            pass

        print(f"\n{market.get('ticker', '-')}")
        print(f"  {market.get('title', '-')}")
        print(
            f"  YES {money(bid)} / {money(ask)}"
            f" | spread {money(spread)}"
            f" | vol {market.get('volume_fp', market.get('volume', 0))}"
            f" | OI {market.get('open_interest_fp', market.get('open_interest', 0))}"
        )
        print(f"  closes: {market.get('close_time', '-')}")


if __name__ == "__main__":
    main()
