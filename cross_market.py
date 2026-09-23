#!/usr/bin/env python3
"""Conservative Kalshi ↔ Polymarket disagreement detector."""

import json, re, urllib.parse, urllib.request
from difflib import SequenceMatcher

KALSHI="https://api.elections.kalshi.com/trade-api/v2"
GAMMA="https://gamma-api.polymarket.com/events"
CLOB="https://clob.polymarket.com"
STOP={"will","the","a","an","be","is","are","to","of","in","on","for","and","or","by","before","after","at","any","next"}

def get(url,params=None):
    if params: url+="?"+urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"fringe-edge/3.0"}),timeout=25) as r:return json.load(r)

def arr(v):
    if isinstance(v,list):return v
    try:return json.loads(v) if isinstance(v,str) else []
    except:return []

def norm(s):
    return " ".join(re.findall(r"[a-z0-9]+",str(s).lower()))

def tokens(s):
    return {x for x in norm(s).split() if len(x)>2 and x not in STOP}

def sim(a,b):
    A,B=tokens(a),tokens(b)
    jac=len(A&B)/len(A|B) if A|B else 0
    seq=SequenceMatcher(None,norm(a),norm(b)).ratio()
    return max(jac,seq*.85),len(A&B)

def k_markets(limit=500):
    out=[];cur=None
    while len(out)<limit:
        p={"status":"open","limit":min(200,limit-len(out)),"with_nested_markets":"true"}
        if cur:p["cursor"]=cur
        d=get(KALSHI+"/events",p)
        for e in d.get("events",[]):
            for m in e.get("markets",[]):
                if str(m.get("ticker","")).startswith("KXMV"):continue
                q=m.get("title") or e.get("title") or ""
                try: bid=float(m.get("yes_bid_dollars") or 0); ask=float(m.get("yes_ask_dollars") or 0)
                except:continue
                if 0<bid<1 and 0<ask<1:out.append({"q":q,"event":e.get("title",""),"ticker":m.get("ticker"),"bid":bid,"ask":ask,"close":m.get("close_time")})
        cur=d.get("cursor")
        if not cur:break
    return out

def p_markets(limit=500):
    out=[]
    for e in get(GAMMA,{"active":"true","closed":"false","limit":limit,"offset":0}):
        for m in e.get("markets",[]):
            ids=arr(m.get("clobTokenIds"))
            if len(ids)<2:continue
            out.append({"q":m.get("question",""),"event":e.get("title",""),"slug":m.get("slug"),"yes":ids[0],"end":m.get("endDate") or e.get("endDate")})
    return out

def book(token):
    try:
        d=get(CLOB+"/book",{"token_id":token})
        bids=[float(x["price"]) for x in d.get("bids",[])]; asks=[float(x["price"]) for x in d.get("asks",[])]
        return (max(bids) if bids else None,min(asks) if asks else None)
    except:return None,None

def main():
    ks=k_markets(); ps=p_markets()
    matches=[]
    for k in ks:
        best=None
        for p in ps:
            score,common=sim(k["q"]+" "+k["event"],p["q"]+" "+p["event"])
            if common<3 or score<0.55:continue
            if best is None or score>best[0]:best=(score,p)
        if not best:continue
        score,p=best
        pb,pa=book(p["yes"])
        if pb is None or pa is None:continue
        pm=(pb+pa)/2
        gap=abs(km-pm)
        # Conservative alert threshold: large enough to matter, but still requires manual rule verification.
        if gap>=0.05:matches.append((gap,score,k,p,pb,pa))
    matches.sort(reverse=True,key=lambda x:x[0])
    print(f"Kalshi markets checked: {len(ks)} | Polymarket markets checked: {len(ps)}")
    print(f"CROSS-MARKET WATCHES >= 5 points: {len(matches)}")
    print("IMPORTANT: WATCH only until settlement wording/deadlines are verified identical.")
    print("="*88)
    for gap,score,k,p,pb,pa in matches[:30]:
        print(f"\nWATCH gap {gap*100:.1f} pts | match confidence {score:.2f}")
        print(f"  Kalshi {k['ticker']}: {k['q']}")
        print(f"    YES {k['bid']:.3f} / {k['ask']:.3f} | closes {k['close']}")
        print(f"  Polymarket {p['slug']}: {p['q']}")
        print(f"    YES {pb:.3f} / {pa:.3f} | ends {p['end']}")
        print("  STATUS: wording/rules verification required before any edge claim")

if __name__=="__main__":main()
