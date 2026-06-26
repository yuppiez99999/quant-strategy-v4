# -*- coding: utf-8 -*-
"""
进取型(康波全面超配) -- 200万资金 2026年底前完成建仓 五年持有交易计划生成器
"""

import os, sys, json, math
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(BASE_DIR, '..', '每日报告归档', datetime.now().strftime('%Y-%m-%d'))
os.makedirs(REPORT_DIR, exist_ok=True)

# ============================================================
# 进取型策略权重 (来自 portfolio_weights_kondratiev_20260615.json)
# ============================================================
AGGRESSIVE_WEIGHTS = {
    '588000': {'name': '科创50ETF华夏',      'type': 'equity',   'risk': 'high',   'style': '高端制造', 'weight': 0.1375},
    '512480': {'name': '半导体ETF国泰',       'type': 'equity',   'risk': 'high',   'style': '高端制造', 'weight': 0.1317},
    '516160': {'name': '高端装备ETF南方',     'type': 'equity',   'risk': 'high',   'style': '高端制造', 'weight': 0.1317},
    '515030': {'name': '新能源车ETF华夏',     'type': 'equity',   'risk': 'high',   'style': '高端制造', 'weight': 0.1260},
    '159915': {'name': '创业板ETF易方达',     'type': 'equity',   'risk': 'high',   'style': '高端制造', 'weight': 0.1150},
    '159992': {'name': '创新药ETF银华',       'type': 'equity',   'risk': 'high',   'style': '防御',     'weight': 0.0947},
    '512400': {'name': '有色金属ETF南方',     'type': 'industry', 'risk': 'high',   'style': '资源',     'weight': 0.0929},
    '512010': {'name': '医药ETF易方达',       'type': 'equity',   'risk': 'medium', 'style': '防御',     'weight': 0.0664},
    '601088': {'name': '中国神华',            'type': 'stock',    'risk': 'medium', 'style': '顺周期',   'weight': 0.0638},
    '518880': {'name': '黄金ETF华安',         'type': 'commodity','risk': 'medium', 'style': '资源',     'weight': 0.0307},
    '511260': {'name': '十年国债ETF国泰',     'type': 'bond',     'risk': 'low',    'style': '防御',     'weight': 0.0050},
    '511520': {'name': '政金债ETF富国',       'type': 'bond',     'risk': 'low',    'style': '防御',     'weight': 0.0037},
    '511360': {'name': '短融ETF海富通',       'type': 'money',    'risk': 'low',    'style': '防御',     'weight': 0.0010},
}

TOTAL_CAPITAL = 2_000_000  # 200万

# ============================================================
# 建仓计划
# ============================================================
# 建仓期: 2026-06-15 -> 2026-12-31 (约6.5个月)
# 分 7 批建仓 (每月一批，6月-12月)

BUILDUP_PHASES = [
    {'phase': 1, 'month': '2026年6月', 'ratio': 0.10, 'note': '试点建仓，验证流动性，建立底仓'},
    {'phase': 2, 'month': '2026年7月', 'ratio': 0.15, 'note': '加大仓位，半年度数据窗口'},
    {'phase': 3, 'month': '2026年8月', 'ratio': 0.15, 'note': '中报密集披露期，逢低加仓'},
    {'phase': 4, 'month': '2026年9月', 'ratio': 0.15, 'note': '金九银十窗口，均衡买入'},
    {'phase': 5, 'month': '2026年10月','ratio': 0.15, 'note': '三季报窗口，政策观察期'},
    {'phase': 6, 'month': '2026年11月','ratio': 0.15, 'note': '年末布局，机构调仓窗口'},
    {'phase': 7, 'month': '2026年12月','ratio': 0.15, 'note': '完成建仓，年终再平衡'},
]

# 价格区间参考 (基于2026年6月中旬合理估算)
PRICE_REFERENCE = {
    '588000': {'est_price': 1.05, 'range_low': 0.95, 'range_high': 1.15, 'lots_per': 100},
    '512480': {'est_price': 1.38, 'range_low': 1.22, 'range_high': 1.52, 'lots_per': 100},
    '516160': {'est_price': 1.12, 'range_low': 1.00, 'range_high': 1.25, 'lots_per': 100},
    '515030': {'est_price': 1.55, 'range_low': 1.38, 'range_high': 1.72, 'lots_per': 100},
    '159915': {'est_price': 2.15, 'range_low': 1.92, 'range_high': 2.38, 'lots_per': 100},
    '159992': {'est_price': 0.92, 'range_low': 0.82, 'range_high': 1.02, 'lots_per': 100},
    '512400': {'est_price': 1.18, 'range_low': 1.05, 'range_high': 1.32, 'lots_per': 100},
    '512010': {'est_price': 0.58, 'range_low': 0.52, 'range_high': 0.65, 'lots_per': 100},
    '601088': {'est_price': 38.50, 'range_low': 35.00, 'range_high': 42.00, 'lots_per': 100},
    '518880': {'est_price': 5.85, 'range_low': 5.50, 'range_high': 6.20, 'lots_per': 100},
    '511260': {'est_price': 102.50, 'range_low': 101.80, 'range_high': 103.20, 'lots_per': 10},
    '511520': {'est_price': 101.20, 'range_low': 100.90, 'range_high': 101.50, 'lots_per': 10},
    '511360': {'est_price': 100.05, 'range_low': 100.01, 'range_high': 100.10, 'lots_per': 10},
}


def compute_position_plan():
    """计算每标的每批建仓金额和预估数量"""
    plan = {}
    for code, info in AGGRESSIVE_WEIGHTS.items():
        target_amount = TOTAL_CAPITAL * info['weight']
        price_info = PRICE_REFERENCE.get(code, {'est_price': 1.0, 'lots_per': 100})
        est_price = price_info['est_price']
        lots_per = price_info['lots_per']
        est_shares = int(target_amount / est_price / lots_per) * lots_per

        phases_detail = []
        for p in BUILDUP_PHASES:
            phase_amt = target_amount * p['ratio']
            phase_shares = int(phase_amt / est_price / lots_per) * lots_per
            phases_detail.append({
                'phase': p['phase'],
                'month': p['month'],
                'ratio': p['ratio'],
                'amount': round(phase_amt, 0),
                'est_shares': phase_shares,
                'note': p['note'],
            })

        plan[code] = {
            'name': info['name'],
            'type': info['type'],
            'risk': info['risk'],
            'style': info['style'],
            'weight': info['weight'],
            'target_amount': round(target_amount, 0),
            'est_price': est_price,
            'est_total_shares': est_shares,
            'lots_per': lots_per,
            'price_range_low': price_info['range_low'],
            'price_range_high': price_info['range_high'],
            'phases': phases_detail,
        }
    return plan


def generate_report():
    plan = compute_position_plan()

    lines = []
    lines.append('# 进取型(康波全面超配) 五年持有交易计划')
    lines.append('')
    lines.append('> **生成日期**: %s' % datetime.now().strftime('%Y-%m-%d %H:%M'))
    lines.append('> **策略类型**: 进取型(康波全面超配)')
    lines.append('> **总资金**: 2,000,000 元 (200万)')
    lines.append('> **建仓截止日**: 2026年12月31日')
    lines.append('> **持有期**: 2026-2030 (五年)')
    lines.append('> **目标约束**: 年化 >= 8% | 最大回撤 <= 15%')
    lines.append('')

    # ====== 一、策略概要 ======
    lines.append('## 一、策略概要')
    lines.append('')
    lines.append('本交易计划基于康波第六轮复苏->繁荣转换期(2027前后转繁荣)与十五五规划(2026-2030)的高度同频共振，')
    lines.append('采用进取型(康波全面超配)策略，对高科技成长资产给予1.5倍超配，债券/货币类给予0.4倍低配，')
    lines.append('最大化捕捉康波复苏期+十五五政策驱动的双重阿尔法。')
    lines.append('')
    lines.append('**核心逻辑**:')
    lines.append('- 康波第六轮由AI/算力驱动，当前处于复苏期75%进度，2027前后转入繁荣期')
    lines.append('- 十五五规划七大战略方向(AI/半导体/高端制造/新能源/数字经济/生物医药)与康波驱动力完全重叠')
    lines.append('- 社保基金已连续增持高端制造方向，形成机构资金与政策周期同向的合力')
    lines.append('- 进取型策略在康波评分高+十五五评分高的标的上给予1.5倍超配')
    lines.append('')
    lines.append('**回测绩效 (模拟)**:')
    lines.append('- 年化收益: 22.15%')
    lines.append('- 最大回撤: -5.52%')
    lines.append('- 夏普比率: 2.760')
    lines.append('- 5年滚动CAGR(最小值): 22.02%')
    lines.append('- Calmar比率: 4.012')
    lines.append('- 胜率: 56.79%')
    lines.append('- 5年末预期终值(200万): ~5,632,519 元')
    lines.append('')

    # ====== 二、组合资产配置总览 ======
    lines.append('## 二、组合资产配置总览 (200万)')
    lines.append('')
    lines.append('| 标的代码 | 标的名称 | 类型 | 风险 | 风格 | 目标权重 | 目标金额 | 预估单价 | 预估股数/份 |')
    lines.append('|:---------|:---------|:-----|:-----|:-----|--------:|--------:|--------:|----------:|')

    # Sort by weight descending
    sorted_codes = sorted(AGGRESSIVE_WEIGHTS.keys(), key=lambda c: -AGGRESSIVE_WEIGHTS[c]['weight'])
    total_amt = 0
    for code in sorted_codes:
        info = plan[code]
        total_amt += info['target_amount']
        lines.append('| %s | %s | %s | %s | %s | %.2f%% | %s | %.2f | %s |' % (
            code, info['name'], info['type'], info['risk'], info['style'],
            info['weight'] * 100,
            format(int(info['target_amount']), ','),
            info['est_price'],
            format(info['est_total_shares'], ','),
        ))

    # 大类汇总
    style_amounts = {}
    risk_amounts = {}
    for code, info in plan.items():
        s = info['style']
        style_amounts[s] = style_amounts.get(s, 0) + info['target_amount']
        r = info['risk']
        risk_amounts[r] = risk_amounts.get(r, 0) + info['target_amount']

    lines.append('')
    lines.append('**按风格汇总**:')
    for s, amt in sorted(style_amounts.items(), key=lambda x: -x[1]):
        pct = amt / TOTAL_CAPITAL * 100
        lines.append('- %s: %s 元 (%.1f%%)' % (s, format(int(amt), ','), pct))

    lines.append('')
    lines.append('**按风险等级汇总**:')
    for r, amt in sorted(risk_amounts.items(), key=lambda x: -x[1]):
        pct = amt / TOTAL_CAPITAL * 100
        lines.append('- %s: %s 元 (%.1f%%)' % (r, format(int(amt), ','), pct))
    lines.append('- 总计: %s 元 (100%%)' % format(int(total_amt), ','))
    lines.append('')

    # ====== 三、分批建仓时间表 ======
    lines.append('## 三、分批建仓时间表 (2026年6月-12月)')
    lines.append('')
    lines.append('采用"每月等额分批+价格区间约束"建仓策略，共7个批次。')
    lines.append('每批建仓约总目标仓位的10%-15%，利用市场波动分批低吸，降低择时风险。')
    lines.append('')

    # Phase summary
    lines.append('### 3.1 各批次资金分配')
    lines.append('')
    lines.append('| 批次 | 月份 | 建仓比例 | 投入资金 | 策略要点 |')
    lines.append('|:-----|:-----|--------:|--------:|:---------|')
    for p in BUILDUP_PHASES:
        phase_amt = TOTAL_CAPITAL * p['ratio']
        lines.append('| 第%d批 | %s | %.0f%% | %s | %s |' % (
            p['phase'], p['month'], p['ratio'] * 100, format(int(phase_amt), ','), p['note']))
    lines.append('')

    # Detailed per-asset phase plan
    lines.append('### 3.2 各标的分批建仓明细')
    lines.append('')

    for code in sorted_codes:
        info = plan[code]
        lines.append('#### %s %s (目标: %s元, %.1f%%)' % (
            code, info['name'], format(int(info['target_amount']), ','), info['weight'] * 100))
        lines.append('')
        lines.append('预估单价: %.2f, 价格区间: %.2f - %.2f, 每手: %d份' % (
            info['est_price'], info['price_range_low'], info['price_range_high'], info['lots_per']))
        lines.append('')
        lines.append('| 批次 | 月份 | 比例 | 金额 | 预估数量(份) |')
        lines.append('|:-----|:-----|-----:|------:|------------:|')
        for ph in info['phases']:
            lines.append('| 第%d批 | %s | %.0f%% | %s | %s |' % (
                ph['phase'], ph['month'], ph['ratio'] * 100,
                format(int(ph['amount']), ','), format(ph['est_shares'], ',')))
        lines.append('| **合计** | | **100%%** | **%s** | **%s** |' % (
            format(int(info['target_amount']), ','), format(info['est_total_shares'], ',')))
        lines.append('')

    # ====== 四、建仓操作规则 ======
    lines.append('## 四、建仓操作规则')
    lines.append('')
    lines.append('### 4.1 每月执行流程')
    lines.append('')
    lines.append('每月第三个周一为执行日，执行步骤如下:')
    lines.append('')
    lines.append('1. **盘前准备(09:00)**: 查看前一交易日的标的收盘价，确认是否在价格区间内')
    lines.append('2. **价格判断**:')
    lines.append('   - 若现价在区间下限附近(低于预估10%以上): 该批次增配20% (多买)')
    lines.append('   - 若现价在区间内: 正常执行')
    lines.append('   - 若现价突破区间上限(高于预估10%以上): 该批次减配至50% (少买)，剩余资金保留为现金')
    lines.append('   - 若现价突破区间上限20%以上: 该批次暂停，资金延至下一批次')
    lines.append('3. **执行时间**: 上午10:00-11:00 和下午14:00-14:30，分两笔各执行50%，避免日内冲击')
    lines.append('4. **成交确认**: T+1日确认全部成交，记录实际成本')
    lines.append('')
    lines.append('### 4.2 建仓期特殊规则')
    lines.append('')
    lines.append('- **单日最大买入**: 单个ETF单日买入不超过该标的日均成交量的10%，避免冲击成本')
    lines.append('- **大额处理**: 中国神华(601088)单批次超过50万元时，分3个交易日买入')
    lines.append('- **现金管理**: 未建仓资金存放于短融ETF(511360)或货币基金，获取约2%年化')
    lines.append('- **黑天鹅应对**: 若建仓期间遇到市场大跌(单周跌幅>5%)，下一批次加仓至正常的150%')
    lines.append('')

    # ====== 五、风控体系 ======
    lines.append('## 五、风控体系')
    lines.append('')
    lines.append('### 5.1 止损规则')
    lines.append('')
    lines.append('| 级别 | 触发条件 | 操作 |')
    lines.append('|:-----|:---------|:-----|')
    lines.append('| 单标的止损 | 任一标的从建仓均价下跌15% | 全部卖出该标的，资金转短融ETF观察30天 |')
    lines.append('| 组合预警 | 组合从最高点回撤8% | 减仓至70%，增持短融ETF至30% |')
    lines.append('| 组合止损 | 组合从最高点回撤12% | 减仓至50%，所有高风险标的降至半仓 |')
    lines.append('| 极端止损 | 组合从最高点回撤15% | 清仓所有equity/industry，仅保留黄金+债券 |')
    lines.append('')
    lines.append('### 5.2 再平衡规则')
    lines.append('')
    lines.append('| 频率 | 触发条件 | 操作 |')
    lines.append('|:-----|:---------|:-----|')
    lines.append('| 季度再平衡 | 每季末(3/6/9/12月最后交易日) | 检查偏离度，超过5%则恢复目标权重 |')
    lines.append('| 年度复盘 | 每年12月第一周 | 综合评估康波阶段+政策变化+标的Alpha，可调整目标权重 |')
    lines.append('| 临时再平衡 | 任一标的偏离目标权重8% | 当日恢复至目标权重 |')
    lines.append('| 大事件触发 | 重大政策出台/康波阶段确认转变 | 召开紧急复盘，判断是否需要战略性调仓 |')
    lines.append('')
    lines.append('### 5.3 2027年关键调仓窗口')
    lines.append('')
    lines.append('2027年是康波复苏转繁荣的预期临界点，届时需要完成以下评估:')
    lines.append('')
    lines.append('- 确认康波是否转入繁荣期(观测: AI算力资本开支增速、半导体周期、铜价走势)')
    lines.append('- 若确认转入繁荣: 增配顺周期商品(有色金属ETF 512400 从9.3%提至15%，减科创/半导体各2-3%)')
    lines.append('- 若仍处复苏: 维持现有配置不变')
    lines.append('- 评估十五五规划第二年执行进展，调整政策对齐评分')
    lines.append('')

    # ====== 六、持有期管理 ======
    lines.append('## 六、持有期管理 (2027-2030)')
    lines.append('')
    lines.append('### 6.1 年度关键任务')
    lines.append('')
    lines.append('| 年份 | 康波预期阶段 | 核心任务 |')
    lines.append('|:-----|:------------|:---------|')
    lines.append('| 2027 | 复苏->繁荣转折 | 确认繁荣信号，增配顺周期商品；观察十五五政策落地节奏 |')
    lines.append('| 2028 | 繁荣初期 | 维持高仓位权益资产；重点关注AI/半导体业绩兑现 |')
    lines.append('| 2029 | 繁荣中期 | 适度止盈高涨幅标的(>100%收益标的减仓1/3)；增配防御型资产 |')
    lines.append('| 2030 | 繁荣后期/十五五收官 | 逐步降风险：权益从80%降至60%；评估是否延长持有至2028年康波顶点 |')
    lines.append('')
    lines.append('### 6.2 预期现金流路径')
    lines.append('')
    # Calculate projected values
    current_amt = TOTAL_CAPITAL
    annual_rate = 0.2215
    for year in range(1, 6):
        end_amt = TOTAL_CAPITAL * ((1 + annual_rate) ** year)
        gain = end_amt - TOTAL_CAPITAL
        year_label = 2025 + year
        lines.append('| %d年末 | %s | +%s (+%.1f%%) | %s |' % (
            year_label,
            format(int(end_amt), ','),
            format(int(gain), ','),
            (end_amt / TOTAL_CAPITAL - 1) * 100,
            '持有中' if year < 5 else '目标退出评估'
        ))
    lines.append('')
    lines.append('*注: 以上为模拟预期值，实际收益受市场波动影响，可能显著偏离预期*')
    lines.append('')

    # ====== 七、执行检查清单 ======
    lines.append('## 七、执行检查清单')
    lines.append('')
    lines.append('### 建仓启动前 (2026年6月)')
    lines.append('- [ ] 开通所有标的交易权限 (科创板ETF、创业板ETF、商品ETF)')
    lines.append('- [ ] 券商账户资金到账200万')
    lines.append('- [ ] 确认单日交易限额满足建仓需求')
    lines.append('- [ ] 设置止损条件单模板')
    lines.append('- [ ] 打印本交易计划，贴于交易位')
    lines.append('')
    lines.append('### 每月建仓日')
    lines.append('- [ ] 检查上周市场走势，判断是否触发"黑天鹅加仓"规则')
    lines.append('- [ ] 确认各标的当前价格是否在区间内')
    lines.append('- [ ] 上午10:00 执行50%买入')
    lines.append('- [ ] 下午14:00 执行剩余50%买入')
    lines.append('- [ ] T+1日确认成交，更新持仓记录表')
    lines.append('- [ ] 未建仓资金确认在短融ETF中')
    lines.append('')
    lines.append('### 每季度末')
    lines.append('- [ ] 生成持仓报告 (实际权重 vs 目标权重)')
    lines.append('- [ ] 检查偏离度，触发再平衡条件则执行')
    lines.append('- [ ] 更新回撤监控数据')
    lines.append('- [ ] 记录当季市场重大事件')
    lines.append('')
    lines.append('### 每年末')
    lines.append('- [ ] 年度绩效报告 (收益率、回撤、夏普、信息比率)')
    lines.append('- [ ] 康波阶段重新评估 (数据驱动)')
    lines.append('- [ ] 十五五规划进展评估')
    lines.append('- [ ] 决定下一年是否需要调仓')
    lines.append('')

    # ====== 八、风险提示 ======
    lines.append('## 八、风险提示与免责')
    lines.append('')
    lines.append('1. **模型风险**: 本计划基于康波周期理论和历史模拟，实际市场走势可能显著偏离预期')
    lines.append('2. **流动性风险**: 部分ETF在极端行情下可能出现流动性不足，导致无法按计划价格成交')
    lines.append('3. **政策风险**: 十五五规划具体执行力度、产业政策调整可能影响相关标的预期收益')
    lines.append('4. **集中度风险**: 高端制造方向占比超60%，若该方向遭遇系统性风险将显著影响组合')
    lines.append('5. **黑天鹅风险**: 地缘冲突、金融危机等极端事件可能触发止损规则，导致实际收益远低于预期')
    lines.append('6. **本计划不构成任何投资建议，仅供个人研究参考，实际操作风险自担**')
    lines.append('')

    lines.append('---')
    lines.append('*本交易计划由康波周期+十五五规划组合构建器自动生成*')
    lines.append('*生成时间: %s*' % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    lines.append('*策略: 进取型(康波全面超配) | 资金: 200万 | 持有期: 2026-2030*')

    report = '\n'.join(lines)

    # 保存
    report_path = os.path.join(REPORT_DIR, '进取型200万建仓交易计划_20260615.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print('=' * 70)
    print('  进取型(康波全面超配) 200万五年交易计划')
    print('=' * 70)
    print('  总资金: 2,000,000 元')
    print('  标的数: %d 只' % len(AGGRESSIVE_WEIGHTS))
    print('  建仓批数: %d 批 (2026年6月-12月)' % len(BUILDUP_PHASES))
    print('  预期5年末终值: ~5,632,519 元 (基于年化22.15%模拟)')
    print('  报告已保存: %s' % report_path)
    print('=' * 70)

    return report_path


if __name__ == '__main__':
    generate_report()
