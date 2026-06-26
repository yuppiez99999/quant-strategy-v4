# -*- coding: utf-8 -*-
"""测试 ModelScope SDK 导入"""
import sys
print("Python版本:", sys.version)

# 测试 zoneinfo
try:
    import zoneinfo
    print("OK zoneinfo 已安装")
except ImportError as e:
    print("FAIL zoneinfo 导入失败:", e)
    try:
        from backports import zoneinfo
        print("OK backports.zoneinfo 可用")
        # 注入到标准库位置
        sys.modules['zoneinfo'] = zoneinfo
        print("OK 已注入 zoneinfo 到 sys.modules")
    except ImportError:
        print("FAIL backports.zoneinfo 也未安装")

# 再次测试
try:
    import zoneinfo
    print("OK zoneinfo 现在可用")
except:
    pass

# 测试 modelscope
try:
    from modelscope.msdatasets import MsDataset
    print("OK ModelScope SDK 导入成功")
except Exception as e:
    print("FAIL ModelScope SDK 导入失败:", e)
    import traceback
    traceback.print_exc()
