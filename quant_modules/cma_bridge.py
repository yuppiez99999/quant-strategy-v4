# -*- coding: utf-8 -*-
"""
CMA (Claude Managed Agent) Bridge — 金融代理插件集成层 v1.0

将 financial-services 仓库中的三个 Claude 代理集成到量化策略系统:
  - month-end-closer:  月末结账（应计/滚动/差异说明）
  - valuation-reviewer: 组合估值审阅（NAV/瀑布/LP报告）
  - statement-auditor:  持仓对账（系统NAV vs 实际行情）

架构:
  量化策略系统 → CMA Bridge → Claude Agent (DeepSeek V4 Pro) → 报告
  ─ 不依赖外部MCP, 使用本地数据+DeepSeek LLM模拟代理行为 ─

依赖:
  - financial-services 仓库 (e:/各种PY程序/financial-services/)
  - llm_report_analyzer.py (DeepSeek V4 Pro)
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

_log = logging.getLogger('cma_bridge')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CMA_SKILLS_DIR = os.path.join(os.path.dirname(BASE_DIR), 'financial-services', 'plugins', 'agent-plugins')


@dataclass
class CMAReport:
    """代理报告统一格式"""
    agent: str
    title: str
    summary: str
    details: Dict[str, Any]
    flags: List[str]
    markdown: str
    generated_at: str


# ============================================================
# 技能加载器 — 懒加载 financial-services 技能定义
# ============================================================

def _load_skill_md(agent: str, skill: str) -> str:
    """加载技能 Markdown 提示词"""
    path = os.path.join(CMA_SKILLS_DIR, agent, 'skills', skill, 'SKILL.md')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def _load_agent_md(agent: str) -> str:
    """加载代理定义"""
    path = os.path.join(CMA_SKILLS_DIR, agent, 'agents', f'{agent}.md')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


# ============================================================
# 1. Month-End Closer — 月末结账
# ============================================================

def run_month_end_close(
    positions: Dict[str, Dict],
    prices: Dict[str, float],
    period: str = None,
    previous_nav: float = None,
) -> CMAReport:
    """
    执行月末结账流程

    Args:
        positions: {code: {shares, avg_cost, ...}}
        prices: {code: price}
        period: "2026-06"
        previous_nav: 上期末净值

    Returns:
        CMAReport with accrual/rollforward/variance
    """
    if period is None:
        period = datetime.now().strftime('%Y-%m')
    if previous_nav is None:
        previous_nav = 0

    # 1. 计算当前组合净值
    total_value = 0
    total_cost = 0
    holdings = []
    for code, pos in positions.items():
        price = prices.get(code, pos.get('avg_cost', 0))
        shares = float(pos.get('shares', pos.get('qty', 0)))
        cost = float(pos.get('avg_cost', pos.get('cost', 0)))
        if shares > 0 and price > 0:
            val = shares * price
            cost_val = shares * cost
            pnl = val - cost_val
            pnl_pct = (pnl / cost_val * 100) if cost_val > 0 else 0
            total_value += val
            total_cost += cost_val
            holdings.append({
                'code': code, 'name': pos.get('name', code),
                'shares': shares, 'price': price, 'cost': cost,
                'value': val, 'pnl': pnl, 'pnl_pct': pnl_pct,
            })

    nav = total_value
    period_pnl = nav - previous_nav if previous_nav > 0 else 0
    period_return = (period_pnl / previous_nav * 100) if previous_nav > 0 else 0

    # 2. 构建应计/差异分析
    top_gainers = sorted(holdings, key=lambda x: x['pnl_pct'], reverse=True)[:5]
    top_losers = sorted(holdings, key=lambda x: x['pnl_pct'])[:5]

    # 3. 尝试用 DeepSeek 生成差异说明
    variance_narrative = _generate_variance_narrative(
        period=period, nav=nav, period_return=period_return,
        top_gainers=top_gainers, top_losers=top_losers,
        holdings_count=len(holdings),
    )

    # 4. 构建 Markdown 报告
    lines = []
    lines.append(f"## 📋 Month-End Close — {period}")
    lines.append("")
    lines.append(f"**期末净值**: ¥{nav:,.2f}")
    lines.append(f"**期初净值**: ¥{previous_nav:,.2f}")
    lines.append(f"**期间损益**: ¥{period_pnl:+,.2f} ({period_return:+.2f}%)")
    lines.append(f"**持仓标的**: {len(holdings)} 只")
    lines.append("")

    if top_gainers:
        lines.append("### 📈 期间涨幅 TOP5")
        lines.append("| 代码 | 名称 | 价格 | 成本 | 市值 | 盈亏 | 涨跌% |")
        lines.append("|------|------|------|------|------|------|-------|")
        for h in top_gainers:
            lines.append(f"| {h['code']} | {h['name']} | {h['price']:.2f} | {h['cost']:.2f} | {h['value']:,.0f} | {h['pnl']:+,.0f} | {h['pnl_pct']:+.2f}% |")
        lines.append("")

    if top_losers:
        lines.append("### 📉 期间跌幅 TOP5")
        lines.append("| 代码 | 名称 | 价格 | 成本 | 市值 | 盈亏 | 涨跌% |")
        lines.append("|------|------|------|------|------|------|-------|")
        for h in top_losers:
            lines.append(f"| {h['code']} | {h['name']} | {h['price']:.2f} | {h['cost']:.2f} | {h['value']:,.0f} | {h['pnl']:+,.0f} | {h['pnl_pct']:+.2f}% |")
        lines.append("")

    if variance_narrative:
        lines.append("### 🧠 差异分析")
        lines.append("")
        lines.append(variance_narrative)
        lines.append("")

    return CMAReport(
        agent='month-end-closer',
        title=f'月末结账 {period}',
        summary=f'期末净值 ¥{nav:,.0f}, 期间收益 {period_return:+.2f}%, {len(holdings)}只持仓',
        details={
            'nav': nav, 'period_pnl': period_pnl, 'period_return': period_return,
            'holdings_count': len(holdings), 'top_gainers': top_gainers, 'top_losers': top_losers,
        },
        flags=[h['code'] for h in top_losers if h['pnl_pct'] < -5],
        markdown='\n'.join(lines),
        generated_at=datetime.now().isoformat(),
    )


def _generate_variance_narrative(
    period: str, nav: float, period_return: float,
    top_gainers: List[Dict], top_losers: List[Dict],
    holdings_count: int,
) -> str:
    """DeepSeek 生成差异说明"""
    try:
        from llm_report_analyzer import LLMTradingAdvisor
        advisor = LLMTradingAdvisor(provider='volcengine')
        if not advisor.api_key:
            return ""

        gainers_str = "; ".join(f"{h['name']}({h['code']}) {h['pnl_pct']:+.1f}%" for h in top_gainers)
        losers_str = "; ".join(f"{h['name']}({h['code']}) {h['pnl_pct']:+.1f}%" for h in top_losers)
        prompt = (
            f"你是月末结账代理。期间{period}，期末净值¥{nav:,.0f}，期间收益{period_return:+.2f}%。"
            f"涨幅最大: {gainers_str}。跌幅最大: {losers_str}。"
            f"请用2-3句话分析: 1) 收益驱动因素 2) 主要拖累 3) 下月关注点。"
        )
        result = advisor.ask(prompt[:800])
        return result if isinstance(result, str) else str(result)
    except Exception:
        pass
    return ""


# ============================================================
# 2. Valuation Reviewer — 组合估值审阅
# ============================================================

def run_valuation_review(
    positions: Dict[str, Dict],
    prices: Dict[str, float],
    target_weights: Dict[str, float],
    as_of_date: str = None,
) -> CMAReport:
    """
    执行组合估值审阅

    Args:
        positions: {code: {shares, avg_cost}}
        prices: {code: price}
        target_weights: {code: target_weight}
        as_of_date: "2026-06-21"
    """
    if as_of_date is None:
        as_of_date = datetime.now().strftime('%Y-%m-%d')

    # 1. 计算当前权重 vs 目标权重
    total_value = 0
    weight_check = []
    for code, pos in positions.items():
        price = prices.get(code, pos.get('avg_cost', 0))
        shares = float(pos.get('shares', pos.get('qty', 0)))
        if shares > 0 and price > 0:
            val = shares * price
            total_value += val
            weight_check.append({
                'code': code, 'name': pos.get('name', code),
                'value': val, 'shares': shares, 'price': price,
            })

    over_weight = []
    under_weight = []
    alignment_score = 0
    for w in weight_check:
        actual_w = w['value'] / total_value if total_value > 0 else 0
        target_w = target_weights.get(w['code'], 0)
        drift = actual_w - target_w
        w['actual_weight'] = actual_w
        w['target_weight'] = target_w
        w['drift'] = drift
        if drift > 0.03:
            over_weight.append(w)
        elif drift < -0.03:
            under_weight.append(w)
        alignment_score += 1 if abs(drift) < 0.05 else 0

    nav = total_value
    alignment_pct = alignment_score / len(weight_check) * 100 if weight_check else 0

    flag_list = []
    if alignment_pct < 60:
        flag_list.append(f"权重对齐率 {alignment_pct:.0f}% < 60%，需要再平衡")
    for w in over_weight:
        flag_list.append(f"{w['name']}({w['code']}) 超配 {w['drift']*100:+.1f}%")
    for w in under_weight:
        flag_list.append(f"{w['name']}({w['code']}) 低配 {w['drift']*100:+.1f}%")

    lines = []
    lines.append(f"## 📊 Valuation Review — {as_of_date}")
    lines.append("")
    lines.append(f"**组合净值**: ¥{nav:,.2f} | **标的数**: {len(weight_check)} | **权重对齐率**: {alignment_pct:.0f}%")
    lines.append("")

    if over_weight:
        lines.append("### 🔴 超配标的 (>3%偏离)")
        lines.append("| 代码 | 名称 | 价格 | 实际权重 | 目标权重 | 偏离 |")
        lines.append("|------|------|------|---------|---------|------|")
        for w in sorted(over_weight, key=lambda x: abs(x['drift']), reverse=True):
            lines.append(f"| {w['code']} | {w['name']} | {w['price']:.2f} | {w['actual_weight']:.1%} | {w['target_weight']:.1%} | +{w['drift']*100:.1f}% |")
        lines.append("")

    if under_weight:
        lines.append("### 🟢 低配标的 (<-3%偏离)")
        lines.append("| 代码 | 名称 | 价格 | 实际权重 | 目标权重 | 偏离 |")
        lines.append("|------|------|------|---------|---------|------|")
        for w in sorted(under_weight, key=lambda x: abs(x['drift']), reverse=True):
            lines.append(f"| {w['code']} | {w['name']} | {w['price']:.2f} | {w['actual_weight']:.1%} | {w['target_weight']:.1%} | {w['drift']*100:+.1f}% |")
        lines.append("")

    return CMAReport(
        agent='valuation-reviewer',
        title=f'组合估值审阅 {as_of_date}',
        summary=f'NAV ¥{nav:,.0f}, 对齐率 {alignment_pct:.0f}%, 超配{len(over_weight)}只 低配{len(under_weight)}只',
        details={'nav': nav, 'alignment_pct': alignment_pct, 'over': over_weight, 'under': under_weight},
        flags=flag_list,
        markdown='\n'.join(lines),
        generated_at=datetime.now().isoformat(),
    )


# ============================================================
# 3. Statement Auditor — 持仓对账
# ============================================================

def run_statement_audit(
    system_positions: Dict[str, Dict],
    system_prices: Dict[str, float],
    external_positions: Dict[str, Dict] = None,
    external_prices: Dict[str, float] = None,
    tolerance_pct: float = 0.01,
) -> CMAReport:
    """
    执行持仓对账: 系统NAV vs 外部(券商/基准)NAV

    Args:
        system_positions: 系统记录的持仓
        system_prices: 系统价格(Wind MCP)
        external_positions: 外部持仓(券商), None则只做价格校验
        external_prices: 外部价格, None则只做持仓校验
        tolerance_pct: 容忍偏差 (1%)
    """
    discrepancies = []
    matched = 0
    total = 0

    # 价格校验: 系统价格 vs 外部价格
    if external_prices:
        for code, sys_price in system_prices.items():
            ext_price = external_prices.get(code)
            if ext_price and sys_price > 0:
                total += 1
                diff_pct = abs(sys_price - ext_price) / ext_price
                if diff_pct > tolerance_pct:
                    discrepancies.append({
                        'type': 'price', 'code': code,
                        'system_price': sys_price, 'external_price': ext_price,
                        'diff_pct': diff_pct * 100,
                    })
                else:
                    matched += 1

    # 持仓校验
    if external_positions:
        for code, sys_pos in system_positions.items():
            ext_pos = external_positions.get(code, {})
            sys_shares = float(sys_pos.get('shares', sys_pos.get('qty', 0)))
            ext_shares = float(ext_pos.get('shares', ext_pos.get('qty', 0))) if ext_pos else 0
            if sys_shares > 0 or ext_shares > 0:
                if sys_shares != ext_shares:
                    discrepancies.append({
                        'type': 'position', 'code': code,
                        'system_shares': sys_shares, 'external_shares': ext_shares,
                        'diff': sys_shares - ext_shares,
                    })
                else:
                    matched += 1

    accuracy = matched / max(total, 1) * 100
    result = 'pass' if accuracy >= 99 else 'hold' if accuracy >= 95 else 'fail'

    lines = []
    lines.append(f"## 🔍 Statement Audit — {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append(f"**对账结果**: {'✅ 通过' if result == 'pass' else '⚠️ 暂缓' if result == 'hold' else '❌ 失败'}")
    lines.append(f"**匹配率**: {accuracy:.1f}% ({matched}/{total})")
    lines.append("")

    if discrepancies:
        lines.append("### 差异清单")
        lines.append("| 类型 | 代码 | 系统值 | 外部值 | 偏差 |")
        lines.append("|------|------|--------|--------|------|")
        for d in discrepancies[:20]:
            if d['type'] == 'price':
                lines.append(f"| 价格 | {d['code']} | {d['system_price']:.2f} | {d['external_price']:.2f} | {d['diff_pct']:.2f}% |")
            else:
                lines.append(f"| 持仓 | {d['code']} | {d['system_shares']:.0f}股 | {d['external_shares']:.0f}股 | {d['diff']:+.0f}股 |")
        lines.append("")

    return CMAReport(
        agent='statement-auditor',
        title=f'持仓对账',
        summary=f'匹配率 {accuracy:.1f}% → {result}, {len(discrepancies)}项差异',
        details={'accuracy': accuracy, 'matched': matched, 'total': total, 'discrepancies': discrepancies},
        flags=[d['code'] for d in discrepancies],
        markdown='\n'.join(lines),
        generated_at=datetime.now().isoformat(),
    )


# ============================================================
# 统一调度 — 一站式运行三大代理
# ============================================================

def run_all_cma_checks(
    positions: Dict[str, Dict],
    prices: Dict[str, float],
    target_weights: Dict[str, float],
    period: str = None,
    previous_nav: float = None,
) -> Dict[str, CMAReport]:
    """
    一站式运行全部三大金融代理,返回报告字典
    """
    results = {}

    try:
        results['month_end'] = run_month_end_close(
            positions=positions, prices=prices,
            period=period, previous_nav=previous_nav,
        )
        _log.info("[CMA] month-end-closer: OK")
    except Exception as e:
        _log.warning(f"[CMA] month-end-closer failed: {e}")

    try:
        results['valuation'] = run_valuation_review(
            positions=positions, prices=prices,
            target_weights=target_weights,
        )
        _log.info("[CMA] valuation-reviewer: OK")
    except Exception as e:
        _log.warning(f"[CMA] valuation-reviewer failed: {e}")

    try:
        results['audit'] = run_statement_audit(
            system_positions=positions, system_prices=prices,
        )
        _log.info("[CMA] statement-auditor: OK")
    except Exception as e:
        _log.warning(f"[CMA] statement-auditor failed: {e}")

    return results
