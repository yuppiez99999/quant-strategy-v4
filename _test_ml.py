# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')
from utils.ml_predictor import run_ml_signal_scan

result = run_ml_signal_scan(data_dir='data/cache', model_dir='models', threshold=0.55)
print('扫描标的数:', result.get('scanned_count', 0))
print('模型信息:', result.get('model_info', {}).get('best_model', 'N/A'))
print('买入信号:', len(result.get('signals', {}).get('buy', [])))
print('卖出信号:', len(result.get('signals', {}).get('sell', [])))
print('持有信号:', len(result.get('signals', {}).get('hold', [])))
print()
print('=== 买入信号 Top 5 ===')
for s in result.get('signals', {}).get('buy', [])[:5]:
    print(f"  {s['code']}: 上涨概率 {s['probability']:.2%}, 置信度 {s['confidence']:.2%}")
print()
print('=== 卖出信号 Top 5 ===')
for s in result.get('signals', {}).get('sell', [])[:5]:
    print(f"  {s['code']}: 下跌概率 {(1-s['probability']):.2%}, 置信度 {s['confidence']:.2%}")
