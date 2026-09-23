#!/usr/bin/env python3
"""Read-only targeted Polymarket feed for Fringe Edge."""

import json
import urllib.parse
import urllib.request

GAMMA = "https://gamma-api.polymarket.com/events"

LANES = {
    "WEATHER": ["weather", "temperature", "rain", "snow", "hurricane", "storm", "tornado"],
    "ECON": ["cpi", "inflation", "fed", "fomc", "interest rate", "gdp", "jobs", "unemployment", "treasury", "recession"],
    "CRYPTO": ["bitcoin", "btc", "ethereum", "eth", "crypto"],
    "ENERGY": ["oil", "gas", "natural gas", "electricity", "power", "energy"],
    "WORLD": ["war", "ceasefire", "sanction", "tariff", "iran", "russia", "ukraine", "china"],
    "SCI_TECH": ["spacex", "launch", "rocket", "ai", "openai", "nvidia"],
    "SPORTS": ["nfl", "nba", "mlb", "nhl", "wnba", "ncaa", "football", "basketball", "baseball", "hockey", "tennis", "golf", "soccer"],
}


def get_events(limit=500):
    params = urllib.parse.urlencode({
        "active": "true",
        "closed": "false",
        "order": "volume_24hr",
        "ascending": "false",
        "limit": limit,
        "offset": 0,
    })
    req = urllib.request.Request(
        GAMMA + "?" + params,
        headers={"User-Agent": "fringe-edge/2.0"},
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def parse_json_field(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    return []


def lanes_for(event, market):
    tags = event.get("tags") or []
    tag_text = " ".join(
        str(t.get("label") or t.get("slug") or "") if isinstance(t, dict) else str(t)
        for t in tags
    )
    text = " ".join([
        str(event.get("title") or ""),
        str(event.get("description") or ""),
        tag_text,
        str(market.get("question") or ""),
        str(market.get("groupItemTitle") or ""),
    ]).lower()
    return [lane for lane, terms in LANES.items() if any(term in text for term in terms)]


def n(obj, *keys):
    for key in keys:
        try:
            v = obj.get(key)
            if v not in (None, ""):
                return float(v)
        except (TypeError, ValueError):
            pass
    return 0.0


def main():
    events = get_events()
    candidates = []

    for event in events:
        for market in event.get("markets", []):
            lanes = lanes_for(event, market)
            if not lanes:
                continue
            if not market.get("active", True) or market.get("closed", False):
                continue
            if not market.get("enableOrderBook", True):
                continue
            prices = parse_json_field(market.get("outcomePrices"))
            tokens = parse_json_field(market.get("clobTokenIds"))
            if len(prices) < 2 or len(tokens) < 2:
                continue
            candidates.append((lanes, event, market, prices))

    candidates.sort(
        key=lambda x: (
            n(x[2], "volume24hr"),
            n(x[2], "liquidityNum", "liquidity"),
            n(x[2], "volumeNum", "volume"),
        ),
        reverse=True,
    )

    print(f"Polymarket active events scanned: {len(events)}")
    print(f"FRINGE candidates: {len(candidates)}")
    print("=" * 88)

    for lanes, event, market, prices in candidates[:75]:
        print(f"\n[{','.join(lanes)}] {market.get('slug', market.get('id', '-'))}")
        print(f"  {event.get('title', '-')}")
        print(f"  market: {market.get('question', '-')}")
        print(
            f"  YES {prices[0]} | NO {prices[1]}"
            f" | bestBid {market.get('bestBid', '-')}"
            f" | bestAsk {market.get('bestAsk', '-')}"
            f" | spread {market.get('spread', '-')}"
        )
        print(
            f"  vol24h {market.get('volume24hr', '-')}"
            f" | volume {market.get('volumeNum', market.get('volume', '-'))}"
            f" | liquidity {market.get('liquidityNum', market.get('liquidity', '-'))}"
        )
        print(f"  ends {market.get('endDate', event.get('endDate', '-'))}")


if __name__ == "__main__":
    main()
