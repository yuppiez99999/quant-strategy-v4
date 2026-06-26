# -*- coding: utf-8 -*-
"""
engine/etf_flow.py — 实时ETF资金流向监控模块

整合自 `实时ETF资金流向.py`，加入 v5.1 模块化架构。
功能: 获取ETF资金流向数据，检测国家队加仓/减仓信号
数据源优先级: Wind MCP > tushare > yfinance > 模拟数据

核心类:
    ETFRealTimeTracker — 实时资金流追踪 + 信号检测 + 报告生成
"""

import os
import sys
import json
import random
from datetime import datetime
from typing import Dict, List, Optional

from bootstrap import BASE_DIR, logger


# ============ 模块级常量 ============

# 国家队关注的ETF列表（与主系统持仓/十五五规划方向对齐）
NATIONAL_TEAM_ETFS: List[Dict[str, str]] = [
    # 核心宽基 (5)
    {"code": "510050", "name": "上证50ETF华夏",       "category": "宽基核心"},
    {"code": "510300", "name": "沪深300ETF华泰柏瑞",  "category": "宽基核心"},
    {"code": "510500", "name": "中证500ETF南方",       "category": "中盘成长"},
    {"code": "588000", "name": "科创50ETF华夏",        "category": "成长科技"},
    {"code": "512100", "name": "中证1000ETF南方",      "category": "小盘风格"},
    # 成长/科技主题 (4)
    {"code": "588080", "name": "科创50ETF易方达",      "category": "成长科技"},
    {"code": "512760", "name": "半导体ETF国泰",        "category": "科技主题"},
    {"code": "159915", "name": "创业板ETF易方达",      "category": "成长科技"},
    {"code": "515030", "name": "新能源车ETF华夏",      "category": "新能源主题"},
    # 金融/防御/资源主题 (4)
    {"code": "512880", "name": "证券ETF国泰",          "category": "金融主题"},
    {"code": "512800", "name": "银行ETF华宝",          "category": "金融主题"},
    {"code": "512170", "name": "医疗ETF华宝",          "category": "医药主题"},
    {"code": "518880", "name": "黄金ETF华安",          "category": "避险资产"},
]

# 信号阈值（亿元）
SIGNAL_THRESHOLDS: Dict[str, float] = {
    "high":   50.0,   # 强信号
    "medium": 10.0,   # 中信号
    "low":    2.0,    # 关注信号
}

# ETF → 相关个股映射（用于交易决策关联十五五规划方向）
ETF_TO_STOCKS: Dict[str, Dict] = {
    "510050": {"板块": "上证50大盘蓝筹",  "个股票池": ["600036", "601318", "600519", "600276", "601166", "601088"]},
    "510300": {"板块": "沪深300核心资产", "个股票池": ["600036", "600276", "601088", "600875", "601888", "300274"]},
    "510500": {"板块": "中盘成长",        "个股票池": ["002493", "000301", "601233", "603225", "000425", "600989"]},
    "588000": {"板块": "科创板科技",      "个股票池": ["688041", "300308", "688017", "002371", "300274"]},
    "512100": {"板块": "小盘风格",        "个股票池": ["688017", "603225", "000425", "300308"]},
    "512760": {"板块": "半导体",          "个股票池": ["688041", "002371", "300308", "688017"]},
    "512880": {"板块": "券商",            "个股票池": ["600030", "601211", "600837"]},
    "512800": {"板块": "银行",            "个股票池": ["600036", "601166", "000001"]},
    "518880": {"板块": "黄金避险",        "个股票池": ["600489", "601899", "600547", "601088"]},
    "512170": {"板块": "医疗医药",        "个股票池": ["600276", "300760", "603259", "601888"]},
    "515030": {"板块": "新能源",          "个股票池": ["300274", "600875", "600089", "600995", "002371"]},
    "159915": {"板块": "创业板成长",      "个股票池": ["300274", "300308", "300760", "688017"]},
    "588080": {"板块": "科创50",          "个股票池": ["688041", "688017", "002371", "300308"]},
}

# 年度交易计划个股核心池（2026候选） — 14只个股，用于年度计划信号扩展
YEARLY_STOCK_POOL: List[Dict[str, str]] = [
    {"code": "300308", "name": "中际旭创",   "style": "成长科技",    "theme": "AI/算力/十五五数字经济"},
    {"code": "688041", "name": "海光信息",   "style": "成长科技",    "theme": "芯片/国产替代"},
    {"code": "601088", "name": "中国神华",   "style": "防御/红利",   "theme": "能源安全/高股息"},
    {"code": "518880", "name": "黄金ETF华安", "style": "防御/红利",   "theme": "避险抗通胀"},
    {"code": "600276", "name": "恒瑞医药",   "style": "防御/红利",   "theme": "医药创新/内需复苏"},
    {"code": "600989", "name": "宝丰能源",   "style": "周期/顺周期", "theme": "煤化工/能源价格"},
    {"code": "600875", "name": "东方电气",   "style": "周期/顺周期", "theme": "电力装备/核电"},
    {"code": "600089", "name": "特变电工",   "style": "周期/顺周期", "theme": "特高压/新能源装备"},
    {"code": "600406", "name": "国电南瑞",   "style": "核心资产",    "theme": "电网/数字能源"},
    {"code": "300274", "name": "阳光电源",   "style": "成长科技",    "theme": "储能/光伏逆变器"},
    {"code": "600995", "name": "南网储能",   "style": "周期/顺周期", "theme": "抽水蓄能/新型电力系统"},
    {"code": "000425", "name": "徐工机械",   "style": "周期/顺周期", "theme": "工程机械/一带一路"},
    {"code": "688017", "name": "绿的谐波",   "style": "成长科技",    "theme": "人形机器人/精密制造"},
    {"code": "002371", "name": "北方华创",   "style": "成长科技",    "theme": "半导体设备/国产替代"},
    {"code": "601888", "name": "中国中免",   "style": "防御/红利",   "theme": "消费复苏/免税龙头"},
]

# ETF → 相关ETF替代品映射
ETF_TO_RELATED: Dict[str, List[str]] = {
    "510050": ["510300", "510500"],
    "510300": ["510050", "510500", "512100"],
    "588000": ["159915", "512760"],
    "512760": ["588000", "515030"],
    "518880": ["159980"],     # 黄金ETF → 有色ETF
    "512170": ["512290"],     # 医疗 → 生物医药ETF
}


# ============ 数据源：Wind MCP ============

try:
    import sys as _sys
    import os as _os
    _strat_dir = BASE_DIR
    if _strat_dir not in _sys.path:
        _sys.path.insert(0, _strat_dir)
    from wind_mcp_fetcher import wind_get_quote, wind_get_batch_quotes
    WIND_MCP_AVAILABLE = True
    logger.info("[ETF资金流] Wind MCP 连接器加载成功")
except Exception as e:
    WIND_MCP_AVAILABLE = False
    logger.warning(f"[ETF资金流] Wind MCP 连接器不可用: {e}")


# ============ 数据源：tushare ============

try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
    logger.info("[ETF资金流] tushare 模块加载成功")
except Exception:
    TUSHARE_AVAILABLE = False
    logger.warning("[ETF资金流] tushare 模块不可用")


# ============ 数据源：yfinance ============

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
    logger.info("[ETF资金流] yfinance 模块加载成功")
except Exception:
    YFINANCE_AVAILABLE = False
    logger.warning("[ETF资金流] yfinance 模块不可用")


# ============ 核心追踪器类 ============

class ETFRealTimeTracker:
    """实时ETF资金流向追踪器

    设计要点:
    - 数据源优先级: Wind MCP > tushare > yfinance > 模拟数据
    - 与 ETFFundFlowMonitor (engine/managers.py) 协调: 前者负责历史复盘，此处负责实时监控
    - 输出可被 run_etf_flow_monitor / run_macro_analysis 直接调用
    """

    def __init__(self, etf_list: Optional[List[Dict]] = None, connector_manager=None):
        """
        Args:
            etf_list: 自定义ETF列表；默认使用 NATIONAL_TEAM_ETFS
            connector_manager: 可选 DataConnectorManager 实例，用于数据源共享
        """
        self.etf_list = etf_list or NATIONAL_TEAM_ETFS
        self.connector_manager = connector_manager
        self.flow_data: Dict[str, Dict] = {}
        self.signals: List[Dict] = []

        # tushare
        self.pro = None
        if TUSHARE_AVAILABLE:
            try:
                self.pro = ts.pro_api()
                logger.info("[ETF资金流] tushare API 初始化成功")
            except Exception as e:
                logger.warning(f"[ETF资金流] tushare API 初始化失败: {e}")

        # Wind MCP
        self.wind_ok = False
        if WIND_MCP_AVAILABLE:
            try:
                test = wind_get_quote('510300', is_fund=True)
                self.wind_ok = test is not None and test.get('price', 0) > 0
                logger.info(f"[ETF资金流] Wind MCP {'连接成功' if self.wind_ok else '不可用'}")
            except Exception as e:
                logger.warning(f"[ETF资金流] Wind MCP 初始化失败: {e}")

    # ---------- 单ETF资金流 ----------

    def get_etf_fund_flow(self, etf_code: str) -> Dict[str, object]:
        """获取单个ETF的资金流向数据（按优先级从多数据源取）"""
        result = {
            "code": etf_code,
            "name": "",
            "net_flow_yi": 0.0,   # 单位: 亿元
            "change_pct": 0.0,
            "volume": 0,
            "amount_yi": 0.0,
            "trend": "中性",
            "source": "模拟数据",
        }

        # 填入名称/类别
        for etf in self.etf_list:
            if etf["code"] == etf_code:
                result["name"] = etf["name"]
                result["category"] = etf.get("category", "未知")
                break

        # 1) Wind MCP 最高优先
        if self.wind_ok and WIND_MCP_AVAILABLE:
            try:
                wind_data = wind_get_quote(etf_code, is_fund=True)
                if wind_data and wind_data.get("price", 0) > 0:
                    result["price"] = wind_data.get("price", 0)
                    chg = wind_data.get("change", wind_data.get("change_pct", 0))
                    result["change_pct"] = float(chg) if chg else 0.0
                    result["source"] = "wind_mcp"
                    nf = wind_data.get("net_flow")
                    if nf:
                        result["net_flow_yi"] = round(float(nf) * 1e-8, 2)
                    amt = wind_data.get("amount")
                    if amt:
                        result["amount_yi"] = round(float(amt) * 1e-8, 2)
            except Exception as e:
                logger.warning(f"[ETF资金流] Wind MCP 取数失败({etf_code}): {e}")

        # 2) tushare 回退
        if self.pro and TUSHARE_AVAILABLE and result["net_flow_yi"] == 0:
            try:
                df = self.pro.fund_daily(
                    ts_code=f"{etf_code}.SH",
                    start_date=datetime.now().strftime("%Y%m%d")
                )
                if df is not None and not getattr(df, "empty", True):
                    row = df.iloc[0]
                    result["change_pct"] = float(row.get("pct_chg", 0) or 0)
                    result["volume"] = int(row.get("vol", 0) or 0)
                    amount = float(row.get("amount", 0) or 0)
                    result["amount_yi"] = round(amount / 10000, 2)
                    result["source"] = "tushare"
                    # 估算资金流（涨跌幅 × 成交额的简易模型）
                    if result["change_pct"] > 2:
                        result["net_flow_yi"] = round(result["amount_yi"] * 0.3, 2)
                        result["trend"] = "流入"
                    elif result["change_pct"] < -2:
                        result["net_flow_yi"] = round(-result["amount_yi"] * 0.3, 2)
                        result["trend"] = "流出"
            except Exception as e:
                logger.warning(f"[ETF资金流] tushare 取数失败({etf_code}): {e}")

        # 3) yfinance 回退
        if YFINANCE_AVAILABLE and result["net_flow_yi"] == 0:
            try:
                ticker = yf.Ticker(f"{etf_code}.SS")
                info = ticker.fast_info
                price = getattr(info, "last_price", 0) or 0
                chg2 = getattr(info, "change", 0) or 0
                result["price"] = price
                result["change_pct"] = round(float(chg2), 2) if price > 0 else 0.0
                result["source"] = "yfinance"
            except Exception:
                pass

        # 4) 无真实数据 → 模拟数据（演示/回测用）
        if result["net_flow_yi"] == 0 and result["change_pct"] == 0:
            random.seed(datetime.now().toordinal() + int(etf_code) % 1000)
            result["net_flow_yi"] = round(random.uniform(-30, 80), 2)
            result["change_pct"] = round(random.uniform(-3, 5), 2)
            result["amount_yi"] = round(random.uniform(5, 50), 2)
            result["trend"] = "流入" if result["net_flow_yi"] > 0 else (
                "流出" if result["net_flow_yi"] < 0 else "中性"
            )
            result["source"] = "模拟数据"

        if not result.get("trend") or result["trend"] == "中性":
            result["trend"] = "流入" if result["net_flow_yi"] > 0 else (
                "流出" if result["net_flow_yi"] < 0 else "中性"
            )

        return result

    # ---------- 批量获取 ----------

    def analyze_fund_flow(self) -> Dict[str, Dict]:
        """获取所有监控ETF的资金流向数据，结果写入 self.flow_data"""
        logger.info(f"[ETF资金流] 开始分析 {len(self.etf_list)} 只ETF")
        self.flow_data = {}
        for etf in self.etf_list:
            code = etf["code"]
            try:
                self.flow_data[code] = self.get_etf_fund_flow(code)
            except Exception as e:
                logger.warning(f"[ETF资金流] 分析 {code} 失败: {e}")
                self.flow_data[code] = {
                    "code": code,
                    "name": etf.get("name", code),
                    "net_flow_yi": 0.0,
                    "change_pct": 0.0,
                    "trend": "未知",
                    "source": "error",
                }
        logger.info(f"[ETF资金流] 分析完成，共 {len(self.flow_data)} 只ETF")
        return self.flow_data

    # ---------- 信号检测 ----------

    def detect_signals(self, flow_data: Optional[Dict[str, Dict]] = None) -> List[Dict]:
        """检测国家队资金加仓/减仓信号

        Args:
            flow_data: 若为 None 则使用 self.flow_data

        Returns:
            按置信度/资金量排序的信号列表
        """
        data = flow_data if flow_data is not None else self.flow_data
        signals: List[Dict] = []

        for code, item in data.items():
            net_flow = float(item.get("net_flow_yi", 0) or 0)

            if net_flow >= SIGNAL_THRESHOLDS["high"]:
                conf, stype = "高", "国家队强加仓信号"
            elif net_flow >= SIGNAL_THRESHOLDS["medium"]:
                conf, stype = "中", "国家队加仓信号"
            elif net_flow >= SIGNAL_THRESHOLDS["low"]:
                conf, stype = "低", "国家队关注信号"
            elif net_flow <= -SIGNAL_THRESHOLDS["high"]:
                conf, stype = "高", "国家队强减仓信号"
            elif net_flow <= -SIGNAL_THRESHOLDS["medium"]:
                conf, stype = "中", "国家队减仓信号"
            elif net_flow <= -SIGNAL_THRESHOLDS["low"]:
                conf, stype = "低", "国家队减持关注"
            else:
                continue

            signals.append({
                "code": code,
                "name": item.get("name", code),
                "category": item.get("category", "未知"),
                "net_flow_yi": net_flow,
                "change_pct": item.get("change_pct", 0),
                "trend": item.get("trend", "中性"),
                "signal_type": stype,
                "confidence": conf,
                "source": item.get("source", "未知"),
            })

        # 置信度 → 金额绝对值 排序
        conf_rank = {"高": 0, "中": 1, "低": 2}
        signals.sort(key=lambda x: (conf_rank.get(x["confidence"], 99), -abs(x["net_flow_yi"])))
        self.signals = signals
        return signals

    # ---------- 报告生成 ----------

    def generate_report(self, signals: Optional[List[Dict]] = None,
                        flow_data: Optional[Dict[str, Dict]] = None) -> str:
        """生成 Markdown 格式的资金流向报告"""
        sigs = signals if signals is not None else self.signals
        flows = flow_data if flow_data is not None else self.flow_data
        lines: List[str] = []

        lines.append("# 实时ETF资金流向监控报告")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**监控标的**: {len(flows)} 只ETF")
        source_label = flows and next(iter(flows.values())).get("source", "未知") or "未知"
        lines.append(f"**数据来源**: {source_label}")
        lines.append("")
        lines.append("---")

        # 一、资金流向概况
        total_flow = round(sum(float(d.get("net_flow_yi", 0) or 0) for d in flows.values()), 2)
        overall_trend = "净流入" if total_flow > 0 else ("净流出" if total_flow < 0 else "平衡")
        lines.append("")
        lines.append("## 一、资金流向概况")
        lines.append("")
        lines.append(f"- **整体态势**: {overall_trend}")
        lines.append(f"- **今日净流入**: {total_flow:+.2f} 亿元")
        lines.append(f"- **强信号数量**: {len([s for s in sigs if s['confidence'] == '高'])} 条")
        lines.append("")

        # 二、国家队资金信号
        if sigs:
            lines.append("## 二、国家队资金信号")
            lines.append("")
            lines.append("| ETF名称 | 代码 | 净流入(亿) | 涨跌幅 | 信号类型 | 置信度 |")
            lines.append("|---------|------|-----------|--------|---------|--------|")
            for s in sigs[:15]:
                lines.append(
                    f"| {s['name']} | {s['code']} | {s['net_flow_yi']:+.2f} | "
                    f"{s['change_pct']:+.2f}% | {s['signal_type']} | {s['confidence']} |"
                )
            lines.append("")

        # 三、资金流向排行
        lines.append("## 三、ETF资金流向排行")
        lines.append("")
        sorted_flows = sorted(flows.items(), key=lambda kv: -abs(float(kv[1].get("net_flow_yi", 0) or 0)))
        lines.append("| 排名 | ETF名称 | 净流入(亿) | 涨跌幅 | 成交额(亿) |")
        lines.append("|------|---------|-----------|--------|-----------|")
        for i, (code, data) in enumerate(sorted_flows[:15], 1):
            arrow = "📈" if float(data.get("net_flow_yi", 0) or 0) > 0 else "📉"
            nf = float(data.get("net_flow_yi", 0) or 0)
            cp = float(data.get("change_pct", 0) or 0)
            amt = float(data.get("amount_yi", 0) or 0)
            lines.append(f"| {i} | {arrow} {data.get('name', code)} | {nf:+.2f} | {cp:+.2f}% | {amt:.2f} |")
        lines.append("")

        # 四、投资建议
        lines.append("## 四、投资建议")
        lines.append("")
        strong_buy = [s for s in sigs if "强加仓" in s["signal_type"]]
        strong_sell = [s for s in sigs if "强减仓" in s["signal_type"]]

        if not strong_buy and not strong_sell:
            lines.append("> ⚠️ 当前无强信号，建议继续观察现有持仓。")
        else:
            lines.append(f"**市场总判**: {'强烈看多' if total_flow > 100 else '偏多' if total_flow > 30 else '强烈看空' if total_flow < -100 else '偏空' if total_flow < -30 else '中性震荡'}")
            lines.append(f"**累计净流入**: {total_flow:+.1f} 亿 | **信号总数**: {len(sigs)}")
            lines.append("")

            if strong_buy:
                lines.append(f"### 📈 强加仓建议 ({len(strong_buy)}条)")
                lines.append("")
                lines.append("| 优先 | ETF | 净流入 | 关联个股/ETF | 建议操作 | 仓位调整 |")
                lines.append("|------|-----|--------|-------------|---------|---------|")
                for i, s in enumerate(strong_buy, 1):
                    stock_info = ETF_TO_STOCKS.get(s['code'], {})
                    stocks = stock_info.get('个股票池', [])
                    related_etfs = ETF_TO_RELATED.get(s['code'], [])
                    targets = ", ".join(stocks[:3]) if stocks else "-"
                    if related_etfs:
                        targets += f" (替代ETF: {', '.join(related_etfs[:1])})"
                    lines.append(f"| {i} | {s['name']}({s['code']}) | +{s['net_flow_yi']:.1f}亿 | {targets} | 加仓 | +3~5% |")
                lines.append("")

            if strong_sell:
                lines.append(f"### 📉 强减仓建议 ({len(strong_sell)}条)")
                lines.append("")
                for s in strong_sell:
                    stock_info = ETF_TO_STOCKS.get(s['code'], {})
                    stocks = stock_info.get('个股票池', [])
                    targets = ", ".join(stocks[:3]) if stocks else "-"
                    lines.append(f"- **{s['name']}({s['code']})** — 净流出 {abs(s['net_flow_yi']):.1f}亿；相关个股: {targets}；建议逐步减仓 3~5%")
                lines.append("")

        lines.append("---")
        lines.append(f"*本报告由 量化策略系统 v5.1 | ETF资金流模块 自动生成*")
        lines.append(f"*数据源: {source_label}*")
        return "\n".join(lines)

    # ---------- 交易计划决策 ----------

    def generate_trading_plan(self, signals: Optional[List[Dict]] = None,
                              flow_data: Optional[Dict[str, Dict]] = None) -> str:
        """生成用于再平衡决策的文本片段"""
        sigs = signals if signals is not None else self.signals
        flows = flow_data if flow_data is not None else self.flow_data
        lines: List[str] = []

        lines.append("## 五、ETF资金流驱动的交易计划")
        lines.append("")

        if not sigs:
            lines.append("> 当前无显著资金信号，维持现有持仓不变。")
            return "\n".join(lines)

        strong_buy = [s for s in sigs if "强加仓" in s["signal_type"]]
        strong_sell = [s for s in sigs if "强减仓" in s["signal_type"]]
        total_flow = round(sum(float(d.get("net_flow_yi", 0) or 0) for d in flows.values()), 2)

        if total_flow > 100:
            stance, tone = "强烈看多", "积极进攻"
        elif total_flow > 30:
            stance, tone = "偏多", "谨慎加仓"
        elif total_flow < -100:
            stance, tone = "强烈看空", "大幅减仓"
        elif total_flow < -30:
            stance, tone = "偏空", "逐步减仓"
        else:
            stance, tone = "中性震荡", "高抛低吸"

        lines.append(f"**市场总判**: {stance} | **操作基调**: {tone}")
        lines.append(f"**累计净流入**: {total_flow:+.1f} 亿 | **信号数量**: {len(sigs)}")
        lines.append("")

        if strong_buy:
            lines.append(f"### 5.1 强加仓信号 ({len(strong_buy)}条)")
            lines.append("")
            for s in strong_buy:
                lines.append(f"- {s['name']}({s['code']}) — 净流入 {s['net_flow_yi']:.1f}亿；建议加仓 3~5%")
            lines.append("")

        if strong_sell:
            lines.append(f"### 5.2 强减仓信号 ({len(strong_sell)}条)")
            lines.append("")
            for s in strong_sell:
                lines.append(f"- {s['name']}({s['code']}) — 净流出 {abs(s['net_flow_yi']):.1f}亿；建议减仓 3~5%")
            lines.append("")

        return "\n".join(lines)


# ============ 便捷函数 ============

def run_full_analysis() -> Dict:
    """一键执行: 抓取 → 检测 → 报告"""
    tracker = ETFRealTimeTracker()
    flows = tracker.analyze_fund_flow()
    signals = tracker.detect_signals(flows)
    report = tracker.generate_report(signals, flows)
    return {
        "tracker": tracker,
        "flows": flows,
        "signals": signals,
        "report": report,
    }


if __name__ == "__main__":
    result = run_full_analysis()
    print(result["report"])
