#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单再平衡脚本 - 基于实时价格执行再平衡
使用新浪API获取实时价格,计算准确的市值偏差
"""

import os
import sys
import json
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 设置编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def get_sina_code(symbol):
    """将股票代码转换为新浪财经格式"""
    symbol = str(symbol).zfill(6)
    if symbol.startswith(('51', '58', '15', '6')):
        return f'sh{symbol}'
    elif symbol.startswith(('0', '3', '68')):
        return f'sz{symbol}'
    return f'sh{symbol}'


def get_realtime_price(symbol):
    """从新浪财经获取实时价格"""
    sina_code = get_sina_code(symbol)
    url = f'https://hq.sinajs.cn/list={sina_code}'
    try:
        response = requests.get(url, timeout=10, headers={'Referer': 'https://finance.sina.com.cn'})
        response.encoding = 'gbk'
        data = response.text
        if 'var hq_str_' in data and '=' in data:
            content = data.split('=', 1)[-1].strip().strip('"')
            if content and ',' in content:
                parts = content.split(',')
                if len(parts) >= 4 and parts[3]:
                    price = float(parts[3])
                    if price > 0:
                        return price
    except Exception:
        pass
    return None


def get_batch_prices(symbols, max_workers=10):
    """批量获取实时价格"""
    prices = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {executor.submit(get_realtime_price, sym): sym for sym in symbols}
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                price = future.result()
                if price and price > 0:
                    prices[symbol] = price
            except Exception:
                pass
    return prices


def calculate_market_value_category(symbol, category):
    """根据标的类型判断是否为权益类资产"""
    equity_categories = ['stock', 'etf', 'core_etf', 'high_mfg', 'cyclical', 'resource', 'growth']
    fixed_income_categories = ['bond', 'repo', 'fixed_income', 'convertible_bond']
    
    if category in equity_categories:
        return 'equity'
    elif category in fixed_income_categories:
        return 'fixed_income'
    elif symbol in ['204001', '131810', '204007']:
        return 'repo'
    elif symbol in ['000105', '000084', '000236', '000267', '340001', '001816', '040022']:
        return 'bond_fund'
    else:
        return 'equity'


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 加载持仓配置
    positions_path = os.path.join(base_dir, 'config', 'positions.json')
    
    print("=" * 80)
    print("再平衡分析 - 基于实时市场价格")
    print("=" * 80)
    
    # 1. 读取当前持仓和目标权重
    print("\n1. 当前持仓与目标配置")
    print("-" * 80)
    
    with open(positions_path, 'r', encoding='utf-8') as f:
        positions_data = json.load(f)
    
    current_positions = positions_data['positions']
    current_cash = positions_data.get('cash', 0)
    
    # 过滤出有实际持仓的标的
    active_positions = {code: pos for code, pos in current_positions.items() if pos.get('shares', 0) > 0}
    
    target_weights = {}
    total_target = 0
    for code, pos in active_positions.items():
        target_weights[code] = {
            'name': pos.get('name', code),
            'weight': pos.get('target_weight', 0.05),
            'category': pos.get('category', 'unknown'),
            'shares': pos['shares'],
            'avg_cost': pos['avg_cost']
        }
        total_target += pos.get('target_weight', 0)
        print(f"  {pos.get('name', code):<16} ({code}): 目标{pos.get('target_weight',0)*100:.1f}% | 持仓{pos['shares']:,}股")
    
    print(f"\n  活跃持仓数: {len(active_positions)}")
    print(f"  目标权重总和: {total_target*100:.1f}%")
    
    # 2. 获取实时价格
    print("\n2. 获取实时市场价格")
    print("-" * 80)
    
    symbols = list(target_weights.keys())
    print(f"  正在获取 {len(symbols)} 只标的的实时价格...")
    
    realtime_prices = get_batch_prices(symbols, max_workers=10)
    
    current_values = {}
    total_market_value = current_cash
    fetched_count = 0
    missing_count = 0
    
    for code, target in target_weights.items():
        shares = target['shares']
        avg_cost = target['avg_cost']
        name = target['name']
        
        # 优先使用实时价格,如果没有则使用成本价估算
        if code in realtime_prices:
            market_price = realtime_prices[code]
            fetched_count += 1
        else:
            # 无法获取实时价格,使用成本价作为近似(对于国债逆回购等固定收益类)
            market_price = avg_cost
            missing_count += 1
        
        value = shares * market_price
        current_values[code] = {
            'shares': shares,
            'market_price': market_price,
            'avg_cost': avg_cost,
            'value': value,
            'has_realtime': code in realtime_prices
        }
        total_market_value += value
    
    print(f"  成功获取实时价格: {fetched_count} 只")
    print(f"  使用成本价估算: {missing_count} 只")
    print(f"  总资产(含现金): {total_market_value:,.0f} 元")
    
    # 3. 计算再平衡需求
    print("\n3. 再平衡需求分析")
    print("-" * 80)
    print(f"  {'代码':<8} {'名称':<14} {'持仓市值':>12} {'实际权重':>10} {'目标权重':>10} {'偏差':>10} {'操作'}")
    print("  " + "-" * 76)
    
    orders = []
    total_sell = 0
    total_buy = 0
    
    for code, target in target_weights.items():
        target_value = total_market_value * target['weight']
        current_value = current_values[code]['value']
        current_shares = current_values[code]['shares']
        market_price = current_values[code]['market_price']
        avg_cost = current_values[code]['avg_cost']
        
        # 计算实际权重和偏差
        actual_weight = (current_value / total_market_value * 100) if total_market_value > 0 else 0
        target_weight_pct = target['weight'] * 100
        diff_weight = actual_weight - target_weight_pct
        diff_value = current_value - target_value
        
        # 标记操作类型
        if diff_weight > 1.0:
            action_text = f"卖出 {abs(diff_value):>12,.0f}"
        elif diff_weight < -1.0:
            action_text = f"买入 {diff_value:>12,.0f}"
        else:
            action_text = "持有"
        
        print(f"  {code:<8} {target['name']:<14} {current_value:>12,.0f} {actual_weight:>9.2f}% {target_weight_pct:>9.2f}% {diff_weight:>+9.2f}% {action_text}")
        
        # 生成订单(偏差超过1%)
        if abs(diff_weight) < 1.0:
            continue
        
        # 计算需要调整的股数
        if market_price > 0:
            if diff_weight > 0:  # 需要卖出
                diff_shares = int(abs(diff_value) / market_price / 100) * 100
                if diff_shares > current_shares:
                    diff_shares = current_shares - (current_shares % 100)  # 最多卖出全部
            else:  # 需要买入
                diff_shares = int(abs(diff_value) / market_price / 100) * 100
            
            if diff_shares > 0:
                if diff_weight > 0:
                    orders.append({
                        'action': 'SELL',
                        'code': code,
                        'name': target['name'],
                        'shares': diff_shares,
                        'price': market_price,
                        'amount': diff_shares * market_price,
                        'diff_weight': diff_weight
                    })
                    total_sell += diff_shares * market_price
                else:
                    orders.append({
                        'action': 'BUY',
                        'code': code,
                        'name': target['name'],
                        'shares': diff_shares,
                        'price': market_price,
                        'amount': diff_shares * market_price,
                        'diff_weight': diff_weight
                    })
                    total_buy += diff_shares * market_price
    
    # 4. 输出订单列表
    print("\n" + "=" * 80)
    print("再平衡交易指令")
    print("=" * 80)
    
    if orders:
        print(f"\n  {'序号':<4} {'操作':<6} {'代码':<8} {'名称':<14} {'股数':>8} {'预估价格':>10} {'金额':>12}")
        print("  " + "-" * 70)
        
        for i, order in enumerate(orders, 1):
            action = '买入' if order['action'] == 'BUY' else '卖出'
            print(f"  {i:<4} {action:<6} {order['code']:<8} {order['name']:<14} {order['shares']:>8} {order['price']:>10.3f} {order['amount']:>12,.0f}")
        
        print("\n  汇总:")
        print(f"    卖出总额: {total_sell:,.0f} 元")
        print(f"    买入总额: {total_buy:,.0f} 元")
        print(f"    净现金流: {total_sell - total_buy:,.0f} 元")
    else:
        print("\n  无需调整 - 所有持仓均在目标权重±1%范围内")
    
    # 5. 生成报告
    print("\n" + "=" * 80)
    print("生成再平衡报告")
    print("=" * 80)
    
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append(f"再平衡报告")
    report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append("一、当前状态")
    report_lines.append("-" * 60)
    report_lines.append(f"  总资产: {total_market_value:,.0f} 元")
    report_lines.append(f"  现金: {current_cash:,.0f} 元")
    report_lines.append(f"  持仓市值: {total_market_value - current_cash:,.0f} 元")
    report_lines.append(f"  活跃持仓数: {len(active_positions)}")
    report_lines.append(f"  实时价格获取: {fetched_count}/{len(symbols)}")
    report_lines.append("")
    report_lines.append("二、持仓明细与偏差分析")
    report_lines.append("-" * 60)
    report_lines.append(f"  {'代码':<8} {'名称':<14} {'市值':>12} {'实际权重':>10} {'目标权重':>10} {'偏差':>10}")
    report_lines.append("  " + "-" * 70)
    
    for code, target in target_weights.items():
        current_value = current_values[code]['value']
        actual_weight = (current_value / total_market_value * 100) if total_market_value > 0 else 0
        target_weight_pct = target['weight'] * 100
        diff_weight = actual_weight - target_weight_pct
        report_lines.append(f"  {code:<8} {target['name']:<14} {current_value:>12,.0f} {actual_weight:>9.2f}% {target_weight_pct:>9.2f}% {diff_weight:>+9.2f}%")
    
    report_lines.append("")
    report_lines.append("三、交易指令")
    report_lines.append("-" * 60)
    
    if orders:
        for i, order in enumerate(orders, 1):
            action = '买入' if order['action'] == 'BUY' else '卖出'
            report_lines.append(f"  {i}. {action} {order['name']} ({order['code']}): {order['shares']}股 @ {order['price']:.3f}元, 约{order['amount']:,.0f}元")
        
        report_lines.append("")
        report_lines.append("四、资金需求")
        report_lines.append("-" * 60)
        report_lines.append(f"  卖出回笼: {total_sell:,.0f} 元")
        report_lines.append(f"  买入支出: {total_buy:,.0f} 元")
        report_lines.append(f"  净需追加: {max(0, total_buy - total_sell):,.0f} 元")
    else:
        report_lines.append("  无需调整")
    
    report_lines.append("")
    report_lines.append("=" * 80)
    
    # 保存报告
    report_dir = os.path.join(base_dir, 'reports')
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f'rebalance_report_{datetime.now():%Y%m%d_%H%M%S}.md')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\n  报告已保存: {report_path}")
    print("\n" + "=" * 80)
    print("再平衡分析完成")
    print("=" * 80)


if __name__ == '__main__':
    main()
