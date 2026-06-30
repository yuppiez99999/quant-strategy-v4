#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
本地训练统一启动器 v1.0
- 自动适配数据路径 (model_train/output/kline_cache/ → 训练器预期)
- 阶段1: auto_train_optimized (ML: GBDT/XGBoost/LightGBM + GridSearchCV)
- 阶段2: patchtst_trainer (DL: PatchTST + LSTM 基线)
- 生成综合训练报告

用法: python run_local_train.py [--phase 1|2|all]
"""

import sys
import os
import io
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = Path(__file__).parent
CACHE_SRC = BASE_DIR / 'model_train' / 'output' / 'kline_cache'
CACHE_DST = BASE_DIR / 'data' / 'cache'
MODELS_DIR = BASE_DIR / 'models'

def prepare_data():
    """将 kline_cache 的 parquet 文件复制到训练器预期的 data/cache/ 路径"""
    print('\n' + '='*70)
    print('[PREP] 数据准备 — 适配训练器路径')
    print('='*70)
    
    if not CACHE_SRC.exists():
        print(f'[ERROR] 源数据目录不存在: {CACHE_SRC}')
        return False
    
    parquet_files = list(CACHE_SRC.glob('*.parquet'))
    if not parquet_files:
        print(f'[ERROR] 源数据目录无parquet文件: {CACHE_SRC}')
        return False
    
    print(f'[SRC] 找到 {len(parquet_files)} 个parquet文件')
    CACHE_DST.mkdir(parents=True, exist_ok=True)
    
    copied = 0
    for f in parquet_files:
        # 源命名: 688981.SH.parquet → 目标: kline_688981.SH_daily.parquet
        code = f.stem  # e.g. "688981.SH"
        dst_name = f'kline_{code}_daily.parquet'
        dst_path = CACHE_DST / dst_name
        
        # 检查是否需要更新 (源文件更新时才复制)
        if dst_path.exists() and dst_path.stat().st_mtime >= f.stat().st_mtime:
            copied += 1
            continue
        
        shutil.copy2(f, dst_path)
        copied += 1
    
    print(f'[DST] 已复制 {copied} 个文件到 {CACHE_DST}')
    return True


def run_ml_training():
    """阶段1: 运行 auto_train_optimized (ML分类器)"""
    print('\n' + '='*70)
    print('[PHASE 1] ML分类器训练 — auto_train_optimized')
    print('='*70)
    print(f'开始时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    os.chdir(str(BASE_DIR))
    
    result = subprocess.run(
        [sys.executable, 'auto_train_optimized.py'],
        capture_output=False,
        text=True,
        cwd=str(BASE_DIR)
    )
    
    if result.returncode != 0:
        print(f'\n[ERROR] ML训练失败, 返回码: {result.returncode}')
        return False
    
    print(f'\n[PHASE 1] ML训练完成')
    return True


def run_dl_training():
    """阶段2: 运行 patchtst_trainer (PatchTST + LSTM)"""
    print('\n' + '='*70)
    print('[PHASE 2] 深度学习训练 — PatchTST + LSTM')
    print('='*70)
    print(f'开始时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    os.chdir(str(BASE_DIR))
    
    result = subprocess.run(
        [sys.executable, 'patchtst_trainer.py'],
        capture_output=False,
        text=True,
        cwd=str(BASE_DIR)
    )
    
    if result.returncode != 0:
        print(f'\n[ERROR] DL训练失败, 返回码: {result.returncode}')
        return False
    
    print(f'\n[PHASE 2] DL训练完成')
    return True


def generate_summary():
    """生成训练汇总报告"""
    print('\n' + '='*70)
    print('[SUMMARY] 生成训练汇总报告')
    print('='*70)
    
    summary = {
        'timestamp': datetime.now().isoformat(),
        'phases': {},
        'models': [],
    }
    
    # 扫描 models/ 目录
    if MODELS_DIR.exists():
        for f in sorted(MODELS_DIR.glob('*.pkl'), key=lambda x: x.stat().st_mtime, reverse=True):
            summary['models'].append({
                'name': f.name,
                'size_kb': round(f.stat().st_size / 1024, 1),
                'time': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
        
        # 最新的 JSON 元数据
        json_files = sorted(MODELS_DIR.glob('training_metadata_*.json'), 
                           key=lambda x: x.stat().st_mtime, reverse=True)
        if json_files:
            try:
                with open(json_files[0], 'r', encoding='utf-8') as f:
                    summary['ml_results'] = json.load(f)
            except Exception:
                pass
    
    report_path = BASE_DIR / f'training_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
    
    print(f'[SUMMARY] 报告已保存: {report_path}')
    
    # 打印简要
    print(f'\n├─ 模型文件数: {len(summary["models"])}')
    if 'ml_results' in summary:
        mr = summary['ml_results']
        best = mr.get('best_model', 'N/A')
        if best in mr.get('results', {}):
            acc = mr['results'][best].get('accuracy', 0)
            f1 = mr['results'][best].get('f1', 0)
            print(f'├─ ML最佳模型: {best} (准确率 {acc:.2%}, F1 {f1:.4f})')
    
    return summary


def main():
    import argparse
    parser = argparse.ArgumentParser(description='本地训练统一启动器')
    parser.add_argument('--phase', choices=['1', '2', 'all'], default='all',
                       help='训练阶段: 1=ML分类器, 2=PatchTST+LSTM, all=全部')
    parser.add_argument('--skip-prepare', action='store_true',
                       help='跳过数据准备步骤')
    args = parser.parse_args()
    
    print('='*70)
    print('  量化策略系统 — 本地训练启动器 v1.0')
    print(f'  运行时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'  阶段选择: {args.phase}')
    print('='*70)
    
    t0 = datetime.now()
    
    # Step 0: 数据准备
    if not args.skip_prepare:
        if not prepare_data():
            print('\n[ERROR] 数据准备失败')
            sys.exit(1)
    
    # Step 1: ML训练
    if args.phase in ('1', 'all'):
        run_ml_training()
    
    # Step 2: DL训练
    if args.phase in ('2', 'all'):
        run_dl_training()
    
    # Step 3: 汇总
    generate_summary()
    
    elapsed = (datetime.now() - t0).total_seconds()
    print(f'\n{"="*70}')
    print(f'✅ 本地训练完成! 总耗时: {elapsed:.0f}秒')
    print(f'{"="*70}')


if __name__ == '__main__':
    main()
