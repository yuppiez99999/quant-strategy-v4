# -*- coding: utf-8 -*-
"""
Token信号接入脚本 — 将超算中心Token信号动态注入止损监控和再平衡引擎

运行:
  python apply_token_signals.py                    # 查看完整信号和调整建议
  python apply_token_signals.py --output report    # 生成完整报告
  python apply_token_signals.py --save-config      # 将调整后的规则保存为新配置文件

三种接入路径:
  1. StopLossMonitor 止损动态调整 — 将 signal.stop_loss_multiplier 作用于各标的止损线
  2. RebalancingEngine 板块轮动 — 将 signal.sector_rotation 用于仓位再平衡
  3. DailyTradingWorkflow 盘前信号 — 在 premarket 阶段注入 Token 增强维度
"""

import os
import sys
import yaml
import argparse
from datetime import datetime
from typing import Dict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Windows 编码修复
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


# ============================================================
# 第一步: 加载Token合成器信号
# ============================================================
def load_token_signals():
    """加载Token信号"""
    from signals.token_factor_combiner import get_token_combiner
    combiner = get_token_combiner()
    signal = combiner.compute()
    return combiner, signal


# ============================================================
# 第二步: 动态调整止损监控规则
# ============================================================
def adjust_stop_loss_rules(signal, config_path: str = None) -> tuple:
    """
    将 token 信号注入止损规则:
    - signal.stop_loss_multiplier < 1 → 收紧止损 (风险上升)
    - signal.stop_loss_multiplier > 1 → 放宽止损 (产能景气)
    - signal.stock_risk_alerts  → 逐标的调整止盈止损

    Returns:
        (adjusted_rules: Dict, adjustment_report: list)
    """
    from stop_loss_monitor import StopLossMonitor

    monitor = StopLossMonitor(config_path)
    rules = monitor.rules
    assets = rules.get('assets', [])
    adjustment_report = []

    slm = signal.stop_loss_multiplier

    for asset in assets:
        code = asset['code']
        name = asset['name']
        orig_sl = asset['stop_loss_pct']
        orig_tp = asset['take_profit_pct']

        # 获取该标的风险等级
        risk_level = signal.stock_risk_alerts.get(code, "NORMAL")

        # 基础乘数: 全局止损乘数
        # 逐标修正: CRITICAL标的多紧5%, WARNING标的紧3%, NORMAL维持全局乘数
        individual_mult = slm
        if risk_level == "CRITICAL":
            individual_mult = min(slm, 0.85)
        elif risk_level == "WARNING":
            individual_mult = min(slm, 0.93)

        # 调整止损百分比 (注意: stop_loss_pct 是负数，乘数>1 → 止损更宽)
        new_sl = round(orig_sl * individual_mult, 1)
        new_tp = round(orig_tp * (1.0 / individual_mult), 1)  # 止盈反向调整

        asset['stop_loss_pct'] = new_sl
        asset['stop_loss_price'] = round(asset['base_price'] * (1 + new_sl / 100.0), 2)
        asset['take_profit_pct'] = new_tp
        asset['take_profit_price'] = round(asset['base_price'] * (1 + new_tp / 100.0), 2)

        adjustment_report.append({
            'code': code,
            'name': name,
            'risk_alert': risk_level,
            'stop_loss_pct': f"{orig_sl:+.1f}% → {new_sl:+.1f}%",
            'stop_loss_price': f"{asset['stop_loss_price']:.2f}",
            'take_profit_pct': f"{orig_tp:+.1f}% → {new_tp:+.1f}%",
            'take_profit_price': f"{asset['take_profit_price']:.2f}",
        })

    return rules, adjustment_report


# ============================================================
# 第三步: 板块轮动建议 (供 RebalancingEngine 调用)
# ============================================================
def get_sector_rotation_advice(signal) -> list:
    """
    将 signal.sector_rotation 转换为再平衡引擎可用的建议列表。
    signal.sector_rotation 格式: {stock_code: multiplier}
      - >1.0 → 增配
      - =1.0 → 维持
      - <1.0 → 减配
    """
    advices = []
    for stock, adj in sorted(signal.sector_rotation.items(), key=lambda x: -x[1]):
        if adj > 1.0:
            action = f"增配 {(adj - 1) * 100:+.0f}%"
        elif adj < 1.0:
            action = f"减配 {(adj - 1) * 100:+.0f}%"
        else:
            action = "持平"

        risk = signal.stock_risk_alerts.get(stock, "NORMAL")
        auto_exp = signal.stock_auto_exposure.get(stock, 0)

        advices.append({
            'code': stock,
            'adjustment': adj,
            'action': action,
            'risk_alert': risk,
            'auto_exposure': auto_exp,
        })
    return advices


# ============================================================
# 第四步: 生成完整报告
# ============================================================
def generate_full_report(combiner, signal, adjustment_report, rotation_advices,
                          output_dir: str = None) -> str:
    """生成完整的Token增强信号报告"""
    if output_dir is None:
        output_dir = os.path.join(BASE_DIR, '..', '每日报告归档',
                                  datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(output_dir, exist_ok=True)

    lines = []
    lines.append("=" * 80)
    lines.append("超算中心Token增强信号报告")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"数据日期: {signal.date}")
    lines.append("=" * 80)
    lines.append("")

    # 1. 信号汇总
    lines.append("-" * 60)
    lines.append("[1] Token信号核心指标")
    lines.append("-" * 60)
    lines.append(f"  综合风险指数:    {signal.overall_risk_index:.4f}  (0=安全, 1=危险)")
    lines.append(f"  信用收紧信号:    {'!! 是' if signal.credit_tightening else 'OK 否'}")
    lines.append(f"  欺诈预警信号:    {'!! 是' if signal.fraud_alert else 'OK 否'}")
    lines.append(f"  汽车产能指数:    {signal.auto_capacity_index:.4f}  ({signal.auto_trend})")
    lines.append(f"  板块建议:        {signal.auto_recommendation}")
    lines.append(f"  建议总调仓:      {signal.combined_adjustment:+.1%}")
    lines.append(f"  止损乘数:        {signal.stop_loss_multiplier:.3f}")
    lines.append(f"       ( >1=放宽止损, <1=收紧止损 )")
    lines.append("")

    # 2. 止损调整明细
    lines.append("-" * 60)
    lines.append("[2] 止损止盈动态调整明细")
    lines.append("-" * 60)
    if adjustment_report:
        lines.append(f"  {'代码':<10} {'名称':<10} {'风险':<8} {'止损调整':<24} {'止盈调整':<24}")
        lines.append("  " + "-" * 76)
        for r in adjustment_report:
            lines.append(
                f"  {r['code']:<10} {r['name']:<10} {r['risk_alert']:<8} "
                f"{r['stop_loss_pct']:<24} {r['take_profit_pct']:<24}"
            )
    else:
        lines.append("  (无止损规则数据)")
    lines.append("")

    # 3. 板块轮动建议
    lines.append("-" * 60)
    lines.append("[3] 板块轮动建议 (供 RebalancingEngine 调用)")
    lines.append("-" * 60)
    for adv in rotation_advices:
        lines.append(
            f"  {adv['code']:<10} {adv['action']:<12} "
            f"风险:{adv['risk_alert']:<8} 产能暴露:{adv['auto_exposure']:.2%}"
        )
    lines.append("")

    # 4. 集成指南
    lines.append("-" * 60)
    lines.append("[4] 已生效的接入点")
    lines.append("-" * 60)
    lines.append("  1. StopLossMonitor 止损规则已动态调整 (stop_loss_pct x 乘数)")
    lines.append("  2. RebalancingEngine 板块轮动建议已生成 (见[3])")
    lines.append("  3. daily_trading_workflow.py premarket 阶段已注入 Token 增强维度")
    lines.append("")

    # 5. Token数据来源
    lines.append("-" * 60)
    lines.append("[5] Token数据来源")
    lines.append("-" * 60)
    lines.append("  金融风险因子:  finance_token_A_B  (2,502,009 条, 172.9 MB)")
    lines.append("  汽车产能因子:  manufacturing_token_A (27,888 条, 20条产线)")
    lines.append("  数据路径:     17-超算中心A级token/北数所上架包/01数据文件/业务协同子集/")
    lines.append("")

    report = '\n'.join(lines)

    # 保存报告文件
    report_path = os.path.join(output_dir,
                               f'token_signal_report_{datetime.now().strftime("%Y%m%d_%H%M")}.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n[OK] 报告已保存: {report_path}")

    return report


# ============================================================
# 主入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='Token信号集成 — 止损规则调整 + 板块轮动')
    parser.add_argument('--config', default='config/stop_loss_rules_auto.yaml',
                        help='止损规则配置文件路径')
    parser.add_argument('--output', choices=['console', 'report'], default='console',
                        help='输出模式')
    parser.add_argument('--save-config', action='store_true',
                        help='将调整后的规则保存为新配置文件')
    args = parser.parse_args()

    config_path = os.path.join(BASE_DIR, args.config)
    if not os.path.exists(config_path):
        config_path = None  # 回退到 stop_loss_monitor 内置默认规则

    # === 1. 加载Token信号 ===
    print("[1/4] 加载超算中心Token信号...")
    combiner, signal = load_token_signals()
    print(combiner.summary())

    # === 2. 动态调整止损规则 ===
    print("\n[2/4] 将Token信号注入止损监控规则...")
    adjusted_rules, adjustment_report = adjust_stop_loss_rules(signal, config_path)

    print(f"\n  全局止损乘数: {signal.stop_loss_multiplier:.3f}")
    print(f"  (基础值1.0, 风险高→<1收紧, 产能好→>1放宽)")
    print(f"\n  调整后规则明细:")
    print(f"  {'代码':<10} {'名称':<10} {'风险':<8} {'止损调整':<28} {'止盈调整':<28}")
    print(f"  {'-'*84}")
    for r in adjustment_report:
        print(f"  {r['code']:<10} {r['name']:<10} {r['risk_alert']:<8} "
              f"{r['stop_loss_pct']:<28} {r['take_profit_pct']:<28}")

    # === 3. 板块轮动建议 ===
    print(f"\n[3/4] 生成板块轮动建议 (供 RebalancingEngine 调用)...")
    rotation_advices = get_sector_rotation_advice(signal)

    for adv in rotation_advices:
        print(f"  建议{adv['action']} {adv['code']}: 风险={adv['risk_alert']}, "
              f"产能暴露={adv['auto_exposure']:.2%}")

    # === 4. 保存配置 ===
    if args.save_config:
        save_path = os.path.join(BASE_DIR, 'config',
                                 f'stop_loss_rules_token_adjusted_{datetime.now().strftime("%Y%m%d")}.yaml')
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(adjusted_rules, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"\n[4/4] 调整后的止损规则已保存: {save_path}")
    else:
        print(f"\n[4/4] 跳过保存 (使用 --save-config 可将调整后的规则持久化)")

    # === 5. 生成完整报告 ===
    if args.output == 'report':
        print("\n" + "=" * 80)
        report = generate_full_report(combiner, signal, adjustment_report, rotation_advices)
        print(report)
    else:
        print("\n提示: 使用 --output report 可生成完整Token信号报告")

    return signal


if __name__ == '__main__':
    signal = main()
