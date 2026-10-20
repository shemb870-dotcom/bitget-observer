"""链上免费源（免 key，实测 2026-10-21）。注意：ZEC 为屏蔽链，数据仅含透明池。"""
import json
import urllib.request

UA = {"User-Agent": "bitget-observer/1.0"}


def _get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def blockchair(chain):
    d = _get(f"https://api.blockchair.com/{chain}/stats")["data"]
    return {
        "chain": chain,
        "txs_24h": d.get("transactions_24h"),
        "volume_24h_native": d.get("volume_24h"),
        "mempool_txs": d.get("mempool_transactions"),
    }


def fear_greed():
    d = _get("https://api.alternative.me/fng/?limit=1")["data"][0]
    return {"value": int(d["value"]), "label": d["value_classification"]}


def stablecoin_supply_usd():
    rows = _get("https://stablecoins.llama.fi/stablecoincharts/all")
    if not rows:
        return None
    total = rows[-1]["totalCirculatingUSD"]
    return sum(v for v in total.values() if isinstance(v, (int, float)))


def collect():
    out = {}
    for name, fn in [("btc_chain", lambda: blockchair("bitcoin")),
                     ("zec_chain_transparent_only", lambda: blockchair("zcash")),
                     ("fear_greed", fear_greed),
                     ("stablecoin_supply_usd", stablecoin_supply_usd)]:
        try:
            out[name] = fn()
        except Exception as e:
            out[name] = {"error": str(e)[:100]}
    return out
