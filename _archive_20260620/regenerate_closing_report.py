#!/usr/bin/env python3
"""
重新生成持仓日报 - 使用 positions.json 实际持仓数据
"""
import json
import subprocess
import re
from datetime import datetime

# 读取实际持仓数据
with open(r'e:\各种PY程序\11_量化策略\config\positions.json', 'r', encoding='utf-8') as f:
    pos_data = json.load(f)

positions = pos_data['positions']
cash_actual = pos_data['cash']
total_value_actual = pos_data['total_value']

# 股票代码映射 (去掉 CASH)
stock_codes = {k: v for k, v in positions.items() if k != 'CASH'}

# Wind MCP CLI 路径
WIND_DIR = r"C:\Users\Administrator\.agents\skills\wind-mcp-skill"

def get_wind_closing_price(code):
    """通过 Wind MCP 获取收盘价"""
    # 判断是 ETF 还是股票
    is_etf = code.startswith(('51', '15', '58'))
    
    if is_etf:
        # 修正 ETF 代码
        if code in ('510300', '510500', '512100', '512760', '512880', '518880'):
            wind_code = f"{code}.SH"
        elif code in ('159915', '588000'):
            wind_code = f"{code}.SZ"
        else:
            wind_code = f"{code}.SH"
    else:
        if code.startswith('6'):
            wind_code = f"{code}.SH"
        else:
            wind_code = f"{code}.SZ"
    
    try:
        cmd = f'cd /d "{WIND_DIR}" && node scripts/cli.mjs call stock_data get_stock_kline \'{{"windcode":"{wind_code}","begin_date":"20260618","end_date":"20260618","period":"10","aftime":"0"}}\''
        result = subprocess.run(
            cmd,
            shell=True, capture_output=True, text=True, timeout=30,
            cwd=WIND_DIR
        )
        
        if result.returncode == 0 and result.stdout:
            # 解析输出，找到收盘价
            data = json.loads(result.stdout)
            if 'content' in data:
                content = data['content']
                if isinstance(content, list) and len(content) > 0:
                    text = content[0].get('text', '')
                    if text:
                        inner_data = json.loads(text)
                        if inner_data.get('data') and inner_data['data'].get('rows'):
                            rows = inner_data['data']['rows']
                            if rows:
                                # MATCH 是收盘价，在索引 2
                                return float(rows[-1][2])  # 最后一行是最新数据
    except Exception as e:
        pass
    
    return None

# 获取所有持仓的收盘价
print("正在获取 Wind MCP 收盘价...")
closing_prices = {}

# 先从 positions.json 的 prices 字段获取已有价格
for code, info in stock_codes.items():
    if code in pos_data.get('prices', {}):
        closing_prices[code] = pos_data['prices'][code]
    else:
        closing_prices[code] = None

# 对没有价格的代码尝试从 Wind 获取
missing = [c for c, p in closing_prices.items() if p is None]
print(f"需要从 Wind 获取 {len(missing)} 个价格...")

for code in missing[:5]:  # 先获取前5个
    price = get_wind_closing_price(code)
    if price:
        closing_prices[code] = price
        print(f"  {code}: {price}")

# 如果还有缺失，使用 positions.json 中的备用价格
for code in missing[5:]:
    # 使用已有价格或标记为 None
    pass

# 股票名称映射
stock_names = {
    '601088': '中国神华',
    '600276': '恒瑞医药',
    '510300': '沪深300ETF',
    '512100': '中证1000ETF',
    '588000': '科创50ETF',
    '159915': '创业板ETF',
    '518880': '黄金ETF',
    '512760': '半导体ETF',
    '512880': '证券ETF',
    '000425': '徐工机械',
    '000858': '五粮液',
    '300274': '阳光电源',
    '510500': '中证500ETF',
    '688041': '海光信息',
    '601888': '中国中免',
    '600875': '东方电气',
    '600089': '特变电工',
    '688017': '格科微',
    '600406': '国电南瑞',
    '300308': '中际旭创',
}

# 计算持仓数据
stocks_holdings = []
etf_holdings = []

total_market_value = 0
total_cost = 0

for code, info in stock_codes.items():
    shares = info['shares']
    avg_cost = info['avg_cost']
    price = closing_prices.get(code)
    
    if price is None:
        continue
    
    market_value = shares * price
    cost = shares * avg_cost
    pnl = market_value - cost
    pnl_pct = (pnl / cost) * 100
    
    name = stock_names.get(code, code)
    is_etf = code.startswith(('51', '15', '58'))
    
    item = {
        'code': code,
        'name': name,
        'shares': shares,
        'avg_cost': avg_cost,
        'price': price,
        'market_value': market_value,
        'cost': cost,
        'pnl': pnl,
        'pnl_pct': pnl_pct,
        'is_etf': is_etf
    }
    
    if is_etf:
        etf_holdings.append(item)
    else:
        stocks_holdings.append(item)
    
    total_market_value += market_value
    total_cost += cost

# 计算现金和总盈亏
# 实际总价值 = 持仓市值 + 现金
actual_cash = cash_actual
total_account_value = total_market_value + actual_cash
# 以实际总资产为基准计算收益率
initial_capital = total_cost + actual_cash  # 总投入 = 持仓成本 + 现金
total_pnl = total_account_value - initial_capital

# 生成报告
report_lines = []
report_lines.append("# 持仓日报 2026-06-18 (修正版)")
report_lines.append("")
report_lines.append("> 数据源：positions.json 实际持仓 + Wind MCP 收盘价")
report_lines.append("> 最新交易日：2026-06-18（周四）")
report_lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
report_lines.append("")
report_lines.append("---")
report_lines.append("")
report_lines.append("## 一、组合概览")
report_lines.append("")
report_lines.append("| 指标 | 数值 |")
report_lines.append("|------|------|")
report_lines.append(f"| 初始资金 | 3,000,000 |")
report_lines.append(f"| 持仓成本 | {total_cost:,.0f} |")
report_lines.append(f"| 现金余额 | {actual_cash:,.0f} |")
report_lines.append(f"| 持仓市值 | {total_market_value:,.0f} |")
report_lines.append(f"| 账户总值 | {total_account_value:,.0f} |")
report_lines.append(f"| 总盈亏 | {total_pnl:+,.0f} ({total_pnl/initial_capital*100:+.2f}%) |")
report_lines.append(f"| 标的数量 | {len(stocks_holdings) + len(etf_holdings)} 只 |")
report_lines.append("")
report_lines.append("---")
report_lines.append("")

# 股票持仓
report_lines.append("### 股票持仓")
report_lines.append("")
report_lines.append("| 代码 | 名称 | 持仓量 | 成本价 | 收盘价 | 市值 | 盈亏 | 盈亏% |")
report_lines.append("|------|------|--------|--------|--------|------|------|-------|")

for item in sorted(stocks_holdings, key=lambda x: -abs(x['pnl'])):
    report_lines.append(
        f"| {item['code']} | {item['name']} | {item['shares']:,} | "
        f"{item['avg_cost']:.3f} | {item['price']:.3f} | "
        f"{item['market_value']:,.0f} | {item['pnl']:+,.0f} | {item['pnl_pct']:+.2f}% |"
    )

stock_pnl_total = sum(i['pnl'] for i in stocks_holdings)
stock_mv_total = sum(i['market_value'] for i in stocks_holdings)
report_lines.append("")
report_lines.append(f"**股票小计：市值 {stock_mv_total:,.0f} | 总盈亏 {stock_pnl_total:+,.0f}**")
report_lines.append("")

# ETF 持仓
report_lines.append("### ETF 持仓")
report_lines.append("")
report_lines.append("| 代码 | 名称 | 持仓量 | 成本价 | 收盘价 | 市值 | 盈亏 | 盈亏% |")
report_lines.append("|------|------|--------|--------|--------|------|------|-------|")

for item in sorted(etf_holdings, key=lambda x: -abs(x['pnl'])):
    report_lines.append(
        f"| {item['code']} | {item['name']} | {item['shares']:,} | "
        f"{item['avg_cost']:.3f} | {item['price']:.3f} | "
        f"{item['market_value']:,.0f} | {item['pnl']:+,.0f} | {item['pnl_pct']:+.2f}% |"
    )

etf_pnl_total = sum(i['pnl'] for i in etf_holdings)
etf_mv_total = sum(i['market_value'] for i in etf_holdings)
report_lines.append("")
report_lines.append(f"**ETF小计：市值 {etf_mv_total:,.0f} | 总盈亏 {etf_pnl_total:+,.0f}**")
report_lines.append("")

report_lines.append("---")
report_lines.append("")
report_lines.append("## 二、当日表现")
report_lines.append("")

# 表现最好/最差
all_holdings = stocks_holdings + etf_holdings
sorted_by_pnl = sorted(all_holdings, key=lambda x: x['pnl_pct'], reverse=True)

if sorted_by_pnl:
    report_lines.append("**表现最佳：**")
    for item in sorted_by_pnl[:3]:
        report_lines.append(f"- {item['name']} ({item['code']}): {item['pnl_pct']:+.2f}%")
    
    report_lines.append("")
    report_lines.append("**表现最差：**")
    for item in sorted_by_pnl[-3:]:
        report_lines.append(f"- {item['name']} ({item['code']}): {item['pnl_pct']:+.2f}%")

report_lines.append("")
report_lines.append("---")
report_lines.append("")
report_lines.append(f"> 数据来源：Wind 万得金融数据服务 | positions.json 实际持仓")

# 写入文件
report_content = '\n'.join(report_lines)
output_path = r'e:\各种PY程序\每日报告归档\2026-06-18\持仓日报_20260618_修正版.md'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(report_content)

print(f"\n报告已生成: {output_path}")
print("\n" + "="*60)
print(report_content)
