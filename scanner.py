#!/usr/bin/env python3
"""Minimal read-only Kalshi feed using documented API filters."""

import json
import urllib.parse
import urllib.request

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"


def get_markets(limit=1000):
    # Kalshi documents mve_filter=exclude specifically for excluding
    # multivariate/combo markets. Let the API do the filtering.
    params = urllib.parse.urlencode({
        "status": "open",
        "mve_filter": "exclude",
        "limit": limit,
    })
    req = urllib.request.Request(
        f"{BASE_URL}?{params}",
        headers={"User-Agent": "fringe-edge/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response).get("markets", [])


def main():
    markets = get_markets()

    # Keep discovery native to Kalshi; only rank/filter for tradability here.
    def n(m, key):
        try:
            return float(m.get(key) or 0)
        except (TypeError, ValueError):
            return 0.0

    def tradable(m):
        yb = n(m, "yes_bid_dollars")
        ya = n(m, "yes_ask_dollars")
        nb = n(m, "no_bid_dollars")
        na = n(m, "no_ask_dollars")
        activity = max(n(m, "volume_24h_fp"), n(m, "volume_fp"), n(m, "open_interest_fp"))
        sane_yes = 0 < yb < 1 and 0 < ya < 1 and yb <= ya
        sane_no = 0 < nb < 1 and 0 < na < 1 and nb <= na
        return activity > 0 and (sane_yes or sane_no)

    tradable_markets = [m for m in markets if tradable(m)]
    tradable_markets.sort(
        key=lambda m: (
            n(m, "volume_24h_fp"),
            n(m, "open_interest_fp"),
            n(m, "volume_fp"),
        ),
        reverse=True,
    )

    print(f"Kalshi open non-MVE markets returned: {len(markets)}")
    print(f"Tradable active markets: {len(tradable_markets)}")
    print("=" * 88)

    for m in tradable_markets[:50]:
        print(f"\n{m.get('ticker', '-')}")
        print(f"  {m.get('title', '-')}")
        print(
            f"  YES {m.get('yes_bid_dollars', '-')} / {m.get('yes_ask_dollars', '-')}"
            f" | NO {m.get('no_bid_dollars', '-')} / {m.get('no_ask_dollars', '-')}"
        )
        print(
            f"  vol24h {m.get('volume_24h_fp', '-')}"
            f" | volume {m.get('volume_fp', '-')}"
            f" | OI {m.get('open_interest_fp', '-')}"
        )
        print(
            f"  event {m.get('event_ticker', '-')}"
            f" | closes {m.get('close_time', '-')}"
        )


if __name__ == "__main__":
    main()
