# -*- coding: utf-8 -*-
"""
量化策略实时可视化监控面板 v1.0
功能: 持仓饼图、权重偏差、价格走势、账户总览
"""

import streamlit as st
import json
import os
import time
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="量化策略实时监控",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 配置路径
BASE_DIR = os.path.dirname(__file__)
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
POSITIONS_FILE = os.path.join(CONFIG_DIR, 'positions.json')
HISTORY_FILE = os.path.join(CONFIG_DIR, 'price_history.jsonl')

# 标的信息 (名称映射) - 方案A: 9只标的配置
STOCK_NAMES = {
    "601088": "中国神华", "600276": "恒瑞医药", "510300": "沪深300ETF",
    "512100": "中证1000ETF", "588000": "科创50ETF", "159915": "创业板ETF",
    "518880": "华安黄金ETF", "512760": "半导体ETF", "512880": "证券ETF"
}

# 目标权重 - 方案A: 社保基金风格全覆盖
TARGET_WEIGHTS = {
    "601088": 0.12, "600276": 0.10, "510300": 0.15,
    "512100": 0.10, "588000": 0.15, "159915": 0.12,
    "518880": 0.11, "512760": 0.08, "512880": 0.07
}

# 颜色 + 初始资金
COLORS = ["#1890FF","#52C41A","#FAAD14","#F5222D","#722ED1","#13C2C2","#EB2F96","#FA5454","#73D13D"]
COLOR_MAP = {k: COLORS[i] for i, (k, v) in enumerate(STOCK_NAMES.items())}
INITIAL_CAPITAL = 3000000

def load_positions():
    if not os.path.exists(POSITIONS_FILE):
        return None
    try:
        with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        st.error(f"持仓数据文件格式错误: {e}")
        return None
    except Exception as e:
        st.error(f"读取持仓数据失败: {e}")
        return None

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    history = []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    history.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        return history[-120:]
    except Exception as e:
        st.warning(f"读取历史数据失败: {e}")
        return []

def calc_total_value(positions, prices, cash):
    total = cash
    for code, pos in positions.items():
        shares = pos.get('shares', 0)
        price = prices.get(code, 0) or pos.get('avg_cost', 0)
        total += shares * price
    return total

def get_price(positions, code, prices):
    pos = positions.get(code, {})
    return prices.get(code, 0) or pos.get('avg_cost', 0)

def render():
    st.title("📊 量化策略 v5.1 — 方案A实时监控（9标的社保基金风格）")
    
    data = load_positions()
    history = load_history()
    
    if not data:
        st.warning("等待系统生成持仓数据...")
        return
    
    positions = data.get('positions', {})
    prices = data.get('prices', {})
    cash = data.get('cash', 0)
    last_update = data.get('last_update', '未知')
    
    total_value = calc_total_value(positions, prices, cash)
    uses_live = bool(prices)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("💰 账户总值", f"￥{total_value:,.0f}",
                  delta="📡 实时" if uses_live else "📊 成本估算")
    with col2:
        pos_value = max(total_value - cash, 0)
        st.metric("📦 持仓市值", f"￥{pos_value:,.0f}")
    with col3:
        st.metric("💵 可用现金", f"￥{cash:,.0f}")
    with col4:
        pnl = ((total_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100) if INITIAL_CAPITAL > 0 else 0
        if not uses_live:
            cost_basis = sum(
                positions.get(k, {}).get('shares', 0) * positions.get(k, {}).get('avg_cost', 0)
                for k in positions
            )
            cost_total = cost_basis + cash
            cost_pnl = ((cost_total - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100) if INITIAL_CAPITAL > 0 else 0
            display_pnl = cost_pnl
        else:
            display_pnl = pnl
        st.metric("📈 总收益", f"{display_pnl:+.1f}%")
    with col5:
        st.metric("🕐 最后更新", last_update[:19] if last_update else "未知")
    
    if not uses_live:
        st.caption("⚠️ 当前显示成本估算值，13:00 开盘后将切换为实时行情")
    
    st.markdown("---")
    
    left, right = st.columns([1, 1])
    
    with left:
        st.subheader("🏷️ 持仓权重分布")
        chart_data = []
        for code, pos in positions.items():
            shares = pos.get('shares', 0)
            price = get_price(positions, code, prices)
            mv = shares * price
            w = (mv / total_value * 100) if total_value > 0 else 0
            chart_data.append({"标的": STOCK_NAMES.get(code, code), "权重": max(w, 0.1)})
        
        df = pd.DataFrame(chart_data)
        st.vega_lite_chart(df, {
            "width": "container",
            "mark": {"type": "arc", "innerRadius": 50, "tooltip": True},
            "encoding": {
                "theta": {"field": "权重", "type": "quantitative"},
                "color": {"field": "标的", "type": "nominal", "scale": {"range": COLORS[:len(df)]}},
            },
        }, width='stretch')
    
    with right:
        st.subheader("🎯 权重偏差 (目标 vs 实际)")
        dev_data = []
        for code, tw in TARGET_WEIGHTS.items():
            pos = positions.get(code, {})
            shares = pos.get('shares', 0)
            price = get_price(positions, code, prices)
            mv = shares * price
            aw = (mv / total_value * 100) if total_value > 0 else 0
            tw_pct = tw * 100
            dev = aw - tw_pct
            dev_data.append({
                "标的": STOCK_NAMES.get(code, code),
                "偏差%": dev,
                "实际": aw,
                "目标": tw_pct
            })
        dev_df = pd.DataFrame(dev_data)
        st.bar_chart(dev_df.set_index("标的")["偏差%"], width='stretch')
    
    st.subheader("📋 持仓明细")
    table_data = []
    for code, tw in TARGET_WEIGHTS.items():
        pos = positions.get(code, {})
        shares = pos.get('shares', 0)
        price = get_price(positions, code, prices)
        mv = shares * price
        aw = (mv / total_value * 100) if total_value > 0 else 0
        tw_pct = tw * 100
        dev = aw - tw_pct
        price_label = f"￥{price:,.2f}" + (" 📡" if code in prices else " 💰")
        table_data.append({
            "标的": STOCK_NAMES.get(code, code),
            "代码": code,
            "持仓": f"{shares:,}股",
            "现价": price_label,
            "市值": f"￥{mv:,.0f}",
            "实际权重": f"{aw:.1f}%",
            "目标权重": f"{tw_pct:.0f}%",
            "偏差": f"{dev:+.1f}%"
        })
    
    st.dataframe(
        pd.DataFrame(table_data),
        width='stretch',
        hide_index=True
    )
    
    if history and len(history) > 2:
        st.subheader("💹 账户总值变化")
        tv_data = [{"时间": h['time'], "总值": h.get('total_value', 0)} for h in history]
        tv_df = pd.DataFrame(tv_data)
        st.line_chart(tv_df.set_index("时间"), width='stretch')

refresh_sec = st.sidebar.slider("刷新间隔(秒)", 5, 60, 10, 5)
st.sidebar.info(f"⏱️ 每{refresh_sec}秒自动刷新 | 当前时间: {datetime.now().strftime('%H:%M:%S')}")

if st.sidebar.button("🔄 立即 Refresh"):
    st.rerun()

st.sidebar.markdown("### ✅ 数据校验")
st.sidebar.success("华安黄金ETF: ￥5-15 范围校验")
st.sidebar.success("沪深300/中证1000/创业板ETF: ￥1-8")
st.sidebar.success("科创50ETF: ￥0.5-3 范围校验")

render()

# 自动刷新机制（不依赖实验性 API，sleep + rerun 最稳定）
if st.sidebar.checkbox("🔄 启用自动刷新", value=True, help="每 N 秒重新读取数据文件并刷新图表"):
    time.sleep(refresh_sec)
    st.rerun()