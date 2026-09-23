#!/usr/bin/env python3
"""Fringe Edge: targeted Kalshi discovery, not a generic market dump."""

import json
import urllib.parse
import urllib.request

API = "https://api.elections.kalshi.com/trade-api/v2"

# Fringe Edge lanes. Add/remove terms here; no code changes needed.
LANES = {
    "WEATHER": ["weather", "temperature", "rain", "snow", "hurricane", "storm", "tornado"],
    "ECON": ["cpi", "inflation", "fed", "rate", "gdp", "jobs", "unemployment", "treasury", "recession"],
    "CRYPTO": ["bitcoin", "btc", "ethereum", "eth", "crypto"],
    "ENERGY": ["oil", "gas", "natural gas", "electricity", "power", "energy"],
    "WORLD": ["war", "ceasefire", "sanction", "tariff", "iran", "russia", "ukraine", "china"],
    "SCI_TECH": ["spacex", "launch", "rocket", "ai", "openai", "nvidia"],
}


def get_json(path, params=None):
    url = f"{API}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "fringe-edge/2.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def get_open_events(max_events=500):
    events, cursor = [], None
    while len(events) < max_events:
        params = {
            "status": "open",
            "limit": min(200, max_events - len(events)),
            "with_nested_markets": "true",
        }
        if cursor:
            params["cursor"] = cursor
        payload = get_json("events", params)
        batch = payload.get("events", [])
        events.extend(batch)
        cursor = payload.get("cursor")
        if not batch or not cursor:
            break
    return events


def lane_for(event, market):
    text = " ".join(str(x or "") for x in [
        event.get("category"), event.get("title"), event.get("sub_title"),
        market.get("title"), market.get("subtitle"), market.get("yes_sub_title"),
    ]).lower()
    hits = []
    for lane, terms in LANES.items():
        if any(term in text for term in terms):
            hits.append(lane)
    return hits


def n(m, key):
    try:
        return float(m.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def useful(m):
    # Exclude multivariate/combo contracts and dead books.
    if str(m.get("ticker", "")).upper().startswith("KXMV"):
        return False
    bid, ask = n(m, "yes_bid_dollars"), n(m, "yes_ask_dollars")
    no_bid, no_ask = n(m, "no_bid_dollars"), n(m, "no_ask_dollars")
    live_book = (0 < bid < 1 and 0 < ask < 1) or (0 < no_bid < 1 and 0 < no_ask < 1)
    activity = max(n(m, "volume_24h_fp"), n(m, "volume_fp"), n(m, "open_interest_fp"))
    return live_book or activity > 0


def main():
    events = get_open_events()
    candidates = []

    for event in events:
        for market in event.get("markets", []):
            lanes = lane_for(event, market)
            if lanes and useful(market):
                candidates.append((lanes, event, market))

    candidates.sort(
        key=lambda x: (
            n(x[2], "volume_24h_fp"),
            n(x[2], "open_interest_fp"),
            n(x[2], "volume_fp"),
        ),
        reverse=True,
    )

    print(f"Open events scanned: {len(events)}")
    print(f"FRINGE candidates: {len(candidates)}")
    print("=" * 88)

    for lanes, event, m in candidates[:75]:
        print(f"\n[{','.join(lanes)}] {m.get('ticker', '-')}")
        print(f"  {event.get('title', m.get('title', '-'))}")
        if m.get("title") and m.get("title") != event.get("title"):
            print(f"  market: {m.get('title')}")
        print(
            f"  YES {m.get('yes_bid_dollars', '-')} / {m.get('yes_ask_dollars', '-')}"
            f" | NO {m.get('no_bid_dollars', '-')} / {m.get('no_ask_dollars', '-')}"
        )
        print(
            f"  vol24h {m.get('volume_24h_fp', '-')}"
            f" | volume {m.get('volume_fp', '-')}"
            f" | OI {m.get('open_interest_fp', '-')}"
        )
        print(f"  closes {m.get('close_time', '-')}")


if __name__ == "__main__":
    main()
