import json
import yaml

with open(r'e:\各种PY程序\11_量化策略\config\positions.json', 'r', encoding='utf-8') as f:
    pos_data = json.load(f)

with open(r'e:\各种PY程序\11_量化策略\config\portfolio.yaml', 'r', encoding='utf-8') as f:
    portfolio = yaml.safe_load(f)

positions = pos_data['positions']
prices = pos_data['prices']
cash = pos_data['cash']
last_update = pos_data['last_update']

target_weights = {}
for asset in portfolio['assets']:
    target_weights[asset['code']] = {'name': asset['name'], 'weight': asset['target_weight']}

code_to_name = {
    '601088': '中国神华', '600276': '恒瑞医药', '510300': '沪深300ETF', '512100': '中证1000ETF',
    '588000': '科创50ETF', '159915': '创业板ETF', '518880': '黄金ETF', '512760': '半导体ETF',
    '512880': '证券ETF', '000425': '徐工机械', '000858': '五粮液', '300274': '阳光电源',
    '510500': '中证500ETF', '688041': '海光信息', '601888': '中国中免', '600875': '东方电气',
    '600089': '特变电工', '688017': '绿的谐波', '600406': '国电南瑞',
}

rows = []
total_market_value = cash
total_cost = cash
total_pnl = 0.0

for code, pos in positions.items():
    shares = pos['shares']
    avg_cost = pos['avg_cost']
    current_price = prices.get(code, avg_cost)
    name = code_to_name.get(code, target_weights.get(code, {}).get('name', code))
    cost_basis = shares * avg_cost
    market_value = shares * current_price
    pnl = market_value - cost_basis
    pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
    target_weight = target_weights.get(code, {}).get('weight', 0)
    total_cost += cost_basis
    total_market_value += market_value
    total_pnl += pnl
    rows.append({
        'code': code, 'name': name, 'shares': shares,
        'avg_cost': avg_cost, 'price': current_price,
        'cost_basis': cost_basis, 'market_value': market_value,
        'pnl': pnl, 'pnl_pct': pnl_pct, 'target_weight': target_weight,
    })

rows.sort(key=lambda x: x['market_value'], reverse=True)

print('=' * 120)
print('  2026-06-16 持仓统计报告  | 更新时间:', last_update)
print('=' * 120)

print('\n  [账户概览]')
print('-' * 120)
print('  现金储备:  ¥{:>14,.2f}  |  持仓成本:  ¥{:>14,.2f}'.format(cash, total_cost - cash))
print('  总资产:    ¥{:>14,.2f}  |  总盈亏:    ¥{:>+14,.2f} ({:+.2f}%)'.format(
    total_market_value, total_pnl, total_pnl/(total_cost)*100))
print('  权益仓位:  {:>6.2f}%       |  现金占比:  {:>6.2f}%'.format(
    (total_market_value - cash)/total_market_value*100, cash/total_market_value*100))

print('\n  [持仓明细] 按市值排序  |  权重单位:%')
print('-' * 120)
h = '{:^10} {:^12} {:^8} {:^8} {:^8} {:^12} {:^12} {:^10} {:^8} {:^6} {:^6} {:^7}'
print(h.format('代码', '名称', '股数', '成本', '现价', '成本金额', '市值', '盈亏', '盈亏%', '实际', '目标', '偏离'))
print('-' * 120)

for r in rows:
    act_weight = r['market_value'] / total_market_value * 100
    tgt_weight = r['target_weight'] * 100
    deviation = act_weight - tgt_weight
    if abs(deviation) <= 1.0:
        status = '[OK]'
    elif abs(deviation) <= 3.0:
        status = '[!] '
    else:
        status = '[X] '
    line = '{:>2} {:<10} {:<12} {:>8,.0f} {:>8.2f} {:>8.2f} {:>12,.2f} {:>12,.2f} {:>+10,.2f} {:>+7.2f} {:>6.2f} {:>6.2f} {:>+7.2f}'
    print(line.format(status, r['code'], r['name'], r['shares'], r['avg_cost'],
                       r['price'], r['cost_basis'], r['market_value'], r['pnl'],
                       r['pnl_pct'], act_weight, tgt_weight, deviation))

print('-' * 120)
line = '{:>14} {:<12} {:>8} {:>8} {:>8} {:>12,.2f} {:>12,.2f} {:>+10,.2f} {:>+7.2f} {:>6.2f} {:>6} {:>7}'
pos_cost_base = total_cost - cash
pos_mv = total_market_value - cash
print(line.format('', '持仓合计', '', '', '', pos_cost_base, pos_mv, total_pnl,
                   total_pnl/pos_cost_base*100 if pos_cost_base > 0 else 0, pos_mv/total_market_value*100, '', ''))

print('\n  [再平衡建议] 阈值: +/-1.0%')
print('-' * 120)

over_weight = []
under_weight = []
for r in rows:
    act_weight = r['market_value'] / total_market_value * 100
    tgt_weight = r['target_weight'] * 100
    deviation = act_weight - tgt_weight
    if tgt_weight == 0 and r['market_value'] > 0:
        over_weight.append((r['name'], r['code'], deviation, r['market_value'], '计划外持仓'))
    elif deviation > 1.0:
        over_weight.append((r['name'], r['code'], deviation, r['market_value'],
                            '需减仓 ¥{:,.0f}'.format(abs(deviation/100 * total_market_value))))
    elif deviation < -1.0:
        under_weight.append((r['name'], r['code'], deviation, r['market_value'],
                             '需加仓 ¥{:,.0f}'.format(abs(deviation/100 * total_market_value))))

if over_weight:
    print('  [超配/需减仓] ({}只):'.format(len(over_weight)))
    for name, code, dev, mv, action in sorted(over_weight, key=lambda x: x[2], reverse=True):
        print('    - {}({}): 超配 {:+.2f}%  |  {}'.format(name, code, dev, action))

if under_weight:
    print('  [低配/需加仓] ({}只):'.format(len(under_weight)))
    for name, code, dev, mv, action in sorted(under_weight, key=lambda x: x[2]):
        print('    - {}({}): 低配 {:+.2f}%  |  {}'.format(name, code, dev, action))

planned_not_held = [a for a in portfolio['assets'] if a['code'] != 'CASH' and a['code'] not in positions]
if planned_not_held:
    print('\n  [计划内但未建仓] ({}只):'.format(len(planned_not_held)))
    for a in planned_not_held:
        print('    - {}({}): 目标权重 {:.2f}%  |  目标市值 ¥{:,.0f}'.format(
            a['name'], a['code'], a['target_weight']*100, a['target_weight']*total_market_value))

print('\n  [板块分布]')
print('-' * 120)
sectors = {
    '宽基指数': ['510300', '510500', '512100', '588000', '159915'],
    '黄金/避险': ['518880'],
    '数字经济/AI': ['300308', '688041'],
    '新能源/半导体': ['300274', '002371', '512760'],
    '防御/红利/内需': ['601088', '600276', '601888', '000858'],
    '能源/电力设备': ['600989', '600875', '600089', '600995'],
    '高端制造': ['000425', '688017'],
    '电网/数字能源': ['600406'],
    '证券/金融': ['512880'],
}
sector_mv = {}
for sector, codes in sectors.items():
    mv = sum(p['shares'] * prices.get(p_code, p['avg_cost']) for p_code, p in positions.items() if p_code in codes)
    sector_mv[sector] = mv
for sector, mv in sorted(sector_mv.items(), key=lambda x: x[1], reverse=True):
    if mv > 0:
        print('    {:<16}  ¥{:>12,.2f}  ({:>6.2f}%)'.format(sector, mv, mv/total_market_value*100))

print('\n  [盈亏TOP5]')
print('-' * 120)
for r in sorted(rows, key=lambda x: x['pnl'], reverse=True)[:5]:
    print('    + {}({}):  ¥{:>+10,.2f}  ({:+.2f}%)'.format(r['name'], r['code'], r['pnl'], r['pnl_pct']))
print('\n  [亏损TOP5]')
for r in sorted(rows, key=lambda x: x['pnl'])[:5]:
    if r['pnl'] < 0:
        print('    - {}({}):  ¥{:>+10,.2f}  ({:+.2f}%)'.format(r['name'], r['code'], r['pnl'], r['pnl_pct']))

print('\n' + '=' * 120)
print('  数据源: positions.json (2026-06-16 11:25) + portfolio.yaml')
print('=' * 120)
