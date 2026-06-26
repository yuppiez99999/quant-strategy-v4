#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ModelScope量化模型集成 — 真实数据运行脚本

数据源优先级 (4级回退):
  P0: Wind MCP → 万得金融终端K线
  P1: 腾讯财经 → web.ifzq.gtimg.cn
  P2: 新浪财经 → money.finance.sina.com.cn
  P3: 东方财富 → push2his.eastmoney.com

模型: Kronos-small (24.7M参数, 金融K线预训练)
输出: Markdown分析报告

用法:
  python run_modelscope_real.py                    # 预测全部持仓标的
  python run_modelscope_real.py --stocks 000001,600519  # 预测指定股票
  python run_modelscope_real.py --pred-days 24     # 设置预测步长
"""

import sys
import os
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 添加utils到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))

import pandas as pd
import numpy as np

# ===================== 配置 =====================

# 量化组合持仓标的 (来自 v5.1 配置)
PORTFOLIO_STOCKS = [
    # 高端制造(含算力) 45%
    {'code': '300308', 'name': '中际旭创', 'sector': '高端制造(算力)'},
    {'code': '688041', 'name': '海光信息', 'sector': '高端制造(算力)'},
    {'code': '002371', 'name': '北方华创', 'sector': '高端制造'},
    {'code': '688981', 'name': '中芯国际', 'sector': '高端制造'},
    {'code': '300750', 'name': '宁德时代', 'sector': '高端制造'},
    {'code': '000425', 'name': '徐工机械', 'sector': '高端制造'},
    # 顺周期 20%
    {'code': '601088', 'name': '中国神华', 'sector': '顺周期'},
    {'code': '600219', 'name': '南山铝业', 'sector': '顺周期'},
    {'code': '600019', 'name': '宝钢股份', 'sector': '顺周期'},
    # 资源 20%
    {'code': '000408', 'name': '藏格矿业', 'sector': '资源'},
    # 防御 15%
    {'code': '600276', 'name': '恒瑞医药', 'sector': '防御'},
    {'code': '603259', 'name': '药明康德', 'sector': '防御'},
    {'code': '002422', 'name': '科伦药业', 'sector': '防御'},
]

# 主要宽基指数
BENCHMARK_INDICES = [
    {'code': '000300', 'name': '沪深300', 'type': 'index'},
    {'code': '000905', 'name': '中证500', 'type': 'index'},
    {'code': '000688', 'name': '科创50', 'type': 'index'},
]

# 报告输出目录
REPORT_DIR = os.path.join(os.path.dirname(__file__), 'reports', 'modelscope')
os.makedirs(REPORT_DIR, exist_ok=True)

# ===================== 数据获取 =====================

def fetch_stock_data(code: str, days: int = 200, verbose: bool = True) -> tuple:
    """
    获取A股日K线数据 — 4级回退
    
    返回: (DataFrame, source_name)
    """
    from kronos_predictor import (
        _fetch_from_wind, _fetch_from_tencent,
        _fetch_from_sina, _fetch_from_10jqka
    )
    
    sources = [
        ("Wind MCP", _fetch_from_wind),
        ("腾讯财经", _fetch_from_tencent),
        ("新浪财经", _fetch_from_sina),
        ("东方财富", _fetch_from_10jqka),
    ]
    
    for src_name, fetch_func in sources:
        if verbose:
            print(f"    >>> {src_name} ...", end=" ", flush=True)
        try:
            df = fetch_func(code, days)
            if df is not None and not df.empty and len(df) >= 30:
                if verbose:
                    print(f"[OK] {len(df)}条")
                return df, src_name
            else:
                if verbose:
                    print(f"[FAIL] 数据不足({len(df) if df is not None else 0}条)")
        except Exception as e:
            if verbose:
                print(f"[FAIL] {str(e)[:60]}")
    
    raise RuntimeError(f"所有数据源均无法获取 {code} 数据")


def fetch_index_data(code: str, days: int = 200) -> pd.DataFrame:
    """获取指数日K线 — 优先东方财富"""
    import requests
    
    if code.startswith('000'):
        secid = f"1.{code}"
    elif code.startswith('399'):
        secid = f"0.{code}"
    else:
        secid = f"1.{code}"
    
    url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
    end_date = datetime.now().strftime('%Y%m%d')
    begin_date = (datetime.now() - timedelta(days=days + 30)).strftime('%Y%m%d')
    
    response = requests.get(url, params={
        'secid': secid, 'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57',
        'klt': '101', 'fqt': '1', 'beg': begin_date, 'end': end_date,
        'lmt': str(days + 30),
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
    }, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://quote.eastmoney.com/',
    }, timeout=15)
    
    data = response.json()
    klines = data.get('data', {}).get('klines', [])
    
    records = []
    for line in klines:
        parts = line.split(',')
        records.append({
            'timestamp': parts[0],
            'open': float(parts[1]), 'close': float(parts[2]),
            'high': float(parts[3]), 'low': float(parts[4]),
            'volume': float(parts[5])
        })
    
    df = pd.DataFrame(records)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').tail(days).reset_index(drop=True)
    df['amount'] = df['volume'] * df['close']
    return df


# ===================== 信号解读 =====================

def interpret_signal(return_pct: float, threshold: float = 0.02) -> dict:
    """将预期收益率转化为可读信号"""
    if return_pct > threshold:
        strength = "强" if return_pct > threshold * 2 else "中"
        return {
            'signal': 'BUY',
            'icon': '🟢',
            'strength': strength,
            'description': f"预计上涨 {return_pct*100:.1f}%，建议关注买入机会"
        }
    elif return_pct < -threshold:
        strength = "强" if return_pct < -threshold * 2 else "中"
        return {
            'signal': 'SELL',
            'icon': '🔴',
            'strength': strength,
            'description': f"预计下跌 {abs(return_pct)*100:.1f}%，建议考虑减仓"
        }
    else:
        return {
            'signal': 'HOLD',
            'icon': '🟡',
            'strength': '—',
            'description': f"变动 {return_pct*100:+.1f}%，建议持仓观望"
        }


# ===================== 报告生成 =====================

def generate_report(results: list, data_sources: dict, timestamp: str) -> str:
    """生成Markdown分析报告"""
    
    # 按信号分组
    buys = [r for r in results if r['signal'] == 'BUY']
    sells = [r for r in results if r['signal'] == 'SELL']
    holds = [r for r in results if r['signal'] == 'HOLD']
    
    # 按收益排序
    buys.sort(key=lambda x: x['return_pct'], reverse=True)
    sells.sort(key=lambda x: x['return_pct'])
    holds.sort(key=lambda x: x['return_pct'], reverse=True)
    
    lines = []
    lines.append(f"# Kronos AI 量化预测报告")
    lines.append(f"")
    lines.append(f"> 生成时间: {timestamp}")
    lines.append(f"> 模型: Kronos-small (NeoQuasar) — 24.7M参数, MIT协议")
    lines.append(f"> 数据源: Wind MCP → 腾讯财经 → 新浪财经 → 东方财富 (4级回退)")
    lines.append(f"> 预测周期: 24个交易日")
    lines.append(f"")
    
    # 概览卡片
    lines.append("## 预测概览")
    lines.append("")
    total = len(results)
    buy_pct = len(buys) / total * 100 if total else 0
    sell_pct = len(sells) / total * 100 if total else 0
    
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 预测标的数 | {total} |")
    lines.append(f"| 买入信号 | {len(buys)} 只 ({buy_pct:.0f}%) |")
    lines.append(f"| 卖出信号 | {len(sells)} 只 ({sell_pct:.0f}%) |")
    lines.append(f"| 持有信号 | {len(holds)} 只 |")
    
    # 计算组合平均预期收益
    avg_return = np.mean([r['return_pct'] for r in results]) * 100
    lines.append(f"| 组合平均预期收益 | {avg_return:+.2f}% |")
    lines.append("")
    
    # 数据源使用统计
    lines.append("### 数据源使用情况")
    lines.append("")
    lines.append("| 标的 | 代码 | 数据源 | 数据条数 |")
    lines.append("|------|------|--------|---------|")
    for r in results:
        code = r['code']
        src = data_sources.get(code, '—')
        lines.append(f"| {r['name']} | {code} | {src} | {r.get('data_count', '—')} |")
    lines.append("")
    
    # 买入信号
    if buys:
        lines.append("## 🟢 买入信号")
        lines.append("")
        lines.append("| 标的 | 代码 | 板块 | 当前价 | 预测价 | 预期收益 | 信号强度 |")
        lines.append("|------|------|------|--------|--------|---------|---------|")
        for r in buys:
            lines.append(f"| {r['name']} | {r['code']} | {r['sector']} | {r['current_price']:.2f} | {r['predicted_price']:.2f} | **+{r['return_pct']*100:.2f}%** | {r['signal_strength']} |")
        lines.append("")
    
    # 卖出信号
    if sells:
        lines.append("## 🔴 卖出信号")
        lines.append("")
        lines.append("| 标的 | 代码 | 板块 | 当前价 | 预测价 | 预期收益 | 信号强度 |")
        lines.append("|------|------|------|--------|--------|---------|---------|")
        for r in sells:
            lines.append(f"| {r['name']} | {r['code']} | {r['sector']} | {r['current_price']:.2f} | {r['predicted_price']:.2f} | **{r['return_pct']*100:.2f}%** | {r['signal_strength']} |")
        lines.append("")
    
    # 持有信号
    if holds:
        lines.append("## 🟡 持有信号")
        lines.append("")
        lines.append("| 标的 | 代码 | 板块 | 当前价 | 预测价 | 预期收益 |")
        lines.append("|------|------|------|--------|--------|---------|")
        for r in holds:
            lines.append(f"| {r['name']} | {r['code']} | {r['sector']} | {r['current_price']:.2f} | {r['predicted_price']:.2f} | {r['return_pct']*100:+.2f}% |")
        lines.append("")
    
    # 板块汇总
    lines.append("## 板块预期收益汇总")
    lines.append("")
    sector_groups = {}
    for r in results:
        sector = r['sector']
        if sector not in sector_groups:
            sector_groups[sector] = []
        sector_groups[sector].append(r['return_pct'])
    
    lines.append("| 板块 | 标的数 | 平均预期收益 | 买入/卖出/持有 |")
    lines.append("|------|--------|-------------|---------------|")
    for sector, returns in sector_groups.items():
        avg = np.mean(returns) * 100
        b = sum(1 for r in returns if r > 0.02)
        s = sum(1 for r in returns if r < -0.02)
        h = len(returns) - b - s
        lines.append(f"| {sector} | {len(returns)} | {avg:+.2f}% | {b}/{s}/{h} |")
    lines.append("")
    
    # 风险提示
    lines.append("---")
    lines.append("")
    lines.append("## 风险提示")
    lines.append("")
    lines.append("1. **模型限制**: Kronos-small 参数量仅24.7M，预测精度有限，仅供参考")
    lines.append("2. **数据时效**: 预测基于历史K线模式，不包含突发新闻/政策影响")
    lines.append("3. **市场风险**: AI预测不能替代基本面分析，实盘交易需结合多种信息综合判断")
    lines.append("4. **回撤可能**: 任何预测模型都可能出现显著偏差，请设置止损位")
    lines.append("")
    lines.append(f"---")
    lines.append(f"*本报告由 Kronos-small (NeoQuasar/MIT) + 量化策略系统 v5.1 自动生成*")
    lines.append(f"*数据来源: Wind MCP / 腾讯财经 / 新浪财经 / 东方财富*")
    
    return "\n".join(lines)


# ===================== 主流程 =====================

def main():
    parser = argparse.ArgumentParser(description='Kronos量化预测 — 真实数据')
    parser.add_argument('--stocks', type=str, default=None,
                        help='指定股票代码，逗号分隔 (如 000001,600519)')
    parser.add_argument('--pred-days', type=int, default=24,
                        help='预测步长/交易日 (默认24)')
    parser.add_argument('--days', type=int, default=200,
                        help='历史数据天数 (默认200)')
    parser.add_argument('--threshold', type=float, default=0.02,
                        help='信号阈值 (默认0.02=2%%)')
    parser.add_argument('--device', type=str, default='cpu',
                        help='运行设备 (cpu/cuda)')
    parser.add_argument('--quiet', action='store_true',
                        help='静默模式')
    args = parser.parse_args()
    
    # 确定股票列表
    if args.stocks:
        codes = args.stocks.split(',')
        stocks = [{'code': c.strip(), 'name': c.strip(), 'sector': '自定义'} 
                  for c in codes]
    else:
        stocks = PORTFOLIO_STOCKS
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    quiet = args.quiet
    
    print("\n" + "=" * 70)
    print("  Kronos AI 量化预测系统 — 真实数据模式")
    print("=" * 70)
    print(f"  运行时间: {timestamp}")
    print(f"  数据源: Wind MCP → 腾讯财经 → 新浪财经 → 东方财富")
    print(f"  模型: Kronos-small (NeoQuasar) — 24.7M参数")
    print(f"  预测标的: {len(stocks)} 只")
    print(f"  预测步长: {args.pred_days} 个交易日")
    print("=" * 70)
    
    # ====== 第1阶段: 数据获取 ======
    print("\n[Phase 1/4] 获取真实K线数据 ...")
    print("-" * 50)
    
    stock_data = {}
    data_sources = {}
    fetch_errors = []
    
    for stock in stocks:
        code = stock['code']
        name = stock['name']
        if not quiet:
            print(f"\n  [{name} {code}]")
        
        try:
            df, src = fetch_stock_data(code, days=args.days, verbose=not quiet)
            stock_data[code] = df
            data_sources[code] = src
            if not quiet:
                print(f"  ✓ {name}: {len(df)}条 → 数据源: {src}")
        except Exception as e:
            fetch_errors.append((code, name, str(e)))
            if not quiet:
                print(f"  ✗ {name}: {str(e)[:80]}")
    
    print(f"\n  数据获取完成: {len(stock_data)}/{len(stocks)} 成功")
    
    if not stock_data:
        print("\n[ERROR] 所有数据源均失败，无法继续")
        # 打印详细错误
        print("\n  失败明细:")
        for code, name, err in fetch_errors:
            print(f"    - {name} ({code}): {err[:100]}")
        return
    
    # ====== 第2阶段: 加载Kronos模型 ======
    print(f"\n[Phase 2/4] 加载 Kronos-small 模型 ...")
    print("-" * 50)
    
    try:
        from kronos_predictor import KronosPredictor
        kp = KronosPredictor(device=args.device, verbose=not quiet)
        
        if kp.predictor_obj is None:
            print("[ERROR] Kronos模型加载失败，预测器未初始化")
            return
    except Exception as e:
        print(f"[ERROR] 加载失败: {e}")
        return
    
    # ====== 第3阶段: 执行预测 ======
    print(f"\n[Phase 3/4] 执行 Kronos 预测 ...")
    print("-" * 50)
    
    results = []
    
    for stock in stocks:
        code = stock['code']
        name = stock['name']
        sector = stock['sector']
        
        if code not in stock_data:
            results.append({
                'code': code, 'name': name, 'sector': sector,
                'signal': 'HOLD', 'return_pct': 0, 'current_price': 0,
                'predicted_price': 0, 'signal_strength': '—',
                'data_count': 0, 'error': '数据获取失败',
                'description': '无法获取数据，默认持有信号'
            })
            continue
        
        try:
            df = stock_data[code]
            signal, return_pct = kp.get_signal(df, pred_len=args.pred_days, 
                                                 threshold=args.threshold)
            
            current_price = df['close'].iloc[-1]
            predicted_price = current_price * (1 + return_pct)
            
            interp = interpret_signal(return_pct, args.threshold)
            
            result = {
                'code': code,
                'name': name,
                'sector': sector,
                'current_price': float(current_price),
                'predicted_price': float(predicted_price),
                'return_pct': float(return_pct),
                'signal': interp['signal'],
                'icon': interp['icon'],
                'signal_strength': interp['strength'],
                'description': interp['description'],
                'data_count': len(df),
                'data_source': data_sources.get(code, '—'),
            }
            results.append(result)
            
            if not quiet:
                print(f"  {interp['icon']} {name}: {current_price:.2f} → {predicted_price:.2f} "
                      f"({return_pct*100:+.2f}%) — {interp['signal']}")
            
        except Exception as e:
            print(f"  [ERROR] {name}: {str(e)[:80]}")
            results.append({
                'code': code, 'name': name, 'sector': sector,
                'signal': 'HOLD', 'return_pct': 0, 'current_price': 0,
                'predicted_price': 0, 'signal_strength': '—',
                'data_count': len(df) if 'df' in locals() else 0,
                'error': str(e)[:100],
                'description': f'预测失败: {str(e)[:60]}'
            })
    
    # ====== 第4阶段: 生成报告 ======
    print(f"\n[Phase 4/4] 生成分析报告 ...")
    print("-" * 50)
    
    report = generate_report(results, data_sources, timestamp)
    
    # 保存报告
    date_str = datetime.now().strftime('%Y%m%d')
    report_file = os.path.join(REPORT_DIR, f'kronos_prediction_{date_str}.md')
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"  报告已保存: {report_file}")
    
    # 打印汇总
    print("\n" + "=" * 70)
    print("  预测结果汇总")
    print("=" * 70)
    
    buys = [r for r in results if r['signal'] == 'BUY']
    sells = [r for r in results if r['signal'] == 'SELL']
    holds = [r for r in results if r['signal'] == 'HOLD']
    
    print(f"\n  🟢 买入信号 ({len(buys)} 只):")
    for r in buys:
        print(f"    {r['name']} ({r['code']}) [{r['sector']}] — +{r['return_pct']*100:.2f}%")
    
    print(f"\n  🔴 卖出信号 ({len(sells)} 只):")
    for r in sells:
        print(f"    {r['name']} ({r['code']}) [{r['sector']}] — {r['return_pct']*100:.2f}%")
    
    print(f"\n  🟡 持有信号 ({len(holds)} 只):")
    for r in holds:
        print(f"    {r['name']} ({r['code']}) [{r['sector']}] — {r['return_pct']*100:+.2f}%")
    
    # 数据源统计
    src_counts = {}
    for src in data_sources.values():
        src_counts[src] = src_counts.get(src, 0) + 1
    print(f"\n  数据源分布:")
    for src, cnt in src_counts.items():
        print(f"    {src}: {cnt} 只标的")
    
    # 错误报告
    if fetch_errors:
        print(f"\n  ⚠ 数据获取失败 ({len(fetch_errors)} 只):")
        for code, name, err in fetch_errors:
            print(f"    {name} ({code}): {err[:80]}")
    
    print(f"\n  报告路径: {report_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
