#!/usr/bin/env python3
"""
职业投资训练模型 - 快速启动脚本
用法: python quick_start.py
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from career_investor_model import CareerInvestorModel


def main():
    print("\n" + "="*70)
    print("  职业投资训练模型系统 v1.0")
    print("  持仓股投资分析 + 策略训练 + 风险评估 + 收益预测")
    print("="*70)
    
    # 初始化模型
    model = CareerInvestorModel()
    
    # 菜单
    print("\n请选择分析模式:")
    print("  1. 完整分析（推荐）- 持仓+风险+信号+回测+预测")
    print("  2. 仅持仓分析")
    print("  3. 仅风险评估")
    print("  4. 策略回测")
    print("  5. 收益预测（5年）")
    print("  6. 交易信号生成")
    print("  0. 退出")
    
    try:
        choice = input("\n请输入选项 (0-6): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\n程序已退出")
        return
    
    if choice == "1":
        print("\n运行完整分析...")
        model.full_analysis()
    
    elif choice == "2":
        print("\n分析持仓组合...")
        model.analyze_portfolio()
    
    elif choice == "3":
        print("\n运行风险评估...")
        portfolio = model.analyze_portfolio()
        model.assess_risk(portfolio)
    
    elif choice == "4":
        print("\n运行策略回测...")
        model.run_backtest()
    
    elif choice == "5":
        print("\n运行收益预测...")
        model.predict_future(years=5)
    
    elif choice == "6":
        print("\n生成交易信号...")
        portfolio = model.analyze_portfolio()
        model.generate_signals(portfolio)
    
    elif choice == "0":
        print("\n程序已退出")
    
    else:
        print("\n无效选项")


if __name__ == "__main__":
    main()
