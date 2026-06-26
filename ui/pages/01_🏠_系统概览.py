# -*- coding: utf-8 -*-
"""系统概览 — 模块状态、连接器、配置一览"""
import sys, os
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

import streamlit as st

st.title("🏠 系统概览")
st.markdown("量化策略系统 v5.2 — 康波周期 + 十五五规划 + 社保基金ETF追踪")

from ui.components.module_loader import get_system_module

with st.spinner("正在加载系统模块..."):
    try:
        mod = get_system_module()
        st.success("✅ 系统模块加载成功")
    except Exception as e:
        st.error(f"❌ 系统模块加载失败: {e}")
        st.stop()

from ui.components.system_status import render_module_grid, render_connector_status

def _package_available(pkg_name):
    try:
        import importlib
        return importlib.util.find_spec(pkg_name) is not None
    except Exception:
        return False

# === 模块状态 ===
st.subheader("📦 模块可用性")
modules = {
    '数据提供层': mod.data_provider.get('get_quotes_batch') is not None,
    '自动交易系统': mod.auto_trading.get('AutoTradingSystem') is not None,
    '再平衡引擎': mod.rebalance_engine.get('RebalancingEngine') is not None,
    '每日报告': mod.daily_report.get('generate_daily_report') is not None,
    '止损止盈监控': mod.stop_loss.get('StopLossMonitor') is not None,
    '策略注册表': mod.strategy_registry is not None,
    '连接器管理器': mod.connector_manager is not None,
    'ETF资金流向监控': True,
    '投资组合优化': _package_available('pandas') or _package_available('numpy'),
    '康波周期监控': _package_available('yfinance') or _package_available('tushare'),
    '康波周期分析': mod.KONDRATIEV_AVAILABLE,
    '十五五规划': mod.FIFTEEN_FIVE_AVAILABLE,
    '社保基金ETF': mod.SOCIAL_SECURITY_ETF_AVAILABLE,
}
render_module_grid(modules, cols=4)

# === 连接器状态 ===
st.subheader("🔗 数据源连接器")
cs = mod.connector_manager.get_status()
render_connector_status(cs)

# === 配置摘要 ===
st.subheader("⚙️ 配置摘要")
col1, col2, col3 = st.columns(3)
with col1:
    try:
        configs = mod.config_manager.get_all()
        st.metric("配置类别", len(configs))
        for k in configs:
            st.caption(f"  • {k}")
    except Exception as e:
        st.warning(f"配置加载异常: {e}")
with col2:
    st.metric("已注册策略", len(mod.strategy_registry.list()))
    for sid in mod.strategy_registry.list():
        s = mod.strategy_registry.get(sid)
        st.caption(f"  • {s['name']} v{s['version']}")
with col3:
    st.metric("监测ETF数量", len(mod.ETFFundFlowMonitor.ETF_LIST))
    st.metric("监测商品数量", len(mod.KommoCommodityMonitor.COMMODITY_LIST))

# === 配置文件检查 ===
st.subheader("📋 配置文件")
cf_cols = st.columns(4)
config_files = [
    'config/portfolio.yaml', 'config/settings.yaml',
    'config/positions.json', 'config/rebalance.yaml',
    'config/risk.yaml',
]
for i, cf in enumerate(config_files):
    path = os.path.join(_BASE_DIR, cf)
    exists = os.path.exists(path)
    with cf_cols[i % 4]:
        st.markdown(f"{'✅' if exists else '❌'} `{cf}`")

# === 目录状态 ===
st.subheader("📁 目录状态")
d_cols = st.columns(3)
dirs = [
    ("数据缓存", os.path.join(_BASE_DIR, 'data', 'cache')),
    ("报告目录", os.path.join(_BASE_DIR, 'reports')),
    ("日志目录", mod.LOG_DIR),
]
for i, (label, dpath) in enumerate(dirs):
    with d_cols[i]:
        if os.path.exists(dpath):
            cnt = len(os.listdir(dpath))
            st.metric(label, f"{cnt} 个条目")
        else:
            st.metric(label, "不存在")

# === 降级状态 ===
st.subheader("🛡️ 优雅降级")
fallback = mod.graceful_fallback.is_fallback_mode()
if fallback:
    st.warning("⚠️ 当前处于降级模式 — 部分数据源不可用，已自动切换到备用数据源")
else:
    st.success("✅ 系统正常运行，未触发降级")

# 刷新
if st.button("🔄 刷新系统状态"):
    st.cache_resource.clear()
    st.rerun()
