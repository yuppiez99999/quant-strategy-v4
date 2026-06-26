# -*- coding: utf-8 -*-
"""
ML 模型预测模块 - 集成训练好的量化模型
提供特征工程、模型加载、涨跌预测、信号生成功能

最佳模型: GradientBoosting (F1: 0.628, 准确率: 56.01%)
备选模型: XGBoost_tuned / LightGBM_tuned
低延迟模型: LogisticRegression (PCA版, 8维)
"""

import os
import sys
import json
import glob
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any


class MLFeatureEngineer:
    """ML 特征工程 - 与训练脚本一致的特征构建逻辑"""

    def __init__(self):
        self.feature_cols = []

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        构建增强版特征（42个特征，与训练脚本一致）
        
        Args:
            df: 包含 OHLCV 的K线数据 DataFrame
            
        Returns:
            包含所有特征的 DataFrame
        """
        data = df.copy()
        
        if 'close' not in data.columns:
            raise ValueError("DataFrame 必须包含 'close' 列")
        
        data['close'] = pd.to_numeric(data['close'], errors='coerce')
        data = data.dropna(subset=['close'])
        
        # 价格特征
        data['returns'] = data['close'].pct_change()
        data['log_returns'] = np.log(data['close'] / data['close'].shift(1))
        data['abs_returns'] = data['returns'].abs()
        
        # 移动平均线
        data['ma_5'] = data['close'].rolling(5).mean()
        data['ma_10'] = data['close'].rolling(10).mean()
        data['ma_20'] = data['close'].rolling(20).mean()
        data['ma_60'] = data['close'].rolling(60).mean()
        data['ma_120'] = data['close'].rolling(120).mean()
        
        # 均线比率
        data['ma5_ma20'] = data['ma_5'] / data['ma_20']
        data['ma20_ma60'] = data['ma_20'] / data['ma_60']
        data['ma60_ma120'] = data['ma_60'] / data['ma_120']
        
        # 波动率
        data['volatility_5'] = data['returns'].rolling(5).std()
        data['volatility_20'] = data['returns'].rolling(20).std()
        data['volatility_60'] = data['returns'].rolling(60).std()
        data['vol_ratio_5_20'] = data['volatility_5'] / data['volatility_20']
        
        # RSI
        data['rsi'] = self._calculate_rsi(data['close'], 14)
        data['rsi_7'] = self._calculate_rsi(data['close'], 7)
        data['rsi_21'] = self._calculate_rsi(data['close'], 21)
        
        # MACD
        ema_12 = data['close'].ewm(span=12).mean()
        ema_26 = data['close'].ewm(span=26).mean()
        data['macd'] = ema_12 - ema_26
        signal = data['macd'].ewm(span=9).mean()
        data['macd_signal'] = signal
        data['macd_hist'] = data['macd'] - signal
        
        # 布林带
        data['boll_mid'] = data['ma_20']
        data['boll_upper'] = data['ma_20'] + 2 * data['close'].rolling(20).std()
        data['boll_lower'] = data['ma_20'] - 2 * data['close'].rolling(20).std()
        data['boll_width'] = (data['boll_upper'] - data['boll_lower']) / data['boll_mid']
        data['boll_pct'] = (data['close'] - data['boll_lower']) / (data['boll_upper'] - data['boll_lower'])
        
        # 成交量特征
        if 'volume' in data.columns:
            data['volume'] = pd.to_numeric(data['volume'], errors='coerce')
            data['volume_ma_5'] = data['volume'].rolling(5).mean()
            data['volume_ma_20'] = data['volume'].rolling(20).mean()
            data['volume_ratio'] = data['volume'] / data['volume_ma_5']
            data['volume_ma_ratio'] = data['volume_ma_5'] / data['volume_ma_20']
            data['volume_change'] = data['volume'].pct_change()
        
        if 'VOLUME' in data.columns:
            data['VOLUME'] = pd.to_numeric(data['VOLUME'], errors='coerce')
            if 'volume' not in data.columns:
                data['volume'] = data['VOLUME']
            data['volume_ma_5'] = data['VOLUME'].rolling(5).mean()
            data['volume_ratio'] = data['VOLUME'] / data['volume_ma_5']
        
        # 资金流向特征 (VWAP)
        vol = data.get('volume', pd.Series(1, index=data.index))
        data['vwap'] = (data['close'] * vol).rolling(5).sum() / vol.rolling(5).sum()
        data['price_vwap_diff'] = data['close'] - data['vwap']
        data['price_vwap_ratio'] = data['close'] / data['vwap']
        
        # 动量特征
        data['momentum_5'] = data['returns'].rolling(5).sum()
        data['momentum_10'] = data['returns'].rolling(10).sum()
        data['momentum_20'] = data['returns'].rolling(20).sum()
        data['momentum_60'] = data['returns'].rolling(60).sum()
        
        # 趋势强度
        data['trend_5'] = (data['close'] - data['close'].shift(5)) / data['close'].shift(5)
        data['trend_20'] = (data['close'] - data['close'].shift(20)) / data['close'].shift(20)
        data['trend_60'] = (data['close'] - data['close'].shift(60)) / data['close'].shift(60)
        
        # 日内波动特征
        if 'high' in data.columns and 'low' in data.columns:
            data['high'] = pd.to_numeric(data['high'], errors='coerce')
            data['low'] = pd.to_numeric(data['low'], errors='coerce')
            data['range'] = data['high'] - data['low']
            data['range_ratio'] = data['range'] / data['close']
            data['upper_shadow'] = data['high'] - data[['open', 'close']].max(axis=1)
            data['lower_shadow'] = data[['open', 'close']].min(axis=1) - data['low']
        
        if 'open' in data.columns:
            data['open'] = pd.to_numeric(data['open'], errors='coerce')
            data['open_close_diff'] = data['close'] - data['open']
            data['gap'] = data['open'] - data['close'].shift(1)
        
        # 特征交叉
        data['rsi_volatility'] = data['rsi'] * data['volatility_20']
        data['momentum_volatility'] = data['momentum_20'] * data['volatility_20']
        data['macd_rsi'] = data['macd'] * data['rsi']
        data['boll_momentum'] = data['boll_width'] * data['momentum_20']
        data['trend_rsi'] = data['trend_20'] * data['rsi']
        
        return data

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def get_feature_vector(self, df: pd.DataFrame, feature_list: List[str]) -> np.ndarray:
        """
        获取最新一行的特征向量（用于单样本预测）
        
        Args:
            df: 包含所有特征的 DataFrame
            feature_list: 需要的特征列名列表
            
        Returns:
            特征向量 (1, n_features)
        """
        # 确保所有需要的特征列都存在
        available_features = [f for f in feature_list if f in df.columns]
        if len(available_features) < len(feature_list):
            missing = set(feature_list) - set(available_features)
            print(f"[WARN] 缺失特征: {missing}")
        
        # 取最后一行有效数据
        last_row = df[available_features].dropna().iloc[-1:]
        return last_row.values


class MLModelPredictor:
    """ML 模型预测器 - 加载训练好的模型并生成预测信号"""

    def __init__(self, model_dir: str = 'models'):
        self.model_dir = model_dir
        self.models = {}
        self.metadata = {}
        self.feature_engineer = MLFeatureEngineer()
        self.feature_selector = None
        self.scaler = None
        self.pca = None
        self.selected_features = []
        self._loaded = False

    def auto_discover(self) -> bool:
        """
        自动发现并加载最佳模型
        
        Returns:
            是否成功加载
        """
        # 查找最新的优化版元数据
        meta_pattern = os.path.join(self.model_dir, 'training_metadata_optimized_*.json')
        meta_files = sorted(glob.glob(meta_pattern), reverse=True)
        
        if meta_files:
            return self._load_optimized(meta_files[0])
        
        # 回退到增强版
        meta_pattern = os.path.join(self.model_dir, 'training_metadata_enhanced_*.json')
        meta_files = sorted(glob.glob(meta_pattern), reverse=True)
        if meta_files:
            return self._load_enhanced(meta_files[0])
        
        # 回退到基础版
        meta_pattern = os.path.join(self.model_dir, 'training_metadata_*.json')
        meta_files = sorted(glob.glob(meta_pattern), reverse=True)
        if meta_files:
            return self._load_basic(meta_files[0])
        
        print("[ML] 未找到训练元数据")
        return False

    def _load_optimized(self, meta_path: str) -> bool:
        """加载优化版模型（含特征选择）"""
        print(f"[ML] 加载优化版模型: {os.path.basename(meta_path)}")
        
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        
        self.metadata = meta
        self.selected_features = meta.get('features', [])
        best_model_name = meta.get('best_model', 'GradientBoosting')
        
        # 加载特征选择器
        ts = meta.get('timestamp', '')
        selector_path = os.path.join(self.model_dir, f'feature_selector_{ts}.pkl')
        if os.path.exists(selector_path):
            self.feature_selector = joblib.load(selector_path)
            print(f"[ML] 特征选择器已加载: {os.path.basename(selector_path)}")
        
        # 加载最佳模型
        model_pattern = os.path.join(self.model_dir, f'{best_model_name}_*.pkl')
        model_files = sorted(glob.glob(model_pattern), reverse=True)
        
        if model_files:
            self.models[best_model_name] = joblib.load(model_files[0])
            print(f"[ML] 最佳模型已加载: {best_model_name}")
            print(f"[ML]   准确率: {meta['results'][best_model_name]['accuracy']:.2%}")
            print(f"[ML]   F1分数: {meta['results'][best_model_name]['f1']:.4f}")
            self._loaded = True
            return True
        
        print(f"[ML] 未找到模型文件: {best_model_name}")
        return False

    def _load_enhanced(self, meta_path: str) -> bool:
        """加载增强版模型"""
        print(f"[ML] 加载增强版模型: {os.path.basename(meta_path)}")
        
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        
        self.metadata = meta
        best_model_name = meta.get('best_model', 'GradientBoosting')
        
        # 查找最佳模型文件
        model_pattern = os.path.join(self.model_dir, f'{best_model_name}_*.pkl')
        model_files = sorted(glob.glob(model_pattern), reverse=True)
        
        if model_files:
            self.models[best_model_name] = joblib.load(model_files[0])
            self.selected_features = meta.get('feature_cols', [])
            print(f"[ML] 最佳模型已加载: {best_model_name}")
            self._loaded = True
            return True
        
        return False

    def _load_basic(self, meta_path: str) -> bool:
        """加载基础版模型"""
        print(f"[ML] 加载基础版模型: {os.path.basename(meta_path)}")
        
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        
        self.metadata = meta
        best_model_name = meta.get('best_model', 'ExtraTrees')
        
        model_pattern = os.path.join(self.model_dir, f'{best_model_name}_*.pkl')
        model_files = sorted(glob.glob(model_pattern), reverse=True)
        
        if model_files:
            self.models[best_model_name] = joblib.load(model_files[0])
            self.selected_features = meta.get('feature_cols', [])
            print(f"[ML] 最佳模型已加载: {best_model_name}")
            self._loaded = True
            return True
        
        return False

    def predict(self, kline_df: pd.DataFrame, model_name: str = None) -> Optional[Dict[str, Any]]:
        """
        对单只标的进行涨跌预测
        
        Args:
            kline_df: K线数据 DataFrame（需包含 close, 可选 open/high/low/volume）
            model_name: 指定模型名，None则使用最佳模型
            
        Returns:
            预测结果字典，包含:
            - prediction: 预测方向 (1=上涨, 0=下跌)
            - probability: 上涨概率
            - signal: 信号强度 (-1~1)
            - confidence: 置信度
        """
        if not self._loaded:
            if not self.auto_discover():
                return None
        
        if model_name is None:
            model_name = self.metadata.get('best_model', 'GradientBoosting')
        
        if model_name not in self.models:
            print(f"[ML] 模型未加载: {model_name}")
            return None
        
        model = self.models[model_name]
        
        # 构建特征
        feat_df = self.feature_engineer.build_features(kline_df)
        
        # 确保需要的特征列存在
        available_features = [f for f in self.selected_features if f in feat_df.columns]
        if len(available_features) < len(self.selected_features) * 0.5:
            print(f"[ML] 特征不足: 需要 {len(self.selected_features)}, 可用 {len(available_features)}")
            return None
        
        # 去除NaN行
        feat_clean = feat_df[available_features].dropna()
        if len(feat_clean) == 0:
            print("[ML] 无有效特征数据")
            return None
        
        # 取最后一行做预测
        X = feat_clean.iloc[-1:].values
        
        # 预测
        try:
            pred = model.predict(X)[0]
            prob = model.predict_proba(X)[0]
            up_prob = prob[1] if len(prob) > 1 else prob[0]
            
            # 信号强度: 0~1 映射到 -1~1
            signal = (up_prob - 0.5) * 2
            
            # 置信度: 概率离 0.5 越远越置信
            confidence = abs(up_prob - 0.5) * 2
            
            return {
                'prediction': int(pred),
                'direction': '上涨' if pred == 1 else '下跌',
                'probability': float(up_prob),
                'signal': float(signal),
                'confidence': float(confidence),
                'model': model_name,
            }
        except Exception as e:
            print(f"[ML] 预测失败: {e}")
            return None

    def batch_predict(self, kline_dict: Dict[str, pd.DataFrame], 
                      model_name: str = None,
                      top_n: int = 10) -> List[Dict[str, Any]]:
        """
        批量预测多只标的
        
        Args:
            kline_dict: {code: kline_df} 字典
            model_name: 指定模型
            top_n: 返回前N只最强信号
            
        Returns:
            按信号强度排序的预测结果列表
        """
        results = []
        
        for code, df in kline_dict.items():
            pred = self.predict(df, model_name)
            if pred:
                pred['code'] = code
                results.append(pred)
        
        # 按上涨概率排序
        results.sort(key=lambda x: x['probability'], reverse=True)
        
        return results[:top_n]

    def generate_trading_signals(self, kline_dict: Dict[str, pd.DataFrame],
                                  threshold: float = 0.55) -> Dict[str, Any]:
        """
        生成交易信号
        
        Args:
            kline_dict: {code: kline_df} 字典
            threshold: 买入信号阈值（上涨概率 > threshold）
            
        Returns:
            信号字典，包含 buy/sell/hold 列表
        """
        predictions = self.batch_predict(kline_dict, top_n=len(kline_dict))
        
        buy_signals = []
        sell_signals = []
        hold_signals = []
        
        for pred in predictions:
            code = pred['code']
            prob = pred['probability']
            
            if prob > threshold:
                buy_signals.append({
                    'code': code,
                    'probability': prob,
                    'confidence': pred['confidence'],
                    'signal_strength': pred['signal'],
                })
            elif prob < (1 - threshold):
                sell_signals.append({
                    'code': code,
                    'probability': prob,
                    'confidence': pred['confidence'],
                    'signal_strength': pred['signal'],
                })
            else:
                hold_signals.append({
                    'code': code,
                    'probability': prob,
                    'confidence': pred['confidence'],
                })
        
        return {
            'buy': buy_signals,
            'sell': sell_signals,
            'hold': hold_signals,
            'threshold': threshold,
            'total': len(predictions),
            'model': self.metadata.get('best_model', 'unknown'),
            'model_accuracy': self.metadata.get('results', {}).get(
                self.metadata.get('best_model', ''), {}
            ).get('accuracy', 0),
        }

    def get_model_info(self) -> Dict[str, Any]:
        """获取当前加载的模型信息"""
        if not self._loaded:
            return {'loaded': False}
        
        best_model = self.metadata.get('best_model', 'unknown')
        result = self.metadata.get('results', {}).get(best_model, {})
        
        return {
            'loaded': True,
            'best_model': best_model,
            'accuracy': result.get('accuracy', 0),
            'f1': result.get('f1', 0),
            'auc': result.get('auc', 0),
            'feature_count': len(self.selected_features),
            'features': self.selected_features,
            'timestamp': self.metadata.get('timestamp', ''),
        }


def run_ml_signal_scan(codes: List[str] = None, 
                        data_dir: str = 'data/cache',
                        model_dir: str = 'models',
                        threshold: float = 0.55) -> Dict[str, Any]:
    """
    运行 ML 信号扫描（便捷函数）
    
    Args:
        codes: 股票代码列表，None则扫描所有数据
        data_dir: K线数据目录
        model_dir: 模型目录
        threshold: 信号阈值
        
    Returns:
        扫描结果
    """
    predictor = MLModelPredictor(model_dir=model_dir)
    if not predictor.auto_discover():
        return {'error': '模型加载失败'}
    
    # 加载数据
    kline_dict = {}
    for f in os.listdir(data_dir):
        if not f.startswith('kline_') or not f.endswith('.parquet'):
            continue
        
        code = f.replace('kline_', '').replace('_daily.parquet', '')
        
        if codes and code not in codes:
            continue
        
        try:
            df = pd.read_parquet(os.path.join(data_dir, f))
            kline_dict[code] = df
        except Exception as e:
            print(f"[ML] 加载 {code} 失败: {e}")
    
    if not kline_dict:
        return {'error': '无有效K线数据'}
    
    # 生成信号
    signals = predictor.generate_trading_signals(kline_dict, threshold=threshold)
    
    return {
        'model_info': predictor.get_model_info(),
        'signals': signals,
        'scanned_count': len(kline_dict),
    }


if __name__ == '__main__':
    result = run_ml_signal_scan()
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
