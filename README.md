# 量化策略系统 v5.6

> **AI驱动的多策略量化投资组合管理系统**
>
> 策略: 风险平价 + 核心-卫星 + 动量择时 + AI Hedge Fund | 数据源: Wind MCP (P0) → iFinD MCP (P1) → AKShare (P2) → 新浪 (P3) → 本地缓存 (P4) → 兜底价格 (P5)

---

## 一、快速开始

### 1.1 环境要求

- Python >= 3.10
- Node.js >= 18 (Wind MCP CLI)
- Streamlit >= 1.30
- scikit-learn >= 1.0 (期货期权信号分析)
- langchain + langgraph (可选, AI Hedge Fund)

### 1.2 安装依赖

```bash
# 核心依赖
pip install numpy pandas pyyaml streamlit openpyxl python-dotenv requests yfinance plotly scikit-learn scipy

# 可选: AI Hedge Fund
pip install langgraph langchain langchain-openai

# 可选: 本地LLM推理
pip install transformers torch accelerate
```

### 1.3 配置 API Key

创建 `.env` 文件:

```bash
# DeepSeek V4 Pro API (LLM决策引擎)
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Wind MCP API Key (金融数据主源, P0)
WIND_API_KEY=your_wind_api_key_here

# iFinD MCP (同花顺, P1备选)
IFIND_TOKEN=your_ifind_token_here

# Tushare (国内期货/CPI, P2)
TS_TOKEN=your_tushare_token_here

# 火山引擎 (豆包 LLM, AI分析)
VOLCENGINE_API_KEY=your_volcengine_api_key_here

# 报告输出目录
REPORT_OUTPUT_DIR=./每日报告归档
LOG_LEVEL=INFO
```

---

## 二、常用命令

### 2.1 启动监控面板

```bash
# 启动 Streamlit 监控面板 (推荐)
streamlit run ui/app.py

# 或使用批处理文件
启动UI面板.bat

# Python脚本启动
python run_ui.py
```

访问地址: `http://localhost:8501`

### 2.2 日报生成与交易工作流

```bash
# 每日盘前再平衡流水线 (08:30自动) — XGBoost + 风险平价 + FinBERT + 信号合成
python daily_pre_market.py

# 盘中实时决策调度器 (GLM5 AI)
python auto_intraday_decision.py --once

# 盘后综合报告
python daily_trading_workflow.py --phase postmarket

# 三阶段工作流 (盘前 → 盘中 → 盘后)
python daily_trading_workflow.py --phase all

# 每日量化报告
python 11_quant_daily_report.py
```

### 2.3 AI再平衡与自动交易

```bash
# 自动再平衡 (含AI决策)
python auto_trading_system.py

# AI量化再平衡引擎
python -c "from quant_modules.ai_rebalancing_engine import run_ai_rebalance; print(run_ai_rebalance({}, {}))"

# 简单再平衡
python simple_rebalance.py
```

### 2.4 AI Hedge Fund — 19位大师级AI分析师 ⭐ NEW v5.6

```bash
# 启动AI Hedge Fund (LangGraph编排19位分析师)
python "量化策略系统 v5.6.py" --ai-hedge

# 代码调用
from quant_modules.ai_hedge_fund.orchestrator import run_ai_hedge_fund
result = run_ai_hedge_fund(tickers=['600036', '000001'])
```

19位AI分析师涵盖: 价值投资、成长投资、宏观分析、技术分析、量化因子、风控等维度, LangGraph编排工作流, 最终生成综合投资决策。

### 2.5 四大理论引擎

```bash
# 运行四大理论分析
python -c "from quant_modules.decision_theories import run_full_theory_analysis; run_full_theory_analysis({})"
```

| 理论 | 核心思想 | 输出信号 |
|------|----------|----------|
| 索罗斯反身性 | 市场偏见 → 价格扭曲 → 趋势反转 | 反转信号 |
| 瑞达利奥经济机器 | 债务周期 → 经济阶段 → 资产配置 | 配置信号 |
| 第一性原理 | 基本面 → 内在价值 → 安全边际 | 价值信号 |
| 巴菲特芒格 | 护城河 → 长期持有 → 复利增长 | 持有信号 |

### 2.6 盘中AI决策 (GLM5) ⭐

```bash
# GLM5 AI盘中实时决策
python auto_intraday_decision.py              # 启动定时调度
python auto_intraday_decision.py --once       # 只执行一次

# CLI模式
python "量化策略系统 v5.6.py" --ai-decision
```

### 2.7 期货期权信号系统 ⭐

```bash
# 独立运行信号生成器
python signals/futures_options_signal.py

# 附加到综合日报
python append_futures_to_daily.py

# 完整集成流程
python integrate_futures_options.py --append-to-report
```

功能: 宏观经济量化分析 → 期货信号 (铁矿石/原油/黄金) → 期权信号 (沪深300/上证50ETF) → AI决策引擎 → 交易建议报告

### 2.8 盘前预测流水线 ⭐

```bash
# 自动盘前计划 (XGBoost + 风险平价 + FinBERT + 信号合成)
python daily_pre_market.py

# 批处理启动
自动盘前计划.bat
```

执行顺序: XGBoost 5日方向预测 → 风险平价回测 → FinBERT情感分析 → 三源信号合成 → 生成MD报告
输出: `每日报告归档/YYYY-MM-DD/盘前再平衡报告.md`

### 2.9 期货期权扫描

```bash
# 期货期权套利机会扫描
python -c "from quant_modules.futures_options_scanner import scan_all; scan_all()"

# 期货期权AI自动交易员
python ai_futures_auto_trader.py
```

### 2.10 五年收益预测

```bash
python 五年收益预测.py
```

### 2.11 回测

```bash
# 3年回测
python backtest_3year.py

# 快速回测
python fast_backtest.py

# 综合回测与宏观周期分析
python 综合回测与宏观周期分析.py
```

### 2.12 其他常用命令

```bash
# 持仓统计
python position_stats.py

# 止损监控
python stop_loss_monitor.py

# ETF资金流向
python 实时ETF资金流向.py

# 宏观分析
python macro_analysis.py

# 康波周期分析
python kontratieff_cycle.py

# 统一启动器 (股票 + 期货期权 + 逆回购 + 风控)
python unified_launcher.py
```

---

## 三、CLI运行模式 (20个)

```bash
python "量化策略系统 v5.6.py" --live              # 实时监控
python "量化策略系统 v5.6.py" --report            # 生成报告
python "量化策略系统 v5.6.py" --rebalance         # Excel驱动再平衡
python "量化策略系统 v5.6.py" --rebalance --sync-sl  # 同步止损止盈
python "量化策略系统 v5.6.py" --risk              # 风险监控
python "量化策略系统 v5.6.py" --check             # 系统健康检查
python "量化策略系统 v5.6.py" --etf-flow          # ETF资金流向
python "量化策略系统 v5.6.py" --portfolio-opt     # 投资组合优化
python "量化策略系统 v5.6.py" --kommo-monitor     # 康波周期商品监控
python "量化策略系统 v5.6.py" --commodity-fund    # 大宗商品基本面
python "量化策略系统 v5.6.py" --train-model       # 时序预测训练
python "量化策略系统 v5.6.py" --kondratiev        # 康波+十五五交叠
python "量化策略系统 v5.6.py" --fifteen-five      # 十五五规划适配
python "量化策略系统 v5.6.py" --social-security   # 社保基金ETF追踪
python "量化策略系统 v5.6.py" --macro-analysis    # 宏观综合分析(一键三大)
python "量化策略系统 v5.6.py" --daily --phase all # 三阶段工作流
python "量化策略系统 v5.6.py" --backtest          # 回测验证
python "量化策略系统 v5.6.py" --ai-decision       # GLM5 AI盘中实时决策 ⭐ v5.2
python "量化策略系统 v5.6.py" --futures-options   # 期货期权扫描 ⭐ v5.5
python "量化策略系统 v5.6.py" --ai-hedge          # AI Hedge Fund 19位分析师 ⭐ v5.6
```

---

## 四、目录结构

```
11_量化策略/
├── 量化策略系统 v5.6.py                # 主系统入口 (72.8KB, 20 CLI模式)
│
├── quant_modules/                      # 核心量化模块 ★
│   ├── ai_hedge_fund/                  # AI Hedge Fund (19位AI分析师 + LangGraph) ⭐ v5.6
│   ├── ai_rebalancing_engine.py        # AI量化再平衡引擎
│   ├── decision_theories.py            # 四大理论引擎 (索罗斯/达利奥/第一性/巴菲特)
│   ├── futures_options_scanner.py      # 期货期权扫描器
│   ├── macro_decision_bridge.py        # 宏观决策桥接
│   ├── macro_wind_adapter.py           # Wind宏观数据适配器
│   ├── trading_agents_bridge.py        # 交易代理桥接
│   ├── futures_opportunity_analyzer.py # 期货机会分析
│   ├── wind_mcp.py                     # Wind MCP CLI封装 (P0)
│   ├── data_layer.py                   # 缓存+多源连接器管理器
│   ├── core.py                         # 配置/异常/策略注册/成本计算
│   ├── prediction_bridge.py            # 预测信号桥接器
│   ├── dynamic_position.py             # 动态仓位管理
│   └── cma_bridge.py                   # CMA桥接
│
├── engine/                             # 引擎层
│   ├── data.py                         # 统一数据层
│   ├── rebalance.py                    # 再平衡引擎 v4
│   ├── managers.py                     # 组合优化/康波/ETF管理器
│   ├── etf_flow.py                     # ETF资金流监控
│   └── social_security.py              # 社保基金风格追踪
│
├── signals/                            # 交易信号生成器 ⭐ v5.5+
│   ├── futures_options_signal.py       # 期货期权AI信号生成器
│   ├── token_risk_factor.py            # Token风险因子
│   ├── token_auto_capacity.py          # 自动容量因子
│   ├── token_factor_combiner.py        # 因子组合器
│   └── reports/                        # 信号报告归档
│
├── model_train/                        # 模型训练与增强信号 ⭐ v5.6
│   ├── xgboost_direction.py            # XGBoost 5日方向预测
│   ├── risk_parity_backtest.py         # 风险平价回测
│   ├── finbert_sentiment.py            # FinBERT金融情感分析
│   ├── signal_composer.py              # 三源信号合成器
│   ├── models/                         # 训练好的模型文件
│   └── output/                         # 预测输出 (JSON/Parquet/CSV)
│
├── modes/                              # 运行模式调度 ⭐ v5.2+
│   ├── __init__.py
│   └── operations.py                   # 71KB, 所有run_*函数抽取
│
├── utils/                              # 工具模块 (17个文件)
│   ├── kondratiev_cycle.py             # 康波周期分析
│   ├── five_year_plan.py               # 十五五规划适配
│   ├── social_security_etf.py          # 社保ETF追踪
│   ├── glm5_client.py                  # GLM5客户端
│   ├── glm5_decision_engine.py         # GLM5决策引擎
│   ├── kronos_predictor.py             # Kronos K线预测器
│   ├── qwen_financial_predictor.py     # Qwen金融预测器
│   ├── local_llm.py                    # 本地LLM管理
│   ├── intraday_decision.py            # 盘中决策
│   ├── data_source_manager.py          # 多源自适应管理
│   ├── logging_manager.py              # 统一日志
│   ├── event_tracker.py                # 事件追踪
│   ├── report_archiver.py              # 报告归档
│   ├── console_encoding.py             # 控制台编码
│   └── env_loader.py                   # 环境变量加载
│
├── models/                             # 训练好的ML模型
│   ├── AI-ModelScope/Kronos-small/     # Kronos金融K线预测模型
│   ├── NeoQuasar/Kronos-Tokenizer-base/# Kronos分词器
│   └── *.pkl / *.pt                    # RF/XGBoost/PatchTST模型
│
├── Kronos/                             # Kronos金融预测开源项目 (第三方)
├── Shadowbroker/                       # 全球威胁情报平台 (独立项目)
│
├── ui/                                 # Streamlit可视化面板
│   ├── app.py                          # 主入口 (导航路由)
│   ├── components/                     # 公共UI组件 (7个)
│   │   ├── names.py                    # 共享标的名称映射
│   │   ├── progress.py                 # 进度组件
│   │   ├── report_viewer.py            # 报告浏览/预览
│   │   ├── sidebar.py                  # 公共侧边栏
│   │   └── system_status.py            # 模块状态卡片
│   └── pages/                          # 15个功能页面
│       ├── 01_🏠_系统概览.py
│       ├── 02_📊_实时监控.py
│       ├── 03_🔄_再平衡执行.py          # AI量化再平衡 ⭐
│       ├── 04_📈_投资组合优化.py
│       ├── 05_🛡️_风险监控.py
│       ├── 06_💰_ETF资金流向.py
│       ├── 07_🌊_康波周期分析.py
│       ├── 08_🏛️_十五五规划.py
│       ├── 09_🏦_社保基金追踪.py
│       ├── 10_🔬_宏观综合分析.py         # 一键三大分析
│       ├── 11_💎_大宗商品监控.py
│       ├── 12_📝_报告管理.py
│       ├── 13_🤖_AI决策.py              # GLM5盘中AI决策 ⭐
│       ├── 14_📡_期货期权信号.py        # 期货期权信号 ⭐
│       └── 15_🏦_AI_Hedge_Fund.py       # AI Hedge Fund ⭐ v5.6
│
├── config/                             # 配置文件 (21个)
│   ├── portfolio.yaml                  # 组合配置 (14标的4板块)
│   ├── settings.yaml                   # 系统全局配置 (primary: wind, secondary: ifind)
│   ├── positions.json                  # 实时持仓状态
│   ├── price_history.jsonl             # 历史价格日志
│   ├── stop_loss_rules_auto.yaml       # 止损止盈规则
│   └── watchlist.yaml                  # 大炼化观察仓
│
├── 每日报告归档/YYYY-MM-DD/            # 日报归档
├── reports/                            # 分析报告
├── data/                               # 本地数据缓存
├── scripts/                            # 脚本工具
│   ├── generate_2026_plan.py
│   └── portfolio_5year_forecast.py
├── trade_logs/                         # 交易日志
├── logs/                               # 系统日志
├── .streamlit/config.toml              # 暗色主题配置
│
├── 启动UI面板.bat                       # Streamlit UI启动
├── 启动量化系统.bat                     # 量化系统启动
├── 启动全部模块.bat                     # 统一启动器
├── 启动实时监控.bat                     # 实时监控
├── 启动AI决策UI.bat                     # AI决策面板
├── 自动盘前计划.bat                     # 每日盘前计划
├── run_rebalance.bat                    # 简单再平衡
├── start_futures_ai_trader.bat         # 期货AI交易员
│
├── README.md                           # ← 本文件
├── CLAUDE.md                           # Claude Code指导
├── AGENTS.md                           # Codex指导
├── SECURITY.md                         # 安全策略
└── run_ui.py                           # UI启动脚本
```

---

## 五、核心模块

### 5.1 AI Hedge Fund — 19位大师级分析师 ⭐ v5.6

**文件**: `quant_modules/ai_hedge_fund/`

19个AI分析师Agent, LangGraph编排工作流, 涵盖:
- **价值投资**: 巴菲特、格雷厄姆、费雪风格
- **成长投资**: 凯瑟琳·伍德、彼得·林奇风格
- **宏观分析**: 达利奥、索罗斯、德鲁肯米勒风格
- **技术分析**: 约翰·墨菲、威科夫风格
- **量化因子**: 动量、波动率、质量等多因子
- **风险管理**: 风险预算、压力测试、尾部风险
- **最终决策**: 多分析师投票 + 置信度加权综合

使用: `python "量化策略系统 v5.6.py" --ai-hedge`

### 5.2 AI量化再平衡引擎

**文件**: `quant_modules/ai_rebalancing_engine.py`

整合四大理论引擎信号 + DeepSeek LLM智能决策 + 动态仓位计算 + 差异化止损

### 5.3 每日盘前再平衡流水线 ⭐

**文件**: `daily_pre_market.py`

四步流水线: XGBoost 5日方向预测 → 风险平价回测 → FinBERT情感分析 → 三源信号合成 → 生成MD报告

### 5.4 盘中AI决策调度器 ⭐ v5.2

**文件**: `auto_intraday_decision.py`

GLM5 AI模型中交易时段定时调用, 生成实时交易决策信号。

### 5.5 期货期权信号系统

**文件**: `signals/futures_options_signal.py`

数据流: 宏观经济量化 → 期货信号 (铁矿石/原油/黄金) → 期权信号 (ETF期权) → AI决策 → 交易建议

### 5.6 数据获取 (P0-P5优先级链)

| 优先级 | 数据源 | 文件 | 覆盖 |
|--------|--------|------|------|
| P0 | Wind MCP | `quant_modules/wind_mcp.py` | 主数据源, CLI调用 |
| P1 | iFinD MCP | `ifind_client.py` | 强制回退, 同花顺 |
| P2 | AKShare/efinance/tushare | 内联 | 免费回退层 |
| P3 | 新浪财经 API | `sina_api_helper.py` | 免费实时行情 |
| P4 | 本地缓存 (Parquet/JSON) | `quant_modules/data_layer.py` | 最近成功缓存 |
| P5 | 预定义兜底价格 | `quant_modules/core.py` | 永不崩溃保障 |

**强制规则**: Wind不可用时必须尝试iFinD, 不可直接跳到免费数据源。

---

## 六、持仓配置

### 6.1 权益组合 (14标的4板块)

| 板块 | 权重 | 标的 |
|------|------|------|
| 高端制造(含算力) | 45% | 中际旭创/海光信息/北方华创/中芯国际/宁德时代/徐工机械 |
| 顺周期 | 20% | 中国神华/南山铝业/宝钢股份 |
| 资源 | 20% | 华安黄金ETF/藏格矿业 |
| 防御 | 15% | 恒瑞医药/药明康德/科伦药业 |

### 6.2 期货期权信号 (动态生成)

当前支持: 铁矿石期货、原油期货、黄金期货 + 沪深300ETF期权、上证50ETF期权

---

## 七、风控体系

### 7.1 三级风控

| 级别 | 触发条件 | 操作 |
|------|----------|------|
| 一级 | 个股触发差异化止损 | 自动止损卖出 |
| 二级 | 组合回撤达5%/8%/15% | 降仓至70%/50%/清仓 |
| 三级 | 单日回撤-3%/-5% | 停止买入/强制减仓 |

### 7.2 止损规则

| 类别 | 止损线 |
|------|--------|
| 核心宽基ETF | -8% |
| 科技成长个股 | -10% ~ -15% |
| 高端制造 | -10% ~ -12% |
| 防御/红利 | -8% |
| 黄金ETF | -8% / -12% |

---

## 八、Streamlit 监控面板

启动: `streamlit run ui/app.py` (端口 8501)

15个功能页面, 分组导航:

| 页面 | 功能 |
|------|------|
| 系统概览 | 持仓总览、收益统计、16模块状态、连接器状态 |
| 实时监控 | 盘中行情、异动提醒、净值曲线、标的搜索 |
| 再平衡执行 | AI量化再平衡、Excel驱动买卖计划、止损止盈 |
| 投资组合优化 | 5策略对比 (等权/风险平价/风险配比/因子/自定义) |
| 风险监控 | 回撤监控、止损止盈状态、风险权重分布 |
| ETF资金流向 | 24ETF监控、国家队信号、风格轮动 |
| 康波周期分析 | 长周期定位、行业配置、商品信号 |
| 十五五规划 | 7大战略方向、持仓适配评级、权重调整 |
| 社保基金追踪 | 4大风格、ETF映射、资金流增强 |
| 宏观综合分析 | 一键三大分析 (康波+十五五+社保ETF) |
| 大宗商品监控 | 商品价格/趋势/预警、宏观指标 |
| 报告管理 | 浏览/搜索/预览/下载历史报告 |
| AI决策 | GLM5盘中AI实时决策面板 |
| 期货期权信号 | 期货期权信号生成与监控 |
| AI Hedge Fund | 19位AI分析师联合决策 ⭐ v5.6 |

暗色主题: `primaryColor: #1890FF`, `backgroundColor: #0d1117` (GitHub风格)

---

## 九、数据源优先级

全局统一标准: **Wind MCP (P0) → iFinD MCP (P1) → 免费数据源 (P2) → 新浪API (P3) → 本地缓存 (P4) → 兜底价格 (P5)**

所有报告/采集器/交易模块必须遵循此优先级链, 优雅降级, 不因上层数据源不可用而崩溃。`config/settings.yaml` 为全局配置源。

---

## 十、版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v5.6 | 2026-06-24 | AI Hedge Fund (19位分析师+LangGraph) ⭐; 期货期权信号系统上线 |
| v5.5 | 2026-06-21 | AI量化再平衡引擎、四大理论引擎、期货期权扫描器 |
| v5.2 | 2026-06-18 | DeepSeek V4 Pro LLM决策引擎接入; GLM5盘中AI决策; modes/模块化 |
| v5.1 | 2026-06 | 康波+十五五+社保ETF三大分析模块; Streamlit UI暗色主题 |

---

## 十一、相关文档

| 文件 | 说明 |
|------|------|
| `CLAUDE.md` | Claude Code项目指导 |
| `AGENTS.md` | Codex/Agent项目指导 |
| `CAREER_INVESTOR_GUIDE.md` | 职业投资者指南 |
| `期货期权信号集成指南.md` | 期货期权信号系统使用文档 |
| `GLM5_自动决策_使用指南.md` | GLM5 AI决策使用指南 |
| `SECURITY.md` | 安全策略 |

---

## 十二、License

MIT License — 仅供学习研究使用, 不构成投资建议。所有交易决策请咨询持牌金融顾问。
