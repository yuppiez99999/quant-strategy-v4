"""
期货期权信号集成脚本
====================
将期货期权交易信号集成到每日综合日报中

用法:
  python integrate_futures_options.py [--append-to-report]
  
作者: 量化策略系统 v5.2
日期: 2026-06-24
"""

import os
import sys
from datetime import datetime

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signals.futures_options_signal import FuturesOptionsSignalGenerator


def append_to_daily_report(report_content: str, archive_dir: str = None) -> str:
    """
    将期货期权信号附加到每日综合日报
    
    Args:
        report_content: 期货期权报告内容
        archive_dir: 归档目录路径
        
    Returns:
        合并后的完整报告路径
    """
    if archive_dir is None:
        archive_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '每日报告归档', datetime.now().strftime('%Y-%m-%d'))
    
    os.makedirs(archive_dir, exist_ok=True)
    
    # 查找最新的综合日报
    daily_report = None
    for fname in os.listdir(archive_dir):
        if '综合日报' in fname and fname.endswith('.txt'):
            daily_report = os.path.join(archive_dir, fname)
            break
    
    if daily_report and os.path.exists(daily_report):
        # 读取现有报告
        with open(daily_report, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        # 附加期货期权信号
        merged = existing_content + "\n\n" + "="*80 + "\n" + report_content + "\n"
        
        # 保存
        with open(daily_report, 'w', encoding='utf-8') as f:
            f.write(merged)
        
        print(f"[OK] 已附加期货期权信号到: {daily_report}")
        return daily_report
    else:
        print("[WARN] 未找到综合日报,期货期权报告已单独保存")
        return None


def main():
    """主函数"""
    print("\n" + "="*80)
    print("[INFO] 期货期权交易信号集成 - 开始")
    print("="*80 + "\n")
    
    # 运行信号生成器
    generator = FuturesOptionsSignalGenerator()
    result = generator.run_full_pipeline()
    
    # 获取报告内容
    report_content = result['report']
    
    # 如果命令行参数包含 --append-to-report,则附加到每日报告
    if '--append-to-report' in sys.argv:
        archive_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '每日报告归档', datetime.now().strftime('%Y-%m-%d'))
        append_to_daily_report(report_content, archive_dir)
    
    # 打印摘要
    print("\n" + "="*80)
    print("[SUMMARY] 期货期权信号摘要")
    print("="*80)
    print(f"生成信号数: {len(result['signals'])}")
    print(f"AI建议数: {len(result['recommendations'])}")
    print(f"报告路径: {result['filepath']}")
    print("="*80 + "\n")
    
    return result


if __name__ == '__main__':
    main()
