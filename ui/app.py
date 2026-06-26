# -*- coding: utf-8 -*-
"""
量化策略系统 v5.2 — Streamlit 多页面 UI 主入口
"""

import sys
import os

# 确保主项目目录在 path 中
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

import streamlit as st

st.set_page_config(
    page_title="量化策略系统 v5.2",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 多页面导航 — Streamlit 会自动发现 pages/ 目录
# 用户通过左侧导航切换页面

pg = st.navigation({
    "🏠 系统": [
        st.Page("pages/01_🏠_系统概览.py", title="系统概览"),
        st.Page("pages/02_📊_实时监控.py", title="实时监控"),
        st.Page("pages/12_📝_报告管理.py", title="报告管理"),
    ],
    "🔄 交易与风控": [
        st.Page("pages/03_🔄_再平衡执行.py", title="再平衡执行"),
        st.Page("pages/05_🛡️_风险监控.py", title="风险监控"),
    ],
    "📈 策略分析": [
        st.Page("pages/04_📈_投资组合优化.py", title="投资组合优化"),
        st.Page("pages/06_💰_ETF资金流向.py", title="ETF资金流向"),
        st.Page("pages/11_💎_大宗商品监控.py", title="大宗商品监控"),
    ],
    "🔬 v5.2 宏观分析": [
        st.Page("pages/07_🌊_康波周期分析.py", title="康波周期分析"),
        st.Page("pages/08_🏛️_十五五规划.py", title="十五五规划"),
        st.Page("pages/09_🏦_社保基金追踪.py", title="社保基金追踪"),
        st.Page("pages/10_🔬_宏观综合分析.py", title="宏观综合分析"),
    ],
})

pg.run()
