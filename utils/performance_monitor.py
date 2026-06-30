# -*- coding: utf-8 -*-
"""
快速信号性能监控模块

实时监控快速信号处理器的性能指标，
包括延迟、准确率、资源使用等。

主要功能：
- 实时性能监控
- 延迟测量
- 准确率追踪
- 资源使用监控
- 性能报告生成
"""

import os
import sys
import time
import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
import psutil
import gc
from collections import deque

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from .logging_manager import get_logger
    logger = get_logger('performance_monitor')
except ImportError:
    import logging
    logger = logging.getLogger('performance_monitor')


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: float
    total_signals: int
    successful_signals: int
    failed_signals: int
    avg_latency: float
    min_latency: float
    max_latency: float
    p95_latency: float
    p99_latency: float
    cache_hit_rate: float
    memory_usage: float
    cpu_usage: float
    throughput: float
    error_rate: float


@dataclass
class LatencyData:
    """延迟数据"""
    timestamp: float
    latency: float
    code: str
    source: str
    success: bool
    error_message: str = ""


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, max_history: int = 10000, report_interval: int = 60):
        """
        初始化性能监控器
        
        Args:
            max_history: 最大历史记录数量
            report_interval: 报告生成间隔（秒）
        """
        self.max_history = max_history
        self.report_interval = report_interval
        
        # 性能数据存储
        self.latency_history = deque(maxlen=max_history)
        self.metrics_history = deque(maxlen=max_history)
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'total': 0
        }
        
        # 实时指标
        self.current_metrics = {
            'total_signals': 0,
            'successful_signals': 0,
            'failed_signals': 0,
            'total_latency': 0.0,
            'min_latency': float('inf'),
            'max_latency': 0.0,
            'start_time': time.time(),
            'last_report_time': time.time()
        }
        
        # 系统监控
        self.system_monitor = SystemMonitor()
        
        # 报告生成器
        self.report_generator = PerformanceReportGenerator()
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("性能监控器初始化完成")
    
    def record_signal(self, code: str, source: str, latency: float, success: bool = True, error_message: str = ""):
        """
        记录信号处理数据
        
        Args:
            code: 股票代码
            source: 信号源
            latency: 延迟（毫秒）
            success: 是否成功
            error_message: 错误信息
        """
        timestamp = time.time()
        
        # 记录延迟数据
        latency_data = LatencyData(
            timestamp=timestamp,
            latency=latency,
            code=code,
            source=source,
            success=success,
            error_message=error_message
        )
        self.latency_history.append(latency_data)
        
        # 更新当前指标
        self._update_current_metrics(latency, success)
        
        # 更新缓存统计
        if source == 'fast_technical':
            if success:
                self.cache_stats['hits'] += 1
            else:
                self.cache_stats['misses'] += 1
            self.cache_stats['total'] += 1
    
    def _update_current_metrics(self, latency: float, success: bool):
        """更新当前指标"""
        self.current_metrics['total_signals'] += 1
        self.current_metrics['total_latency'] += latency
        
        if success:
            self.current_metrics['successful_signals'] += 1
        else:
            self.current_metrics['failed_signals'] += 1
        
        self.current_metrics['min_latency'] = min(self.current_metrics['min_latency'], latency)
        self.current_metrics['max_latency'] = max(self.current_metrics['max_latency'], latency)
    
    def _monitor_loop(self):
        """监控循环"""
        while True:
            try:
                # 定期生成报告
                current_time = time.time()
                if current_time - self.current_metrics['last_report_time'] >= self.report_interval:
                    self._generate_periodic_report()
                    self.current_metrics['last_report_time'] = current_time
                
                # 休眠
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                time.sleep(5)
    
    def _generate_periodic_report(self):
        """生成定期报告"""
        try:
            metrics = self.get_current_metrics()
            report = self.report_generator.generate_report(metrics)
            
            logger.info(f"性能报告: {json.dumps(report, ensure_ascii=False, indent=2, default=str)}")
            
        except Exception as e:
            logger.error(f"生成定期报告失败: {e}")
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """获取当前性能指标"""
        current_time = time.time()
        total_signals = self.current_metrics['total_signals']
        
        if total_signals == 0:
            return PerformanceMetrics(
                timestamp=current_time,
                total_signals=0,
                successful_signals=0,
                failed_signals=0,
                avg_latency=0.0,
                min_latency=0.0,
                max_latency=0.0,
                p95_latency=0.0,
                p99_latency=0.0,
                cache_hit_rate=0.0,
                memory_usage=0.0,
                cpu_usage=0.0,
                throughput=0.0,
                error_rate=0.0
            )
        
        # 计算延迟百分位数
        latencies = [data.latency for data in self.latency_history if data.success]
        if latencies:
            p95_latency = np.percentile(latencies, 95)
            p99_latency = np.percentile(latencies, 99)
        else:
            p95_latency = 0.0
            p99_latency = 0.0
        
        # 计算缓存命中率
        cache_hit_rate = self.cache_stats['hits'] / max(self.cache_stats['total'], 1)
        
        # 计算吞吐量
        running_time = current_time - self.current_metrics['start_time']
        throughput = total_signals / max(running_time / 60, 1)  # 每分钟信号数
        
        # 计算错误率
        error_rate = self.current_metrics['failed_signals'] / total_signals
        
        # 获取系统资源使用情况
        memory_usage = self.system_monitor.get_memory_usage()
        cpu_usage = self.system_monitor.get_cpu_usage()
        
        return PerformanceMetrics(
            timestamp=current_time,
            total_signals=total_signals,
            successful_signals=self.current_metrics['successful_signals'],
            failed_signals=self.current_metrics['failed_signals'],
            avg_latency=self.current_metrics['total_latency'] / total_signals,
            min_latency=self.current_metrics['min_latency'],
            max_latency=self.current_metrics['max_latency'],
            p95_latency=p95_latency,
            p99_latency=p99_latency,
            cache_hit_rate=cache_hit_rate,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            throughput=throughput,
            error_rate=error_rate
        )
    
    def get_historical_metrics(self, limit: int = 100) -> List[PerformanceMetrics]:
        """获取历史性能指标"""
        return list(self.metrics_history)[-limit:]
    
    def get_latency_distribution(self) -> Dict[str, Any]:
        """获取延迟分布"""
        if not self.latency_history:
            return {}
        
        latencies = [data.latency for data in self.latency_history if data.success]
        if not latencies:
            return {}
        
        return {
            'count': len(latencies),
            'mean': np.mean(latencies),
            'median': np.median(latencies),
            'std': np.std(latencies),
            'min': np.min(latencies),
            'max': np.max(latencies),
            'p25': np.percentile(latencies, 25),
            'p75': np.percentile(latencies, 75),
            'p95': np.percentile(latencies, 95),
            'p99': np.percentile(latencies, 99),
            'distribution': self._calculate_latency_bins(latencies)
        }
    
    def _calculate_latency_bins(self, latencies: List[float]) -> Dict[str, int]:
        """计算延迟分箱"""
        bins = {
            '<1ms': 0,
            '1-5ms': 0,
            '5-10ms': 0,
            '10-20ms': 0,
            '20-50ms': 0,
            '50-100ms': 0,
            '100-200ms': 0,
            '200-500ms': 0,
            '500ms-1s': 0,
            '>1s': 0
        }
        
        for latency in latencies:
            if latency < 1:
                bins['<1ms'] += 1
            elif latency < 5:
                bins['1-5ms'] += 1
            elif latency < 10:
                bins['5-10ms'] += 1
            elif latency < 20:
                bins['10-20ms'] += 1
            elif latency < 50:
                bins['20-50ms'] += 1
            elif latency < 100:
                bins['50-100ms'] += 1
            elif latency < 200:
                bins['100-200ms'] += 1
            elif latency < 500:
                bins['200-500ms'] += 1
            elif latency < 1000:
                bins['500ms-1s'] += 1
            else:
                bins['>1s'] += 1
        
        return bins
    
    def get_source_performance(self, source: str) -> Dict[str, Any]:
        """获取特定信号源的性能"""
        source_data = [data for data in self.latency_history if data.source == source]
        
        if not source_data:
            return {}
        
        successful_data = [data for data in source_data if data.success]
        
        return {
            'total_signals': len(source_data),
            'successful_signals': len(successful_data),
            'failed_signals': len(source_data) - len(successful_data),
            'error_rate': (len(source_data) - len(successful_data)) / len(source_data) if source_data else 0,
            'avg_latency': np.mean([data.latency for data in successful_data]) if successful_data else 0,
            'min_latency': np.min([data.latency for data in successful_data]) if successful_data else 0,
            'max_latency': np.max([data.latency for data in successful_data]) if successful_data else 0,
            'p95_latency': np.percentile([data.latency for data in successful_data], 95) if successful_data else 0,
            'p99_latency': np.percentile([data.latency for data in successful_data], 99) if successful_data else 0
        }
    
    def reset_metrics(self):
        """重置性能指标"""
        self.latency_history.clear()
        self.metrics_history.clear()
        self.cache_stats = {'hits': 0, 'misses': 0, 'total': 0}
        
        self.current_metrics = {
            'total_signals': 0,
            'successful_signals': 0,
            'failed_signals': 0,
            'total_latency': 0.0,
            'min_latency': float('inf'),
            'max_latency': 0.0,
            'start_time': time.time(),
            'last_report_time': time.time()
        }
        
        logger.info("性能指标已重置")
    
    def export_metrics(self, file_path: str):
        """导出性能指标到文件"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'current_metrics': self.get_current_metrics().__dict__,
                'historical_metrics': [m.__dict__ for m in self.get_historical_metrics()],
                'latency_distribution': self.get_latency_distribution(),
                'source_performance': {
                    source: self.get_source_performance(source)
                    for source in ['fast_technical', 'ml', 'ai_hedge']
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"性能指标已导出到: {file_path}")
            
        except Exception as e:
            logger.error(f"导出性能指标失败: {e}")


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.process = psutil.Process()
    
    def get_memory_usage(self) -> float:
        """获取内存使用量（MB）"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def get_cpu_usage(self) -> float:
        """获取CPU使用率（%）"""
        return self.process.cpu_percent(interval=1)
    
    def get_thread_count(self) -> int:
        """获取线程数"""
        return self.process.num_threads()
    
    def get_handle_count(self) -> int:
        """获取句柄数"""
        return self.process.num_handles()


class PerformanceReportGenerator:
    """性能报告生成器"""
    
    def generate_report(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """生成性能报告"""
        report = {
            'timestamp': datetime.fromtimestamp(metrics.timestamp).isoformat(),
            'signal_processing': {
                'total_signals': metrics.total_signals,
                'successful_signals': metrics.successful_signals,
                'failed_signals': metrics.failed_signals,
                'success_rate': (metrics.successful_signals / max(metrics.total_signals, 1)) * 100,
                'error_rate': metrics.error_rate * 100,
                'throughput': metrics.throughput
            },
            'latency': {
                'average_ms': metrics.avg_latency,
                'min_ms': metrics.min_latency,
                'max_ms': metrics.max_latency,
                'p95_ms': metrics.p95_latency,
                'p99_ms': metrics.p99_latency,
                'performance_grade': self._get_performance_grade(metrics.avg_latency)
            },
            'cache': {
                'hit_rate': metrics.cache_hit_rate * 100,
                'efficiency': 'high' if metrics.cache_hit_rate > 0.8 else 'medium' if metrics.cache_hit_rate > 0.5 else 'low'
            },
            'system': {
                'memory_usage_mb': metrics.memory_usage,
                'cpu_usage_percent': metrics.cpu_usage,
                'status': 'healthy' if metrics.error_rate < 0.05 else 'degraded'
            },
            'recommendations': self._generate_recommendations(metrics)
        }
        
        return report
    
    def _get_performance_grade(self, avg_latency: float) -> str:
        """根据平均延迟获取性能等级"""
        if avg_latency < 5:
            return 'excellent'
        elif avg_latency < 10:
            return 'good'
        elif avg_latency < 20:
            return 'fair'
        elif avg_latency < 50:
            return 'poor'
        else:
            return 'critical'
    
    def _generate_recommendations(self, metrics: PerformanceMetrics) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 延迟相关建议
        if metrics.avg_latency > 10:
            recommendations.append("平均延迟过高，建议优化信号处理逻辑")
        
        # 错误率相关建议
        if metrics.error_rate > 0.05:
            recommendations.append("错误率较高，建议检查数据质量和系统稳定性")
        
        # 缓存相关建议
        if metrics.cache_hit_rate < 0.5:
            recommendations.append("缓存命中率较低，建议优化缓存策略")
        
        # 资源使用相关建议
        if metrics.cpu_usage > 80:
            recommendations.append("CPU使用率过高，建议增加资源或优化算法")
        
        if metrics.memory_usage > 1000:  # 1GB
            recommendations.append("内存使用量过高，建议优化内存管理")
        
        if not recommendations:
            recommendations.append("系统运行良好，继续保持")
        
        return recommendations


# 全局性能监控器
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


# 便捷函数
def record_signal_performance(code: str, source: str, latency: float, success: bool = True, error_message: str = ""):
    """记录信号性能"""
    monitor = get_performance_monitor()
    monitor.record_signal(code, source, latency, success, error_message)


def get_performance_report() -> Dict[str, Any]:
    """获取性能报告"""
    monitor = get_performance_monitor()
    metrics = monitor.get_current_metrics()
    return PerformanceReportGenerator().generate_report(metrics)


def get_performance_stats() -> Dict[str, Any]:
    """获取性能统计"""
    monitor = get_performance_monitor()
    return {
        'current_metrics': monitor.get_current_metrics().__dict__,
        'latency_distribution': monitor.get_latency_distribution(),
        'source_performance': {
            source: monitor.get_source_performance(source)
            for source in ['fast_technical', 'ml', 'ai_hedge']
        }
    }


if __name__ == '__main__':
    # 测试示例
    print("测试性能监控...")
    
    # 记录一些测试数据
    for i in range(100):
        code = f"600{i:03d}"
        latency = np.random.exponential(5)  # 指数分布延迟
        success = np.random.random() > 0.05  # 95%成功率
        record_signal_performance(code, 'fast_technical', latency, success)
        
        if i % 20 == 0:
            time.sleep(0.1)  # 模拟处理时间
    
    # 显示性能报告
    print(f"\n性能报告:")
    report = get_performance_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    
    # 显示详细统计
    print(f"\n详细统计:")
    stats = get_performance_stats()
    print(f"总信号数: {stats['current_metrics']['total_signals']}")
    print(f"平均延迟: {stats['current_metrics']['avg_latency']:.2f}ms")
    print(f"缓存命中率: {stats['current_metrics']['cache_hit_rate']:.2%}")
    print(f"错误率: {stats['current_metrics']['error_rate']:.2%}")
    
    # 显示延迟分布
    print(f"\n延迟分布:")
    distribution = stats['latency_distribution']['distribution']
    for bin_name, count in distribution.items():
        print(f"  {bin_name}: {count}")
    
    # 导出性能指标
    export_path = 'performance_metrics.json'
    get_performance_monitor().export_metrics(export_path)
    print(f"\n性能指标已导出到: {export_path}")