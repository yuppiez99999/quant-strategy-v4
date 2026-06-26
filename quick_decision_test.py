# -*- coding: utf-8 -*-
"""
GLM-5 自动决策引擎 - 快速验证（30秒）
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.console_encoding import setup_utf8_console
from utils.env_loader import load_dotenv

setup_utf8_console()
load_dotenv()
if not os.environ.get('ZHIPUAI_API_KEY'):
    print('未检测到 ZHIPUAI_API_KEY，请在 .env 中配置后重试。')
    sys.exit(1)

from utils.glm5_decision_engine import GLM5DecisionEngine

print("=" * 60)
print("GLM-5 自动决策引擎 - 快速验证")
print("=" * 60)

# 初始化引擎
print("\n[1] 初始化决策引擎...")
try:
    engine = GLM5DecisionEngine(mode='api', api_model='glm-4-plus')
    print("    [OK] 引擎初始化成功")
except Exception as e:
    print(f"    [FAIL] 初始化失败: {e}")
    sys.exit(1)

# 模拟持仓数据
print("\n[2] 模拟持仓数据...")
portfolio_data = {
    "账户总值": "1,052,340元",
    "当日盈亏": "+12,850元 (+1.24%)",
    "持仓": [
        {
            "代码": "300308",
            "名称": "中际旭创",
            "仓位": "5.2%",
            "成本价": 128.50,
            "现价": 145.30,
            "盈亏": "+13.1%",
        },
        {
            "代码": "601088",
            "名称": "中国神华",
            "仓位": "4.8%",
            "成本价": 38.20,
            "现价": 37.90,
            "盈亏": "-0.8%",
        },
    ],
    "目标仓位": {
        "中际旭创": "5%",
        "中国神华": "4%",
    },
}
print(f"    [OK] 持仓: {len(portfolio_data['持仓'])} 只标的")

# 生成快速决策
print("\n[3] 生成交易决策...")
print("    [WAIT] AI 正在分析（约10-30秒）...")

try:
    decision = engine.quick_check(portfolio_data)
    
    print(f"\n    [OK] 决策生成完成!")
    print(f"\n    市场概况: {decision.market_summary[:100]}...")
    print(f"\n    交易信号: {len(decision.trading_signals)} 条")
    
    for sig in decision.trading_signals:
        print(f"      [{sig.action}] {sig.code} {sig.name} - 置信度:{sig.confidence:.2f}")
    
    print(f"\n    风险预警: {len(decision.risk_alerts)} 条")
    for alert in decision.risk_alerts:
        print(f"      [{alert.severity}] {alert.message[:60]}")
    
    print(f"\n    AI 整体置信度: {decision.ai_confidence:.2%}")
    
    # 导出报告
    print(f"\n[4] 导出报告...")
    file_path = engine.export_decisions(decision)
    print(f"    [OK] 报告已保存: {file_path}")
    
    print("\n" + "=" * 60)
    print("决策引擎验证成功!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n    [FAIL] 决策生成失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
