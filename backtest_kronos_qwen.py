#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kronos + Qwen 回测验证 & 参数优化系统
=====================================
回测流程:
1. 从 Wind MCP 获取历史数据
2. 滑动窗口: 每20日滚动预测未来5日
3. 记录预测 vs 实际
4. 计算准确率/收益率/夏普比率
5. 网格搜索最优参数

参数优化维度:
- pred_len: 预测步长 [5, 10, 15, 24]
- threshold: 交易信号阈值 [0.01, 0.015, 0.02, 0.03]
- weight_qwen: Qwen融合权重 [0.0, 0.3, 0.4, 0.5]
- lookback: 回看窗口 [20, 30, 60]
"""
import sys
import os
import json
import time
import itertools
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))

from kronos_predictor import KronosPredictor, fetch_a_stock_data
from qwen_financial_predictor import get_qwen_predictor, QwenFinancialPredictor


# ============================================================
#  组合持仓 (13只标的, 4板块)
# ============================================================

PORTFOLIO = [
    # 高端制造 (含算力) 45%
    {"code": "300308", "name": "中际旭创", "weight": 0.09},
    {"code": "688041", "name": "海光信息", "weight": 0.09},
    {"code": "002371", "name": "北方华创", "weight": 0.09},
    {"code": "688981", "name": "中芯国际", "weight": 0.09},
    {"code": "300750", "name": "宁德时代", "weight": 0.05},
    {"code": "000425", "name": "徐工机械", "weight": 0.04},
    # 顺周期 20%
    {"code": "601088", "name": "中国神华", "weight": 0.08},
    {"code": "600219", "name": "南山铝业", "weight": 0.06},
    {"code": "600019", "name": "宝钢股份", "weight": 0.06},
    # 资源 20%
    {"code": "000408", "name": "藏格矿业", "weight": 0.10},
    # 防御 15%
    {"code": "600276", "name": "恒瑞医药", "weight": 0.05},
    {"code": "603259", "name": "药明康德", "weight": 0.05},
    {"code": "002422", "name": "科伦药业", "weight": 0.05},
]


class KronosQwenBacktester:
    """Kronos + Qwen 联合回测引擎"""

    def __init__(
        self,
        stocks: List[Dict],
        verbose: bool = True,
        use_qwen: bool = True,
    ):
        self.stocks = stocks
        self.verbose = verbose
        self.use_qwen = use_qwen

        # 初始化预测器
        self.kronos = KronosPredictor(device="cpu", verbose=False)
        self.qwen = get_qwen_predictor() if use_qwen else None

        if self.verbose:
            print("=" * 70)
            print("Kronos + Qwen 回测引擎初始化")
            print(f"  标的数量: {len(stocks)}")
            print(f"  Kronos: {'OK' if self.kronos.predictor_obj else 'FAIL'}")
            print(f"  Qwen: {'OK' if (self.qwen and self.qwen.available) else 'N/A'}")
            print("=" * 70)

    def run_single_backtest(
        self,
        pred_len: int = 5,
        threshold: float = 0.02,
        lookback: int = 20,
        weight_qwen: float = 0.4,
        test_days: int = 60,
    ) -> Dict:
        """运行单次回测

        Args:
            pred_len: 预测步长(Kronos 预测几天后)
            threshold: 交易信号阈值
            lookback: 回看窗口
            weight_qwen: Qwen 融合权重
            test_days: 回测天数

        Returns:
            回测指标字典
        """
        all_trades = []
        all_returns = []
        stock_metrics = {}

        for stock in self.stocks:
            code = stock['code']
            name = stock['name']
            weight = stock['weight']

            try:
                # 获取数据
                df = fetch_a_stock_data(code, days=lookback + test_days + 50, verbose=False)
                if df is None or len(df) < lookback + 10:
                    if self.verbose:
                        print(f"  [SKIP] {name}({code}): 数据不足")
                    continue

                # 滑动窗口回测
                trades = []
                predicted_returns = []
                actual_returns = []

                for i in range(lookback, len(df) - pred_len):
                    train_df = df.iloc[i - lookback:i].copy()
                    future_df = df.iloc[i:i + pred_len]

                    if len(future_df) < pred_len:
                        break

                    # Kronos 预测
                    try:
                        kronos_result = self.kronos.analyze_stock(
                            code, name, train_df, pred_len=pred_len
                        )
                    except Exception:
                        continue

                    kronos_signal = kronos_result.get('signal', 'hold')
                    kronos_return = kronos_result.get('return_pct', 0)

                    # Qwen 增强
                    final_signal = kronos_signal
                    final_return = kronos_return
                    if self.use_qwen and self.qwen and self.qwen.available:
                        try:
                            fused = self.qwen.fused_predict(
                                code, name, train_df, kronos_result,
                                weight_qwen=weight_qwen,
                            )
                            final_signal = fused.get('final_signal', kronos_signal)
                            final_return = fused.get('final_return', kronos_return)
                        except Exception:
                            pass

                    # 实际收益
                    actual_return = (future_df['close'].iloc[-1] / train_df['close'].iloc[-1] - 1)

                    # 记录
                    entry_price = train_df['close'].iloc[-1]
                    exit_price = future_df['close'].iloc[-1]
                    predicted_returns.append(final_return)
                    actual_returns.append(actual_return)

                    if final_signal == 'buy':
                        trades.append({
                            'date': future_df['timestamp'].iloc[0] if 'timestamp' in future_df.columns else str(i),
                            'code': code,
                            'name': name,
                            'action': 'buy',
                            'entry': entry_price,
                            'exit': exit_price,
                            'return': actual_return,
                            'predicted_return': final_return,
                            'weight': weight,
                        })
                    elif final_signal == 'sell':
                        trades.append({
                            'date': future_df['timestamp'].iloc[0] if 'timestamp' in future_df.columns else str(i),
                            'code': code,
                            'name': name,
                            'action': 'sell',
                            'entry': entry_price,
                            'exit': exit_price,
                            'return': actual_return,
                            'predicted_return': final_return,
                            'weight': weight,
                        })

                # 计算该标的指标
                if trades:
                    trade_returns = [t['return'] for t in trades]
                    win_trades = [r for r in trade_returns if r > 0]
                    loss_trades = [r for r in trade_returns if r < 0]

                    hit_count = 0
                    for t in trades:
                        pred_dir = np.sign(t['predicted_return'])
                        actual_dir = np.sign(t['return'])
                        if pred_dir == actual_dir and pred_dir != 0:
                            hit_count += 1

                    stock_metrics[code] = {
                        'name': name,
                        'trades': len(trades),
                        'win_rate': len(win_trades) / len(trades) if trades else 0,
                        'direction_accuracy': hit_count / len(trades) if trades else 0,
                        'avg_return': np.mean(trade_returns) if trade_returns else 0,
                        'avg_win': np.mean(win_trades) if win_trades else 0,
                        'avg_loss': np.mean(loss_trades) if loss_trades else 0,
                        'total_return': np.prod([1 + r for r in trade_returns]) - 1 if trade_returns else 0,
                    }
                    all_trades.extend(trades)
                    all_returns.extend(trade_returns)

            except Exception as e:
                if self.verbose:
                    print(f"  [ERR] {name}({code}): {str(e)[:60]}")

        # 汇总指标
        return self._compute_summary_metrics(all_trades, all_returns, stock_metrics, {
            'pred_len': pred_len,
            'threshold': threshold,
            'lookback': lookback,
            'weight_qwen': weight_qwen,
        })

    def _compute_summary_metrics(
        self,
        all_trades: List[Dict],
        all_returns: List[float],
        stock_metrics: Dict,
        params: Dict,
    ) -> Dict:
        """计算汇总指标"""
        if not all_trades:
            return {'error': '无有效交易', **params}

        n_trades = len(all_trades)
        win_trades = [r for r in all_returns if r > 0]
        loss_trades = [r for r in all_returns if r < 0]

        # 方向准确率
        correct = sum(1 for t in all_trades
                      if np.sign(t['predicted_return']) == np.sign(t['return'])
                      and np.sign(t['return']) != 0)
        direction_accuracy = correct / n_trades if n_trades else 0

        # 基础指标
        win_rate = len(win_trades) / n_trades if n_trades else 0
        avg_return = np.mean(all_returns) if all_returns else 0
        avg_win = np.mean(win_trades) if win_trades else 0
        avg_loss = np.mean(loss_trades) if loss_trades else 0

        # 夏普比率
        risk_free = 0.03 / 252
        excess = np.array(all_returns) - risk_free
        sharpe = np.mean(excess) / max(np.std(excess), 1e-9) * np.sqrt(252)

        # 最大回撤
        cumulative = np.cumprod([1 + r for r in all_returns])
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak
        max_dd = float(np.min(drawdown)) if len(drawdown) > 0 else 0

        # 盈亏比
        profit_factor = abs(sum(r for r in all_returns if r > 0) / max(
            abs(sum(r for r in all_returns if r < 0)), 1e-9
        ))

        # Calmar 比率
        total_ret = cumulative[-1] - 1 if len(cumulative) > 0 else 0
        calmar = total_ret / abs(max_dd) if max_dd < 0 else 0

        return {
            'params': params,
            'n_stocks_traded': len(stock_metrics),
            'n_trades': n_trades,
            'win_rate': win_rate,
            'direction_accuracy': direction_accuracy,
            'avg_return': avg_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe,
            'calmar_ratio': calmar,
            'max_drawdown': max_dd,
            'total_return': total_ret,
            'stock_metrics': stock_metrics,
        }


def run_parameter_optimization(
    stocks: List[Dict],
    param_grid: Optional[Dict] = None,
    use_qwen: bool = True,
    verbose: bool = True,
) -> Tuple[Dict, pd.DataFrame]:
    """网格搜索最优参数

    Returns:
        (best_params, results_df)
    """
    if param_grid is None:
        param_grid = {
            'pred_len': [5, 10],
            'threshold': [0.015, 0.02, 0.03],
            'lookback': [20, 40],
            'weight_qwen': [0.0, 0.3, 0.4],
        }

    # 生成所有组合
    keys = list(param_grid.keys())
    combos = list(itertools.product(*param_grid.values()))

    if verbose:
        print(f"\n[OPT] 参数优化: {len(combos)} 种组合")

    results = []
    best_score = -float('inf')
    best_params = None
    best_result = None

    for idx, combo in enumerate(combos):
        params = dict(zip(keys, combo))
        if verbose:
            print(f"  [{idx+1}/{len(combos)}] {params}")

        bt = KronosQwenBacktester(stocks, verbose=False, use_qwen=use_qwen)
        result = bt.run_single_backtest(**params, test_days=40)

        if 'error' not in result:
            # 综合评分: 夏普比率 * 0.3 + 方向准确率 * 0.4 + 收益率 * 0.3
            score = (
                max(result.get('sharpe_ratio', 0), 0) * 0.3 +
                result.get('direction_accuracy', 0) * 0.4 +
                max(result.get('total_return', 0), -1) * 0.5       # 0.3 -> 0.5 加大收益权重
            )
            result['score'] = score
        else:
            result['score'] = -999

        results.append(result)

        if result.get('score', -999) > best_score:
            best_score = result['score']
            best_params = params
            best_result = result

    df_results = pd.DataFrame(results)
    if 'params' in df_results.columns:
        for key in keys:
            df_results[f'param_{key}'] = df_results['params'].apply(
                lambda x: x.get(key) if isinstance(x, dict) else None
            )

    if verbose and best_params:
        print(f"\n{'='*70}")
        print(f"最优参数: {best_params}")
        print(f"最优评分: {best_score:.4f}")
        if best_result:
            print(f"方向准确率: {best_result.get('direction_accuracy', 0):.2%}")
            print(f"夏普比率: {best_result.get('sharpe_ratio', 0):.2f}")
            print(f"总收益率: {best_result.get('total_return', 0):.2%}")
            print(f"胜率: {best_result.get('win_rate', 0):.2%}")
        print(f"{'='*70}")

    return best_params, df_results


def run_full_backtest(
    stocks: Optional[List[Dict]] = None,
    pred_len: int = 5,
    threshold: float = 0.02,
    lookback: int = 20,
    weight_qwen: float = 0.4,
    test_days: int = 60,
    use_qwen: bool = True,
    save_report: bool = True,
) -> Dict:
    """完整回测流程"""
    if stocks is None:
        stocks = PORTFOLIO[:6]  # 默认测试前6只(高端制造核心)

    bt = KronosQwenBacktester(stocks, verbose=True, use_qwen=use_qwen)
    result = bt.run_single_backtest(
        pred_len=pred_len,
        threshold=threshold,
        lookback=lookback,
        weight_qwen=weight_qwen,
        test_days=test_days,
    )

    # 打印结果
    print(f"\n{'='*70}")
    print("回测结果汇总")
    print(f"{'='*70}")
    print(f"参数: pred_len={pred_len}, threshold={threshold}, lookback={lookback}, w_qwen={weight_qwen}")
    print(f"交易次数: {result.get('n_trades', 0)}")
    print(f"方向准确率: {result.get('direction_accuracy', 0):.2%}")
    print(f"胜率: {result.get('win_rate', 0):.2%}")
    print(f"平均收益: {result.get('avg_return', 0):.4%}")
    print(f"盈亏比: {result.get('profit_factor', 0):.2f}")
    print(f"夏普比率: {result.get('sharpe_ratio', 0):.2f}")
    print(f"卡玛比率: {result.get('calmar_ratio', 0):.2f}")
    print(f"最大回撤: {result.get('max_drawdown', 0):.2%}")
    print(f"总收益率: {result.get('total_return', 0):.2%}")

    # 各标的详情
    sm = result.get('stock_metrics', {})
    if sm:
        print(f"\n各标的表现:")
        for code, m in sm.items():
            print(f"  {m['name']}({code}): 交易{m['trades']}次, "
                  f"胜率{m['win_rate']:.0%}, 方向准确率{m['direction_accuracy']:.0%}, "
                  f"总收益{m['total_return']:.2%}")

    # 保存报告
    if save_report:
        report_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        os.makedirs(report_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = os.path.join(report_dir, f'backtest_kronos_qwen_{ts}.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n[SAVED] 报告: {report_path}")

    return result


# ============================================================
#  CLI
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Kronos+Qwen 回测与参数优化')
    parser.add_argument('--mode', choices=['backtest', 'optimize', 'quick'], default='backtest',
                        help='运行模式')
    parser.add_argument('--stocks', type=int, default=6,
                        help='测试股票数量 (默认6)')
    parser.add_argument('--pred-len', type=int, default=5,
                        help='预测步长')
    parser.add_argument('--threshold', type=float, default=0.02,
                        help='信号阈值')
    parser.add_argument('--lookback', type=int, default=20,
                        help='回看窗口')
    parser.add_argument('--weight-qwen', type=float, default=0.4,
                        help='Qwen融合权重')
    parser.add_argument('--test-days', type=int, default=60,
                        help='回测天数')
    parser.add_argument('--no-qwen', action='store_true',
                        help='禁用Qwen')
    parser.add_argument('--no-save', action='store_true',
                        help='不保存报告')

    args = parser.parse_args()

    stocks = PORTFOLIO[:args.stocks]
    use_qwen = not args.no_qwen

    if args.mode == 'optimize':
        best, df = run_parameter_optimization(stocks, use_qwen=use_qwen)
        print("\n参数排序 (Top 5):")
        if 'score' in df.columns:
            top5 = df.nlargest(5, 'score')
            for _, row in top5.iterrows():
                p = row.get('params', {})
                print(f"  Score={row['score']:.4f} | {p} | "
                      f"Acc={row.get('direction_accuracy',0):.1%} | "
                      f"Sharpe={row.get('sharpe_ratio',0):.2f}")
    elif args.mode == 'quick':
        # 快速测试: 只用3只核心股票
        result = run_full_backtest(
            stocks=PORTFOLIO[:3],
            pred_len=5,
            threshold=0.02,
            lookback=20,
            weight_qwen=0.4,
            test_days=30,
            use_qwen=use_qwen,
            save_report=not args.no_save,
        )
    else:
        result = run_full_backtest(
            stocks=stocks,
            pred_len=args.pred_len,
            threshold=args.threshold,
            lookback=args.lookback,
            weight_qwen=args.weight_qwen,
            test_days=args.test_days,
            use_qwen=use_qwen,
            save_report=not args.no_save,
        )


if __name__ == "__main__":
    main()
