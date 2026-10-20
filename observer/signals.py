"""信号判定：纯函数，可单测。只报测量与阈值，不输出涨跌概率。"""


def evaluate(snap, prev, th):
    """snap 当前快照，prev 约 1 小时前快照（可为 None），th 阈值 dict。返回告警字符串列表。"""
    alerts = []
    sym = snap["symbol"]
    fr = snap["funding_rate"]
    if abs(fr) >= th["funding_abs"]:
        side = "多头拥挤（多付空）" if fr > 0 else "空头拥挤（空付多）"
        alerts.append(f"{sym} 资金费率 {fr*100:.3f}%/8h，{side}")
    if abs(snap["mom_15m_pct"]) >= th["mom_15m_abs_pct"]:
        alerts.append(f"{sym} 15 分钟动量 {snap['mom_15m_pct']:+.2f}%")
    if abs(snap["mom_1h_pct"]) >= th["mom_1h_abs_pct"]:
        alerts.append(f"{sym} 1 小时动量 {snap['mom_1h_pct']:+.2f}%")
    depth_total = snap["bid_depth_1pct_usd"] + snap["ask_depth_1pct_usd"]
    if abs(snap["imbalance_1pct"]) >= th["book_imbalance_abs"] and depth_total >= th["book_min_depth_usd"]:
        side = "买盘压过卖盘" if snap["imbalance_1pct"] > 0 else "卖盘压过买盘"
        alerts.append(f"{sym} 盘口 ±1% 失衡 {snap['imbalance_1pct']:+.2f}，{side}（深度 ${depth_total:,.0f}）")
    if snap.get("ls_ratio") is not None:
        if snap["ls_ratio"] >= th["ls_ratio_high"]:
            alerts.append(f"{sym} 持仓多空比 {snap['ls_ratio']:.2f}，多头极端占优")
        elif snap["ls_ratio"] <= th["ls_ratio_low"]:
            alerts.append(f"{sym} 持仓多空比 {snap['ls_ratio']:.2f}，空头极端占优")
    if prev and prev.get("open_interest"):
        oi_chg = (snap["open_interest"] / prev["open_interest"] - 1) * 100
        if abs(oi_chg) >= th["oi_change_1h_abs_pct"]:
            alerts.append(f"{sym} 持仓量约 1 小时变化 {oi_chg:+.2f}%")
    return alerts
