"""美股板块（免 key，实测 2026-10-21）：Yahoo chart 主源，Nasdaq 财报日历。

Stooq / CBOE CSV / CNN 恐惧贪婪在本环境实测不可用，不使用。
"""
import json
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

INDICES = ["^GSPC", "^IXIC", "^DJI", "^VIX", "^TNX", "DX-Y.NYB"]
SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLC", "XLY", "XLP", "XLB", "XLRE", "XLU"]
MAG7 = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]
CRYPTO_LINKED = ["COIN", "MSTR", "HOOD", "MARA", "RIOT", "CLSK", "IBIT"]


def chart(symbol):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(symbol, safe="") + "?range=5d&interval=1d")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        body = json.loads(r.read().decode())
    result = body["chart"]["result"][0]
    meta = result["meta"]
    closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
    price = meta.get("regularMarketPrice", closes[-1] if closes else None)
    prev = closes[-2] if len(closes) >= 2 else None
    return {
        "symbol": symbol,
        "price": price,
        "change_1d_pct": round((price / prev - 1) * 100, 2) if price and prev else None,
        "change_5d_pct": round((closes[-1] / closes[0] - 1) * 100, 2) if len(closes) >= 2 else None,
    }


def board():
    out = {}
    for name, symbols in [("indices", INDICES), ("sectors", SECTORS), ("mag7", MAG7), ("crypto_linked", CRYPTO_LINKED)]:
        rows = []
        for s in symbols:
            try:
                rows.append(chart(s))
            except Exception as e:
                rows.append({"symbol": s, "error": str(e)[:80]})
        out[name] = rows
    return out


def earnings_today(limit=8):
    today_et = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    url = f"https://api.nasdaq.com/api/calendar/earnings?date={today_et}"
    req = urllib.request.Request(url, headers={**UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        body = json.loads(r.read().decode())
    rows = (body.get("data") or {}).get("rows") or []
    return [{"symbol": x["symbol"], "name": x["name"], "time": x["time"],
             "eps_forecast": x.get("epsForecast")} for x in rows[:limit]]
