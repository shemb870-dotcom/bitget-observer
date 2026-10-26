#!/usr/bin/env python3
"""美股板块探针 - Yahoo Finance chart 接口（免 key，需 UA 头），仅行情读取。

用法: python3 us_probe.py [SYMBOL ...]   不带参数则跑默认观察清单。
验证日期: 2026-10-21。Stooq 与 CBOE CSV 在本机环境返回空/HTML，不用。
"""
import json
import sys
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

WATCHLIST = {
    "indices": ["^GSPC", "^IXIC", "^DJI", "^VIX", "^TNX", "DX-Y.NYB"],
    "sectors_spdr": ["XLK", "XLF", "XLE", "XLV", "XLI", "XLC", "XLY", "XLP", "XLB", "XLRE", "XLU"],
    "mag7": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"],
    "crypto_linked": ["COIN", "MSTR", "HOOD", "MARA", "RIOT", "CLSK", "IBIT"],
}


def chart(symbol):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol, safe="") + "?range=5d&interval=1d"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        body = json.loads(r.read().decode())
    result = body["chart"]["result"][0]
    meta = result["meta"]
    closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
    price = meta.get("regularMarketPrice", closes[-1] if closes else None)
    prev = closes[-2] if len(closes) >= 2 else meta.get("chartPreviousClose")
    chg = round((price / prev - 1) * 100, 2) if price and prev else None
    chg5 = round((closes[-1] / closes[0] - 1) * 100, 2) if len(closes) >= 2 else None
    return {"symbol": symbol, "price": price, "change_1d_pct": chg, "change_5d_pct": chg5}


def main():
    if len(sys.argv) > 1:
        groups = {"custom": sys.argv[1:]}
    else:
        groups = WATCHLIST
    out = {}
    for name, symbols in groups.items():
        rows = []
        for s in symbols:
            try:
                rows.append(chart(s))
            except Exception as e:
                rows.append({"symbol": s, "error": str(e)[:80]})
        out[name] = rows
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
