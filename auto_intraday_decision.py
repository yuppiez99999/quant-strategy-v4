#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
盘中自动决策调度器
在交易时段定时调用GLM5生成交易决策

使用方式:
    python auto_intraday_decision.py              # 启动定时调度
    python auto_intraday_decision.py --once       # 只执行一次
    python auto_intraday_decision.py --test       # 测试模式(不调用API)
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

# 设置编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path(__file__).parent / 'logs' / 'intraday_decision.log',
            encoding='utf-8'
        ) if (Path(__file__).parent / 'logs').exists() else logging.NullHandler(),
    ]
)
logger = logging.getLogger(__name__)


# 交易时段配置
TRADING_HOURS = {
    'morning_start': '09:30',
    'morning_end': '11:30',
    'afternoon_start': '13:00',
    'afternoon_end': '15:00',
}

# 决策时间点(交易时段内每小时检查一次)
DECISION_TIMES = [
    '09:35',  # 开盘后5分钟
    '10:35',  # 上午盘中
    '11:25',  # 上午收盘前
    '13:05',  # 午后开盘
    '14:05',  # 下午盘中
    '14:50',  # 收盘前10分钟
]


def is_trading_day() -> bool:
    """判断是否为交易日(周一至周五,排除节假日)"""
    today = datetime.now()
    # 周末不交易
    if today.weekday() >= 5:
        return False
    # TODO: 添加节假日判断
    return True


def is_trading_time() -> bool:
    """判断当前是否在交易时段内"""
    if not is_trading_day():
        return False
    
    now = datetime.now().strftime('%H:%M')
    return (
        TRADING_HOURS['morning_start'] <= now <= TRADING_HOURS['morning_end'] or
        TRADING_HOURS['afternoon_start'] <= now <= TRADING_HOURS['afternoon_end']
    )


def should_run_decision() -> bool:
    """判断是否应该执行决策(在决策时间点附近5分钟内)"""
    if not is_trading_day():
        return False
    
    now = datetime.now()
    current_time = now.strftime('%H:%M')
    
    for decision_time in DECISION_TIMES:
        dt = datetime.strptime(decision_time, '%H:%M')
        diff = abs((now.hour * 60 + now.minute) - (dt.hour * 60 + dt.minute))
        if diff <= 5:  # 5分钟窗口
            return True
    
    return False


def run_decision_once(test_mode: bool = False) -> dict:
    """
    执行一次决策
    
    Args:
        test_mode: 测试模式(不调用API)
        
    Returns:
        执行结果
    """
    result = {
        'timestamp': datetime.now().isoformat(),
        'success': False,
        'trading_signals': 0,
        'risk_alerts': 0,
        'report_path': '',
        'error': '',
    }
    
    try:
        from utils.intraday_decision import IntradayDecisionMonitor
        
        logger.info("=" * 70)
        logger.info("开始盘中决策检查")
        logger.info("=" * 70)
        
        # 创建监控器
        monitor = IntradayDecisionMonitor(
            api_model='glm-4-plus',
            check_interval=300,
            enable_notifications=True,
        )
        
        # 加载持仓
        if not monitor.load_positions():
            result['error'] = '持仓数据加载失败'
            logger.error(result['error'])
            return result
        
        logger.info(f"已加载 {len(monitor.positions)} 只持仓")
        
        if test_mode:
            logger.info("[测试模式] 跳过API调用")
            result['success'] = True
            result['error'] = '测试模式'
            return result
        
        # 生成决策
        logger.info("正在调用GLM5生成交易决策...")
        decision = monitor.generate_decision()
        
        if not decision:
            result['error'] = '决策生成失败'
            logger.error(result['error'])
            return result
        
        result['trading_signals'] = len(decision.trading_signals)
        result['risk_alerts'] = len(decision.risk_alerts)
        
        logger.info(f"决策生成完成 - 交易信号: {result['trading_signals']}条, 风险预警: {result['risk_alerts']}条")
        
        # 检查风险预警
        critical_alerts = [
            a for a in decision.risk_alerts
            if a.severity in ['CRITICAL', 'HIGH']
        ]
        
        if critical_alerts:
            logger.warning(f"发现 {len(critical_alerts)} 条高风险预警:")
            for alert in critical_alerts:
                logger.warning(f"  [{alert.severity}] {alert.message}")
        
        # 导出报告
        report_path = monitor.export_report(decision)
        result['report_path'] = report_path
        result['success'] = True
        
        logger.info(f"决策报告已保存: {report_path}")
        logger.info("=" * 70)
        logger.info("盘中决策检查完成")
        logger.info("=" * 70)
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"决策执行异常: {e}", exc_info=True)
    
    return result


def start_scheduler():
    """启动定时调度器"""
    logger.info("=" * 70)
    logger.info("盘中自动决策调度器已启动")
    logger.info(f"决策时间点: {', '.join(DECISION_TIMES)}")
    logger.info("=" * 70)
    
    last_run_date = None
    run_times = set()  # 当天已执行的时间点
    
    try:
        while True:
            now = datetime.now()
            today = now.strftime('%Y-%m-%d')
            current_time = now.strftime('%H:%M')
            
            # 新的一天,重置执行记录
            if today != last_run_date:
                last_run_date = today
                run_times = set()
                logger.info(f"新交易日开始: {today}")
            
            # 检查是否应该执行决策
            if is_trading_day() and current_time in DECISION_TIMES and current_time not in run_times:
                logger.info(f"到达决策时间点: {current_time}")
                run_times.add(current_time)
                
                # 执行决策
                result = run_decision_once()
                
                if result['success']:
                    logger.info(f"决策执行成功 - 信号: {result['trading_signals']}, 预警: {result['risk_alerts']}")
                else:
                    logger.error(f"决策执行失败: {result['error']}")
            
            # 等待1分钟再检查
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("收到中断信号,停止调度器")
    except Exception as e:
        logger.error(f"调度器异常: {e}", exc_info=True)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='盘中自动决策调度器')
    parser.add_argument('--once', action='store_true', help='只执行一次决策')
    parser.add_argument('--test', action='store_true', help='测试模式(不调用API)')
    parser.add_argument('--schedule', action='store_true', help='启动定时调度')
    args = parser.parse_args()
    
    if args.once:
        # 只执行一次
        result = run_decision_once(test_mode=args.test)
        
        print("\n" + "=" * 70)
        print("执行结果:")
        print(f"  成功: {result['success']}")
        print(f"  交易信号: {result['trading_signals']}")
        print(f"  风险预警: {result['risk_alerts']}")
        print(f"  报告路径: {result['report_path']}")
        if result['error']:
            print(f"  错误: {result['error']}")
        print("=" * 70)
        
    elif args.test:
        # 测试模式
        print("=" * 70)
        print("盘中决策调度器 - 测试模式")
        print("=" * 70)
        
        print(f"\n当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"是否交易日: {'是' if is_trading_day() else '否'}")
        print(f"是否交易时段: {'是' if is_trading_time() else '否'}")
        print(f"是否决策时间: {'是' if should_run_decision() else '否'}")
        print(f"\n决策时间点: {', '.join(DECISION_TIMES)}")
        
        print("\n测试执行决策(不调用API)...")
        result = run_decision_once(test_mode=True)
        print(f"结果: {result}")
        
    elif args.schedule:
        # 启动定时调度
        start_scheduler()
        
    else:
        # 默认: 执行一次
        result = run_decision_once(test_mode=args.test)
        
        print("\n" + "=" * 70)
        print("执行结果:")
        print(f"  成功: {result['success']}")
        print(f"  交易信号: {result['trading_signals']}")
        print(f"  风险预警: {result['risk_alerts']}")
        print(f"  报告路径: {result['report_path']}")
        if result['error']:
            print(f"  错误: {result['error']}")
        print("=" * 70)
        
        print("\n提示:")
        print("  --once     只执行一次决策")
        print("  --test     测试模式(不调用API)")
        print("  --schedule 启动定时调度(交易时段每小时检查)")


if __name__ == '__main__':
    main()
