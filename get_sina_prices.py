# -*- coding: utf-8 -*-
"""
从新浪财经获取实时股票价格
"""

import requests

def get_sina_price(code):
    url = f'https://hq.sinajs.cn/list={code}'
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'gbk'
        data = response.text
        if 'var hq_str_' in data:
            parts = data.split(',')
            if len(parts) > 3:
                name = parts[0].split('_')[-1]
                price = float(parts[3])
                return name, price
    except Exception as e:
        print(f'Error for {code}: {str(e)[:30]}')
    return None, None

# 股票代码映射
code_map = {
    '601088': 'sh601088',  # 中国神华
    '600276': 'sh600276',  # 恒瑞医药
    '600019': 'sh600019',  # 宝钢股份
    '000425': 'sz000425',  # 徐工机械
    '002371': 'sz002371',  # 北方华创
    '002422': 'sz002422',  # 科伦药业
    '300308': 'sz300308',  # 中际旭创
    '300750': 'sz300750',  # 宁德时代
    '688041': 'sh688041',  # 海光信息
    '688981': 'sh688981',  # 中芯国际
    '600219': 'sh600219',  # 南山铝业
    '518880': 'sh518880',  # 黄金ETF
    '000792': 'sz000792',  # 藏格矿业
    '603259': 'sh603259',  # 药明康德
}

print('从新浪财经获取实时股票价格...')
print()

prices = {}
for code, sina_code in code_map.items():
    name, price = get_sina_price(sina_code)
    if name and price:
        prices[code] = {'name': name, 'price': price}
        print('OK {} {}: {}'.format(code, name, price))
    else:
        print('NO {}'.format(code))

print()
print('=' * 50)
print('获取到的价格数据:')
print('=' * 50)
for code in sorted(prices.keys()):
    info = prices[code]
    print('{} {}: {}'.format(code, info['name'], info['price']))

# 输出为Python字典格式，方便复制
print()
print('=' * 50)
print('价格字典 (复制到代码中):')
print('=' * 50)
price_dict = {code: info['price'] for code, info in prices.items()}
print('CURRENT_PRICES =', price_dict)
