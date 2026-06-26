import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests

url = 'https://hq.sinajs.cn/list=sh601088'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("Testing Sina API...")
try:
    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = 'gbk'
    print(f"Status code: {response.status_code}")
    print(f"Response length: {len(response.text)}")
    print(f"Response: {response.text[:100]}...")
except Exception as e:
    print(f"Error: {e}")
