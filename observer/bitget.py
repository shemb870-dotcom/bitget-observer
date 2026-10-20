"""Bitget v2 合约公开接口（免 key）。实测 2026-10-21。

坑：merge-depth 的 precision 必须传 scale0/scale1/scale2；深度数组顺序不稳定，必须自排序。
"""
import json
import urllib.request

BASE = "https://api.bitget.com/api/v2/mix/market"
PT = "productType=USDT-FUTURES"
UA = {"User-Agent": "bitget-observer/1.0"}


def get(path):
    req = urllib.request.Request(BASE + path, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        body = json.loads(r.read().decode())
    if body.get("code") != "00000":
        raise RuntimeError(f"{path} -> {body.get('code')} {body.get('msg')}")
    return body["data"]


def all_tickers():
    return get(f"/tickers?{PT}")


def top_symbols(core, extra_n):
    tickers = all_tickers()
    ranked = sorted(tickers, key=lambda x: -float(x["quoteVolume"]))
    out = list(core)
    for t in ranked:
        if len(out) >= len(core) + extra_n:
            break
        if t["symbol"] not in out:
            out.append(t["symbol"])
    return out


def _try(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def snapshot(symbol):
    t = get(f"/ticker?symbol={symbol}&{PT}")[0]
    # 深度/多空比对部分合约（股票类永续）会返回 400，降级为无盘口而不是整只失败
    depth = _try(lambda: get(f"/merge-depth?symbol={symbol}&{PT}&precision=scale0"), {"bids": [], "asks": []})
    bids = sorted(([float(p), float(s)] for p, s in depth["bids"]), reverse=True)
    asks = sorted(([float(p), float(s)] for p, s in depth["asks"]))
    bid_usd = sum(p * s for p, s in bids if p >= bids[0][0] * 0.99) if bids else 0.0
    ask_usd = sum(p * s for p, s in asks if p <= asks[0][0] * 1.01) if asks else 0.0
    total = bid_usd + ask_usd
    candles = get(f"/candles?symbol={symbol}&{PT}&granularity=15m&limit=6")
    closes = [float(c[4]) for c in candles]
    mom_15m = (closes[-1] / closes[-2] - 1) * 100 if len(closes) >= 2 else 0.0
    mom_1h = (closes[-1] / closes[0] - 1) * 100 if len(closes) >= 2 else 0.0
    ls = _try(lambda: get(f"/long-short?symbol={symbol}&{PT}&period=1h"), [])
    return {
        "symbol": symbol,
        "price": float(t["lastPr"]),
        "change24h_pct": round(float(t["change24h"]) * 100, 2),
        "quote_volume_24h": float(t["quoteVolume"]),
        "funding_rate": float(t["fundingRate"]),
        "open_interest": float(t["holdingAmount"]),
        "spread": round(asks[0][0] - bids[0][0], 6) if bids and asks else None,
        "bid_depth_1pct_usd": round(bid_usd),
        "ask_depth_1pct_usd": round(ask_usd),
        "imbalance_1pct": round((bid_usd - ask_usd) / total, 3) if total > 0 else 0.0,
        "top_bids": bids[:5],
        "top_asks": asks[:5],
        "mom_15m_pct": round(mom_15m, 2),
        "mom_1h_pct": round(mom_1h, 2),
        "ls_ratio": float(ls[-1]["longShortRatio"]) if ls else None,
    }
