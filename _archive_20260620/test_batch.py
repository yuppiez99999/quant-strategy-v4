import subprocess, json, yaml, os

WIND_CLI = r"C:\Users\Administrator\.agents\skills\wind-mcp-skill\scripts\cli.mjs"
SCRIPT_DIR = r"e:\各种PY程序\12只标的量化策略"

batch = '''@echo off
chcp 65001 >nul
node "C:\\Users\\Administrator\\.agents\\skills\\wind-mcp-skill\\scripts\\cli.mjs" call stock_data get_stock_price_indicators "{\"windcode\":\"601088.SH\",\"indexes\":\"最新成交价\"}"
'''
batch_file = os.path.join(SCRIPT_DIR, '_temp_wind.bat')
with open(batch_file, 'w', encoding='utf-8') as f:
    f.write(batch)

print("Running batch...")
result = subprocess.run(batch_file, capture_output=True, text=True, encoding='utf-8', errors='ignore', cwd=SCRIPT_DIR)
print(f"RC: {result.returncode}")
print(f"STDOUT: {result.stdout[:500] if result.stdout else 'empty'}")
print(f"STDERR: {result.stderr[:200] if result.stderr else 'empty'}")
