# -*- coding: utf-8 -*-
"""
12只标的量化策略 - 回测引擎
策略: 固定比例配置 + 回撤控制
"""

import os
import sys
import yaml
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional


def load_configs():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, 'config', 'settings.yaml'), 'r', encoding='utf-8') as f:
        settings = yaml.safe_load(f)
    with open(os.path.join(base_dir, 'config', 'portfolio.yaml'), 'r', encoding='utf-8') as f:
        portfolio = yaml.safe_load(f)
    return settings, portfolio


def load_klines_from_cache(portfolio_config: Dict, cache_dir: str = 'data/cache', years: int = 5):
    klines = {}
    print("加载历史K线...")
    for asset in portfolio_config['assets']:
        code = asset['code']
        cache_file = os.path.join(cache_dir, f'kline_{code}_daily.parquet')
        if os.path.exists(cache_file):
            df = pd.read_parquet(cache_file, columns=['close'])
            if not df.empty:
                if len(df) > years * 252:
                    df = df.tail(years * 252)
                klines[code] = df
                print(f"  {code} {asset['name']}: {len(df)}条")
        else:
            print(f"  {code} {asset['name']}: 未找到缓存")
    return klines


class PortfolioEngine:
    def __init__(self, portfolio_config: Dict, initial_capital: float):
        self.config = portfolio_config
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {asset['code']: {'shares': 0, 'avg_cost': 0} for asset in portfolio_config['assets']}
        self.equity_curve = []

    def get_total_value(self, prices: Dict[str, float]):
        total = self.cash
        for code, pos in self.positions.items():
            if pos['shares'] > 0 and code in prices:
                total += pos['shares'] * prices[code]
        return total

    def get_current_weights(self, prices: Dict[str, float]):
        total = self.get_total_value(prices)
        weights = {}
        for code in self.positions:
            if self.positions[code]['shares'] > 0 and code in prices:
                weights[code] = self.positions[code]['shares'] * prices[code] / total
            else:
                weights[code] = 0
        return weights

    def apply_trade(self, code: str, side: str, shares: int, price: float, commission_rate: float = 0.0005):
        """执行交易并计算成本（佣金+滑点）"""
        # 计算交易成本：佣金(0.05%) + 滑点(0.03%)
        cost_rate = commission_rate + 0.0003  # 总成本0.08%
        
        if side == 'buy':
            gross_cost = shares * price
            trade_cost = gross_cost * cost_rate
            total_cost = gross_cost + trade_cost
            
            if total_cost <= self.cash:
                old_cost = self.positions[code]['shares'] * self.positions[code]['avg_cost']
                new_shares = self.positions[code]['shares'] + shares
                if new_shares > 0:
                    new_avg_cost = (old_cost + gross_cost) / new_shares
                else:
                    new_avg_cost = 0
                self.positions[code]['shares'] = new_shares
                self.positions[code]['avg_cost'] = new_avg_cost
                self.cash -= total_cost
                return True, trade_cost
        elif side == 'sell':
            if self.positions[code]['shares'] >= shares:
                gross_revenue = shares * price
                trade_cost = gross_revenue * cost_rate
                net_revenue = gross_revenue - trade_cost
                
                self.positions[code]['shares'] -= shares
                self.cash += net_revenue
                return True, trade_cost
        return False, 0.0


class BacktestEngine:
    def __init__(self, settings: Dict, portfolio_config: Dict, initial_capital: float = 1_000_000):
        self.settings = settings
        self.portfolio_config = portfolio_config
        self.initial_capital = initial_capital
        self.portfolio = PortfolioEngine(portfolio_config, initial_capital)
        self.trades = []
        self.equity_curve = []
        self.peak_value = initial_capital
        self.current_drawdown = 0.0

    def _get_common_dates(self, klines: Dict[str, pd.DataFrame]):
        date_counts = {}
        for df in klines.values():
            if df is not None and not df.empty:
                for d in df.index:
                    date_counts[d] = date_counts.get(d, 0) + 1

        min_assets = max(1, int(len(klines) * 0.5))
        valid_dates = [d for d, cnt in date_counts.items() if cnt >= min_assets]
        valid_dates.sort()
        return pd.DatetimeIndex(valid_dates)

    @staticmethod
    def _prebuild_price_matrix(klines, codes):
        """预建价格矩阵: columns=代码, rows=日期 → O(1) per-date lookup"""
        aligned = {}
        for code in codes:
            if code in klines and klines[code] is not None and not klines[code].empty:
                aligned[code] = klines[code]['close']
        if not aligned:
            return None, None, None
        matrix = pd.DataFrame(aligned).sort_index()
        matrix = matrix.ffill()
        return matrix, matrix.index, list(aligned.keys())

    def _get_day_prices(self, price_matrix, codes, date):
        """O(1) single-row lookup from prebuilt matrix"""
        if price_matrix is None:
            return {}
        if date in price_matrix.index:
            row = price_matrix.loc[date]
        else:
            prev_mask = price_matrix.index <= date
            if not prev_mask.any():
                return {}
            row = price_matrix.loc[price_matrix.index[prev_mask][-1]]
        prices = {}
        for c in codes:
            val = row.get(c)
            if val is not None and not (isinstance(val, float) and pd.isna(val)):
                prices[c] = float(val)
        return prices

    def _check_drawdown_control(self, total_value: float):
        """基于回撤程度动态调整头寸规模（精细化控制）"""
        if total_value > self.peak_value:
            self.peak_value = total_value
            self.current_drawdown = 0.0
            return 1.0

        drawdown = (self.peak_value - total_value) / self.peak_value
        self.current_drawdown = drawdown

        # 精细化的回撤控制阈值
        if drawdown >= 0.10:
            return 0.40  # 严重回撤：持仓缩减60%
        elif drawdown >= 0.08:
            return 0.55
        elif drawdown >= 0.06:
            return 0.70
        elif drawdown >= 0.04:
            return 0.85
        elif drawdown >= 0.02:
            return 0.93
        else:
            return 1.0

    def _get_fixed_weights(self):
        """返回基础目标权重"""
        weights = {}
        for asset in self.portfolio_config['assets']:
            weights[asset['code']] = asset['target_weight']
        return weights
    
    def _calculate_volatility(self, klines: Dict[str, pd.DataFrame], code: str, lookback: int = 20):
        """计算资产最近N个交易日的波动率"""
        if code not in klines or klines[code].empty:
            return 1.0
        
        df = klines[code]
        if len(df) < lookback:
            lookback = len(df)
        
        recent_prices = df['close'].tail(lookback).values
        returns = np.diff(recent_prices) / recent_prices[:-1]
        volatility = float(np.std(returns))
        return max(0.001, volatility)  # 避免除零
    
    def _get_dynamic_weights(self, klines: Dict[str, pd.DataFrame], lookback: int = 20):
        """基于波动率计算动态权重 - 低波动率资产获得更高权重"""
        base_weights = self._get_fixed_weights()
        volatilities = {}
        
        # 计算每个资产的波动率
        for code in base_weights:
            if base_weights[code] > 0 and code in klines and not klines[code].empty:
                vol = self._calculate_volatility(klines, code, lookback)
                volatilities[code] = vol
        
        # 反向波动率加权：低波动率资产权重更高
        if not volatilities:
            return base_weights
        
        # 波动率倒数加权
        inv_vol_weights = {code: 1.0 / (vol + 0.0001) for code, vol in volatilities.items()}
        inv_vol_sum = sum(inv_vol_weights.values())
        
        # 混合基础权重和波动率权重：60%基础权重 + 40%波动率加权
        dynamic_weights = {}
        total_w = 0
        
        for code in base_weights:
            if base_weights[code] > 0:
                if code in volatilities:
                    base_w = base_weights[code]
                    vol_w = inv_vol_weights[code] / inv_vol_sum * 0.4
                    # 权重混合
                    dynamic_weights[code] = base_w * 0.6 + vol_w
                else:
                    # 无数据的资产权重减半
                    dynamic_weights[code] = base_weights[code] * 0.3
            else:
                dynamic_weights[code] = 0
            total_w += dynamic_weights[code]
        
        # 归一化权重
        if total_w > 0:
            dynamic_weights = {code: w / total_w for code, w in dynamic_weights.items()}
        
        return dynamic_weights

    def _execute_rebalance(self, target_weights: Dict, prices: Dict, date, position_scale: float = 1.0):
        """自适应再平衡：偏差驱动 + 更高的再平衡阈值减少交易成本"""
        current_weights = self.portfolio.get_current_weights(prices)
        total_value = self.portfolio.get_total_value(prices)

        for code, target_w in target_weights.items():
            if target_w <= 0:
                continue
            if code not in prices:
                continue

            adjusted_target = target_w * position_scale
            current_w = current_weights.get(code, 0)
            diff = adjusted_target - current_w

            # 标准再平衡阈值：2.5% 的权重偏差才触发
            if abs(diff) > 0.025:
                price = prices[code]
                amount = abs(diff) * total_value
                shares = int(amount / price / 100) * 100

                if shares > 0:
                    side = 'buy' if diff > 0 else 'sell'
                    success, trade_cost = self.portfolio.apply_trade(code, side, shares, price)
                    if success:
                        self.trades.append({
                            'date': str(date),
                            'code': code,
                            'side': side,
                            'shares': shares,
                            'price': price,
                            'amount': shares * price,
                            'trade_cost': trade_cost,
                            'weight_drift': abs(diff)
                        })

    def run(self, klines: Dict[str, pd.DataFrame]):
        """核心回测循环：动态权重 + 自适应再平衡 + 交易成本建模"""
        dates = self._get_common_dates(klines)
        if len(dates) < 20:
            return {'error': '数据不足'}

        # 预建价格矩阵 — O(1) per date instead of O(codes) per date
        codes = [a['code'] for a in self.portfolio_config.get('assets', []) if a.get('code') and a['code'] != 'CASH']
        price_matrix, all_dates, active_codes = self._prebuild_price_matrix(klines, codes)

        # 对齐日期
        if price_matrix is not None:
            dates = all_dates[all_dates.isin([d for d in all_dates if d in set(dates)])]
            if len(dates) < 20:
                return {'error': '数据不足'}
            dates = dates if len(dates) <= self.settings.get('backtest', {}).get('max_years', 5) * 280 else dates[-self.settings.get('backtest', {}).get('max_years', 5) * 280:]

        last_rebalance = None
        rebalance_frequency = 15  # 最小再平衡间隔（天数）

        for i, date in enumerate(dates):
            prices = self._get_day_prices(price_matrix, active_codes, date)
            total_value = self.portfolio.get_total_value(prices)

            position_scale = self._check_drawdown_control(total_value)

            # 自适应再平衡触发：时间间隔 OR 权重偏差阈值
            should_rebalance = False
            if last_rebalance is None:
                should_rebalance = True
            elif (date - last_rebalance).days >= rebalance_frequency:
                should_rebalance = True
            else:
                # 检查权重偏差是否超过5%（严格触发）
                current_weights = self.portfolio.get_current_weights(prices)
                dynamic_weights = self._get_dynamic_weights(klines, lookback=20)
                max_drift = max(abs(current_weights.get(code, 0) - dynamic_weights.get(code, 0)) 
                               for code in dynamic_weights)
                if max_drift > 0.05:
                    should_rebalance = True
            
            if should_rebalance:
                # 使用动态权重而非固定权重
                target_weights = self._get_dynamic_weights(klines, lookback=20)
                self._execute_rebalance(target_weights, prices, date, position_scale)
                last_rebalance = date

            self.equity_curve.append({
                'date': str(date),
                'value': total_value
            })

        return self._compute_results(dates)

    def _compute_results(self, dates):
        if len(self.equity_curve) < 2:
            return {'error': '回测数据不足'}

        values = np.array([e['value'] for e in self.equity_curve])
        initial = self.initial_capital
        final = values[-1]
        total_return = (final - initial) / initial
        years = len(dates) / 252
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        peak = np.maximum.accumulate(values)
        drawdowns = (peak - values) / peak
        max_drawdown = float(drawdowns.max())

        daily_rets = np.diff(values) / values[:-1]
        annual_vol = float(np.std(daily_rets) * np.sqrt(252)) if len(daily_rets) > 0 else 0
        sharpe = (annual_return - 0.03) / annual_vol if annual_vol > 0 else 0
        win_rate = float(np.sum(daily_rets > 0) / len(daily_rets)) if len(daily_rets) > 0 else 0

        return {
            'initial_capital': initial,
            'final_capital': float(final),
            'total_return': float(total_return),
            'annual_return': float(annual_return),
            'annual_volatility': float(annual_vol),
            'max_drawdown': float(max_drawdown),
            'sharpe_ratio': float(sharpe),
            'win_rate': float(win_rate),
            'num_trades': len(self.trades),
            'num_days': len(values),
            'target_check': {
                'annual_return_ok': annual_return >= 0.08,
                'max_drawdown_ok': max_drawdown <= 0.10
            },
            'dates': [e['date'] for e in self.equity_curve],
            'values': [e['value'] for e in self.equity_curve],
            'trades': self.trades
        }
