#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
12只标的量化策略回测脚本
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_engine import BacktestEngine, load_configs, load_klines_from_cache


def main():
    print("=" * 60)
    print("12只标的量化策略 — 回测")
    print("=" * 60)

    settings, portfolio = load_configs()
    capital = settings["capital"]["total"]

    print(f"\n资金: ¥{capital:,.0f}")
    print(f"标的数: {len(portfolio['assets'])}")

    klines = load_klines_from_cache(portfolio, "data/cache", years=5)

    if not klines:
        print("\n错误: 无可用数据，请先运行 data_download.py")
        sys.exit(1)

    print("\n运行回测...")
    engine = BacktestEngine(settings, portfolio, capital)
    result = engine.run(klines)

    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    print(f"初始资金: ¥{result.get('initial_capital', 0):,.0f}")
    print(f"最终资金: ¥{result.get('final_capital', 0):,.0f}")
    print(f"总收益率: {result.get('total_return', 0):.2%}")
    print(f"年化收益: {result.get('annual_return', 0):.2%}")
    print(f"年化波动: {result.get('annual_volatility', 0):.2%}")
    print(f"最大回撤: {result.get('max_drawdown', 0):.2%}")
    print(f"夏普比率: {result.get('sharpe_ratio', 0):.2f}")
    print(f"胜率(日): {result.get('win_rate', 0):.1%}")
    print(f"交易次数: {result.get('num_trades', 0)}")

    tc = result.get('target_check', {})
    ar_ok = tc.get('annual_return_ok', False)
    dd_ok = tc.get('max_drawdown_ok', False)

    print("\n--- 目标达成情况 ---")
    print(f"年化收益≥8%: {'通过' if ar_ok else '未通过'} ({result.get('annual_return', 0):.2%})")
    print(f"最大回撤≤10%: {'通过' if dd_ok else '未通过'} ({result.get('max_drawdown', 0):.2%})")

    if ar_ok and dd_ok:
        print("\n✅ 目标全部达成！")
        sys.exit(0)
    else:
        print("\n⚠️ 目标未完全达成，需要调整参数")
        sys.exit(1)


if __name__ == '__main__':
    main()
