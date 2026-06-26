# -*- coding: utf-8 -*-
"""测试数据提供层"""

from wind_data_provider import get_quote, get_quotes_batch

if __name__ == '__main__':
    print("=" * 60)
    print("测试数据提供层")
    print("=" * 60)
    
    # 测试单只股票
    print("\n--- 测试单只股票 ---")
    codes = ['601088', '002371', '300308', '688041', '518880']
    
    for code in codes:
        result = get_quote(code, is_fund=(code.startswith('5')))
        print(f"{code}: 价格={result['price']:.2f}, 来源={result['source']}")
    
    # 测试批量获取
    print("\n--- 测试批量获取 ---")
    stocks = ['601088', '002371', '688041']
    funds = ['518880']
    quotes = get_quotes_batch(stocks, funds)
    
    print(f"成功获取: {len(quotes)}/{len(stocks)+len(funds)}")
    for code, data in quotes.items():
        print(f"  {code}: ¥{data['price']:.2f} ({data['source']})")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)