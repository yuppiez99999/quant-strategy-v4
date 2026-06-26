#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
优化版自动化模型训练脚本
支持: SelectKBest特征选择 + GridSearchCV超参数调优 + XGBoost/LightGBM优化
"""

import sys
import os
import io
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, f1_score, roc_auc_score
import xgboost as xgb
import lightgbm as lgb
import joblib

if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

class OptimizedAutoTrainer:
    """优化版自动训练器"""
    
    def __init__(self, output_dir='models'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.models = {}
        self.results = {}
        self.feature_cols = []
        self.selected_features = []
        self.feature_selector = None
        self.scaler = None
    
    def load_data(self, data_dir='data/cache'):
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
                except Exception as e:
                    print(f'  [WARN] {file}: 加载失败 - {e}')
        
        if not all_data:
            print('\n[ERROR] 未找到任何parquet数据文件!')
            return None
        
        combined = pd.concat(all_data, ignore_index=True)
        print(f'\n[DATA] 共加载 {file_count} 个文件, {len(combined)} 条记录')
        return combined
    
    def engineer_features(self, df):
        print('\n[FEATURE] 构建增强特征...')
        
        features = []
        
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
            
            group['returns'] = group['close'].pct_change()
            group['log_returns'] = np.log(group['close'] / group['close'].shift(1))
            group['abs_returns'] = group['returns'].abs()
            
            group['ma_5'] = group['close'].rolling(5).mean()
            group['ma_10'] = group['close'].rolling(10).mean()
            group['ma_20'] = group['close'].rolling(20).mean()
            group['ma_60'] = group['close'].rolling(60).mean()
            group['ma_120'] = group['close'].rolling(120).mean()
            
            group['ma5_ma20'] = group['ma_5'] / group['ma_20']
            group['ma20_ma60'] = group['ma_20'] / group['ma_60']
            group['ma60_ma120'] = group['ma_60'] / group['ma_120']
            
            group['volatility_5'] = group['returns'].rolling(5).std()
            group['volatility_20'] = group['returns'].rolling(20).std()
            group['volatility_60'] = group['returns'].rolling(60).std()
            group['vol_ratio_5_20'] = group['volatility_5'] / group['volatility_20']
            
            group['rsi'] = self._calculate_rsi(group['close'], 14)
            group['rsi_7'] = self._calculate_rsi(group['close'], 7)
            group['rsi_21'] = self._calculate_rsi(group['close'], 21)
            
            ema_12 = group['close'].ewm(span=12).mean()
            ema_26 = group['close'].ewm(span=26).mean()
            group['macd'] = ema_12 - ema_26
            signal = group['macd'].ewm(span=9).mean()
            group['macd_signal'] = signal
            group['macd_hist'] = group['macd'] - signal
            
            group['boll_mid'] = group['ma_20']
            group['boll_upper'] = group['ma_20'] + 2 * group['close'].rolling(20).std()
            group['boll_lower'] = group['ma_20'] - 2 * group['close'].rolling(20).std()
            group['boll_width'] = (group['boll_upper'] - group['boll_lower']) / group['boll_mid']
            group['boll_pct'] = (group['close'] - group['boll_lower']) / (group['boll_upper'] - group['boll_lower'])
            
            if 'volume' in group.columns:
                group['volume'] = pd.to_numeric(group['volume'], errors='coerce')
                group['volume_ma_5'] = group['volume'].rolling(5).mean()
                group['volume_ma_20'] = group['volume'].rolling(20).mean()
                group['volume_ratio'] = group['volume'] / group['volume_ma_5']
                group['volume_ma_ratio'] = group['volume_ma_5'] / group['volume_ma_20']
                group['volume_change'] = group['volume'].pct_change()
            elif 'VOLUME' in group.columns:
                group['VOLUME'] = pd.to_numeric(group['VOLUME'], errors='coerce')
                group['volume'] = group['VOLUME']
                group['volume_ma_5'] = group['VOLUME'].rolling(5).mean()
                group['volume_ratio'] = group['VOLUME'] / group['volume_ma_5']
            
            group['vwap'] = (group['close'] * group.get('volume', 1)).rolling(5).sum() / group.get('volume', 1).rolling(5).sum()
            group['price_vwap_diff'] = group['close'] - group['vwap']
            group['price_vwap_ratio'] = group['close'] / group['vwap']
            
            group['momentum_5'] = group['returns'].rolling(5).sum()
            group['momentum_10'] = group['returns'].rolling(10).sum()
            group['momentum_20'] = group['returns'].rolling(20).sum()
            group['momentum_60'] = group['returns'].rolling(60).sum()
            
            group['trend_5'] = (group['close'] - group['close'].shift(5)) / group['close'].shift(5)
            group['trend_20'] = (group['close'] - group['close'].shift(20)) / group['close'].shift(20)
            group['trend_60'] = (group['close'] - group['close'].shift(60)) / group['close'].shift(60)
            
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
            
            group['rsi_volatility'] = group['rsi'] * group['volatility_20']
            group['momentum_volatility'] = group['momentum_20'] * group['volatility_20']
            group['macd_rsi'] = group['macd'] * group['rsi']
            group['boll_momentum'] = group['boll_width'] * group['momentum_20']
            group['trend_rsi'] = group['trend_20'] * group['rsi']
            
            group['label_up'] = (group['returns'].shift(-1) > 0).astype(int)
            
            features.append(group)
        
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
            'label_up'
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
        
        df_features = df_features[available_cols]
        df_features = df_features.dropna(subset=available_cols)
        
        self.feature_cols = [col for col in base_features + additional_features if col in df_features.columns and col != 'label_up']
        
        print(f'[FEATURE] 使用 {len(self.feature_cols)} 个特征')
        print(f'[DATA] 样本数: {len(df_features)}')
        
        return df_features, self.feature_cols
    
    def _calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def select_features(self, X, y, k=20, method='mutual_info'):
        print(f'\n[FEATURE SELECTION] 使用SelectKBest ({method}), 选择top {k}个特征...')
        
        if method == 'f_classif':
            selector = SelectKBest(score_func=f_classif, k=k)
        else:
            selector = SelectKBest(score_func=mutual_info_classif, k=k)
        
        X_selected = selector.fit_transform(X, y)
        
        selected_indices = selector.get_support(indices=True)
        self.selected_features = [self.feature_cols[i] for i in selected_indices]
        
        print(f'[FEATURE SELECTION] 选择的特征: {", ".join(self.selected_features)}')
        
        scores = selector.scores_
        feature_scores = sorted(
            zip(self.feature_cols, scores), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        print('\n[FEATURE SELECTION] 特征评分排名 (Top 15):')
        for i, (feat, score) in enumerate(feature_scores[:15], 1):
            is_selected = '★' if feat in self.selected_features else ' '
            print(f'  {is_selected} {i:2d}. {feat:<25} {score:.4f}')
        
        self.feature_selector = selector
        
        return X_selected
    
    def train_baseline_models(self, X, y):
        print('\n[TRAIN] 训练基准模型...')
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        baseline_models = {
            'GradientBoosting': GradientBoostingClassifier(
                n_estimators=300, max_depth=6, learning_rate=0.05, random_state=42
            ),
            'ExtraTrees': ExtraTreesClassifier(
                n_estimators=300, max_depth=12, random_state=42, n_jobs=-1, class_weight='balanced'
            ),
            'LogisticRegression': LogisticRegression(
                max_iter=2000, random_state=42, C=0.5, class_weight='balanced'
            ),
        }
        
        results = {}
        for name, model in baseline_models.items():
            print(f'\n[{name}] 训练中...')
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred)
            roc_auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]) if hasattr(model, 'predict_proba') else 0
            
            print(f'  [OK] 准确率: {accuracy:.2%}, F1: {f1:.4f}, AUC: {roc_auc:.4f}')
            self.models[name] = model
            results[name] = {'accuracy': accuracy, 'f1': f1, 'auc': roc_auc}
        
        return results
    
    def tune_xgboost(self, X, y):
        print('\n[GRID SEARCH] XGBoost超参数调优...')
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        param_grid = {
            'max_depth': [4, 5],
            'learning_rate': [0.05],
            'n_estimators': [200],
            'subsample': [0.8],
            'colsample_bytree': [0.8],
            'reg_lambda': [1.0],
            'min_child_weight': [1],
        }
        
        base_model = xgb.XGBClassifier(
            random_state=42,
            eval_metric='logloss',
            use_label_encoder=False,
            scale_pos_weight=len(y_train[y_train==0])/len(y_train[y_train==1])
        )
        
        skf = StratifiedKFold(n_splits=2, shuffle=True, random_state=42)
        grid_search = GridSearchCV(
            estimator=base_model,
            param_grid=param_grid,
            cv=skf,
            scoring='f1',
            n_jobs=1,
            verbose=1
        )
        
        grid_search.fit(X_train, y_train)
        
        print(f'\n[GRID SEARCH] XGBoost最佳参数: {grid_search.best_params_}')
        print(f'[GRID SEARCH] XGBoost最佳交叉验证F1: {grid_search.best_score_:.4f}')
        
        best_model = grid_search.best_estimator_
        y_pred = best_model.predict(X_test)
        y_prob = best_model.predict_proba(X_test)[:, 1]
        
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        roc_auc = roc_auc_score(y_test, y_prob)
        
        print(f'[GRID SEARCH] XGBoost测试集: 准确率 {accuracy:.2%}, F1 {f1:.4f}, AUC {roc_auc:.4f}')
        
        return best_model, {
            'accuracy': accuracy, 'f1': f1, 'auc': roc_auc,
            'params': grid_search.best_params_
        }
    
    def tune_lightgbm(self, X, y):
        print('\n[GRID SEARCH] LightGBM超参数调优...')
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        param_grid = {
            'max_depth': [4, 5],
            'learning_rate': [0.05],
            'n_estimators': [200],
            'subsample': [0.8],
            'colsample_bytree': [0.8],
            'reg_alpha': [0.1],
            'reg_lambda': [1.0],
            'min_child_samples': [20],
        }
        
        base_model = lgb.LGBMClassifier(
            random_state=42,
            class_weight='balanced',
            verbose=-1
        )
        
        skf = StratifiedKFold(n_splits=2, shuffle=True, random_state=42)
        grid_search = GridSearchCV(
            estimator=base_model,
            param_grid=param_grid,
            cv=skf,
            scoring='f1',
            n_jobs=1,
            verbose=1
        )
        
        grid_search.fit(X_train, y_train)
        
        print(f'\n[GRID SEARCH] LightGBM最佳参数: {grid_search.best_params_}')
        print(f'[GRID SEARCH] LightGBM最佳交叉验证F1: {grid_search.best_score_:.4f}')
        
        best_model = grid_search.best_estimator_
        y_pred = best_model.predict(X_test)
        y_prob = best_model.predict_proba(X_test)[:, 1]
        
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        roc_auc = roc_auc_score(y_test, y_prob)
        
        print(f'[GRID SEARCH] LightGBM测试集: 准确率 {accuracy:.2%}, F1 {f1:.4f}, AUC {roc_auc:.4f}')
        
        return best_model, {
            'accuracy': accuracy, 'f1': f1, 'auc': roc_auc,
            'params': grid_search.best_params_
        }
    
    def save_models(self, saved_items):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for name, model, result in saved_items:
            accuracy = result.get('accuracy', 0)
            f1 = result.get('f1', 0)
            filename = f'{name}_acc{accuracy:.3f}_f1{f1:.3f}_{timestamp}.pkl'
            path = os.path.join(self.output_dir, filename)
            joblib.dump(model, path)
            print(f'[SAVE] {name} → {filename}')
        
        if self.feature_selector is not None:
            selector_path = os.path.join(self.output_dir, f'feature_selector_{timestamp}.pkl')
            joblib.dump(self.feature_selector, selector_path)
            print(f'[SAVE] 特征选择器 → {selector_path}')
        
        return saved_items
    
    def generate_report(self, results):
        print('\n' + '='*70)
        print('优化版训练结果报告')
        print('='*70)
        
        sorted_results = sorted(
            results.items(), 
            key=lambda x: x[1]['accuracy'], 
            reverse=True
        )
        
        print(f'\n{'模型':<20} {'准确率':>10} {'F1分数':>10} {'AUC':>10}')
        print('-'*70)
        
        for name, result in sorted_results:
            accuracy = result['accuracy']
            f1 = result['f1']
            auc = result.get('auc', 0)
            print(f'{name:<20} {accuracy:>9.2%} {f1:>9.4f} {auc:>9.4f}')
        
        best_name, best_result = sorted_results[0]
        print(f'\n[BEST] 最佳模型: {best_name} (准确率 {best_result["accuracy"]:.2%}, F1 {best_result["f1"]:.4f})')
        
        if 'params' in best_result:
            print('\n[BEST PARAMS] 最佳参数:')
            for k, v in best_result['params'].items():
                print(f'  {k}: {v}')
        
        print('\n' + '='*70)
    
    def save_training_metadata(self, results):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        metadata_file = os.path.join(self.output_dir, f'training_metadata_optimized_{timestamp}.json')
        
        metadata = {
            'timestamp': timestamp,
            'models_trained': list(results.keys()),
            'best_model': max(results, key=lambda x: results[x]['accuracy']),
            'results': {
                name: {
                    'accuracy': result['accuracy'],
                    'f1': result['f1'],
                    'auc': result.get('auc', 0),
                    'params': result.get('params', {})
                } for name, result in results.items()
            },
            'feature_count': len(self.selected_features),
            'features': self.selected_features,
            'total_features_before_selection': len(self.feature_cols)
        }
        
        import json
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f'[META] 训练元数据已保存: {metadata_file}')
        return metadata_file


def main():
    print('='*70)
    print('优化版量化模型训练系统')
    print('='*70)
    print(f'开始时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    trainer = OptimizedAutoTrainer(output_dir='models')
    
    print('\n【步骤1/6】加载数据')
    print('-'*70)
    df = trainer.load_data()
    if df is None:
        print('\n[ERROR] 数据加载失败,退出训练')
        sys.exit(1)
    
    print('\n【步骤2/6】特征工程')
    print('-'*70)
    X_y, feature_cols = trainer.engineer_features(df)
    if X_y is None:
        print('\n[ERROR] 特征工程失败,退出训练')
        sys.exit(1)
    
    X = X_y[feature_cols]
    y = X_y['label_up']
    
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0)
    
    print('\n【步骤3/6】特征选择 (SelectKBest)')
    print('-'*70)
    X_selected = trainer.select_features(X, y, k=20)
    
    print('\n【步骤4/6】训练基准模型')
    print('-'*70)
    baseline_results = trainer.train_baseline_models(X_selected, y)
    
    print('\n【步骤5/6】超参数调优 (XGBoost + LightGBM)')
    print('-'*70)
    xgb_model, xgb_result = trainer.tune_xgboost(X_selected, y)
    lgb_model, lgb_result = trainer.tune_lightgbm(X_selected, y)
    
    all_results = {**baseline_results, 'XGBoost_tuned': xgb_result, 'LightGBM_tuned': lgb_result}
    
    print('\n【步骤6/6】生成报告 & 保存模型')
    print('-'*70)
    trainer.generate_report(all_results)
    
    saved_items = [
        ('GradientBoosting', trainer.models.get('GradientBoosting'), baseline_results['GradientBoosting']),
        ('ExtraTrees', trainer.models.get('ExtraTrees'), baseline_results['ExtraTrees']),
        ('LogisticRegression', trainer.models.get('LogisticRegression'), baseline_results['LogisticRegression']),
        ('XGBoost_tuned', xgb_model, xgb_result),
        ('LightGBM_tuned', lgb_model, lgb_result),
    ]
    
    saved_items = [item for item in saved_items if item[1] is not None]
    trainer.save_models(saved_items)
    trainer.save_training_metadata(all_results)
    
    print('\n' + '='*70)
    print('✅ 训练完成!')
    print('='*70)
    print(f'结束时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    best_name = max(all_results, key=lambda x: all_results[x]['accuracy'])
    best_result = all_results[best_name]
    print(f'🏆 最佳模型: {best_name} (准确率 {best_result["accuracy"]:.2%}, F1 {best_result["f1"]:.4f})')
    
    print('='*70)


if __name__ == '__main__':
    main()