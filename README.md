# Bitget 合约动向观测器 + 美股板块

仅研究工具：不接钱包、不代下单、不承诺盈利。全部数据源为免 key 公开接口，零依赖（Python 标准库）。

## 看什么

- **Bitget 合约**：核心 BTC/ETH/SOL/ZEC + 24h 成交额 Top 16，共 20 个 USDT 永续。价格、15m/1h 动量、资金费率、持仓量、多空比、盘口 ±1% 深度与失衡、买卖五档（价格/数量）。
- **异动告警**：阈值在 `config.json`。资金费率极端、急动、盘口失衡（带最小深度防薄盘误报）、多空比极端、持仓量 1h 异动。
- **链上与情绪**：BTC/ZEC 链统计（Blockchair；注意 ZEC 是屏蔽链，仅透明池）、恐惧贪婪、稳定币总供给。
- **美股板块**：标普/纳指/道指/VIX/10 年美债/美元指数、SPDR 11 板块强弱、Mag7、加密联动股（COIN/MSTR/HOOD/矿股/IBIT）、当日财报日历（Nasdaq）。
- **巨鲸动向**：Blockchair BTC ≥100 / ZEC ≥1000 透明池大额转账 + mempool.space 实时补充（方向四分类框架，暂无交易所标签包，诚实标注 unknown）。
- **跨所与宏观**：OKX 爆仓单/持仓量/资金费率（跨所验证）、Deribit BTC DVOL 波动率、Farside ETF 资金流、BLS CPI/PPI/非农、Blockstream 区块高度。

## 跑法

```bash
python3 -m observer.scan        # 生成 reports/latest.md
python3 -m unittest discover tests
python3 scripts/bitget_probe.py ZECUSDT   # 单合约快照
python3 scripts/us_probe.py                 # 美股全板快照
```

GitHub Actions 每 30 分钟自动扫描并把报告提交回仓库（见 `.github/workflows/scan.yml`），打开 `reports/latest.md` 即最新一期。

## 数据源（2026-10-21 全部实测）

- Bitget v2 公开 REST（免 key）。注意：盘口 precision 传 scale0/1/2；深度数组顺序不稳定，代码里已自排序。
- Yahoo Finance chart 接口（带 UA 免 key）；Nasdaq 官方 API（报价/财报日历）；SEC EDGAR。
- Blockchair、mempool.space、CoinGecko、DeFiLlama、alternative.me。
- 2026-10-27 新增（全部免 key 实测）：OKX 公开 API（爆仓/持仓/费率）、Deribit DVOL、Farside ETF 流、BLS CPI/PPI/非农、Blockstream；避开 FRED CSV 超时、Binance 451、Bybit 403、blockchain.info 图表 404。
- 不可用已避开：Stooq（返回空）、CBOE VIX CSV（返回 HTML）、CNN 恐惧贪婪（挡机器人）。

准备调研全文见 `PREP.md`。
