# -*- coding: utf-8 -*-
"""持仓统计报告 - PDF 生成器"""
import json, yaml, os, sys
from datetime import datetime
from fpdf import FPDF

# ── 加载数据 ─────────────────────────────────────────────
BASE = r'e:\各种PY程序\11_量化策略'
with open(os.path.join(BASE, 'config', 'positions.json'), 'r', encoding='utf-8') as f:
    pos_data = json.load(f)
with open(os.path.join(BASE, 'config', 'portfolio.yaml'), 'r', encoding='utf-8') as f:
    portfolio = yaml.safe_load(f)

positions = pos_data['positions']
prices = pos_data['prices']
cash = pos_data['cash']
last_update = pos_data['last_update']

target_weights = {}
for asset in portfolio['assets']:
    target_weights[asset['code']] = {'name': asset['name'], 'weight': asset['target_weight']}

code_to_name = {
    '510300': '沪深300ETF', '510500': '中证500ETF', '512100': '中证1000ETF',
    '588000': '科创50ETF', '159915': '创业板ETF', '688041': '海光信息',
    '300308': '中际旭创', '300274': '阳光电源', '002371': '北方华创',
    '688017': '绿的谐波', '600276': '恒瑞医药', '600089': '特变电工',
    '600875': '东方电气', '000425': '徐工机械', '600406': '国电南瑞',
    '600989': '宝丰能源', '515180': '中证红利ETF', '600036': '招商银行',
    '600900': '长江电力', '601088': '中国神华', '518880': '黄金ETF',
    '204007': '7天逆回购(沪)', '204001': '1天逆回购(沪)',
}

# ── 计算数据 ─────────────────────────────────────────────
rows = []
total_market_value = cash
total_cost = cash
total_pnl = 0.0

for code, pos in positions.items():
    shares = pos['shares']
    avg_cost = pos['avg_cost']
    if shares == 0 and avg_cost == 0:
        continue
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

# ── PDF 配置 ─────────────────────────────────────────────
class PDFReport(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A3')  # 横向A3容纳宽表
        # 注册中文字体 (SimHei 黑体)
        font_path = r'C:\Windows\Fonts\simhei.ttf'
        self.add_font('SimHei', '', font_path, uni=True)
        self.add_font('SimHei', 'B', font_path, uni=True)
        self.set_auto_page_break(True, 12)

    def header(self):
        if self.page_no() == 1:
            # 只在第一页显示标题头
            self.set_font('SimHei', 'B', 18)
            self.cell(0, 12, '持仓统计报告', new_x="LMARGIN", new_y="NEXT", align='C')
            self.set_font('SimHei', '', 9)
            today = datetime.now().strftime('%Y-%m-%d %H:%M')
            self.cell(0, 6, f'报告日期: {today}  |  数据更新: {last_update}', align='C', new_x="LMARGIN", new_y="NEXT")
            self.ln(4)
        else:
            self.set_font('SimHei', '', 8)
            self.cell(0, 5, f'持仓统计报告 (续) - {datetime.now().strftime("%Y-%m-%d")}', align='R', new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font('SimHei', '', 7)
        self.cell(0, 8, f'第 {self.page_no()} 页', align='C')

    def section_title(self, title):
        self.set_font('SimHei', 'B', 12)
        self.set_fill_color(40, 60, 100)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, f'  {title}', fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def kv_row(self, key, value, col_width=None):
        self.set_font('SimHei', 'B', 9)
        self.cell(28, 6, key + ':')
        self.set_font('SimHei', '', 9)
        w = col_width if col_width else 60
        self.cell(w, 6, value)
        return w


pdf = PDFReport()
pdf.add_page()

# ── 账户概览 ─────────────────────────────────────────────
pdf.section_title('账户概览')

pdf.set_font('SimHei', 'B', 10)
overview_data = [
    ('可用现金', f'￥{cash:,.2f}'),
    ('持仓成本', f'￥{total_cost - cash:,.2f}'),
    ('持仓市值', f'￥{total_market_value - cash:,.2f}'),
    ('账户总资产', f'￥{total_market_value:,.2f}'),
    ('持仓盈亏', f'￥{total_pnl:+,.2f}  ({total_pnl/(total_cost-cash)*100:+.2f}%)' if (total_cost-cash)>0 else 'N/A'),
    ('权益仓位', f'{(total_market_value-cash)/total_market_value*100:.2f}%'),
    ('现金占比', f'{cash/total_market_value*100:.2f}%'),
]

# 两列布局
col_count = 0
for k, v in overview_data:
    pdf.set_font('SimHei', 'B', 9)
    pdf.cell(22, 6, k + ':')
    pdf.set_font('SimHei', '', 9)
    pdf.cell(70, 6, v)
    col_count += 1
    if col_count % 3 == 0:
        pdf.ln(7)
if col_count % 3 != 0:
    pdf.ln(7)
pdf.ln(3)

# ── 持仓明细表头 ─────────────────────────────────────────
pdf.section_title('持仓明细 (按市值排序)')

col_widths = [17, 30, 16, 16, 16, 22, 22, 22, 18, 16, 16, 14, 12]
headers = ['代码', '名称', '持仓(股)', '成本价', '现价', '成本金额', '市值', '盈亏', '盈亏%', '实际权重', '目标权重', '偏离', '状态']

pdf.set_fill_color(230, 235, 245)
pdf.set_font('SimHei', 'B', 7.5)
for i, h in enumerate(headers):
    pdf.cell(col_widths[i], 7, h, border=1, fill=True, align='C')
pdf.ln()

# ── 持仓明细数据 ─────────────────────────────────────────
pdf.set_font('SimHei', '', 7.5)
pos_cost_base = total_cost - cash
pos_mv = total_market_value - cash

for r in rows:
    act_weight = r['market_value'] / total_market_value * 100
    tgt_weight = r['target_weight'] * 100
    deviation = act_weight - tgt_weight
    if abs(deviation) <= 1.0:
        status = 'OK'
        color = (40, 140, 40)
    elif abs(deviation) <= 3.0:
        status = '!'
        color = (200, 150, 0)
    else:
        status = 'X'
        color = (200, 40, 40)

    pnl_color = (40, 140, 40) if r['pnl'] >= 0 else (200, 40, 40)

    data = [
        r['code'],
        r['name'][:8],
        f"{r['shares']:,}",
        f"{r['avg_cost']:.2f}",
        f"{r['price']:.2f}",
        f"{r['cost_basis']/10000:.1f}万",
        f"{r['market_value']/10000:.1f}万",
        f"{r['pnl']/10000:+.1f}万",
        f"{r['pnl_pct']:+.1f}%",
        f"{act_weight:.1f}%",
        f"{tgt_weight:.1f}%",
        f"{deviation:+.1f}%",
    ]

    for i, d in enumerate(data):
        if i == 0:
            pdf.set_text_color(40, 80, 140)
        elif i in (7, 8):
            pdf.set_text_color(*pnl_color)
        else:
            pdf.set_text_color(0, 0, 0)
        pdf.cell(col_widths[i], 6, d, border=1, align='C')

    # 状态列
    pdf.set_text_color(*color)
    pdf.set_font('SimHei', 'B', 8)
    pdf.cell(col_widths[-1], 6, status, border=1, align='C')
    pdf.set_font('SimHei', '', 7.5)
    pdf.set_text_color(0, 0, 0)
    pdf.ln()

# 合计行
pdf.set_fill_color(245, 245, 250)
pdf.set_font('SimHei', 'B', 7.5)
total_data = ['', '持仓合计', '', '', '',
              f'{pos_cost_base/10000:.1f}万', f'{pos_mv/10000:.1f}万',
              f'{total_pnl/10000:+.1f}万',
              f'{total_pnl/pos_cost_base*100:+.1f}%' if pos_cost_base>0 else '',
              f'{pos_mv/total_market_value*100:.1f}%', '', '', '']
for i, d in enumerate(total_data):
    pdf.cell(col_widths[i], 6, d, border=1, fill=True, align='C')
pdf.cell(col_widths[-1], 6, '', border=1, fill=True, align='C')
pdf.ln(10)

# ── 再平衡建议 ─────────────────────────────────────────
pdf.section_title('再平衡建议 (阈值 +/-1.0%)')

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
                            f'需减仓 ￥{abs(deviation/100 * total_market_value):,.0f}'))
    elif deviation < -1.0:
        under_weight.append((r['name'], r['code'], deviation, r['market_value'],
                             f'需加仓 ￥{abs(deviation/100 * total_market_value):,.0f}'))

pdf.set_font('SimHei', '', 9)
if over_weight:
    pdf.set_text_color(200, 40, 40)
    pdf.cell(0, 6, f'超配/需减仓 ({len(over_weight)}只):', new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    for name, code, dev, mv, action in sorted(over_weight, key=lambda x: x[2], reverse=True):
        pdf.cell(0, 5.5, f'  {name}({code}): 超配 {dev:+.2f}%  |  市值 ￥{mv:,.0f}  |  {action}', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

if under_weight:
    pdf.set_text_color(40, 140, 40)
    pdf.cell(0, 6, f'低配/需加仓 ({len(under_weight)}只):', new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    for name, code, dev, mv, action in sorted(under_weight, key=lambda x: x[2]):
        pdf.cell(0, 5.5, f'  {name}({code}): 低配 {dev:+.2f}%  |  市值 ￥{mv:,.0f}  |  {action}', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

if not over_weight and not under_weight:
    pdf.cell(0, 6, '所有持仓均在目标权重 +/-1.0% 范围内，无需再平衡操作。', new_x="LMARGIN", new_y="NEXT")

# 未建仓
planned_not_held = [a for a in portfolio['assets'] if a['code'] != 'CASH' and a['code'] not in positions]
if planned_not_held:
    pdf.set_text_color(100, 100, 160)
    pdf.cell(0, 6, f'计划内但未建仓 ({len(planned_not_held)}只):', new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    for a in planned_not_held:
        pdf.cell(0, 5.5, f'  {a["name"]}({a["code"]}): 目标权重 {a["target_weight"]*100:.1f}%, 目标市值 ￥{a["target_weight"]*total_market_value:,.0f}', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

# ── 板块分布 ─────────────────────────────────────────
pdf.section_title('板块分布 (按市值)')

sectors = {
    '宽基指数': ['510300', '510500', '512100', '588000', '159915'],
    '黄金/避险': ['518880'],
    '数字经济/AI': ['300308', '688041'],
    '新能源/半导体': ['300274', '002371'],
    '防御/红利/内需': ['601088', '600276', '515180', '600036', '600900'],
    '能源/电力设备': ['600989', '600875', '600089'],
    '高端制造': ['000425', '688017'],
    '电网/数字能源': ['600406'],
    '逆回购(7天)': ['204007'],
}

sector_data = []
for sector, codes in sectors.items():
    mv = 0
    for code in codes:
        p = positions.get(code)
        if p and p['shares'] > 0:
            mv += p['shares'] * prices.get(code, p['avg_cost'])
    if mv > 0:
        sector_data.append((sector, mv, mv/total_market_value*100))
sector_data.sort(key=lambda x: x[1], reverse=True)

# 两列紧凑显示
pdf.set_font('SimHei', '', 9)
half = (len(sector_data) + 1) // 2
for i in range(half):
    left = sector_data[i]
    line = f'  {left[0]:<16} ￥{left[1]:>14,.0f}  ({left[2]:>6.2f}%)'
    if i + half < len(sector_data):
        right = sector_data[i + half]
        line += f'    {right[0]:<16} ￥{right[1]:>14,.0f}  ({right[2]:>6.2f}%)'
    pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")

pdf.ln(3)

# ── 盈亏排行 ─────────────────────────────────────────
# 左右两栏：TOP5盈利 与 TOP5亏损
y_start = pdf.get_y()
pdf.section_title('盈亏排行')

pdf.set_font('SimHei', 'B', 9)
pdf.set_text_color(40, 140, 40)
pdf.cell(130, 6, '盈利 TOP5', align='C')
pdf.set_text_color(200, 40, 40)
pdf.cell(130, 6, '亏损 TOP5', align='C', new_x="LMARGIN", new_y="NEXT")
pdf.set_text_color(0, 0, 0)

top_gain = sorted(rows, key=lambda x: x['pnl'], reverse=True)[:5]
top_loss = sorted(rows, key=lambda x: x['pnl'])[:5]

for i in range(5):
    pdf.set_font('SimHei', '', 8.5)
    if i < len(top_gain):
        g = top_gain[i]
        g_text = f'  {g["name"]}({g["code"]}): ￥{g["pnl"]:+,.0f} ({g["pnl_pct"]:+.1f}%)'
    else:
        g_text = ''
    if i < len(top_loss) and top_loss[i]['pnl'] < 0:
        l = top_loss[i]
        l_text = f'  {l["name"]}({l["code"]}): ￥{l["pnl"]:+,.0f} ({l["pnl_pct"]:+.1f}%)'
    else:
        l_text = ''
    pdf.cell(130, 6, g_text)
    pdf.cell(130, 6, l_text, new_x="LMARGIN", new_y="NEXT")

pdf.ln(5)

# ── 数据源 ─────────────────────────────────────────────
pdf.set_font('SimHei', '', 7)
pdf.set_text_color(100, 100, 100)
pdf.cell(0, 5, f'数据源: positions.json (更新: {last_update}) + portfolio.yaml  |  生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', new_x="LMARGIN", new_y="NEXT")

# ── 保存 PDF ─────────────────────────────────────────────
today_str = datetime.now().strftime('%Y%m%d_%H%M%S')
output_path = os.path.join(BASE, 'data', f'position_report_{today_str}.pdf')
pdf.output(output_path)
print(f'PDF报告已生成: {output_path}')
print(f'文件大小: {os.path.getsize(output_path)/1024:.1f} KB')
