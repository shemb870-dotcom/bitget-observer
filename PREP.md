# Bitget 合约动向观测器 — 准备工作报告

日期：2026-10-21（Asia/Shanghai）
状态：v1 已建成并实跑（2026-10-21 04:33 首次全量扫描，20 合约零失败，测试 4/4 通过）。GitHub 建仓被拒（GitHub App 无建仓权限 403），代码在本地完整就绪，待用户手动建空仓库 bitget-observer 后推送。边界沿用既有约定：仅研究、不接钱包、不代下单、不承诺盈利、零新增费用优先、免 key 能跑。

## 1. GitHub 调研（经 GitHub 官方接口按星数实查，2026-10-21）

### 可直接复用/借鉴
- ccxt/ccxt（44,487 星）：100+ 交易所统一接口，含 Bitget。适合做多所交叉验证，避免单一盘口被刷。
- freqtrade/freqtrade（55,668 星）+ freqtrade-strategies（5,576 星）：指标、回测、FreqAI 框架最成熟。本项目只做观测，可借它的指标与信号组织方式，不用它的下单部分。
- hummingbot/hummingbot（20,606 星）：做市/高频盘口分析思路可借鉴，偏重，本期不引入。
- BitgetLimited/v3-bitget-api-sdk（304 星）：Bitget 官方 SDK；另 sieblyio/bitget-api（77 星，含 WS）、cuongitl/python-bitget（49 星）。本项目行情走 REST 直连已实测通过，SDK 备选。
- atilaahmettaner/tradingview-mcp（5,089 星）：多周期技术分析 MCP，可作指标层参考。
- nardew/talipp（543 星）：Python 增量指标库（RSI/MACD 等流式计算），适合实时观测场景。
- kukapay/crypto-indicators-mcp（130 星）：指标 MCP 服务，备选。

### 链上/鲸鱼方向（开源生态薄弱，结论：不依赖开源仓库，走数据源 API）
- 关键词搜索总量仅 49 个仓库且星数低（最高 chainscope 4 星类小工具），无成熟开源链上分析框架。
- uzair-inamdar/crypto-whale-watcher（195 星）：大额成交监控+告警的思路可参考。
- aicoincom/coinos-skills（57 星）：AiCoin 的 AI agent 工具集（含资金费率、鲸鱼），可观察。

### 预测类（结论：只作参考，不采信）
- cbyn/bitpredict（761 星）、CryptoPredictions（275 星）等 ML 预测仓库普遍小且久未成气候。价格预测没有可靠开源解法；观测器只报测量值（动量、拥挤度、资金流），不输出涨跌概率。

## 2. Bitget 合约接口（全部实测，免 key，2026-10-21 03:51 CST）

基地址 https://api.bitget.com/api/v2/mix/market，productType=USDT-FUTURES，全站 845 个合约。

实测通过（code=00000）：
- ticker：最新价/买卖一档/标记价/指数价/24h 涨幅与成交额/资金费率/持仓量
- merge-depth：盘口各档价格+数量。注意 precision 必须传 scale0/scale1/scale2，传数字报 40020；返回数组顺序不稳定，使用前必须自排序（买降序、卖升序）
- candles：多周期 K 线（15m 实测）
- current-fund-rate / history-fund-rate：当前与历史资金费率（8h 周期）
- open-interest：持仓量
- long-short：持仓多空比；account-long-short：账户多空比

ZECUSDT 实测快照（03:51）：现价 $1,210.07，24h +7.96%，24h 成交额 $1.51 亿（全站第 8），资金费率 0.002%/8h，持仓 95,905 ZEC，持仓多空比 1.13，账户多空比 1.09，盘口价差 0.01。

未验证：公共 WebSocket（wss://ws.bitget.com/v2/ws/public，官方文档有 ticker/books 频道）在本机握手失败一次（SSL 错误），标记待验证，v1 先用 REST 轮询。

探针脚本：scripts/bitget_probe.py，任意 symbol 一键出快照（价格、价差、±1% 深度与失衡、资金费率、OI、多空比、15m 动量），已实测 ZEC 通过。

## 3. 链上资金流（免费源全部实测有返回）

- Blockchair API：ZEC/BTC 等多链统计（24h 交易数、链上量、mempool）。注意：ZEC 是屏蔽链，浏览器数据仅覆盖透明池，报告必须标注。
- mempool.space：BTC 费率与拥堵，免 key。
- CoinGecko 免费版：全币种现价/市值/量，免 key（有速率限制）。
- DeFiLlama：稳定币总供给（资金入场代理指标）、TVL，免 key。
- alternative.me：恐惧贪婪指数（当前 55，贪婪）。
- 付费可选（不装也能跑）：Whale Alert（大额转账标签）、CryptoQuant（交易所流入流出）、Glassnode、Nansen、Arkham（标签免费层）。需要时再议，默认不花钱。

## 4. 事件预警源（已确认可达）

- 定时事件：美联储 FOMC 日历（federalreserve.gov，页面 200）、美国 CPI/非农（BLS 日程）、CoinDesk「Crypto Week Ahead」周历（宏观+加密事件汇总）。
- 资金事件：Farside 每日美国现货 BTC ETF 流入流出（页面 200，免费）。
- 交易所事件：Bitget 官方公告（上币/下架/合约参数/维护），联网搜索+官网核验。
- 突发事件：browser.search 联网检索 + browser.open 打开源头核实，区分已证实与传闻。
- 代币解锁日历：DeFiLlama unlocks 等免费页面，v1 接入时逐一核验。

## 5. Skill 准备

- 系统 skill/connector 检索结论：无 Bitget、无加密行情类 connector；financial_planning 是个人预算规划，不适用于合约观测。
- 已新建自定义 skill：~/workspace/custom-skills/crypto-contract-observer/（SKILL.md + skill.yaml），内容含：研究边界、Bitget 接口用法与两个实测坑、信号组合读法（三信号以上才算异动、极端资金费+OI 上升=拥挤而非方向）、链上源与 ZEC 屏蔽链标注、事件预警流程、中文报告格式。
- GitHub connector 已连接可用（本次搜索即走它）。

## 6. 美股板块（2026-10-21 用户追加，准备已完成）

### GitHub（实查）
- OpenBB（openbq-org/OpenBB，74,474 星）：开源金融数据平台，美股数据层首选参考。
- ranaroussi/yfinance（25,568 星）：Yahoo Finance 数据下载库，行业标准。
- wshobson/maverick-mcp（707 星）：Yahoo 数据+技术分析 MCP，备选。
- defeat-beta/defeatbeta-api（787 星）：Yahoo 替代数据 API，备选。

### 数据源（全部实测，免 key）
- Yahoo Finance chart 接口（query1.finance.yahoo.com/v8/finance/chart）：带 UA 头免 key，指数/板块/个股日线与现价全通。美股主源。
- Nasdaq 官方 API（api.nasdaq.com）：个股实时报价实测通（COIN $170.50，Oct 20 收盘后）；财报日历实测通（10/21 META 盘后，EPS 预期 $6.54）。
- SEC EDGAR（company_tickers.json + 备案检索）：公司公告/财报原文，免 key（需 UA）。
- 不可用（本机实测）：Stooq CSV 返回空、CBOE VIX CSV 返回 HTML、CNN 恐惧贪婪 418。VIX 改走 Yahoo ^VIX。
- 付费/需免费 key 可选：FRED（宏观序列，免费 key）、Finnhub/Alpha Vantage（免费档），默认不用。

### 观察清单（探针 scripts/us_probe.py 已实测全量跑通，Oct 20 美股收盘数据）
- 指数与宏观：标普 ^GSPC 7712.57（+0.28%）、纳指 ^IXIC 26424.82、道指 ^DJI 52495.88（+1.02%）、VIX 17.39、10 年美债 ^TNX 5.117%、美元指数 101.72。
- 11 大板块（SPDR）：XLK 科技、XLF 金融、XLE 能源、XLV 医疗、XLI 工业、XLC 通讯、XLY 可选消费、XLP 必选消费、XLB 材料、XLRE 地产、XLU 公用。看相对标普强弱做板块轮动。
- Mag7：AAPL/MSFT/NVDA/AMZN/GOOGL/META/TSLA（当日 META -1.59%，财报前走弱，5 日 -5.87%）。
- 加密联动股：COIN、MSTR（当日 +4.93%）、HOOD、MARA、RIOT、CLSK、IBIT（BTC 现货 ETF）。
- 事件：财报日历（Nasdaq）、FOMC/CPI（已在事件预警节）、盘前盘后异动、SEC 备案（8-K 重大事项）。

### 与币圈的联动读法
- 风险偏好：纳指/VIX/美元/10Y 是 BTC 的宏观四件套，先看它们再解释币价异动。
- 板块轮动领先信号：XLK 与 Mag7 走弱常先于加密风险资产回撤；XLE/黄金走强提示避险。
- 加密股是币价的放大镜：MSTR/COIN/矿股与 BTC 同向但波动更大，背离时标注（如股价涨而币不动，多为个股事件）。

## 7. 待用户决定（开建 v1 前）

1. 观测币种清单：「部分合约」具体哪些？默认建议 BTC/ETH/SOL/ZEC + 24h 成交额 Top 20 山寨，自动轮换。
2. 预警阈值：价格异动 %、资金费率极值、OI 变化 %、盘口失衡，默认值可先用（15m 涨跌 3%、资金费率 ±0.05%、OI 1h 变化 5%）。
3. 推送渠道：先在这个对话里报，还是要手机推送（可复用事件镜的 Cloudflare Workers 定时任务+免费推送路线）。
4. 形态：独立小工具（脚本+定时扫描+报告），还是并入事件镜 PWA 加一个「合约观测」页。

## 8. 2026-10-27 扩展：巨鲸追踪 + 新增数据源（已集成、已实测）

### 巨鲸模块 observer/whale.py
- Blockchair BTC/ZEC 最近 100 笔交易筛大额：BTC ≥100、ZEC ≥1000（仅透明池，屏蔽池不可见，报告必须标注）。
- mempool.space 实时补充：最新内存池 10 笔 + 最新区块第一页 25 笔；Blockchair 430 限速时自动降级，不中断扫描。
- 方向四分类框架（参考 dominique1993/Crypto-Whale-Tracker 与 openclaw skill）：exchange_to_exchange / exchange_to_unknown / unknown_to_exchange / unknown_to_unknown；当前无交易所标签包，全部记 unknown_to_unknown（诚实标注，不猜测）。
- 实测：ZEC 1634.78（约 $198 万）已抓到；BTC 本轮样本无 ≥100 交易（巨鲸交易稀少，30 分钟一扫总能抓到）。

### 新增数据源 observer/extra.py（全部免 key，2026-10-27 实测）
- OKX 公开 API：爆仓单（必须带 state=filled，返回结构为 details 嵌套数组）、持仓量、资金费率——跨所验证 Bitget。
- Deribit 公开 API：BTC DVOL 波动率指数（需传毫秒时间戳，取最近 1 小时最后一点；实测 38.43）。
- Farside：BTC/ETH ETF 资金流（HTML 解析，失败自动跳过；BTC 实测有数，ETH 解析未命中返回 None）。
- BLS 公开 API v2：CPI CUUR0000SA0、PPI WPUFD49207、非农 CES0000000001（月度，免 key 限 25 次/天，观测器每月拉 3 次足够）。
- Blockstream：BTC 区块高度（实测 973274）。
- 未通过（不要集成）：FRED CSV 超时、Binance 451 地理封锁、Bybit 403、OKX 多空比端点不存在、BLS 日程页 403、blockchain.info 图表 404、美国财政部接口 0 条数据。

### 报告与仪表盘
- scan.py 新增"巨鲸动向"与"跨所与宏观"两节，payload 增加 whales、extras 字段。
- index.html 新增对应两个板块；测试 5/5（含新增 WhaleFilterTest：阈值过滤 + output_total=None 容错）。

### Blockchair 限流警告（2026-10-27 调研实测）
- Blockchair 匿名调用过频会触发 IP 临时黑名单（430："Your IP address is temporary blacklisted due to exceeding usage"）。
- 观测器调用 Blockchair 处：onchain（BTC/ZEC stats）+ whale（BTC/ZEC 最近交易）= 每轮 4 次；Actions 每 30 分钟跑一次、每次换 runner IP，风险低于本机连续调试，但仍需节流意识：不要在 Actions 工作流里加重试循环，不要把扫描间隔改短于 30 分钟。
- 本机调试 Blockchair 时两次请求间隔至少 60 秒，遇到 430 就停手等下一轮（whale 模块已有 limited 降级，扫描不会因此中断）。
