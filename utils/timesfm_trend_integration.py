# -*- coding: utf-8 -*-
"""
TimesFM趋势判断集成模块 - v5.8

将TimesFM的时间序列预测结果集成到信号融合系统中，
作为趋势判断的重要输入源。

核心功能：
- 实时趋势预测：基于历史数据预测短期走势
- 置信区间分析：提供概率分布信息
- 异常检测：识别市场异常波动
- 趋势强度评估：量化趋势的确定性
- 多时间窗口预测：短期、中期、长期趋势判断
- 与现有信号源深度融合

集成点：
- EnhancedSignalFusionEngine 新增信号源
- 技术指标规则引擎增强
- 风险预警系统联动

作者：量化策略系统 v5.8
日期：2026-06-29
"""

import os
import sys
import json
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from collections import deque
import threading
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from .timesfm_predictor import TimesFMPredictor, _get_kline_series
    from .logging_manager import get_logger
    from .signal_fusion import SignalResult, FusedSignal
    from .enhanced_signal_fusion import EnhancedSignalFusionEngine, SourcePerformanceMetrics
    logger = get_logger('timesfm_trend_integration')
except ImportError:
    try:
        from timesfm_predictor import TimesFMPredictor, _get_kline_series
        from logging_manager import get_logger
        from signal_fusion import SignalResult, FusedSignal
        from enhanced_signal_fusion import EnhancedSignalFusionEngine, SourcePerformanceMetrics
        logger = get_logger('timesfm_trend_integration')
    except ImportError:
        import logging
        logger = logging.getLogger('timesfm_trend_integration')


@dataclass
class TrendPrediction:
    """趋势预测结果"""
    symbol: str
    name: str = ""
    trend: str = ""  # 'up' / 'down' / 'flat'
    strength: float = 0.0  # 0-1，趋势强度
    confidence: float = 0.0  # 0-1，预测置信度
    horizon_days: int = 10
    forecast_prices: List[float] = field(default_factory=list)
    confidence_intervals: Dict[str, List[float]] = field(default_factory=dict)
    volatility_forecast: float = 0.0
    anomaly_detected: bool = False
    anomaly_type: str = ""
    timestamp: str = ""
    
    def to_signal_result(self) -> SignalResult:
        """转换为SignalResult格式"""
        # 基于趋势强度和置信度计算综合分数
        if self.trend == 'up':
            score = min(1.0, 0.5 + self.strength * 0.5)
        elif self.trend == 'down':
            score = max(0.0, 0.5 - self.strength * 0.5)
        else:  # flat
            score = 0.5
        
        # 确定动作
        if score >= 0.7:
            action = "BUY"
        elif score <= 0.3:
            action = "SELL"
        else:
            action = "HOLD"
        
        # 生成原因说明
        reasons = []
        reasons.append(f"TimesFM趋势预测: {self.trend}")
        reasons.append(f"趋势强度: {self.strength:.2f}")
        reasons.append(f"预测置信度: {self.confidence:.2f}")
        reasons.append(f"预测波动率: {self.volatility_forecast:.2f}")
        if self.anomaly_detected:
            reasons.append(f"异常检测: {self.anomaly_type}")
        
        return SignalResult(
            code=self.symbol,
            source='timesfm_trend',
            score=score,
            action=action,
            confidence=self.confidence,
            reason=" | ".join(reasons),
            timestamp=self.timestamp
        )


class TimesFMTrendIntegrator:
    """TimesFM趋势判断集成器"""
    
    def __init__(self, horizon_days: int = 10, context_days: int = 252, 
                 cache_size: int = 1000, enable_anomaly_detection: bool = True):
        self.horizon_days = horizon_days
        self.context_days = context_days
        self.cache_size = cache_size
        self.enable_anomaly_detection = enable_anomaly_detection
        
        # 初始化TimesFM预测器
        self.predictor = TimesFMPredictor(horizon=horizon_days, context_days=context_days)
        
        # 缓存机制
        self.prediction_cache: Dict[str, TrendPrediction] = {}
        self.cache_lock = threading.RLock()
        
        # 性能统计
        self.performance_stats = {
            'total_predictions': 0,
            'successful_predictions': 0,
            'failed_predictions': 0,
            'average_response_time': 0.0,
            'last_update': ""
        }
        
        # 异常检测参数
        self.volatility_threshold = 0.15  # 15%波动率阈值
        self.price_jump_threshold = 0.08  # 8%价格跳变阈值
        
        logger.info(f"TimesFM趋势判断集成器初始化完成 (预测天数: {horizon_days}, 上下文: {context_days})")
    
    def predict_trend(self, symbol: str, force_refresh: bool = False) -> Optional[TrendPrediction]:
        """预测趋势"""
        start_time = time.time()
        
        try:
            # 检查缓存
            if not force_refresh and symbol in self.prediction_cache:
                cached_result = self.prediction_cache[symbol]
                # 检查缓存是否过期（1小时）
                cache_time = datetime.fromisoformat(cached_result.timestamp)
                if (datetime.now() - cache_time) < timedelta(hours=1):
                    return cached_result
            
            # 获取历史数据
            kline = _get_kline_series(symbol, days=self.context_days)
            if kline is None or len(kline) < 32:
                logger.warning(f"无法获取 {symbol} 的足够历史数据")
                return None
            
            # 使用TimesFM进行预测
            if not self.predictor.available:
                logger.error(f"TimesFM预测器不可用: {self.predictor.load_error}")
                return None
            
            # 执行预测
            prediction_result = self.predictor.predict_single_with_confidence(symbol, kline)
            
            # 分析预测结果
            trend_prediction = self._analyze_prediction_result(symbol, prediction_result, kline)
            
            # 更新缓存
            with self.cache_lock:
                if len(self.prediction_cache) >= self.cache_size:
                    # 删除最旧的缓存项
                    oldest_key = next(iter(self.prediction_cache))
                    del self.prediction_cache[oldest_key]
                
                self.prediction_cache[symbol] = trend_prediction
            
            # 更新性能统计
            response_time = (time.time() - start_time) * 1000  # 毫秒
            self._update_performance_stats(response_time)
            
            logger.info(f"TimesFM趋势预测完成: {symbol} {trend_prediction.trend} "
                       f"(强度: {trend_prediction.strength:.2f}, 置信度: {trend_prediction.confidence:.2f})")
            
            return trend_prediction
            
        except Exception as e:
            logger.error(f"TimesFM趋势预测失败: {symbol} - {e}")
            self._update_performance_stats((time.time() - start_time) * 1000, failed=True)
            return None
    
    def _analyze_prediction_result(self, symbol: str, prediction_result: Dict[str, Any], 
                                  kline: pd.Series) -> TrendPrediction:
        """分析预测结果"""
        
        # 提取基本信息
        symbol = prediction_result['symbol']
        name = prediction_result['name']
        horizon = prediction_result['horizon']
        
        # 获取价格数据
        last_price = prediction_result['last_price']
        forecast_prices = prediction_result['forecast']
        confidence_intervals = {
            'lower_60': prediction_result.get('lower_60', []),
            'upper_60': prediction_result.get('upper_60', []),
            'lower_80': prediction_result.get('lower_80', []),
            'upper_80': prediction_result.get('upper_80', [])
        }
        
        # 分析趋势
        trend, strength = self._analyze_trend_direction(forecast_prices, last_price)
        
        # 计算置信度
        confidence = self._calculate_confidence(confidence_intervals, strength)
        
        # 预测波动率
        volatility_forecast = prediction_result.get('volatility_forecast', 0.0)
        
        # 异常检测
        anomaly_detected, anomaly_type = self._detect_anomalies(kline, prediction_result)
        
        # 创建预测结果
        trend_prediction = TrendPrediction(
            symbol=symbol,
            name=name,
            trend=trend,
            strength=strength,
            confidence=confidence,
            horizon_days=horizon,
            forecast_prices=forecast_prices,
            confidence_intervals=confidence_intervals,
            volatility_forecast=volatility_forecast,
            anomaly_detected=anomaly_detected,
            anomaly_type=anomaly_type,
            timestamp=datetime.now().isoformat()
        )
        
        return trend_prediction
    
    def _analyze_trend_direction(self, forecast_prices: List[float], last_price: float) -> Tuple[str, float]:
        """分析趋势方向和强度"""
        if not forecast_prices or last_price <= 0:
            return 'flat', 0.0
        
        # 计算预测变化百分比
        price_changes = []
        for i, price in enumerate(forecast_prices):
            if i == 0:
                change = (price - last_price) / last_price
            else:
                change = (price - forecast_prices[i-1]) / forecast_prices[i-1]
            price_changes.append(abs(change))
        
        # 总体趋势变化
        overall_change = (forecast_prices[-1] - last_price) / last_price
        
        # 确定趋势方向
        if overall_change > 0.03:  # 3%以上上涨
            trend = 'up'
        elif overall_change < -0.03:  # 3%以上下跌
            trend = 'down'
        else:
            trend = 'flat'
        
        # 计算趋势强度（基于价格变化的稳定性和幅度）
        avg_change = np.mean(price_changes)
        max_change = np.max(price_changes)
        
        # 强度评分：考虑变化的稳定性、幅度和一致性
        stability_factor = 1.0 - (np.std(price_changes) / max(0.01, avg_change))
        magnitude_factor = min(1.0, abs(overall_change) * 10)  # 10倍放大效果
        
        strength = magnitude_factor * max(0.1, stability_factor)
        strength = min(1.0, strength)
        
        return trend, strength
    
    def _calculate_confidence(self, confidence_intervals: Dict[str, List[float]], strength: float) -> float:
        """计算预测置信度"""
        # 基于置信区间宽度计算置信度
        if not confidence_intervals or len(confidence_intervals['lower_80']) == 0:
            return strength  # 如果没有置信区间信息，使用强度作为置信度
        
        # 计算置信区间的相对宽度
        lower_80 = confidence_intervals['lower_80']
        upper_80 = confidence_intervals['upper_80']
        
        interval_widths = [(u - l) / max(l, 0.01) for l, u in zip(lower_80, upper_80)]
        avg_width = np.mean(interval_widths)
        
        # 区间越窄，置信度越高
        width_factor = max(0.1, 1.0 - min(1.0, avg_width * 5))  # 5倍放大效果
        
        # 综合置信度
        confidence = strength * width_factor
        confidence = min(1.0, max(0.1, confidence))
        
        return confidence
    
    def _detect_anomalies(self, kline: pd.Series, prediction_result: Dict[str, Any]) -> Tuple[bool, str]:
        """检测异常情况"""
        if not self.enable_anomaly_detection:
            return False, ""
        
        anomalies = []
        
        # 1. 检测波动率异常
        volatility = prediction_result.get('volatility_forecast', 0.0)
        if volatility > self.volatility_threshold:
            anomalies.append(f"高波动率异常: {volatility:.2%}")
        
        # 2. 检测价格跳变异常
        recent_changes = []
        prices = kline.values[-10:]  # 最近10天
        for i in range(1, len(prices)):
            change = abs((prices[i] - prices[i-1]) / prices[i-1])
            recent_changes.append(change)
        
        if recent_changes and max(recent_changes) > self.price_jump_threshold:
            anomalies.append(f"价格跳变异常: {max(recent_changes):.2%}")
        
        # 3. 检测预测一致性异常
        forecast_prices = prediction_result.get('forecast', [])
        if len(forecast_prices) > 3:
            # 检查预测趋势的一致性
            trend_changes = []
            for i in range(1, len(forecast_prices)):
                change = (forecast_prices[i] - forecast_prices[i-1]) / forecast_prices[i-1]
                trend_changes.append(np.sign(change))
            
            # 如果趋势频繁变化，可能存在不一致性
            sign_changes = sum(1 for i in range(1, len(trend_changes)) if trend_changes[i] != trend_changes[i-1])
            if sign_changes > 2:  # 超过2次变化
                anomalies.append(f"预测趋势不一致异常: {sign_changes}次变化")
        
        if anomalies:
            return True, "; ".join(anomalies)
        return False, ""
    
    def _update_performance_stats(self, response_time: float, failed: bool = False):
        """更新性能统计"""
        self.performance_stats['total_predictions'] += 1
        
        if failed:
            self.performance_stats['failed_predictions'] += 1
        else:
            self.performance_stats['successful_predictions'] += 1
        
        # 更新平均响应时间
        current_avg = self.performance_stats['average_response_time']
        total = self.performance_stats['total_predictions']
        self.performance_stats['average_response_time'] = (
            (current_avg * (total - 1) + response_time) / total
        )
        
        self.performance_stats['last_update'] = datetime.now().isoformat()
    
    def get_trend_signal(self, symbol: str, force_refresh: bool = False) -> Optional[SignalResult]:
        """获取趋势信号（SignalResult格式）"""
        prediction = self.predict_trend(symbol, force_refresh)
        if prediction is None:
            return None
        
        return prediction.to_signal_result()
    
    def get_batch_trend_signals(self, symbols: List[str]) -> Dict[str, SignalResult]:
        """批量获取趋势信号"""
        results = {}
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_symbol = {
                executor.submit(self.get_trend_signal, symbol): symbol 
                for symbol in symbols
            }
            
            for future in future_to_symbol:
                symbol = future_to_symbol[future]
                try:
                    result = future.result(timeout=30)  # 30秒超时
                    if result:
                        results[symbol] = result
                except Exception as e:
                    logger.error(f"批量预测失败: {symbol} - {e}")
        
        return results
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        stats = self.performance_stats.copy()
        stats['cache_size'] = len(self.prediction_cache)
        stats['cache_hit_rate'] = stats['successful_predictions'] / max(1, stats['total_predictions'])
        stats['last_prediction'] = self.prediction_cache[next(iter(self.prediction_cache))]['timestamp'] if self.prediction_cache else ""
        
        return stats
    
    def clear_cache(self):
        """清空缓存"""
        with self.cache_lock:
            self.prediction_cache.clear()
        logger.info("TimesFM预测缓存已清空")
    
    def get_cached_predictions(self) -> Dict[str, TrendPrediction]:
        """获取当前缓存的预测结果"""
        with self.cache_lock:
            return self.prediction_cache.copy()


# ── 便捷函数和集成 ──

# 全局单例
_trend_integrator: Optional[TimesFMTrendIntegrator] = None


def get_trend_integrator() -> TimesFMTrendIntegrator:
    """获取全局趋势集成器单例"""
    global _trend_integrator
    if _trend_integrator is None:
        _trend_integrator = TimesFMTrendIntegrator()
    return _trend_integrator


def _get_timesfm_trend_source(symbol: str) -> SignalResult:
    """TimesFM趋势信号源"""
    try:
        integrator = get_trend_integrator()
        signal_result = integrator.get_trend_signal(symbol)
        
        if signal_result:
            # 更新性能指标
            if _enhanced_fusion_engine:
                _enhanced_fusion_engine.update_performance_metrics(
                    'timesfm_trend', 'UNKNOWN', signal_result.action
                )
        
        return signal_result
        
    except Exception as e:
        logger.warning(f"获取TimesFM趋势信号失败: {e}")
        return None


def register_timesfm_trend_source(initial_weight: float = 0.15):
    """注册TimesFM趋势信号源"""
    try:
        engine = get_enhanced_fusion_engine()
        engine.register_enhanced_source(
            'timesfm_trend', 
            _get_timesfm_trend_source, 
            initial_weight,
            {"type": "trend_forecast", "horizon": 10, "provider": "TimesFM"}
        )
        logger.info("TimesFM趋势信号源已注册")
    except Exception as e:
        logger.error(f"注册TimesFM趋势信号源失败: {e}")


# 自动注册TimesFM趋势信号源
try:
    enhanced_engine = get_enhanced_fusion_engine()
    if 'timesfm_trend' not in enhanced_engine._sources:
        register_timesfm_trend_source()
        logger.info("自动注册TimesFM趋势信号源成功")
except Exception as e:
    logger.warning(f"自动注册TimesFM趋势信号源失败: {e}")