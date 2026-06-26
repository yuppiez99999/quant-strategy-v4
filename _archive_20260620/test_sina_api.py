# -*- coding: utf-8 -*-
"""
测试新浪财经API连接
"""

import requests
import re

def test_sina_api():
    codes = ['601088', '600995', '300274']
    sina_codes = [f'sh{c}' if c.startswith('6') else f'sz{c}' for c in codes]
    url = 'http://hq.sinajs.cn/list=' + ','.join(sina_codes)
    
    print('🔌 测试新浪财经API...')
    try:
        resp = requests.get(url, timeout=10)
        resp.encoding = 'gbk'
        
        if resp.status_code == 200:
            print('✅ 新浪财经连接成功!')
            print('\n返回数据:')
            lines = resp.text.split('\n')
            for line in lines[:5]:
                if line:
                    match = re.search(r'var hq_str_([a-z]{2}\d{6})=\"([^\"]+)\"', line)
                    if match:
                        data = match.group(2).split(',')
                        code = match.group(1)
                        name = data[0]
                        price = data[3]
                        print(f'  {code} {name}: 现价={price}')
            return True
        else:
            print(f'❌ 连接失败: {resp.status_code}')
            return False
    except Exception as e:
        print(f'❌ 连接异常: {e}')
        return False

if __name__ == '__main__':
    test_sina_api()
