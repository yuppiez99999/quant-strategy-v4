# -*- coding: utf-8 -*-
"""
长期预测模块 - 基于历史数据预测未来10年年化收益率和最大回撤
使用蒙特卡洛模拟方法进行概率分布预测
"""

import pandas as pd
import numpy as np
import yaml
import matplotlib.pyplot as plt

class FuturePredictor:
    def __init__(self, config_path='config/portfolio.yaml'):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.assets = self.config['assets']
        self.codes = [a['code'] for a in self.assets]
        self.target_weights = {a['code']: a['target_weight'] for a in self.assets}
    
    def load_historical_data(self, excel_path):
        print(f"📥 加载历史行情数据...")
        raw_df = pd.read_excel(excel_path)
        df = raw_df.copy()
        df['日期'] = pd.to_datetime(df['日期'])
        df['code'] = df['Wind代码'].str.split('.').str[0]
        self.df = df.sort_values('日期')
        
        self.returns_data = {}
        for code in self.codes:
            prices = self.df[self.df['code'] == code][['日期', '收盘价']].set_index('日期')
            prices.columns = ['close']
            prices['return'] = prices['close'].pct_change().fillna(0)
            self.returns_data[code] = prices
        
        self.historical_returns = pd.DataFrame()
        for code in self.codes:
            if code in self.returns_data:
                self.historical_returns[code] = self.returns_data[code]['return']
        
        self.historical_returns = self.historical_returns.dropna()
        print(f"✅ 历史数据加载完成, 共 {len(self.historical_returns)} 个交易日")
    
    def calculate_historical_covariance(self):
        self.cov_matrix = self.historical_returns.cov()
        self.mean_returns = self.historical_returns.mean()
        self.annualized_mean = self.mean_returns * 252
        self.annualized_cov = self.cov_matrix * 252
        
        print(f"\n📊 历史统计特征:")
        print(f"  日平均收益: {self.mean_returns.mean():.6f}")
        print(f"  年平均收益: {self.annualized_mean.mean():.2%}")
        print(f"  组合年收益: {(self.annualized_mean * pd.Series(self.target_weights)).sum():.2%}")
    
    def monte_carlo_simulation(self, years=10, simulations=10000, initial_capital=1000000):
        print(f"\n🚀 运行蒙特卡洛模拟: {simulations} 次模拟, {years} 年预测期")

        daily_days = years * 252
        codes_in_model = [c for c in self.codes if c in self.mean_returns.index]
        weights = np.array([self.target_weights[c] for c in codes_in_model])
        mu = self.mean_returns[codes_in_model].values
        cov = self.cov_matrix.loc[codes_in_model, codes_in_model].values

        # 向量化：一次生成 [simulations × daily_days × N] 的随机路径
        L = np.linalg.cholesky(cov)
        rng = np.random.default_rng()
        Z = rng.standard_normal((simulations, daily_days, len(weights)))
        daily_returns_3d = mu + Z @ L.T

        # 组合日收益 [simulations × daily_days]
        portfolio_daily = np.dot(daily_returns_3d, weights)  # (S, D, N) @ (N,) → (S, D)
        portfolio_value = initial_capital * np.cumprod(1 + portfolio_daily, axis=1)

        # 回撤
        peak = np.maximum.accumulate(portfolio_value, axis=1)
        drawdown = (peak - portfolio_value) / peak
        max_dd = drawdown.max(axis=1)

        final_value = portfolio_value[:, -1]
        total_return = final_value / initial_capital - 1
        annualized_return = (1 + total_return) ** (1 / years) - 1

        self.simulation_results = {
            'annualized_returns': annualized_return,
            'max_drawdowns': max_dd,
            'final_values': final_value,
        }

        print(f"✅ 蒙特卡洛模拟完成")
        return self.simulation_results
    
    def analyze_results(self):
        returns = self.simulation_results['annualized_returns']
        drawdowns = self.simulation_results['max_drawdowns']
        values = self.simulation_results['final_values']
        
        print("\n" + "="*70)
        print("📈 未来10年预测分析报告")
        print("="*70)
        
        print(f"\n🎯 年化收益率预测")
        print(f"  平均值: {np.mean(returns):.2%}")
        print(f"  中位数: {np.median(returns):.2%}")
        print(f"  最小值: {np.min(returns):.2%}")
        print(f"  最大值: {np.max(returns):.2%}")
        print(f"  5%分位数: {np.percentile(returns, 5):.2%}")
        print(f"  95%分位数: {np.percentile(returns, 95):.2%}")
        
        print(f"\n📉 最大回撤预测")
        print(f"  平均值: {np.mean(drawdowns):.2%}")
        print(f"  中位数: {np.median(drawdowns):.2%}")
        print(f"  最小值: {np.min(drawdowns):.2%}")
        print(f"  最大值: {np.max(drawdowns):.2%}")
        print(f"  95%分位数: {np.percentile(drawdowns, 95):.2%}")
        
        print(f"\n💰 最终净值预测 (初始资金 ¥{1000000:,})")
        print(f"  平均值: ¥{np.mean(values):,.0f}")
        print(f"  中位数: ¥{np.median(values):,.0f}")
        print(f"  最小值: ¥{np.min(values):,.0f}")
        print(f"  最大值: ¥{np.max(values):,.0f}")
        print(f"  5%分位数: ¥{np.percentile(values, 5):,.0f}")
        print(f"  95%分位数: ¥{np.percentile(values, 95):,.0f}")
        
        prob_meet_target = np.sum(returns >= 0.08) / len(returns)
        prob_drawdown_ok = np.sum(drawdowns <= 0.10) / len(drawdowns)
        prob_both = np.sum((returns >= 0.08) & (drawdowns <= 0.10)) / len(returns)
        
        print(f"\n📊 目标达成概率")
        print(f"  年化收益≥8%: {prob_meet_target:.1%}")
        print(f"  最大回撤≤10%: {prob_drawdown_ok:.1%}")
        print(f"  同时达成双目标: {prob_both:.1%}")
        
        self.predictions = {
            'expected_annual_return': np.mean(returns),
            'expected_max_drawdown': np.mean(drawdowns),
            'expected_final_value': np.mean(values),
            'probability_meet_target': prob_meet_target,
            'probability_drawdown_ok': prob_drawdown_ok,
            'probability_both': prob_both,
            'return_5th_percentile': np.percentile(returns, 5),
            'return_95th_percentile': np.percentile(returns, 95),
            'drawdown_95th_percentile': np.percentile(drawdowns, 95)
        }
        
        return self.predictions
    
    def run(self, excel_path, years=10):
        self.load_historical_data(excel_path)
        self.calculate_historical_covariance()
        self.monte_carlo_simulation(years=years)
        return self.analyze_results()

def main():
    excel_path = r'e:\各种PY程序\12个标的2024年12月1日至2026年5月25日完整日度行情数据.xlsx'
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║         12只标的量化策略 - 长期预测模块                  ║
║         预测未来10年年化收益率与最大回撤                  ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    predictor = FuturePredictor()
    predictions = predictor.run(excel_path, years=10)
    
    print("\n" + "="*70)
    print("🎯 核心预测结果")
    print("="*70)
    print(f"📈 预期年化收益率: {predictions['expected_annual_return']:.2%}")
    print(f"📉 预期最大回撤: {predictions['expected_max_drawdown']:.2%}")
    print(f"💰 预期最终净值: ¥{predictions['expected_final_value']:,.0f}")
    print(f"✅ 同时达成双目标概率: {predictions['probability_both']:.1%}")

if __name__ == '__main__':
    main()