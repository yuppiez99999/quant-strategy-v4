# -*- coding: utf-8 -*-
"""Wind MCP Fetcher 测试脚本"""
import sys
sys.path.insert(0, r'e:\各种PY程序\11_量化策略')

from wind_mcp_fetcher import wind_check_connection, wind_get_quote, wind_get_batch_quotes

print('=== Wind MCP 连接检查 ===')
c = wind_check_connection()
print(f"  连接状态: {c['connected']}")
print(f"  API Key: {'已配置' if c['api_key_set'] else '未配置'}")
print(f"  延迟: {c['latency_ms']}ms")
if c.get('test_price'):
    print(f"  测试价格(510300): {c['test_price']}")

print('\n=== 单只查询 (588000 科创50ETF) ===')
q = wind_get_quote('588000', is_fund=True)
if q:
    print(f"  价格: {q['price']}")
    print(f"  涨跌: {q.get('change', 'N/A')}%")
    print(f"  来源: {q['source']}")
    print(f"  耗时: {q.get('elapsed', 'N/A')}s")
else:
    print('  失败!')

print('\n=== 批量查询 (3只ETF) ===')
batch = wind_get_batch_quotes(['588000', '159915', '518880'], is_fund=True)
for k, v in batch.items():
    print(f"  {k}: 价格={v['price']} 来源={v['source']}")

print(f'\n总计: {len(batch)}/3 成功')
