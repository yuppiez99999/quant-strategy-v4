# 量化策略系统 v5.7

> **AI驱动的多策略量化投资组合管理系统**
>
> 策略: 风险平价 + 核心-卫星 + 动量择时 + ML涨跌预测 + TrendCast Pro AI预测 | 数据源: Wind MCP（优先）→ iFinD → 新浪 → AKShare → 本地缓存 | LLM: 本地 Ollama Qwen2.5:7B + 豆包 Speed

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

### 2.20 每日自动化工作流（daily_runner）

`daily_runner.py` 是每日自动任务的主入口，由 Windows 计划任务触发或手动执行。

```bash
# 完整流程（数据下载 + 回测 + TrendCast AI预测 + 报告生成）
python daily_runner.py

# 跳过数据下载
python daily_runner.py --skip-download

# 跳过回测
python daily_runner.py --skip-backtest

# 报告后启动模拟交易
python daily_runner.py --trading

# 仅生成报告
python daily_runner.py --report-only

# 禁用AI分析
python daily_runner.py --no-ai

# 禁用 TrendCast AI 预测（默认开启）
python daily_runner.py --no-trendcast
```

**执行流程**（5步流水线）：

| 步骤 | 名称 | 说明 |
|------|------|------|
| 步骤1 | 数据更新 | 从 Wind MCP / iFinD / AKShare 下载最新行情 |
| 步骤2 | 快速回测 | 验证当前策略参数有效性 |
| 步骤2.5 | TrendCast AI预测 | 调用 TrendCast Pro API 获取14只核心持仓涨跌预测信号 ⭐ |
| 步骤3 | 每日报告 | 生成含 AI 分析的完整 Markdown 日报 |
| 步骤4 | 模拟交易（可选） | 启动盘中模拟交易 |

**TrendCast Pro 集成详情**：
- 默认开启（`enable_trendcast=True`），若 API 不可用则优雅降级跳过
- 批量预测 14 只核心持仓标的，输出看涨/看跌/中立信号 + 置信度
- 预测结果写入审计追踪（`logs/trendcast_audit/predictions.jsonl`）
- 到期后自动回溯验证命中率，模型漂移检测告警
- 信号通过 `quant_modules/prediction_bridge.py` 桥接到再平衡引擎

### 2.21 收盘报告（close_report_runner）

`close_report_runner.py` 每日收盘后自动生成持仓报告。

```bash
# 立即生成收盘报告
python close_report_runner.py

# 仅模拟运行，不保存
python close_report_runner.py --dry-run
```

---

## 三、ML模型训练系统

### 3.1 训练系统概览

本系统提供三级模型训练流水线，从简单到复杂逐步优化：

```
基础版 (auto_train.py)          4个模型 / 9个特征
    ↓
增强版 (auto_train_enhanced.py)  6个模型 / 42个特征 + PCA降维
    ↓
优化版 (auto_train_optimized.py) 6个模型 / 特征选择 + 超参数调优
```

**预测目标**: 下一日涨跌二分类（上涨/下跌）
**预测周期**: T+1 日收盘价相对 T 日收盘价的涨跌
**信号阈值**: 默认 55%（可配置）

---

### 3.2 训练数据

**数据来源**: K线历史数据（data/cache/ 目录下的 Parquet 文件）

| 数据项 | 说明 |
|--------|------|
| 数据量 | 32 只标的，44,837 条记录 |
| 时间跨度 | 2021-2026（约5年） |
| 数据字段 | 日期、开盘价、最高价、最低价、收盘价、成交量、成交额 |
| 最终样本 | 7,650 条有效样本（特征工程后） |

**数据文件格式**: Parquet
```python
# 列名映射
columns = {
    'date': '日期',
    'open': '开盘价',
    'high': '最高价',
    'low': '最低价',
    'close': '收盘价',
    'volume': '成交量',
    'amount': '成交额',
}
```

---

### 3.3 特征工程详解

#### 3.3.1 基础特征（9个）

| 特征类别 | 特征名称 | 说明 |
|----------|----------|------|
| 收益率 | returns | 日收益率 |
| 收益率 | log_returns | 对数收益率 |
| 收益率 | abs_returns | 绝对收益率 |
| 均线 | ma5_ma20 | 5日/20日均线交叉 |
| 波动率 | volatility_5 | 5日波动率 |
| 波动率 | volatility_20 | 20日波动率 |
| 动量 | momentum_10 | 10日动量 |
| 动量 | momentum_20 | 20日动量 |
| RSI | rsi_14 | 14日RSI |

#### 3.3.2 增强特征（42个）

扩展至6大类技术指标：

**1. 收益率类（4个）**
- returns, log_returns, abs_returns, returns_3

**2. 移动平均线类（8个）**
- ma5, ma10, ma20, ma60, ma5_ma10, ma5_ma20, ma20_ma60, price_ma20

**3. 波动率类（6个）**
- volatility_5, volatility_10, volatility_20, volatility_60, atr_14, range_ratio

**4. RSI 类（3个）**
- rsi_7, rsi_14, rsi_21

**5. MACD & 布林带（5个）**
- macd, macd_signal, macd_hist, boll_mid, boll_width

**6. 动量 & 趋势类（8个）**
- momentum_5, momentum_10, momentum_20, trend_5, trend_10, trend_20, ema_12, ema_26

**7. 成交量类（4个）**
- volume_ma5, volume_ma20, vwap, price_vwap_diff

**8. 特征交叉（4个）**
- rsi_volatility (RSI × 波动率)
- momentum_volatility (动量 × 波动率)
- macd_rsi (MACD × RSI)
- trend_rsi (趋势 × RSI)

#### 3.3.3 特征选择（SelectKBest）

优化版使用 `SelectKBest(mutual_info_classif, k=20)` 从42个特征中选择最相关的20个：

**Top 15 重要特征（按互信息评分排序）**:
```
1. volatility_60      0.0277  ← 60日波动率（最重要）
2. trend_rsi          0.0245  ← 趋势×RSI 交叉特征
3. volatility_5       0.0239  ← 5日波动率
4. momentum_10        0.0212  ← 10日动量
5. vwap               0.0189  ← 成交量加权均价
6. ma5_ma20           0.0160  ← 均线交叉
7. rsi_21             0.0160  ← 21日RSI
8. momentum_20        0.0156  ← 20日动量
9. momentum_5         0.0155  ← 5日动量
10. boll_width        0.0153  ← 布林带宽度
```

---

### 3.4 训练脚本详解

#### 3.4.1 基础训练（4个模型，9个特征）

```bash
python auto_train.py
```

**训练模型**:
| 模型 | 说明 |
|------|------|
| RandomForest | 随机森林分类器 |
| GradientBoosting | 梯度提升分类器 |
| LogisticRegression | 逻辑回归 |
| SVC | 支持向量机 |

**适用场景**: 快速验证、基线对比

#### 3.4.2 增强训练（6个模型，42个特征）⭐

```bash
# 标准增强训练
python auto_train_enhanced.py

# 增强训练 + PCA降维（8个主成分）
python auto_train_enhanced.py --pca --pca-components 8
```

**训练模型**:
| 模型 | 说明 |
|------|------|
| RandomForest | 随机森林（基准） |
| GradientBoosting | 梯度提升（最佳） |
| LogisticRegression | 逻辑回归（低延迟） |
| ExtraTrees | 极端随机树 |
| XGBoost | 极限梯度提升 |
| LightGBM | 轻量级梯度提升机 |

**PCA 降维选项**:
- 8个主成分，累计解释方差 72.54%
- 适合低延迟场景，计算更快
- LogisticRegression 在 PCA 版准确率可达 55.70%

**适用场景**: 特征丰富度验证、模型对比

#### 3.4.3 优化版训练（特征选择+超参数调优）⭐⭐

```bash
python auto_train_optimized.py
```

**核心特性**:
1. **SelectKBest 特征选择** - 从42个特征中选择 Top 20
2. **GridSearchCV 超参数调优** - XGBoost/LightGBM 网格搜索
3. **5个基准模型 + 2个调优模型** - 全面对比
4. **自动保存最佳模型** - 按准确率+F1排序

**调优参数网格**:

| 参数 | XGBoost | LightGBM |
|------|---------|----------|
| max_depth | [4, 5] | [4, 5] |
| learning_rate | [0.05] | [0.05] |
| n_estimators | [200] | [200] |
| subsample | [0.8] | [0.8] |
| colsample_bytree | [0.8] | [0.8] |
| reg_lambda | [1.0] | [1.0] |
| min_child_weight | [1] | - |
| min_child_samples | - | [20] |

**适用场景**: 生产级模型、追求最佳性能

---

### 3.5 训练流程

```
步骤1: 数据加载
    ↓
步骤2: 特征工程（42个特征）
    ↓
步骤3: 特征选择（SelectKBest → 20个）
    ↓
步骤4: 数据划分（训练集 80% / 测试集 20%）
    ↓
步骤5: 基准模型训练（GradientBoosting / ExtraTrees / LogisticRegression）
    ↓
步骤6: 超参数调优（XGBoost / LightGBM GridSearchCV）
    ↓
步骤7: 模型评估（准确率 / F1 / AUC / 混淆矩阵）
    ↓
步骤8: 保存模型（.pkl + 元数据 + 特征选择器）
```

---

### 3.6 模型性能对比

| 模型 | 准确率 | F1分数 | AUC | 特征数 | 训练版本 |
|------|--------|--------|-----|--------|----------|
| **GradientBoosting** ⭐ | **56.01%** | **0.6280** | 0.5741 | 20 | 优化版 |
| XGBoost_tuned | 54.84% | 0.5573 | 0.5872 | 20 | 优化版 |
| ExtraTrees | 54.84% | 0.5061 | 0.5722 | 20 | 优化版 |
| LightGBM_tuned | 54.18% | 0.5385 | 0.5748 | 20 | 优化版 |
| LogisticRegression | 54.38% | 0.4978 | 0.5898 | 20 | 优化版 |
| GradientBoosting（增强版） | 55.18% | 0.6240 | - | 42 | 增强版 |
| LogisticRegression（PCA版） | 55.70% | - | - | 8 | PCA增强版 |

**最佳模型**: GradientBoosting（优化版）
- 准确率: **56.01%**
- F1分数: **0.6280**
- AUC: 0.5741
- 特征数: 20（经 SelectKBest 选择）

---

### 3.7 训练输出

训练完成后，模型文件保存在 `models/` 目录：

```
models/
├── training_metadata_optimized_YYYYMMDD_HHMMSS.json  # 训练元数据
├── feature_selector_YYYYMMDD_HHMMSS.pkl              # 特征选择器（优化版）
│
├── GradientBoosting_acc0.560_f10.628_YYYYMMDD_HHMMSS.pkl
├── ExtraTrees_acc0.548_f10.506_YYYYMMDD_HHMMSS.pkl
├── LogisticRegression_acc0.544_f10.498_YYYYMMDD_HHMMSS.pkl
├── XGBoost_tuned_acc0.548_f10.557_YYYYMMDD_HHMMSS.pkl
└── LightGBM_tuned_acc0.542_f10.539_YYYYMMDD_HHMMSS.pkl
```

**元数据文件结构**:
```json
{
  "best_model": "GradientBoosting",
  "best_accuracy": 0.5601,
  "best_f1": 0.6280,
  "n_features": 20,
  "n_samples": 7650,
  "feature_names": ["returns", "volatility_60", ...],
  "model_results": { ... }
}
```

---

### 3.8 ML信号驱动交易执行

#### 3.8.1 信号生成

```bash
# 默认阈值 55%
python "量化策略系统 v5.7.py" --ml-signal

# 自定义阈值（提高置信度要求）
python "量化策略系统 v5.7.py" --ml-signal --threshold 0.6
```

**信号分类**:
| 信号 | 条件 | 说明 |
|------|------|------|
| 🟢 买入 | 上涨概率 > 阈值 | 强烈上涨信号 |
| 🔴 卖出 | 下跌概率 > 阈值 | 强烈下跌信号 |
| 🟡 持有 | 双方概率 ≤ 阈值 | 信号不明确 |

#### 3.8.2 卖出执行脚本

```bash
# 生成卖出计划（不修改持仓）
python ml_sell_executor.py

# 实际执行卖出（更新持仓文件）
python ml_sell_executor.py --execute
```

**卖出策略（按下跌概率分级）**:

| 下跌概率 | 卖出比例 | 策略说明 |
|----------|----------|----------|
| ≥ 65% | **100%** | 高置信度下跌信号，全部清仓 |
| 60-65% | **50%** | 中置信度下跌信号，减半持仓 |
| 55-60% | **30%** | 低置信度下跌信号，适度减仓 |

#### 3.8.3 自动执行配置

**Windows 任务计划**:
```powershell
# 创建6月29日09:30自动执行任务
powershell -ExecutionPolicy Bypass -File create_task.ps1

# 查看任务
taskschd.msc

# 删除任务
Unregister-ScheduledTask -TaskName "ML_Sell_Execute_20260629"
```

---

### 3.9 模型集成到主系统

ML预测模块已集成到主系统，文件位置：`utils/ml_predictor.py`

**核心类**:
| 类名 | 功能 |
|------|------|
| `MLFeatureEngineer` | 特征工程（42个特征构建） |
| `MLModelPredictor` | 模型加载与预测 |

**核心方法**:
```python
from utils.ml_predictor import MLModelPredictor, run_ml_signal_scan

# 批量预测所有标的
result = run_ml_signal_scan(
    data_dir='data/cache',
    model_dir='models',
    threshold=0.55
)

print(f"最佳模型: {result['model_info']['best_model']}")
print(f"买入信号: {len(result['signals']['buy'])} 只")
print(f"卖出信号: {len(result['signals']['sell'])} 只")
```

**自动发现机制**:
- 自动扫描 `models/` 目录
- 选择最新训练的最佳模型
- 自动加载特征选择器和元数据
- 特征数量自动匹配

---

## 四、目录结构

```
11_量化策略/
├── 量化策略系统 v5.7.py                # 主程序入口（19种CLI模式）⭐
├── daily_runner.py                     # 每日自动化工作流 ⭐ NEW
├── close_report_runner.py              # 收盘报告自动生成器 ⭐ NEW
├── trendcast_client.py                 # TrendCast Pro API 客户端 ⭐ NEW
├── trendcast_audit.py                  # TrendCast 预测审计追踪 ⭐ NEW
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
│   ├── ml_predictor.py                 # ML模型预测模块 ⭐
│   └── report_archiver.py              # 报告归档工具
├── quant_modules/                      # 核心量化模块
│   ├── prediction_bridge.py            # TrendCast 信号权重桥接器 ⭐ NEW
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
├── model_train/                        # ML模型训练模块 ⭐ NEW
│   ├── finbert_sentiment.py            # FinBERT 情感分析
│   ├── xgboost_direction.py            # XGBoost 涨跌预测
│   ├── risk_parity_backtest.py         # 风险平价回测
│   └── signal_composer.py              # 多模型信号合成
├── Kronos/                             # Kronos 时序预测框架 ⭐ NEW
│   ├── model/                          # 预训练模型
│   ├── finetune/                       # 微调脚本
│   ├── finetune_csv/                   # CSV数据微调
│   ├── webui/                          # Web管理界面
│   └── examples/                       # 示例代码
├── signals/                            # 信号生成模块
│   └── futures_options_signal.py       # 期货期权信号
├── config/                             # 配置文件
│   ├── portfolio.yaml                  # 组合配置（14标的4板块）
│   ├── settings.yaml                   # 系统全局配置
│   ├── positions.json                  # 实时持仓状态
│   ├── stop_loss_rules_auto.yaml       # 止损止盈规则
│   └── watchlist.yaml                  # 观察仓配置
├── models/                             # ML模型输出目录 ⭐
│   └── *.pkl / *.json                  # 训练好的模型和元数据
├── data/                               # 数据缓存
│   └── cache/                          # K线数据缓存
├── logs/                               # 运行日志
│   ├── trendcast_audit/                # TrendCast 审计日志 ⭐ NEW
│   └── close_report_*.log              # 收盘报告日志
├── reports/                            # 生成的报告
├── scripts/                            # 脚本工具
├── auto_train.py                       # 基础版训练脚本
├── auto_train_enhanced.py              # 增强版训练脚本 ⭐
├── auto_train_optimized.py             # 优化版训练脚本 ⭐⭐
├── ml_sell_executor.py                 # ML信号驱动卖出执行脚本 ⭐
├── ml_sell_auto_execute.bat            # ML卖出自动执行批处理
├── create_task.ps1                     # Windows任务计划配置脚本
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

### 6.6 TrendCast Pro AI 预测信号系统 ⭐ NEW

**文件**: `trendcast_client.py` + `trendcast_audit.py` + `quant_modules/prediction_bridge.py`

**功能**:
- 对接 TrendCast Pro 金融预测 API（`22_auto_金融市场预测模型/`）
- 批量预测 14 只核心持仓标的的涨跌方向 + 置信度
- 多周期共识信号（短期/中期/长期）
- 审计追踪系统：每条预测写入 JSONL 日志，到期后自动回溯验证命中率
- 模型漂移检测：近30天命中率 vs 整体命中率，偏差超过10%告警
- 信号权重桥接器：将预测信号直接注入再平衡引擎（看涨+高置信度→增持，看跌+高置信度→减持）
- API 不可用时优雅降级，不影响其他流程

**使用**:
```bash
# 1. 先启动 TrendCast Pro API 服务
cd "22_auto_金融市场预测模型"
python main.py serve

# 2. 运行每日流程（默认已开启，无需 --trendcast）
cd "../11_量化策略"
python daily_runner.py

# 如需禁用
python daily_runner.py --no-trendcast
```

**信号逻辑**:
| 信号 | 条件 | 权重调整 |
|------|------|----------|
| 看涨 + 高置信度 | 上涨概率 > 60% | 权重 × (1 + 信号倍数) |
| 看跌 + 高置信度 | 下跌概率 > 60% | 权重减少 |
| 中立 / 低置信度 | 概率 ≤ 60% | 维持原权重 |

### 6.6 盘中决策系统 ⭐

**文件**: `auto_intraday_decision.py` + `utils/intraday_decision.py`

**功能**:
- 交易时段定时调度（09:35, 10:35, 11:25, 13:05, 14:05, 14:50）
- 实时持仓数据获取
- GLM-5 AI 驱动交易决策生成
- 风险预警实时监控
- 自动生成决策报告

**决策时间点**:
| 时间 | 说明 |
|------|------|
| 09:35 | 开盘后5分钟 |
| 10:35 | 上午盘中 |
| 11:25 | 上午收盘前 |
| 13:05 | 午后开盘 |
| 14:05 | 下午盘中 |
| 14:50 | 收盘前10分钟 |

**LLM 配置**:
- 决策引擎: `GLM5DecisionEngine`
- API 模式: `doubao-speed-32k` (豆包Speed)
- 检查间隔: 5分钟
- 最小置信度: 0.6

**使用**:
```bash
# 启动定时调度（持续运行）
python auto_intraday_decision.py

# 只执行一次
python auto_intraday_decision.py --once

# 测试模式（不调用API）
python auto_intraday_decision.py --test
```

**核心类**:
| 类名 | 功能 |
|------|------|
| `IntradayDecisionMonitor` | 盘中决策监控器 |
| `GLM5DecisionEngine` | GLM-5 决策引擎 |
| `GLM5Client` | GLM-5 API 客户端 |

### 6.7 数据获取（优先级链）

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
| v5.7 | 2026-06-27 | **TrendCast Pro AI预测信号系统完整集成** ⭐、每日自动化工作流(daily_runner)、收盘报告自动生成器、Kronos时序预测框架、model_train训练模块 |
| v5.6 | 2026-06-26 | ML模型预测信号系统、AI Hedge Fund、本地Ollama Qwen2.5部署 |
| v5.5 | 2026-06-21 | AI量化再平衡引擎、四大理论引擎、期货期权扫描器 |
| v5.2 | 2026-06-18 | DeepSeek V4 Pro LLM决策引擎接入 |
| v5.1 | 2026-06 | 康波+十五五+社保ETF三大分析模块 |

---

## 十、常用脚本

### 10.1 数据处理与工作流

```bash
# 每日自动化工作流（数据+回测+AI预测+报告）
python daily_runner.py

# 收盘报告自动生成
python close_report_runner.py

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
