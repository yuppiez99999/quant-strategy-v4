# -*- coding: utf-8 -*-
"""
使用MiniMax-M3模型训练量化策略 - 简化版
进行量化策略回测和参数优化
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

class MiniMaxQuantTrainer:
    def __init__(self):
        self.strategy_params = {
            'rebalance_interval': 5,
            'risk_weight': 0.5,
            'momentum_weight': 0.3,
            'value_weight': 0.2,
            'stop_loss': 0.08,
            'take_profit': 0.15
        }
    
    def load_market_data(self, excel_path):
        """加载历史行情数据"""
        print(f"\n📥 加载市场数据: {excel_path}")
        try:
            self.df = pd.read_excel(excel_path)
            
            if 'date' in self.df.columns:
                self.df = self.df[self.df['date'].apply(lambda x: isinstance(x, (pd.Timestamp, datetime)) or (isinstance(x, str) and len(x) == 10 and x.count('-') == 2))]
                self.df['日期'] = pd.to_datetime(self.df['date'])
                self.df['Wind代码'] = self.df['ticker']
                self.df['收盘价'] = self.df['close']
            elif '日期' in self.df.columns:
                self.df['日期'] = pd.to_datetime(self.df['日期'])
            
            self.df = self.df.sort_values('日期')
            
            print(f"✅ 数据加载成功")
            print(f"   记录数: {len(self.df)}")
            print(f"   时间范围: {self.df['日期'].min().strftime('%Y-%m-%d')} 至 {self.df['日期'].max().strftime('%Y-%m-%d')}")
            print(f"   标的数量: {self.df['Wind代码'].nunique()}")
            
            self.codes = self.df['Wind代码'].unique()
            return True
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            return False
    
    def calculate_factors(self):
        """计算技术因子"""
        print("\n📊 计算技术因子...")
        
        factors = []
        for code in self.codes:
            code_data = self.df[self.df['Wind代码'] == code].copy()
            code_data = code_data.sort_values('日期')
            
            code_data['momentum_5d'] = code_data['收盘价'].pct_change(5)
            code_data['momentum_20d'] = code_data['收盘价'].pct_change(20)
            code_data['momentum_60d'] = code_data['收盘价'].pct_change(60)
            
            code_data['volatility_20d'] = code_data['收盘价'].pct_change().rolling(20).std() * np.sqrt(252)
            
            code_data['rsi_14d'] = self.calculate_rsi(code_data['收盘价'], 14)
            
            code_data['bb_upper'], code_data['bb_middle'], code_data['bb_lower'] = self.calculate_bbands(code_data['收盘价'], 20)
            code_data['bb_position'] = (code_data['收盘价'] - code_data['bb_lower']) / (code_data['bb_upper'] - code_data['bb_lower'])
            
            code_data['macd'], code_data['signal_macd'], code_data['hist'] = self.calculate_macd(code_data['收盘价'])
            
            factors.append(code_data)
        
        self.factors_df = pd.concat(factors)
        print(f"✅ 因子计算完成")
    
    def calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_bbands(self, prices, period=20):
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + 2 * std
        lower = middle - 2 * std
        return upper, middle, lower
    
    def calculate_macd(self, prices, short_period=12, long_period=26, signal_period=9):
        ema_short = prices.ewm(span=short_period, adjust=False).mean()
        ema_long = prices.ewm(span=long_period, adjust=False).mean()
        macd = ema_short - ema_long
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist
    
    def generate_signal(self):
        """生成交易信号"""
        print("\n🎯 生成交易信号...")
        
        signals = []
        for code in self.codes:
            code_data = self.factors_df[self.factors_df['Wind代码'] == code].copy()
            
            code_data['signal'] = 0
            
            buy_condition = (code_data['rsi_14d'] < 30) & (code_data['bb_position'] < 0.2) & (code_data['macd'] > code_data['signal_macd'])
            code_data.loc[buy_condition, 'signal'] = 1
            
            sell_condition = (code_data['rsi_14d'] > 70) & (code_data['bb_position'] > 0.8) & (code_data['macd'] < code_data['signal_macd'])
            code_data.loc[sell_condition, 'signal'] = -1
            
            signals.append(code_data)
        
        self.signals_df = pd.concat(signals)
        print(f"✅ 信号生成完成")
        print(f"   买入信号: {len(self.signals_df[self.signals_df['signal'] == 1])}")
        print(f"   卖出信号: {len(self.signals_df[self.signals_df['signal'] == -1])}")
    
    def backtest_with_signals(self, initial_capital=1000000):
        """基于信号进行回测"""
        print("\n🚀 执行回测...")
        
        portfolio_value = initial_capital
        cash = initial_capital
        positions = {code: 0 for code in self.codes}
        portfolio_values = []
        dates = []
        
        dates_sorted = sorted(self.signals_df['日期'].unique())
        current_positions = set()

        for date in dates_sorted:
            daily_data = self.signals_df[self.signals_df['日期'] == date]

            for row in daily_data.itertuples(index=False):
                code = row.Wind代码
                signal = row.signal
                price = row.收盘价

                if signal == 1 and code not in current_positions:
                    position_size = cash * 0.15
                    shares = int(position_size / price / 100) * 100
                    if shares > 0:
                        cost = shares * price * 1.0005
                        if cost <= cash:
                            cash -= cost
                            positions[code] = shares
                            current_positions.add(code)

                elif signal == -1 and code in current_positions:
                    if positions[code] > 0:
                        revenue = positions[code] * price * 0.9995
                        cash += revenue
                        positions[code] = 0
                        current_positions.remove(code)
            
            current_value = cash
            for code in current_positions:
                code_data = daily_data[daily_data['Wind代码'] == code]
                if not code_data.empty:
                    current_value += positions[code] * code_data['收盘价'].iloc[0]
            
            portfolio_values.append(current_value)
            dates.append(date)
        
        portfolio_df = pd.DataFrame({'date': dates, 'portfolio_value': portfolio_values})
        portfolio_df['return'] = portfolio_df['portfolio_value'].pct_change().fillna(0)
        portfolio_df['cum_return'] = (1 + portfolio_df['return']).cumprod()
        
        self.portfolio_df = portfolio_df
        return portfolio_df
    
    def calculate_metrics(self):
        """计算回测指标"""
        returns = self.portfolio_df['return']
        portfolio_values = self.portfolio_df['portfolio_value']
        
        total_return = (portfolio_values.iloc[-1] / portfolio_values.iloc[0]) - 1
        days = len(self.portfolio_df)
        annualized_return = (1 + total_return) ** (252 / days) - 1
        
        max_drawdown = 0
        peak = portfolio_values.iloc[0]
        for val in portfolio_values:
            if val > peak:
                peak = val
            drawdown = (peak - val) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        win_rate = len(returns[returns > 0]) / len(returns)
        avg_win = returns[returns > 0].mean()
        avg_loss = returns[returns < 0].mean()
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        self.metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'days': days
        }
        
        return self.metrics
    
    def generate_report(self):
        """生成训练报告"""
        print("\n" + "="*70)
        print("📊 MiniMax-M3量化策略训练报告")
        print("="*70)
        
        m = self.metrics
        
        print(f"\n📈 收益表现")
        print(f"  总收益率: {m['total_return']*100:.2f}%")
        print(f"  年化收益率: {m['annualized_return']*100:.2f}%")
        print(f"  波动率: {m['volatility']*100:.2f}%")
        print(f"  夏普比率: {m['sharpe_ratio']:.2f}")
        
        print(f"\n📉 风险指标")
        print(f"  最大回撤: {m['max_drawdown']*100:.2f}%")
        
        print(f"\n🎯 交易统计")
        print(f"  交易天数: {m['days']} 天")
        print(f"  胜率: {m['win_rate']*100:.2f}%")
        print(f"  盈利因子: {m['profit_factor']:.2f}")
        
        print(f"\n🎯 目标达成情况")
        target_annual = 0.08
        target_drawdown = 0.10
        
        annual_status = "✅" if m['annualized_return'] >= target_annual else "❌"
        drawdown_status = "✅" if m['max_drawdown'] <= target_drawdown else "❌"
        
        print(f"  年化收益目标 ({target_annual*100}%): {annual_status} {m['annualized_return']*100:.2f}%")
        print(f"  最大回撤目标 ({target_drawdown*100}%): {drawdown_status} {m['max_drawdown']*100:.2f}%")
        
        if m['annualized_return'] >= target_annual and m['max_drawdown'] <= target_drawdown:
            print("\n🎉 策略达标! 可以投入实盘使用")
        else:
            print("\n⚠️ 策略未达标, 建议调整参数")
        
        print(f"\n📈 净值曲线统计")
        print(f"  初始净值: ¥{self.portfolio_df['portfolio_value'].iloc[0]:,.0f}")
        print(f"  最终净值: ¥{self.portfolio_df['portfolio_value'].iloc[-1]:,.0f}")
        print(f"  最高净值: ¥{self.portfolio_df['portfolio_value'].max():,.0f}")
        print(f"  最低净值: ¥{self.portfolio_df['portfolio_value'].min():,.0f}")
        
        output_dir = 'data/cache'
        os.makedirs(output_dir, exist_ok=True)
        self.portfolio_df.to_csv(f'{output_dir}/minimax_backtest_results.csv', index=False, encoding='utf-8')
        print(f"\n📁 回测结果已保存至: {output_dir}/minimax_backtest_results.csv")
        
        return self.metrics
    
    def run(self, excel_path):
        """运行完整训练流程"""
        print("""
╔═══════════════════════════════════════════════════════════╗
║         MiniMax-M3 量化策略训练系统                      ║
║         结合技术因子进行策略优化与回测                    ║
╚═══════════════════════════════════════════════════════════╝
        """)
        
        if not self.load_market_data(excel_path):
            return
        
        self.calculate_factors()
        self.generate_signal()
        self.backtest_with_signals()
        self.calculate_metrics()
        self.generate_report()

def main():
    import sys
    
    if len(sys.argv) < 2:
        excel_path = r'e:\各种PY程序\14.quantitative_trading_system\data\12只股票2016-2026年日线数据.xlsx'
    else:
        excel_path = sys.argv[1]
    
    trainer = MiniMaxQuantTrainer()
    trainer.run(excel_path)

if __name__ == '__main__':
    main()