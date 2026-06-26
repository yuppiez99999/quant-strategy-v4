# -*- coding: utf-8 -*-
"""
康波周期 + 十五五规划 五年目标组合构建器
目标: 年化 >= 8%, 最大回撤 <= 15%, 持有期 5 年

生成的组合基于:
  - 康波第六轮复苏->繁荣转换期 (AI/算力驱动)
  - 十五五规划 (2026-2030) 七大战略方向
  - 社保基金ETF风格追踪 (高端制造超配信号)
  - 多策略对比选优
"""

import os, sys, json, math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows 控制台 UTF-8 编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(BASE_DIR, '..', u'每日报告归档', datetime.now().strftime('%Y-%m-%d'))
os.makedirs(REPORT_DIR, exist_ok=True)

# ============================================================
# 目标约束 (与系统 PORTFOLIO_TARGETS 一致)
# ============================================================
TARGET_ANNUAL_RETURN = 0.08   # >= 8%
TARGET_MAX_DRAWDOWN = -0.15   # >= -15% (即 <= 15%)
TARGET_YEARS = 5.0

# ============================================================
# 康波第六轮 + 十五五规划 成长型资产池
# ============================================================
# 基于今日宏观分析结果:
#   - 康波阶段: 第六轮复苏期 (75%进度, 2027前后转繁荣)
#   - 十五五规划核心: AI/半导体/高端制造/新能源/数字经济/生物医药
#   - 社保基金风格: 高端制造超配35%, 顺周期25%, 资源20%, 防御20%

KONDRATIEV_FIFTEENFIVE_PORTFOLIO = {
    # ===== 高端制造+算力 (核心引擎) =====
    '588000':  {'name': u'科创50ETF华夏',      'type': 'equity', 'risk': 'high',
               'kondratiev_score': 0.95, 'fifteenfive_score': 0.92, 'social_style': u'高端制造'},
    '512480':  {'name': u'半导体ETF国泰',       'type': 'equity', 'risk': 'high',
               'kondratiev_score': 0.93, 'fifteenfive_score': 0.90, 'social_style': u'高端制造'},
    '515030':  {'name': u'新能源车ETF华夏',     'type': 'equity', 'risk': 'high',
               'kondratiev_score': 0.88, 'fifteenfive_score': 0.91, 'social_style': u'高端制造'},
    '159915':  {'name': u'创业板ETF易方达',     'type': 'equity', 'risk': 'high',
               'kondratiev_score': 0.86, 'fifteenfive_score': 0.85, 'social_style': u'高端制造'},
    '516160':  {'name': u'高端装备ETF南方',     'type': 'equity', 'risk': 'high',
               'kondratiev_score': 0.90, 'fifteenfive_score': 0.93, 'social_style': u'高端制造'},

    # ===== 顺周期+资源 =====
    '512400':  {'name': u'有色金属ETF南方',     'type': 'industry', 'risk': 'high',
               'kondratiev_score': 0.82, 'fifteenfive_score': 0.72, 'social_style': u'资源'},
    '601088':  {'name': u'中国神华',            'type': 'stock', 'risk': 'medium',
               'kondratiev_score': 0.78, 'fifteenfive_score': 0.78, 'social_style': u'顺周期'},

    # ===== 医药/创新 =====
    '512010':  {'name': u'医药ETF易方达',       'type': 'equity', 'risk': 'medium',
               'kondratiev_score': 0.72, 'fifteenfive_score': 0.88, 'social_style': u'防御'},
    '159992':  {'name': u'创新药ETF银华',       'type': 'equity', 'risk': 'high',
               'kondratiev_score': 0.70, 'fifteenfive_score': 0.86, 'social_style': u'防御'},

    # ===== 防御/对冲 =====
    '518880':  {'name': u'黄金ETF华安',         'type': 'commodity', 'risk': 'medium',
               'kondratiev_score': 0.65, 'fifteenfive_score': 0.45, 'social_style': u'资源'},
    '511260':  {'name': u'十年国债ETF国泰',     'type': 'bond', 'risk': 'low',
               'kondratiev_score': 0.30, 'fifteenfive_score': 0.40, 'social_style': u'防御'},
    '511520':  {'name': u'政金债ETF富国',       'type': 'bond', 'risk': 'low',
               'kondratiev_score': 0.25, 'fifteenfive_score': 0.35, 'social_style': u'防御'},
    '511360':  {'name': u'短融ETF海富通',       'type': 'money', 'risk': 'low',
               'kondratiev_score': 0.10, 'fifteenfive_score': 0.20, 'social_style': u'防御'},
}


# ============================================================
# 各资产在康波不同阶段的预期年化参数 (基于历史统计+周期推演)
# ============================================================
EXPECTED_RETURNS_BY_TYPE = {
    'equity':   {'annual_mean': 0.14, 'annual_vol': 0.22, 'shock_prob': 0.02, 'shock_magnitude': -0.08},
    'industry': {'annual_mean': 0.12, 'annual_vol': 0.25, 'shock_prob': 0.03, 'shock_magnitude': -0.09},
    'commodity': {'annual_mean': 0.09, 'annual_vol': 0.18, 'shock_prob': 0.02, 'shock_magnitude': -0.06},
    'stock':    {'annual_mean': 0.10, 'annual_vol': 0.20, 'shock_prob': 0.02, 'shock_magnitude': -0.07},
    'bond':     {'annual_mean': 0.03, 'annual_vol': 0.04, 'shock_prob': 0.005, 'shock_magnitude': -0.01},
    'money':    {'annual_mean': 0.02, 'annual_vol': 0.005, 'shock_prob': 0.0, 'shock_magnitude': 0.0},
}


def generate_asset_returns(asset_info, n_days, seed=42):
    """基于康波阶段参数生成单资产日收益率序列"""
    params = EXPECTED_RETURNS_BY_TYPE.get(asset_info['type'], EXPECTED_RETURNS_BY_TYPE['stock'])

    # 用十五五+康波评分微调预期收益
    composite_score = (asset_info.get('kondratiev_score', 0.5) + asset_info.get('fifteenfive_score', 0.5)) / 2
    # score>0.8 超配溢价 +2%, score<0.5 折价 -1%
    score_adj = (composite_score - 0.65) * 0.05

    daily_mean = (params['annual_mean'] + score_adj) / 252
    daily_vol = params['annual_vol'] / math.sqrt(252)

    rng = np.random.RandomState(seed)
    returns = rng.normal(daily_mean, daily_vol, n_days)

    # 随机冲击事件 (黑天鹅)
    shock_mask = rng.random(n_days) < params['shock_prob'] / 252
    returns[shock_mask] += params['shock_magnitude']

    return returns


def build_equity_curve(weights, data, initial_capital=1000000):
    """构建组合净值曲线"""
    codes = list(data.keys())
    dates = data[codes[0]]['date']
    ret_df = pd.DataFrame({code: data[code]['returns'] for code in codes}, index=dates)

    weight_vector = np.array([weights.get(c, 0.0) for c in codes])
    port_ret = ret_df.fillna(0).dot(weight_vector)
    port_ret = pd.Series(port_ret, index=ret_df.index)

    equity = initial_capital * (1 + port_ret).cumprod()
    return equity


def compute_metrics(equity, initial_capital=1000000):
    """计算组合绩效指标"""
    n_days = len(equity)
    total_return = (equity.iloc[-1] / initial_capital - 1) * 100
    annual_return = ((1 + total_return / 100) ** (252 / max(n_days, 1)) - 1) * 100

    returns = equity.pct_change().dropna()
    sharpe = returns.mean() / returns.std() * math.sqrt(252) if returns.std() > 0 else 0

    dd = equity / equity.cummax() - 1
    max_dd = dd.min() * 100

    calmar = abs(annual_return / max_dd) if max_dd != 0 else 0
    win_rate = (returns > 0).mean() * 100

    # 5年滚动CAGR (向量化)
    window = int(TARGET_YEARS * 252)
    if len(equity) >= window:
        equity_arr = equity.values
        # 向量化: 滚动窗口起点/终点对
        start_vals = equity_arr[:-window]
        end_vals = equity_arr[window:]
        roll_cagr = ((end_vals / start_vals) ** (252 / window) - 1) * 100
        min_5y_cagr = float(np.min(roll_cagr))
    else:
        min_5y_cagr = annual_return

    meet_targets = (annual_return >= TARGET_ANNUAL_RETURN * 100 and
                    max_dd >= TARGET_MAX_DRAWDOWN * 100 and
                    min_5y_cagr >= TARGET_ANNUAL_RETURN * 100)

    return {
        'total_return': round(total_return, 2),
        'annual_return': round(annual_return, 2),
        'sharpe_ratio': round(sharpe, 3),
        'max_drawdown': round(max_dd, 2),
        'calmar_ratio': round(calmar, 3),
        'win_rate': round(win_rate, 2),
        'final_equity': round(float(equity.iloc[-1]), 2),
        'min_5y_cagr': round(min_5y_cagr, 2),
        'meet_targets': meet_targets,
    }


def generate_strategy_weights(strategy, portfolio):
    """生成各策略权重"""
    codes = list(portfolio.keys())

    if strategy == u'等权重':
        n = len(codes)
        return {c: 1.0 / n for c in codes}

    elif strategy == u'康波评分加权':
        raw = {c: portfolio[c]['kondratiev_score'] * portfolio[c]['fifteenfive_score']
               for c in codes}
        total = sum(raw.values())
        return {c: v / total for c, v in raw.items()}

    elif strategy == u'十五五政策对齐':
        raw = {c: portfolio[c]['fifteenfive_score'] ** 2 for c in codes}
        total = sum(raw.values())
        return {c: v / total for c, v in raw.items()}

    elif strategy == u'社保风格跟踪':
        style_weights = {u'高端制造': 0.35, u'顺周期': 0.25, u'资源': 0.20, u'防御': 0.20}
        style_groups = {}
        for c in codes:
            s = portfolio[c].get('social_style', u'防御')
            style_groups.setdefault(s, []).append(c)

        weights = {}
        for style, target_w in style_weights.items():
            members = style_groups.get(style, [])
            if members:
                per_member = target_w / len(members)
                for c in members:
                    weights[c] = per_member
        total = sum(weights.values())
        return {c: v / total for c, v in weights.items()}

    elif strategy == u'风险平价':
        risk_map = {'high': 0.20, 'medium': 0.12, 'low': 0.05}
        raw = {c: 1.0 / max(risk_map.get(portfolio[c]['risk'], 0.12), 0.01) for c in codes}
        total = sum(raw.values())
        return {c: v / total for c, v in raw.items()}

    elif strategy == u'进取型(康波全面超配)':
        raw = {}
        for c in codes:
            info = portfolio[c]
            base = info.get('kondratiev_score', 0.5) * info.get('fifteenfive_score', 0.5)
            if info['type'] in ('equity', 'industry') and info['risk'] == 'high':
                base *= 1.5
            elif info['type'] in ('bond', 'money'):
                base *= 0.4
            raw[c] = max(base, 0.01)
        total = sum(raw.values())
        return {c: v / total for c, v in raw.items()}

    elif strategy == u'均衡型(风险约束)':
        raw = {}
        for c in codes:
            info = portfolio[c]
            base = info.get('kondratiev_score', 0.5) * info.get('fifteenfive_score', 0.5)
            if info['type'] in ('equity', 'industry') and info['risk'] == 'high':
                base *= 1.3
            elif info['type'] in ('bond', 'money'):
                base *= 0.5
            raw[c] = max(base, 0.015)
        total = sum(raw.values())
        return {c: v / total for c, v in raw.items()}

    else:
        return {c: 1.0 / len(codes) for c in codes}


# ============================================================
# 主流程: 多策略对比 + 目标过滤
# ============================================================
def main():
    print("=" * 75)
    print("  康波周期 + 十五五规划 -- 五年目标组合构建器")
    print("  目标: 年化 >= 8% | 回撤 <= 15% | 持有期 5年")
    print("=" * 75)
    print("  生成时间: %s" % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("  康波阶段: 第六轮 复苏期 (75%进度, 2027前后->繁荣)")
    print("  十五五规划: 2026-2030 (AI/半导体/新能源/高端制造/生物医药)")
    print("-" * 75)

    portfolio = KONDRATIEV_FIFTEENFIVE_PORTFOLIO
    codes = list(portfolio.keys())

    # ========== 生成5年模拟数据 ==========
    start_date = pd.Timestamp('2026-01-01')
    end_date = pd.Timestamp('2030-12-31')
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    n_days = len(dates)

    print("\n  模拟期: %s -> %s (%d 交易日)" % (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), n_days))
    print("  资产池: %d 只标的" % len(codes))

    data = {}
    for i, code in enumerate(codes):
        info = portfolio[code]
        returns = generate_asset_returns(info, n_days, seed=42 + i * 7)
        prices = np.cumprod(1 + returns)
        data[code] = {
            'date': dates,
            'returns': returns,
            'prices': prices,
        }

    # ========== 策略列表 ==========
    strategies = [
        u'等权重',
        u'康波评分加权',
        u'十五五政策对齐',
        u'社保风格跟踪',
        u'风险平价',
        u'进取型(康波全面超配)',
        u'均衡型(风险约束)',
    ]

    print("\n" + "=" * 75)
    print("%-22s %8s %8s %6s %14s %6s" % (u'策略', u'年化收益', u'最大回撤', u'夏普', u'5年CAGR(min)', u'达标'))
    print("-" * 75)

    all_results = {}
    passed_strategies = {}

    for strategy in strategies:
        weights = generate_strategy_weights(strategy, portfolio)
        equity = build_equity_curve(weights, data)
        metrics = compute_metrics(equity)
        all_results[strategy] = dict(metrics, weights=weights)

        flag = 'YES' if metrics['meet_targets'] else 'NO '
        print("%-22s %7.2f%% %7.2f%% %6.3f %13.2f%% %6s" % (
            strategy, metrics['annual_return'], metrics['max_drawdown'],
            metrics['sharpe_ratio'], metrics['min_5y_cagr'], flag))

        if metrics['meet_targets']:
            passed_strategies[strategy] = metrics

    print("-" * 75)

    # ========== 选出最佳策略 ==========
    if passed_strategies:
        best_name = max(passed_strategies, key=lambda k: passed_strategies[k]['sharpe_ratio'])
        best = passed_strategies[best_name]
        print("\n  [BEST] 达标策略: %d/%d" % (len(passed_strategies), len(strategies)))
        print("  最佳策略: %s" % best_name)
        print("  年化收益: %.2f%% | 最大回撤: %.2f%% | 夏普: %.3f" % (
            best['annual_return'], best['max_drawdown'], best['sharpe_ratio']))
    else:
        def score(r):
            ret_score = max(0, r['annual_return'] - TARGET_ANNUAL_RETURN * 100)
            dd_penalty = max(0, abs(r['max_drawdown']) - abs(TARGET_MAX_DRAWDOWN * 100))
            return ret_score - dd_penalty * 2

        best_name = max(all_results, key=lambda k: score(all_results[k]))
        best = all_results[best_name]
        print("\n  [WARN] 无策略完全达标 (当前模拟条件下)")
        print("  最接近策略: %s" % best_name)
        print("  年化收益: %.2f%% | 最大回撤: %.2f%%" % (best['annual_return'], best['max_drawdown']))

    # ========== 生成详细报告 ==========
    best_weights = best.get('weights', generate_strategy_weights(best_name, portfolio))
    sorted_weights = sorted(best_weights.items(), key=lambda x: -x[1])

    report_lines = []
    report_lines.append(u"# 康波周期 + 十五五规划 五年目标组合")
    report_lines.append("")
    report_lines.append(u"> 生成日期: %s" % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    report_lines.append(u"> 目标约束: 年化 >= 8% | 最大回撤 <= 15% | 持有期 5年 (2026-2030)")
    report_lines.append(u"> 康波阶段: 第六轮复苏期 -> 2027前后转入繁荣期")
    report_lines.append(u"> 十五五规划: 2026-2030 七大战略方向")
    report_lines.append("")

    report_lines.append("## 一、宏观背景")
    report_lines.append("")
    report_lines.append(u"**康波周期判定**: 当前处于第六轮康波(AI/算力驱动)复苏期，进度75%。")
    report_lines.append(u"十五五规划期(2026-2030)恰好处于第六轮康波复苏->繁荣转换期，两者高度同频。")
    report_lines.append(u"十五五核心产业(AI、半导体、高端制造、新能源)与康波第六轮驱动力完全一致，")
    report_lines.append(u"形成政策+周期的戴维斯双击效应。")
    report_lines.append("")
    report_lines.append(u"**大宗商品信号**: 铜(看多)、锡(看多)、白银(看多)、铝(偏多)、黄金(配置)、原油(中性)")
    report_lines.append("")
    report_lines.append(u"**社保基金风格**: 高端制造超配35% / 顺周期25% / 资源20% / 防御20%")
    report_lines.append("")

    report_lines.append("## 二、组合构成")
    report_lines.append("")
    report_lines.append("| 代码 | 名称 | 类型 | 风险 | 康波评分 | 十五五评分 | 权重 |")
    report_lines.append("|:-----|:-----|:-----|:-----|--------:|----------:|-----:|")
    for code, w in sorted_weights:
        info = portfolio[code]
        report_lines.append("| %s | %s | %s | %s | %.0f%% | %.0f%% | %.1f%% |" % (
            code, info['name'], info['type'], info['risk'],
            info['kondratiev_score'] * 100, info['fifteenfive_score'] * 100, w * 100))
    report_lines.append("")

    # 按大类汇总
    type_weights = {}
    for code, w in sorted_weights:
        t = portfolio[code]['type']
        type_weights[t] = type_weights.get(t, 0) + w
    report_lines.append(u"**大类配置**:")
    for t, w in sorted(type_weights.items(), key=lambda x: -x[1]):
        report_lines.append(u"- %s: %.1f%%" % (t, w * 100))
    report_lines.append("")

    report_lines.append("## 三、策略对比")
    report_lines.append("")
    report_lines.append("| 策略 | 年化收益 | 最大回撤 | 夏普比率 | 5年CAGR(min) | 达标 |")
    report_lines.append("|:-----|--------:|--------:|--------:|-------------:|:----:|")
    for strategy in strategies:
        r = all_results[strategy]
        flag = u'是' if r['meet_targets'] else u'否'
        report_lines.append("| %s | %.2f%% | %.2f%% | %.3f | %.2f%% | %s |" % (
            strategy, r['annual_return'], r['max_drawdown'],
            r['sharpe_ratio'], r['min_5y_cagr'], flag))
    report_lines.append("")

    report_lines.append(u"## 四、推荐策略: %s" % best_name)
    report_lines.append("")
    report_lines.append(u"- **年化收益**: %.2f%%" % best['annual_return'])
    report_lines.append(u"- **最大回撤**: %.2f%%" % best['max_drawdown'])
    report_lines.append(u"- **夏普比率**: %.3f" % best['sharpe_ratio'])
    report_lines.append(u"- **5年滚动CAGR(最小值)**: %.2f%%" % best['min_5y_cagr'])
    report_lines.append(u"- **胜率**: %.2f%%" % best['win_rate'])
    report_lines.append(u"- **Calmar比率**: %.3f" % best['calmar_ratio'])
    report_lines.append(u"- **最终资金**: {0:,.0f} 元 (起始100万)".format(best['final_equity']))
    report_lines.append("")

    report_lines.append(u"### 推荐权重")
    report_lines.append("")
    report_lines.append("| 代码 | 名称 | 权重 | 风格 |")
    report_lines.append("|:-----|:-----|-----:|:-----|")
    for code, w in sorted_weights:
        info = portfolio[code]
        report_lines.append("| %s | %s | %.1f%% | %s |" % (
            code, info['name'], w * 100, info.get('social_style', '')))
    report_lines.append("")

    report_lines.append("## 五、风控建议")
    report_lines.append("")
    report_lines.append(u"1. **再平衡频率**: 季度再平衡，偏离基准5%以上触发调仓")
    report_lines.append(u"2. **止损规则**: 单标的-15%止损，组合-10%减仓至50%现金")
    report_lines.append(u"3. **黑天鹅应对**: 保留10%现金等价物应对极端波动")
    report_lines.append(u"4. **年度复盘**: 每年12月根据康波阶段进展+十五五执行进度调整权重")
    report_lines.append(u"5. **关键观测点**: 2027年康波转繁荣确认时，增配顺周期商品")
    report_lines.append("")

    report_lines.append("---")
    report_lines.append(u"*本报告由康波周期+十五五规划组合构建器自动生成*")
    report_lines.append(u"*生成时间: %s*" % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    report = '\n'.join(report_lines)

    # 保存报告
    report_path = os.path.join(REPORT_DIR, u'康波十五五五年组合_%s.md' % datetime.now().strftime('%Y%m%d'))
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print("\n  [OK] 报告已保存: %s" % report_path)

    # 同时保存 JSON 供系统调用
    json_path = os.path.join(REPORT_DIR, 'portfolio_weights_kondratiev_%s.json' % datetime.now().strftime('%Y%m%d'))
    json_data = {
        'strategy': best_name,
        'generated': datetime.now().isoformat(),
        'targets': {'annual_return': TARGET_ANNUAL_RETURN, 'max_drawdown': TARGET_MAX_DRAWDOWN, 'years': TARGET_YEARS},
        'metrics': {k: v for k, v in best.items() if k != 'weights'},
        'weights': best_weights,
        'all_results': {k: {kk: vv for kk, vv in v.items() if kk != 'weights'} for k, v in all_results.items()},
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print("  [OK] 权重JSON已保存: %s" % json_path)

    # 打印摘要
    print("\n" + "=" * 75)
    print("  推荐策略: %s" % best_name)
    print("  年化 %.2f%% | 回撤 %.2f%% | 夏普 %.3f" % (best['annual_return'], best['max_drawdown'], best['sharpe_ratio']))
    print("=" * 75)

    return best_name, best_weights, all_results


if __name__ == '__main__':
    main()
