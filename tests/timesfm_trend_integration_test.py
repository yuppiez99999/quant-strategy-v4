# -*- coding: utf-8 -*-
"""
TimesFM趋势集成测试脚本

验证TimesFM预测作为趋势判断输入的功能，包括：
- 实时趋势预测
- 置信区间分析
- 异常检测
- 性能监控
- 与信号融合系统集成

使用方式:
    python timesfm_trend_integration_test.py
"""

import os
import sys
import json
import time
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加当前目录到路径
utils_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'utils')
sys.path.insert(0, utils_path)

try:
    from timesfm_trend_integration import (
        TimesFMTrendIntegrator,
        TrendPrediction,
        get_trend_integrator,
        register_timesfm_trend_source
    )
    from enhanced_signal_fusion import get_enhanced_fusion_engine
    from logging_manager import get_logger
    logger = get_logger('timesfm_test')
except ImportError:
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'utils'))
        from timesfm_trend_integration import (
            TimesFMTrendIntegrator,
            TrendPrediction,
            get_trend_integrator,
            register_timesfm_trend_source
        )
        from enhanced_signal_fusion import get_enhanced_fusion_engine
        from logging_manager import get_logger
        logger = get_logger('timesfm_test')
    except ImportError:
        import logging
        logger = logging.getLogger('timesfm_test')


def test_timesfm_trend_integration():
    """测试TimesFM趋势集成功能"""
    logger.info("开始测试TimesFM趋势集成功能")
    
    # 创建趋势集成器
    integrator = TimesFMTrendIntegrator(
        horizon_days=5,  # 短期预测
        context_days=126,  # 6个月历史数据
        cache_size=100,
        enable_anomaly_detection=True
    )
    
    # 测试标的列表
    test_symbols = ['600519', '000858', '002415', '600276', '300750']
    test_symbols_with_market = [f"{symbol}.SH" if symbol.startswith('6') else f"{symbol}.SZ" 
                               for symbol in test_symbols]
    
    logger.info(f"测试标的: {test_symbols}")
    
    # 1. 测试单个趋势预测
    logger.info("\n=== 1. 单个趋势预测测试 ===")
    single_results = {}
    for symbol in test_symbols_with_market:
        start_time = time.time()
        prediction = integrator.predict_trend(symbol)
        response_time = (time.time() - start_time) * 1000
        
        if prediction:
            single_results[symbol] = {
                'trend': prediction.trend,
                'strength': prediction.strength,
                'confidence': prediction.confidence,
                'volatility': prediction.volatility_forecast,
                'anomaly': prediction.anomaly_detected,
                'response_time_ms': response_time
            }
            logger.info(f"{symbol}: {prediction.trend} (强度: {prediction.strength:.2f}, "
                       f"置信度: {prediction.confidence:.2f}, 响应时间: {response_time:.2f}ms)")
        else:
            logger.warning(f"{symbol}: 预测失败")
    
    # 2. 测试批量趋势预测
    logger.info("\n=== 2. 批量趋势预测测试 ===")
    start_time = time.time()
    batch_results = integrator.get_batch_trend_signals(test_symbols_with_market)
    batch_time = (time.time() - start_time) * 1000
    
    logger.info(f"批量预测完成: {len(batch_results)} 个标的，耗时: {batch_time:.2f}ms")
    
    for symbol, signal_result in batch_results.items():
        logger.info(f"{symbol}: {signal_result.action} (分数: {signal_result.score:.3f}, "
                   f"置信度: {signal_result.confidence:.3f})")
    
    # 3. 测试趋势信号转换
    logger.info("\n=== 3. 趋势信号转换测试 ===")
    for symbol, prediction in batch_results.items():
        signal_result = prediction.to_signal_result()
        logger.info(f"{symbol} -> {signal_result.action} (分数: {signal_result.score:.3f})")
    
    # 4. 测试异常检测
    logger.info("\n=== 4. 异常检测测试 ===")
    anomaly_count = 0
    for symbol, prediction in batch_results.items():
        if prediction.anomaly_detected:
            anomaly_count += 1
            logger.warning(f"{symbol}: 检测到异常 - {prediction.anomaly_type}")
    
    logger.info(f"异常检测结果: {anomaly_count}/{len(batch_results)} 个标的存在异常")
    
    # 5. 测试缓存机制
    logger.info("\n=== 5. 缓存机制测试 ===")
    logger.info(f"缓存大小: {len(integrator.prediction_cache)}")
    
    # 第二次预测应该使用缓存
    start_time = time.time()
    cached_results = integrator.get_batch_trend_signals(test_symbols_with_market)
    cache_time = (time.time() - start_time) * 1000
    
    logger.info(f"缓存预测耗时: {cache_time:.2f}ms (应该比第一次快)")
    
    # 6. 测试性能统计
    logger.info("\n=== 6. 性能统计测试 ===")
    stats = integrator.get_performance_stats()
    logger.info(f"总预测次数: {stats['total_predictions']}")
    logger.info(f"成功次数: {stats['successful_predictions']}")
    logger.info(f"失败次数: {stats['failed_predictions']}")
    logger.info(f"平均响应时间: {stats['average_response_time']:.2f}ms")
    logger.info(f"缓存命中率: {stats['cache_hit_rate']:.2%}")
    
    # 7. 测试与增强信号融合引擎的集成
    logger.info("\n=== 7. 信号融合引擎集成测试 ===")
    try:
        engine = get_enhanced_fusion_engine()
        
        # 检查TimesFM趋势源是否已注册
        if 'timesfm_trend' in engine._sources:
            logger.info("TimesFM趋势信号源已注册")
            
            # 测试融合信号获取
            start_time = time.time()
            fused_signals = {}
            for symbol in test_symbols_with_market:
                try:
                    signal = engine.get_fused_signal(symbol, f"测试股票{symbol}")
                    fused_signals[symbol] = signal
                    logger.info(f"{symbol}: 融合信号 {signal.action} "
                               f"(分数: {signal.fused_score:.3f}, 置信度: {signal.confidence:.3f})")
                except Exception as e:
                    logger.warning(f"{symbol} 融合信号获取失败: {e}")
            
            integration_time = (time.time() - start_time) * 1000
            logger.info(f"集成测试完成: {len(fused_signals)} 个标的，耗时: {integration_time:.2f}ms")
            
            # 分析融合结果
            analyze_fusion_results(fused_signals)
            
        else:
            logger.warning("TimesFM趋势信号源未注册")
            register_timesfm_trend_source()
            logger.info("TimesFM趋势信号源已注册")
    
    except Exception as e:
        logger.error(f"信号融合引擎集成测试失败: {e}")
    
    # 保存测试结果
    test_results = {
        'test_time': datetime.now().isoformat(),
        'integrator_config': {
            'horizon_days': integrator.horizon_days,
            'context_days': integrator.context_days,
            'cache_size': integrator.cache_size,
            'enable_anomaly_detection': integrator.enable_anomaly_detection
        },
        'single_predictions': single_results,
        'batch_predictions': {k: {
            'trend': v.trend,
            'strength': v.strength,
            'confidence': v.confidence,
            'volatility': v.volatility_forecast,
            'anomaly': v.anomaly_detected
        } for k, v in batch_results.items()},
        'performance_stats': stats,
        'integration_results': {k: {
            'action': v.action,
            'fused_score': v.fused_score,
            'confidence': v.confidence,
            'consensus': v.consensus
        } for k, v in fused_signals.items()} if 'fused_signals' in locals() else {},
        'summary': {
            'total_tested': len(test_symbols_with_market),
            'successful_predictions': len(batch_results),
            'anomalies_detected': anomaly_count,
            'avg_response_time': stats['average_response_time'],
            'cache_hit_rate': stats['cache_hit_rate']
        }
    }
    
    # 保存到文件
    output_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'timesfm_trend_integration_test_results.json')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"测试结果已保存到: {output_file}")
    
    # 性能测试
    logger.info("\n=== 8. 性能压力测试 ===")
    start_time = time.time()
    for _ in range(10):  # 10次预测
        integrator.get_batch_trend_signals(test_symbols_with_market[:3])  # 只测试前3个
    avg_time = ((time.time() - start_time) / 10) * 1000
    logger.info(f"平均批量预测时间: {avg_time:.2f}ms")
    
    # 内存使用测试
    logger.info("\n=== 9. 内存使用测试 ===")
    initial_cache_size = len(integrator.prediction_cache)
    logger.info(f"初始缓存大小: {initial_cache_size}")
    
    # 清空缓存
    integrator.clear_cache()
    logger.info(f"清空后缓存大小: {len(integrator.prediction_cache)}")
    
    logger.info("TimesFM趋势集成测试完成!")
    
    return test_results


def analyze_fusion_results(fused_signals: Dict[str, Any]):
    """分析融合结果"""
    logger.info("\n=== 融合结果分析 ===")
    
    total_signals = len(fused_signals)
    buy_signals = sum(1 for s in fused_signals.values() if s.action == 'BUY')
    sell_signals = sum(1 for s in fused_signals.values() if s.action == 'SELL')
    hold_signals = sum(1 for s in fused_signals.values() if s.action == 'HOLD')
    
    logger.info(f"信号分布: 买入 {buy_signals}, 卖出 {sell_signals}, 持有 {hold_signals}")
    
    # 分析置信度分布
    confidences = [s.confidence for s in fused_signals.values()]
    avg_confidence = np.mean(confidences)
    max_confidence = np.max(confidences)
    min_confidence = np.min(confidences)
    
    logger.info(f"置信度分布: 平均 {avg_confidence:.3f}, 最高 {max_confidence:.3f}, 最低 {min_confidence:.3f}")
    
    # 分析共识分布
    consensus_counts = {}
    for s in fused_signals.values():
        consensus = s.consensus
        consensus_counts[consensus] = consensus_counts.get(consensus, 0) + 1
    
    logger.info(f"共识分布: {dict(consensus_counts)}")


def test_edge_cases():
    """测试边界情况"""
    logger.info("\n=== 边界情况测试 ===")
    
    integrator = TimesFMTrendIntegrator()
    
    # 1. 测试无效标的
    invalid_result = integrator.predict_trend("INVALID_SYMBOL")
    logger.info(f"无效标的测试: {invalid_result is None}")
    
    # 2. 测试空预测
    empty_result = integrator.predict_trend("600519.SH", force_refresh=True)
    logger.info(f"空预测测试: {empty_result is None}")
    
    # 3. 测试批量空预测
    empty_batch = integrator.get_batch_trend_signals(["INVALID1", "INVALID2"])
    logger.info(f"批量空预测测试: {len(empty_batch)} 个有效结果")
    
    logger.info("边界情况测试完成")


if __name__ == "__main__":
    print("=== TimesFM趋势集成测试 ===")
    print("测试功能:")
    print("1. 单个趋势预测")
    print("2. 批量趋势预测")
    print("3. 趋势信号转换")
    print("4. 异常检测")
    print("5. 缓存机制")
    print("6. 性能统计")
    print("7. 信号融合集成")
    print("8. 性能压力测试")
    print("9. 边界情况测试")
    print("=" * 50)
    
    # 运行测试
    test_results = test_timesfm_trend_integration()
    test_edge_cases()
    
    print("\n测试完成! 查看 data/timesfm_trend_integration_test_results.json 获取详细结果。")
    
    # 输出摘要
    summary = test_results['summary']
    print(f"\n测试摘要:")
    print(f"- 测试标的数: {summary['total_tested']}")
    print(f"- 成功预测数: {summary['successful_predictions']}")
    print(f"- 异常检测数: {summary['anomalies_detected']}")
    print(f"- 平均响应时间: {summary['avg_response_time']:.2f}ms")
    print(f"- 缓存命中率: {summary['cache_hit_rate']:.2%}")