# -*- coding: utf-8 -*-
"""
收盘报告自动生成器 - 量化策略 v4.3
每日收盘后15:05自动生成持仓报告

功能:
  1. 获取实时收盘行情（优先Wind API）
  2. 生成完整持仓报告（含AI分析）
  3. 自动归档到每日报告目录
  4. 支持手动触发和计划任务两种模式

使用方式:
  python close_report_runner.py          # 立即生成收盘报告
  python close_report_runner.py --dry-run # 仅模拟运行，不保存
"""

import os
import sys
import json
import logging
from datetime import datetime, time as dt_time

# Windows编码修复
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# LLM深度解读集成
try:
    sys.path.insert(0, os.path.join(os.path.dirname(BASE_DIR), '09_配置与依赖'))
    from llm_integration import append_llm_analysis
    _LLM_INTEGRATION_OK = True
except ImportError:
    _LLM_INTEGRATION_OK = False

# 日志配置
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, f'close_report_{datetime.now().strftime("%Y%m%d")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger('CloseReportRunner')


def generate_close_report(dry_run=False):
    """生成收盘报告主函数"""
    logger.info('='*70)
    logger.info(f'  收盘报告自动生成器 v4.3')
    logger.info(f'  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    logger.info('='*70)

    try:
        from daily_report import generate_daily_report
        
        portfolio_file = os.path.join(BASE_DIR, 'config', 'portfolio.yaml')
        
        logger.info('[1/3] 开始生成每日报告...')
        report_content = generate_daily_report(
            portfolio_file=portfolio_file,
            enable_ai_analysis=True
        )
        
        if dry_run:
            logger.info('[DRY-RUN] 模拟模式，不保存报告')
            print('\n' + report_content[:2000] + '...')
            return True

        # LLM深度解读
        if _LLM_INTEGRATION_OK:
            logger.info('[1.5/3] 生成LLM深度解读...')
            try:
                report_content = append_llm_analysis(report_content, context="收盘报告")
                logger.info('      ✅ LLM深度解读完成')
            except Exception as e:
                logger.warning(f'      ⚠️ LLM分析失败: {e}')
        else:
            logger.info('[1.5/3] LLM模块未加载，跳过深度解读')

        # 保存到归档目录
        archive_dir = os.path.join(os.path.dirname(BASE_DIR), '每日报告归档', datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(archive_dir, exist_ok=True)
        archive_path = os.path.join(archive_dir, f'综合日报_{datetime.now().strftime("%Y%m%d")}.txt')
        
        logger.info(f'[2/3] 保存报告到归档目录...')
        with open(archive_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # 同时保存到本地reports目录
        reports_dir = os.path.join(BASE_DIR, 'reports', datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(reports_dir, exist_ok=True)
        local_path = os.path.join(reports_dir, f'close_report_{datetime.now().strftime("%H%M%S")}.txt')
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # 生成报告摘要JSON
        summary = generate_report_summary(report_content)
        summary_path = os.path.join(archive_dir, f'report_summary_{datetime.now().strftime("%Y%m%d")}.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f'[3/3] 报告生成完成')
        logger.info(f'      归档位置: {archive_path}')
        logger.info(f'      本地位置: {local_path}')
        logger.info(f'      摘要文件: {summary_path}')
        
        logger.info('='*70)
        logger.info('  ✅ 收盘报告生成成功')
        logger.info('='*70)
        
        return True
        
    except Exception as e:
        logger.error(f'❌ 报告生成失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return False


def generate_report_summary(report_content):
    """从报告内容中提取摘要信息"""
    lines = report_content.split('\n')
    summary = {
        'report_time': datetime.now().isoformat(),
        'total_value': 0,
        'cash': 0,
        'positions': [],
        'up_count': 0,
        'down_count': 0,
        'best_performer': '',
        'worst_performer': '',
        'ai_recommendations': {'sell': [], 'hold': [], 'buy': []}
    }
    
    for line in lines:
        # 提取账户总值
        if '账户总值' in line:
            try:
                parts = line.split('¥')
                if len(parts) > 1:
                    summary['total_value'] = float(parts[1].replace(',', '').strip())
            except Exception:
                pass
        
        # 提取可用现金
        if '可用现金' in line:
            try:
                parts = line.split('¥')
                if len(parts) > 1:
                    summary['cash'] = float(parts[1].replace(',', '').strip())
            except Exception:
                pass
        
        # 提取持仓明细
        if '市值:' in line and '@' in line:
            try:
                parts = line.split()
                name = parts[1] if len(parts) > 1 else ''
                code = parts[2] if len(parts) > 2 else ''
                shares = int(parts[3].replace('股', '')) if len(parts) > 3 else 0
                summary['positions'].append({
                    'name': name,
                    'code': code,
                    'shares': shares
                })
            except Exception:
                pass
        
        # 提取涨跌数量
        if '上涨标的' in line:
            try:
                summary['up_count'] = int(line.split('上涨标的:')[1].split('只')[0].strip())
            except Exception:
                pass
        if '下跌标的' in line:
            try:
                summary['down_count'] = int(line.split('下跌标的:')[1].split('只')[0].strip())
            except Exception:
                pass
        
        # 提取表现最好/最差
        if '表现最佳' in line:
            summary['best_performer'] = line.split('表现最佳:')[1].strip() if len(line.split('表现最佳:')) > 1 else ''
        if '表现最弱' in line:
            summary['worst_performer'] = line.split('表现最弱:')[1].strip() if len(line.split('表现最弱:')) > 1 else ''
        
        # 提取AI建议
        if '建议清仓' in line:
            summary['ai_recommendations']['sell'] = []
        elif '建议持有' in line:
            summary['ai_recommendations']['hold'] = []
        elif '建议关注' in line:
            summary['ai_recommendations']['buy'] = []
        elif summary['ai_recommendations']['sell'] != [] and '•' in line:
            summary['ai_recommendations']['sell'].append(line.strip().replace('•', '').strip())
        elif summary['ai_recommendations']['hold'] != [] and '•' in line:
            summary['ai_recommendations']['hold'].append(line.strip().replace('•', '').strip())
        elif summary['ai_recommendations']['buy'] != [] and '•' in line:
            summary['ai_recommendations']['buy'].append(line.strip().replace('•', '').strip())
    
    return summary


def is_valid_time_for_report():
    """检查是否在合适的时间生成报告（15:00之后）"""
    now = datetime.now()
    current_time = now.time()
    
    # 收盘后时间：15:00 - 18:00
    if dt_time(15, 0) <= current_time <= dt_time(18, 0):
        return True
    
    # 如果是周末，只在指定时间内允许
    weekday = now.weekday()
    if weekday >= 5:
        logger.info(f'周末({weekday})，建议在工作日收盘后运行')
        return True  # 允许手动触发
    
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='收盘报告自动生成器 v4.3',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='模拟运行，不保存报告')
    parser.add_argument('--force', action='store_true',
                        help='强制生成报告，不检查时间')
    
    args = parser.parse_args()
    
    # 时间检查
    if not args.force and not is_valid_time_for_report():
        logger.warning('⚠️ 当前时间不在收盘报告生成时段(15:00-18:00)')
        logger.warning('   使用 --force 参数强制生成')
        return
    
    success = generate_close_report(dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()