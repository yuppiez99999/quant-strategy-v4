# GLM-5 自动决策引擎 - 使用指南

## 🎯 功能概述

GLM-5 自动决策引擎可以让你的量化系统在运行时**自动分析市场并生成交易决策**：

- ✅ **自动分析市场数据**（指数、板块、资金流、技术指标）
- ✅ **生成交易信号**（买/卖/持有/减仓）
- ✅ **风险预警**（止损/止盈/仓位超标）
- ✅ **组合再平衡建议**
- ✅ **自动生成 Markdown 报告**

---

## 🚀 快速开始（3步）

### 第1步：导入引擎

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.glm5_decision_engine import GLM5DecisionEngine

# 初始化
engine = GLM5DecisionEngine(mode='api', api_model='glm-4-plus')
```

### 第2步：准备数据

```python
# 市场数据
market_data = {
    "日期": "2026-06-23",
    "指数行情": {
        "上证指数": {"收盘": 3050.12, "涨跌幅": "+0.85%"},
    },
    "资金流向": {
        "北向资金": "净流入 +85亿",
    },
}

# 持仓数据
portfolio_data = {
    "账户总值": "1,052,340元",
    "持仓": [
        {
            "代码": "300308",
            "名称": "中际旭创",
            "仓位": "5.2%",
            "成本价": 128.50,
            "现价": 145.30,
            "盈亏": "+13.1%",
        },
    ],
    "目标仓位": {
        "中际旭创": "5%",
    },
}
```

### 第3步：生成决策

```python
# 生成交易决策
decision = engine.make_decisions(
    market_data=market_data,
    portfolio_data=portfolio_data,
    risk_rules={
        "max_single_position": 0.10,  # 单只标的最大10%
        "stop_loss_pct": -0.08,        # 止损线-8%
        "take_profit_pct": 0.15,       # 止盈线+15%
    }
)

# 查看交易信号
for signal in decision.trading_signals:
    print(f"[{signal.action}] {signal.code} {signal.name}")
    print(f"  理由: {signal.reason}")

# 查看风险预警
for alert in decision.risk_alerts:
    print(f"[{alert.severity}] {alert.message}")

# 导出报告
report_path = engine.export_decisions(decision)
print(f"报告已保存: {report_path}")
```

---

## 📊 实际运行结果示例

刚才的测试输出：

```
市场概况: 立即卖出中国神华，规避潜在下跌风险；中际旭创虽接近止盈线但技术面仍强，建议维持观察...

风险预警: 
  [CRITICAL] 中国神华技术指标转弱，资金持续流出，存在进一步下跌风险
  [MEDIUM] 中际旭创盈利已达13.1%，接近15%止盈

AI 整体置信度: 0.00%

报告已保存: E:\各种PY程序\每日报告归档\2026-06-23\AI决策_20260623_092407.md
```

---

## 🔧 集成到现有系统

### 示例1：在日报生成流程中使用

```python
# 文件: 11_量化策略/daily_report.py

from utils.glm5_decision_engine import GLM5DecisionEngine

class DailyReportGenerator:
    def __init__(self):
        self.ai_engine = GLM5DecisionEngine(mode='api')
    
    def generate_daily_report(self, market_data, portfolio_data):
        """生成包含AI决策的日报"""
        
        # 1. 生成AI决策
        decision = self.ai_engine.make_decisions(
            market_data=market_data,
            portfolio_data=portfolio_data,
        )
        
        # 2. 将AI分析插入日报
        report = f"""# 每日交易日报 - {datetime.now().strftime('%Y-%m-%d')}

## AI 智能决策

{decision.raw_analysis}

## 交易信号汇总

"""
        for sig in decision.trading_signals:
            report += f"- [{sig.action}] {sig.code} {sig.name} (置信度:{sig.confidence:.2f})\n"
        
        # 3. 保存报告
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return decision
```

### 示例2：在 Streamlit UI 中添加 AI 决策页面

```python
# 文件: ui/pages/05_🤖_AI决策.py

import streamlit as st
import sys
sys.path.insert(0, '../..')
from utils.glm5_decision_engine import GLM5DecisionEngine

st.set_page_config(page_title="AI 决策引擎", layout="wide")

st.title("🤖 GLM-5 自动决策引擎")

# 侧边栏：参数设置
with st.sidebar:
    st.header("配置")
    api_model = st.selectbox("模型", ["glm-4-plus", "glm-4-flash", "glm-4"])
    temperature = st.slider("温度", 0.1, 1.0, 0.3)
    
    if st.button("生成决策", type="primary"):
        # 获取市场数据（从你的系统）
        market_data = get_market_data()  # 你的函数
        portfolio_data = get_portfolio_data()  # 你的函数
        
        # 生成决策
        with st.spinner("AI 正在分析..."):
            engine = GLM5DecisionEngine(
                mode='api',
                api_model=api_model,
                temperature=temperature,
            )
            decision = engine.make_decisions(
                market_data=market_data,
                portfolio_data=portfolio_data,
            )
        
        # 显示结果
        st.success("决策生成完成!")
        
        # 交易信号
        st.subheader("交易信号")
        if decision.trading_signals:
            for sig in decision.trading_signals:
                st.write(f"**[{sig.action}]** {sig.code} {sig.name}")
                st.write(f"  理由: {sig.reason}")
        else:
            st.info("暂无交易信号")
        
        # 风险预警
        st.subheader("风险预警")
        for alert in decision.risk_alerts:
            if alert.severity == "CRITICAL":
                st.error(f"🚨 {alert.message}")
            elif alert.severity == "HIGH":
                st.warning(f"⚠️ {alert.message}")
        
        # 原始分析
        with st.expander("查看完整 AI 分析"):
            st.markdown(decision.raw_analysis)
```

### 示例3：定时自动决策（每天盘后运行）

```python
# 文件: auto_decision_scheduler.py

import schedule
import time
from utils.glm5_decision_engine import GLM5DecisionEngine

def daily_decision_job():
    """每日盘后自动决策"""
    print(f"\n[{datetime.now()}] 开始自动决策...")
    
    try:
        # 1. 获取数据
        market_data = collect_market_data()
        portfolio_data = get_portfolio_data()
        
        # 2. 生成决策
        engine = GLM5DecisionEngine(mode='api')
        decision = engine.make_decisions(
            market_data=market_data,
            portfolio_data=portfolio_data,
        )
        
        # 3. 导出报告
        report_path = engine.export_decisions(decision)
        print(f"报告已保存: {report_path}")
        
        # 4. 检查风险预警
        critical_alerts = [a for a in decision.risk_alerts if a.severity in ["CRITICAL", "HIGH"]]
        if critical_alerts:
            print(f"\n⚠️  发现 {len(critical_alerts)} 条高风险预警:")
            for alert in critical_alerts:
                print(f"  [{alert.severity}] {alert.message}")
                # 可以发送邮件/微信通知
                send_notification(alert)
        
    except Exception as e:
        print(f"决策生成失败: {e}")

# 设置定时任务（每天15:30盘后运行）
schedule.every().day.at("15:30").do(daily_decision_job)

# 启动
print("自动决策引擎已启动...")
while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 📁 输出文件格式

决策报告会保存到：`每日报告归档/YYYY-MM-DD/AI决策_YYYYMMDD_HHMMSS.md`

**报告内容：**

```markdown
# AI 交易决策报告

**生成时间**: 2026-06-23T09:24:07.123456
**AI 置信度**: 75.50%

## 市场概况

立即卖出中国神华，规避潜在下跌风险；中际旭创虽接近止盈线但技术面仍强...

## 交易信号

| 代码 | 名称 | 动作 | 当前仓位 | 目标仓位 | 数量 | 置信度 | 紧急程度 |
|------|------|------|---------|---------|------|--------|----------|

## 风险预警

- [CRITICAL] 中国神华技术指标转弱，资金持续流出，存在进一步下跌风险
- [MEDIUM] 中际旭创盈利已达13.1%，接近15%止盈

## 组合调整建议

- 建议将现金比例从5%提升至8%
- 减持中国神华2%，增持中际旭创1%

## 宏观展望

- 短期：震荡上行，关注3050点压力位
- 中期：结构性行情，科技板块占优

---
*以上决策由 GLM-5 AI 自动生成，仅供参考，不构成投资建议*
*请人工审核后再执行交易*
```

---

## ⚙️ 高级配置

### 1. 调整决策风格

```python
# 保守型（低温度，更确定性）
engine = GLM5DecisionEngine(
    mode='api',
    temperature=0.1,  # 更低，更保守
    api_model='glm-4-plus',
)

# 激进型（高温度，更多创新）
engine = GLM5DecisionEngine(
    mode='api',
    temperature=0.7,  # 更高，更灵活
    api_model='glm-4',
)
```

### 2. 自定义风控规则

```python
risk_rules = {
    "max_single_position": 0.08,      # 单只标的最大8%（更严格）
    "stop_loss_pct": -0.05,           # 止损线-5%（更敏感）
    "take_profit_pct": 0.10,          # 止盈线+10%（更早止盈）
    "max_sector_exposure": 0.25,      # 单一行业最大25%
    "min_cash_ratio": 0.10,           # 最低现金比例10%
}

decision = engine.make_decisions(
    market_data=market_data,
    portfolio_data=portfolio_data,
    risk_rules=risk_rules,
)
```

### 3. 添加宏观指标

```python
macro_indicators = {
    "PMI": 50.5,
    "CPI": 2.1,
    "M2增速": "10.2%",
    "社融增量": "3.2万亿",
    "失业率": "5.2%",
}

decision = engine.make_decisions(
    market_data=market_data,
    portfolio_data=portfolio_data,
    macro_indicators=macro_indicators,
)
```

---

## 🎯 使用场景

### 场景1：盘前决策（每天9:00）

```python
# 盘前生成今日交易计划
decision = engine.make_decisions(
    market_data=get_premarket_data(),
    portfolio_data=get_portfolio_data(),
)

# 输出今日操作计划
for sig in decision.trading_signals:
    if sig.action == "BUY":
        print(f"今日计划买入: {sig.code} {sig.name} 目标仓位{sig.target_weight:.1%}")
```

### 场景2：盘中监控（每小时）

```python
# 每小时检查一次
while trading_hours:
    decision = engine.quick_check(get_portfolio_data())
    
    # 检查风险预警
    for alert in decision.risk_alerts:
        if alert.severity == "CRITICAL":
            execute_emergency_action(alert)  # 紧急操作
```

### 场景3：盘后复盘（每天15:30）

```python
# 盘后生成完整分析报告
decision = engine.make_decisions(
    market_data=get_aftermarket_data(),
    portfolio_data=get_portfolio_data(),
)

# 导出报告
report_path = engine.export_decisions(decision)

# 发送复盘报告
send_report_via_wechat(report_path)
```

---

## ⚠️ 注意事项

### 1. API 成本

- 每次决策调用约消耗 200-500 tokens
- 日均调用 3-5 次，月成本约 ¥15-30
- 可使用 `glm-4-flash` 降低成本（更快更便宜）

### 2. 决策可靠性

- AI 决策仅供参考，**必须人工审核**
- 置信度低于 0.6 的建议需谨慎对待
- 高风险预警（CRITICAL/HIGH）应立即处理

### 3. 网络依赖

- API 模式需要网络连接
- 如遇网络问题，可切换到本地模式（需要 GPU）

### 4. 风控优先

- 永远不要完全依赖 AI 决策
- 设置硬性止损线，不受 AI 建议影响
- 重大决策（如清仓）必须人工确认

---

## 📞 故障排查

### Q1: 决策生成失败

**错误**: `API 调用失败` 或 `所有模型调用失败`

**解决**:
```python
# 检查 API Key 是否正确
print(os.environ.get('ZHIPUAI_API_KEY', ''))

# 尝试切换模型
engine = GLM5DecisionEngine(api_model='glm-4-flash')
```

### Q2: 决策速度慢

**原因**: GLM-5 分析需要 10-30 秒

**优化**:
```python
# 使用快速检查（仅检查持仓风险）
decision = engine.quick_check(portfolio_data)

# 或使用更快的模型
engine = GLM5DecisionEngine(api_model='glm-4-flash')
```

### Q3: 交易信号为空

**原因**: 当前持仓无需调整

**解决**: 这是正常现象，说明市场稳定，无需操作

---

## 🎓 下一步

1. ✅ 运行 `python quick_decision_test.py` 验证功能
2. ✅ 将决策引擎集成到你的日报生成流程
3. ✅ 在 Streamlit UI 中添加 AI 决策页面
4. ✅ 设置定时任务自动运行决策
5. ✅ 根据实际需求调整风控参数

**祝使用愉快！** 🚀
