#!/usr/bin/env python3
"""Minimal read-only Kalshi live market pull."""

import json
import urllib.parse
import urllib.request

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"


def get_open_markets(limit=20):
    params = urllib.parse.urlencode({"status": "open", "limit": limit})
    req = urllib.request.Request(
        f"{BASE_URL}?{params}",
        headers={"User-Agent": "fringe-edge/0.1"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response).get("markets", [])


def main():
    markets = get_open_markets()
    print(f"Kalshi open markets returned: {len(markets)}\n")

    for market in markets:
        print(
            f"{market.get('ticker')} | "
            f"YES {market.get('yes_bid_dollars', market.get('yes_bid'))}/"
            f"{market.get('yes_ask_dollars', market.get('yes_ask'))} | "
            f"vol {market.get('volume_fp', market.get('volume'))} | "
            f"{market.get('title')}"
        )


if __name__ == "__main__":
    main()
