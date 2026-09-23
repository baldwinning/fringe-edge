#!/usr/bin/env python3
"""Read-only targeted Polymarket feed for Fringe Edge."""

import json
import urllib.parse
import urllib.request

GAMMA = "https://gamma-api.polymarket.com/events"
CLOB = "https://clob.polymarket.com"

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


def clob_book(token_id):
    """Public CLOB order book for one outcome token."""
    try:
        req = urllib.request.Request(
            CLOB + "/book?" + urllib.parse.urlencode({"token_id": token_id}),
            headers={"User-Agent": "fringe-edge/2.1"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            book = json.load(r)
        bids = book.get("bids") or []
        asks = book.get("asks") or []
        best_bid = max((float(x["price"]) for x in bids), default=None)
        best_ask = min((float(x["price"]) for x in asks), default=None)
        return best_bid, best_ask
    except Exception:
        return None, None


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
        tokens = parse_json_field(market.get("clobTokenIds"))
        yes_bid, yes_ask = clob_book(tokens[0]) if tokens else (None, None)
        no_bid, no_ask = clob_book(tokens[1]) if len(tokens) > 1 else (None, None)
        print(f"\n[{','.join(lanes)}] {market.get('slug', market.get('id', '-'))}")
        print(f"  {event.get('title', '-')}")
        print(f"  market: {market.get('question', '-')}")
        print(
            f"  CLOB YES {yes_bid if yes_bid is not None else '-'} / {yes_ask if yes_ask is not None else '-'}"
            f" | NO {no_bid if no_bid is not None else '-'} / {no_ask if no_ask is not None else '-'}"
        )
        print(
            f"  displayed YES {prices[0]} | NO {prices[1]}"
            f" | Gamma spread {market.get('spread', '-')}"
        )
        print(
            f"  vol24h {market.get('volume24hr', '-')}"
            f" | volume {market.get('volumeNum', market.get('volume', '-'))}"
            f" | liquidity {market.get('liquidityNum', market.get('liquidity', '-'))}"
        )
        print(f"  ends {market.get('endDate', event.get('endDate', '-'))}")


if __name__ == "__main__":
    main()
