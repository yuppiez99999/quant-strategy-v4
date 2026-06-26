# -*- coding: utf-8 -*-
"""
收益率预测模块 — 基于 parquet 缓存数据的蒙特卡洛模拟
适配 portfolio.yaml，预测未来5年年化收益率与最大回撤分布
"""
import os, sys, json
import numpy as np
import pandas as pd
import yaml
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, 'data', 'cache')
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'portfolio.yaml')

def load_portfolio():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_cache_data(codes):
    """从 parquet 缓存加载价格序列，构建收益率矩阵"""
    returns_dict = {}
    coverage = {}
    for code in codes:
        path = os.path.join(CACHE_DIR, f'kline_{code}_daily.parquet')
        if not os.path.exists(path):
            continue
        df = pd.read_parquet(path, columns=['close', 'date', 'trade_date', '收盘价'])
        if 'close' not in df.columns and '收盘价' in df.columns:
            df.rename(columns={'收盘价': 'close'}, inplace=True)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
        elif 'trade_date' in df.columns:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.set_index('trade_date').sort_index()
        # 标准化索引为纯日期（去掉时分秒）
        df.index = pd.to_datetime(df.index).normalize()
        df['ret'] = df['close'].pct_change().fillna(0)
        returns_dict[code] = df['ret']
        coverage[code] = (df.index.min(), df.index.max(), len(df))
    if not returns_dict:
        return None, {}
    # 找重叠区间并对齐
    min_max = [(v[0], v[1]) for v in coverage.values()]
    overlap_start = max(m[0] for m in min_max)
    overlap_end = min(m[1] for m in min_max)
    print(f"  📅 重叠区间: {overlap_start.strftime('%Y-%m-%d')} ~ {overlap_end.strftime('%Y-%m-%d')}")
    all_returns = pd.DataFrame(returns_dict)
    all_returns = all_returns.loc[overlap_start:overlap_end].dropna()
    return all_returns, coverage

def monte_carlo_sim(returns_df, weights_dict, years=5, n_sim=10000, init_cap=1_000_000):
    """蒙特卡洛模拟"""
    # 只保留有权重的标的
    valid_codes = [c for c in weights_dict if c in returns_df.columns]
    if len(valid_codes) < 2:
        print(f"  ⚠️ 有效标的不够: {len(valid_codes)}")
        return None
    
    ret_sub = returns_df[valid_codes]
    
    # 过滤全零列和 NaN 列
    valid_cols = []
    for c in valid_codes:
        col = ret_sub[c]
        col_clean = col.replace([np.inf, -np.inf], np.nan).dropna()
        if len(col_clean) > 30 and col_clean.std() > 1e-10:
            valid_cols.append(c)
    
    if len(valid_cols) < 2:
        print(f"  ⚠️ 数据质量不够，有效列: {valid_cols}")
        return None
    
    ret_sub = ret_sub[valid_cols].dropna()
    weights = np.array([weights_dict[c] for c in valid_cols])
    weights = weights / weights.sum()
    
    print(f"  📊 最终有效标的: {len(valid_cols)}只, 共同交易日: {len(ret_sub)}天")
    
    mean_daily = ret_sub.mean().values
    cov_daily = ret_sub.cov().values
    
    # 检查并修复 NaN/Inf
    if np.any(np.isnan(mean_daily)) or np.any(np.isnan(cov_daily)):
        print("  ⚠️ 协方差含 NaN，填充为 0")
        mean_daily = np.nan_to_num(mean_daily, nan=0.0)
        cov_daily = np.nan_to_num(cov_daily, nan=0.0)
    
    # 协方差矩阵正则化 (防止 SVD 不收敛)
    cov_daily = cov_daily + np.eye(len(valid_codes)) * 1e-8
    eigvals = np.linalg.eigvals(cov_daily).real
    if np.min(eigvals) <= 0:
        cov_daily = cov_daily + np.eye(len(valid_codes)) * (abs(np.min(eigvals)) + 1e-6)
    
    n_days = years * 252
    annual_returns = []
    max_drawdowns = []
    final_values = []
    
    print(f"  🎲 模拟参数: {n_sim}次 × {years}年 ({n_days}交易日)")
    print(f"  📊 有效标的: {len(valid_codes)}/{len(weights_dict)}只")
    print(f"  📈 历史年化收益: {(mean_daily * 252).dot(weights):.2%}")
    print(f"  📉 历史年化波动: {np.sqrt(weights @ cov_daily @ weights * 252):.2%}")
    
    # 向量化蒙特卡洛：一次生成全部路径
    L = np.linalg.cholesky(cov_daily)
    rng = np.random.default_rng()
    Z = rng.standard_normal((n_sim, n_days, len(valid_codes)))
    sim_ret_3d = mean_daily + Z @ L.T
    port_daily_2d = sim_ret_3d @ weights  # (n_sim, n_days)
    port_value = init_cap * np.cumprod(1 + port_daily_2d, axis=1)

    peak = np.maximum.accumulate(port_value, axis=1)
    dd = (peak - port_value) / peak
    max_dd = dd.max(axis=1)

    final_val = port_value[:, -1]
    total_ret = final_val / init_cap - 1
    ann_ret = (1 + total_ret) ** (1 / years) - 1

    return {
        'annual_returns': ann_ret,
        'max_drawdowns': max_dd,
        'final_values': final_val,
        'valid_codes': valid_codes,
        'weights': weights,
    }

def print_report(results, init_cap=1_000_000, years=5):
    """打印预测报告"""
    rets = results['annual_returns']
    dds = results['max_drawdowns']
    vals = results['final_values']
    
    print("\n" + "=" * 70)
    print("  📈 蒙特卡洛收益率预测报告")
    print("=" * 70)
    
    print(f"\n  🎯 年化收益率分布:")
    print(f"    均值:    {np.mean(rets):.2%}")
    print(f"    中位数:  {np.median(rets):.2%}")
    print(f"    标准差:  {np.std(rets):.2%}")
    print(f"    5%分位:  {np.percentile(rets, 5):.2%}")
    print(f"    25%分位: {np.percentile(rets, 25):.2%}")
    print(f"    75%分位: {np.percentile(rets, 75):.2%}")
    print(f"    95%分位: {np.percentile(rets, 95):.2%}")
    
    print(f"\n  📉 最大回撤分布:")
    print(f"    均值:    {np.mean(dds):.2%}")
    print(f"    中位数:  {np.median(dds):.2%}")
    print(f"    5%分位:  {np.percentile(dds, 5):.2%}")
    print(f"    95%分位: {np.percentile(dds, 95):.2%}")
    print(f"    最坏5%:  超过 {np.percentile(dds, 95):.2%}")
    
    print(f"\n  💰 期末净值 (初始 ¥1,000,000):")
    print(f"    均值:    ¥{np.mean(vals):,.0f}")
    print(f"    中位数:  ¥{np.median(vals):,.0f}")
    print(f"    5%分位:  ¥{np.percentile(vals, 5):,.0f}")
    print(f"    95%分位: ¥{np.percentile(vals, 95):,.0f}")
    
    # 目标达成概率
    prob_ret_8 = np.mean(rets >= 0.08)
    prob_dd_10 = np.mean(dds <= 0.10)
    prob_dd_15 = np.mean(dds <= 0.15)
    prob_both = np.mean((rets >= 0.08) & (dds <= 0.10))
    prob_both_loose = np.mean((rets >= 0.08) & (dds <= 0.15))
    
    print(f"\n  📊 目标达成概率:")
    print(f"    年化收益 >= 8%:              {prob_ret_8:.1%}")
    print(f"    最大回撤 <= 10%:             {prob_dd_10:.1%}")
    print(f"    最大回撤 <= 15%:             {prob_dd_15:.1%}")
    print(f"    双目标(8%/10%):              {prob_both:.1%}")
    print(f"    双目标(8%/15%):              {prob_both_loose:.1%}")
    
    # 分年预测
    print(f"\n  📅 逐年净值预测 (中位数):")
    for yr in range(1, 6):
        yr_ret = (1 + np.median(rets)) ** yr - 1
        yr_val = init_cap * (1 + yr_ret)
        print(f"    第{yr}年末: ¥{yr_val:,.0f}  (累计 {yr_ret:.1%})")
    
    return {
        'expected_annual': np.mean(rets),
        'median_annual': np.median(rets),
        'expected_max_dd': np.mean(dds),
        'prob_8pct_return': prob_ret_8,
        'prob_dd_under_15': prob_dd_15,
        'prob_both_8_15': prob_both_loose,
        'final_median': np.median(vals),
    }

def main():
    init_cap = 1_000_000
    years = 5
    
    print("=" * 70)
    print("  量化策略系统 v4.3 — 蒙特卡洛收益率预测")
    print(f"  基于 portfolio.yaml 配置，预测未来 {years} 年表现")
    print(f"  运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    config = load_portfolio()
    assets = config.get('assets', [])
    weights_dict = {a['code']: a['target_weight'] for a in assets}
    codes = list(weights_dict.keys())
    
    print(f"\n📋 组合配置: {len(codes)}只标的")
    for a in assets:
        print(f"  {a['code']} {a['name']:<10} 权重 {a['target_weight']:.0%}")
    
    print(f"\n📥 加载缓存数据...")
    returns_df, coverage = load_cache_data(codes)
    
    if returns_df is None:
        print("  ❌ 无可用缓存数据!")
        return
    
    # 清理 NaT 索引
    returns_df = returns_df[returns_df.index.notna()]
    print(f"  ✅ 数据加载完成: {len(returns_df)} 个共同时段交易日")
    if len(returns_df) > 0:
        dmin = returns_df.index.min()
        dmax = returns_df.index.max()
        print(f"  📅 数据区间: {dmin.strftime('%Y-%m-%d') if pd.notna(dmin) else 'N/A'} ~ {dmax.strftime('%Y-%m-%d') if pd.notna(dmax) else 'N/A'}")
    
    for code in codes:
        if code in coverage:
            d = coverage[code]
            try:
                s = d[0].strftime('%Y-%m-%d') if pd.notna(d[0]) else '?'
                e = d[1].strftime('%Y-%m-%d') if pd.notna(d[1]) else '?'
                print(f"  ✅ {code}: {s}~{e} ({d[2]}条)")
            except Exception:
                print(f"  ✅ {code}: ({d[2]}条)")
        else:
            print(f"  ❌ {code}: 无缓存数据")
    
    missing = [c for c in codes if c not in coverage]
    if missing:
        print(f"\n  ⚠️ 缺失数据标的 ({len(missing)}只): {', '.join(missing)}")
        print(f"     蒙特卡洛将仅使用 {len(coverage)} 只有效标的，权重归一化")
    
    results = monte_carlo_sim(returns_df, weights_dict, years=years, n_sim=10000, init_cap=init_cap)
    if results is None:
        return
    
    pred = print_report(results, init_cap=init_cap, years=years)
    
    # 保存报告
    report_path = os.path.join(BASE_DIR, '..', '每日报告归档', 
                                datetime.now().strftime('%Y-%m-%d'),
                                f'收益率预测_{datetime.now().strftime("%Y%m%d")}.txt')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"蒙特卡洛收益率预测报告\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"预期年化收益: {pred['expected_annual']:.2%}\n")
        f.write(f"预期最大回撤: {pred['expected_max_dd']:.2%}\n")
        f.write(f"期末净值中位数: ¥{pred['final_median']:,.0f}\n")
        f.write(f"双目标达成概率(8%/15%): {pred['prob_both_8_15']:.1%}\n")
    
    print(f"\n  📁 报告已保存: {report_path}")
    return pred

if __name__ == '__main__':
    main()
