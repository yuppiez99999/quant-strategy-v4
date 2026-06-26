# CLAUDE.md — 量化策略系统 v5.1

> 本文件为 Claude Code 在本仓库工作时提供指导。
> 相关规则文件：`e:\各种PY程序\.rules\` | `e:\各种PY程序\.skills\`

---

## 1. 项目概述

本项目是一个**生产级别的量化交易策略系统 v5.1**，整合康波周期 + 十五五规划 + 社保基金ETF追踪。

| 模块 | 用途 | 主要文件 |
|------|------|---------|
| 主系统 (v5.1) | 统一入口 — 17 个 CLI 模式 | `量化策略系统 v5.1 - 康波周期 + 十五五规划 + 社保基金ETF追踪 增强版.py` |
| Streamlit UI | 可视化面板 — 12 页面多页面应用 | `ui/app.py` + `ui/pages/` |
| 动力煤舆情日报 | 大宗商品舆情与市场分析 | `coal_news_daily_report.py` |
| ETF 资金流监控 | ETF 板块资金流向跟踪 | `etf_tracker.py` |
| 大宗商品舆情 | 商品/期货/股票信息聚合 | `CommodityMarketSentiment.py` |
| 快速回测引擎 | 本地回测与策略验证 | `fast_backtest.py` |
| 康波周期分析 | 宏观周期 + 十五五交叠 + 行业轮动 | `utils/kondratiev_cycle.py` |
| 十五五规划 | 政策对齐评分 + 权重调整 | `utils/five_year_plan.py` |
| 社保基金ETF追踪 | 风格分类 + 国家队信号 | `utils/social_security_etf.py` |
| 再平衡配置 | 14标的 4板块 3阶段执行 | `rebalancing_config_v6.py`, `build_plan_100w.py` |

**配置风格**: 社保基金风格 + 康波周期 + 十五五规划 + 算力赛道
- 高端制造(含算力): 45% — 中际旭创/海光信息/北方华创/中芯国际/宁德时代/徐工机械
- 顺周期: 20% — 中国神华/南山铝业/宝钢股份
- 资源: 20% — 华安黄金ETF/藏格矿业
- 防御: 15% — 恒瑞医药/药明康德/科伦药业

**核心特性**：
- Python 3.8+（优先级 Python 3.8 → 3.14）
- 零第三方依赖的主系统（兜底价格机制）
- 数据源优先级：Wind MCP Connector (P0, 内置注册) → AKShare Connector (P1, 免费回退) → sina API → 本地缓存 → 预定义价格
- 每日自动运行，Markdown 报告归档到 `每日报告归档/YYYY-MM-DD/`
- Streamlit 可视化 UI（暗色主题 .streamlit/config.toml）

---

## 2. Streamlit UI 面板

### 启动方式

```bash
# 方式1: 双击批处理
启动UI面板.bat

# 方式2: Python 脚本
python run_ui.py

# 方式3: 直接 streamlit
"C:\Program Files\Python38\python.exe" -m streamlit run ui/app.py --server.port 8501
```

### 页面结构 (12 页, 4 组导航)

```
ui/
├── app.py                              # 主入口（导航路由）
├── components/
│   ├── names.py                        # 共享标的名称映射（50+只标的）
│   ├── progress.py                     # Streamlit 进度组件
│   ├── report_viewer.py                # 报告浏览/预览/下载
│   ├── sidebar.py                      # 公共侧边栏
│   └── system_status.py                # 模块卡片/连接器状态
└── pages/
    ├── 01_🏠_系统概览.py               # 16模块状态 + 连接器 + 配置检查
    ├── 02_📊_实时监控.py               # 持仓饼图(按风格着色) + 权重偏差 + 净值曲线 + 标的搜索
    ├── 03_🔄_再平衡执行.py             # 5 Excel表驱动 - 买卖计划 + 止损止盈
    ├── 04_📈_投资组合优化.py           # 5策略对比(等权/风险平价/风险配比/因子/自定义)
    ├── 05_🛡️_风险监控.py              # 止损止盈状态(🔴🟡🟢) + 风险权重分布
    ├── 06_💰_ETF资金流向.py           # 24ETF监控 + 国家队信号 + 风格轮动
    ├── 07_🌊_康波周期分析.py          # 周期阶段 + 行业配置 + 商品信号
    ├── 08_🏛️_十五五规划.py            # 7大战略方向 + 持仓适配评级 + 权重调整
    ├── 09_🏦_社保基金追踪.py          # 4大风格 + ETF映射 + 资金流增强
    ├── 10_🔬_宏观综合分析.py          # 一键三大分析(康波+十五五+社保ETF)
    ├── 11_💎_大宗商品监控.py          # 商品价格/趋势/预警 + 宏观指标
    └── 12_📝_报告管理.py              # 浏览/搜索/预览/下载历史报告
```

### 暗色主题配置

`.streamlit/config.toml`:
```
[theme]
base = "dark"
primaryColor = "#1890FF"
backgroundColor = "#0d1117"
secondaryBackgroundColor = "#161b22"
textColor = "#e6edf3"
```

---

## 3. CLI 运行模式 (17个)

```bash
python "量化策略系统 v5.1.py" --live              # 实时监控
python "量化策略系统 v5.1.py" --report            # 生成报告
python "量化策略系统 v5.1.py" --rebalance         # Excel驱动再平衡
python "量化策略系统 v5.1.py" --rebalance --sync-sl  # 同步止损止盈
python "量化策略系统 v5.1.py" --risk              # 风险监控
python "量化策略系统 v5.1.py" --check             # 系统健康检查
python "量化策略系统 v5.1.py" --etf-flow          # ETF资金流向
python "量化策略系统 v5.1.py" --portfolio-opt     # 投资组合优化
python "量化策略系统 v5.1.py" --kommo-monitor     # 康波周期商品监控
python "量化策略系统 v5.1.py" --commodity-fund    # 大宗商品基本面
python "量化策略系统 v5.1.py" --train-model       # 时序预测训练
python "量化策略系统 v5.1.py" --kondratiev        # 康波+十五五交叠
python "量化策略系统 v5.1.py" --fifteen-five      # 十五五规划适配
python "量化策略系统 v5.1.py" --social-security   # 社保基金ETF追踪
python "量化策略系统 v5.1.py" --macro-analysis    # 宏观综合分析(一键三大)
python "量化策略系统 v5.1.py" --daily --phase all # 三阶段工作流
python "量化策略系统 v5.1.py" --backtest          # 回测验证
```

---

## 4. 可用的 Agent / Skill（已扫描集成）

### 4.1 金融类 Skill（P0 — 直接可用）

| Skill | 来源 | 用途 |
|-------|------|------|
| `wind-mcp-skill` | 系统注册 | Wind 数据终端 MCP 连接 |
| `deep-research` | 系统注册 | 多源深度研究 + 对抗验证 + 引用合成 |
| `equity-research:*` | 会话可用 | 催化剂日历/盈利分析/晨报/初始化覆盖 |
| `financial-analysis:*` | 会话可用 | DCF/LBO/3报表/可比分析 |
| `market-researcher:*` | 会话可用 | 竞争分析/行业概览/标的筛选 |
| `investment-banking:*` | 会话可用 | 并购模型/项目追踪/买家名单 |
| `daily_stock_analysis` | `.claude/skills/` | A股情绪评分 + 技术面 + 战报 |

### 4.2 FinClaw 金融 Skill 库 (1,031个 — 按需复用)

路径: `E:\各种PY程序\10_第三方项目\FinClaw\skills\`

| 类别 | 数量 | 最相关 Skill |
|------|------|-------------|
| A股组合管理 | 174+ | `a-share-portfolio`, `a-share-portfolio-optimize` |
| A股风险分析 | 30+ | `a-share-risk-alert`, `a-share-tail-risk`, `a-share-risk-budget` |
| 数据获取 | 40+ | `cn-stock-data`（5源自适应）, `akshare-*`（33个子Skill） |
| 可视化 | 5+ | `visualization` — K线/收益曲线/因子热力图/饼图 |
| 估值模型 | 20+ | `a-share-dcf`, `a-share-multifactor-model` |
| 回测/执行 | 15+ | `backtrader-skill`, `a-share-execution-algo` |

### 4.3 数据源连接器

| 连接器 | 文件 | 优先级 |
|--------|------|--------|
| Wind MCP Connector | `quant_modules/wind_mcp.py` | P0 (最高优先, 内置注册) |
| AKShare Connector | `量化策略系统.py` (内联) | P1 (免费回退, 内置注册) |
| LSEG MCP | `11_量化策略/lseg_mcp_connector.py` | P2 (已禁用) |
| TrendRadar MCP | `mcp-servers/mcp-config.json` | 大宗商品舆情 |

### 4.4 工程类 Skill

| Skill | 用途 |
|-------|------|
| `code-review` / `security-review` | 代码审查 / 安全审查 |
| `verify` | 代码变更验证 |
| `tdd-workflow` | TDD 开发流程 |
| `python-patterns` / `python-testing` | Python 最佳实践 |
| `error-handling` | 优雅降级模式 |
| `mle-workflow` | ML 工程生命周期 |

### 4.5 ECC Agent 系统 (64个 — `10_第三方项目\ECC\agents\`)

| Agent | 用途 |
|-------|------|
| `code-reviewer` | 代码审查 |
| `code-architect` | 功能架构设计 |
| `harness-optimizer` | Claude Code 配置优化 |

---

## 5. 架构原则

### 5.1 不可变性（CRITICAL）

始终创建新对象，**绝不**原地修改：

```python
# WRONG
df['new_col'] = df['price'] * 1.1

# CORRECT
result = df.assign(new_col=lambda d: d['price'] * 1.1)
```

### 5.2 核心原则

- **KISS** — 选择最简单的可行方案
- **DRY** — 重复逻辑提取到共享函数（如 `ui/components/names.py`）
- **YAGNI** — 不提前构建不需要的功能

### 5.3 文件组织

- 多小文件 > 少大文件；典型 200-400 行，最大 800 行
- UI 页面均 < 200 行；公共组件 < 80 行
- 共享名称映射集中在 `ui/components/names.py`（一处维护全局生效）

---

## 6. 数据源优先级

```
Wind MCP analytics_data              ← P0 已注册
    ↓ (不可用时降级)
iFinD MCP                            ← 需要时启用
    ↓ (不可用时降级)
akshare / efinance / baostock
    ↓ (不可用时降级)
新浪财经 API
    ↓ (不可用时降级)
本地缓存 (Parquet/JSON)
    ↓ (不可用时降级)
兜底预定义价格                        ← 保证永不崩溃
```

**降级原则**：始终优雅降级，不因上层数据源不可用而崩溃。

---

## 7. 测试要求

- **最低覆盖率**: 80%
- **测试类型**: 单元测试 → 集成测试 → E2E 测试
- **工作流**: TDD（RED → GREEN → REFACTOR）
- **AAA 模式**: Arrange → Act → Assert

---

## 8. 安全要求

- [ ] 无硬编码密钥（使用环境变量 `.env`）
- [ ] 敏感数据不在日志明文输出
- [ ] API 调用使用 HTTPS
- [ ] 文件路径已验证（防路径遍历）
- [ ] CSV/JSON 输出不含未清理的敏感信息

```python
# CORRECT
api_key = os.environ.get("WIND_API_KEY", "")
config = load_json_config("config/positions.json")
```

---

## 9. Git 工作流 (Conventional Commits)

```
feat(ui): 添加康波周期分析页面
fix(etf): 修复资金流信号检测阈值
refactor(core): 提取报告保存公共函数
style(ui): 切换暗色主题
docs(claude): 更新 v5.1 项目文档
```

---

## 10. 目录结构 (v5.1)

```
11_量化策略/
├── 量化策略系统 v5.1 - 康波周期 + 十五五规划 + 社保基金ETF追踪 增强版.py
├── ui/                              # Streamlit 多页面 UI ★
│   ├── app.py
│   ├── components/                  # 公共组件 (names/progress/report_viewer/system_status/sidebar)
│   └── pages/                       # 12 个功能页面
├── utils/                           # 核心分析模块
│   ├── kondratiev_cycle.py          # 康波周期 v2.0
│   ├── five_year_plan.py            # 十五五规划
│   ├── social_security_etf.py       # 社保基金ETF追踪
│   ├── logging_manager.py           # 统一日志
│   ├── event_tracker.py             # 事件追踪
│   └── data_source_manager.py       # 多源自适应
├── config/
│   ├── portfolio.yaml               # 组合配置 (14标的4板块)
│   ├── settings.yaml                # 系统全局配置
│   ├── positions.json               # 实时持仓状态
│   ├── price_history.jsonl          # 历史价格日志
│   ├── stop_loss_rules_auto.yaml    # 止损止盈规则
│   └── watchlist.yaml               # 大炼化观察仓
├── rebalancing_config_v6.py         # 再平衡策略 v6
├── build_plan_100w.py/json          # 100万建仓计划
├── 每日报告归档/YYYY-MM-DD/
├── reports/
├── .streamlit/config.toml           # 暗色主题
├── 启动UI面板.bat
├── run_ui.py
└── CLAUDE.md                        # ← 本文件
```

---

## 11. 环境变量

```
WIND_API_KEY=...               # Wind MCP (P0 数据源)
IFIND_TOKEN=...                # iFinD MCP (备选)
TS_TOKEN=...                   # Tushare (国内期货/CPI)
LSEG_API_KEY=...               # LSEG (国际金融数据, 已禁用)
VOLCENGINE_API_KEY=...         # 豆包 LLM (AI 分析)
REPORT_OUTPUT_DIR=./每日报告归档
LOG_LEVEL=INFO
```

---

**更新时间**: 2026-06-12
**版本**: v5.1 (康波周期 + 十五五规划 + 社保基金ETF追踪 + Streamlit UI 暗色主题)
