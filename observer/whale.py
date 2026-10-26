"""巨鲸追踪（免 key，零费用）。

数据源：
- Blockchair BTC/ZEC 最近 100 笔交易，按阈值筛大额（主源；430 限速时自动降级跳过）。
- mempool.space BTC 实时补充：最新内存池 + 最新区块第一页（免 key）。

方向分类（参考 dominique1993/Crypto-Whale-Tracker 与 openclaw skill 的四分类法）：
- exchange_to_exchange / exchange_to_unknown / unknown_to_exchange / unknown_to_unknown。
- 当前版本未内置交易所地址标签包，所有方向暂记为 unknown_to_unknown（诚实标注，
  不猜测）；标签包可后续以外挂 JSON 形式接入，不改代码结构。

边界：只报测量值（交易哈希、金额、时间），不做涨跌预测；ZEC 仅透明池，报告中必须标注。
"""

import json
import urllib.request

UA = {"User-Agent": "bitget-observer/1.0"}

# 大额阈值（原生币单位）
BTC_MIN = 100.0
ZEC_MIN = 1000.0


def _get_json(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _get_text(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode().strip()


def blockchair_large(chain, min_native, limit=100):
    """Blockchair 最近交易筛大额。返回 list[{hash, time, value_native, value_usd}]。

    chain: 'bitcoin' 或 'zcash'。限速（430）或失败时返回 ([], 'limited'|'error')，
    调用方不得因此中断整轮扫描。
    """
    try:
        d = _get_json(
            f"https://api.blockchair.com/{chain}/transactions"
            f"?limit={limit}&sort=time(desc)"
        )
    except Exception as e:
        msg = str(e)
        status = "limited" if "430" in msg else "error"
        return [], status
    out = []
    for t in d.get("data", []):
        v = (t.get("output_total") or 0) / 1e8
        if v >= min_native:
            out.append({
                "hash": t.get("hash", ""),
                "time": t.get("time", ""),
                "value_native": round(v, 2),
                "value_usd": round(t.get("output_total_usd") or 0),
                "direction": "unknown_to_unknown",
            })
    return out, "ok"


def mempool_large(min_btc=BTC_MIN):
    """mempool.space BTC 实时补充：最新内存池 10 笔 + 最新区块第一页 25 笔。"""
    out = []
    try:
        for tx in _get_json("https://mempool.space/api/mempool/recent"):
            v = tx.get("value", 0) / 1e8
            if v >= min_btc:
                out.append({
                    "hash": tx.get("txid", ""),
                    "time": "",
                    "value_native": round(v, 2),
                    "value_usd": None,
                    "direction": "unknown_to_unknown",
                    "source": "mempool",
                })
    except Exception:
        pass
    try:
        tip = _get_text("https://mempool.space/api/blocks/tip/hash")
        for tx in _get_json(f"https://mempool.space/api/block/{tip}/txs"):
            v = tx.get("value", 0) / 1e8
            if v >= min_btc:
                out.append({
                    "hash": tx.get("txid", ""),
                    "time": "",
                    "value_native": round(v, 2),
                    "value_usd": None,
                    "direction": "unknown_to_unknown",
                    "source": "block",
                })
    except Exception:
        pass
    # 去重（同一交易可能同时出现在内存池与区块）
    seen, uniq = set(), []
    for t in out:
        if t["hash"] not in seen:
            seen.add(t["hash"])
            uniq.append(t)
    return uniq


def collect():
    """一轮巨鲸扫描。返回 dict，含状态字段供报告标注。"""
    btc_bc, btc_status = blockchair_large("bitcoin", BTC_MIN)
    zec_bc, zec_status = blockchair_large("zcash", ZEC_MIN)
    btc_mp = mempool_large()
    # mempool 与 Blockchair 去重
    seen = {t["hash"] for t in btc_bc}
    btc_all = btc_bc + [t for t in btc_mp if t["hash"] not in seen]
    return {
        "btc": sorted(btc_all, key=lambda t: -t["value_native"])[:20],
        "btc_blockchair_status": btc_status,
        "zec_transparent_only": sorted(zec_bc, key=lambda t: -t["value_native"])[:20],
        "zec_blockchair_status": zec_status,
    }
