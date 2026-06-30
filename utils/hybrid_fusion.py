# -*- coding: utf-8 -*-
"""
混合信号融合引擎 - 快速响应层集成

将快速技术指标信号与现有的ML模型、AI系统融合，
实现毫秒级响应的同时保持系统复杂性。

主要功能：
- 快速信号路由
- 智能策略选择
- 性能监控
- 故障恢复
- 动态权重调整

集成点：
- SignalFusionEngine 快速信号源
- RuleEngine 决策逻辑
- FastSignalProcessor 技术指标计算
"""

import os
import sys
import json
import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor
import asyncio

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from .signal_fusion import SignalFusionEngine, SignalResult, FusedSignal
    from .fast_signal_processor import FastSignalProcessor, FastSignal, generate_fast_signals
    from .rule_engine import RuleEngine, DecisionContext, Action, evaluate_trading_decision
    from .logging_manager import get_logger
    logger = get_logger('hybrid_fusion')
except ImportError:
    import logging
    logger = logging.getLogger('hybrid_fusion')


@dataclass
class HybridSignal:
    """混合信号"""
    code: str
    name: str = ""
    source: str  # 'fast' / 'ml' / 'ai_hedge' / 'glm5'
    action: str  # 'BUY' / 'SELL' / 'HOLD'
    confidence: float  # 0-1
    score: float  # 0-1
    latency: float  # 毫秒
    timestamp: str = ""
    fast_signal: Optional[FastSignal] = None
    technical_indicators: Dict[str, float] = field(default_factory=dict)
    reasoning: str = ""


@dataclass
class FusionConfig:
    """融合配置"""
    # 快速信号配置
    fast_signal_enabled: bool = True
    fast_signal_threshold: float = 0.6  # 快速信号置信度阈值
    fast_signal_strategy: str = "balanced"  # 快速信号策略
    fast_signal_cache_ttl: int = 60  # 缓存TTL(秒)
    
    # 混合模式配置
    hybrid_enabled: bool = True
    hybrid_timeout: int = 1000  # 毫秒
    fallback_to_ml: bool = True
    
    # 性能配置
    max_workers: int = 4
    batch_size: int = 50
    
    # 风险管理配置
    risk_management_enabled: bool = True
    position_limit: float = 0.15  # 单只股票持仓限制
    stop_loss_threshold: float = -0.10  # 止损阈值
    take_profit_threshold: float = 0.20  # 止盈阈值
    
    # 动态权重配置
    weight_adjustment_enabled: bool = True
    weight_adjustment_period: int = 300  # 权重调整周期(秒)
    fast_signal_weight: float = 0.3  # 快速信号初始权重
    ml_signal_weight: float = 0.4  # ML信号权重
    ai_signal_weight: float = 0.3  # AI信号权重


class HybridFusionEngine:
    """混合信号融合引擎"""
    
    def __init__(self, config: FusionConfig = None):
        """
        初始化混合信号融合引擎
        
        Args:
            config: 融合配置
        """
        self.config = config or FusionConfig()
        
        # 初始化组件
        self.signal_fusion = SignalFusionEngine()
        self.fast_processor = FastSignalProcessor(
            cache_ttl=self.config.fast_signal_cache_ttl,
            max_workers=self.config.max_workers
        )
        self.rule_engine = RuleEngine()
        
        # 性能监控
        self.performance_stats = {
            'total_requests': 0,
            'fast_signals': 0,
            'hybrid_signals': 0,
            'fallback_signals': 0,
            'avg_latency': 0.0,
            'last_updated': time.time()
        }
        
        # 动态权重
        self.dynamic_weights = {
            'fast_signal': self.config.fast_signal_weight,
            'ml_signal': self.config.ml_signal_weight,
            'ai_signal': self.config.ai_signal_weight
        }
        
        # 缓存和状态
        self.signal_cache = {}
        self.cache_lock = threading.RLock()
        self.weight_lock = threading.RLock()
        
        # 初始化信号源
        self._init_signal_sources()
        
        logger.info("混合信号融合引擎初始化完成")
    
    def _init_signal_sources(self):
        """初始化信号源"""
        # 注册快速信号源
        if self.config.fast_signal_enabled:
            self.signal_fusion.register_source(
                'fast_technical',
                self._get_fast_signal,
                initial_weight=self.config.fast_signal_weight
            )
        
        # 注册其他信号源（假设已存在）
        self.signal_fusion.register_source(
            'ml',
            self._get_ml_signal,
            initial_weight=self.config.ml_signal_weight
        )
        
        self.signal_fusion.register_source(
            'ai_hedge',
            self._get_ai_hedge_signal,
            initial_weight=self.config.ai_signal_weight
        )
        
        logger.info(f"已注册信号源: {list(self.signal_fusion._sources.keys())}")
    
    def get_hybrid_signal(self, code: str, name: str = "", force_hybrid: bool = False) -> HybridSignal:
        """
        获取混合信号
        
        Args:
            code: 股票代码
            name: 股票名称
            force_hybrid: 是否强制混合模式
            
        Returns:
            HybridSignal: 混合信号
        """
        start_time = time.time()
        
        try:
            # 1. 首先尝试快速信号
            if self.config.fast_signal_enabled and not force_hybrid:
                fast_signal = self._get_fast_signal(code)
                if fast_signal and fast_signal.confidence >= self.config.fast_signal_threshold:
                    latency = (time.time() - start_time) * 1000
                    self._update_performance_stats('fast', latency)
                    
                    return HybridSignal(
                        code=code,
                        name=name,
                        source='fast',
                        action=fast_signal.action,
                        confidence=fast_signal.confidence,
                        score=self._calculate_fast_score(fast_signal),
                        latency=latency,
                        timestamp=datetime.now().isoformat(),
                        fast_signal=fast_signal,
                        technical_indicators=fast_signal.indicators,
                        reasoning="快速信号满足置信度阈值"
                    )
            
            # 2. 混合模式
            if self.config.hybrid_enabled:
                hybrid_signal = self._generate_hybrid_signal(code, name)
                if hybrid_signal:
                    latency = (time.time() - start_time) * 1000
                    self._update_performance_stats('hybrid', latency)
                    
                    return hybrid_signal
            
            # 3. 回退到ML信号
            if self.config.fallback_to_ml:
                ml_signal = self._get_ml_signal(code)
                if ml_signal:
                    latency = (time.time() - start_time) * 1000
                    self._update_performance_stats('fallback', latency)
                    
                    return HybridSignal(
                        code=code,
                        name=name,
                        source='ml',
                        action=ml_signal.action,
                        confidence=ml_signal.confidence,
                        score=ml_signal.score,
                        latency=latency,
                        timestamp=datetime.now().isoformat(),
                        reasoning="快速信号不足，回退到ML信号"
                    )
            
            # 4. 最终回退到持有
            latency = (time.time() - start_time) * 1000
            return HybridSignal(
                code=code,
                name=name,
                source='system',
                action='HOLD',
                confidence=0.0,
                score=0.5,
                latency=latency,
                timestamp=datetime.now().isoformat(),
                reasoning="无可用信号，默认持有"
            )
            
        except Exception as e:
            logger.error(f"获取混合信号时出错: {e}")
            latency = (time.time() - start_time) * 1000
            return HybridSignal(
                code=code,
                name=name,
                source='error',
                action='HOLD',
                confidence=0.0,
                score=0.5,
                latency=latency,
                timestamp=datetime.now().isoformat(),
                reasoning=f"系统错误: {str(e)}"
            )
    
    def _generate_hybrid_signal(self, code: str, name: str) -> Optional[HybridSignal]:
        """生成混合信号"""
        try:
            # 获取融合信号
            fused_signal = self.signal_fusion.get_fused_signal(code, name)
            
            if not fused_signal:
                return None
            
            # 动态权重调整
            if self.config.weight_adjustment_enabled:
                self._adjust_dynamic_weights()
            
            # 获取快速信号作为技术指标
            fast_signal = self._get_fast_signal(code)
            
            # 应用风险管理
            if self.config.risk_management_enabled:
                fused_signal = self._apply_risk_management(fused_signal, fast_signal)
            
            return HybridSignal(
                code=code,
                name=name,
                source='hybrid',
                action=fused_signal.action,
                confidence=fused_signal.confidence,
                score=fused_signal.fused_score,
                latency=0,  # 将在主函数中计算
                timestamp=datetime.now().isoformat(),
                fast_signal=fast_signal,
                technical_indicators=fast_signal.indicators if fast_signal else {},
                reasoning="多源信号融合结果"
            )
            
        except Exception as e:
            logger.error(f"生成混合信号时出错: {e}")
            return None
    
    def _get_fast_signal(self, code: str) -> Optional[FastSignal]:
        """获取快速信号"""
        try:
            # 这里需要实现从FastSignalProcessor获取信号的方法
            # 由于FastSignalProcessor的设计，我们需要模拟市场数据
            # 在实际应用中，这里应该从数据源获取实时数据
            
            # 模拟数据 - 实际应用中应该替换为真实数据获取
            market_data = {
                code: {
                    'close': [100, 102, 98, 105, 110, 108, 112, 115, 113, 118, 120, 122, 125, 123, 128],
                    'volume': [1000000, 1100000, 900000, 1200000, 1300000, 1150000, 1400000, 1350000, 1250000, 1450000, 1500000, 1550000, 1600000, 1480000, 1650000]
                }
            }
            
            signals = generate_fast_signals(market_data, self.config.fast_signal_strategy)
            return signals.get(code)
            
        except Exception as e:
            logger.error(f"获取快速信号时出错: {e}")
            return None
    
    def _get_ml_signal(self, code: str) -> Optional[SignalResult]:
        """获取ML信号"""
        try:
            # 这里应该调用实际的ML预测器
            # 由于这是一个示例，我们返回模拟数据
            return SignalResult(
                code=code,
                source='ml',
                score=0.65,
                action='BUY',
                confidence=0.65,
                reason="ML模型买入信号",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"获取ML信号时出错: {e}")
            return None
    
    def _get_ai_hedge_signal(self, code: str) -> Optional[SignalResult]:
        """获取AI对冲基金信号"""
        try:
            # 这里应该调用实际的AI对冲基金系统
            # 由于这是一个示例，我们返回模拟数据
            return SignalResult(
                code=code,
                source='ai_hedge',
                score=0.58,
                action='BUY',
                confidence=0.58,
                reason="AI对冲基金买入信号",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"获取AI对冲基金信号时出错: {e}")
            return None
    
    def _calculate_fast_score(self, fast_signal: FastSignal) -> float:
        """计算快速信号分数"""
        # 基于技术指标计算综合分数
        score = 0.5  # 基础分数
        
        # RSI影响
        if fast_signal.rsi < 30:
            score += 0.2
        elif fast_signal.rsi > 70:
            score -= 0.2
        
        # MACD影响
        if fast_signal.macd_signal > 0:
            score += 0.15
        else:
            score -= 0.15
        
        # 动量影响
        score += min(max(fast_signal.momentum * 5, -0.2), 0.2)
        
        # 趋势影响
        if fast_signal.ma_trend == 'bullish':
            score += 0.1
        elif fast_signal.ma_trend == 'bearish':
            score -= 0.1
        
        return max(0, min(1, score))
    
    def _apply_risk_management(self, signal: FusedSignal, fast_signal: Optional[FastSignal]) -> FusedSignal:
        """应用风险管理"""
        # 如果置信度过低，降低信号强度
        if signal.confidence < 0.3:
            signal.fused_score = 0.5
            signal.action = 'HOLD'
            signal.confidence *= 0.5
            signal.warnings.append("低置信度信号已调整为观望")
        
        # 基于快速信号的风险检查
        if fast_signal:
            if fast_signal.action == 'BUY' and fast_signal.confidence < 0.4:
                signal.fused_score = min(signal.fused_score, 0.55)
                signal.warnings.append("快速信号买入信心不足")
            elif fast_signal.action == 'SELL' and fast_signal.confidence < 0.4:
                signal.fused_score = max(signal.fused_score, 0.45)
                signal.warnings.append("快速信号卖出信心不足")
        
        return signal
    
    def _adjust_dynamic_weights(self):
        """动态调整权重"""
        current_time = time.time()
        if not hasattr(self, '_last_weight_adjustment'):
            self._last_weight_adjustment = current_time
        
        if current_time - self._last_weight_adjustment < self.config.weight_adjustment_period:
            return
        
        # 简单的权重调整逻辑
        # 实际应用中应该基于历史表现调整
        with self.weight_lock:
            # 快速信号权重增加（因为速度优势）
            self.dynamic_weights['fast_signal'] = min(self.dynamic_weights['fast_signal'] + 0.05, 0.5)
            
            # ML和AI权重相应减少
            remaining = 1.0 - self.dynamic_weights['fast_signal']
            self.dynamic_weights['ml_signal'] = remaining * 0.5
            self.dynamic_weights['ai_signal'] = remaining * 0.5
        
        self._last_weight_adjustment = current_time
        logger.info(f"动态权重调整完成: {self.dynamic_weights}")
    
    def _update_performance_stats(self, signal_type: str, latency: float):
        """更新性能统计"""
        self.performance_stats['total_requests'] += 1
        
        if signal_type == 'fast':
            self.performance_stats['fast_signals'] += 1
        elif signal_type == 'hybrid':
            self.performance_stats['hybrid_signals'] += 1
        elif signal_type == 'fallback':
            self.performance_stats['fallback_signals'] += 1
        
        # 更新平均延迟
        current_avg = self.performance_stats['avg_latency']
        count = self.performance_stats['total_requests']
        self.performance_stats['avg_latency'] = (current_avg * (count - 1) + latency) / count
        
        self.performance_stats['last_updated'] = time.time()
    
    def batch_get_hybrid_signals(self, codes: List[str], names: Dict[str, str] = None) -> Dict[str, HybridSignal]:
        """批量获取混合信号"""
        names = names or {}
        results = {}
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = []
            for code in codes:
                future = executor.submit(self.get_hybrid_signal, code, names.get(code, ""))
                futures.append((code, future))
            
            for code, future in futures:
                try:
                    result = future.result(timeout=self.config.hybrid_timeout / 1000)
                    results[code] = result
                except Exception as e:
                    logger.error(f"批量处理 {code} 时出错: {e}")
                    results[code] = HybridSignal(
                        code=code,
                        name=names.get(code, ""),
                        source='error',
                        action='HOLD',
                        confidence=0.0,
                        score=0.5,
                        latency=0,
                        timestamp=datetime.now().isoformat(),
                        reasoning=f"批量处理错误: {str(e)}"
                    )
        
        return results
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        total = self.performance_stats['total_requests']
        if total == 0:
            return self.performance_stats
        
        return {
            **self.performance_stats,
            'fast_signal_ratio': self.performance_stats['fast_signals'] / total,
            'hybrid_signal_ratio': self.performance_stats['hybrid_signals'] / total,
            'fallback_signal_ratio': self.performance_stats['fallback_signals'] / total,
            'signals_per_second': total / max((time.time() - self.performance_stats['last_updated']) / 60, 1),
            'dynamic_weights': self.dynamic_weights.copy()
        }
    
    def clear_cache(self):
        """清空缓存"""
        with self.cache_lock:
            self.signal_cache.clear()
            self.fast_processor.clear_cache()
        logger.info("混合信号缓存已清空")
    
    def update_config(self, config: FusionConfig):
        """更新配置"""
        self.config = config
        logger.info("混合信号配置已更新")
    
    def get_signal_sources(self) -> List[str]:
        """获取信号源列表"""
        return list(self.signal_fusion._sources.keys())


# 全局单例
_hybrid_fusion_engine: Optional[HybridFusionEngine] = None


def get_hybrid_fusion_engine() -> HybridFusionEngine:
    """获取全局混合信号融合引擎单例"""
    global _hybrid_fusion_engine
    if _hybrid_fusion_engine is None:
        _hybrid_fusion_engine = HybridFusionEngine()
    return _hybrid_fusion_engine


# 便捷函数
def get_hybrid_signal(code: str, name: str = "", force_hybrid: bool = False) -> HybridSignal:
    """便捷函数：获取混合信号"""
    engine = get_hybrid_fusion_engine()
    return engine.get_hybrid_signal(code, name, force_hybrid)


def batch_get_hybrid_signals(codes: List[str], names: Dict[str, str] = None) -> Dict[str, HybridSignal]:
    """便捷函数：批量获取混合信号"""
    engine = get_hybrid_fusion_engine()
    return engine.batch_get_hybrid_signals(codes, names)


def get_hybrid_fusion_stats() -> Dict[str, Any]:
    """便捷函数：获取混合信号引擎统计"""
    engine = get_hybrid_fusion_engine()
    return engine.get_performance_stats()


if __name__ == '__main__':
    # 测试示例
    print("测试混合信号融合引擎...")
    
    engine = get_hybrid_fusion_engine()
    
    # 测试单只股票
    print("\n=== 单只股票测试 ===")
    signal = get_hybrid_signal('600519', '贵州茅台')
    print(f"代码: {signal.code}")
    print(f"名称: {signal.name}")
    print(f"信号源: {signal.source}")
    print(f"动作: {signal.action}")
    print(f"置信度: {signal.confidence:.3f}")
    print(f"分数: {signal.score:.3f}")
    print(f"延迟: {signal.latency:.2f}ms")
    print(f"时间戳: {signal.timestamp}")
    print(f"原因: {signal.reasoning}")
    
    if signal.fast_signal:
        print(f"快速信号 RSI: {signal.fast_signal.rsi:.2f}")
        print(f"快速信号 MACD: {signal.fast_signal.macd_signal:.4f}")
        print(f"快速信号趋势: {signal.fast_signal.ma_trend}")
    
    # 测试批量处理
    print("\n=== 批量处理测试 ===")
    test_codes = ['600519', '000001', '000002', '600000']
    batch_signals = batch_get_hybrid_signals(test_codes)
    
    for code, signal in batch_signals.items():
        print(f"{code}: {signal.action} (置信度: {signal.confidence:.3f}, 来源: {signal.source})")
    
    # 显示统计信息
    print(f"\n性能统计:")
    stats = get_hybrid_fusion_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 显示信号源
    print(f"\n信号源:")
    sources = engine.get_signal_sources()
    for source in sources:
        print(f"  - {source}")
    
    # 测试配置更新
    print(f"\n配置更新测试:")
    new_config = FusionConfig(
        fast_signal_threshold=0.7,
        fast_signal_strategy="conservative",
        hybrid_timeout=800
    )
    engine.update_config(new_config)
    print("配置已更新")