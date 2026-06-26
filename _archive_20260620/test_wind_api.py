# -*- coding: utf-8 -*-
"""
测试 Wind API 连接
"""

from wind_trading import WindClient
import time

def main():
    print("🔌 测试 Wind API 连接...")
    
    client = WindClient()
    
    codes = ['601088', '600995', '300274']
    quotes = client.get_realtime_quote(codes)
    
    print("\n📊 获取到的行情数据:")
    for code, quote in quotes.items():
        is_mock = "(模拟)" if quote.get('is_mock', False) else ""
        print(f"  {code}: 现价={quote['price']:.2f} {is_mock}")
        print(f"    最高: {quote['high']:.2f}, 最低: {quote['low']:.2f}")
        print(f"    时间: {quote['time']}")
    
    client.disconnect()
    print("\n✅ 测试完成")

if __name__ == "__main__":
    main()
