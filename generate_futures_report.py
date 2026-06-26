# -*- coding: utf-8 -*-
"""期货模拟持仓报告生成器"""
import json
import os
from datetime import datetime

BASE_DIR = r'e:\各种PY程序'
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
TRADE_LOG_DIR = os.path.join(BASE_DIR, '11_量化策略', 'trade_logs')

def load_sim_account():
    """加载模拟账户"""
    account_file = os.path.join(CONFIG_DIR, 'futures_sim_account.json')
    if os.path.exists(account_file):
        with open(account_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def load_trade_logs():
    """加载所有交易日志"""
    logs = []
    if os.path.exists(TRADE_LOG_DIR):
        for fname in os.listdir(TRADE_LOG_DIR):
            if fname.endswith('.json'):
                fpath = os.path.join(TRADE_LOG_DIR, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        logs.append(json.load(f))
                except:
                    pass
    return logs

def generate_report():
    """生成期货模拟持仓报告"""
    sim_account = load_sim_account()
    trade_logs = load_trade_logs()
    
    print("=" * 70)
    print("期货模拟持仓报告")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 账户概览
    if sim_account:
        capital = sim_account['account']['total_capital']
        cash = sim_account['cash']
        positions = sim_account['positions']
        
        print(f"\n[ACCOUNT] 账户概览")
        print("-" * 70)
        print(f"  总资金:     {capital:,.0f}")
        print(f"  已用保证金: {cash['margin_used']:,.0f} ({cash['utilization_rate']*100:.1f}%)")
        print(f"  可用资金:   {cash['available']:,.0f}")
        print(f"  持仓数量:   {len(positions)}个品种")
    
    # 持仓详情
    print(f"\n[POSITIONS] 持仓详情")
    print("-" * 70)
    
    for symbol, pos in positions.items():
        print(f"\n  {symbol} ({pos['name']})")
        print(f"    方向:       {pos['direction'].upper()}")
        print(f"    入场价:     {pos['entry_price']:,.0f}")
        print(f"    持仓数量:   {pos['quantity']}手")
        print(f"    保证金占用: {pos['margin_used']:,.0f}")
        print(f"    持仓市值:   {pos['position_value']:,.0f}")
        print(f"    止损价:     {pos['stop_loss']:,.0f}")
        print(f"    止盈价:     {pos['take_profit']:,.0f}")
        print(f"    AI评分:     {pos['score']}")
        print(f"    入场时间:   {pos['entry_time']}")
        print(f"    状态:       {pos['status']}")
    
    # 交易信号历史
    print(f"\n[HISTORY] 交易信号历史")
    print("-" * 70)
    
    by_symbol = {}
    for log in trade_logs:
        sym = log.get('symbol', '')
        if sym not in by_symbol:
            by_symbol[sym] = []
        by_symbol[sym].append(log)
    
    for symbol in sorted(by_symbol.keys()):
        sigs = by_symbol[symbol]
        print(f"\n  {symbol}: {len(sigs)}个信号")
        for s in sigs:
            print(f"    - {s.get('direction', '')} @ {s.get('entry_price', 0):,.0f} | {s.get('entry_time', '')}")
    
    # 风险提示
    print(f"\n{'=' * 70}")
    print("[WARNING] 风险提示")
    print("-" * 70)
    print("  1. 当前为模拟交易阶段,尚未接入实盘")
    print("  2. 期货杠杆交易存在高风险,请注意仓位管理")
    print("  3. 建议单品种仓位不超过总资金的20%")
    print("  4. 严格执行止损纪律")
    print("=" * 70)

if __name__ == '__main__':
    generate_report()
