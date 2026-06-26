# 量化策略系统 v5.7

> **AI驱动的多策略量化投资组合管理系统**
>
> 策略: 风险平价 + 核心-卫星 + 动量择时 + ML涨跌预测 | 数据源: Wind MCP（优先）→ iFinD → 新浪 → AKShare → 本地缓存 | LLM: 本地 Ollama Qwen2.5:7B + 豆包 Speed

---

## 一、快速开始

### 1.1 环境要求

- Python ≥ 3.8（推荐 3.10+）
- Node.js ≥ 18（Wind MCP CLI）
- Ollama ≥ 0.30（本地 LLM 推理，需下载安装）
- Streamlit ≥ 1.30
- scikit-learn ≥ 1.0
- xgboost ≥ 2.0（ML模型训练）
- lightgbm ≥ 4.0（ML模型训练）

### 1.2 安装依赖

```bash
# 基础依赖
pip install numpy pandas pyyaml streamlit openpyxl python-dotenv requests yfinance plotly scikit-learn scipy

# ML模型训练依赖（推荐）
pip install xgboost lightgbm

# AI Hedge Fund 依赖（可选）
pip install langgraph langchain langchain-openai
```

### 1.3 配置 API Key

创建 `.env` 文件：

```bash
# Wind MCP API Key（金融数据主源）
WIND_API_KEY=your_wind_api_key_here

# iFinD MCP Token（备选数据源）
IFIND_TOKEN=your_ifind_token_here

# Tushare Token（期货数据）
TS_TOKEN=your_ts_token_here

# ---- LLM 配置（AI Hedge Fund / AI 决策引擎） ----
# 推荐：本地 Ollama Qwen2.5（免费，无需联网）
AI_HEDGE_MODEL=qwen2.5:7b
AI_HEDGE_PROVIDER=Ollama
OLLAMA_BASE_URL=http://localhost:11434

# 备选：豆包 Speed（云端，需 API Key）
VOLCENGINE_API_KEY=your_volcengine_api_key_here
VOLCENGINE_MODEL=doubao-speed-32k

# 报告输出目录
REPORT_OUTPUT_DIR=./每日报告归档

# 日志级别
LOG_LEVEL=INFO
```

---

## 二、主程序 CLI 模式（19种运行模式）

主程序入口：`量化策略系统 v5.7.py`

```bash
python "量化策略系统 v5.7.py" --<模式> [选项]
```

### 2.1 基础模式

| 模式 | 说明 | 示例 |
|------|------|------|
| `--live` | 实时监控模式（盘中行情监控） | `python 量化策略系统 v5.7.py --live` |
| `--report` | 报告生成模式 | `python 量化策略系统 v5.7.py --report` |
| `--check` | 系统健康检查 | `python 量化策略系统 v5.7.py --check` |
| `--risk` | 风险监控模式（止损止盈状态） | `python 量化策略系统 v5.7.py --risk` |

### 2.2 再平衡模式

```bash
# 执行再平衡（Excel驱动）
python "量化策略系统 v5.7.py" --rebalance

# 再平衡 + 同步止损止盈规则
python "量化策略系统 v5.7.py" --rebalance --sync-sl
```

### 2.3 三阶段工作流

```bash
# 盘前计划
python "量化策略系统 v5.7.py" --daily --phase premarket

# 盘中策略
python "量化策略系统 v5.7.py" --daily --phase intraday

# 盘后报告
python "量化策略系统 v5.7.py" --daily --phase postmarket

# 完整三阶段（盘前 → 盘中 → 盘后）
python "量化策略系统 v5.7.py" --daily --phase all
```

### 2.4 ETF资金流向监控

```bash
python "量化策略系统 v5.7.py" --etf-flow
```

### 2.5 投资组合优化

```bash
python "量化策略系统 v5.7.py" --portfolio-opt
```

### 2.6 康波周期监控

```bash
python "量化策略系统 v5.7.py" --kommo-monitor
```

### 2.7 大宗商品基本面

```bash
python "量化策略系统 v5.7.py" --commodity-fund
```

### 2.8 时序预测训练

```bash
python "量化策略系统 v5.7.py" --train-model
```

### 2.9 康波周期+十五五交叠分析

```bash
python "量化策略系统 v5.7.py" --kondratiev
```

### 2.10 十五五规划适配分析

```bash
python "量化策略系统 v5.7.py" --fifteen-five
```

### 2.11 社保基金ETF风格追踪

```bash
python "量化策略系统 v5.7.py" --social-security
```

### 2.12 宏观综合分析（一键三大）

```bash
python "量化策略系统 v5.7.py" --macro-analysis
```

### 2.13 AI盘中实时决策

```bash
python "量化策略系统 v5.7.py" --ai-decision
```

### 2.14 期货期权扫描

```bash
python "量化策略系统 v5.7.py" --futures-options
```

### 2.15 统一监控模式（一键启动所有模块）

```bash
python "量化策略系统 v5.7.py" --unified-monitor
```

### 2.16 AI Hedge Fund（19位大师级AI分析师）

```bash
# 基础用法
python "量化策略系统 v5.7.py" --ai-hedge

# 指定股票代码
python "量化策略系统 v5.7.py" --ai-hedge --ticker 600519 000858

# 选择特定分析师
python "量化策略系统 v5.7.py" --ai-hedge --analysts warren_buffett charlie_munger

# 显示分析推理过程
python "量化策略系统 v5.7.py" --ai-hedge --show-reasoning
```

### 2.17 ML模型预测信号 ⭐ NEW

```bash
# 基础用法（默认阈值 55%）
python "量化策略系统 v5.7.py" --ml-signal

# 自定义信号阈值（提高置信度要求）
python "量化策略系统 v5.7.py" --ml-signal --threshold 0.6

# 保存报告到指定文件
python "量化策略系统 v5.7.py" --ml-signal -o ML信号报告.md
```

**输出示例**:
```
模型: GradientBoosting
准确率: 56.34% | F1: 0.6370
扫描标的: 32 只 | 阈值: 55.00%

🟢 买入信号: 13 只
🔴 卖出信号: 16 只
🟡 持有观望: 2 只
```

### 2.18 回测模式

```bash
python "量化策略系统 v5.7.py" --backtest

# 指定时间范围
python "量化策略系统 v5.7.py" --backtest --start-date 2025-01-01 --end-date 2026-06-26
```

### 2.19 通用选项

| 选项 | 说明 |
|------|------|
| `--output`, `-o` | 指定输出报告文件名 |
| `--no-ai` | 禁用AI分析模块 |
| `--sync-sl` | 同步止损止盈规则（配合 --rebalance） |
| `--threshold` | ML信号阈值（配合 --ml-signal，默认0.55） |

---

## 三、ML模型训练

### 3.1 基础训练（4个模型，9个特征）

```bash
python auto_train.py
```

训练模型：RandomForest、GradientBoosting、LogisticRegression、SVM

### 3.2 增强训练（6个模型，42个特征）⭐

```bash
# 标准增强训练
python auto_train_enhanced.py

# 增强训练 + PCA降维（8个主成分）
python auto_train_enhanced.py --pca --pca-components 8
```

训练模型：RandomForest、GradientBoosting、LogisticRegression、ExtraTrees、XGBoost、LightGBM

### 3.3 优化版训练（特征选择+超参数调优）⭐⭐

```bash
python auto_train_optimized.py
```

**特性**:
- SelectKBest 特征选择（Top 20特征）
- GridSearchCV 超参数调优
- 自动保存最佳模型和元数据

### 3.4 训练输出

训练完成后，模型文件保存在 `models/` 目录：

```
models/
├── training_metadata_optimized_YYYYMMDD_HHMMSS.json  # 训练元数据
├── feature_selector_YYYYMMDD_HHMMSS.pkl              # 特征选择器
├── GradientBoosting_YYYYMMDD_HHMMSS.pkl              # GradientBoosting模型
├── XGBoost_tuned_YYYYMMDD_HHMMSS.pkl                 # XGBoost调优模型
├── LightGBM_tuned_YYYYMMDD_HHMMSS.pkl                # LightGBM调优模型
└── ...
```

### 3.5 模型性能对比

| 模型 | 准确率 | F1分数 | AUC | 特征数 |
|------|--------|--------|-----|--------|
| GradientBoosting（优化版） | **56.34%** | **0.6370** | 0.5806 | 20 |
| GradientBoosting（增强版） | 55.18% | 0.6240 | - | 42 |
| LogisticRegression（PCA版） | 55.70% | - | - | 8 (PCA) |

---

## 四、目录结构

```
11_量化策略/
├── 量化策略系统 v5.7.py                # 主程序入口（19种CLI模式）⭐
├── ui/                                 # Streamlit多页面UI
│   ├── app.py                          # Streamlit主入口
│   ├── components/                     # UI组件
│   │   ├── names.py                    # 共享标的名称映射
│   │   ├── progress.py                 # 进度组件
│   │   ├── report_viewer.py            # 报告浏览/预览
│   │   ├── sidebar.py                  # 公共侧边栏
│   │   └── system_status.py            # 模块卡片/连接器状态
│   └── pages/                          # 12个功能页面
│       ├── 01_🏠_系统概览.py
│       ├── 02_📊_实时监控.py
│       ├── 03_🔄_再平衡执行.py
│       ├── 04_📈_投资组合优化.py
│       ├── 05_🛡️_风险监控.py
│       ├── 06_💰_ETF资金流向.py
│       ├── 07_🌊_康波周期分析.py
│       ├── 08_🏛️_十五五规划.py
│       ├── 09_🏦_社保基金追踪.py
│       ├── 10_🔬_宏观综合分析.py
│       ├── 11_💎_大宗商品监控.py
│       └── 12_📝_报告管理.py
├── utils/                              # 核心工具模块
│   ├── kondratiev_cycle.py             # 康波周期分析 v2.0
│   ├── five_year_plan.py               # 十五五规划适配
│   ├── social_security_etf.py          # 社保基金ETF追踪
│   ├── logging_manager.py              # 统一日志
│   ├── event_tracker.py                # 事件追踪
│   ├── data_source_manager.py          # 多源自适应数据源
│   ├── ml_predictor.py                 # ML模型预测模块 ⭐ NEW
│   └── report_archiver.py              # 报告归档工具
├── quant_modules/                      # 核心量化模块
│   ├── ai_hedge_fund/                  # AI Hedge Fund（19位分析师）
│   │   ├── agents/                     # 分析师Agent
│   │   ├── llm/                        # LLM配置
│   │   └── orchestrator.py             # 编排器
│   ├── ai_rebalancing_engine.py        # AI量化再平衡引擎
│   ├── decision_theories.py            # 四大理论引擎
│   ├── futures_options_scanner.py      # 期货期权扫描器
│   ├── wind_mcp.py                     # Wind MCP CLI封装
│   ├── data_layer.py                   # 缓存+连接器
│   └── core.py                         # 配置/异常/成本计算
├── engine/                             # 回测与策略引擎
│   ├── data.py                         # 统一数据层
│   ├── rebalance.py                    # 再平衡引擎
│   ├── managers.py                     # 组合优化/康波/ETF管理器
│   ├── etf_flow.py                     # ETF资金流监控
│   └── social_security.py              # 社保基金风格追踪
├── config/                             # 配置文件
│   ├── portfolio.yaml                  # 组合配置（14标的4板块）
│   ├── settings.yaml                   # 系统全局配置
│   ├── positions.json                  # 实时持仓状态
│   ├── stop_loss_rules_auto.yaml       # 止损止盈规则
│   └── watchlist.yaml                  # 观察仓配置
├── models/                             # ML模型输出目录 ⭐ NEW
│   └── *.pkl / *.json                  # 训练好的模型和元数据
├── data/                               # 数据缓存
│   └── cache/                          # K线数据缓存
├── reports/                            # 生成的报告
├── scripts/                            # 脚本工具
├── auto_train.py                       # 基础版训练脚本
├── auto_train_enhanced.py              # 增强版训练脚本 ⭐
├── auto_train_optimized.py             # 优化版训练脚本 ⭐⭐
├── backtest_engine.py                  # 回测引擎
├── run_ui.py                           # UI启动脚本
├── 启动UI面板.bat                      # UI启动批处理
└── .streamlit/config.toml              # 暗色主题配置
```

---

## 五、本地 LLM 部署（Ollama + Qwen2.5）

本项目支持本地 LLM 推理，无需云端 API Key，数据不出本机。

### 5.1 安装 Ollama

从 [ollama.com](https://ollama.com/download) 下载安装，或使用包管理器：

```bash
# Windows: 下载安装程序，建议将模型目录设到大容量盘符
# 安装后设置模型存储路径（不占 C 盘）
setx OLLAMA_MODELS "D:\Ollama\models"
```

### 5.2 拉取模型

```bash
# 推荐 7B（~4.7GB，8GB RAM 可运行）
ollama pull qwen2.5:7b

# 进阶 14B（~9GB，需 16GB+ RAM）
ollama pull qwen2.5:14b
```

### 5.3 启动服务

```bash
# 启动 Ollama 服务（默认监听 127.0.0.1:11434）
ollama serve

# 如遇 CUDA 兼容问题（RTX 3060 等），强制 CPU 模式
set OLLAMA_NUM_GPU=0 && ollama serve
```

### 5.4 验证可用

```bash
ollama list
# 输出示例:
# NAME            ID              SIZE      MODIFIED
# qwen2.5:7b      xxxxxxxx        4.7 GB    2 minutes ago
# qwen2.5:14b     xxxxxxxx        9.0 GB    5 minutes ago
```

### 5.5 当前部署状态

| 项目 | 状态 |
|------|------|
| Ollama 版本 | v0.30.9 |
| 安装位置 | C:\Users\...\Programs\Ollama\ |
| 模型存储 | D:\Ollama\models（不占 C 盘） |
| 可用模型 | qwen2.5:7b（~26s/次 CPU）、qwen2.5:14b（已下载，需更多内存） |
| GPU 支持 | RTX 3060（6GB）暂不可用，需编译自定义 Ollama CUDA 版本 |

### 5.6 切换 LLM 提供方

在 `.env` 中修改：

```bash
# 本地 Ollama（默认）
AI_HEDGE_PROVIDER=Ollama
AI_HEDGE_MODEL=qwen2.5:7b

# 云端豆包
AI_HEDGE_PROVIDER=Volcengine
AI_HEDGE_MODEL=doubao-speed-32k

# OpenAI 兼容接口（vLLM / LM Studio 等）
AI_HEDGE_PROVIDER=OpenAI
AI_HEDGE_MODEL=qwen2.5-14b-instruct
OPENAI_API_BASE=http://localhost:8000/v1
```

---

## 六、核心模块

### 6.1 ML模型预测模块 ⭐ NEW

**文件**: `utils/ml_predictor.py`

**功能**:
- 自动发现最新训练的模型
- 特征工程（42个技术特征 → 20个选择特征）
- 批量预测（支持多标的同时预测）
- 交易信号生成（买入/卖出/持有）
- 信号置信度评估

**使用**:
```python
from utils.ml_predictor import MLModelPredictor, run_ml_signal_scan

# 扫描所有标的生成信号
result = run_ml_signal_scan(
    data_dir='data/cache',
    model_dir='models',
    threshold=0.55
)

print(f"模型: {result['model_info']['best_model']}")
print(f"买入信号: {len(result['signals']['buy'])}")
print(f"卖出信号: {len(result['signals']['sell'])}")
```

### 6.2 AI Hedge Fund ⭐

**文件**: `quant_modules/ai_hedge_fund/orchestrator.py`

**功能**:
- 19位大师级AI分析师联合决策
- 价值投资、成长投资、逆向投资等多策略
- 基本面分析、技术分析、情绪分析
- 风险评估与仓位建议
- **支持本地 Ollama Qwen2.5 推理**（无需云端 API）

**LLM 后端**: 本地 Ollama Qwen2.5:7B（默认）| 豆包 Speed | OpenAI 兼容接口

**支持的分析师**:
| 分析师 | 投资风格 |
|--------|----------|
| Warren Buffett | 价值投资 |
| Charlie Munger | 多元思维模型 |
| Peter Lynch | 成长投资 |
| Benjamin Graham | 价值投资之父 |
| Michael Burry | 逆向投资 |
| Cathie Wood | 颠覆性创新 |
| Stanley Druckenmiller | 宏观对冲 |
| Bill Ackman | 激进投资 |
| ... | ... |

### 6.3 AI量化再平衡引擎

**文件**: `quant_modules/ai_rebalancing_engine.py`

**功能**:
- 整合四大理论引擎信号
- DeepSeek LLM智能决策
- 动态仓位计算
- 止损规则（按类别差异化）
- 信号聚合与置信度评估

### 6.4 四大理论引擎

| 理论 | 核心思想 | 输出信号 |
|------|----------|----------|
| 索罗斯反身性 | 市场偏见 → 价格扭曲 → 趋势反转 | 反转信号 |
| 瑞达利奥经济机器 | 债务周期 → 经济阶段 → 资产配置 | 配置信号 |
| 第一性原理 | 基本面 → 内在价值 → 安全边际 | 价值信号 |
| 巴菲特芒格 | 护城河 → 长期持有 → 复利增长 | 持有信号 |

### 6.5 期货期权信号系统

**文件**: `signals/futures_options_signal.py`

**功能**:
- 宏观经济量化分析
- 期货信号生成（铁矿石/原油/黄金等）
- 期权信号生成（沪深300/上证50等ETF期权）
- AI决策引擎（置信度评估/仓位计算/风险管理）

### 6.6 数据获取（优先级链）

| 优先级 | 数据源 | 覆盖 | 说明 |
|--------|--------|------|------|
| P0 | Wind MCP | 100% | 主数据源，CLI调用 |
| P1 | iFinD MCP | 95% | 强制回退 |
| P2 | AKShare | 80% | 免费数据源 |
| P3 | 新浪财经 | 70% | 免费HTTP接口 |
| P4 | yfinance | 60% | 国际品种 |
| P5 | 本地缓存 | - | 最近成功数据 |
| P6 | 兜底价格 | - | 确保永不崩溃 |

---

## 七、持仓配置

### 7.1 权益组合（14标的 + 现金）

| 板块 | 标的数 | 权重 | 标的示例 |
|------|--------|------|----------|
| 高端制造(含算力) | 6 | 45% | 中际旭创/海光信息/北方华创/中芯国际/宁德时代/徐工机械 |
| 顺周期 | 3 | 20% | 中国神华/南山铝业/宝钢股份 |
| 资源 | 2 | 20% | 华安黄金ETF/藏格矿业 |
| 防御 | 3 | 15% | 恒瑞医药/药明康德/科伦药业 |

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

### 8.1 启动方式

```bash
# 方式1: Streamlit直接启动
streamlit run ui/app.py --server.port 8501

# 方式2: 使用批处理文件
启动UI面板.bat

# 方式3: Python脚本
python run_ui.py
```

### 8.2 访问地址

- Local: http://localhost:8501
- Network: http://192.168.0.105:8501

### 8.3 功能页面

| 页面 | 功能 |
|------|------|
| 系统概览 | 16模块状态 + 连接器 + 配置检查 |
| 实时监控 | 持仓饼图 + 权重偏差 + 净值曲线 + 标的搜索 |
| 再平衡执行 | 5 Excel表驱动 - 买卖计划 + 止损止盈 |
| 投资组合优化 | 5策略对比(等权/风险平价/风险配比/因子/自定义) |
| 风险监控 | 止损止盈状态(🔴🟡🟢) + 风险权重分布 |
| ETF资金流向 | 24ETF监控 + 国家队信号 + 风格轮动 |
| 康波周期分析 | 周期阶段 + 行业配置 + 商品信号 |
| 十五五规划 | 7大战略方向 + 持仓适配评级 + 权重调整 |
| 社保基金追踪 | 4大风格 + ETF映射 + 资金流增强 |
| 宏观综合分析 | 一键三大分析(康波+十五五+社保ETF) |
| 大宗商品监控 | 商品价格/趋势/预警 + 宏观指标 |
| 报告管理 | 浏览/搜索/预览/下载历史报告 |

### 8.4 暗色主题

```toml
[theme]
base = "dark"
primaryColor = "#1890FF"
backgroundColor = "#0d1117"
secondaryBackgroundColor = "#161b22"
textColor = "#e6edf3"
```

---

## 九、版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v5.7 | 2026-06-26 | **本地 Ollama Qwen2.5:7B LLM 部署** ⭐、模型存储 D 盘隔离 |
| v5.6 | 2026-06-26 | ML模型预测信号系统、AI Hedge Fund |
| v5.5 | 2026-06-21 | AI量化再平衡引擎、四大理论引擎、期货期权扫描器 |
| v5.2 | 2026-06-18 | DeepSeek V4 Pro LLM决策引擎接入 |
| v5.1 | 2026-06 | 康波+十五五+社保ETF三大分析模块 |

---

## 十、常用脚本

### 10.1 数据处理

```bash
# 补全缺失K线数据
python download_missing_klines.py

# 检查K线完整性
python check_kline_complete.py

# 获取新浪实时价格
python get_sina_prices.py
```

### 10.2 回测

```bash
# 3年回测
python backtest_3year.py

# 快速回测
python fast_backtest.py

# 回测引擎
python backtest_engine.py
```

### 10.3 分析

```bash
# 持仓统计
python position_stats.py

# ETF资金流向
python 实时ETF资金流向.py

# 宏观分析
python macro_analysis.py

# 康波周期分析
python kontratieff_cycle.py

# 五年收益预测
python 五年收益预测.py
```

### 10.4 风控

```bash
# 止损监控
python stop_loss_monitor.py

# 风险预警
python risk_early_warning.py
```

---

## 十一、相关文件

| 文件 | 说明 |
|------|------|
| `BACKTEST_FIX_LOG.md` | 回测修复记录 |
| `CAREER_INVESTOR_GUIDE.md` | 职业投资者指南 |
| `LSEG_INTEGRATION_GUIDE.md` | LSEG数据集成指南 |
| `期货期权信号集成指南.md` | 期货期权信号系统使用文档 |
| `GLM5_自动决策_使用指南.md` | GLM5自动决策使用指南 |

---

## 十二、License

MIT License - 仅供学习研究使用，不构成投资建议。
