# -*- coding: utf-8 -*-
"""
生成12只标的量化策略的持仓报告
"""

import yaml
import os
import sys
import io

def generate_position_report():
    # Windows控制台UTF-8编码修复
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'portfolio.yaml')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    capital = 1000000  # 初始资金100万
    
    print("=" * 70)
    print("                    12只标的量化策略 - 持仓表")
    print("=" * 70)
    print(f"初始资金: ¥{capital:,.0f}")
    print(f"标的数量: {len(config['assets'])}只")
    print("-" * 70)
    
    print(f"{'序号':<4} {'股票名称':<12} {'代码':<10} {'权重':<8} {'持仓金额':<12} {'风险等级':<8}")
    print("-" * 70)
    
    total_allocated = 0
    positions = []
    
    for i, asset in enumerate(config['assets'], 1):
        weight = asset['target_weight']
        amount = capital * weight
        total_allocated += amount
        
        risk_level = "低" if asset['risk_weight'] < 0.15 else \
                     "中" if asset['risk_weight'] < 0.25 else \
                     "中高" if asset['risk_weight'] < 0.30 else "高"
        
        positions.append({
            'index': i,
            'name': asset['name'],
            'code': asset['code'],
            'weight': f"{weight*100:.1f}%",
            'amount': f"¥{amount:,.0f}",
            'risk': risk_level,
            'risk_weight': asset['risk_weight']
        })
        
        print(f"{i:<4} {asset['name']:<12} {asset['code']:<10} {weight*100:<8.1f}% ¥{amount:<12,.0f} {risk_level:<8}")
    
    cash = capital - total_allocated
    print("-" * 70)
    print(f"{'合计':<26} {'-':<10} {100:<8.1f}% ¥{total_allocated:<12,.0f}")
    print(f"{'现金':<26} {'-':<10} {cash/capital*100:<8.1f}% ¥{cash:<12,.0f}")
    print("=" * 70)
    
    print("\n【风险分布统计】")
    print("-" * 50)
    risk_counts = {'低': 0, '中': 0, '中高': 0, '高': 0}
    risk_weights = {'低': 0, '中': 0, '中高': 0, '高': 0}
    
    for pos in positions:
        risk = pos['risk']
        risk_counts[risk] += 1
        risk_weights[risk] += float(pos['weight'].replace('%', ''))
    
    print(f"{'风险等级':<8} {'标的数':<8} {'权重占比':<10}")
    print("-" * 50)
    for level in ['低', '中', '中高', '高']:
        print(f"{level:<8} {risk_counts[level]:<8} {risk_weights[level]:<10.1f}%")
    
    print("\n【资产类型分布】")
    print("-" * 50)
    type_counts = {}
    type_weights = {}
    
    for asset in config['assets']:
        asset_type = asset['type']
        if asset_type not in type_counts:
            type_counts[asset_type] = 0
            type_weights[asset_type] = 0
        type_counts[asset_type] += 1
        type_weights[asset_type] += asset['target_weight'] * 100
    
    print(f"{'资产类型':<10} {'标的数':<8} {'权重占比':<10}")
    print("-" * 50)
    for asset_type, count in type_counts.items():
        print(f"{asset_type:<10} {count:<8} {type_weights[asset_type]:<10.1f}%")
    
    print("\n【持仓明细(假设初始价格)】")
    print("-" * 70)
    print(f"{'股票名称':<12} {'代码':<10} {'假设价格':<10} {'持仓数量':<10} {'市值':<12}")
    print("-" * 70)
    
    mock_prices = {
        '601088': 28.5,   # 中国神华
        '600989': 15.2,   # 宝丰能源
        '600875': 22.8,   # 东方电气
        '600089': 18.5,   # 特变电工
        '600406': 25.6,   # 国电南瑞
        '600268': 12.8,   # 国电南自
        '300274': 78.5,   # 阳光电源
        '600995': 8.9,    # 南网储能
        '002371': 185.0,  # 北方华创
        '600276': 45.2,   # 恒瑞医药
        '688017': 68.5,   # 绿的谐波
        '000425': 6.8,    # 徐工机械
    }
    
    total_market_value = 0
    for asset in config['assets']:
        code = asset['code']
        price = mock_prices.get(code, 10.0)
        amount = capital * asset['target_weight']
        shares = int(amount / price / 100) * 100
        market_value = shares * price
        total_market_value += market_value
        
        print(f"{asset['name']:<12} {code:<10} ¥{price:<10.2f} {shares:<10} ¥{market_value:<12,.0f}")
    
    print("-" * 70)
    print(f"{'合计':<22} {'-':<10} {'-':<10} ¥{total_market_value:<12,.0f}")
    print("=" * 70)
    
    print("\n【说明】")
    print("• 以上持仓数量基于假设价格计算，实际数量以建仓时价格为准")
    print("• 持仓会每15个交易日根据策略重新平衡")
    print("• 回撤超过7%时自动降仓至50%")

if __name__ == "__main__":
    generate_position_report()
