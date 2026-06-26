# -*- coding: utf-8 -*-
import json
import logging
import os
import sys
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# 修复Windows控制台GBK编码emoji问题
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 尝试加载 YiZhao 增强模块
_ENHANCED_AVAILABLE = False
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ai_analysis_enhanced import (
        EnhancedNewsAnalyzer, EnhancedValuationAnalyzer,
        EnhancedSuggestionEngine, PortfolioRiskEarlyWarning
    )
    from event_driven_factor import get_factor_generator
    from yizhao_data_loader import get_yizhao_loader
    _ENHANCED_AVAILABLE = True
except ImportError:
    pass

# 接入统一行情数据提供层 (Wind / iFinD / 新浪三级回退 + 并发)
try:
    from wind_data_provider import get_quotes_batch, get_stats as _get_wind_stats, reset_stats
    _WIND_PROVIDER_OK = True
except ImportError:
    _WIND_PROVIDER_OK = False

# 接入止损止盈监控模块
try:
    from stop_loss_monitor import StopLossMonitor, generate_risk_alert_report
    _SL_MONITOR_OK = True
except ImportError:
    _SL_MONITOR_OK = False

# 接入大模型报告解读模块
try:
    from llm_report_analyzer import LLMReportAnalyzer, format_llm_analysis_for_report
    _LLM_ANALYZER_OK = True
except ImportError:
    _LLM_ANALYZER_OK = False


class FallbackEngine:
    """降级模式下的AI分析引擎"""
    def __init__(self):
        from ai_analysis_enhanced import (
            EnhancedNewsAnalyzer, EnhancedValuationAnalyzer
        )
        self.news_analyzer = EnhancedNewsAnalyzer()
        self.valuation_analyzer = EnhancedValuationAnalyzer()
    
    def analyze_stock(self, code, name, price):
        news = self.news_analyzer.search_news_for_code(code)
        policy = self.news_analyzer.analyze_fifteen_five_policy(code, news)
        val = self.valuation_analyzer.analyze_valuation(code, price)
        sugg = ('sell' if policy['suggestion'] == 'sell' or val['suggestion'] == 'sell'
                else 'buy' if policy['suggestion'] == 'buy' or val['suggestion'] == 'buy'
                else 'hold')
        return {
            'code': code, 'name': name, 'news_count': len(news),
            'policy_analysis': policy, 'valuation_analysis': val,
            'final_suggestion': sugg, 'news_list': news[:2],
            'data_sources': list(set(n.get('type','') for n in news)),
            'analysis_quality': 'basic'
        }


def generate_daily_report(portfolio_file='config/portfolio.yaml', report_file=None,
                          rebalance_threshold=1.0, enable_ai_analysis=True):
    today_str = datetime.now().strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if report_file is None:
        report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports', today_str)
        os.makedirs(report_dir, exist_ok=True)
        report_file = os.path.join(report_dir, 'daily_report.md')

    with open(portfolio_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    assets = config['assets']
    target_weights = {a['code']: a['target_weight'] for a in assets}
    names = {a['code']: a['name'] for a in assets}

    base_dir = os.path.dirname(os.path.abspath(__file__))
    positions_path = os.path.join(base_dir, 'config', 'positions.json')
    
    actual_positions = {}
    cash = 0
    if os.path.exists(positions_path):
        with open(positions_path, 'r', encoding='utf-8') as f:
            pos_data = json.load(f)
            actual_positions = pos_data.get('positions', {})
            cash = pos_data.get('cash', 0)
    
    positions = {}
    # 从 config 读取初始资金，优先 settings.yaml → portfolio.yaml → positions.json → 3000000
    total_value = 3000000
    try:
        yaml_path = os.path.join(base_dir, 'config', 'settings.yaml')
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r', encoding='utf-8') as f:
                stg = yaml.safe_load(f)
                total_value = float(stg.get('initial_capital', total_value))
        if total_value == 3000000:
            total_value = float(config.get('initial_capital', total_value))
        # 如果 positions.json 有正确的 total_value，用它覆盖（含浮动盈亏）
        if os.path.exists(positions_path):
            pdata = json.load(open(positions_path, 'r', encoding='utf-8'))
            pv = pdata.get('total_value', 0)
            # 优先使用positions.json中的实际总值（只要大于初始资金就采用）
            if pv > total_value:
                total_value = float(pv)
                logging.info(f"[total_value] 使用positions.json中的实际总值: ¥{total_value:,.0f}")
            else:
                logging.info(f"[total_value] 使用config中的初始资金: ¥{total_value:,.0f}")
    except Exception as e:
        logging.warning(f"加载配置文件失败: {e}")

    ai_analyses = {}
    risk_report = None
    factor_report = None
    if enable_ai_analysis:
        if _ENHANCED_AVAILABLE:
            suggestion_engine = EnhancedSuggestionEngine()
            try:
                early_warning = PortfolioRiskEarlyWarning()
                risk_report = early_warning.generate_risk_report(
                    [a['code'] for a in assets]
                )
            except Exception:
                pass
            try:
                factor_gen = get_factor_generator()
                factor_report = factor_gen.compute_portfolio_factors(
                    [a['code'] for a in assets]
                )
            except Exception:
                pass
        else:
            suggestion_engine = FallbackEngine()

    # ================================================================
    #  批量获取行情数据 (Wind / iFinD / 新浪三级回退 + 并发)
    # ================================================================
    stock_codes = [a['code'] for a in assets if not (a['code'].startswith('5') or a['code'].startswith('15'))]
    fund_codes = [a['code'] for a in assets if a['code'].startswith('5') or a['code'].startswith('15')]

    if _WIND_PROVIDER_OK:
        quotes = get_quotes_batch(stock_codes, fund_codes, max_workers=5)
    else:
        quotes = {}
        for a in assets:
            quotes[a['code']] = {'price': 0, 'change': 0, 'source': 'unavailable'}

    # ================================================================
    #  止损止盈实时监控
    # ================================================================
    sl_alerts = None
    sl_report_text = None
    if _SL_MONITOR_OK:
        try:
            sl_monitor = StopLossMonitor()
            # 构建监控所需的quotes格式: {code: {'price': float, 'high': float|None, ...}}
            sl_quotes = {}
            for code, q in quotes.items():
                price = q.get('price', 0)
                # 增加价格合理性验证: 过滤异常价格
                if price > 0:
                    # 对于股票，价格应该在合理范围内
                    if price < 10000:  # 合理价格上限
                        sl_quotes[code] = {
                            'price': price,
                            'high': q.get('high'),
                            'low': q.get('low')
                        }
            
            # 调试日志：打印获取到的行情数据
            logging.info(f"[止损监控] 获取到行情数据: {len(sl_quotes)}/{len(quotes)} 只标的")
            if sl_quotes:
                logging.info(f"[止损监控] 标的代码: {list(sl_quotes.keys())[:10]}...")
            
            if sl_quotes:
                sl_alerts = sl_monitor.check_all(sl_quotes)
                # 统计有数据的标的
                with_data = sum(1 for a in sl_alerts if 'error' not in a)
                without_data = sum(1 for a in sl_alerts if 'error' in a)
                triggered = sum(1 for a in sl_alerts if a.get('alert_level') in ['triggered', 'critical', 'warning'])
                logging.info(f"[止损监控] 检查结果: {len(sl_alerts)}只标的, {with_data}只有数据, {without_data}只无数据, {triggered}只有警报")
                
                # 生成报告文本
                sl_report_text = generate_risk_alert_report(sl_alerts, include_header=False)
                logging.info(f"[止损监控] 报告生成成功, 长度: {len(sl_report_text)} 字符")
            else:
                logging.warning("[止损监控] ⚠️ sl_quotes为空,无法进行检查")
        except Exception as e:
            import traceback
            logging.error(f"[止损监控] ❌ 异常: {e}\n{traceback.format_exc()}")
            sl_alerts = None
            sl_report_text = None

    # ---- 报告生成 ----
    report_lines = []
    
    # 头部装饰
    report_lines.append("=" * 80)
    report_lines.append(f"📊 {today} 实时持仓报告 (含AI分析)")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    # 实时行情概览
    report_lines.append("## 📈 实时行情概览")
    report_lines.append("-" * 80)

    source_icons = {
        'wind_analytics': '☁️Wind分析',
        'wind_direct': '⚡Wind直连',
        'ifind': '📡iFinD',
        'sina': '🌐新浪',
        'failed': '❌失败',
        'error': '💥异常',
        'unavailable': '⚠️不可用',
    }

    for a in assets:
        code = a['code']
        r = quotes.get(code, {'price': 0, 'change': 0, 'source': '?'})

        if r['price'] > 0:
            target_w = target_weights[code]
            
            if code in actual_positions:
                shares = actual_positions[code].get('shares', 0)
            else:
                target_amount = total_value * target_w
                shares = int(target_amount / r['price'] / 100) * 100
            
            mv = shares * r['price']

            positions[code] = {
                'name': names[code],
                'price': r['price'],
                'change': r['change'],
                'shares': shares,
                'market_value': mv,
                'target_weight': target_w
            }

            status = "📈" if r['change'] >= 0 else "📉"
            src_tag = source_icons.get(r.get('source', ''), '')
            change_color = "🟢" if r['change'] > 0 else "🔴" if r['change'] < 0 else "⚪"
            report_lines.append(
                f"  {status} {names[code]:<12} {code:<10} "
                f"¥{r['price']:>8.2f}  {change_color} {r['change']:>+6.2f}%  [{src_tag}]"
            )

            if enable_ai_analysis:
                ai_analyses[code] = suggestion_engine.analyze_stock(code, names[code], r['price'])
        else:
            src_tag = source_icons.get(r.get('source', 'failed'), '❌')
            report_lines.append(f"  ❌ {names[code]:<12} {code:<10} 无法获取实时数据 ({src_tag})")

    report_lines.append("")
    
    # 持仓明细
    report_lines.append("## 📋 持仓明细")
    report_lines.append("-" * 80)

    total_mv = 0
    weight_diffs = []
    
    # 持仓明细表头
    report_lines.append(f"  {'状态':<4} {'标的':<12} {'持仓':>8} {'价格':>10} {'市值':>14} {'权重':>10} {'偏差':>10}")
    report_lines.append(f"  {'-'*4} {'-'*12} {'-'*8} {'-'*10} {'-'*14} {'-'*10} {'-'*10}")
    
    for code, pos in positions.items():
        actual_weight = pos['market_value'] / total_value * 100
        weight_diff = actual_weight - pos['target_weight'] * 100
        weight_diffs.append((pos['name'], weight_diff))

        diff_status = "✅" if abs(weight_diff) <= rebalance_threshold else "⚠️"
        diff_color = "🟢" if weight_diff > 0 else "🔴" if weight_diff < 0 else "⚪"
        report_lines.append(
            f"  {diff_status:<4} {pos['name']:<12} {pos['shares']:>6}股 "
            f"¥{pos['price']:>8.2f}  ¥{pos['market_value']:>12,.0f}  "
            f"{actual_weight:>6.2f}% ({pos['target_weight']*100:>4.1f}%)  "
            f"{diff_color}{weight_diff:>+.2f}%"
        )
        total_mv += pos['market_value']

    report_lines.append("")
    
    # 账户总览
    report_lines.append("## 💰 账户总览")
    report_lines.append("-" * 80)
    report_lines.append(f"  持仓市值: ¥{total_mv:>18,.2f}")
    report_lines.append(f"  可用现金: ¥{cash:>18,.2f}")
    report_lines.append(f"  账户总值: ¥{total_mv + cash:>18,.2f}")
    
    # 建仓盈亏分析（以建仓成本为基准）
    report_lines.append("")
    report_lines.append("## 📈 建仓盈亏分析（以建仓成本为基准）")
    report_lines.append("-" * 80)
    
    # 计算总建仓成本和当前盈亏
    total_cost_basis = 0
    total_current_value = 0
    profit_details = []
    
    for code, pos in positions.items():
        if code == 'CASH':
            continue
        
        if code in actual_positions:
            pos_info = actual_positions[code]
            shares = pos_info.get('shares', 0)
            avg_cost = pos_info.get('avg_cost', 0)
            
            if shares > 0 and avg_cost > 0:
                cost_basis = shares * avg_cost
                current_value = pos['market_value']
                profit_loss = current_value - cost_basis
                profit_pct = (profit_loss / cost_basis * 100) if cost_basis > 0 else 0
                
                total_cost_basis += cost_basis
                total_current_value += current_value
                
                status_icon = "🟢" if profit_loss > 0 else "🔴" if profit_loss < 0 else "⚪"
                
                profit_details.append({
                    'code': code,
                    'name': pos['name'],
                    'shares': shares,
                    'cost': avg_cost,
                    'current_price': pos['price'],
                    'cost_basis': cost_basis,
                    'current_value': current_value,
                    'profit_loss': profit_loss,
                    'profit_pct': profit_pct,
                    'icon': status_icon
                })
    
    profit_details.sort(key=lambda x: x['profit_loss'])
    
    if profit_details:
        # 盈亏明细表头
        report_lines.append(f"  {'盈亏':<4} {'标的':<12} {'持仓':>8} {'成本':>8} {'现价':>8} {'建仓成本':>12} {'当前市值':>12} {'盈亏':>10} {'盈亏%':>8}")
        report_lines.append(f"  {'-'*4} {'-'*12} {'-'*8} {'-'*8} {'-'*8} {'-'*12} {'-'*12} {'-'*10} {'-'*8}")
        
        for pd_item in profit_details:
            report_lines.append(
                f"  {pd_item['icon']:<4} {pd_item['name']:<12} {pd_item['shares']:>6}股 "
                f"¥{pd_item['cost']:>6.2f} "
                f"¥{pd_item['current_price']:>6.2f} "
                f"¥{pd_item['cost_basis']:>10,.0f} "
                f"¥{pd_item['current_value']:>10,.0f} "
                f"¥{pd_item['profit_loss']:>+8,.0f} "
                f"{pd_item['profit_pct']:>+6.2f}%"
            )
        
        # 汇总统计
        report_lines.append("")
        total_profit = sum(p['profit_loss'] for p in profit_details)
        total_profit_pct = (total_profit / total_cost_basis * 100) if total_cost_basis > 0 else 0
        
        overall_icon = "🟢" if total_profit > 0 else "🔴" if total_profit < 0 else "⚪"
        report_lines.append(f"  {overall_icon} 汇总统计")
        report_lines.append(f"    • 总建仓成本: ¥{total_cost_basis:>18,.2f}")
        report_lines.append(f"    • 当前总市值: ¥{total_current_value:>18,.2f}")
        report_lines.append(f"    • 总盈亏金额: ¥{total_profit:>18,.2f}")
        report_lines.append(f"    • 总盈亏比例: {total_profit_pct:>+18.2f}%")
        
        profitable = [p for p in profit_details if p['profit_loss'] > 0]
        losing = [p for p in profit_details if p['profit_loss'] < 0]
        flat = [p for p in profit_details if p['profit_loss'] == 0]
        
        report_lines.append(f"    • 盈利标的: {len(profitable)} 只 (总盈利 ¥{sum(p['profit_loss'] for p in profitable):,.0f})")
        report_lines.append(f"    • 亏损标的: {len(losing)} 只 (总亏损 ¥{sum(p['profit_loss'] for p in losing):,.0f})")
        report_lines.append(f"    • 持平标的: {len(flat)} 只")
        
        if profitable:
            best_performer = max(profitable, key=lambda x: x['profit_pct'])
            report_lines.append(f"    • 🌟 最佳表现: {best_performer['name']} (+{best_performer['profit_pct']:.2f}%)")
        
        if losing:
            worst_performer = min(losing, key=lambda x: x['profit_pct'])
            report_lines.append(f"    • 💫 最差表现: {worst_performer['name']} ({worst_performer['profit_pct']:.2f}%)")
        
        max_single_loss = max(losing, key=lambda x: abs(x['profit_pct'])) if losing else None
        if max_single_loss and max_single_loss['profit_pct'] < -5:
            report_lines.append(f"    • ⚠️ 风险警示: {max_single_loss['name']} 亏损超过5%，建议关注!")
    
    # 操作建议
    report_lines.append("")
    report_lines.append("## 🎯 操作建议 (阈值: ±{}%)".format(rebalance_threshold))
    report_lines.append("-" * 80)

    overweight_stocks = [(n, d) for n, d in weight_diffs if d > rebalance_threshold]
    underweight_stocks = [(n, d) for n, d in weight_diffs if d < -rebalance_threshold]

    if overweight_stocks:
        report_lines.append("  📤 需减仓标的:")
        for name, diff in overweight_stocks:
            report_lines.append(f"    • {name}: 超配 {diff:.2f}%")
    if underweight_stocks:
        report_lines.append("  📥 需加仓标的:")
        for name, diff in underweight_stocks:
            report_lines.append(f"    • {name}: 低配 {abs(diff):.2f}%")
    if not overweight_stocks and not underweight_stocks:
        report_lines.append("  ✅ 当前持仓权重与目标权重偏差在阈值范围内，无需操作")

    # 实时表现分析
    report_lines.append("")
    report_lines.append("## 📊 实时表现分析")
    report_lines.append("-" * 80)
    up_count = sum(1 for p in positions.values() if p['change'] >= 0)
    down_count = len(positions) - up_count
    report_lines.append(f"  上涨标的: {up_count} 只")
    report_lines.append(f"  下跌标的: {down_count} 只")
    if positions:
        best = max(positions.values(), key=lambda x: x['change'])
        worst = min(positions.values(), key=lambda x: x['change'])
        report_lines.append(f"  🌟 表现最佳: {best['name']} (+{best['change']:.2f}%)")
        report_lines.append(f"  💫 表现最弱: {worst['name']} ({worst['change']:.2f}%)")

    # 策略建议
    report_lines.append("")
    report_lines.append("## 💡 策略建议")
    report_lines.append("-" * 80)
    total_change = sum(p['change'] * p['target_weight'] for p in positions.values())
    report_lines.append(f"  组合实时收益: {total_change:+.2f}%")
    if total_change >= 1:
        report_lines.append("  ✅ 当前市场表现良好，建议继续持有")
    elif total_change <= -1:
        report_lines.append("  ⚠️ 当前市场波动较大，建议关注回撤风险")
    else:
        report_lines.append("  📊 市场震荡整理，建议观望为主")

    # 操作计划
    report_lines.append("")
    report_lines.append("## ⏰ 操作计划")
    report_lines.append("-" * 80)
    report_lines.append("  • 持续监控实时行情变化")
    report_lines.append("  • 当权重偏差超过阈值时执行再平衡")
    report_lines.append("  • 关注市场风险，设置止损提醒")

    # AI 分析部分
    if enable_ai_analysis and ai_analyses:
        report_lines.append("")
        report_lines.append("## 🤖 AI智能分析")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append("### 📰 十五五规划政策影响分析")

        sell_suggestions = []
        hold_suggestions = []
        buy_suggestions = []

        for code, analysis in ai_analyses.items():
            name = analysis['name']
            sugg = analysis['final_suggestion']
            pa = analysis['policy_analysis']
            va = analysis['valuation_analysis']

            report_lines.append(f"  ── {name} ({code}) ──")
            if pa['has_policy_news']:
                keywords = ', '.join(pa['keyword_hits'])
                report_lines.append("  📜 政策相关: ✅ 有相关新闻")
                report_lines.append(f"    • 关键词: {keywords}")
                report_lines.append(f"    • 政策得分: {pa['policy_score']:.1f}")
                if pa['has_benefit_theme']:
                    report_lines.append("    • ✅ 受益于十五五规划相关主题")
            else:
                report_lines.append("  📜 政策相关: ❌ 暂无相关新闻")

            val_level_map = {'overvalued': '📈高估', 'high': '⬆️偏高',
                             'fair': '➖合理', 'undervalued': '📉低估'}
            val_text = val_level_map.get(va['level'], va['level'])
            report_lines.append(f"  💰 估值分析: {val_text}")
            report_lines.append(f"    • 估值评分: {va['score']:.1f}/10")

            sugg_icon = '🔴清仓' if sugg == 'sell' else '🟡持有' if sugg == 'hold' else '🟢关注'
            report_lines.append(f"  🎯 AI建议: {sugg_icon}")

            if sugg == 'sell':
                reason = []
                if pa['suggestion'] == 'sell':
                    reason.append('政策落地，建议获利了结')
                if va['suggestion'] == 'sell':
                    reason.append('估值过高')
                sell_suggestions.append((name, code, '；'.join(reason) if reason else ''))
            elif sugg == 'buy':
                buy_suggestions.append((name, code))
            else:
                hold_suggestions.append((name, code))

        report_lines.append("")
        report_lines.append("### 🎯 AI交易建议")
        if sell_suggestions:
            report_lines.append("  🔴 建议清仓:")
            for name, code, reason in sell_suggestions:
                report_lines.append(f"    • {name} ({code})")
                if reason:
                    report_lines.append(f"      原因: {reason}")
        if hold_suggestions:
            report_lines.append("  🟡 建议持有:")
            hold_names = [f"{name} ({code})" for name, code in hold_suggestions]
            report_lines.append(f"    • {', '.join(hold_names[:5])}{'...' if len(hold_names) > 5 else ''}")
            if len(hold_names) > 5:
                report_lines.append(f"    • 等共 {len(hold_suggestions)} 只标的")
        if buy_suggestions:
            report_lines.append("  🟢 建议关注/加仓:")
            for name, code in buy_suggestions:
                report_lines.append(f"    • {name} ({code})")

        report_lines.append("")
        report_lines.append("### 💡 AI综合判断")
        if len(sell_suggestions) > 5:
            report_lines.append("  ⚠️ 检测到较多建议清仓标的，建议逐步获利了结")
        elif len(sell_suggestions) > 0:
            report_lines.append("  📊 部分标的触发清仓条件，建议评估后操作")
        else:
            report_lines.append("  ✅ 当前持仓总体稳定，建议继续持有")

    # 事件驱动因子分析
    if factor_report and 'error' not in factor_report:
        report_lines.append("")
        report_lines.append("## 📊 事件驱动因子分析 (YiZhao)")
        report_lines.append("-" * 80)
        report_lines.append(f"  组合综合因子: {factor_report['portfolio_composite']:.4f}")
        report_lines.append(f"  主导信号: {factor_report['dominant_signal']}")
        report_lines.append(f"  信号分布: {factor_report['signal_distribution']}")
        report_lines.append("")
        report_lines.append("  各标的因子详情:")
        for code, info in factor_report.get('code_factors', {}).items():
            f_ = info.get('factors', {})
            factor_text = f"{code}: 综合={info['composite']:.3f} S={f_.get('sentiment', 0):.2f} E={f_.get('event_impact', 0):.2f} H={f_.get('text_heat', 0):.2f} I={f_.get('industry_corr', 0):.2f} P={f_.get('policy_bias', 0):.2f}"
            report_lines.append(f"    • {factor_text}")

    # 风险预警
    if risk_report:
        report_lines.append("")
        report_lines.append("## ⚠️ 舆情风险预警 (YiZhao)")
        report_lines.append("-" * 80)
        report_lines.append(f"  预警级别: {risk_report['alert_level']}")
        report_lines.append(f"  预警数量: {risk_report['warning_count']}")
        report_lines.append(f"  建议: {risk_report['suggestion']}")
        if risk_report.get('warnings'):
            report_lines.append("")
            report_lines.append("  预警详情:")
            for w in risk_report['warnings']:
                report_lines.append(f"    • ⚠️ {w['code']}: {w['high_risk_count']}个高风险事件")

    # 止损止盈实时监控
    logging.info(f"[报告生成] sl_alerts 类型: {type(sl_alerts)}, 长度: {len(sl_alerts) if sl_alerts else 0}")
    logging.info(f"[报告生成] sl_report_text 类型: {type(sl_report_text)}, 长度: {len(sl_report_text) if sl_report_text else 0}")
    
    if sl_alerts and sl_report_text:
        report_lines.append("")
        report_lines.append("## 🛡️ 止损止盈风险监控")
        report_lines.append("-" * 80)
        for line in sl_report_text.strip().split('\n'):
            report_lines.append(f"  {line}")
        logging.info("[报告生成] ✅ 止损监控报告已添加到报告")
    elif _SL_MONITOR_OK and sl_alerts is None:
        report_lines.append("")
        report_lines.append("## 🛡️ 止损止盈风险监控")
        report_lines.append("-" * 80)
        report_lines.append("  ⚠️ 止损止盈模块已加载，但当前无有效行情数据可供检查")
        logging.warning("[报告生成] ⚠️ sl_alerts 为 None, 无法生成止损监控报告")
    else:
        logging.error(f"[报告生成] ❌ sl_alerts={sl_alerts}, sl_report_text长度={len(sl_report_text) if sl_report_text else 0}")

    # ---- 大模型深度解读 ----
    if _LLM_ANALYZER_OK and enable_ai_analysis:
        try:
            llm_analyzer = LLMReportAnalyzer()
            llm_analysis = llm_analyzer.analyze_report('\n'.join(report_lines))
            llm_report_text = format_llm_analysis_for_report(llm_analysis)
            report_lines.append(llm_report_text)
        except Exception as e:
            import traceback
            logger = logging.getLogger('DailyReport')
            logger.warning(f"LLM分析失败: {e}")

    # 数据源统计 & 报告尾部
    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("## 📋 报告元数据")
    report_lines.append("-" * 80)
    report_lines.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if _WIND_PROVIDER_OK:
        stats = _get_wind_stats()
        ok_count = stats.get('wind_analytics_ok', 0) + stats.get('wind_direct_ok', 0) + \
                   stats.get('ifind_ok', 0) + stats.get('sina_ok', 0)
        total_calls = stats.get('total_calls', 0)
        fail_count = stats.get('all_failed', 0)

        sources = []
        wa = stats.get('wind_analytics_ok', 0)
        wd = stats.get('wind_direct_ok', 0)
        ifi = stats.get('ifind_ok', 0)
        sin = stats.get('sina_ok', 0)
        if wa: sources.append(f"Wind-NL({wa})")
        if wd: sources.append(f"Wind-API({wd})")
        if ifi: sources.append(f"iFinD({ifi})")
        if sin: sources.append(f"新浪({sin})")

        report_lines.append(f"  数据源: {' + '.join(sources) if sources else '无'}")
        report_lines.append(f"  成功率: {ok_count}/{total_calls}")
        if fail_count > 0:
            report_lines.append(f"  ⚠️ {fail_count} 只标的所有数据源均失败")
    else:
        report_lines.append("  数据源: wind_data_provider 未加载 (降级模式)")

    if _ENHANCED_AVAILABLE:
        report_lines.append("  AI分析: 十五五规划政策 + 估值分析 + 舆情因子 + 风险预警")
    else:
        report_lines.append("  AI分析: 十五五规划政策 + 估值分析")
    if _SL_MONITOR_OK:
        sl_status = "已启用" if sl_alerts else "无数据"
        report_lines.append(f"  止损监控: {sl_status} (5只核心持仓)")
    if _LLM_ANALYZER_OK:
        llm_status = "已启用 (豆包Seed 2.0 Pro)" if enable_ai_analysis else "未启用"
        report_lines.append(f"  LLM解读: {llm_status}")

    report_content = '\n'.join(report_lines)

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(report_content)
    return report_content


if __name__ == '__main__':
    generate_daily_report()
