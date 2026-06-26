"""
快速附加期货期权信号到综合日报
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signals.futures_options_signal import FuturesOptionsSignalGenerator

# 运行信号生成器
generator = FuturesOptionsSignalGenerator()
result = generator.run_full_pipeline()

# 附加到综合日报
report_path = r'e:\各种PY程序\每日报告归档\2026-06-24\综合日报_20260624.txt'
with open(report_path, 'a', encoding='utf-8') as f:
    f.write('\n\n')
    f.write('='*80 + '\n')
    f.write(result['report'])
    f.write('\n')

print(f'[OK] 期货期权信号已附加到: {report_path}')
