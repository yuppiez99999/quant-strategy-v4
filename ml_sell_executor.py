#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ML信号驱动卖出执行脚本
=====================================
基于 GradientBoosting 模型预测的下跌信号，在指定日期开盘时自动卖出

执行标的（2026-06-29 开盘）:
  - 510300 (沪深300ETF)   下跌概率 63.56%
  - 510500 (中证500ETF)   下跌概率 62.33%
  - 600519 (贵州茅台)     下跌概率 56.84%

模型信息:
  - 模型: GradientBoosting
  - 准确率: 56.01%
  - F1分数: 0.6280
  - 阈值: 55%
"""

import os
import sys
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('ml_sell_executor')


class MLSellExecutor:
    """ML信号驱动卖出执行器"""

    def __init__(self, config_dir: str = 'config', output_dir: str = '每日报告归档'):
        self.config_dir = Path(config_dir)
        self.output_dir = Path(output_dir)
        self.positions_file = self.config_dir / 'positions.json'
        self.portfolio_file = self.config_dir / 'portfolio.yaml'
        self.stop_loss_file = self.config_dir / 'stop_loss_rules_auto.yaml'

        # 卖出信号标的（ML预测下跌概率 > 55%）
        self.sell_signals = {
            '510300': {'down_prob': 0.6356, 'name': '沪深300ETF', 'action': 'SELL'},
            '510500': {'down_prob': 0.6233, 'name': '中证500ETF', 'action': 'SELL'},
            '600519': {'down_prob': 0.5684, 'name': '贵州茅台', 'action': 'SELL'},
            '159980': {'down_prob': 0.6849, 'name': '有色ETF', 'action': 'MONITOR'},  # 不在持仓
            '511260': {'down_prob': 0.5647, 'name': '国债ETF', 'action': 'MONITOR'},  # 不在持仓
        }

        # 执行日期
        self.execute_date = '2026-06-29'
        self.execute_time = '09:30:00'  # 开盘时间

    def load_positions(self) -> Dict:
        """加载当前持仓"""
        if not self.positions_file.exists():
            logger.error(f"持仓文件不存在: {self.positions_file}")
            return {}

        with open(self.positions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"[POSITIONS] 加载持仓数据: {len(data.get('positions', {}))} 个标的")
        logger.info(f"[POSITIONS] 总资产: ¥{data.get('total_value', 0):,.2f}")
        logger.info(f"[POSITIONS] 现金: ¥{data.get('cash', 0):,.2f}")

        return data

    def calculate_sell_amount(self, code: str, position_data: Dict) -> Dict:
        """计算卖出数量和金额"""
        shares = position_data.get('shares', 0)
        avg_cost = position_data.get('avg_cost', 0)
        current_price = position_data.get('current_price', avg_cost)

        if shares <= 0:
            return None

        # 卖出策略：根据下跌概率决定卖出比例
        down_prob = self.sell_signals.get(code, {}).get('down_prob', 0.55)

        if down_prob >= 0.65:
            # 高置信度下跌信号：卖出全部持仓
            sell_ratio = 1.0
            sell_reason = "ML高置信度下跌信号(≥65%)"
        elif down_prob >= 0.60:
            # 中置信度下跌信号：卖出50%持仓
            sell_ratio = 0.5
            sell_reason = "ML中置信度下跌信号(60-65%)"
        else:
            # 低置信度下跌信号：卖出30%持仓
            sell_ratio = 0.3
            sell_reason = "ML下跌信号(55-60%)"

        sell_shares = int(shares * sell_ratio)
        sell_amount = sell_shares * current_price

        return {
            'code': code,
            'name': self.sell_signals.get(code, {}).get('name', ''),
            'shares_total': shares,
            'shares_to_sell': sell_shares,
            'sell_ratio': sell_ratio,
            'avg_cost': avg_cost,
            'current_price': current_price,
            'sell_amount': sell_amount,
            'down_prob': down_prob,
            'sell_reason': sell_reason,
            'expected_profit': sell_shares * (current_price - avg_cost),
        }

    def generate_sell_plan(self) -> Dict:
        """生成卖出计划"""
        positions_data = self.load_positions()
        positions = positions_data.get('positions', {})
        prices = positions_data.get('prices', {})
        total_value = positions_data.get('total_value', 0)
        cash = positions_data.get('cash', 0)

        sell_plan = {
            'execute_date': self.execute_date,
            'execute_time': self.execute_time,
            'model_info': {
                'model': 'GradientBoosting',
                'accuracy': 0.5601,
                'f1_score': 0.6280,
                'threshold': 0.55,
            },
            'positions_before': {
                'total_value': total_value,
                'cash': cash,
                'equity_value': total_value - cash,
            },
            'sell_orders': [],
            'sell_summary': {
                'total_sell_amount': 0,
                'expected_cash_after': cash,
                'codes_to_sell': [],
                'codes_not_in_position': [],
            },
        }

        # 遍历卖出信号标的
        for code, signal in self.sell_signals.items():
            if code not in positions:
                logger.warning(f"[SKIP] {code} ({signal['name']}) 不在持仓中")
                sell_plan['sell_summary']['codes_not_in_position'].append({
                    'code': code,
                    'name': signal['name'],
                    'down_prob': signal['down_prob'],
                })
                continue

            # 更新当前价格
            position = positions[code]
            position['current_price'] = prices.get(code, position.get('avg_cost', 0))

            # 计算卖出数量
            sell_order = self.calculate_sell_amount(code, position)
            if sell_order:
                sell_plan['sell_orders'].append(sell_order)
                sell_plan['sell_summary']['total_sell_amount'] += sell_order['sell_amount']
                sell_plan['sell_summary']['codes_to_sell'].append(code)

        # 更新预期现金
        sell_plan['sell_summary']['expected_cash_after'] = cash + sell_plan['sell_summary']['total_sell_amount']

        logger.info(f"[PLAN] 卖出计划生成完成")
        logger.info(f"[PLAN]   卖出标的数: {len(sell_plan['sell_orders'])}")
        logger.info(f"[PLAN]   预计卖出金额: ¥{sell_plan['sell_summary']['total_sell_amount']:,.2f}")
        logger.info(f"[PLAN]   预计现金余额: ¥{sell_plan['sell_summary']['expected_cash_after']:,.2f}")

        return sell_plan

    def generate_execution_report(self, sell_plan: Dict) -> str:
        """生成执行报告（Markdown格式）"""
        report_date = datetime.now().strftime('%Y-%m-%d')
        report_lines = []

        report_lines.append(f"# ML信号驱动卖出执行计划")
        report_lines.append(f"")
        report_lines.append(f"> **执行日期**: {self.execute_date} 开盘 ({self.execute_time})")
        report_lines.append(f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"")
        report_lines.append(f"---")
        report_lines.append(f"")

        # 模型信息
        report_lines.append(f"## 🤖 ML模型信息")
        report_lines.append(f"")
        report_lines.append(f"| 项目 | 值 |")
        report_lines.append(f"|------|-----|")
        report_lines.append(f"| 模型 | **{sell_plan['model_info']['model']}** |")
        report_lines.append(f"| 准确率 | {sell_plan['model_info']['accuracy']:.2%} |")
        report_lines.append(f"| F1分数 | {sell_plan['model_info']['f1_score']:.4f} |")
        report_lines.append(f"| 信号阈值 | {sell_plan['model_info']['threshold']:.2%} |")
        report_lines.append(f"")
        report_lines.append(f"---")
        report_lines.append(f"")

        # 卖出信号
        report_lines.append(f"## 📉 卖出信号标的")
        report_lines.append(f"")
        report_lines.append(f"| 代码 | 名称 | 下跌概率 | 建议操作 |")
        report_lines.append(f"|------|------|----------|----------|")
        for code, signal in self.sell_signals.items():
            action_icon = '🔴 **卖出**' if signal['action'] == 'SELL' else '🟡 监控'
            report_lines.append(f"| {code} | {signal['name']} | {signal['down_prob']:.2%} | {action_icon} |")
        report_lines.append(f"")
        report_lines.append(f"---")
        report_lines.append(f"")

        # 卖出计划
        report_lines.append(f"## 📋 卖出执行计划")
        report_lines.append(f"")
        if sell_plan['sell_orders']:
            report_lines.append(f"| 代码 | 名称 | 持仓股数 | 卖出股数 | 卖出比例 | 当前价格 | 卖出金额 | 预期盈亏 |")
            report_lines.append(f"|------|------|----------|----------|----------|----------|----------|----------|")
            for order in sell_plan['sell_orders']:
                profit_icon = '🟢' if order['expected_profit'] >= 0 else '🔴'
                report_lines.append(
                    f"| {order['code']} | {order['name']} | {order['shares_total']} | "
                    f"**{order['shares_to_sell']}** | {order['sell_ratio']:.0%} | "
                    f"¥{order['current_price']:.3f} | ¥{order['sell_amount']:,.2f} | "
                    f"{profit_icon} ¥{order['expected_profit']:,.2f} |"
                )
            report_lines.append(f"")
            report_lines.append(f"| **合计** | - | - | - | - | - | **¥{sell_plan['sell_summary']['total_sell_amount']:,.2f}** | - |")
        else:
            report_lines.append(f"*暂无需要卖出的持仓*")
        report_lines.append(f"")
        report_lines.append(f"---")
        report_lines.append(f"")

        # 不在持仓的标的
        if sell_plan['sell_summary']['codes_not_in_position']:
            report_lines.append(f"## 🟡 不在持仓的标的")
            report_lines.append(f"")
            report_lines.append(f"以下标的有卖出信号但不在当前持仓中，无需操作：")
            report_lines.append(f"")
            for item in sell_plan['sell_summary']['codes_not_in_position']:
                report_lines.append(f"- {item['code']} ({item['name']}) - 下跌概率 {item['down_prob']:.2%}")
            report_lines.append(f"")
            report_lines.append(f"---")
            report_lines.append(f"")

        # 资产变动
        report_lines.append(f"## 💰 资产变动预估")
        report_lines.append(f"")
        report_lines.append(f"| 项目 | 当前值 | 执行后预估 | 变动 |")
        report_lines.append(f"|------|--------|------------|------|")
        report_lines.append(f"| 总资产 | ¥{sell_plan['positions_before']['total_value']:,.2f} | ¥{sell_plan['positions_before']['total_value']:,.2f} | - |")
        report_lines.append(f"| 现金 | ¥{sell_plan['positions_before']['cash']:,.2f} | ¥{sell_plan['sell_summary']['expected_cash_after']:,.2f} | +¥{sell_plan['sell_summary']['total_sell_amount']:,.2f} |")
        report_lines.append(f"| 股票市值 | ¥{sell_plan['positions_before']['equity_value']:,.2f} | ¥{sell_plan['positions_before']['equity_value'] - sell_plan['sell_summary']['total_sell_amount']:,.2f} | -¥{sell_plan['sell_summary']['total_sell_amount']:,.2f} |")
        report_lines.append(f"| 现金比例 | {sell_plan['positions_before']['cash']/sell_plan['positions_before']['total_value']:.2%} | {sell_plan['sell_summary']['expected_cash_after']/sell_plan['positions_before']['total_value']:.2%} | +{sell_plan['sell_summary']['total_sell_amount']/sell_plan['positions_before']['total_value']:.2%} |")
        report_lines.append(f"")
        report_lines.append(f"---")
        report_lines.append(f"")

        # 执行策略说明
        report_lines.append(f"## 📝 卖出策略说明")
        report_lines.append(f"")
        report_lines.append(f"**卖出比例决策规则**：")
        report_lines.append(f"")
        report_lines.append(f"| 下跌概率 | 卖出比例 | 策略说明 |")
        report_lines.append(f"|----------|----------|----------|")
        report_lines.append(f"| ≥ 65% | **100%** | 高置信度下跌信号，全部清仓 |")
        report_lines.append(f"| 60-65% | **50%** | 中置信度下跌信号，减半持仓 |")
        report_lines.append(f"| 55-60% | **30%** | 低置信度下跌信号，适度减仓 |")
        report_lines.append(f"")
        report_lines.append(f"**执行时机**：")
        report_lines.append(f"- 🕘 **开盘集合竞价** (09:15-09:25): 可提前挂单")
        report_lines.append(f"- 🕙 **连续竞价开盘** (09:30): 正式执行卖出")
        report_lines.append(f"- 建议：在开盘后5-10分钟内完成卖出，避免追涨杀跌")
        report_lines.append(f"")
        report_lines.append(f"---")
        report_lines.append(f"")

        # 风险提示
        report_lines.append(f"## ⚠️ 风险提示")
        report_lines.append(f"")
        report_lines.append(f"1. ML模型准确率 **56.01%**，存在误判风险")
        report_lines.append(f"2. 卖出后可能错过反弹机会")
        report_lines.append(f"3. 建议分批卖出，避免一次性清仓")
        report_lines.append(f"4. 执行前请确认当前持仓和市场状态")
        report_lines.append(f"5. **免责声明**：本计划仅供参考，不构成投资建议")
        report_lines.append(f"")
        report_lines.append(f"---")
        report_lines.append(f"")

        # 页脚
        report_lines.append(f"**报告生成**: 量化策略系统 v5.7 - ML信号驱动模块")
        report_lines.append(f"**报告归档**: `{self.output_dir / self.execute_date / 'ML卖出执行计划.md'}`")

        return '\n'.join(report_lines)

    def save_report(self, report: str) -> Path:
        """保存报告"""
        report_dir = self.output_dir / self.execute_date
        report_dir.mkdir(parents=True, exist_ok=True)

        report_file = report_dir / 'ML卖出执行计划.md'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"[REPORT] 报告已保存: {report_file}")

        return report_file

    def save_sell_plan_json(self, sell_plan: Dict) -> Path:
        """保存卖出计划JSON"""
        plan_dir = self.output_dir / self.execute_date
        plan_dir.mkdir(parents=True, exist_ok=True)

        plan_file = plan_dir / 'ml_sell_plan.json'
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(sell_plan, f, ensure_ascii=False, indent=2)

        logger.info(f"[PLAN] 计划已保存: {plan_file}")

        return plan_file

    def execute_sell(self, sell_plan: Dict) -> Dict:
        """实际执行卖出操作（更新持仓文件）"""
        logger.info("=" * 70)
        logger.info("ML卖出执行 - 更新持仓")
        logger.info("=" * 70)

        # 加载当前持仓
        with open(self.positions_file, 'r', encoding='utf-8') as f:
            positions_data = json.load(f)

        positions = positions_data.get('positions', {})
        prices = positions_data.get('prices', {})
        cash = positions_data.get('cash', 0)

        executed_orders = []
        total_sell_amount = 0

        # 执行卖出订单
        for order in sell_plan['sell_orders']:
            code = order['code']
            shares_to_sell = order['shares_to_sell']
            current_price = order['current_price']

            if code not in positions:
                logger.warning(f"[SKIP] {code} 不在持仓中")
                continue

            # 更新持仓股数
            old_shares = positions[code]['shares']
            new_shares = old_shares - shares_to_sell

            if new_shares <= 0:
                # 全部卖出，删除持仓记录
                del positions[code]
                logger.info(f"[SELL] {code} ({order['name']}): 全部卖出 {old_shares} 股 @ ¥{current_price:.3f}")
            else:
                # 部分卖出，更新持仓
                positions[code]['shares'] = new_shares
                logger.info(f"[SELL] {code} ({order['name']}): 卖出 {shares_to_sell} 股 → 剩余 {new_shares} 股 @ ¥{current_price:.3f}")

            # 计算卖出金额
            sell_amount = shares_to_sell * current_price
            total_sell_amount += sell_amount

            executed_orders.append({
                'code': code,
                'name': order['name'],
                'shares_sold': shares_to_sell,
                'price': current_price,
                'amount': sell_amount,
                'timestamp': datetime.now().isoformat(),
            })

        # 更新现金
        positions_data['cash'] = cash + total_sell_amount
        positions_data['last_update'] = datetime.now().isoformat()
        positions_data['positions'] = positions

        # 计算新总资产
        new_total = positions_data['cash']
        for code, pos in positions.items():
            if code != 'CASH':
                price = prices.get(code, pos.get('avg_cost', 0))
                new_total += pos['shares'] * price
        positions_data['total_value'] = new_total

        # 保存更新后的持仓
        with open(self.positions_file, 'w', encoding='utf-8') as f:
            json.dump(positions_data, f, ensure_ascii=False, indent=2)

        logger.info(f"[CASH] 现金更新: ¥{cash:,.2f} → ¥{positions_data['cash']:,.2f}")
        logger.info(f"[TOTAL] 总资产更新: ¥{new_total:,.2f}")

        return {
            'executed_orders': executed_orders,
            'total_sell_amount': total_sell_amount,
            'cash_after': positions_data['cash'],
            'total_after': new_total,
        }

    def execute(self, do_execute: bool = False) -> Dict:
        """执行卖出计划生成（可选择是否实际执行）"""
        logger.info("=" * 70)
        logger.info("ML信号驱动卖出执行计划生成")
        logger.info("=" * 70)
        logger.info(f"执行日期: {self.execute_date}")
        logger.info(f"执行时间: {self.execute_time}")
        logger.info("")

        # 生成卖出计划
        sell_plan = self.generate_sell_plan()

        # 生成报告
        report = self.generate_execution_report(sell_plan)

        # 保存文件
        report_file = self.save_report(report)
        plan_file = self.save_sell_plan_json(sell_plan)

        # 是否实际执行卖出
        execute_result = None
        if do_execute:
            logger.info("")
            logger.info("=" * 70)
            logger.info("开始执行卖出操作...")
            logger.info("=" * 70)
            execute_result = self.execute_sell(sell_plan)

        logger.info("")
        logger.info("=" * 70)
        logger.info("卖出执行完成")
        logger.info("=" * 70)
        logger.info(f"报告文件: {report_file}")
        logger.info(f"计划文件: {plan_file}")
        logger.info(f"预计卖出金额: {sell_plan['sell_summary']['total_sell_amount']:,.2f}")

        if execute_result:
            logger.info(f"实际卖出金额: {execute_result['total_sell_amount']:,.2f}")
            logger.info(f"现金余额: {execute_result['cash_after']:,.2f}")

        return {
            'sell_plan': sell_plan,
            'report_file': str(report_file),
            'plan_file': str(plan_file),
            'execute_result': execute_result,
        }


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='ML信号驱动卖出执行脚本')
    parser.add_argument('--execute', action='store_true', help='实际执行卖出操作（更新持仓文件）')
    args = parser.parse_args()

    executor = MLSellExecutor()
    result = executor.execute(do_execute=args.execute)

    # 打印摘要
    print("\n" + "=" * 70)
    print("卖出执行计划摘要")
    print("=" * 70)

    sell_plan = result['sell_plan']

    if sell_plan['sell_orders']:
        print("\n卖出订单:")
        for order in sell_plan['sell_orders']:
            print(f"  - {order['code']} ({order['name']}): 卖出 {order['shares_to_sell']} 股 @ {order['current_price']:.3f}")
            print(f"    卖出金额: {order['sell_amount']:,.2f} | 原因: {order['sell_reason']}")

        print(f"\n合计卖出金额: {sell_plan['sell_summary']['total_sell_amount']:,.2f}")
        print(f"预计现金余额: {sell_plan['sell_summary']['expected_cash_after']:,.2f}")

    if sell_plan['sell_summary']['codes_not_in_position']:
        print("\n不在持仓的标的:")
        for item in sell_plan['sell_summary']['codes_not_in_position']:
            print(f"  - {item['code']} ({item['name']}): 下跌概率 {item['down_prob']:.2%}")

    if result['execute_result']:
        print("\n实际执行结果:")
        print(f"  - 卖出标的数: {len(result['execute_result']['executed_orders'])}")
        print(f"  - 实际卖出金额: {result['execute_result']['total_sell_amount']:,.2f}")
        print(f"  - 现金余额: {result['execute_result']['cash_after']:,.2f}")

    print(f"\n详细报告: {result['report_file']}")
    print("=" * 70)


if __name__ == '__main__':
    main()