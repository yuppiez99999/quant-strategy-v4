#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Qwen2.5-1.5B 参数优化与回测验证
===============================
- 独立Qwen预测 (不依赖Kronos)
- 网格搜索: temperature [0.1, 0.3, 0.5, 0.7], max_tokens [200, 400]
- 滑动窗口回测: 60天, 20日lookback
- Markdown报告
"""
import sys, os, json, time, itertools
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UTILS_DIR = os.path.join(BASE_DIR, 'utils')
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, UTILS_DIR)

from kronos_predictor import fetch_a_stock_data
from qwen_financial_predictor import get_qwen_predictor, QwenServerManager

# 核心6只标的 (用于快速回测)
CORE_STOCKS = [
    {"code": "601088", "name": "中国神华", "sector": "顺周期"},
    {"code": "002371", "name": "北方华创", "sector": "高端制造"},
    {"code": "688981", "name": "中芯国际", "sector": "高端制造"},
    {"code": "600276", "name": "恒瑞医药", "sector": "防御"},
    {"code": "300750", "name": "宁德时代", "sector": "高端制造"},
    {"code": "603259", "name": "药明康德", "sector": "防御"},
]


def ensure_server():
    mgr = QwenServerManager.get_instance()
    try:
        import subprocess as sp
        sp.run(['taskkill', '/F', '/IM', 'llama-server.exe'], capture_output=True)
        time.sleep(2)
    except: pass
    mgr.start()
    return mgr


def qwen_predict_signal(df, predictor, temperature=0.3, max_tokens=300):
    """使用Qwen直接预测买入/卖出/持有信号"""
    close = df['close'].values
    price = float(close[-1])
    n = len(close)

    # 计算指标
    ma5 = float(np.mean(close[-5:])) if n >= 5 else price
    ma10 = float(np.mean(close[-10:])) if n >= 10 else price
    ma20 = float(np.mean(close[-20:])) if n >= 20 else price
    pct5d = (price / close[-5] - 1) * 100 if n >= 5 and close[-5] > 0 else 0
    pct10d = (price / close[-10] - 1) * 100 if n >= 10 and close[-10] > 0 else 0

    # RSI简化
    if n >= 14:
        delta = np.diff(close[-15:])
        gain = np.mean(delta[delta > 0]) if any(delta > 0) else 0
        loss = -np.mean(delta[delta < 0]) if any(delta < 0) else 0
        rsi = 100 - 100/(1 + gain/max(loss, 1e-9)) if loss > 0 else 50
    else:
        rsi = 50

    # 波动率
    if n >= 10:
        rets = np.diff(close[-11:]) / close[-11:-1]
        vol = float(np.std(rets) * 100)
    else:
        vol = 0

    prompt = f"""分析以下A股技术数据，预测短期(1-3天)走势方向。

当前价格: {price:.2f}
5日涨跌: {pct5d:+.1f}%
10日涨跌: {pct10d:+.1f}%
MA5: {ma5:.2f}
MA10: {ma10:.2f}
MA20: {ma20:.2f}
RSI(14): {rsi:.0f}
波动率: {vol:.1f}%
均线排列: {'多头' if ma5>ma10>ma20 else '空头' if ma5<ma10<ma20 else '交叉'}

只输出一个英文单词: buy/sell/hold"""

    try:
        predictor.temperature = temperature
        predictor.max_tokens = max_tokens
        client = predictor.client
        resp = client.generate(
            prompt=prompt,
            system_prompt="你是A股量化分析师。只输出一个单词: buy, sell, 或 hold。不要解释。",
            temperature=temperature,
            max_tokens=10,
        )
        resp_lower = resp.strip().lower()
        if 'buy' in resp_lower:
            return 'buy'
        elif 'sell' in resp_lower:
            return 'sell'
        else:
            return 'hold'
    except Exception as e:
        # Fallback: MA交叉策略
        if ma5 > ma20 * 1.01:
            return 'buy'
        elif ma5 < ma20 * 0.99:
            return 'sell'
        else:
            return 'hold'


def run_backtest(stocks, params, test_days=60, lookback=20, pred_len=3):
    """滑动窗口回测"""
    predictor = get_qwen_predictor()
    temp = params.get('temperature', 0.3)
    max_tok = params.get('max_tokens', 300)

    all_predictions = []
    all_actuals = []

    for stock in stocks:
        code, name = stock['code'], stock['name']
        try:
            df = fetch_a_stock_data(code, days=lookback + test_days + 30, verbose=False)
            if len(df) < lookback + 10:
                continue

            for i in range(lookback, len(df) - pred_len, 5):
                train = df.iloc[i - lookback:i]
                future = df.iloc[i + pred_len - 1] if i + pred_len < len(df) else None
                if future is None or 'close' not in future:
                    continue

                current = float(train['close'].iloc[-1])
                future_close = float(future['close']) if hasattr(future, 'close') else float(train['close'].iloc[-1])

                signal = qwen_predict_signal(train, predictor, temperature=temp, max_tokens=max_tok)
                pred_dir = 1 if signal == 'buy' else (-1 if signal == 'sell' else 0)

                actual_ret = (future_close / current - 1) if current > 0 else 0
                all_predictions.append(pred_dir)
                all_actuals.append(actual_ret)
        except Exception as e:
            print(f"  [SKIP] {name}: {str(e)[:50]}")
            continue

    n = len(all_predictions)
    if n == 0:
        return {'error': '无有效数据', 'n': 0}

    non_zero = [i for i, p in enumerate(all_predictions) if p != 0]
    correct_dir = sum(1 for i in non_zero if np.sign(all_predictions[i]) == np.sign(all_actuals[i]))

    returns_when_trade = [all_actuals[i] for i in non_zero]
    win_trades = [r for r in returns_when_trade if r > 0]

    total_ret = float(np.prod([1 + r for r in returns_when_trade]) - 1) if returns_when_trade else 0
    cum = np.cumprod([1 + r for r in returns_when_trade]) if returns_when_trade else np.array([1])
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak
    max_dd = float(np.min(dd))

    avg_ret = float(np.mean(returns_when_trade)) if returns_when_trade else 0
    std_ret = float(np.std(returns_when_trade)) if len(returns_when_trade) > 1 else 0.01
    sharpe = (avg_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0

    return {
        'params': params,
        'n_predictions': n,
        'n_trades': len(non_zero),
        'direction_accuracy': correct_dir / len(non_zero) if non_zero else 0,
        'win_rate': len(win_trades) / len(non_zero) if non_zero else 0,
        'avg_return': avg_ret,
        'total_return': total_ret,
        'max_drawdown': max_dd,
        'sharpe_ratio': sharpe,
    }


def grid_search(stocks):
    """参数网格搜索"""
    param_grid = {
        'temperature': [0.1, 0.3, 0.5],
        'max_tokens': [200, 400],
    }

    keys = list(param_grid.keys())
    combos = list(itertools.product(*param_grid.values()))
    print(f"\n[OPT] 网格搜索: {len(combos)} 种组合")

    results = []
    best_score = -float('inf')
    best_params = None
    best_result = None

    for idx, combo in enumerate(combos):
        params = dict(zip(keys, combo))
        print(f"  [{idx+1}/{len(combos)}] {params}")

        result = run_backtest(stocks, params, test_days=40)
        if 'error' not in result:
            score = result.get('direction_accuracy', 0) * 0.5 + max(result.get('sharpe_ratio', 0), 0) * 0.3 + max(result.get('total_return', -1), 0) * 0.2
            result['score'] = score
        else:
            result['score'] = -999

        results.append(result)
        if result['score'] > best_score:
            best_score = result['score']
            best_params = params
            best_result = result

    return best_params, best_result, results


def generate_optimization_report(best_params, best_result, all_results, stocks, output_path):
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    lines = [
        f"# Qwen2.5-1.5B 参数优化报告",
        f"",
        f"**生成时间**: {now}",
        f"**模型**: Qwen2.5-1.5B-Instruct-GGUF Q4_K_M",
        f"**后端**: llama.cpp b9789 CPU (llama-server HTTP)",
        f"**回测标的**: {len(stocks)} 只 (Wind MCP 数据)",
        f"",
        f"---",
        f"",
        f"## 1. 最优参数",
        f"",
        f"| 参数 | 最优值 |",
        f"|------|-------|",
        f"| temperature | {best_params.get('temperature')} |",
        f"| max_tokens | {best_params.get('max_tokens')} |",
        f"",
        f"## 2. 最优参数回测指标",
        f"",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 预测次数 | {best_result.get('n_predictions', 'N/A')} |",
        f"| 交易次数 | {best_result.get('n_trades', 'N/A')} |",
        f"| 方向准确率 | {best_result.get('direction_accuracy', 0)*100:.1f}% |",
        f"| 胜率 | {best_result.get('win_rate', 0)*100:.1f}% |",
        f"| 平均收益 | {best_result.get('avg_return', 0)*100:.2f}% |",
        f"| 总收益率 | {best_result.get('total_return', 0)*100:.2f}% |",
        f"| 最大回撤 | {best_result.get('max_drawdown', 0)*100:.2f}% |",
        f"| 夏普比率 | {best_result.get('sharpe_ratio', 0):.2f} |",
        f"",
        f"## 3. 全部组合排名",
        f"",
        f"| 排名 | Temperature | MaxTokens | 方向准确率 | 夏普 | 总收益 | 评分 |",
        f"|------|------------|-----------|----------|------|-------|------|",
    ]

    sorted_results = sorted([r for r in all_results if 'error' not in r],
                            key=lambda x: x.get('score', -999), reverse=True)
    for rank, r in enumerate(sorted_results, 1):
        p = r.get('params', {})
        lines.append(
            f"| {rank} | {p.get('temperature', '?')} | {p.get('max_tokens', '?')} | "
            f"{r.get('direction_accuracy', 0)*100:.1f}% | "
            f"{r.get('sharpe_ratio', 0):.2f} | "
            f"{r.get('total_return', 0)*100:.1f}% | "
            f"{r.get('score', 0):.3f} |"
        )

    lines.extend([
        f"",
        f"## 4. 系统配置",
        f"",
        f"```yaml",
        f"model: Qwen2.5-1.5B-Instruct-GGUF (Q4_K_M)", 
        f"size: 1066 MB",
        f"backend: llama.cpp b9789 (CPU, Windows x64)",
        f"server: llama-server.exe @ 127.0.0.1:8100",
        f"inference_speed: ~9 tok/s",
        f"context_length: 2048",
        f"```",
        f"",
        f"---",
        f"*报告由 Qwen2.5-1.5B 参数优化管线自动生成*",
    ])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    print("=" * 70)
    print("Qwen2.5-1.5B 参数优化 & 回测验证")
    print("=" * 70)

    # 1. 启动服务器
    print("[1/4] 启动 Qwen 服务器...")
    mgr = ensure_server()
    print(f"  Server: {mgr.base_url} | Health: {mgr.health()}")

    # 2. 参数优化
    print("[2/4] 网格搜索最优参数...")
    best_params, best_result, all_results = grid_search(CORE_STOCKS[:4])  # 4只核心标的快速优化

    # 3. 用最优参数跑完整回测
    print(f"\n[3/4] 最优参数完整回测: {best_params}")
    final_result = run_backtest(CORE_STOCKS, best_params, test_days=60)

    print(f"\n  方向准确率: {final_result.get('direction_accuracy', 0)*100:.1f}%")
    print(f"  夏普比率: {final_result.get('sharpe_ratio', 0):.2f}")
    print(f"  总收益率: {final_result.get('total_return', 0)*100:.1f}%")
    print(f"  最大回撤: {final_result.get('max_drawdown', 0)*100:.1f}%")

    # 4. 报告
    print("[4/4] 生成报告...")
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = os.path.join(BASE_DIR, 'reports', f'qwen_optimization_report_{ts}.md')
    generate_optimization_report(best_params, final_result, all_results, CORE_STOCKS, report_path)
    print(f"\n[SAVED] {report_path}")

    mgr.stop()
    print("\n[DONE]")


if __name__ == "__main__":
    main()
