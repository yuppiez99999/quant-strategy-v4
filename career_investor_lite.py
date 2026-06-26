#!/usr/bin/env python3
"""
职业投资训练模型 - 精简可运行版
================================
功能：持仓分析 + 风险评估 + 策略回测 + 收益预测
无需外部数据源，使用内置示例数据演示
"""

import json
import random
import math
from datetime import datetime, timedelta
from pathlib import Path
import yaml


class CareerInvestorLite:
    """精简版职业投资训练模型"""
    
    def __init__(self):
        self.portfolio_file = Path(__file__).parent / "config" / "portfolio.yaml"
        self.config = self._load_config()
        self.results = {}
    
    def _load_config(self):
        """加载配置"""
        with open(self.portfolio_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def analyze_portfolio(self):
        """分析持仓组合（模拟数据）"""
        print("\n" + "="*70)
        print("  持仓组合分析报告")
        print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        assets = self.config.get('assets', [])
        stock_assets = [a for a in assets if a.get('code') != 'CASH']
        cash_asset = [a for a in assets if a.get('code') == 'CASH'][0]
        
        print(f"\n持仓标的数: {len(stock_assets)} 只")
        print(f"现金比例: {cash_asset.get('target_weight', 0)*100:.1f}%")
        print(f"\n{'代码':<10} {'名称':<12} {'权重':>6} {'模拟价':>10} {'涨跌%':>8}")
        print("-"*70)
        
        total_weight = 0
        for asset in stock_assets:
            code = asset['code']
            name = asset.get('name', code)
            weight = asset.get('target_weight', 0)
            
            # 模拟价格（实际使用时替换为Wind数据）
            base_prices = {
                '510300': 3.85, '510500': 6.42, '512100': 1.58,
                '588000': 1.25, '159915': 1.98, '518880': 4.52,
                '300308': 168.5, '688041': 245.3, '300274': 89.6,
                '002371': 312.8, '601088': 35.6, '600276': 42.8,
                '601888': 58.9, '600989': 12.4, '600875': 18.7,
                '600089': 15.3, '600995': 6.82, '000425': 10.5,
                '688017': 256.4, '600406': 28.9
            }
            
            price = base_prices.get(code, random.uniform(5, 200))
            change = random.uniform(-3, 3)
            
            print(f"{code:<10} {name:<12} {weight*100:>5.1f}%  {price:>10.2f} {change:+.2f}%")
            total_weight += weight
        
        print("-"*70)
        print(f"{'股票总计':<24} {total_weight*100:>5.1f}%")
        
        self.results['portfolio'] = {
            'total_assets': len(stock_assets),
            'cash_ratio': cash_asset.get('target_weight', 0),
            'total_weight': total_weight
        }
        
        return self.results['portfolio']
    
    def assess_risk(self):
        """风险评估"""
        print("\n" + "="*70)
        print("  风险评估报告")
        print("="*70)
        
        # 模拟风险指标
        var_95 = random.uniform(1.5, 3.5)
        max_dd = random.uniform(8, 15)
        volatility = random.uniform(15, 25)
        
        # 判断风险等级
        if max_dd < 10:
            risk_level = "LOW"
            recommendation = "风险控制良好，维持当前仓位"
        elif max_dd < 15:
            risk_level = "MEDIUM"
            recommendation = "回撤接近阈值，建议关注"
        else:
            risk_level = "HIGH"
            recommendation = "[警告] 最大回撤超限，建议降低仓位10-20%"
        
        print(f"\n  风险等级:     {risk_level}")
        print(f"  组合VaR(95%): {var_95:.2f}%")
        print(f"  最大回撤:     {max_dd:.2f}%")
        print(f"  波动率:       {volatility:.2f}%")
        print(f"\n  [建议] {recommendation}")
        
        self.results['risk'] = {
            'risk_level': risk_level,
            'var_95': var_95,
            'max_drawdown': max_dd,
            'volatility': volatility
        }
        
        return self.results['risk']
    
    def run_backtest(self, start_date="2021-01-01", end_date="2026-12-31"):
        """策略回测（模拟数据）"""
        print("\n" + "="*70)
        print(f"  策略回测报告")
        print(f"  回测区间: {start_date} ~ {end_date}")
        print("="*70)
        
        # 模拟回测结果
        total_return = random.uniform(35, 65)
        annual_return = total_return / 5
        max_dd = random.uniform(10, 18)
        sharpe = random.uniform(0.8, 1.8)
        trade_count = random.randint(30, 80)
        win_rate = random.uniform(45, 65)
        
        print(f"\n  总收益率:     {total_return:.2f}%")
        print(f"  年化收益率:   {annual_return:.2f}%")
        print(f"  最大回撤:     {max_dd:.2f}%")
        print(f"  夏普比率:     {sharpe:.2f}")
        print(f"  交易次数:     {trade_count}")
        print(f"  胜率:         {win_rate:.1f}%")
        
        # 评价
        print("\n  [策略评价]:")
        if sharpe > 1.5:
            print("     [优秀] 夏普比率优秀（>1.5），风险调整后收益佳")
        elif sharpe > 1.0:
            print("     [良好] 夏普比率良好（1.0-1.5），可进一步优化")
        else:
            print("     [偏低] 夏普比率偏低（<1.0），建议调整策略参数")
        
        if max_dd > 15:
            print("     [警告] 最大回撤超过15%，建议加强风控")
        
        self.results['backtest'] = {
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_dd,
            'sharpe_ratio': sharpe,
            'trade_count': trade_count,
            'win_rate': win_rate
        }
        
        return self.results['backtest']
    
    def predict_future(self, years=5):
        """蒙特卡洛预测"""
        print("\n" + "="*70)
        print(f"  {years}年后持仓市值预测（蒙特卡洛模拟）")
        print("="*70)
        
        simulations = 10000
        initial_capital = 2000000
        
        # 模拟收益分布
        annual_returns = [random.gauss(0.08, 0.15) for _ in range(simulations)]
        final_values = [initial_capital * ((1 + r) ** years) for r in annual_returns]
        
        final_values.sort()
        
        mean_val = sum(final_values) / len(final_values)
        median_val = final_values[len(final_values) // 2]
        p5_val = final_values[int(len(final_values) * 0.05)]
        p95_val = final_values[int(len(final_values) * 0.95)]
        expected_annual = mean_val / initial_capital ** (1/years) - 1
        
        print(f"\n  初始资金:     {initial_capital:,.0f} RMB")
        print(f"  模拟次数:     {simulations:,}")
        print(f"  预测年限:     {years}年")
        print(f"\n  预期均值:     {mean_val:,.0f} RMB")
        print(f"  中位数:       {median_val:,.0f} RMB")
        print(f"  5%分位（悲观）: {p5_val:,.0f} RMB")
        print(f"  95%分位（乐观）: {p95_val:,.0f} RMB")
        print(f"  预期年化:     {expected_annual*100:.2f}%")
        
        print("\n  [解读]:")
        print(f"     - 有95%概率最终市值不低于 {p5_val:,.0f} RMB")
        print(f"     - 有5%概率最终市值超过 {p95_val:,.0f} RMB")
        print(f"     - 中位数 {median_val:,.0f} 表示一半情况更好，一半更差")
        
        self.results['prediction'] = {
            'mean': mean_val,
            'median': median_val,
            'p5': p5_val,
            'p95': p95_val,
            'expected_annual': expected_annual
        }
        
        return self.results['prediction']
    
    def generate_signals(self):
        """生成交易信号"""
        print("\n" + "="*70)
        print("  交易信号")
        print("="*70)
        
        assets = self.config.get('assets', [])
        stock_assets = [a for a in assets if a.get('code') != 'CASH']
        
        signals = []
        for asset in stock_assets[:10]:  # 只显示前10只
            code = asset['code']
            name = asset.get('name', code)
            
            # 随机生成信号
            rand = random.random()
            if rand < 0.3:
                action = "BUY"
                strength = random.uniform(0.5, 0.9)
                reason = "技术面突破 + 资金流入"
            elif rand < 0.6:
                action = "SELL"
                strength = random.uniform(0.4, 0.8)
                reason = "触及止盈位 + 情绪过热"
            else:
                action = "HOLD"
                strength = random.uniform(0.1, 0.4)
                reason = "震荡整理，等待方向"
            
            signals.append({
                'code': code,
                'name': name,
                'action': action,
                'strength': strength,
                'reason': reason
            })
        
        print(f"\n  {'代码':<10} {'名称':<12} {'信号':>6} {'强度':>6} {'原因'}")
        print("-"*70)
        for sig in signals:
            # 使用ASCII字符代替emoji
            if sig['action'] == 'BUY':
                icon = "[UP]"
            elif sig['action'] == 'SELL':
                icon = "[DN]"
            else:
                icon = "[--]"
            print(f"  {sig['code']:<10} {sig['name']:<12} {sig['action']:>6} {sig['strength']:.2f}  {icon} {sig['reason']}")
        
        buy_count = sum(1 for s in signals if s['action'] == 'BUY')
        sell_count = sum(1 for s in signals if s['action'] == 'SELL')
        hold_count = sum(1 for s in signals if s['action'] == 'HOLD')
        
        print("-"*70)
        print(f"\n  信号统计: 买入{buy_count} | 卖出{sell_count} | 持有{hold_count}")
        
        if buy_count > sell_count:
            print("  [多头] 整体偏多头，可适当加仓")
        elif sell_count > buy_count:
            print("  [空头] 整体偏空头，建议减仓防守")
        else:
            print("  [平衡] 多空平衡，维持观望")
        
        self.results['signals'] = signals
        
        return self.results['signals']
    
    def full_analysis(self):
        """完整分析"""
        print("\n" + "#"*70)
        print("#  职业投资训练模型 - 完整分析报告")
        print(f"#  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("#"*70)
        
        # 执行各模块
        self.analyze_portfolio()
        self.assess_risk()
        self.generate_signals()
        self.run_backtest()
        self.predict_future(years=5)
        
        # 综合建议
        print("\n" + "#"*70)
        print("#  综合投资建议")
        print("#"*70)
        
        risk = self.results.get('risk', {})
        backtest = self.results.get('backtest', {})
        prediction = self.results.get('prediction', {})
        
        recommendations = []
        
        # 基于风险评估
        if risk.get('max_drawdown', 0) > 15:
            recommendations.append("[警告] 回撤较大，建议降低高风险资产仓位")
        else:
            recommendations.append("[OK] 风险控制良好，维持现有配置")
        
        # 基于回测
        if backtest.get('sharpe_ratio', 0) > 1.5:
            recommendations.append("[优秀] 夏普比率优秀，策略有效性强")
        
        # 基于预测
        if prediction.get('expected_annual', 0) > 0.08:
            recommendations.append(f"[目标] 预期年化{prediction['expected_annual']*100:.1f}%，达到目标")
        
        print("\n  投资建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"    {i}. {rec}")
        
        print("\n" + "#"*70)
        print("#  报告生成完毕！")
        print("#"*70)
        
        return self.results


def main():
    print("\n" + "="*70)
    print("  职业投资训练模型系统 v1.0 (精简版)")
    print("  持仓股投资分析 + 策略训练 + 风险评估 + 收益预测")
    print("="*70)
    
    model = CareerInvestorLite()
    
    print("\n请选择分析模式:")
    print("  1. 完整分析（推荐）")
    print("  2. 仅持仓分析")
    print("  3. 仅风险评估")
    print("  4. 策略回测")
    print("  5. 收益预测")
    print("  6. 交易信号")
    print("  0. 退出")
    
    try:
        choice = input("\n请输入选项 (0-6): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\n程序已退出")
        return
    
    if choice == "1":
        model.full_analysis()
    elif choice == "2":
        model.analyze_portfolio()
    elif choice == "3":
        model.assess_risk()
    elif choice == "4":
        model.run_backtest()
    elif choice == "5":
        model.predict_future()
    elif choice == "6":
        model.generate_signals()
    elif choice == "0":
        print("\n程序已退出")
    else:
        print("\n无效选项")


if __name__ == "__main__":
    main()
