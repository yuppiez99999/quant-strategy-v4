import subprocess, json, yaml, time

WIND_CLI = r"C:\Users\Administrator\.agents\skills\wind-mcp-skill\scripts\cli.mjs"

def get_price(windcode):
    """获取价格，对超时错误自动重试（最多2次，间隔3秒）"""
    cmd = f'node "{WIND_CLI}" call stock_data get_stock_price_indicators \'{{\\"windcode\\":\\"{windcode}\\",\\"indexes\\":\\"最新成交价,涨跌幅\\"}}\''
    print(f"CMD: {cmd[:80]}...")
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30)
            print(f"RC: {r.returncode}")
            print(f"STDOUT: {r.stdout[:200] if r.stdout else 'empty'}")
            print(f"STDERR: {r.stderr[:200] if r.stderr else 'empty'}")
            if r.returncode == 0 and r.stdout:
                d = json.loads(r.stdout)
                if d.get('content'):
                    rows = json.loads(d['content'][0]['text'])['data']['rows'][0]
                    return {'price': float(rows[0]), 'change': float(rows[1])}
        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                print(f"超时，3秒后重试({attempt+1}/{max_retries})...")
                time.sleep(3)
                continue
            print(f"Error: 调用超时")
        except Exception as e:
            # 非超时错误，不重试
            print(f"Error: {e}")
            return {'price': 0, 'change': 0}
        break
    return {'price': 0, 'change': 0}

with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
    assets = yaml.safe_load(f)['assets']

a = assets[0]
code = a['code']
windcode = f'{code}.SH' if code.startswith('6') else f'{code}.SZ'
print(f'Testing {a["name"]} ({windcode})')
r = get_price(windcode)
print(f'Result: {r}')
