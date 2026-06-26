# -*- coding: utf-8 -*-
"""
engine/social_security.py — 社保基金ETF风格追踪与交易决策模块

整合自 `社保基金追踪/social_security_tracker_v2.py`。

核心功能:
- 风格分类 (核心资产/周期/防御/成长/金融)
- 持仓权重计算与风格暴露分析
- 买入/卖出信号检测 (关联康波周期阶段 + 十五五规划方向)
- 与 ETFRealTimeTracker (engine/etf_flow.py) 联动增强信号

设计要点:
- 数据源: Wind MCP (最高) > tushare > yfinance > 模拟数据
- 风格池与 engine/etf_flow.py 中的 ETF_TO_STOCKS 对齐
- 输出: 结构化 Markdown 报告 + 交易指令(给 ExcelDrivenRebalancingEngineV4 用)
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from bootstrap import BASE_DIR, logger


# ============ 数据源 ============

try:
    from wind_mcp_fetcher import wind_get_quote, wind_get_batch_quotes
    WIND_AVAILABLE = True
    logger.info("[社保基金] Wind MCP 连接器加载成功")
except Exception:
    WIND_AVAILABLE = False
    logger.warning("[社保基金] Wind MCP 不可用")

try:
    import tushare as ts
    TUSHARE_AVAILABLE = True
except Exception:
    TUSHARE_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except Exception:
    YFINANCE_AVAILABLE = False


# ============ 风格定义（与十五五规划方向对齐）============

STYLE_DEFINITIONS: Dict[str, Dict] = {
    "核心资产": {
        "weight": 0.25,
        "description": "沪深300成分股 + 核心宽基ETF，长期持有",
        "etf_codes": ["510300", "510050", "510500"],
        "sh_15th_5_alignment": 0.9,  # 十五五规划核心科技+内需
    },
    "周期/顺周期": {
        "weight": 0.20,
        "description": "有色金属/能源化工/机械设备，康波复苏阶段受益",
        "etf_codes": ["159980", "159981", "518880"],
        "sh_15th_5_alignment": 0.8,
    },
    "防御/红利": {
        "weight": 0.25,
        "description": "高股息红利ETF，熊市抗跌 + 分红复利",
        "etf_codes": ["512890", "515080", "512880"],
        "sh_15th_5_alignment": 0.7,
    },
    "成长科技": {
        "weight": 0.15,
        "description": "科创50/创业板/半导体ETF，十五五核心受益方向",
        "etf_codes": ["588000", "588080", "512760", "159915"],
        "sh_15th_5_alignment": 0.95,
    },
    "金融/银行": {
        "weight": 0.15,
        "description": "银行ETF + 券商ETF，国家队维稳主力",
        "etf_codes": ["512800", "512880"],
        "sh_15th_5_alignment": 0.6,
    },
}

# 全局持仓（可从 positions.json 加载，若无则使用默认权重）
DEFAULT_HOLDING_VALUES: Dict[str, float] = {
    "核心资产": 500000.0,
    "周期/顺周期": 300000.0,
    "防御/红利": 400000.0,
    "成长科技": 200000.0,
    "金融/银行": 200000.0,
}


# ============ 工具：行情获取 ============

def _get_quote(code: str) -> Optional[Dict[str, float]]:
    """统一的行情获取，按 Wind → tushare → yfinance → 模拟 顺序"""
    try:
        if WIND_AVAILABLE:
            wq = wind_get_quote(code, is_fund=True)
            if wq and wq.get("price", 0) > 0:
                return {
                    "price": float(wq.get("price", 0)),
                    "change_pct": float(wq.get("change", wq.get("change_pct", 0)) or 0),
                    "source": "wind_mcp",
                }
        if TUSHARE_AVAILABLE:
            pro = ts.pro_api()
            df = pro.daily(ts_code=f"{code}.SH", start_date=datetime.now().strftime("%Y%m%d"))
            if df is not None and not getattr(df, "empty", True):
                row = df.iloc[0]
                return {
                    "price": float(row.get("close", 0)),
                    "change_pct": float(row.get("pct_chg", 0)),
                    "source": "tushare",
                }
        if YFINANCE_AVAILABLE:
            ticker = yf.Ticker(f"{code}.SS")
            info = ticker.fast_info
            price = float(getattr(info, "last_price", 0) or 0)
            if price > 0:
                return {
                    "price": price,
                    "change_pct": float(getattr(info, "change", 0) or 0),
                    "source": "yfinance",
                }
    except Exception as e:
        logger.warning(f"[社保基金] 获取 {code} 行情失败: {e}")

    # 模拟数据兜底
    return {
        "price": 4.2,
        "change_pct": 0.3,
        "source": "模拟数据",
    }


# ============ 风格分析 ============

def calculate_style_weights(holding_values: Dict[str, float]) -> Dict[str, float]:
    """根据持仓计算各风格的实际权重

    Returns:
        {style_name: weight_pct} 例如 {"核心资产": 0.312, ...}
    """
    total = sum(float(v) for v in holding_values.values() if v > 0)
    if total <= 0:
        return {s: 0.0 for s in STYLE_DEFINITIONS}

    result: Dict[str, float] = {}
    for style in STYLE_DEFINITIONS:
        value = float(holding_values.get(style, 0) or 0)
        result[style] = round(value / total, 4)
    return result


def classify_etf_by_style(etf_code: str) -> Tuple[str, float]:
    """返回 (风格名称, 匹配度 0~1)"""
    for style, info in STYLE_DEFINITIONS.items():
        if etf_code in info.get("etf_codes", []):
            return style, 1.0
    # 未在显式列表中 → 按代码前缀启发式归类
    prefix_map = {
        "5103": ("核心资产", 0.7),
        "5100": ("核心资产", 0.7),
        "5105": ("核心资产", 0.7),
        "159980": ("周期/顺周期", 0.8),
        "159981": ("周期/顺周期", 0.8),
        "5188": ("周期/顺周期", 0.6),
        "512890": ("防御/红利", 0.9),
        "515080": ("防御/红利", 0.9),
        "588": ("成长科技", 0.9),
        "512760": ("成长科技", 0.9),
        "159915": ("成长科技", 0.8),
        "512800": ("金融/银行", 0.9),
        "512880": ("金融/银行", 0.8),
        # 2026新增个股代码
        "300308": ("成长科技", 0.95),   # 中际旭创
        "688041": ("成长科技", 0.95),   # 海光信息
        "601088": ("防御/红利", 0.9),   # 中国神华
        "600276": ("防御/红利", 0.7),   # 恒瑞医药
        "601888": ("防御/红利", 0.7),   # 中国中免
        "600989": ("周期/顺周期", 0.8), # 宝丰能源
        "600875": ("周期/顺周期", 0.85),# 东方电气
        "600089": ("周期/顺周期", 0.85),# 特变电工
        "600406": ("核心资产", 0.75),   # 国电南瑞
        "300274": ("成长科技", 0.9),    # 阳光电源
        "600995": ("周期/顺周期", 0.8), # 南网储能
        "000425": ("周期/顺周期", 0.8), # 徐工机械
        "688017": ("成长科技", 0.9),    # 绿的谐波
        "002371": ("成长科技", 0.95),   # 北方华创
    }
    for prefix, (style, score) in prefix_map.items():
        if etf_code.startswith(prefix):
            return style, score
    return "核心资产", 0.3


# ============ 信号检测 ============

def detect_buy_signals(current_weights: Dict[str, float],
                        etf_flow_data: Optional[Dict[str, Dict]] = None) -> List[Dict]:
    """买入信号检测

    条件 (任一):
      1) 当前风格实际权重 < 目标权重 × 0.85 (配置不足)
      2) 该风格对应ETF有 "国家队强加仓" 信号 (净流>50亿)
      3) 十五五规划对齐权重 ≥ 0.9 且当前权重偏低
    """
    signals: List[Dict] = []

    for style, info in STYLE_DEFINITIONS.items():
        target = info.get("weight", 0.1)
        actual = float(current_weights.get(style, 0) or 0)
        aligned = info.get("sh_15th_5_alignment", 0.5)

        reasons = []
        if actual < target * 0.85:
            reasons.append(f"配置不足(实际{actual*100:.1f}% vs 目标{target*100:.0f}%)")
        if etf_flow_data:
            for code in info.get("etf_codes", []):
                if code in etf_flow_data:
                    nf = float(etf_flow_data[code].get("net_flow_yi", 0) or 0)
                    if nf >= 50:
                        reasons.append(f"{code} 国家队资金净流入 +{nf:.0f}亿")
                        break
        if aligned >= 0.9 and actual < target:
            reasons.append(f"十五五规划高度对齐(对齐系数{aligned})")

        if reasons:
            signals.append({
                "style": style,
                "signal_type": "BUY",
                "target_weight_pct": round(target * 100, 1),
                "current_weight_pct": round(actual * 100, 1),
                "suggested_adjust_pct": round((target - actual) * 100, 1),
                "alignment_15th_5": aligned,
                "confidence": "高" if len(reasons) >= 2 else "中",
                "reasons": reasons,
                "related_etfs": info.get("etf_codes", []),
            })
    return signals


def detect_sell_signals(quotes: Dict[str, Dict],
                         stop_loss_pct: float = -10.0,
                         take_profit_pct: float = 15.0) -> List[Dict]:
    """卖出信号检测 — 基于止损/止盈阈值

    Args:
        quotes: {code: {"price": float, "change_pct": float, "base_price": float}}
        stop_loss_pct: 止损百分比 (负数, 如 -10.0 表示 -10%)
        take_profit_pct: 止盈百分比 (正数, 如 15.0 表示 +15%)
    """
    signals: List[Dict] = []
    for code, q in quotes.items():
        base = float(q.get("base_price", q.get("price", 0)) or 0)
        price = float(q.get("price", 0) or 0)
        if base <= 0 or price <= 0:
            continue
        ret = (price - base) / base * 100
        if ret <= stop_loss_pct:
            style, _ = classify_etf_by_style(code)
            signals.append({
                "code": code,
                "style": style,
                "signal_type": "SELL_STOP_LOSS",
                "return_pct": round(ret, 2),
                "threshold_pct": stop_loss_pct,
                "current_price": price,
                "base_price": base,
                "confidence": "高",
            })
        elif ret >= take_profit_pct:
            style, _ = classify_etf_by_style(code)
            signals.append({
                "code": code,
                "style": style,
                "signal_type": "SELL_TAKE_PROFIT",
                "return_pct": round(ret, 2),
                "threshold_pct": take_profit_pct,
                "current_price": price,
                "base_price": base,
                "confidence": "中",
            })
    return signals


# ============ 主追踪器类 ============

class SocialSecurityStyleTracker:
    """社保基金风格追踪与交易决策"""

    def __init__(self, holdings: Optional[Dict[str, float]] = None,
                 stop_loss: float = -10.0, take_profit: float = 15.0):
        self.holdings = holdings or dict(DEFAULT_HOLDING_VALUES)
        self.stop_loss_pct = stop_loss
        self.take_profit_pct = take_profit
        self.style_weights: Dict[str, float] = {}
        self.buy_signals: List[Dict] = []
        self.sell_signals: List[Dict] = []
        self.etf_flow_data: Dict[str, Dict] = {}

    # ---------- 分析 ----------

    def analyze_styles(self) -> Dict[str, float]:
        """计算并返回当前各风格权重"""
        self.style_weights = calculate_style_weights(self.holdings)
        return self.style_weights

    def fetch_etf_flows(self, external_flow_data: Optional[Dict[str, Dict]] = None):
        """获取或直接使用外部 ETF 资金流数据 (来自 ETFRealTimeTracker)"""
        if external_flow_data is not None:
            self.etf_flow_data = external_flow_data
        else:
            # 自行抓取核心ETF
            for style, info in STYLE_DEFINITIONS.items():
                for code in info.get("etf_codes", [])[:2]:
                    q = _get_quote(code)
                    self.etf_flow_data[code] = {
                        **(q or {}),
                        "code": code,
                        "style": style,
                        "net_flow_yi": 0.0,
                    }
        return self.etf_flow_data

    def run_signal_detection(self):
        """统一运行买入/卖出检测"""
        if not self.style_weights:
            self.analyze_styles()
        self.buy_signals = detect_buy_signals(self.style_weights, self.etf_flow_data)

        # 构造 quotes (合并 style 中每只ETF的 price + base_price)
        quotes: Dict[str, Dict] = {}
        for style, info in STYLE_DEFINITIONS.items():
            for code in info.get("etf_codes", []):
                q = _get_quote(code)
                if q and q.get("price", 0) > 0:
                    quotes[code] = {
                        "price": q["price"],
                        "base_price": q["price"] * 1.03,
                        "change_pct": q.get("change_pct", 0),
                        "style": style,
                    }
        self.sell_signals = detect_sell_signals(quotes, self.stop_loss_pct, self.take_profit_pct)
        return self.buy_signals + self.sell_signals

    # ---------- 报告生成 ----------

    def generate_report(self) -> str:
        """生成完整 Markdown 报告"""
        lines: List[str] = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines.append("# 社保基金ETF风格追踪报告")
        lines.append("")
        lines.append(f"**生成时间**: {now}")
        lines.append(f"**体系**: 康波周期 + 十五五规划 + 社保基金风格三元框架")
        lines.append("")
        lines.append("---")

        # 一、风格权重
        total_value = round(sum(float(v) for v in self.holdings.values()), 2)
        lines.append("## 一、当前持仓风格权重（总资产 ￥{:,.0f}）".format(total_value))
        lines.append("")
        lines.append("| 风格 | 当前权重 | 目标权重 | 偏差 | 十五五对齐系数 |")
        lines.append("|------|---------|---------|------|--------------|")
        for style, info in STYLE_DEFINITIONS.items():
            actual = round(self.style_weights.get(style, 0) * 100, 1)
            target = round(info.get("weight", 0) * 100, 1)
            delta = actual - target
            align = info.get("sh_15th_5_alignment", 0)
            flag = " 🔴" if delta < -5 else (" 🟡" if -5 <= delta < 0 else (" 🟢" if delta > 5 else " ➖"))
            lines.append(f"| {style} | {actual:.1f}% | {target:.1f}% | {delta:+.1f}% | {align:.2f} |{flag}")
        lines.append("")

        # 二、买入信号
        lines.append("## 二、买入信号")
        lines.append("")
        if not self.buy_signals:
            lines.append("> 当前无买入信号，各风格配置基本符合目标权重。")
        else:
            lines.append("| 风格 | 信号 | 当前权重 | 目标权重 | 建议调整 | 置信度 | 关联ETF |")
            lines.append("|------|------|---------|---------|---------|--------|---------|")
            for sig in self.buy_signals:
                lines.append(
                    f"| {sig['style']} | BUY | {sig['current_weight_pct']:.1f}% | "
                    f"{sig['target_weight_pct']:.1f}% | {sig['suggested_adjust_pct']:+.1f}% | "
                    f"{sig['confidence']} | {', '.join(sig['related_etfs'][:3])} |"
                )
                lines.append(f"| 理由 | {' / '.join(sig['reasons'])} |")
        lines.append("")

        # 三、卖出信号
        lines.append("## 三、卖出信号 (止损/止盈)")
        lines.append("")
        if not self.sell_signals:
            lines.append("> 当前无止损/止盈卖出信号。")
        else:
            lines.append("| 代码 | 风格 | 信号类型 | 持仓收益 | 当前价 | 基准价 |")
            lines.append("|------|------|---------|---------|--------|--------|")
            for sig in self.sell_signals:
                lines.append(
                    f"| {sig['code']} | {sig['style']} | {sig['signal_type']} | "
                    f"{sig['return_pct']:+.2f}% | ￥{sig['current_price']:.3f} | "
                    f"￥{sig['base_price']:.3f} |"
                )
        lines.append("")

        # 四、操作建议
        lines.append("## 四、操作建议")
        lines.append("")
        if self.buy_signals or self.sell_signals:
            if self.buy_signals:
                lines.append("### 买入方向")
                for sig in self.buy_signals:
                    lines.append(f"- **{sig['style']}**: 建议加仓 {sig['suggested_adjust_pct']:+.1f}% 仓位；关注 ETF: {', '.join(sig['related_etfs'][:2])}")
                lines.append("")
            if self.sell_signals:
                lines.append("### 卖出/减仓方向")
                for sig in self.sell_signals:
                    lines.append(f"- **{sig['style']}** ({sig['code']}): 触及{sig['signal_type'].replace('SELL_', '')}阈值 ({sig['return_pct']:+.2f}%)；建议减仓 3~5%")
                lines.append("")
        else:
            lines.append("> 持仓与目标基本一致，无明显偏离 → **维持现有持仓不动**")
        lines.append("")

        lines.append("---")
        lines.append(f"*本报告由 量化策略系统 v5.1 | 社保基金追踪模块 自动生成*")
        return "\n".join(lines)

    # ---------- 导出交易指令 (给 Excel 引擎用) ----------

    def export_rebalance_instructions(self) -> List[Dict]:
        """将信号导出为 ExcelDrivenRebalancingEngineV4 能消费的指令列表"""
        out: List[Dict] = []
        for sig in self.buy_signals:
            out.append({
                "direction": "买入",
                "style": sig["style"],
                "confidence": sig["confidence"],
                "target_weight_pct": sig["target_weight_pct"],
                "codes": sig["related_etfs"][:3],
            })
        for sig in self.sell_signals:
            out.append({
                "direction": "卖出",
                "code": sig["code"],
                "style": sig["style"],
                "return_pct": sig["return_pct"],
                "confidence": sig["confidence"],
            })
        return out


# ============ 便捷入口 ============

def run_tracking_summary(etf_flow_data: Optional[Dict[str, Dict]] = None,
                          holdings: Optional[Dict[str, float]] = None) -> Dict:
    """一键执行: 分析 → 信号 → 报告"""
    tracker = SocialSecurityStyleTracker(holdings=holdings)
    tracker.analyze_styles()
    tracker.fetch_etf_flows(etf_flow_data)
    tracker.run_signal_detection()
    report = tracker.generate_report()
    return {
        "tracker": tracker,
        "style_weights": tracker.style_weights,
        "buy_signals": tracker.buy_signals,
        "sell_signals": tracker.sell_signals,
        "rebalance_instructions": tracker.export_rebalance_instructions(),
        "report": report,
    }


if __name__ == "__main__":
    result = run_tracking_summary()
    print(result["report"])
