#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
盘中实时决策 - 快速测试脚本
测试GLM5自动决策引擎的盘中监控功能
"""

import sys
import os
from pathlib import Path

# 设置编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.intraday_decision import IntradayDecisionMonitor

def main():
    print("=" * 80)
    print("盘中实时决策监控器 - 快速测试")
    print("=" * 80)
    
    try:
        # 1. 创建监控器
        print("\n[1/4] 初始化监控器...")
        monitor = IntradayDecisionMonitor(
            api_model='glm-4-plus',
            check_interval=60,
            enable_notifications=False,
        )
        print("    ✓ 监控器初始化成功")
        
        # 2. 加载持仓
        print("\n[2/4] 加载持仓数据...")
        if not monitor.load_positions():
            print("    ✗ 持仓数据加载失败")
            return
        print(f"    ✓ 已加载 {len(monitor.positions)} 只持仓")
        
        # 3. 生成决策
        print("\n[3/4] 生成交易决策...")
        print("    (这需要10-30秒,请耐心等待)")
        decision = monitor.generate_decision()
        
        if not decision:
            print("    ✗ 决策生成失败")
            return
        
        print(f"    ✓ 决策生成成功!")
        print(f"    - 交易信号: {len(decision.trading_signals)} 条")
        print(f"    - 风险预警: {len(decision.risk_alerts)} 条")
        print(f"    - AI置信度: {decision.ai_confidence:.2%}")
        
        # 显示交易信号
        if decision.trading_signals:
            print("\n    交易信号详情:")
            for sig in decision.trading_signals:
                action_map = {
                    'BUY': '买入',
                    'SELL': '卖出',
                    'HOLD': '持有',
                    'REDUCE': '减仓'
                }
                action_cn = action_map.get(sig.action, sig.action)
                print(f"      [{action_cn}] {sig.code} {sig.name}")
                print(f"        理由: {sig.reason[:100]}...")
                print(f"        置信度: {sig.confidence:.2f}, 紧急程度: {sig.urgency}")
        
        # 显示风险预警
        if decision.risk_alerts:
            print("\n    风险预警:")
            for alert in decision.risk_alerts:
                print(f"      [{alert.severity}] {alert.message}")
        
        # 4. 导出报告
        print("\n[4/4] 导出决策报告...")
        report_path = monitor.export_report(decision)
        
        if report_path:
            print(f"    ✓ 报告已保存: {report_path}")
        else:
            print("    ✗ 报告导出失败")
            return
        
        print("\n" + "=" * 80)
        print("测试完成!")
        print("=" * 80)
        
        # 显示市场概况
        print("\n市场概况:")
        print(decision.market_summary[:200] + "...")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n提示: 可以运行以下命令启动持续监控:")
    print("  python intraday_decision_test.py --interval 300  # 每5分钟检查一次")
    print("  python intraday_decision_test.py --once          # 只执行一次")


if __name__ == '__main__':
    main()
