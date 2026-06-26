import subprocess, json, yaml, time
from datetime import datetime

WIND_CLI = r"C:\Users\Administrator\.agents\skills\wind-mcp-skill\scripts\cli.mjs"

def get_stock_price(code):
    """获取股票价格，对超时错误自动重试（最多2次，间隔3秒）"""
    windcode = f'{code}.SH' if code.startswith('6') else f'{code}.SZ'
    ps_script = f'node "{WIND_CLI}" call stock_data get_stock_price_indicators \'{{\\"windcode\\":\\"{windcode}\\",\\"indexes\\":\\"最新成交价,涨跌幅\\"}}\''
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            r = subprocess.run(['powershell', '-Command', ps_script], capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30)
            if r.stdout:
                d = json.loads(r.stdout)
                if d.get('content'):
                    rows = json.loads(d['content'][0]['text'])['data']['rows'][0]
                    return {'price': float(rows[0]), 'change': float(rows[1])}
        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                time.sleep(3)
                continue
        except Exception:
            pass
        break
    return {'price': 0, 'change': 0}

def get_fund_price(code):
    """获取基金价格，对超时错误自动重试（最多2次，间隔3秒）"""
    windcode = f'{code}.SH' if code.startswith('5') else f'{code}.SZ'
    ps_script = f'node "{WIND_CLI}" call fund_data get_fund_price_indicators \'{{\\"windcode\\":\\"{windcode}\\",\\"indexes\\":\\"最新成交价,涨跌幅\\"}}\''
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            r = subprocess.run(['powershell', '-Command', ps_script], capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30)
            if r.stdout:
                d = json.loads(r.stdout)
                if d.get('content'):
                    rows = json.loads(d['content'][0]['text'])['data']['rows'][0]
                    return {'price': float(rows[0]), 'change': float(rows[1])}
        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                time.sleep(3)
                continue
        except Exception:
            pass
        break
    return {'price': 0, 'change': 0}

def main():
    print("="*70)
    print("🚀 Wind API 实时模拟交易系统")
    print("="*70)

    with open('config/portfolio.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    assets = config['assets']
    names = {a['code']: a['name'] for a in assets}
    weights = {a['code']: a['target_weight'] for a in assets}

    print(f"\n📅 系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 监控标的: {len(assets)} 只")
    print(f"💰 初始资金: ¥1,000,000")

    print(f"\n⏳ 获取Wind实时行情...")
    quotes = {}
    for a in assets:
        code = a['code']
        if code.startswith('5'):
            r = get_fund_price(code)
        else:
            r = get_stock_price(code)
        quotes[code] = r
        status = "✅" if r['price'] > 0 else "❌"
        print(f"  {status} {a['name']}: ¥{r['price']:.2f} ({r['change']:+.2f}%)")

    initial_capital = 1000000
    cash = initial_capital
    positions = {}
    positions_value = 0

    print(f"\n{'='*70}")
    print("📋 初始持仓 (按目标权重配置)")
    print(f"{'='*70}")

    for a in assets:
        code = a['code']
        price = quotes[code]['price']
        if price > 0:
            target_w = weights[code]
            target_amount = initial_capital * target_w
            shares = int(target_amount / price / 100) * 100
            cost = shares * price * 1.0005
            if cost <= cash:
                cash -= cost
                positions[code] = {'shares': shares, 'avg_cost': price, 'name': names[code]}
                mv = shares * price
                positions_value += mv
                print(f"  {names[code]:<12} 买入 {shares:>6} 股 @ ¥{price:>8.2f} = ¥{mv:>12,.0f}")

    total = cash + positions_value
    print(f"\n{'='*70}")
    print("📊 账户状态")
    print(f"{'='*70}")
    print(f"💵 可用现金: ¥{cash:>12,.2f}")
    print(f"📈 持仓市值: ¥{positions_value:>12,.2f}")
    print(f"💰 账户总值: ¥{total:>12,.2f}")
    print(f"{'='*70}")
    print("\n✅ Wind实时行情模拟盘已启动!")
    print("   按 Ctrl+C 停止\n")

if __name__ == "__main__":
    main()
