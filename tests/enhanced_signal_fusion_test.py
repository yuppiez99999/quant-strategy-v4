# -*- coding: utf-8 -*-
"""
增强信号融合引擎测试脚本

验证动态权重升级功能，包括：
- 多维度性能指标计算
- 相关性矩阵计算
- 动态权重调整
- 性能监控与优化
- 基于市场条件的权重优化

使用方式:
    python enhanced_signal_fusion_test.py
"""

import os
import sys
import time
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加当前目录到路径
utils_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'utils')
sys.path.insert(0, utils_path)

try:
    from enhanced_signal_fusion import (
        EnhancedSignalFusionEngine, 
        WeightAdjustmentConfig,
        get_enhanced_fusion_engine,
        register_enhanced_fast_signal_source
    )
    from signal_fusion import SignalResult, FusedSignal
    from logging_manager import get_logger
    logger = get_logger('enhanced_test')
except ImportError:
    import logging
    logger = logging.getLogger('enhanced_test')


def create_mock_signal_sources():
    """创建模拟信号源用于测试"""
    def ml_predictor(code: str) -> SignalResult:
        # 模拟ML模型性能：75%准确率
        import random
        actual = random.random()
        if actual < 0.75:
            action = "BUY"
            confidence = random.uniform(0.6, 0.9)
        elif actual < 0.9:
            action = "HOLD"
            confidence = random.uniform(0.4, 0.6)
        else:
            action = "SELL"
            confidence = random.uniform(0.1, 0.4)
        
        return SignalResult(
            code=code,
            source='ml',
            score=confidence if action == "BUY" else 1 - confidence,
            action=action,
            confidence=confidence,
            reason=f"ML模型预测: {action}",
            timestamp=datetime.now().isoformat()
        )
    
    def ai_hedge_predictor(code: str) -> SignalResult:
        # 模拟AI对冲基金：80%准确率，响应时间较长
        import random
        time.sleep(0.1)  # 模拟较慢响应
        actual = random.random()
        if actual < 0.8:
            action = "BUY"
            confidence = random.uniform(0.7, 0.95)
        elif actual < 0.95:
            action = "HOLD"
            confidence = random.uniform(0.45, 0.55)
        else:
            action = "SELL"
            confidence = random.uniform(0.05, 0.3)
        
        return SignalResult(
            code=code,
            source='ai_hedge',
            score=confidence if action == "BUY" else 1 - confidence,
            action=action,
            confidence=confidence,
            reason=f"AI对冲基金预测: {action}",
            timestamp=datetime.now().isoformat()
        )
    
    def glm5_predictor(code: str) -> SignalResult:
        # 模拟GLM5：70%准确率，中等响应时间
        import random
        time.sleep(0.05)  # 模拟中等响应
        actual = random.random()
        if actual < 0.7:
            action = "BUY"
            confidence = random.uniform(0.65, 0.85)
        elif actual < 0.85:
            action = "HOLD"
            confidence = random.uniform(0.35, 0.65)
        else:
            action = "SELL"
            confidence = random.uniform(0.15, 0.35)
        
        return SignalResult(
            code=code,
            source='glm5',
            score=confidence if action == "BUY" else 1 - confidence,
            action=action,
            confidence=confidence,
            reason=f"GLM5预测: {action}",
            timestamp=datetime.now().isoformat()
        )
    
    def kondratiev_predictor(code: str) -> SignalResult:
        # 模拟康波周期：60%准确率，响应时间快但准确率较低
        import random
        time.sleep(0.02)  # 模拟快速响应
        actual = random.random()
        if actual < 0.6:
            action = "BUY"
            confidence = random.uniform(0.6, 0.8)
        elif actual < 0.8:
            action = "HOLD"
            confidence = random.uniform(0.3, 0.7)
        else:
            action = "SELL"
            confidence = random.uniform(0.2, 0.4)
        
        return SignalResult(
            code=code,
            source='kondratiev',
            score=confidence if action == "BUY" else 1 - confidence,
            action=action,
            confidence=confidence,
            reason=f"康波周期分析: {action}",
            timestamp=datetime.now().isoformat()
        )
    
    return {
        'ml': ml_predictor,
        'ai_hedge': ai_hedge_predictor,
        'glm5': glm5_predictor,
        'kondratiev': kondratiev_predictor
    }


def test_enhanced_signal_fusion():
    """测试增强信号融合引擎"""
    logger.info("开始测试增强信号融合引擎")
    
    # 创建配置
    from enhanced_signal_fusion import WeightAdjustmentConfig
    config = WeightAdjustmentConfig(
        lookback_days=30,
        min_samples=5,
        max_weight_per_source=0.5,
        min_weight_per_source=0.05,
        adaptive_learning_rate=0.1,
        correlation_penalty_factor=0.2,
        performance_trend_window=7
    )
    
    # 创建引擎实例
    engine = EnhancedSignalFusionEngine(config=config)
    
    # 创建模拟信号源
    mock_sources = create_mock_signal_sources()
    
    # 注册信号源
    for source_name, source_func in mock_sources.items():
        initial_weight = 0.25  # 初始均分
        engine.register_enhanced_source(source_name, source_func, initial_weight)
        logger.info(f"注册信号源: {source_name} (初始权重: {initial_weight})")
    
    logger.info(f"已注册信号源: {list(engine._sources.keys())}")
    logger.info(f"初始权重: {engine._source_weights}")
    
    # 测试信号融合
    test_codes = ['600519', '000858', '002415', '600276']
    results = {}
    
    logger.info("开始信号融合测试...")
    for code in test_codes:
        start_time = time.time()
        fused_signal = engine.get_fused_signal(code, f"测试股票{code}")
        response_time = (time.time() - start_time) * 1000
        
        results[code] = {
            'fused_score': fused_signal.fused_score,
            'action': fused_signal.action,
            'confidence': fused_signal.confidence,
            'consensus': fused_signal.consensus,
            'response_time_ms': response_time,
            'individual_signals': {k: {
                'score': v.score, 
                'action': v.action,
                'confidence': v.confidence
            } for k, v in fused_signal.individual_signals.items()}
        }
        
        logger.info(f"股票 {code}: {fused_signal.action} (分数: {fused_signal.fused_score:.3f}, "
                   f"置信度: {fused_signal.confidence:.3f}, 响应时间: {response_time:.2f}ms)")
    
    # 获取统计信息
    stats = engine.get_enhanced_stats()
    logger.info("\n=== 增强版统计信息 ===")
    logger.info(f"信号源数量: {len(stats['sources_registered'])}")
    logger.info(f"当前权重: {stats['source_weights']}")
    
    # 性能指标
    if 'performance_metrics' in stats:
        logger.info("\n=== 性能指标 ===")
        for source_name, metrics in stats['performance_metrics'].items():
            logger.info(f"{source_name}: 准确率={metrics['recent_accuracy']:.3f}, "
                       f"信号数={metrics['total_signals']}, "
                       f"连续胜={metrics['consecutive_wins']}, "
                       f"连败={metrics['consecutive_losses']}, "
                       f"多样性={metrics['diversity_score']:.3f}")
    
    # 相关性矩阵
    if 'correlation_matrix' in stats:
        logger.info("\n=== 相关性矩阵 ===")
        for source1, correlations in stats['correlation_matrix'].items():
            for source2, correlation in correlations.items():
                if source1 != source2:
                    logger.info(f"{source1}-{source2}: {correlation:.3f}")
    
    # 测试权重变化分析
    logger.info("\n=== 权重变化分析 ===")
    for source_name in stats['sources_registered']:
        analysis = engine.get_weight_change_analysis(source_name, days=7)
        if 'error' not in analysis:
            logger.info(f"{source_name}: {analysis['trend_direction']} (变化: {analysis['total_change']:.3f}, "
                       f"波动: {analysis['weight_volatility']:.3f})")
    
    # 测试基于市场条件的权重优化
    logger.info("\n=== 基于市场条件的权重优化 ===")
    
    # 模拟牛市
    logger.info("牛市环境权重调整:")
    engine.optimize_weights_based_on_market_conditions("bullish")
    bull_weights = engine._source_weights.copy()
    logger.info(f"牛市权重: {bull_weights}")
    
    # 模拟熊市
    logger.info("熊市环境权重调整:")
    engine.optimize_weights_based_on_market_conditions("bearish")
    bear_weights = engine._source_weights.copy()
    logger.info(f"熊市权重: {bear_weights}")
    
    # 模拟震荡市
    logger.info("震荡市环境权重调整:")
    engine.optimize_weights_based_on_market_conditions("volatile")
    volatile_weights = engine._source_weights.copy()
    logger.info(f"震荡市权重: {volatile_weights}")
    
    # 保存测试结果
    test_results = {
        'test_time': datetime.now().isoformat(),
        'config': {
            'lookback_days': config.lookback_days,
            'max_weight_per_source': config.max_weight_per_source,
            'min_weight_per_source': config.min_weight_per_source,
            'adaptive_learning_rate': config.adaptive_learning_rate
        },
        'initial_weights': dict(stats['source_weights']),
        'bull_market_weights': bull_weights,
        'bear_market_weights': bear_weights,
        'volatile_market_weights': volatile_weights,
        'fusion_results': results,
        'final_weights': engine._source_weights,
        'performance_metrics': stats.get('performance_metrics', {}),
        'correlation_matrix': stats.get('correlation_matrix', {})
    }
    
    # 保存到文件
    output_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'enhanced_fusion_test_results.json')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"测试结果已保存到: {output_file}")
    
    # 性能测试
    logger.info("\n=== 性能测试 ===")
    start_time = time.time()
    for _ in range(100):  # 测试100次融合
        engine.get_fused_signal('600519', '测试股票')
    avg_time = ((time.time() - start_time) / 100) * 1000
    logger.info(f"平均融合时间: {avg_time:.2f}ms")
    
    # 验证权重约束
    logger.info("\n=== 权重约束验证 ===")
    for source_name, weight in engine._source_weights.items():
        if weight > config.max_weight_per_source:
            logger.warning(f"警告: {source_name} 权重 {weight:.3f} 超过最大值 {config.max_weight_per_source}")
        if weight < config.min_weight_per_source:
            logger.warning(f"警告: {source_name} 权重 {weight:.3f} 低于最小值 {config.min_weight_per_source}")
    
    total_weight = sum(engine._source_weights.values())
    logger.info(f"总权重: {total_weight:.3f} (应该等于1.0)")
    
    logger.info("增强信号融合引擎测试完成!")
    
    return results


def test_fast_signal_integration():
    """测试快速信号集成"""
    logger.info("\n开始测试快速信号集成...")
    
    try:
        engine = get_enhanced_fusion_engine()
        
        # 检查快速信号源是否已注册
        if 'fast_technical' in engine._sources:
            logger.info("快速技术指标信号源已注册")
            
            # 测试快速信号获取
            start_time = time.time()
            result = engine.get_fused_signal('600519', '测试股票')
            response_time = (time.time() - start_time) * 1000
            
            logger.info(f"快速信号融合结果: {result.action} "
                       f"(分数: {result.fused_score:.3f}, 响应时间: {response_time:.2f}ms)")
            
            # 更新性能指标（模拟真实交易结果）
            if result.action == 'BUY':
                actual_outcome = 'BUY'
            else:
                actual_outcome = 'HOLD'  # 简化处理
            
            engine.update_performance_metrics(
                'fast_technical', actual_outcome, result.action, response_time
            )
            
        else:
            logger.warning("快速技术指标信号源未注册")
            register_enhanced_fast_signal_source()
            
    except Exception as e:
        logger.error(f"快速信号集成测试失败: {e}")


if __name__ == "__main__":
    print("=== 增强信号融合引擎测试 ===")
    print("测试功能:")
    print("1. 多维度性能指标计算")
    print("2. 相关性矩阵计算")
    print("3. 动态权重调整")
    print("4. 基于市场条件的权重优化")
    print("5. 快速信号集成")
    print("=" * 50)
    
    # 运行测试
    test_results = test_enhanced_signal_fusion()
    test_fast_signal_integration()
    
    print("\n测试完成! 查看 data/enhanced_fusion_test_results.json 获取详细结果。")