"""主扫描：Bitget 合约 + 链上 + 美股，生成中文 Markdown 报告。

用法（仓库根目录）: python3 -m observer.scan
产物: reports/latest.md、data/state.json、data/snapshots.jsonl
"""
import json
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import bitget, onchain, signals, usboard, whale, extra

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CST = ZoneInfo("Asia/Shanghai")


def _load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def _prev_snapshot(history, symbol, now):
    """取该 symbol 约 1 小时前（至少 45 分钟前）的最近一条快照。"""
    best = None
    for row in history:
        if row["symbol"] != symbol:
            continue
        ts = datetime.fromisoformat(row["ts"])
        if now - ts >= timedelta(minutes=45):
            if best is None or ts > datetime.fromisoformat(best["ts"]):
                best = row
    return best


def fmt_price(p):
    if p is None:
        return "-"
    if p >= 100:
        return f"{p:,.2f}"
    if p >= 1:
        return f"{p:.3f}"
    if p >= 0.01:
        return f"{p:.4f}"
    return f"{p:.8f}".rstrip("0")


def fmt_usd(v):
    if v is None:
        return "-"
    if abs(v) >= 1e9:
        return f"${v/1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.1f}M"
    return f"${v:,.0f}"


def run():
    with open(os.path.join(ROOT, "config.json")) as f:
        cfg = json.load(f)
    th = cfg["thresholds"]
    now = datetime.now(timezone.utc)
    now_cst = now.astimezone(CST)

    state_path = os.path.join(ROOT, "data", "state.json")
    snap_path = os.path.join(ROOT, "data", "snapshots.jsonl")
    history = _load(state_path, {}).get("history", [])

    symbols = bitget.top_symbols(cfg["core_symbols"], cfg["top_volume_extra"])
    snaps, alerts = [], []
    for sym in symbols:
        try:
            s = bitget.snapshot(sym)
        except Exception as e:
            alerts.append(f"{sym} 拉取失败：{str(e)[:80]}")
            continue
        s["ts"] = now.isoformat()
        snaps.append(s)
        alerts.extend(signals.evaluate(s, _prev_snapshot(history, sym, now), th))

    try:
        chain = onchain.collect()
    except Exception as e:
        chain = {"error": str(e)[:100]}
    try:
        us = usboard.board()
        earnings = usboard.earnings_today()
    except Exception as e:
        us, earnings = {}, []
        alerts.append(f"美股板块拉取失败：{str(e)[:80]}")
    try:
        whales = whale.collect()
    except Exception as e:
        whales = {"btc": [], "zec_transparent_only": [],
                  "btc_blockchair_status": "error", "zec_blockchair_status": "error"}
    try:
        extras = extra.collect()
    except Exception:
        extras = {}

    lines = []
    lines.append(f"# 合约动向观测报告")
    lines.append(f"时间：{now_cst.strftime('%Y-%m-%d %H:%M')} CST ｜ 仅研究，不接钱包、不下单、不承诺盈利")
    lines.append("")
    lines.append("## 异动告警")
    if alerts:
        for a in alerts:
            lines.append(f"- ⚠️ {a}")
    else:
        lines.append("- 无（全部在阈值内）")
    lines.append("")
    lines.append("## Bitget 合约（按 24h 成交额）")
    lines.append("| 合约 | 价格 | 24h | 15m | 1h | 资金费率/8h | 持仓量 | 多空比 | 盘口失衡±1% |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for s in sorted(snaps, key=lambda x: -x["quote_volume_24h"]):
        lines.append(
            f"| {s['symbol']} | {fmt_price(s['price'])} | {s['change24h_pct']:+.2f}% | {s['mom_15m_pct']:+.2f}% "
            f"| {s['mom_1h_pct']:+.2f}% | {s['funding_rate']*100:.4f}% | {s['open_interest']:,.0f} "
            f"| {s['ls_ratio'] if s['ls_ratio'] is not None else '-'} | {s['imbalance_1pct']:+.2f} |")
    lines.append("")
    focus = next((s for s in snaps if s["symbol"] == "ZECUSDT"), None)
    if focus:
        lines.append(f"## 盘口明细 ZECUSDT（价差 {focus['spread']}）")
        lines.append("卖盘（价/量）：" + " ｜ ".join(f"{p:g} / {q:g}" for p, q in reversed(focus["top_asks"])))
        lines.append("买盘（价/量）：" + " ｜ ".join(f"{p:g} / {q:g}" for p, q in focus["top_bids"]))
        lines.append("")
    lines.append("## 链上与情绪")
    fg = chain.get("fear_greed", {})
    if "value" in fg:
        lines.append(f"- 恐惧贪婪指数：{fg['value']}（{fg['label']}）")
    btc = chain.get("btc_chain", {})
    if "txs_24h" in btc:
        lines.append(f"- BTC 链 24h 交易数：{btc['txs_24h']:,}，mempool 待确认：{btc['mempool_txs']:,}")
    zec = chain.get("zec_chain_transparent_only", {})
    if "txs_24h" in zec:
        lines.append(f"- ZEC 链 24h 交易数：{zec['txs_24h']:,}（仅透明池，屏蔽池不可见）")
    if chain.get("stablecoin_supply_usd"):
        lines.append(f"- 稳定币总供给：{fmt_usd(chain['stablecoin_supply_usd'])}")
    lines.append("")
    lines.append("## 巨鲸动向（大额转账，免 key 链上源）")
    if whales.get("btc"):
        lines.append(f"- BTC ≥100（{len(whales['btc'])} 笔）：")
        for t in whales["btc"][:10]:
            usd = f" ≈ ${t['value_usd']:,.0f}" if t.get("value_usd") else ""
            lines.append(f"  - {t['value_native']:,.1f} BTC{usd} ｜ {t['hash'][:16]}… ｜ {t['time'] or '内存池/最新区块'}")
    else:
        note = "（Blockchair 限速，本轮以 mempool 实时源为准）" if whales.get("btc_blockchair_status") == "limited" else ""
        lines.append(f"- BTC ≥100：本轮未见{note}")
    if whales.get("zec_transparent_only"):
        lines.append(f"- ZEC ≥1000 透明池（{len(whales['zec_transparent_only'])} 笔，仅透明池，屏蔽池不可见）：")
        for t in whales["zec_transparent_only"][:10]:
            usd = f" ≈ ${t['value_usd']:,.0f}" if t.get("value_usd") else ""
            lines.append(f"  - {t['value_native']:,.0f} ZEC{usd} ｜ {t['hash'][:16]}… ｜ {t['time']}")
    else:
        note = "（Blockchair 限速，下一轮重试）" if whales.get("zec_blockchair_status") == "limited" else ""
        lines.append(f"- ZEC ≥1000 透明池：本轮未见{note}")
    lines.append("")
    lines.append("## 跨所与宏观（新增免费源）")
    oi = extras.get("okx_oi_funding") or {}
    if isinstance(oi, dict) and oi.get("oi_usd"):
        lines.append(f"- OKX BTC 持仓量：{fmt_usd(oi['oi_usd'])} ｜ 资金费率：{oi['funding_rate']*100:.4f}%（跨所验证 Bitget）")
    liq = extras.get("okx_liquidations") or []
    if isinstance(liq, list) and liq:
        longs = sum(1 for t in liq if t.get("side") == "long")
        shorts = len(liq) - longs
        lines.append(f"- OKX 最近爆仓：{len(liq)} 单（多头 {longs} / 空头 {shorts}）")
    dvol = extras.get("deribit_dvol_btc")
    if isinstance(dvol, (int, float)):
        lines.append(f"- Deribit BTC 波动率指数 DVOL：{dvol:.2f}")
    fb = extras.get("farside_btc_flow")
    if isinstance(fb, (int, float)):
        lines.append(f"- BTC ETF 资金流（Farside）：${fb:,.0f}")
    fe = extras.get("farside_eth_flow")
    if isinstance(fe, (int, float)):
        lines.append(f"- ETH ETF 资金流（Farside）：${fe:,.0f}")
    bls = extras.get("bls") or {}
    if isinstance(bls, dict) and bls:
        parts = []
        if bls.get("cpi"): parts.append(f"CPI {bls['cpi']['period']} {bls['cpi']['value']}")
        if bls.get("ppi"): parts.append(f"PPI {bls['ppi']['period']} {bls['ppi']['value']}")
        if bls.get("nonfarm"): parts.append(f"非农 {bls['nonfarm']['period']} {bls['nonfarm']['value']}千人")
        if parts: lines.append("- 美国宏观（BLS）： " + " ｜ ".join(parts))
    cc = extras.get("chain_charts") or {}
    if isinstance(cc, dict) and cc.get("unique_addresses"):
        lines.append(f"- BTC 链上健康：活跃地址 {cc['unique_addresses']:,.0f}/日 ｜ 算力 {cc['hash_rate']/1e9:.2f} EH/s ｜ 矿工日收入 ${cc['miners_revenue']/1e6:.1f}M")
    sd = extras.get("stablecoin_delta") or {}
    if isinstance(sd, dict) and sd.get("USDT"):
        u = sd["USDT"]
        dd = f"{(u['now']-u['prev_day'])/1e9:+.2f}B/日" if u.get("now") and u.get("prev_day") else "-"
        dw = f"{(u['now']-u['prev_week'])/1e9:+.2f}B/周" if u.get("now") and u.get("prev_week") else "-"
        lines.append(f"- USDT 供给：${u['now']/1e9:.1f}B（{dd}，{dw}）")
    lines.append("")
    lines.append("## 美股板块")
    idx = {r["symbol"]: r for r in us.get("indices", []) if "price" in r}
    if idx:
        lines.append("- 指数：" + " ｜ ".join(
            f"{k} {v['price']:,.2f}（{v['change_1d_pct']:+.2f}%）" for k, v in idx.items()))
    sectors = [r for r in us.get("sectors", []) if r.get("change_1d_pct") is not None]
    if sectors:
        sectors.sort(key=lambda r: -r["change_1d_pct"])
        lines.append("- 板块强弱（1d）：" + " ｜ ".join(f"{r['symbol']} {r['change_1d_pct']:+.2f}%" for r in sectors))
    for key, label in [("mag7", "Mag7"), ("crypto_linked", "加密联动股")]:
        rows = [r for r in us.get(key, []) if r.get("price")]
        if rows:
            lines.append(f"- {label}：" + " ｜ ".join(
                f"{r['symbol']} {r['price']:,.2f}（{r['change_1d_pct']:+.2f}%）" for r in rows))
    if earnings:
        lines.append("- 今日财报（美东）：" + " ｜ ".join(
            f"{e['symbol']} {e['time']} EPS预期 {e['eps_forecast']}" for e in earnings))
    lines.append("")

    report = "\n".join(lines)
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    payload = {
        "ts_cst": now_cst.strftime("%Y-%m-%d %H:%M"),
        "alerts": alerts,
        "crypto": sorted(snaps, key=lambda x: -x["quote_volume_24h"]),
        "zec_book": focus,
        "onchain": chain,
        "whales": whales,
        "extras": extras,
        "us": us,
        "earnings": earnings,
    }
    with open(os.path.join(ROOT, "reports", "latest.json"), "w") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "reports", "latest.md"), "w") as f:
        f.write(report)
    with open(snap_path, "a") as f:
        for s in snaps:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    history = (history + snaps)[-400:]
    with open(state_path, "w") as f:
        json.dump({"history": history}, f, ensure_ascii=False)
    print(report)
    return report


if __name__ == "__main__":
    run()
