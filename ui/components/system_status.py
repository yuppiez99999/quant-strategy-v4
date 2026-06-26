# -*- coding: utf-8 -*-
"""系统状态徽章组件"""
import streamlit as st


def status_badge(available: bool, label: str) -> str:
    """返回状态徽章HTML"""
    color = "#52c41a" if available else "#ff4d4f"
    icon = "✅" if available else "❌"
    return f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;background:{color}20;color:{color};font-size:13px;margin:2px;">{icon} {label}</span>'


def render_module_grid(modules: dict, cols: int = 3):
    """以卡片网格渲染模块可用性状态"""
    items = list(modules.items())
    rows = [items[i:i + cols] for i in range(0, len(items), cols)]

    for row in rows:
        columns = st.columns(cols)
        for i, (name, available) in enumerate(row):
            with columns[i]:
                border = "#52c41a" if available else "#ff4d4f"
                bg = "#f6ffed" if available else "#fff2f0"
                st.markdown(
                    f"""<div style="padding:12px;border-radius:8px;border-left:4px solid {border};
                    background:{bg};margin-bottom:8px;">
                    <div style="font-size:16px;">{'✅' if available else '❌'} {name}</div>
                    <div style="font-size:12px;color:#888;">{'可用' if available else '不可用'}</div>
                    </div>""",
                    unsafe_allow_html=True
                )


def render_connector_status(status: dict):
    """渲染数据源连接器状态"""
    cols = st.columns(4)
    with cols[0]:
        st.metric("活跃连接器", status.get('active_connector') or 'None')
    with cols[1]:
        fallback = status.get('fallback_mode', False)
        st.metric("降级模式", "⚠️ 是" if fallback else "✅ 否")
    with cols[2]:
        st.metric("已注册", status.get('total_connectors', 0))
    with cols[3]:
        st.metric("可用", status.get('available_connectors', 0))
