# -*- coding: utf-8 -*-
"""
三年期回测 - 基于portfolio.yaml配置
总资金: 300万
目标: 年化收益 ≥8%, 最大回撤 ≤15%
"""

import os
import sys
import yaml
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 添加路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from quant_modules.core import PerformanceTracker, config_manager


def load_portfolio_config():
    """加载组合配置"""
    config_path = os.path.join(BASE_DIR, 'config', 'portfolio.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_price_data(assets, years=3):
    """加载历史价格数据"""
    price_data = {}
    cache_dir = os.path.join(BASE_DIR, 'data', 'cache')

    for asset in assets:
        code = asset['code']
        if code == 'CASH':
            continue

        filepath = os.path.join(cache_dir, f'kline_{code}_daily.parquet')
        if os.path.exists(filepath):
            try:
                df = pd.read_parquet(filepath, columns=['close'])
                if not df.empty:
                    df.index = pd.to_datetime(df.index)
                    df = df[~df.index.duplicated(keep='last')]

                    # 只取最近3年数据
                    cutoff = df.index[-1] - timedelta(days=years*365)
                    df = df[df.index >= cutoff]

                    price_data[code] = df
                    print(f"  OK {asset['name']} ({code}): {len(df)} 条, {df.index[0].date()} ~ {df.index[-1].date()}")
            except Exception as e:
                print(f"  FAIL {asset['name']} ({code}): 加载失败 - {e}")

    return price_data


def prebuild_price_matrix(price_data, codes):
    """预建价格矩阵: 每列一个代码，每行一个交易日 → O(1) per-date lookup"""
    aligned = {}
    for code in codes:
        if code not in price_data:
            continue
        aligned[code] = price_data[code]['close']
    if not aligned:
        return None, None, None
    matrix = pd.DataFrame(aligned).sort_index()
    matrix = matrix.ffill()
    return matrix, matrix.index, list(aligned.keys())


def run_backtest(initial_capital=3_000_000, years=3):
    """执行回测"""
    tracker = PerformanceTracker('3年回测')

    print("="*70)
    print("3年期量化策略回测")
    print("="*70)

    # 加载配置
    portfolio = load_portfolio_config()
    assets = [a for a in portfolio['assets'] if a['code'] != 'CASH']
    codes = [a['code'] for a in assets]
    names = {a['code']: a['name'] for a in assets}
    target_weights = {a['code']: a['target_weight'] for a in assets}

    # 归一化权重（排除现金后的相对权重）
    cash_weight = next((a['target_weight'] for a in portfolio['assets'] if a['code'] == 'CASH'), 0.1)
    investable_weight = 1.0 - cash_weight

    normalized_weights = {}
    for code, weight in target_weights.items():
        normalized_weights[code] = weight / investable_weight if investable_weight > 0 else 0

    print(f"\n[配置] {len(assets)} 只标的")
    print(f"{'名称':<12} {'代码':<10} {'目标权重':<10} {'归一化权重':<10}")
    print("-"*60)
    for asset in assets:
        code = asset['code']
        print(f"{asset['name']:<12} {code:<10} {asset['target_weight']*100:>6.1f}%    {normalized_weights[code]*100:>6.1f}%")
    print(f"{'现金':<12} {'CASH':<10} {cash_weight*100:>6.1f}%")
    print("-"*60)

    # 加载数据
    print(f"\n[加载] {years} 年历史数据...")
    price_data = load_price_data(assets, years)

    if not price_data:
        print("[错误] 没有可用数据")
        return

    # 预建价格矩阵 — O(1) per date instead of O(codes) per date
    price_matrix, common_dates_all, active_codes = prebuild_price_matrix(price_data, codes)

    if price_matrix is None or len(common_dates_all) < 60:
        print("[错误] 共同交易日不足")
        return

    common_dates = common_dates_all if len(common_dates_all) <= years * 280 else common_dates_all[-years * 280:]

    print(f"\n[回测区间] {common_dates[0].date()} ~ {common_dates[-1].date()}")
    print(f"   共 {len(common_dates)} 个交易日 ({len(common_dates)/252:.1f}年)")

    # 初始化回测状态
    cash = initial_capital * (1 - cash_weight)
    positions = {code: {'shares': 0, 'avg_cost': 0} for code in active_codes}

    equity_curve = []
    peak_value = initial_capital
    max_drawdown = 0
    trade_count = 0
    last_rebalance = common_dates[0]

    # 年度统计
    year_stats = {}
    current_year = common_dates[0].year
    year_start_value = initial_capital

    print(f"\n[开始回测]")

    for i, date in enumerate(common_dates):
        # O(1) single-shot row lookup — no per-code loop
        if date in price_matrix.index:
            prices_row = price_matrix.loc[date]
        else:
            prev_mask = price_matrix.index <= date
            if not prev_mask.any():
                continue
            prices_row = price_matrix.loc[price_matrix.index[prev_mask][-1]]

        prices = {c: float(prices_row.get(c)) for c in active_codes
                  if prices_row.get(c) and float(prices_row.get(c)) > 0}
        if not prices:
            continue

        # 计算总资产
        total = cash
        for code, pos in positions.items():
            if code in prices:
                total += pos['shares'] * prices[code]

        # 跟踪峰值和回撤
        if total > peak_value:
            peak_value = total
        drawdown = (peak_value - total) / peak_value if peak_value > 0 else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown

        equity_curve.append({
            'date': date,
            'value': total,
            'drawdown': drawdown
        })

        # 年度统计
        if date.year != current_year:
            year_return = (total - year_start_value) / year_start_value
            year_stats[current_year] = {'return': year_return, 'value': total}
            current_year = date.year
            year_start_value = total

        # 再平衡逻辑（每15个交易日）
        if i == 0 or (date - last_rebalance).days >= 15:
            for code in active_codes:
                if code not in prices:
                    continue

                target_weight = normalized_weights.get(code, 0)
                target_amount = total * target_weight

                current_shares = positions.get(code, {}).get('shares', 0)
                current_amount = current_shares * prices[code]
                diff_amount = target_amount - current_amount

                # 阈值过滤（2%）
                if abs(diff_amount) / total < 0.02:
                    continue

                price = prices[code]
                shares = int(abs(diff_amount) / price / 100) * 100

                if shares > 0:
                    # 交易成本（佣金 + 滑点）
                    commission = shares * price * 0.0005

                    if diff_amount > 0:  # 买入
                        cost = shares * price + commission
                        if cost <= cash:
                            cash -= cost
                            if code not in positions:
                                positions[code] = {'shares': 0, 'avg_cost': 0}
                            old_cost = positions[code]['shares'] * positions[code]['avg_cost']
                            positions[code]['shares'] += shares
                            positions[code]['avg_cost'] = (old_cost + shares * price) / positions[code]['shares']
                            trade_count += 1
                    else:  # 卖出
                        if code in positions and positions[code]['shares'] >= shares:
                            positions[code]['shares'] -= shares
                            cash += shares * price - commission
                            if positions[code]['shares'] == 0:
                                del positions[code]
                            trade_count += 1

            last_rebalance = date

        # 进度显示
        if (i + 1) % 100 == 0:
            print(f"  [{i + 1}/{len(common_dates)}] 净值: {total/1e6:.2f}M | 回撤: {drawdown*100:.1f}%")

    tracker.finish()

    # 计算结果
    print(f"\n[回测完成]")

    values = [e['value'] for e in equity_curve]
    dates_list = [e['date'] for e in equity_curve]

    initial = values[0]
    final = values[-1]
    total_return = (final - initial) / initial
    num_years = len(dates_list) / 252
    annual_return = (1 + total_return) ** (1 / num_years) - 1 if num_years > 0 else 0

    # 波动率
    daily_rets = np.diff(values) / values[:-1]
    annual_vol = np.std(daily_rets) * np.sqrt(252) if len(daily_rets) > 0 else 0

    # 夏普比率（无风险利率3%）
    sharpe = (annual_return - 0.03) / annual_vol if annual_vol > 0 else 0

    # 胜率
    win_rate = np.sum(daily_rets > 0) / len(daily_rets) if len(daily_rets) > 0 else 0

    # 计算严重回撤区间
    drawdowns_over_15 = []
    in_drawdown = False
    drawdown_start = None

    for entry in equity_curve:
        if entry['drawdown'] > 0.15:
            if not in_drawdown:
                in_drawdown = True
                drawdown_start = entry['date']
            max_dd_entry = entry
        else:
            if in_drawdown and drawdown_start:
                drawdowns_over_15.append({
                    'start': drawdown_start,
                    'end': entry['date'],
                    'max_dd': max_dd_entry['drawdown'],
                    'duration': (entry['date'] - drawdown_start).days
                })
                in_drawdown = False

    # 打印结果
    print(f"\n{'='*70}")
    print("回测结果")
    print(f"{'='*70}")
    print(f"初始资金: {initial:,.0f}")
    print(f"最终资金: {final:,.0f}")
    print(f"总收益率: {total_return*100:+.2f}%")
    print(f"年化收益: {annual_return*100:+.2f}%")
    print(f"年化波动: {annual_vol*100:.2f}%")
    print(f"最大回撤: {max_drawdown*100:.2f}%")
    print(f"夏普比率: {sharpe:.2f}")
    print(f"日胜率: {win_rate*100:.1f}%")
    print(f"交易次数: {trade_count}")
    print(f"{'='*70}")

    # 目标达成情况
    print(f"\n目标达成:")
    print(f"   年化>=8%: {'OK' if annual_return >= 0.08 else 'FAIL'} ({annual_return*100:.2f}%)")
    print(f"   回撤<=15%: {'OK' if max_drawdown <= 0.15 else 'FAIL'} ({max_drawdown*100:.2f}%)")
    print(f"   夏普>0.5: {'OK' if sharpe > 0.5 else 'FAIL'} ({sharpe:.2f})")

    # 年度收益
    if year_stats:
        print(f"\n年度收益:")
        print(f"{'年份':<8} {'收益率':<12} {'期末净值'}")
        print("-"*45)
        for year in sorted(year_stats.keys()):
            stat = year_stats[year]
            print(f"{year:<8} {stat['return']*100:+.2f}%          {stat['value']:,.0f}")

    # 严重回撤
    if drawdowns_over_15:
        print(f"\n回撤超过15%的区间 ({len(drawdowns_over_15)}次):")
        for i, dd in enumerate(drawdowns_over_15, 1):
            print(f"  {i}. {dd['start'].date()} ~ {dd['end'].date()}, 持续{dd['duration']}天, 最大回撤{dd['max_dd']*100:.1f}%")

    # 最终持仓 — 使用最终日期矩阵行
    print(f"\n最终持仓:")
    print(f"{'名称':<12} {'代码':<10} {'持仓':<12} {'市值':<16} {'占比'}")
    print("-"*70)

    last_date = dates_list[-1]
    total_market_value = 0
    if last_date in price_matrix.index:
        final_row = price_matrix.loc[last_date]
    else:
        prev_mask = price_matrix.index <= last_date
        final_row = price_matrix.loc[price_matrix.index[prev_mask][-1]] if prev_mask.any() else None

    for code in active_codes:
        if code in positions and positions[code]['shares'] > 0:
            shares = positions[code]['shares']
            price = float(final_row.get(code, 0)) if final_row is not None else 0
            market_value = shares * price
            total_market_value += market_value
            weight = market_value / final * 100 if final > 0 else 0
            print(f"{names.get(code, code):<12} {code:<10} {shares:<12,} {market_value:<15,.0f} {weight:>5.1f}%")

    total_value = cash + total_market_value
    print("-"*70)
    print(f"{'持仓市值':<22} {total_market_value:<15,.0f}")
    print(f"{'可用现金':<22} {cash:<15,.0f}")
    print(f"{'账户总值':<22} {total_value:<15,.0f}")

    # 预测
    print(f"\n{'='*70}")
    print("三年预测（基于历史统计）")
    print(f"{'='*70}")

    pred_3y = initial * (1 + annual_return) ** 3
    pred_3y_return = (pred_3y - initial) / initial

    # 蒙特卡洛模拟（简化版）
    rng = np.random.default_rng(42)
    simulations = 1000
    yr_returns = annual_return + rng.normal(0, annual_vol / np.sqrt(3), size=(simulations, 3))
    cum_values = initial * np.cumprod(1 + yr_returns, axis=1)
    final_values = np.sort(cum_values[:, -1])

    p5 = final_values[int(len(final_values) * 0.05)]
    p25 = final_values[int(len(final_values) * 0.25)]
    p50 = final_values[int(len(final_values) * 0.50)]
    p75 = final_values[int(len(final_values) * 0.75)]
    p95 = final_values[int(len(final_values) * 0.95)]

    profit_prob = sum(1 for v in final_values if v > initial) / len(final_values) * 100

    print(f"预期年化收益: {annual_return*100:.2f}%")
    print(f"预期最大回撤: {max_drawdown*100:.2f}%")
    print(f"\n三年后净值预测:")
    print(f"   悲观情景 (5%):  {p5:,.0f} ({(p5/initial-1)*100:+.1f}%)")
    print(f"   保守情景 (25%): {p25:,.0f} ({(p25/initial-1)*100:+.1f}%)")
    print(f"   中位情景 (50%): {p50:,.0f} ({(p50/initial-1)*100:+.1f}%)")
    print(f"   乐观情景 (75%): {p75:,.0f} ({(p75/initial-1)*100:+.1f}%)")
    print(f"   极乐观情景 (95%): {p95:,.0f} ({(p95/initial-1)*100:+.1f}%)")
    print(f"\n盈利概率: {profit_prob:.1f}%")
    success_prob = profit_prob * (1-max_drawdown/0.15) if max_drawdown < 0.15 else 0
    print(f"达成双目标概率 (年化>=8% + 回撤<=15%): {success_prob:.0f}%")

    print(f"\n{'='*70}")

    # 保存结果
    result = {
        'initial_capital': initial,
        'final_capital': final,
        'total_return': total_return,
        'annual_return': annual_return,
        'annual_volatility': annual_vol,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe,
        'win_rate': win_rate,
        'trade_count': trade_count,
        'num_years': num_years,
        'equity_curve': equity_curve,
        'year_stats': year_stats,
        'predictions': {
            'p5': p5,
            'p25': p25,
            'p50': p50,
            'p75': p75,
            'p95': p95,
            'profit_prob': profit_prob
        }
    }

    return result


if __name__ == "__main__":
    result = run_backtest(initial_capital=3_000_000, years=3)
