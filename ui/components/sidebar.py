# -*- coding: utf-8 -*-
"""公共侧边栏组件"""
import streamlit as st
from datetime import datetime


def render_sidebar():
    """渲染全局侧边栏"""
    with st.sidebar:
        st.markdown("## 📊 量化策略系统 v5.2")
        st.markdown("— 康波周期 + 十五五规划 + 社保基金ETF追踪")
        st.markdown("---")

        st.markdown(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        st.markdown("---")
        st.markdown("### 📌 快速导航")
        st.caption("使用左侧页面菜单切换功能模块")

        st.markdown("---")
        st.markdown("### 🔗 快捷操作")
        if st.button("🔍 系统健康检查", use_container_width=True):
            st.switch_page("pages/01_🏠_系统概览.py")
        if st.button("📊 持仓监控", use_container_width=True):
            st.switch_page("pages/02_📊_实时监控.py")
        if st.button("🔬 宏观综合分析", use_container_width=True):
            st.switch_page("pages/10_🔬_宏观综合分析.py")

        st.markdown("---")
        st.caption(f"工作目录: `11_量化策略`")
