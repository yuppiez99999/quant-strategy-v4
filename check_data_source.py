# -*- coding: utf-8 -*-
"""检查数据下载能力"""
import sys
import os

print("=" * 60)
print("  数据源依赖检查")
print("=" * 60)

# akshare
try:
    import akshare as ak
    print(f"✅ akshare: {ak.__version__}")
except ImportError as e:
    print(f"❌ akshare: {e}")

# requests
try:
    import requests
    print(f"✅ requests: {requests.__version__}")
except ImportError as e:
    print(f"❌ requests: {e}")

# ifind client
try:
    sys.path.insert(0, 'e:\\各种PY程序\\11_量化策略')
    from ifind_client import IFindClient
    c = IFindClient()
    print(f"✅ ifind_client: 可用")
    # 测试一只
    raw = c.get_historical_klines('600519', days=10)
    if raw:
        print(f"   600519 测试成功, {len(raw)} 条")
    else:
        print(f"   600519 测试无数据")
except Exception as e:
    print(f"❌ ifind_client: {e}")

# pandas / pyarrow
try:
    import pandas as pd
    print(f"✅ pandas: {pd.__version__}")
except ImportError as e:
    print(f"❌ pandas: {e}")

# 新浪 API
try:
    import sina_api_helper
    print(f"✅ sina_api_helper")
except Exception as e:
    print(f"❌ sina_api_helper: {e}")
