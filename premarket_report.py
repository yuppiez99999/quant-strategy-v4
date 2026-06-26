# -*- coding: utf-8 -*-
"""
盘前综合报告生成器 v1.0
整合三大数据源：社保基金追踪 + 量化策略系统 + ETF资金流向
每日盘前自动生成，保存至每日报告归档目录

数据源:
  1. social_security_tracker_v2.py — 社保基金风格追踪 + 买入信号
  2. 量化策略系统 v5.1 — 康波周期 + 十五五规划 + 持仓分析
  3. ETF资金流向 — 关联ETF净流入/流出 + 国家队信号

运行方式:
  python premarket_report.py
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Windows编码修复
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# LLM深度解读集成
try:
    sys.path.insert(0, r'E:\各种PY程序\09_配置与依赖')
    from llm_integration import append_llm_analysis
    _LLM_OK = True
except ImportError:
    _LLM_OK = False

# ==================== 配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_ROOT = os.path.join(os.path.dirname(BASE_DIR), '每日报告归档')
TODAY = datetime.now().strftime('%Y-%m-%d')
TODAY_SHORT = datetime.now().strftime('%Y%m%d')
ARCHIVE_TODAY = os.path.join(ARCHIVE_ROOT, TODAY)
os.makedirs(ARCHIVE_TODAY, exist_ok=True)

# Wind API
WIND_CLI = os.environ.get(
    "WIND_CLI_PATH",
    os.path.expandvars(r"%USERPROFILE%\.agents\skills\wind-mcp-skill\scripts\cli.mjs")
)
WIND_API_KEY = os.environ.get('WIND_API_KEY', '')

# ==================== 用户持仓 ====================
USER_HOLDINGS = {
    "山金国际": {"code": "000975.SZ", "shares": 10000, "style": "资源"},
    "藏格矿业": {"code": "000408.SZ", "shares": 5000, "style": "资源"},
    "山推股份": {"code": "000680.SZ", "shares": 8000, "style": "高端制造"},
    "南山铝业": {"code": "600219.SH", "shares": 15000, "style": "顺周期"},
    "科伦药业": {"code": "002422.SZ", "shares": 6000, "style": "防御"},
    "美的集团": {"code": "000333.SZ", "shares": 4000, "style": "高端制造"},
    "中国神华": {"code": "601088.SH", "shares": 2000, "style": "顺周期"},
    "华安黄金ETF": {"code": "518880.SH", "shares": 30000, "style": "资源"},
}

# 社保基金风格目标权重
TARGET_STYLE_WEIGHTS = {
    "顺周期": 0.25,
    "高端制造": 0.35,
    "资源": 0.20,
    "防御": 0.20,
}

# 关联ETF
RELATED_ETFS = [
    {"code": "510300", "name": "沪深300ETF", "market": "sh", "style": "顺周期"},
    {"code": "510500", "name": "中证500ETF", "market": "sh", "style": "顺周期"},
    {"code": "512100", "name": "中证1000ETF", "market": "sh", "style": "高端制造"},
    {"code": "588000", "name": "科创50ETF", "market": "sh", "style": "高端制造"},
    {"code": "159915", "name": "创业板ETF", "market": "sz", "style": "高端制造"},
    {"code": "518880", "name": "华安黄金ETF", "market": "sh", "style": "资源"},
    {"code": "512010", "name": "医药ETF", "market": "sh", "style": "防御"},
    {"code": "512170", "name": "医疗ETF", "market": "sh", "style": "防御"},
    {"code": "510050", "name": "上证50ETF", "market": "sh", "style": "防御"},
]

# 康波周期第六轮关键商品
KONDRATIEV_COMMODITIES = [
    {"name": "COMEX黄金", "code": "GC00Y.CMX", "type": "贵金属"},
    {"name": "WTI原油", "code": "CL00Y.NYM", "type": "能源"},
    {"name": "LME铜", "code": "MP00Y.LME", "type": "工业金属"},
    {"name": "动力煤", "code": "ZC00Y.CZC", "type": "能源"},
    {"name": "铁矿石", "code": "I00Y.DCE", "type": "黑色"},
]


# ==================== Wind API ====================
def _call_wind_api(server_type: str, tool_name: str, params: dict) -> Optional[dict]:
    """调用Wind MCP Skill API"""
    env = os.environ.copy()
    env['WIND_API_KEY'] = WIND_API_KEY
    for k in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
        env.pop(k, None)
    env['no_proxy'] = '*'

    params_json = json.dumps(params, ensure_ascii=False)
    try:
        result = subprocess.run(
            ['node', WIND_CLI, 'call', server_type, tool_name, params_json],
            capture_output=True, text=True, timeout=60,
            env=env, encoding='utf-8', errors='replace'
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                parsed = json.loads(result.stdout.strip())
                content = parsed.get('content', [{}])
                if content and isinstance(content, list):
                    text = content[0].get('text', '')
                    if text:
                        return json.loads(text)
            except (json.JSONDecodeError, IndexError, KeyError):
                pass
    except (subprocess.TimeoutExpired, Exception):
        pass
    return None


def sf(v):
    """安全浮点转换"""
    try:
        return float(v) if v is not None else 0
    except (ValueError, TypeError):
        return 0


# ==================== 数据获取 ====================
def get_stock_quotes(codes: List[str]) -> Dict[str, Dict]:
    """批量获取个股行情"""
    quotes = {}
    for code in codes:
        resp = _call_wind_api('analytics_data', 'get_financial_data', {
            'question': f'查询{code}最新收盘价、涨跌幅、成交量、成交额、PE(TTM)、PB、总市值、换手率'
        })
        if resp and isinstance(resp, dict):
            try:
                datasets = resp.get('data', {}).get('data', [])
                if not datasets:
                    continue
                dataset = datasets[0]
                columns = [c.get('name', '') for c in dataset.get('columns', [])]
                rows = dataset.get('rows', [])
                if not rows:
                    continue
                row = rows[0]
                data = {}
                for i, col in enumerate(columns):
                    if i < len(row):
                        data[col] = row[i]
                quotes[code] = {
                    'close': sf(data.get('最新收盘价', data.get('收盘价', 0))),
                    'change_pct': sf(data.get('最新涨跌幅', data.get('涨跌幅', 0))),
                    'pe_ttm': sf(data.get('最新市盈率PE_TTM', data.get('PE(TTM)', 0))),
                    'pb': sf(data.get('最新市净率PB', data.get('PB', 0))),
                    'market_cap': sf(data.get('最新总市值', data.get('总市值', 0))),
                    'turnover': sf(data.get('最新换手率', data.get('换手率', 0))),
                    'amount': sf(data.get('最新成交额', data.get('成交额', 0))),
                }
            except Exception:
                continue
    return quotes


def get_etf_kline(code: str, market: str, days: int = 5) -> Optional[List[Dict]]:
    """获取ETF近N日K线数据"""
    wind_code = f"{code}.{market.upper()}"
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days + 10)).strftime('%Y%m%d')

    resp = _call_wind_api('fund_data', 'get_fund_kline', {
        'windcode': wind_code,
        'begin_date': start_date,
        'end_date': end_date,
        'count': days + 5
    })
    if resp and isinstance(resp, dict):
        try:
            data_section = resp.get('data', {})
            columns = [c.get('name', '') for c in data_section.get('columns', [])]
            rows = data_section.get('rows', [])
            if not rows:
                return None

            col_idx = {}
            for i, col in enumerate(columns):
                cu = col.upper()
                if cu in ('TIME', '_DATE'):
                    col_idx['date'] = i
                elif cu == 'MATCH':
                    col_idx['close'] = i
                elif cu == 'TURNOVER':
                    col_idx['amount'] = i

            if 'close' not in col_idx:
                return None

            recent_rows = rows[-days:] if len(rows) >= days else rows
            kline = []
            prev_close = 0
            for row in recent_rows:
                close_val = sf(row[col_idx['close']]) if 'close' in col_idx else 0
                amount_val = sf(row[col_idx['amount']]) if 'amount' in col_idx else 0
                date_val = str(row[col_idx['date']]) if 'date' in col_idx else ''
                change_pct = ((close_val - prev_close) / prev_close * 100) if prev_close > 0 and close_val > 0 else 0
                net_flow = amount_val * (1 if change_pct >= 0 else -1)
                kline.append({
                    'date': date_val[:10] if len(date_val) >= 10 else date_val,
                    'close': close_val, 'change_pct': round(change_pct, 2),
                    'amount': amount_val, 'net_flow': net_flow,
                })
                prev_close = close_val
            return kline if kline else None
        except Exception:
            pass
    return None


# ==================== 分析模块 ====================
def analyze_portfolio(quotes: Dict[str, Dict]) -> Dict:
    """分析用户持仓"""
    total_value = 0
    holdings = []
    style_values = {}

    for name, info in USER_HOLDINGS.items():
        code = info["code"]
        quote = quotes.get(code, {})
        price = quote.get('close', 0)
        shares = info["shares"]
        style = info["style"]

        if price > 0:
            value = shares * price
            total_value += value
            holdings.append({
                "name": name, "code": code, "shares": shares,
                "price": price, "value": value, "style": style,
                "change_pct": quote.get('change_pct', 0),
                "pe": quote.get('pe_ttm', 0),
            })
            style_values[style] = style_values.get(style, 0) + value

    # 风格权重
    style_weights = {}
    for style, val in style_values.items():
        style_weights[style] = val / total_value if total_value > 0 else 0

    # 风格偏离
    deviations = {}
    for style, target in TARGET_STYLE_WEIGHTS.items():
        current = style_weights.get(style, 0)
        deviations[style] = current - target

    return {
        "total_value": total_value,
        "holdings": sorted(holdings, key=lambda x: -x["value"]),
        "style_weights": style_weights,
        "deviations": deviations,
    }


def detect_signals(portfolio: Dict, quotes: Dict[str, Dict]) -> Dict:
    """检测买入/卖出信号"""
    buy_signals = []
    sell_signals = []
    deviations = portfolio["deviations"]

    # 买入信号：风格低配
    for style, dev in deviations.items():
        if dev < -0.05:
            buy_signals.append({
                "type": "风格低配",
                "style": style,
                "reason": f"{style}低配{abs(dev):.1%}，建议加仓",
                "urgency": "高" if dev < -0.10 else "中",
            })

    # 买入信号：估值低位
    for name, info in USER_HOLDINGS.items():
        quote = quotes.get(info["code"], {})
        pe = quote.get('pe_ttm', 0)
        change = quote.get('change_pct', 0)
        if 0 < pe < 15 and change < -2:
            buy_signals.append({
                "type": "估值低位",
                "stock": name, "code": info["code"],
                "reason": f"PE={pe:.1f}，当日跌{abs(change):.2f}%",
                "urgency": "高" if pe < 10 else "中",
                "pe": pe, "change_pct": change,
            })

    # 卖出信号：估值过高
    for name, info in USER_HOLDINGS.items():
        quote = quotes.get(info["code"], {})
        pe = quote.get('pe_ttm', 0)
        change = quote.get('change_pct', 0)
        if pe > 80 and change > 5:
            sell_signals.append({
                "type": "估值过高+大涨",
                "stock": name, "code": info["code"],
                "reason": f"PE={pe:.1f}，当日涨{change:.2f}%",
                "urgency": "高",
            })

    return {"buy": buy_signals, "sell": sell_signals}


def analyze_etf_flows() -> List[Dict]:
    """分析ETF资金流入"""
    results = []
    for etf in RELATED_ETFS:
        kline = get_etf_kline(etf["code"], etf["market"], days=5)
        if kline and len(kline) >= 2:
            total_flow = sum(k['net_flow'] for k in kline)
            positive_days = sum(1 for k in kline if k['net_flow'] > 0)
            latest = kline[-1]
            if total_flow > 5e8:
                trend = "持续流入"
            elif total_flow < -5e8:
                trend = "持续流出"
            else:
                trend = "震荡"
            results.append({
                "name": etf["name"], "code": etf["code"],
                "style": etf["style"],
                "latest_price": latest['close'],
                "change_pct": latest['change_pct'],
                "flow_5d_yi": total_flow / 1e8,
                "positive_days": positive_days,
                "trend": trend,
            })
        else:
            results.append({
                "name": etf["name"], "code": etf["code"],
                "style": etf["style"],
                "latest_price": 0, "change_pct": 0,
                "flow_5d_yi": 0, "positive_days": 0,
                "trend": "无数据",
            })
    return results


# ==================== 报告生成 ====================
def _change_badge(pct: float) -> str:
    """涨跌幅徽章"""
    if pct > 3:
        return f"**+{pct:.2f}%**"
    elif pct > 0:
        return f"+{pct:.2f}%"
    elif pct < -3:
        return f"**{pct:.2f}%**"
    elif pct < 0:
        return f"{pct:.2f}%"
    return "0.00%"


def _flow_badge(flow: float) -> str:
    """资金流徽章"""
    if flow > 10:
        return f"**+{flow:.2f}**"
    elif flow > 0:
        return f"+{flow:.2f}"
    elif flow < -10:
        return f"**{flow:.2f}**"
    elif flow < 0:
        return f"{flow:.2f}"
    return "0.00"


def generate_premarket_report() -> str:
    """生成盘前综合报告"""
    now = datetime.now()
    lines = []

    lines.append("# 盘前综合报告")
    lines.append("")
    lines.append(f"> 日期：{TODAY} | 生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')} | 数据源：Wind直连")
    lines.append("")

    # ============ 一、持仓概览 ============
    print("  [1/5] 获取持仓行情...")
    all_codes = [info["code"] for info in USER_HOLDINGS.values()]
    quotes = get_stock_quotes(all_codes)
    quote_ok = len(quotes)
    print(f"  行情: {quote_ok}/{len(all_codes)} 成功")

    portfolio = analyze_portfolio(quotes)
    signals = detect_signals(portfolio, quotes)

    lines.append("## 一、持仓概览")
    lines.append("")
    lines.append(f"> 持仓总市值：**¥{portfolio['total_value']:,.0f}** | 行情数据：{quote_ok}/{len(all_codes)}")
    lines.append("")
    lines.append("| 名称 | 代码 | 持股 | 现价 | 市值 | 涨跌幅 | PE(TTM) | 风格 |")
    lines.append("|:-----|:-----|-----:|-----:|-----:|-------:|--------:|:-----|")

    for h in portfolio["holdings"]:
        change_str = _change_badge(h['change_pct'])
        pe_str = f"{h['pe']:.1f}" if h['pe'] > 0 else "-"
        lines.append(f"| {h['name']} | {h['code']} | {h['shares']:,} | ¥{h['price']:.2f} | ¥{h['value']:,.0f} | {change_str} | {pe_str} | {h['style']} |")

    lines.append("")

    # ============ 二、风格偏离 ============
    lines.append("## 二、风格偏离分析")
    lines.append("")
    lines.append("| 风格 | 目标权重 | 当前权重 | 偏离 | 状态 |")
    lines.append("|:-----|--------:|--------:|-----:|:-----|")

    for style in TARGET_STYLE_WEIGHTS:
        target = TARGET_STYLE_WEIGHTS[style]
        current = portfolio["style_weights"].get(style, 0)
        dev = portfolio["deviations"].get(style, 0)
        if abs(dev) < 0.03:
            status = "✅ 正常"
        elif dev > 0:
            status = "⚠️ 超配"
        else:
            status = "📥 低配"
        lines.append(f"| {style} | {target:.0%} | {current:.1%} | {dev:+.1%} | {status} |")

    lines.append("")

    # ============ 三、买入/卖出信号 ============
    lines.append("## 三、交易信号")
    lines.append("")

    if signals["buy"]:
        lines.append("### 买入信号")
        lines.append("")
        lines.append("| 紧急度 | 类型 | 标的/风格 | 原因 |")
        lines.append("|:------|:-----|:---------|:-----|")
        for sig in signals["buy"]:
            urgency = "🔴 高" if sig["urgency"] == "高" else "🟡 中"
            target = sig.get("stock", sig.get("style", ""))
            lines.append(f"| {urgency} | {sig['type']} | {target} | {sig['reason']} |")
        lines.append("")

    if signals["sell"]:
        lines.append("### 卖出信号")
        lines.append("")
        lines.append("| 紧急度 | 类型 | 标的 | 原因 |")
        lines.append("|:------|:-----|:-----|:-----|")
        for sig in signals["sell"]:
            urgency = "🔴 高" if sig["urgency"] == "高" else "🟡 中"
            lines.append(f"| {urgency} | {sig['type']} | {sig['stock']} | {sig['reason']} |")
        lines.append("")

    if not signals["buy"] and not signals["sell"]:
        lines.append("> 暂无交易信号")
        lines.append("")

    # ============ 四、ETF资金流向 ============
    print("  [2/5] 获取ETF资金流向...")
    etf_flows = analyze_etf_flows()
    etf_ok = sum(1 for e in etf_flows if e["trend"] != "无数据")
    print(f"  ETF资金流: {etf_ok}/{len(etf_flows)} 成功")

    lines.append("## 四、关联ETF资金流向（5日）")
    lines.append("")
    lines.append(f"> 数据源：Wind直连（{etf_ok}/{len(etf_flows)} 成功）")
    lines.append("")
    lines.append("| ETF | 风格 | 现价 | 涨跌幅 | 5日净流入(亿) | 趋势 |")
    lines.append("|:----|:-----|-----:|-------:|-------------:|:-----|")

    for item in etf_flows:
        flow = item["flow_5d_yi"]
        flow_icon = "🟢" if flow > 0 else "🔴" if flow < 0 else "⚪"
        flow_str = _flow_badge(flow)
        change_str = _change_badge(item["change_pct"])
        price_str = f"{item['latest_price']:.4f}" if item['latest_price'] > 0 else "-"
        lines.append(f"| {flow_icon} {item['name']} | {item['style']} | {price_str} | {change_str} | {flow_str} | {item['trend']} |")

    lines.append("")

    # 风格汇总
    style_etf_flow = {}
    for item in etf_flows:
        style = item["style"]
        style_etf_flow[style] = style_etf_flow.get(style, 0) + item["flow_5d_yi"]

    if style_etf_flow:
        lines.append("### 各风格ETF资金流汇总")
        lines.append("")
        lines.append("| 风格 | 5日净流入(亿) | 方向 |")
        lines.append("|:-----|-------------:|:-----|")
        for style, flow in sorted(style_etf_flow.items(), key=lambda x: x[1], reverse=True):
            icon = "📈" if flow > 0 else "📉"
            lines.append(f"| {icon} {style} | {_flow_badge(flow)} | {'净流入' if flow > 0 else '净流出'} |")
        lines.append("")

    # ============ 五、康波周期定位 ============
    print("  [3/5] 康波周期定位...")
    lines.append("## 五、康波周期定位（第六轮：AI/算力驱动）")
    lines.append("")

    # 基于当前日期推算康波阶段
    year = now.year
    # 第六轮康波：2020-2045，当前处于复苏→繁荣过渡期
    phase_progress = min(100, max(0, (year - 2020) / 25 * 100))
    if year < 2026:
        phase_name = "复苏期"
        risk_level = "中低"
        recommended = "高端制造+资源"
    elif year < 2032:
        phase_name = "繁荣期"
        risk_level = "中"
        recommended = "算力+新能源+顺周期"
    else:
        phase_name = "衰退期"
        risk_level = "高"
        recommended = "防御+黄金"

    lines.append(f"> 当前阶段：**{phase_name}** | 进度：{phase_progress:.0f}% | 风险等级：{risk_level} | 推荐风格：{recommended}")
    lines.append("")
    lines.append("| 品种 | 类型 | 康波信号 | 建议 |")
    lines.append("|:-----|:-----|:---------|:-----|")
    lines.append("| 黄金 | 贵金属 | 通胀对冲+货币信用弱化 | 🟢 长期配置 |")
    lines.append("| 原油 | 能源 | 需求复苏+供给约束 | 🟡 波段操作 |")
    lines.append("| 铜 | 工业金属 | 新能源+电网需求 | 🟢 超配 |")
    lines.append("| 动力煤 | 能源 | 碳中和转型 | 🟡 标配 |")
    lines.append("| 铁矿石 | 黑色 | 地产下行周期 | 🔴 低配 |")
    lines.append("")

    # ============ 六、十五五规划对标 ============
    print("  [4/5] 十五五规划对标...")
    lines.append("## 六、十五五规划持仓对标")
    lines.append("")

    plan_sectors = [
        {"direction": "科技自立自强", "weight": "25%", "holdings": "山推股份、美的集团", "match": "高"},
        {"direction": "新能源与双碳", "weight": "20%", "holdings": "藏格矿业", "match": "高"},
        {"direction": "资源安全", "weight": "15%", "holdings": "山金国际、藏格矿业", "match": "高"},
        {"direction": "高端装备制造", "weight": "15%", "holdings": "山推股份", "match": "中"},
        {"direction": "医药健康", "weight": "10%", "holdings": "科伦药业", "match": "中"},
        {"direction": "数字经济", "weight": "10%", "holdings": "-", "match": "低"},
        {"direction": "新型城镇化", "weight": "5%", "holdings": "南山铝业", "match": "中"},
    ]

    lines.append("| 战略方向 | 权重 | 持仓对标 | 匹配度 |")
    lines.append("|:---------|:----:|:---------|:------:|")
    for s in plan_sectors:
        match_icon = "🟢" if s["match"] == "高" else "🟡" if s["match"] == "中" else "🔴"
        lines.append(f"| {s['direction']} | {s['weight']} | {s['holdings']} | {match_icon} {s['match']} |")
    lines.append("")

    # ============ 七、今日操作建议 ============
    print("  [5/5] 生成操作建议...")
    lines.append("## 七、今日操作建议")
    lines.append("")

    # 综合信号生成建议
    has_action = False

    # 紧急买入
    high_buy = [s for s in signals["buy"] if s["urgency"] == "高"]
    if high_buy:
        has_action = True
        targets = "、".join(s.get("stock", s.get("style", "")) for s in high_buy)
        lines.append(f"- 🔴 **紧急买入**：{targets}，建议仓位2-5%")

    # 紧急卖出
    high_sell = [s for s in signals["sell"] if s["urgency"] == "高"]
    if high_sell:
        has_action = True
        targets = "、".join(s["stock"] for s in high_sell)
        lines.append(f"- 🔴 **紧急卖出**：{targets}")

    # 低配风格加仓
    for style, dev in portfolio["deviations"].items():
        if dev < -0.05:
            has_action = True
            lines.append(f"- 📥 **{style}低配{abs(dev):.1%}**，建议加仓至{TARGET_STYLE_WEIGHTS[style]:.0%}")

    # ETF资金流信号
    for item in etf_flows:
        if item["trend"] == "持续流入" and item["flow_5d_yi"] > 20:
            has_action = True
            lines.append(f"- 📈 **{item['name']}持续流入**（5日+{item['flow_5d_yi']:.1f}亿），关注相关标的")
        elif item["trend"] == "持续流出" and item["flow_5d_yi"] < -20:
            has_action = True
            lines.append(f"- 📉 **{item['name']}持续流出**（5日{item['flow_5d_yi']:.1f}亿），注意风险")

    if not has_action:
        lines.append("- ✅ 当前持仓风格均衡，无紧急操作需求")
        lines.append("- 📊 建议关注盘中ETF资金流变化")

    lines.append("")

    # ============ 尾部 ============
    lines.append("---")
    lines.append("")
    lines.append(f"*盘前综合报告 | 生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')} | 数据源：Wind直连({quote_ok}/{len(all_codes)}) | ETF({etf_ok}/{len(etf_flows)}) | LLM解读：{'已启用' if _LLM_OK else '未启用'}*")

    return "\n".join(lines)


# ==================== 主程序 ====================
def main():
    """主程序"""
    print(f"\n{'='*60}")
    print(f"  盘前综合报告生成器 v1.0")
    print(f"  日期: {TODAY}")
    print(f"  归档: {ARCHIVE_TODAY}")
    print(f"{'='*60}")

    start = time.time()

    # 生成报告
    report = generate_premarket_report()

    # LLM深度解读
    if _LLM_OK:
        print("  [LLM] 生成深度解读...")
        try:
            report = append_llm_analysis(report, "盘前综合报告：社保基金风格追踪+ETF资金流+康波周期+十五五规划")
        except Exception as e:
            print(f"  [LLM] 解读失败: {e}")

    # 保存报告
    report_path = os.path.join(ARCHIVE_TODAY, f"盘前综合报告_{TODAY_SHORT}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  ✅ 盘前综合报告已保存")
    print(f"  📄 {report_path}")
    print(f"  ⏱️ 耗时: {elapsed:.1f}s")
    print(f"{'='*60}\n")

    return report_path


if __name__ == "__main__":
    main()
