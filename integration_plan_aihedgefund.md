# AI Hedge Fund 集成报告

## 集成状态: ✅ 完成

集成时间: 2026-06-26

---

## 已集成的 19 位 AI 分析师

| # | 分析师 | 风格 | 状态 |
|---|--------|------|------|
| 1 | Warren Buffett | 价值投资 + 护城河 | ✅ |
| 2 | Ben Graham | 价值投资 + 安全边际 | ✅ |
| 3 | Bill Ackman | 激进投资者 | ✅ |
| 4 | Cathie Wood | 颠覆性成长 | ✅ |
| 5 | Charlie Munger | 理性价值 | ✅ |
| 6 | Michael Burry | 逆向投资 | ✅ |
| 7 | Mohnish Pabrai | Dhandho 投资 | ✅ |
| 8 | Nassim Taleb | 黑天鹅风险 | ✅ |
| 9 | Peter Lynch | 十倍股猎手 | ✅ |
| 10 | Phil Fisher | 闲聊法投资 | ✅ |
| 11 | Rakesh Jhunjhunwala | 印度大牛 | ✅ |
| 12 | Stanley Druckenmiller | 宏观投资 | ✅ |
| 13 | Aswath Damodaran | 估值院长 | ✅ |
| 14 | Fundamentals Analyst | 基本面分析 | ✅ |
| 15 | Technicals Analyst | 技术分析 | ✅ |
| 16 | Sentiment Analyst | 情绪分析 | ✅ |
| 17 | Valuation Analyst | 估值分析 | ✅ |
| 18 | Growth Analyst | 成长分析 | ✅ |
| 19 | News Sentiment Analyst | 新闻情绪 | ✅ |

+ Risk Manager + Portfolio Manager

---

## 新增文件

```
quant_modules/ai_hedge_fund/
├── __init__.py              # 模块入口 + 懒加载
├── orchestrator.py          # LangGraph 工作流编排
├── data_adapter.py          # 数据源桥接器 (sina/akshare/baostock)
├── input.py                 # CLI 交互
├── agents/ (21 文件)        # 19 分析师 + 风控 + 组合管理
├── data/                    # 数据模型 + 缓存
├── graph/                   # AgentState 定义
├── llm/                     # LLM 模型管理
└── utils/                   # 工具 (analysts配置/progress/llm/disp)

ui/pages/13_🤖_AI分析师.py   # Streamlit 页面
```

## CLI 使用方式

```bash
# 使用默认持仓标的 + 全部分析师
python "量化策略系统 v5.6.py" --ai-hedge

# 指定标的
python "量化策略系统 v5.6.py" --ai-hedge --ticker 600036 000001 300750

# 选择特定分析师
python "量化策略系统 v5.6.py" --ai-hedge --ticker 600036 --analysts warren_buffett ben_graham

# 指定 LLM (需要设置 API Key)
set DEEPSEEK_API_KEY=sk-xxx
python "量化策略系统 v5.6.py" --ai-hedge --ticker 600036 --model deepseek-chat --provider DeepSeek

# 显示详细推理
python "量化策略系统 v5.6.py" --ai-hedge --ticker 600036 --show-reasoning
```

## 数据源适配

AI Hedge Fund 的 Financial Datasets API 已替换为:
- 价格: sina API → akshare 回退
- 财务指标: akshare stock_financial_abstract_ths
- 财务报表: akshare profit/balance/cashflow sheets
- 市值: akshare stock_zh_a_spot_em

## 依赖

```bash
pip install langgraph langchain langchain-openai python-dotenv pandas numpy matplotlib akshare
```

需要至少一个 LLM API Key:
- OPENAI_API_KEY
- DEEPSEEK_API_KEY
- ANTHROPIC_API_KEY
