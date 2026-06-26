#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增强版自动化模型训练脚本
支持: 增强特征工程 + XGBoost/LightGBM + PCA降维 + 特征交叉
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
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
import xgboost as xgb
import lightgbm as lgb
import joblib

if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

class EnhancedAutoTrainer:
    """增强版自动训练器"""
    
    def __init__(self, output_dir='models', use_pca=False, pca_components=6):
        self.output_dir = output_dir
        self.use_pca = use_pca
        self.pca_components = pca_components
        os.makedirs(output_dir, exist_ok=True)
        self.models = {}
        self.results = {}
        self.feature_cols = []
        self.scaler = None
        self.pca = None
    
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
        """增强特征工程"""
        print('\n[FEATURE] 构建增强特征...')
        
        print(f'[DEBUG] df形状: {df.shape}')
        print(f'[DEBUG] df列名: {df.columns.tolist()}')
        print(f'[DEBUG] 唯一code数: {df["code"].nunique()}')
        
        features = []
        valid_codes = 0
        
        for code, group in df.groupby('code'):
            if len(group) < 60:
                continue
            
            if isinstance(group.index, pd.DatetimeIndex):
                group = group.reset_index().rename(columns={'index': 'date'})
            else:
                group = group.reset_index(drop=True)
            
            if 'date' not in group.columns:
                if '_DATE' in group.columns:
                    try:
                        group['date'] = pd.to_datetime(group['_DATE'], errors='coerce')
                    except:
                        group['date'] = pd.to_datetime(group['_DATE'].astype(str), errors='coerce')
                elif 'DATE' in group.columns:
                    group['date'] = pd.to_datetime(group['DATE'], errors='coerce')
            
            if 'date' in group.columns:
                group = group.dropna(subset=['date'])
            
            for col in ['_DATE', 'DATE', 'index']:
                if col in group.columns:
                    group.drop(columns=[col], inplace=True)
            
            if 'close' not in group.columns:
                continue
            
            group['close'] = pd.to_numeric(group['close'], errors='coerce')
            group = group.dropna(subset=['close'])
            
            # 价格特征
            group['returns'] = group['close'].pct_change()
            group['log_returns'] = np.log(group['close'] / group['close'].shift(1))
            group['abs_returns'] = group['returns'].abs()
            
            # 移动平均线
            group['ma_5'] = group['close'].rolling(5).mean()
            group['ma_10'] = group['close'].rolling(10).mean()
            group['ma_20'] = group['close'].rolling(20).mean()
            group['ma_60'] = group['close'].rolling(60).mean()
            group['ma_120'] = group['close'].rolling(120).mean()
            
            # 均线比率
            group['ma5_ma20'] = group['ma_5'] / group['ma_20']
            group['ma20_ma60'] = group['ma_20'] / group['ma_60']
            group['ma60_ma120'] = group['ma_60'] / group['ma_120']
            
            # 波动率
            group['volatility_5'] = group['returns'].rolling(5).std()
            group['volatility_20'] = group['returns'].rolling(20).std()
            group['volatility_60'] = group['returns'].rolling(60).std()
            group['vol_ratio_5_20'] = group['volatility_5'] / group['volatility_20']
            
            # RSI
            group['rsi'] = self._calculate_rsi(group['close'], 14)
            group['rsi_7'] = self._calculate_rsi(group['close'], 7)
            group['rsi_21'] = self._calculate_rsi(group['close'], 21)
            
            # MACD
            ema_12 = group['close'].ewm(span=12).mean()
            ema_26 = group['close'].ewm(span=26).mean()
            group['macd'] = ema_12 - ema_26
            signal = group['macd'].ewm(span=9).mean()
            group['macd_signal'] = signal
            group['macd_hist'] = group['macd'] - signal
            
            # 布林带
            group['boll_mid'] = group['ma_20']
            group['boll_upper'] = group['ma_20'] + 2 * group['close'].rolling(20).std()
            group['boll_lower'] = group['ma_20'] - 2 * group['close'].rolling(20).std()
            group['boll_width'] = (group['boll_upper'] - group['boll_lower']) / group['boll_mid']
            group['boll_pct'] = (group['close'] - group['boll_lower']) / (group['boll_upper'] - group['boll_lower'])
            
            # 成交量特征
            if 'volume' in group.columns:
                group['volume'] = pd.to_numeric(group['volume'], errors='coerce')
                group['volume_ma_5'] = group['volume'].rolling(5).mean()
                group['volume_ma_20'] = group['volume'].rolling(20).mean()
                group['volume_ratio'] = group['volume'] / group['volume_ma_5']
                group['volume_ma_ratio'] = group['volume_ma_5'] / group['volume_ma_20']
                group['volume_change'] = group['volume'].pct_change()
                
            if 'VOLUME' in group.columns:
                group['VOLUME'] = pd.to_numeric(group['VOLUME'], errors='coerce')
                if 'volume' not in group.columns:
                    group['volume'] = group['VOLUME']
                group['volume_ma_5'] = group['VOLUME'].rolling(5).mean()
                group['volume_ratio'] = group['VOLUME'] / group['volume_ma_5']
            
            # 资金流向特征
            group['vwap'] = (group['close'] * group.get('volume', 1)).rolling(5).sum() / group.get('volume', 1).rolling(5).sum()
            group['price_vwap_diff'] = group['close'] - group['vwap']
            group['price_vwap_ratio'] = group['close'] / group['vwap']
            
            # 动量特征
            group['momentum_5'] = group['returns'].rolling(5).sum()
            group['momentum_10'] = group['returns'].rolling(10).sum()
            group['momentum_20'] = group['returns'].rolling(20).sum()
            group['momentum_60'] = group['returns'].rolling(60).sum()
            
            # 趋势强度
            group['trend_5'] = (group['close'] - group['close'].shift(5)) / group['close'].shift(5)
            group['trend_20'] = (group['close'] - group['close'].shift(20)) / group['close'].shift(20)
            group['trend_60'] = (group['close'] - group['close'].shift(60)) / group['close'].shift(60)
            
            # 日内波动特征
            if 'high' in group.columns and 'low' in group.columns:
                group['high'] = pd.to_numeric(group['high'], errors='coerce')
                group['low'] = pd.to_numeric(group['low'], errors='coerce')
                group['range'] = group['high'] - group['low']
                group['range_ratio'] = group['range'] / group['close']
                group['upper_shadow'] = group['high'] - group[['open', 'close']].max(axis=1)
                group['lower_shadow'] = group[['open', 'close']].min(axis=1) - group['low']
            
            if 'open' in group.columns:
                group['open'] = pd.to_numeric(group['open'], errors='coerce')
                group['open_close_diff'] = group['close'] - group['open']
                group['gap'] = group['open'] - group['close'].shift(1)
            
            # 特征交叉
            group['rsi_volatility'] = group['rsi'] * group['volatility_20']
            group['momentum_volatility'] = group['momentum_20'] * group['volatility_20']
            group['macd_rsi'] = group['macd'] * group['rsi']
            group['boll_momentum'] = group['boll_width'] * group['momentum_20']
            group['trend_rsi'] = group['trend_20'] * group['rsi']
            
            # 标签
            group['label_up'] = (group['returns'].shift(-1) > 0).astype(int)
            group['label_return'] = group['returns'].shift(-1)
            group['label_3d_return'] = group['returns'].shift(-3)
            group['label_3d_up'] = (group['label_3d_return'] > 0).astype(int)
            
            features.append(group)
            valid_codes += 1
        
        if not features:
            print('\n[ERROR] 没有有效的数据!')
            return None, None
        
        df_features = pd.concat(features, ignore_index=True)
        
        base_features = [
            'returns', 'log_returns', 'abs_returns',
            'ma5_ma20', 'ma20_ma60', 'ma60_ma120',
            'volatility_5', 'volatility_20', 'volatility_60', 'vol_ratio_5_20',
            'rsi', 'rsi_7', 'rsi_21',
            'macd', 'macd_signal', 'macd_hist',
            'boll_width', 'boll_pct',
            'momentum_5', 'momentum_10', 'momentum_20', 'momentum_60',
            'trend_5', 'trend_20', 'trend_60',
            'vwap', 'price_vwap_diff', 'price_vwap_ratio',
            'label_up', 'label_return', 'label_3d_return', 'label_3d_up'
        ]
        
        additional_features = [
            'volume_ratio', 'volume_ma_ratio', 'volume_change',
            'range', 'range_ratio', 'upper_shadow', 'lower_shadow',
            'open_close_diff', 'gap',
            'rsi_volatility', 'momentum_volatility', 'macd_rsi', 'boll_momentum', 'trend_rsi'
        ]
        
        available_cols = [col for col in base_features if col in df_features.columns]
        for col in additional_features:
            if col in df_features.columns:
                available_cols.append(col)
        
        print(f'[DEBUG] 需要 {len(base_features) + len(additional_features)} 列, 实际有 {len(available_cols)} 列')
        
        df_features = df_features[available_cols]
        df_features = df_features.dropna(subset=available_cols)
        
        self.feature_cols = [col for col in base_features + additional_features if col in df_features.columns and col not in ['label_up', 'label_return', 'label_3d_return', 'label_3d_up']]
        
        print(f'[FEATURE] 使用 {len(self.feature_cols)} 个特征')
        print(f'[FEATURE] 特征列表: {", ".join(self.feature_cols)}')
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
    
    def apply_pca(self, X, n_components=6):
        """应用PCA降维"""
        print(f'\n[PCA] 应用PCA降维, 保留 {n_components} 个主成分...')
        
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        self.pca = PCA(n_components=n_components)
        X_pca = self.pca.fit_transform(X_scaled)
        
        explained_variance = self.pca.explained_variance_ratio_
        print(f'[PCA] 解释方差比: {explained_variance.round(3)}')
        print(f'[PCA] 累计解释方差: {explained_variance.sum():.2%}')
        
        pca_cols = [f'pca_{i+1}' for i in range(n_components)]
        X_pca_df = pd.DataFrame(X_pca, columns=pca_cols, index=X.index)
        
        return X_pca_df, pca_cols
    
    def train_models(self, X_y, feature_cols):
        """训练多个模型并对比"""
        X = X_y[feature_cols]
        
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(0)
        
        if self.use_pca:
            X, feature_cols = self.apply_pca(X, self.pca_components)
            self.feature_cols = feature_cols
        
        print('\n[TRAIN] 划分训练集/测试集 (80/20)...')
        y_primary = X_y['label_up']
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_primary, test_size=0.2, random_state=42, stratify=y_primary
        )
        
        print(f'[DATA] 训练集: {len(X_train)} 样本')
        print(f'[DATA] 测试集: {len(X_test)} 样本')
        
        models = {
            'RandomForest': RandomForestClassifier(
                n_estimators=300, 
                max_depth=12, 
                min_samples_split=5,
                random_state=42,
                n_jobs=-1,
                class_weight='balanced'
            ),
            'GradientBoosting': GradientBoostingClassifier(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                random_state=42
            ),
            'ExtraTrees': ExtraTreesClassifier(
                n_estimators=300,
                max_depth=12,
                random_state=42,
                n_jobs=-1,
                class_weight='balanced'
            ),
            'LogisticRegression': LogisticRegression(
                max_iter=2000,
                random_state=42,
                C=0.5,
                class_weight='balanced'
            ),
            'XGBoost': xgb.XGBClassifier(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                eval_metric='logloss',
                use_label_encoder=False,
                scale_pos_weight=len(y_train[y_train==0])/len(y_train[y_train==1])
            ),
            'LightGBM': lgb.LGBMClassifier(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                class_weight='balanced',
                verbose=-1
            ),
        }
        
        print('\n[TRAIN] 开始训练...')
        print('='*60)
        
        for name, model in models.items():
            print(f'\n[{name}] 训练中...')
            try:
                model.fit(X_train, y_train)
                
                y_pred = model.predict(X_test)
                y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else None
                
                accuracy = accuracy_score(y_test, y_pred)
                f1 = f1_score(y_test, y_pred)
                
                print(f'  [OK] 准确率: {accuracy:.2%}, F1: {f1:.4f}')
                
                if accuracy > 0.55:
                    print(f'  [GOOD] 模型表现优于随机!')
                
                self.models[name] = model
                self.results[name] = {
                    'accuracy': accuracy,
                    'f1': f1,
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
            
            if accuracy > 0.50:
                filename = f'{name}_acc{accuracy:.3f}_f1{result.get("f1", 0):.3f}_{timestamp}.pkl'
                path = os.path.join(self.output_dir, filename)
                joblib.dump(model, path)
                saved_models.append((name, path, accuracy))
                print(f'[SAVE] {name} (准确率{accuracy:.2%}, F1{result.get("f1", 0):.4f}) → {filename}')
        
        if self.use_pca and self.pca is not None:
            pca_path = os.path.join(self.output_dir, f'pca_{self.pca_components}_components_{timestamp}.pkl')
            joblib.dump(self.pca, pca_path)
            print(f'[SAVE] PCA模型 → {pca_path}')
        
        if self.scaler is not None:
            scaler_path = os.path.join(self.output_dir, f'scaler_{timestamp}.pkl')
            joblib.dump(self.scaler, scaler_path)
            print(f'[SAVE] 标准化器 → {scaler_path}')
        
        if not saved_models:
            print('\n[WARN] 没有模型达到保存标准 (准确率>50%)')
        else:
            print(f'\n[OK] 成功保存 {len(saved_models)} 个模型')
        
        return saved_models
    
    def generate_report(self):
        """生成训练报告"""
        print('\n' + '='*70)
        print('增强版训练结果报告')
        print('='*70)
        
        if not self.results:
            print('\n[ERROR] 没有训练结果!')
            return
        
        sorted_results = sorted(
            self.results.items(), 
            key=lambda x: x[1]['accuracy'], 
            reverse=True
        )
        
        print(f'\n{'模型':<20} {'准确率':>10} {'F1分数':>10} {'排名':>6}')
        print('-'*70)
        
        for rank, (name, result) in enumerate(sorted_results, 1):
            accuracy = result['accuracy']
            f1 = result['f1']
            print(f'{name:<20} {accuracy:>9.2%} {f1:>9.4f} {rank:>5}')
        
        best_name, best_result = sorted_results[0]
        best_model = self.models[best_name]
        
        print(f'\n[BEST] 最佳模型: {best_name} (准确率 {best_result["accuracy"]:.2%}, F1 {best_result["f1"]:.4f})')
        print('\n详细分类报告:')
        print(classification_report(
            best_result['y_test'], 
            best_result['y_pred'],
            target_names=['下跌', '上涨']
        ))
        
        if hasattr(best_model, 'feature_importances_') and not self.use_pca:
            print('\n[FEATURE] 特征重要性 (Top 10):')
            importances = best_model.feature_importances_
            indices = np.argsort(importances)[::-1][:10]
            
            for idx in indices:
                feat_name = self.feature_cols[idx]
                feat_imp = importances[idx]
                bar = '█' * int(feat_imp * 200)
                print(f'  {feat_name:<25} {feat_imp:.4f} {bar}')
        
        print('\n' + '='*70)
    
    def save_training_metadata(self, saved_models):
        """保存训练元数据"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        metadata_file = os.path.join(self.output_dir, f'training_metadata_enhanced_{timestamp}.json')
        
        metadata = {
            'timestamp': timestamp,
            'models_trained': list(self.models.keys()),
            'best_model': saved_models[0][0] if saved_models else None,
            'accuracies': {name: result['accuracy'] for name, result in self.results.items()},
            'f1_scores': {name: result['f1'] for name, result in self.results.items()},
            'feature_count': len(self.feature_cols),
            'features': self.feature_cols,
            'model_files': [(name, path, accuracy) for name, path, accuracy in saved_models],
            'use_pca': self.use_pca,
            'pca_components': self.pca_components if self.use_pca else None,
            'pca_explained_variance': self.pca.explained_variance_ratio_.tolist() if (self.use_pca and self.pca is not None) else None
        }
        
        import json
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f'[META] 训练元数据已保存: {metadata_file}')
        return metadata_file


def main():
    """主函数"""
    print('='*70)
    print('增强版量化模型训练系统')
    print('='*70)
    print(f'开始时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    parser = argparse.ArgumentParser(description='增强版量化模型训练')
    parser.add_argument('--pca', action='store_true', help='启用PCA降维')
    parser.add_argument('--pca-components', type=int, default=6, help='PCA主成分数量')
    args = parser.parse_args()
    
    trainer = EnhancedAutoTrainer(
        output_dir='models',
        use_pca=args.pca,
        pca_components=args.pca_components
    )
    
    print('\n【步骤1/5】加载数据')
    print('-'*70)
    df = trainer.load_data()
    if df is None:
        print('\n[ERROR] 数据加载失败,退出训练')
        sys.exit(1)
    
    print('\n【步骤2/5】特征工程 (增强版)')
    print('-'*70)
    X_y, feature_cols = trainer.engineer_features(df)
    if X_y is None:
        print('\n[ERROR] 特征工程失败,退出训练')
        sys.exit(1)
    
    print('\n【步骤3/5】模型训练 (XGBoost/LightGBM)')
    print('-'*70)
    results = trainer.train_models(X_y, feature_cols)
    
    if not results:
        print('\n[ERROR] 模型训练失败,退出训练')
        sys.exit(1)
    
    print('\n【步骤4/5】生成报告')
    print('-'*70)
    trainer.generate_report()
    
    print('\n【步骤5/5】保存模型')
    print('-'*70)
    saved_models = trainer.save_models()
    
    metadata_file = trainer.save_training_metadata(saved_models)
    
    print('\n' + '='*70)
    print('✅ 训练完成!')
    print('='*70)
    print(f'结束时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'保存模型: {len(saved_models)} 个')
    print(f'元数据: {metadata_file}')
    print(f'使用PCA: {"是" if trainer.use_pca else "否"}')
    print()
    
    if saved_models:
        best_name, best_path, best_acc = saved_models[0]
        best_f1 = trainer.results[best_name]['f1']
        print(f'🏆 最佳模型: {best_name} (准确率 {best_acc:.2%}, F1 {best_f1:.4f})')
        print(f'📁 模型路径: {best_path}')
    
    print('='*70)


if __name__ == '__main__':
    import argparse
    main()