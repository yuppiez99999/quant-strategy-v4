# 量化策略系统 v5.6

> **AI驱动的多策略量化投资组合管理系统**
>
> 总资金: ¥76,682,514 | 持仓市值: ¥36,682,514 | 国债逆回购: ¥40,000,000
>
> 策略: 风险平价 + 核心-卫星 + 动量择时 | 数据源: Wind MCP（优先）→ 新浪 → AKShare → 本地缓存

---

## 一、快速开始

### 1.1 环境要求

- Python ≥ 3.10
- Node.js ≥ 18（Wind MCP CLI）
- Streamlit ≥ 1.30
- scikit-learn ≥ 1.0（期货期权信号分析）

### 1.2 安装依赖

```bash
pip install numpy pandas pyyaml streamlit openpyxl python-dotenv requests yfinance plotly scikit-learn scipy
```

### 1.3 配置 API Key

创建 `.env` 文件：

```bash
# DeepSeek V4 Pro API（LLM决策引擎）
DEEPSEEK_API_KEY=47afd46f84e74f5d9b6faaa8cb1705f9.yb0Fk33H0QxVWWvr

# Wind MCP API Key（金融数据主源）
WIND_API_KEY=<your-wind-api-key>
```

---

## 二、常用命令

### 2.1 启动监控面板

```bash
# 启动 Streamlit 监控面板（推荐）
streamlit run ui/app.py

# 或使用批处理文件
启动UI面板.bat
```

### 2.2 日报生成

```bash
# 盘后综合报告
python daily_trading_workflow.py --phase postmarket

# 盘中实时监控
python daily_trading_workflow.py --phase intraday

# 三阶段工作流（盘前 → 盘中 → 盘后）
python daily_trading_workflow.py --phase all

# 每日量化报告
python 11_quant_daily_report.py
```

### 2.3 AI再平衡

```bash
# 自动再平衡（含DeepSeek LLM决策）
python auto_trading_system.py

# AI量化再平衡引擎（替代Excel驱动）
python -c "from quant_modules.ai_rebalancing_engine import run_ai_rebalance; print(run_ai_rebalance({}, {}))"

# 简单再平衡
python simple_rebalance.py
```

### 2.4 四大理论分析

```bash
# 运行四大理论引擎
python -c "from quant_modules.decision_theories import run_full_theory_analysis; run_full_theory_analysis({})"
```

### 2.5 期货期权信号系统 ⭐ NEW

```bash
# 方法1: 独立运行信号生成器
python signals/futures_options_signal.py

# 方法2: 附加到综合日报
python append_futures_to_daily.py

# 方法3: 完整集成流程
python integrate_futures_options.py --append-to-report
```

**功能说明:**
- 宏观经济量化分析 (实体经济/宏观健康/市场情绪/商品周期)
- 期货信号生成 (铁矿石/原油/黄金等)
- 期权信号生成 (沪深300/上证50等ETF期权)
- AI决策引擎 (置信度评估/仓位计算/风险管理)
- 自动生成交易建议报告

**输出:**
- 独立报告: `signals/reports/期货期权决策_YYYY-MM-DD.md`
- 综合日报: `每日报告归档/YYYY-MM-DD/综合日报_YYYYMMDD.txt` (已附加)

### 2.6 期货期权扫描

```bash
# 期货期权套利机会扫描
python -c "from quant_modules.futures_options_scanner import scan_all; scan_all()"
```

### 2.7 五年收益预测

```bash
# 生成五年收益预测报告
python 五年收益预测.py
```

### 2.8 回测

```bash
# 3年回测
python backtest_3year.py

# 快速回测
python fast_backtest.py
```

### 2.9 其他常用命令

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

# 期货期权信号 (NEW)
python signals/futures_options_signal.py
```

---

## 三、目录结构

```
11_量化策略/
├── quant_modules/                      # 核心量化模块
│   ├── ai_rebalancing_engine.py        # AI量化再平衡引擎 ⭐
│   ├── decision_theories.py            # 四大理论引擎 ⭐
│   ├── futures_options_scanner.py      # 期货期权扫描器 ⭐
│   ├── wind_mcp.py                     # Wind MCP CLI封装
│   ├── data_layer.py                   # 缓存+连接器
│   ├── core.py                         # 配置/异常/成本计算
│   ├── prediction_bridge.py            # 预测信号桥接器
│   └── dynamic_position.py             # 动态仓位管理
├── signals/                            # 交易信号生成器 ⭐ NEW
│   ├── futures_options_signal.py       # 期货期权AI信号生成器 ⭐
│   ├── token_risk_factor.py            # Token风险因子
│   ├── token_auto_capacity.py          # 自动容量因子
│   ├── token_factor_combiner.py        # 因子组合器
│   └── reports/                        # 信号报告目录
│       └── 期货期权决策_YYYY-MM-DD.md
├── engine/
│   ├── data.py                         # 统一数据层
│   ├── rebalance.py                    # 再平衡引擎
│   ├── managers.py                     # 组合优化/康波/ETF管理器
│   ├── etf_flow.py                     # ETF资金流监控
│   └── social_security.py              # 社保基金风格追踪
├── ui/
│   ├── app.py                          # Streamlit主入口
│   ├── components/                     # UI组件
│   └── pages/                          # 12个功能页面
│       ├── 01_🏠_系统概览.py
│       ├── 02_📊_实时监控.py
│       ├── 03_🔄_再平衡执行.py          # AI量化再平衡 ⭐
│       ├── 04_📈_投资组合优化.py
│       ├── 05_🛡️_风险监控.py
│       ├── 06_💰_ETF资金流向.py
│       ├── 07_🌊_康波周期分析.py
│       ├── 08_🏛️_十五五规划.py
│       ├── 09_🏦_社保基金追踪.py
│       ├── 10_🔬_宏观综合分析.py
│       ├── 11_💎_大宗商品监控.py
│       └── 12_📝_报告管理.py
├── utils/
│   ├── kondratiev_cycle.py             # 康波周期分析
│   ├── five_year_plan.py               # 十五五规划适配
│   ├── social_security_etf.py          # 社保ETF追踪
│   └── logging_manager.py              # 统一日志
├── config/
│   ├── settings.yaml                   # 全局参数配置
│   └── positions.json                  # 实时持仓数据
├── reports/                            # 生成的报告
├── data/                               # 数据缓存
├── scripts/                            # 脚本工具
├── append_futures_to_daily.py          # 快速附加期货期权信号 ⭐ NEW
├── integrate_futures_options.py        # 完整集成脚本 ⭐ NEW
└── 期货期权信号集成指南.md              # 使用文档 ⭐ NEW
```

---

## 四、核心模块

### 4.1 AI量化再平衡引擎 ⭐

**文件**: `quant_modules/ai_rebalancing_engine.py`

**功能**:
- 整合四大理论引擎信号
- DeepSeek LLM智能决策
- 动态仓位计算
- 止损规则（按类别差异化）
- 信号聚合与置信度评估

**使用**:
```python
from quant_modules.ai_rebalancing_engine import run_ai_rebalance

result = run_ai_rebalance(positions, prices)
print(f"交易信号: {result.signals}")
print(f"LLM决策: {result.llm_decision}")
```

### 4.2 四大理论引擎 ⭐

| 理论 | 核心思想 | 输出信号 |
|------|----------|----------|
| 索罗斯反身性 | 市场偏见 → 价格扭曲 → 趋势反转 | 反转信号 |
| 瑞达利奥经济机器 | 债务周期 → 经济阶段 → 资产配置 | 配置信号 |
| 第一性原理 | 基本面 → 内在价值 → 安全边际 | 价值信号 |
| 巴菲特芒格 | 护城河 → 长期持有 → 复利增长 | 持有信号 |

### 4.3 期货期权信号系统 ⭐ NEW

**文件**: `signals/futures_options_signal.py`

**功能**:
- 宏观经济量化分析 (实体经济/宏观健康/市场情绪/商品周期)
- 期货信号生成 (铁矿石/原油/黄金等)
- 期权信号生成 (沪深300/上证50等ETF期权)
- AI决策引擎 (置信度评估/仓位计算/风险管理)
- 自动生成交易建议报告

**数据流**:
```
宏观经济量化系统 → 量化分析 → 信号生成 → AI决策 → 交易建议
```

**使用**:
```python
from signals.futures_options_signal import FuturesOptionsSignalGenerator

generator = FuturesOptionsSignalGenerator()
result = generator.run_full_pipeline()

print(f"生成信号数: {len(result['signals'])}")
print(f"AI建议数: {len(result['recommendations'])}")
```

**示例信号**:
```
【期货信号】2 个
  [WARN] 铁矿石期货 (i): 做空 (置信度: 75%)
  [OK] 原油期货 (sc): 持有/止盈 (置信度: 70%)

【期权信号】1 个
  [OK] 沪深300ETF期权 (510300): 买入看涨期权 (Call) (置信度: 80%)
```

### 4.4 期货期权扫描器

| 功能 | 说明 |
|------|------|
| 期货行情快照 | 主力合约价格、涨跌幅、成交量 |
| 期权扫描 | 隐含波动率、期权PCR、套利机会 |
| 跨品种套利 | 螺纹钢-热卷、豆粕-菜粕、PTA-乙二醇等 |
| AI分析 | DeepSeek V4 Pro衍生品策略建议 |

### 4.5 数据获取（Wind MCP优先）

| 优先级 | 数据源 | 覆盖 | 说明 |
|--------|--------|------|------|
| 0 | Wind MCP | 100% | 主数据源，CLI调用 |
| 1 | 新浪财经 | 备选 | 免费HTTP接口 |
| 2 | yfinance | 兜底 | 国际品种 |
| 3 | 模拟数据 | 最终保障 | 确保报告完整性 |

---

## 五、持仓配置（27只标的 + 期货期权）

### 5.1 权益组合（约3668万）

| 梯队 | 标的数 | 权重 | 金额 |
|------|--------|------|------|
| 核心宽基ETF | 5 | 28% | 84万 |
| 科技成长个股 | 6 | 20% | 60万 |
| 高端制造/基建 | 5 | 20% | 60万 |
| 防御/红利 | 4 | 15% | 45万 |
| 商品/避险 | 1 | 5% | 15万 |
| 现金缓冲 | 1 | 8% | 24万 |

### 5.2 低风险理财（4000万）

| 类型 | 金额 | 年化收益 |
|------|------|----------|
| 国债逆回购 | 4000万 | 2.8% |

### 5.3 期货期权信号系统

**当前生成的信号** (2026-06-24):
- 铁矿石期货: 做空 (置信度75%)
- 原油期货: 持有/止盈 (置信度70%)
- 沪深300ETF期权: 买入看涨 (置信度80%)

**AI交易建议**:
- 沪深300ETF期权 - 建议仓位4.00%
- 铁矿石期货 - 建议仓位2.25%
- 原油期货 - 建议仓位2.10%

---

## 六、五年收益预测

| 指标 | 数值 |
|------|------|
| 总账户初始 | ¥43,000,000 |
| 5年后基准资金 | ¥53,569,984 |
| 年化收益率 | 4.5% |
| 权益组合年化 | 18.0% |
| 低风险理财年化 | 3.2% |
| 累计收益率 | 24.6% |

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
| 科技成长个股 | -10%~-15% |
| 高端制造 | -10%~-12% |
| 防御/红利 | -8% |
| 黄金ETF | -8%/-12% |

---

## 八、Streamlit监控面板

启动命令：
```bash
streamlit run ui/app.py
```

访问地址：
- Local: http://localhost:8501
- Network: http://192.168.0.105:8501

### 功能页面

| 页面 | 功能 |
|------|------|
| 系统概览 | 持仓总览、收益统计、系统状态 |
| 实时监控 | 盘中行情、异动提醒 |
| 再平衡执行 | AI量化再平衡、交易信号 |
| 投资组合优化 | 权重优化、风险分析 |
| 风险监控 | 回撤监控、止损止盈 |
| ETF资金流向 | 主力资金、板块轮动 |
| 康波周期分析 | 长周期定位、资产配置 |
| 十五五规划 | 政策主题、投资机会 |
| 社保基金追踪 | 机构动向、风格漂移 |
| 宏观综合分析 | 经济指标、政策解读 |
| 大宗商品监控 | 商品期货、套利机会 |
| 报告管理 | 历史报告、PDF导出 |

---

## 九、版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v5.6 | 2026-06-24 | 期货期权信号系统上线 ⭐ NEW |
| v5.5 | 2026-06-21 | AI量化再平衡引擎、四大理论引擎、期货期权扫描器 |
| v5.2 | 2026-06-18 | DeepSeek V4 Pro LLM决策引擎接入 |
| v5.1 | 2026-06 | 康波+十五五+社保ETF三大分析模块 |

---

## 十、相关文件

| 文件 | 说明 |
|------|------|
| `2026年交易计划_优化版_v2.md` | 持仓配置详细说明 |
| `CAREER_INVESTOR_GUIDE.md` | 职业投资者指南 |
| `LSEG_INTEGRATION_GUIDE.md` | LSEG数据集成指南 |
| `期货期权信号集成指南.md` | 期货期权信号系统使用文档 ⭐ NEW |

---

## 十一、期货期权信号系统文档

详细使用说明请参考: [`期货期权信号集成指南.md`](期货期权信号集成指南.md)

**核心功能**:
- 宏观经济量化分析
- 期货/期权交易信号生成
- AI决策引擎
- 风险管理方案

**快速开始**:
```bash
# 独立运行
python signals/futures_options_signal.py

# 附加到综合日报
python append_futures_to_daily.py
```

---

## 十二、License

MIT License - 仅供学习研究使用，不构成投资建议。
