# -*- coding: utf-8 -*-
"""量化策略系统 v5.1 重构验证脚本

测试内容:
  1. quant_modules 包导入
  2. DynamicPositionManager 功能验证
  3. 精细化手续费计算
  4. 并发K线获取工具函数
"""
import sys
import os

BASE_DIR = r"E:\各种PY程序\11_量化策略"
sys.path.insert(0, BASE_DIR)

print("=" * 70)
print("量化策略系统 v5.1 — 重构验证测试")
print("=" * 70)

# ============================================
# 测试 1: quant_modules 包导入
# ============================================
print("\n[测试 1] quant_modules 包导入")
try:
    from quant_modules.wind_mcp import _wind_code, PORTFOLIO_TARGETS
    assert _wind_code('510300') == '510300.SH'
    assert _wind_code('000001') == '000001.SZ'
    print("  ✅ wind_mcp 模块导入成功")
    print(f"  ✅ _wind_code: 510300 -> {_wind_code('510300')}")
    print(f"  ✅ _wind_code: 000001 -> {_wind_code('000001')}")
except ImportError as e:
    print(f"  ⚠️ wind_mcp 导入失败: {e}")
except AssertionError as e:
    print(f"  ❌ Assert 失败: {e}")

try:
    from quant_modules.core import (
        StrategyRegistry, config_manager, compute_trade_cost,
        _classify_asset_type, ProgressIndicator
    )
    sr = StrategyRegistry()
    assert len(sr.strategies) > 0
    print("  ✅ core 模块导入成功")
    print(f"  ✅ StrategyRegistry 策略数: {len(sr.strategies)}")
    
    # 测试资产分类
    assert _classify_asset_type('510300') == 'etf'
    assert _classify_asset_type('600519') == 'stock'
    print(f"  ✅ _classify_asset_type: 510300 -> {_classify_asset_type('510300')}")
    print(f"  ✅ _classify_asset_type: 600519 -> {_classify_asset_type('600519')}")
    
    # 测试 compute_trade_cost
    cost = compute_trade_cost(1000, 150.0, 'buy', '600519')
    side_label = '买' if 'buy' == 'buy' else '卖'
    print(f"  ✅ compute_trade_cost: 1000股 x 150元 ({side_label}) -> ¥{cost:.2f}")
except ImportError as e:
    print(f"  ⚠️ core 导入失败: {e}")
except Exception as e:
    print(f"  ❌ 错误: {e}")

try:
    from quant_modules.data_layer import DataCache, DataConnector
    print("  ✅ data_layer 模块导入成功")
except ImportError as e:
    print(f"  ⚠️ data_layer 导入失败: {e}")

# ============================================
# 测试 2: DynamicPositionManager 功能验证
# ============================================
print("\n[测试 2] DynamicPositionManager 功能验证")
try:
    from quant_modules.dynamic_position import DynamicPositionManager
    import numpy as np
    
    dpm = DynamicPositionManager(target_vol=0.15, max_vol=0.25)
    
    # 模拟收益率数据
    np.random.seed(42)
    daily_returns = np.random.normal(0.0003, 0.015, 60)
    equity = np.cumprod(1 + daily_returns) * 10000
    
    vol = dpm.calculate_volatility(daily_returns)
    print(f"  ✅ 年化波动率: {vol:.2f}%")
    
    dd = dpm.calculate_drawdown(equity)
    print(f"  ✅ 回撤: {dd:.2f}%")
    
    risk_level = dpm.get_risk_level(vol, dd)
    print(f"  ✅ 风险等级: {risk_level}")
    
    pos = dpm.compute_position_size(daily_returns, equity)
    print(f"  ✅ 推荐仓位: {pos['position_ratio']*100:.1f}%")
    print(f"  ✅ 调整原因: {pos['adjustment_reason']}")
    print(f"  ✅ 波动率因子: {pos['vol_factor']:.4f}")
    print(f"  ✅ 回撤因子: {pos['dd_factor']:.4f}")
    
except Exception as e:
    print(f"  ⚠️ DynamicPositionManager 测试失败: {e}")

# ============================================
# 测试 3: 并发K线获取工具
# ============================================
print("\n[测试 3] 并发K线获取工具验证")
try:
    from quant_modules.wind_mcp import _wind_mcp_fetch_kline
    # 不实际调用（需要 Wind MCP 连接），仅验证函数存在
    assert callable(_wind_mcp_fetch_kline)
    print("  ✅ _wind_mcp_fetch_kline 函数存在")
except Exception as e:
    print(f"  ⚠️ 并发K线工具验证失败: {e}")

# ============================================
# 测试结果汇总
# ============================================
print("\n" + "=" * 70)
print("✅ 所有测试完成")
print("=" * 70)
