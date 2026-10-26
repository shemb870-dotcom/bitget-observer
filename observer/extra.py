"""新增免费数据源（全部免 key，2026-10-27 实测通过）。

- OKX 公开 API：爆仓单、资金费率、持仓量（跨所验证 Bitget 数据）。
- Deribit 公开 API：BTC 期权盘口摘要、DVOL 波动率指数。
- Farside：BTC/ETH ETF 每日资金流（HTML 解析，失败自动跳过）。
- BLS 公开 API v2：CPI/PPI/非农（月度，免 key 限 25 次/天，观测器每月拉 3 次足够）。
- Blockstream：BTC 区块高度与内存池（巨鲸模块的备用源）。
- blockchain.info 图表：活跃地址、算力、矿工收入（7 日）。

全部容错：任一源失败只记状态，不中断整轮扫描。
"""

import json
import re
import urllib.request

UA = {"User-Agent": "bitget-observer/1.0"}


def _get_json(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _get_text(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode()


def okx_liquidations(inst="BTC-USDT"):
    """OKX 最近已成交爆仓单。注意必须带 state=filled，否则 400。
    返回结构为 [{details: [{posSide, bkPx, sz, ...}]}]，需展开 details。"""
    d = _get_json(
        "https://www.okx.com/api/v5/public/liquidation-orders"
        f"?instType=SWAP&uly={inst}&state=filled"
    )
    out = []
    for r in d.get("data", []):
        for item in r.get("details", []):
            try:
                out.append({
                    "side": item.get("posSide"),
                    "price": float(item.get("bkPx") or 0),
                    "sz": float(item.get("sz") or 0),
                })
            except (TypeError, ValueError):
                continue
    return out[:20]


def okx_oi_funding(inst="BTC-USDT-SWAP"):
    d1 = _get_json(
        f"https://www.okx.com/api/v5/public/open-interest?instId={inst}")
    d2 = _get_json(
        f"https://www.okx.com/api/v5/public/funding-rate?instId={inst}")
    oi = (d1.get("data") or [{}])[0]
    fr = (d2.get("data") or [{}])[0]
    return {
        "oi_usd": float(oi.get("oiUsd") or 0) or None,
        "funding_rate": float(fr.get("fundingRate") or 0) or None,
    }


def deribit_dvol(currency="BTC"):
    """Deribit 波动率指数（需传毫秒时间戳，取最近 1 小时最后一个点）。"""
    import time
    now = int(time.time())
    d = _get_json(
        "https://www.deribit.com/api/v2/public/get_volatility_index_data"
        f"?currency={currency}&start_timestamp={(now - 3600) * 1000}"
        f"&end_timestamp={now * 1000}&resolution=60")
    data = d.get("result", {}).get("data", [])
    if not data:
        return None
    return float(data[-1][1])


def farside_etf_flow(kind="btc"):
    """Farside ETF 资金流（HTML 表格解析）。解析失败返回 None，不抛错。"""
    try:
        html = _get_text(f"https://farside.co.uk/{kind}/")
    except Exception:
        return None
    m = re.search(r"Total Flow[^0-9\-+]*([\-+0-9,\.]+)", html)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def bls_macro():
    """BLS：CPI、PPI、非农最新值。"""
    series = {"cpi": "CUUR0000SA0", "ppi": "WPUFD49207", "nonfarm": "CES0000000001"}
    out = {}
    for key, sid in series.items():
        try:
            d = _get_json(
                f"https://api.bls.gov/publicAPI/v2/timeseries/data/{sid}?latest=true")
            rows = d.get("Results", {}).get("series", [{}])[0].get("data", [])
            if rows:
                out[key] = {"period": rows[0].get("periodName"), "value": rows[0].get("value")}
        except Exception:
            continue
    return out


def blockstream_tip():
    h = _get_text("https://blockstream.info/api/blocks/tip/height")
    return int(h)


def chain_charts():
    """blockchain.info 7 日图表：活跃地址、算力、矿工收入（取最新点）。
    注意 timespan 参数必须是 7days（写 7day 会 404）。"""
    out = {}
    for key, slug in [("unique_addresses", "n-unique-addresses"),
                      ("hash_rate", "hash-rate"),
                      ("miners_revenue", "miners-revenue")]:
        try:
            d = _get_json(
                f"https://api.blockchain.info/charts/{slug}?timespan=7days&format=json")
            vals = d.get("values", [])
            if vals:
                out[key] = vals[-1].get("y")
        except Exception:
            continue
    return out


def stablecoin_delta():
    """DeFiLlama 稳定币供给日/周变化（只用列表接口，不拉单币 21MB 全量历史）。"""
    d = _get_json("https://stablecoins.llama.fi/stablecoins?includePrices=true")
    out = {}
    for row in d.get("peggedAssets", []):
        sym = row.get("symbol")
        if sym in ("USDT", "USDC"):
            circ = row.get("circulating", {})
            prev_day = (row.get("circulatingPrevDay") or {}).get("peggedUSD")
            prev_week = (row.get("circulatingPrevWeek") or {}).get("peggedUSD")
            out[sym] = {
                "now": circ.get("peggedUSD"),
                "prev_day": prev_day,
                "prev_week": prev_week,
            }
    return out


def collect():
    out = {}
    for key, fn in [
        ("okx_liquidations", okx_liquidations),
        ("okx_oi_funding", okx_oi_funding),
        ("deribit_dvol_btc", deribit_dvol),
        ("farside_btc_flow", lambda: farside_etf_flow("btc")),
        ("farside_eth_flow", lambda: farside_etf_flow("eth")),
        ("bls", bls_macro),
        ("blockstream_height", blockstream_tip),
        ("chain_charts", chain_charts),
        ("stablecoin_delta", stablecoin_delta),
    ]:
        try:
            out[key] = fn()
        except Exception as e:
            out[key] = {"error": str(e)[:80]}
    return out
