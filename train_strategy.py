# -*- coding: utf-8 -*-
"""
策略训练模块 - 使用历史行情数据训练量化策略
数据来源: 12个标的2024年12月1日至2026年5月25日完整日度行情数据
"""

import sys
import os
import io
import pandas as pd
import numpy as np
import yaml
from datetime import datetime
from collections import OrderedDict

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

class StrategyTrainer:
    def __init__(self, config_path='config/portfolio.yaml'):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.assets = self.config['assets']
        self.codes = [a['code'] for a in self.assets]
        self.names = {a['code']: a['name'] for a in self.assets}
        self.target_weights = {a['code']: a['target_weight'] for a in self.assets}
        
    def load_data(self, excel_path):
        print(f"[INFO] 加载历史行情数据: {excel_path}")
        try:
            self.df = pd.read_excel(excel_path)
            print(f"[OK] 数据加载成功, 共 {len(self.df)} 条记录")
            print(f"[DATE] 时间范围: {self.df['日期'].min()} 至 {self.df['日期'].max()}")
            return True
        except Exception as e:
            print(f"[ERROR] 数据加载失败: {e}")
            return False
    
    def prepare_data(self):
        df = self.df.copy()
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')
        df['code'] = df['Wind代码'].str.split('.').str[0]
        self.df = df
        
        self.daily_returns = {}
        for code in self.codes:
            prices = self.df[self.df['code'] == code][['日期', '收盘价']].set_index('日期')
            prices.columns = ['close']
            prices['return'] = prices['close'].pct_change().fillna(0)
            self.daily_returns[code] = prices
        
        self.dates = sorted(set(self.df['日期']))
        print(f"[DATA] 准备完成, 共 {len(self.dates)} 个交易日")
    
    def backtest(self, initial_capital=1000000, rebalance_threshold=5, rebalance_interval=5):
        print("\n[START] 开始回测...")
        
        portfolio_value = initial_capital
        cash = initial_capital
        positions = {code: 0 for code in self.codes}
        portfolio_values = []
        dates = []
        rebalance_dates = []
        
        last_rebalance_day = 0
        total_trades = 0
        
        for day_idx, date in enumerate(self.dates):
            prices = {}
            for code in self.codes:
                if date in self.daily_returns[code].index:
                    prices[code] = float(self.daily_returns[code].loc[date, 'close'])
                else:
                    prices[code] = None
            
            valid_codes = [c for c in self.codes if prices[c] is not None]
            
            if not valid_codes:
                continue
            
            current_value = cash
            for code in valid_codes:
                current_value += positions[code] * prices[code]
            
            portfolio_values.append(current_value)
            dates.append(date)
            
            should_rebalance = (day_idx - last_rebalance_day) >= rebalance_interval
            
            if should_rebalance:
                target_values = {}
                for code in valid_codes:
                    target_values[code] = current_value * self.target_weights[code]
                
                for code in valid_codes:
                    target_shares = int(target_values[code] / prices[code] / 100) * 100
                    current_shares = positions[code]
                    diff = target_shares - current_shares
                    
                    if diff != 0:
                        cost = abs(diff) * prices[code] * 1.0005
                        if diff > 0:
                            cash -= cost
                            positions[code] += diff
                            total_trades += 1
                        else:
                            cash += abs(diff) * prices[code] * 0.9995
                            positions[code] += diff
                            total_trades += 1
                
                last_rebalance_day = day_idx
                rebalance_dates.append(date)
        
        portfolio_df = pd.DataFrame({'date': dates, 'portfolio_value': portfolio_values})
        portfolio_df['return'] = portfolio_df['portfolio_value'].pct_change().fillna(0)
        portfolio_df['cum_return'] = (1 + portfolio_df['return']).cumprod()
        
        self.portfolio_df = portfolio_df
        self.total_trades = total_trades
        self.rebalance_count = len(rebalance_dates)
        
        return portfolio_df
    
    def calculate_metrics(self):
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
            'total_trades': self.total_trades,
            'rebalance_count': self.rebalance_count,
            'days': days
        }
        
        return self.metrics
    
    def generate_report(self):
        print("\n" + "="*70)
        print("策略训练报告")
        print("="*70)
        
        m = self.metrics
        
        print(f"\n[PERFORMANCE] 收益表现")
        print(f"  总收益率: {m['total_return']*100:.2f}%")
        print(f"  年化收益率: {m['annualized_return']*100:.2f}%")
        print(f"  波动率: {m['volatility']*100:.2f}%")
        print(f"  夏普比率: {m['sharpe_ratio']:.2f}")
        
        print(f"\n[RISK] 风险指标")
        print(f"  最大回撤: {m['max_drawdown']*100:.2f}%")
        
        print(f"\n[TRADE_STATS] 交易统计")
        print(f"  交易天数: {m['days']} 天")
        print(f"  总交易次数: {m['total_trades']} 次")
        print(f"  再平衡次数: {m['rebalance_count']} 次")
        print(f"  胜率: {m['win_rate']*100:.2f}%")
        print(f"  盈利因子: {m['profit_factor']:.2f}")
        
        print(f"\n[GOALS] 目标达成情况")
        target_annual = 0.08
        target_drawdown = 0.10
        
        annual_status = "PASS" if m['annualized_return'] >= target_annual else "FAIL"
        drawdown_status = "PASS" if m['max_drawdown'] <= target_drawdown else "FAIL"
        
        print(f"  年化收益目标 ({target_annual*100}%): [{annual_status}] {m['annualized_return']*100:.2f}%")
        print(f"  最大回撤目标 ({target_drawdown*100}%): [{drawdown_status}] {m['max_drawdown']*100:.2f}%")
        
        if m['annualized_return'] >= target_annual and m['max_drawdown'] <= target_drawdown:
            print("\n[SUCCESS] 策略达标! 可以投入实盘使用")
        else:
            print("\n[WARNING] 策略未达标, 建议调整参数")
        
        print(f"\n[EQUITY_CURVE] 净值曲线统计")
        print(f"  初始净值: ¥{self.portfolio_df['portfolio_value'].iloc[0]:,.0f}")
        print(f"  最终净值: ¥{self.portfolio_df['portfolio_value'].iloc[-1]:,.0f}")
        print(f"  最高净值: ¥{self.portfolio_df['portfolio_value'].max():,.0f}")
        print(f"  最低净值: ¥{self.portfolio_df['portfolio_value'].min():,.0f}")
        
        self.portfolio_df.to_csv('data/cache/backtest_results.csv', index=False, encoding='utf-8')
        print(f"\n[FILE] 回测结果已保存至: data/cache/backtest_results.csv")
        
        return self.metrics
    
    def run(self, excel_path):
        if not self.load_data(excel_path):
            return
        
        self.prepare_data()
        self.backtest()
        self.calculate_metrics()
        return self.generate_report()
    
    def load_parquet_data(self, data_dir='data/cache'):
        """从parquet文件加载数据"""
        print(f"[INFO] 从 {data_dir} 加载parquet数据...")
        
        all_data = []
        self.parquet_files = []
        
        for asset in self.assets:
            code = asset['code']
            filepath = os.path.join(data_dir, f'kline_{code}_daily.parquet')
            
            if os.path.exists(filepath):
                try:
                    df = pd.read_parquet(filepath)
                    
                    # 标准化列名
                    column_mapping = {}
                    if '_DATE' in df.columns:
                        column_mapping['_DATE'] = '日期'
                    if 'date' in df.columns:
                        column_mapping['date'] = '日期'
                    if 'close' in df.columns:
                        column_mapping['close'] = '收盘价'
                    
                    if column_mapping:
                        df.rename(columns=column_mapping, inplace=True)
                    
                    # 确保必要列存在
                    if '日期' in df.columns and '收盘价' in df.columns:
                        df['Wind代码'] = code
                        all_data.append(df[['日期', '收盘价', 'Wind代码']])
                        self.parquet_files.append(filepath)
                        print(f"  [OK] {asset['name']} ({code}): {len(df)}条记录")
                    else:
                        print(f"  [WARN] {asset['name']} ({code}): 缺少必要列")
                        
                except Exception as e:
                    print(f"  [WARN] {asset['name']} ({code}): 加载失败 - {e}")
            else:
                print(f"  [SKIP] {asset['name']} ({code}): 文件不存在")
        
        if all_data:
            self.df = pd.concat(all_data, ignore_index=True)
            print(f"\n[DATA] 总共加载 {len(self.df)} 条记录")
            return True
        else:
            print("\n[ERROR] 没有成功加载任何数据")
            return False
    
    def prepare_data_from_parquet(self):
        """从parquet数据准备训练数据"""
        df = self.df.copy()
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期')
        df['code'] = df['Wind代码'].str.split('.').str[0]
        self.df = df
        
        self.daily_returns = {}
        for code in self.codes:
            prices = self.df[self.df['code'] == code][['日期', '收盘价']].set_index('日期')
            prices.columns = ['close']
            prices['return'] = prices['close'].pct_change().fillna(0)
            self.daily_returns[code] = prices
        
        self.dates = sorted(set(self.df['日期']))
        print(f"[DATA] 准备完成, 共 {len(self.dates)} 个交易日")

def main():
    import sys
    
    # 使用parquet数据文件
    data_dir = 'data/cache'
    parquet_files = [f for f in os.listdir(data_dir) if f.startswith('kline_') and f.endswith('.parquet')]
    
    if parquet_files:
        print(f"\n[DATA] 找到 {len(parquet_files)} 个parquet数据文件")
        print(f"[FILES] 使用本地parquet数据进行训练")
        excel_path = None
    else:
        print("\n[ERROR] 未找到parquet数据文件")
        print(f"[PATH] 请检查目录: {data_dir}")
        return
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║         12只标的量化策略 - 历史数据训练模块              ║
║         目标: 年化收益≥8% | 最大回撤≤10%                ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    trainer = StrategyTrainer()
    
    # 使用parquet数据直接训练
    print("\n[LOAD] 从parquet文件加载数据...")
    if not trainer.load_parquet_data(data_dir):
        print("\n[ERROR] 数据加载失败,退出训练")
        return
    
    print("\n[PREPARE] 准备训练数据...")
    trainer.prepare_data_from_parquet()
    print("\n[BACKTEST] 开始回测...")
    trainer.backtest()
    print("\n[METRICS] 计算指标...")
    trainer.calculate_metrics()
    print("\n[REPORT] 生成报告...")
    trainer.generate_report()

if __name__ == '__main__':
    main()