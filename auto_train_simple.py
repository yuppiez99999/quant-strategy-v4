#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化版自动化模型训练脚本
"""

import sys
import os
import io
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib

# 修复编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print('='*70)
print('自动化量化模型训练系统 (简化版)')
print('='*70)

# 步骤1: 加载数据
print('\n【步骤1】加载parquet数据...')
data_dir = 'data/cache'
all_data = []

for file in os.listdir(data_dir):
    if file.startswith('kline_') and file.endswith('.parquet'):
        filepath = os.path.join(data_dir, file)
        df = pd.read_parquet(filepath)
        code = file.replace('kline_', '').replace('_daily.parquet', '')
        df['code'] = code
        all_data.append(df)
        print(f'  [OK] {file}: {len(df)}条')

combined = pd.concat(all_data, ignore_index=True)
print(f'\n[DATA] 共 {len(combined)} 条记录')

# 步骤2: 计算特征
print('\n【步骤2】计算技术指标...')
features_list = []

for code, group in combined.groupby('code'):
    group = group.reset_index(drop=True)
    group = group.sort_values('_DATE')
    
    # 收益率
    group['returns'] = group['close'].pct_change()
    
    # 移动平均线
    group['ma5'] = group['close'].rolling(5).mean()
    group['ma20'] = group['close'].rolling(20).mean()
    
    # 均线比率
    group['ma_ratio'] = group['ma5'] / group['ma20']
    
    # 波动率
    group['volatility'] = group['returns'].rolling(10).std()
    
    # 标签: 次日涨跌
    group['label'] = (group['returns'].shift(-1) > 0).astype(int)
    
    features_list.append(group[['returns', 'ma_ratio', 'volatility', 'label']])

df_features = pd.concat(features_list, ignore_index=True)
df_features.dropna(inplace=True)
df_features.replace([np.inf, -np.inf], 0, inplace=True)

print(f'[DATA] 有效样本: {len(df_features)}')
print(f'[FEATURE] 特征: returns, ma_ratio, volatility')

# 步骤3: 划分训练测试集
print('\n【步骤3】划分数据集...')
X = df_features[['returns', 'ma_ratio', 'volatility']]
y = df_features['label']

from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f'[DATA] 训练集: {len(X_train)} 样本')
print(f'[DATA] 测试集: {len(X_test)} 样本')

# 步骤4: 训练模型
print('\n【步骤4】训练RandomForest模型...')
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    min_samples_split=5,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# 步骤5: 评估模型
print('\n【步骤5】模型评估...')
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f'\n{"="*70}')
print(f'训练结果')
print(f'{"="*70}')
print(f'准确率: {accuracy:.2%}')

if accuracy > 0.55:
    print(f'✅ 模型表现良好!')
elif accuracy > 0.50:
    print(f'⚠️  模型表现一般,可进一步优化')
else:
    print(f'❌ 模型表现不佳,需要调整特征或参数')

# 特征重要性
print(f'\n特征重要性:')
importances = model.feature_importances_
feat_names = ['returns', 'ma_ratio', 'volatility']

for name, imp in sorted(zip(feat_names, importances), key=lambda x: x[1], reverse=True):
    bar = '█' * int(imp * 50)
    print(f'  {name:<15} {imp:.3f} {bar}')

# 步骤6: 保存模型
print(f'\n【步骤6】保存模型...')
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
model_path = f'models/RandomForest_acc{accuracy:.3f}_{timestamp}.pkl'

os.makedirs('models', exist_ok=True)
joblib.dump(model, model_path)
print(f'💾 模型已保存: {model_path}')

# 保存元数据
import json
metadata = {
    'timestamp': timestamp,
    'model': 'RandomForest',
    'accuracy': float(accuracy),
    'features': feat_names,
    'feature_importances': {name: float(imp) for name, imp in zip(feat_names, importances)},
    'training_samples': len(X_train),
    'testing_samples': len(X_test)
}

metadata_path = f'models/metadata_{timestamp}.json'
with open(metadata_path, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print(f'📄 元数据已保存: {metadata_path}')

print(f'\n{"="*70}')
print(f'✅ 训练完成!')
print(f'{"="*70}')
