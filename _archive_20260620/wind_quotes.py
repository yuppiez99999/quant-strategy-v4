import subprocess, json, yaml, os, tempfile, time

WIND_CLI = r"C:\Users\Administrator\.agents\skills\wind-mcp-skill\scripts\cli.mjs"
SCRIPT_DIR = r"e:\各种PY程序\12只标的量化策略"

def get_price(windcode):
    """获取价格，对超时错误自动重试（最多2次，间隔3秒）"""
    ps_script = f'''node "{WIND_CLI}" call stock_data get_stock_price_indicators '{{\\"windcode\\":\\"{windcode}\\",\\"indexes\\":\\"最新成交价,涨跌幅\\"}}'
'''
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            r = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True, text=True, encoding='utf-8', errors='ignore',
                cwd=SCRIPT_DIR, timeout=30
            )
            if r.stdout:
                d = json.loads(r.stdout)
                if d.get('content'):
                    rows = json.loads(d['content'][0]['text'])['data']['rows'][0]
                    return {'price': float(rows[0]), 'change': float(rows[1]) if len(rows) > 1 else 0}
        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                time.sleep(3)
                continue
        except Exception:
            pass
        break
    return {'price': 0, 'change': 0}

with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
    assets = yaml.safe_load(f)['assets']

print('='*60)
print('📊 Wind 实时行情监控')
print('='*60)
print(f'{"名称":<10} {"代码":<10} {"价格":>10} {"涨跌":>8}')
print('-'*60)

for a in assets:
    code = a['code']
    windcode = f'{code}.SH' if code.startswith('6') else f'{code}.SZ'
    r = get_price(windcode)
    print(f'{a["name"]:<10} {code:<10} {r["price"]:>10.2f} {r["change"]:>+7.2f}%')

print('='*60)
