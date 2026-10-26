#!/usr/bin/env python3
"""Bitget 合约观测器 - 公开接口探针（免 key，仅行情读取，不下单）

用法: python3 bitget_probe.py [SYMBOL]   例: python3 bitget_probe.py ZECUSDT
验证日期: 2026-10-21，全部端点实测返回 code=00000。
"""
import json
import sys
import urllib.request

BASE = "https://api.bitget.com/api/v2/mix/market"
PT = "productType=USDT-FUTURES"


def get(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "bitget-observer/0.1"})
    with urllib.request.urlopen(req, timeout=15) as r:
        body = json.loads(r.read().decode())
    if body.get("code") != "00000":
        raise RuntimeError(f"{path} -> {body.get('code')} {body.get('msg')}")
    return body["data"]


def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "ZECUSDT"
    out = {"symbol": symbol}

    t = get(f"/ticker?symbol={symbol}&{PT}")[0]
    out["ticker"] = {
        "last": t["lastPr"], "bid": t["bidPr"], "ask": t["askPr"],
        "mark": t["markPrice"], "index": t["indexPrice"],
        "change24h_pct": round(float(t["change24h"]) * 100, 2),
        "quote_volume_24h": round(float(t["quoteVolume"])),
        "funding_rate": t["fundingRate"], "open_interest_size": t["holdingAmount"],
    }

    depth = get(f"/merge-depth?symbol={symbol}&{PT}&precision=scale0")
    # 实测 Bitget 返回顺序不稳定，统一排序：买盘降序、卖盘升序，[0] 为最优档
    bids = sorted(([float(p), float(s)] for p, s in depth["bids"]), reverse=True)
    asks = sorted(([float(p), float(s)] for p, s in depth["asks"]))
    spread = asks[0][0] - bids[0][0]
    bid_usd_1pct = sum(p * s for p, s in bids if p >= bids[0][0] * 0.99)
    ask_usd_1pct = sum(p * s for p, s in asks if p <= asks[0][0] * 1.01)
    out["orderbook_top5"] = {"bids": bids[:5], "asks": asks[:5]}
    out["orderbook_stats"] = {
        "spread": round(spread, 4),
        "bid_depth_within_1pct_usd": round(bid_usd_1pct),
        "ask_depth_within_1pct_usd": round(ask_usd_1pct),
        "imbalance_1pct": round((bid_usd_1pct - ask_usd_1pct) / max(bid_usd_1pct + ask_usd_1pct, 1), 3),
    }

    fr = get(f"/current-fund-rate?symbol={symbol}&{PT}")[0]
    out["funding"] = {"rate": fr["fundingRate"], "interval_h": fr["fundingRateInterval"]}

    ls = get(f"/long-short?symbol={symbol}&{PT}&period=1h")
    if ls:
        out["position_long_short_ratio"] = ls[-1]["longShortRatio"]
    als = get(f"/account-long-short?symbol={symbol}&{PT}")
    if als:
        out["account_long_short_ratio"] = als[-1]["longShortAccountRatio"]

    candles = get(f"/candles?symbol={symbol}&{PT}&granularity=15m&limit=20")
    closes = [float(c[4]) for c in candles]
    if len(closes) >= 2:
        out["momentum_15m_x20_pct"] = round((closes[-1] / closes[0] - 1) * 100, 2)

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
