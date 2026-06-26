#!/usr/bin/env python3
"""
职业投资训练模型系统 v1.0
========================
功能：持仓股投资分析 + 策略训练 + 风险评估 + 收益预测

适用场景：
- 个人投资者日常持仓管理
- 量化策略回测与优化
- 风险控制与止损止盈
- 康波周期择时
- 十五五规划主题投资

需求编号: 1770371634132965
创建日期: 2026-06-17
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import json
import yaml

# 确保项目路径
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from 11_量化策略.config import Config, get_config, RiskLevel
from 11_量化策略.wind_mcp_fetcher import WindMCPFetcher
from 11_量化策略.indicators import TechnicalAnalyzer
from 11_量化策略.signals import SignalEngine
from 11_量化策略.risk_management import RiskManager
from 11_量化策略.backtest import BacktestEngine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("CareerInvestor")


class CareerInvestorModel:
    """
    职业投资训练模型
    
    整合：
    1. 持仓股实时监控
    2. 多维度技术分析
    3. 风险控制管理
    4. 策略回测优化
    5. 收益预测（蒙特卡洛）
    """
    
    def __init__(self, config: Config = None):
        self.config = config or get_config()
        self.wind = WindMCPFetcher()
        self.tech_analyzer = TechnicalAnalyzer(self.config.technical_params)
        self.signal_engine = SignalEngine(self.config)
        self.risk_manager = RiskManager(self.config.risk_control)
        self.backtest = BacktestEngine(self.config)
        
        logger.info("职业投资训练模型初始化完成")
    
    def analyze_portfolio(self, portfolio_file: str = None):
        """
        分析当前持仓组合
        
        Args:
            portfolio_file: 持仓配置文件路径（默认使用 config/portfolio.yaml）
        """
        logger.info("="*60)
        logger.info("  持仓组合分析报告")
        logger.info("="*60)
        
        # 加载持仓配置
        if portfolio_file is None:
            portfolio_file = str(Path(__file__).parent / "config" / "portfolio.yaml")
        
        with open(portfolio_file, 'r', encoding='utf-8') as f:
            portfolio = yaml.safe_load(f)
        
        assets = portfolio.get('assets', [])
        logger.info(f"\n持仓数量: {len([a for a in assets if a.get('code') != 'CASH'])} 只标的")
        logger.info(f"现金比例: {portfolio['assets'][-1].get('target_weight', 0)*100:.1f}%")
        
        # 获取实时行情
        results = []
        for asset in assets:
            if asset.get('code') == 'CASH':
                continue
            
            code = asset['code']
            name = asset.get('name', code)
            weight = asset.get('target_weight', 0)
            
            # 获取行情数据
            try:
                price_data = self.wind.get_stock_price(code)
                if price_data:
                    results.append({
                        'code': code,
                        'name': name,
                        'weight': weight,
                        'price': price_data.get('latest_price'),
                        'change_pct': price_data.get('change_pct'),
                        'volume': price_data.get('volume'),
                    })
            except Exception as e:
                logger.warning(f"{name} ({code}) 获取行情失败: {e}")
                results.append({
                    'code': code,
                    'name': name,
                    'weight': weight,
                    'status': 'error'
                })
        
        # 打印持仓概览
        print("\n" + "-"*60)
        print(f"{'代码':<10} {'名称':<12} {'权重':>6} {'最新价':>10} {'涨跌%':>8}")
        print("-"*60)
        
        total_weight = 0
        for r in results:
            if r.get('status') == 'error':
                print(f"{r['code']:<10} {r['name']:<12} {r['weight']*100:>5.1f}%  {'获取失败':>10}")
            else:
                price = r.get('price', '-')
                change = r.get('change_pct', 0)
                change_str = f"{change:+.2f}%" if isinstance(change, (int, float)) else '-'
                print(f"{r['code']:<10} {r['name']:<12} {r['weight']*100:>5.1f}%  {str(price):>10} {change_str:>8}")
                total_weight += r.get('weight', 0)
        
        print("-"*60)
        print(f"{'总计':<24} {total_weight*100:>5.1f}%")
        
        return results
    
    def run_backtest(self, start_date: str = "2021-01-01", end_date: str = "2026-12-31"):
        """
        运行策略回测
        
        Args:
            start_date: 回测开始日期
            end_date: 回测结束日期
        """
        logger.info(f"\n运行策略回测: {start_date} ~ {end_date}")
        
        # 配置回测参数
        self.config.backtest.start_date = start_date
        self.config.backtest.end_date = end_date
        self.config.backtest.rebalance_freq = "quarterly"
        
        # 执行回测
        results = self.backtest.run()
        
        # 打印回测结果
        if results:
            print("\n" + "="*60)
            print("  回测结果摘要")
            print("="*60)
            print(f"  总收益率:     {results.get('total_return', 0)*100:.2f}%")
            print(f"  年化收益率:   {results.get('annual_return', 0)*100:.2f}%")
            print(f"  最大回撤:     {results.get('max_drawdown', 0)*100:.2f}%")
            print(f"  夏普比率:     {results.get('sharpe_ratio', 0):.2f}")
            print(f"  交易次数:     {results.get('trade_count', 0)}")
            print(f"  胜率:         {results.get('win_rate', 0)*100:.1f}%")
            print("="*60)
        
        return results
    
    def assess_risk(self, portfolio_results: list = None):
        """
        风险评估
        
        Args:
            portfolio_results: 持仓分析结果
        """
        logger.info("运行风险评估...")
        
        if portfolio_results is None:
            portfolio_results = self.analyze_portfolio()
        
        risk_report = self.risk_manager.assess_portfolio_risk(portfolio_results)
        
        print("\n" + "="*60)
        print("  风险评估报告")
        print("="*60)
        print(f"  风险等级:     {risk_report.get('risk_level', 'N/A')}")
        print(f"  组合VaR(95%): {risk_report.get('portfolio_var', 0)*100:.2f}%")
        print(f"  最大回撤:     {risk_report.get('max_drawdown', 0)*100:.2f}%")
        print(f"  波动率:       {risk_report.get('volatility', 0)*100:.2f}%")
        print(f"  建议操作:     {risk_report.get('recommendation', 'N/A')}")
        print("="*60)
        
        return risk_report
    
    def predict_future(self, years: int = 5):
        """
        蒙特卡洛模拟预测未来持仓市值
        
        Args:
            years: 预测年数
        """
        logger.info(f"运行蒙特卡洛预测（{years}年）...")
        
        # 加载持仓配置
        portfolio_file = str(Path(__file__).parent / "config" / "portfolio.yaml")
        with open(portfolio_file, 'r', encoding='utf-8') as f:
            portfolio = yaml.safe_load(f)
        
        # 模拟10000次
        simulations = 10000
        initial_capital = 2000000  # 假设初始资金200万
        
        results = self.backtest.run_monte_carlo(
            portfolio=portfolio,
            initial_capital=initial_capital,
            years=years,
            simulations=simulations
        )
        
        print("\n" + "="*60)
        print(f"  {years}年后持仓市值预测（蒙特卡洛模拟）")
        print("="*60)
        print(f"  初始资金:     ¥{initial_capital:,.0f}")
        print(f"  模拟次数:     {simulations}")
        print(f"  预期均值:     ¥{results.get('mean_value', 0):,.0f}")
        print(f"  中位数:       ¥{results.get('median_value', 0):,.0f}")
        print(f"  5%分位（悲观）: ¥{results.get('p5_value', 0):,.0f}")
        print(f"  95%分位（乐观）: ¥{results.get('p95_value', 0):,.0f}")
        print(f"  预期年化:     {results.get('expected_annual_return', 0)*100:.2f}%")
        print("="*60)
        
        return results
    
    def generate_signals(self, portfolio_results: list = None):
        """
        生成交易信号
        
        Args:
            portfolio_results: 持仓分析结果
        """
        logger.info("生成交易信号...")
        
        if portfolio_results is None:
            portfolio_results = self.analyze_portfolio()
        
        signals = self.signal_engine.generate_signals(portfolio_results)
        
        print("\n" + "="*60)
        print("  交易信号")
        print("="*60)
        
        for signal in signals:
            action = signal.get('action', 'HOLD')
            strength = signal.get('strength', 0)
            reason = signal.get('reason', '')
            
            color_map = {
                'BUY': '\033[92m',  # 绿色
                'SELL': '\033[91m',  # 红色
                'HOLD': '\033[90m',  # 灰色
            }
            color = color_map.get(action, '\033[0m')
            
            print(f"\n  {color}[{action}]{'\033[0m'} {signal.get('code', 'N/A')} - {signal.get('name', '')}")
            print(f"    强度: {strength:.2f} | 原因: {reason}")
        
        print("="*60)
        
        return signals
    
    def full_analysis(self):
        """
        完整投资分析流程
        """
        logger.info("\n" + "#"*60)
        logger.info("#  职业投资训练模型 - 完整分析")
        logger.info("#"*60)
        
        # Step 1: 持仓分析
        print("\n[Step 1/5] 持仓组合分析")
        portfolio_results = self.analyze_portfolio()
        
        # Step 2: 风险评估
        print("\n[Step 2/5] 风险评估")
        risk_report = self.assess_risk(portfolio_results)
        
        # Step 3: 交易信号
        print("\n[Step 3/5] 交易信号生成")
        signals = self.generate_signals(portfolio_results)
        
        # Step 4: 策略回测
        print("\n[Step 4/5] 策略回测")
        backtest_results = self.run_backtest()
        
        # Step 5: 收益预测
        print("\n[Step 5/5] 收益预测（5年）")
        prediction = self.predict_future(years=5)
        
        # 生成综合报告
        print("\n" + "#"*60)
        print("#  综合分析结论")
        print("#"*60)
        
        recommendation = self._generate_recommendation(
            risk_report, signals, backtest_results, prediction
        )
        
        print(f"\n  投资建议: {recommendation}")
        print("#"*60)
        
        return {
            'portfolio': portfolio_results,
            'risk': risk_report,
            'signals': signals,
            'backtest': backtest_results,
            'prediction': prediction,
            'recommendation': recommendation
        }
    
    def _generate_recommendation(self, risk_report, signals, backtest_results, prediction):
        """生成综合投资建议"""
        
        risk_level = risk_report.get('risk_level', 'MEDIUM')
        max_drawdown = risk_report.get('max_drawdown', 0)
        sharpe = backtest_results.get('sharpe_ratio', 0) if backtest_results else 0
        expected_return = prediction.get('expected_annual_return', 0) if prediction else 0
        
        recommendations = []
        
        # 风险评估
        if max_drawdown > 0.15:
            recommendations.append("⚠️ 最大回撤超过15%，建议降低仓位")
        elif max_drawdown < 0.08:
            recommendations.append("✅ 回撤控制在8%以内，风险良好")
        
        # 夏普比率
        if sharpe > 1.5:
            recommendations.append("📈 夏普比率>1.5，风险调整后收益优秀")
        elif sharpe < 0.5:
            recommendations.append("📉 夏普比率<0.5，建议优化策略")
        
        # 预期收益
        if expected_return > 0.08:
            recommendations.append(f"🎯 预期年化{expected_return*100:.1f}%，达到目标")
        
        # 交易信号统计
        buy_signals = sum(1 for s in signals if s.get('action') == 'BUY')
        sell_signals = sum(1 for s in signals if s.get('action') == 'SELL')
        
        if buy_signals > sell_signals:
            recommendations.append(f"📊 买入信号{buy_signals}个 > 卖出{sell_signals}个，偏多头")
        elif sell_signals > buy_signals:
            recommendations.append(f"📊 卖出信号{sell_signals}个 > 买入{buy_signals}个，偏空头")
        
        if not recommendations:
            recommendations.append("📋 建议保持观望，等待明确信号")
        
        return "; ".join(recommendations)


def main():
    parser = argparse.ArgumentParser(
        description="职业投资训练模型系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 完整分析（推荐）
  python career_investor_model.py --mode full
  
  # 仅持仓分析
  python career_investor_model.py --mode portfolio
  
  # 仅风险评估
  python career_investor_model.py --mode risk
  
  # 策略回测
  python career_investor_model.py --mode backtest
  
  # 收益预测
  python career_investor_model.py --mode predict
  
  # 生成交易信号
  python career_investor_model.py --mode signals
        """
    )
    
    parser.add_argument(
        "--mode", "-m",
        choices=["full", "portfolio", "risk", "backtest", "predict", "signals"],
        default="full",
        help="运行模式 (默认: full)"
    )
    
    parser.add_argument(
        "--portfolio", "-p",
        default=None,
        help="持仓配置文件路径"
    )
    
    parser.add_argument(
        "--years", "-y",
        type=int,
        default=5,
        help="预测年数 (默认: 5)"
    )
    
    args = parser.parse_args()
    
    # 初始化模型
    model = CareerInvestorModel()
    
    # 执行对应模式
    if args.mode == "full":
        model.full_analysis()
    
    elif args.mode == "portfolio":
        model.analyze_portfolio(args.portfolio)
    
    elif args.mode == "risk":
        portfolio = model.analyze_portfolio(args.portfolio)
        model.assess_risk(portfolio)
    
    elif args.mode == "backtest":
        model.run_backtest()
    
    elif args.mode == "predict":
        model.predict_future(args.years)
    
    elif args.mode == "signals":
        portfolio = model.analyze_portfolio(args.portfolio)
        model.generate_signals(portfolio)


if __name__ == "__main__":
    sys.exit(main())
