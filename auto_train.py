#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动化模型训练脚本
支持: 数据加载 → 特征工程 → 模型训练 → 评估 → 保存
"""

import sys
import os
import io
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

class AutoTrainer:
    """自动训练器"""
    
    def __init__(self, output_dir='models'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.models = {}
        self.results = {}
        self.feature_cols = []
    
    def load_data(self, data_dir='data/cache'):
        """加载所有parquet数据"""
        print('[DATA] 加载历史数据...')
        print(f'[PATH] 数据目录: {os.path.abspath(data_dir)}')
        
        all_data = []
        file_count = 0
        
        for file in os.listdir(data_dir):
            if file.startswith('kline_') and file.endswith('.parquet'):
                filepath = os.path.join(data_dir, file)
                try:
                    df = pd.read_parquet(filepath)
                    code = file.replace('kline_', '').replace('_daily.parquet', '')
                    df['code'] = code
                    all_data.append(df)
                    file_count += 1
                    print(f'  [OK] {file}: {len(df)}条记录')
                except Exception as e:
                    print(f'  [WARN] {file}: 加载失败 - {e}')
        
        if not all_data:
            print('\n[ERROR] 未找到任何parquet数据文件!')
            print(f'[PATH] 请检查目录: {os.path.abspath(data_dir)}')
            return None
        
        combined = pd.concat(all_data, ignore_index=True)
        print(f'\n[DATA] 共加载 {file_count} 个文件, {len(combined)} 条记录')
        return combined
    
    def engineer_features(self, df):
        """特征工程"""
        print('\n[FEATURE] 构建特征...')
        
        # 先检查数据结构
        print(f'[DEBUG] df形状: {df.shape}')
        print(f'[DEBUG] df列名: {df.columns.tolist()}')
        print(f'[DEBUG] 唯一code数: {df["code"].nunique()}')
        
        features = []
        valid_codes = 0
        
        for code, group in df.groupby('code'):
            if len(group) < 30:
                continue
            
            # 重置索引,使日期成为列
            group = group.reset_index(drop=True)
            
            # 处理日期列
            if 'date' not in group.columns:
                if 'index' in group.columns:
                    group.rename(columns={'index': 'date'}, inplace=True)
                elif '_DATE' in group.columns:
                    group['date'] = pd.to_datetime(group['_DATE'].astype(str), format='%Y%m%d')
            group.drop(columns=['_DATE'], inplace=True)
            
            # 价格特征
            group['returns'] = group['close'].pct_change()
            group['log_returns'] = np.log(group['close'] / group['close'].shift(1))
            
            # 移动平均线
            group['ma_5'] = group['close'].rolling(5).mean()
            group['ma_10'] = group['close'].rolling(10).mean()
            group['ma_20'] = group['close'].rolling(20).mean()
            group['ma_60'] = group['close'].rolling(60).mean()
            
            # 均线比率
            group['ma5_ma20'] = group['ma_5'] / group['ma_20']
            group['ma20_ma60'] = group['ma_20'] / group['ma_60']
            
            # 波动率
            group['volatility_5'] = group['returns'].rolling(5).std()
            group['volatility_20'] = group['returns'].rolling(20).std()
            
            # RSI
            group['rsi'] = self._calculate_rsi(group['close'], 14)
            
            # MACD
            ema_12 = group['close'].ewm(span=12).mean()
            ema_26 = group['close'].ewm(span=26).mean()
            group['macd'] = ema_12 - ema_26
            
            # 布林带
            group['boll_mid'] = group['ma_20']
            group['boll_upper'] = group['ma_20'] + 2 * group['close'].rolling(20).std()
            group['boll_lower'] = group['ma_20'] - 2 * group['close'].rolling(20).std()
            group['boll_width'] = (group['boll_upper'] - group['boll_lower']) / group['boll_mid']
            
            # 成交量特征
            if 'volume' in group.columns:
                group['volume_ma_5'] = group['volume'].rolling(5).mean()
                group['volume_ratio'] = group['volume'] / group['volume_ma_5']
            
            # 标签: 次日涨跌 (分类) 和 次日收益率 (回归)
            group['label_up'] = (group['returns'].shift(-1) > 0).astype(int)
            group['label_return'] = group['returns'].shift(-1)
            
            # 未来3日收益
            group['label_3d_return'] = group['returns'].shift(-3)
            group['label_3d_up'] = (group['label_3d_return'] > 0).astype(int)
            
            features.append(group)
            valid_codes += 1
        
        if not features:
            print('\n[ERROR] 没有有效的数据!')
            return None, None
        
        df_features = pd.concat(features, ignore_index=True)
        df_features.dropna(inplace=True)
        
        # 选择特征列
        self.feature_cols = [
            'returns', 'log_returns', 
            'ma5_ma20', 'ma20_ma60',
            'volatility_5', 'volatility_20',
            'rsi', 'macd',
            'boll_width'
        ]
        
        # 确保所有特征列都存在
        self.feature_cols = [col for col in self.feature_cols if col in df_features.columns]
        
        print(f'[FEATURE] 使用 {len(self.feature_cols)} 个特征: {", ".join(self.feature_cols)}')
        print(f'[DATA] 有效代码数: {valid_codes}')
        print(f'[DATA] 样本数: {len(df_features)}')
        
        return df_features, self.feature_cols
    
    def _calculate_rsi(self, prices, period=14):
        """计算RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def train_models(self, X_y, feature_cols):
        """训练多个模型并对比"""
        X = X_y[feature_cols]
        
        # 移除异常值
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(0)
        
        print('\n[TRAIN] 划分训练集/测试集 (80/20)...')
        y_primary = X_y['label_up']
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_primary, test_size=0.2, random_state=42, stratify=y_primary
        )
        
        print(f'[DATA] 训练集: {len(X_train)} 样本')
        print(f'[DATA] 测试集: {len(X_test)} 样本')
        
        # 定义模型
        models = {
            'RandomForest': RandomForestClassifier(
                n_estimators=200, 
                max_depth=10, 
                min_samples_split=5,
                random_state=42,
                n_jobs=-1
            ),
            'GradientBoosting': GradientBoostingClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            ),
            'ExtraTrees': ExtraTreesClassifier(
                n_estimators=200,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            ),
            'LogisticRegression': LogisticRegression(
                max_iter=1000,
                random_state=42,
                C=1.0
            ),
        }
        
        print('\n[TRAIN] 开始训练...')
        print('='*60)
        
        for name, model in models.items():
            print(f'\n[{name}] 训练中...')
            try:
                model.fit(X_train, y_train)
                
                # 预测
                y_pred = model.predict(X_test)
                y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else None
                
                # 评估
                accuracy = accuracy_score(y_test, y_pred)
                
                print(f'  [OK] 准确率: {accuracy:.2%}')
                
                if accuracy > 0.55:  # 略高于随机
                    print(f'  [GOOD] 模型表现优于随机!')
                
                self.models[name] = model
                self.results[name] = {
                    'accuracy': accuracy,
                    'y_pred': y_pred,
                    'y_test': y_test.values,
                    'y_prob': y_prob
                }
                
            except Exception as e:
                print(f'  [ERROR] {name} 训练失败: {e}')
        
        print('\n' + '='*60)
        return self.results
    
    def save_models(self):
        """保存所有模型"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        saved_models = []
        
        for name, model in self.models.items():
            result = self.results.get(name, {})
            accuracy = result.get('accuracy', 0)
            
            # 只保存准确率>50%的模型
            if accuracy > 0.50:
                filename = f'{name}_acc{accuracy:.3f}_{timestamp}.pkl'
                path = os.path.join(self.output_dir, filename)
                joblib.dump(model, path)
                saved_models.append((name, path, accuracy))
                print(f'[SAVE] {name} (准确率{accuracy:.2%}) → {filename}')
        
        if not saved_models:
            print('\n[WARN] 没有模型达到保存标准 (准确率>50%)')
        else:
            print(f'\n[OK] 成功保存 {len(saved_models)} 个模型')
        
        return saved_models
    
    def generate_report(self):
        """生成训练报告"""
        print('\n' + '='*70)
        print('训练结果报告')
        print('='*70)
        
        if not self.results:
            print('\n[ERROR] 没有训练结果!')
            return
        
        # 按准确率排序
        sorted_results = sorted(
            self.results.items(), 
            key=lambda x: x[1]['accuracy'], 
            reverse=True
        )
        
        print(f'\n{'模型':<25} {'准确率':>10} {'排名':>6}')
        print('-'*70)
        
        for rank, (name, result) in enumerate(sorted_results, 1):
            accuracy = result['accuracy']
            print(f'{name:<25} {accuracy:>9.2%} {rank:>5}')
        
        # 最佳模型详细报告
        best_name, best_result = sorted_results[0]
        best_model = self.models[best_name]
        
        print(f'\n[BEST] 最佳模型: {best_name} (准确率 {best_result["accuracy"]:.2%})')
        print('\n详细分类报告:')
        print(classification_report(
            best_result['y_test'], 
            best_result['y_pred'],
            target_names=['下跌', '上涨']
        ))
        
        # 特征重要性 (仅Tree模型)
        if hasattr(best_model, 'feature_importances_'):
            print('\n[FEATURE] 特征重要性 (Top 5):')
            importances = best_model.feature_importances_
            indices = np.argsort(importances)[::-1][:5]
            
            for idx in indices:
                feat_name = self.feature_cols[idx]
                feat_imp = importances[idx]
                bar = '█' * int(feat_imp * 100)
                print(f'  {feat_name:<20} {feat_imp:.3f} {bar}')
        
        print('\n' + '='*70)
    
    def save_training_metadata(self, saved_models):
        """保存训练元数据"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        metadata_file = os.path.join(self.output_dir, f'training_metadata_{timestamp}.json')
        
        metadata = {
            'timestamp': timestamp,
            'models_trained': list(self.models.keys()),
            'best_model': saved_models[0][0] if saved_models else None,
            'accuracies': {name: result['accuracy'] for name, result in self.results.items()},
            'feature_count': len(self.feature_cols),
            'features': self.feature_cols,
            'model_files': [(name, path, accuracy) for name, path, accuracy in saved_models]
        }
        
        import json
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f'[META] 训练元数据已保存: {metadata_file}')
        return metadata_file


def main():
    """主函数"""
    print('='*70)
    print('自动化量化模型训练系统')
    print('='*70)
    print(f'开始时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    # 初始化训练器
    trainer = AutoTrainer(output_dir='models')
    
    # 步骤1: 加载数据
    print('\n【步骤1/5】加载数据')
    print('-'*70)
    df = trainer.load_data()
    if df is None:
        print('\n[ERROR] 数据加载失败,退出训练')
        sys.exit(1)
    
    # 步骤2: 特征工程
    print('\n【步骤2/5】特征工程')
    print('-'*70)
    X_y, feature_cols = trainer.engineer_features(df)
    if X_y is None:
        print('\n[ERROR] 特征工程失败,退出训练')
        sys.exit(1)
    
    # 步骤3: 训练模型
    print('\n【步骤3/5】模型训练')
    print('-'*70)
    results = trainer.train_models(X_y, feature_cols)
    
    if not results:
        print('\n[ERROR] 模型训练失败,退出训练')
        sys.exit(1)
    
    # 步骤4: 生成报告
    print('\n【步骤4/5】生成报告')
    print('-'*70)
    trainer.generate_report()
    
    # 步骤5: 保存模型
    print('\n【步骤5/5】保存模型')
    print('-'*70)
    saved_models = trainer.save_models()
    
    # 保存元数据
    metadata_file = trainer.save_training_metadata(saved_models)
    
    # 完成
    print('\n' + '='*70)
    print('✅ 训练完成!')
    print('='*70)
    print(f'结束时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'保存模型: {len(saved_models)} 个')
    print(f'元数据: {metadata_file}')
    print()
    
    if saved_models:
        best_name, best_path, best_acc = saved_models[0]
        print(f'🏆 最佳模型: {best_name} (准确率 {best_acc:.2%})')
        print(f'📁 模型路径: {best_path}')
    
    print('='*70)


if __name__ == '__main__':
    main()
