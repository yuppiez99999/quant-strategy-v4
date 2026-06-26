# -*- coding: utf-8 -*-
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
logging.disable(logging.CRITICAL)
from daily_report import generate_daily_report
r = generate_daily_report(enable_ai_analysis=False)
with open('_report_result.txt', 'w', encoding='utf-8') as f:
    f.write('LEN=' + str(len(r)) + '\n')
print('DONE')
