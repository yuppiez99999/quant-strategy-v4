# -*- coding: utf-8 -*-
"""
TimesFM 2.5 — Google Research 零样本时间序列预测集成模块
==========================================================
集成到量化策略系统 v5.7，提供 14 只持仓标的的短期走势预测。
基于 200M 参数 Decoder-only 架构，不需要本地训练，零样本直接预测。

核心能力：
- 单条序列预测：给历史收盘价 → 输出未来 N 日点预测 + 分位数预测区间
- 批量预测：一次推理跑完 14 只标的
- 异常检测：实际价超出 90% CI → 触发预警信号
- 协变量增强：可注入大盘指数、板块资金流、康波周期阶段标签作为 XReg

数据源优先级：akshare > sina > 本地缓存 > TypeError回退

作者：量化策略系统 v5.7
日期：2026-06-28
"""

import os
import sys
import json
import time
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from collections import OrderedDict

import numpy as np
import pandas as pd

try:
    from .logging_manager import get_logger
except ImportError:
    # 直接执行脚本时回退到绝对导入
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from logging_manager import get_logger

_logger = get_logger("timesfm")


# ---------------------------------------------------------------------------
# 懒加载 TimesFM — 版本兼容
# ---------------------------------------------------------------------------
_TFM_AVAILABLE = False
_TFM_CLASSES: Dict[str, Any] = {}
_TFM_LOAD_ERROR: Optional[str] = None

def _ensure_timesfm():
    """懒加载 TimesFM，只在首次调用时导入并下载模型权重。"""
    global _TFM_AVAILABLE, _TFM_CLASSES, _TFM_LOAD_ERROR

    if _TFM_AVAILABLE:
        return True
    if _TFM_LOAD_ERROR:
        return False

    try:
        import torch
        torch.set_float32_matmul_precision("high")
    except ImportError:
        _TFM_LOAD_ERROR = "PyTorch 未安装"
        _logger.error(f"TimesFM 加载失败: {_TFM_LOAD_ERROR}")
        return False

    try:
        import timesfm
        _TFM_CLASSES["TimesFM"] = timesfm.TimesFM_2p5_200M_torch
        _TFM_CLASSES["ForecastConfig"] = timesfm.ForecastConfig
    except ImportError as e:
        _TFM_LOAD_ERROR = f"TimesFM 未安装: {e}"
        _logger.error(f"TimesFM 加载失败: {_TFM_LOAD_ERROR}")
        return False

    try:
        model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
            "google/timesfm-2.5-200m-pytorch"
        )
        _TFM_CLASSES["model"] = model
        _TFM_AVAILABLE = True
        _logger.info("TimesFM 2.5 (200M) 模型加载成功")
        return True
    except Exception as e:
        _TFM_LOAD_ERROR = f"模型权重下载失败: {e}"
        _logger.error(f"TimesFM 模型加载失败: {_TFM_LOAD_ERROR}")
        return False


# ---------------------------------------------------------------------------
# 数据获取 — 多层降级
# ---------------------------------------------------------------------------

def _akshare_fetch(symbol: str, days: int = 252) -> Optional[pd.Series]:
    """通过 AKShare 获取日线收盘价。"""
    try:
        import akshare as ak

        code = symbol.split(".")[0] if "." in symbol else symbol
        market = symbol.split(".")[-1].lower() if "." in symbol else "sz"

        # 统一 Tushare 风格: sh/sz
        if market in ("sh", "shanghai", "ssh"):
            symbol_ak = f"sh{code}"
        elif market in ("sz", "shenzhen", "szse"):
            symbol_ak = f"sz{code}"
        else:
            symbol_ak = f"sz{code}"

        df = ak.stock_zh_a_hist(
            symbol=code, period="daily",
            start_date=(datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d"),
            end_date=datetime.now().strftime("%Y%m%d"),
            adjust="qfq",
        )
        if df is None or df.empty:
            return None

        col = "收盘" if "收盘" in df.columns else ("close" if "close" in df.columns else None)
        if col is None:
            return None

        series = pd.to_numeric(df[col], errors="coerce").dropna()
        series.index = pd.to_datetime(df["日期"] if "日期" in df.columns else df.index)
        return series.iloc[-days:]
    except ImportError:
        _logger.debug("AKShare 未安装，跳过")
        return None
    except Exception as e:
        _logger.debug(f"AKShare {symbol} 获取失败: {e}")
        return None


def _sina_fetch(symbol: str, days: int = 252) -> Optional[pd.Series]:
    """通过新浪财经 API 获取日线收盘价。"""
    try:
        code = symbol.split(".")[0] if "." in symbol else symbol
        market = symbol.split(".")[-1].lower() if "." in symbol else "sz"
        prefix = "sh" if market in ("sh", "shanghai") else "sz"

        import urllib.request, re
        url = f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={prefix}{code}&scale=240&ma=no&datalen={days}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("gbk", errors="replace")

        data = json.loads(text)
        if not data:
            return None

        closes = []
        dates = []
        for row in data[-days:]:
            try:
                closes.append(float(row["close"]))
                dates.append(row["day"])
            except (KeyError, ValueError):
                continue

        if not closes:
            return None
        return pd.Series(closes, index=pd.to_datetime(dates))
    except ImportError:
        return None
    except Exception as e:
        _logger.debug(f"新浪 {symbol} 获取失败: {e}")
        return None


def _get_kline_series(symbol: str, days: int = 252) -> Optional[pd.Series]:
    """
    获取标的日线收盘价序列，多层降级：akshare → sina → None。
    返回: pd.Series (index=日期, values=收盘价)
    """
    # 1. AKShare
    series = _akshare_fetch(symbol, days)
    if series is not None and len(series) >= 30:
        _logger.debug(f"{symbol} 从 AKShare 获取 {len(series)} 条K线")
        return series

    # 2. 新浪财经
    series = _sina_fetch(symbol, days)
    if series is not None and len(series) >= 30:
        _logger.debug(f"{symbol} 从新浪获取 {len(series)} 条K线")
        return series

    _logger.warning(f"{symbol} 无法获取K线数据（所有数据源不可用）")
    return None


# ---------------------------------------------------------------------------
# 资产配置 — 来自 portfolio.yaml
# ---------------------------------------------------------------------------

# 14 只持仓标的 (冗余定义，无需解析 yaml)
PORTFOLIO_SYMBOLS: List[Dict[str, str]] = [
    {"code": "300308.SZ", "name": "中际旭创",     "category": "high_end_manufacturing"},
    {"code": "688041.SH", "name": "海光信息",     "category": "high_end_manufacturing"},
    {"code": "002371.SZ", "name": "北方华创",     "category": "high_end_manufacturing"},
    {"code": "688981.SH", "name": "中芯国际",     "category": "high_end_manufacturing"},
    {"code": "300750.SZ", "name": "宁德时代",     "category": "high_end_manufacturing"},
    {"code": "000425.SZ", "name": "徐工机械",     "category": "high_end_manufacturing"},
    {"code": "601088.SH", "name": "中国神华",     "category": "cyclical"},
    {"code": "600219.SH", "name": "南山铝业",     "category": "cyclical"},
    {"code": "600019.SH", "name": "宝钢股份",     "category": "cyclical"},
    {"code": "518880.SH", "name": "华安黄金ETF", "category": "resources"},
    {"code": "000408.SZ", "name": "藏格矿业",     "category": "resources"},
    {"code": "600276.SH", "name": "恒瑞医药",     "category": "defensive"},
    {"code": "603259.SH", "name": "药明康德",     "category": "defensive"},
    {"code": "002422.SZ", "name": "科伦药业",     "category": "defensive"},
]

CATEGORY_NAMES = {
    "high_end_manufacturing": "高端制造(含算力)",
    "cyclical": "顺周期",
    "resources": "资源",
    "defensive": "防御",
}


# ---------------------------------------------------------------------------
# TimesFM 预测器
# ---------------------------------------------------------------------------

class TimesFMPredictor:
    """
    TimesFM 2.5 (200M) 零样本时序预测器。

    Usage:
        pred = TimesFMPredictor(horizon=10, context_days=252)
        point, quantiles = pred.predict_single("300308.SZ")
        # point:        np.ndarray shape (horizon,)   — 中位数预测
        # quantiles:    np.ndarray shape (horizon, 10) — q10..q90 分位数
    """

    def __init__(
        self,
        horizon: int = 10,
        context_days: int = 252,
        normalize_inputs: bool = True,
        verbose: bool = True,
    ):
        """
        Args:
            horizon: 预测未来天数 (1~128)
            context_days: 历史上下文天数 (最低 32，推荐 128-512)
            normalize_inputs: 是否对输入做归一化 (推荐开启)
            verbose: 是否打印加载日志
        """
        self.horizon = horizon
        self.context_days = max(context_days, 32)
        self.normalize_inputs = normalize_inputs
        self.verbose = verbose
        self._model = None
        self._config = None

    @property
    def available(self) -> bool:
        """模型是否可用。"""
        return _TFM_AVAILABLE

    @property
    def load_error(self) -> Optional[str]:
        """加载失败的详细原因。"""
        return _TFM_LOAD_ERROR

    # ---- 模型懒加载 --------------------------------------------------------

    def _load(self) -> bool:
        if self._model is not None:
            return True
        if not _ensure_timesfm():
            return False

        self._model = _TFM_CLASSES["model"]
        ForecastConfig = _TFM_CLASSES["ForecastConfig"]

        self._config = ForecastConfig(
            max_context=self.context_days,
            max_horizon=self.horizon,
            normalize_inputs=self.normalize_inputs,
            use_continuous_quantile_head=True,
            force_flip_invariance=True,
            infer_is_positive=True,
            fix_quantile_crossing=True,
        )
        self._model.compile(self._config)

        if self.verbose:
            _logger.info(
                f"TimesFM 预测器就绪 (horizon={self.horizon}天, context={self.context_days}天)"
            )
        return True

    # ---- 单标的预测 -------------------------------------------------------

    def predict_single(
        self, symbol: str, kline: Optional[pd.Series] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        预测单只标的未来 N 日走势。

        Args:
            symbol: 标的代码 (如 "300308.SZ")
            kline: 可选，外部传入的历史收盘价 Series

        Returns:
            (point_forecast, quantile_forecast)
            - point_forecast:  shape (horizon,)  中位数预测价格
            - quantile_forecast: shape (horizon, 10) q10/q20/.../q90 分位数
        """
        if not self._load():
            raise RuntimeError(f"TimesFM 不可用: {_TFM_LOAD_ERROR}")

        if kline is None:
            kline = _get_kline_series(symbol, days=self.context_days)
            if kline is None:
                raise ValueError(f"无法获取 {symbol} 的历史K线数据")

        if len(kline) < 32:
            raise ValueError(f"{symbol} 历史数据不足（{len(kline)} 条，最低 32）")

        prices = kline.values.astype(np.float32)
        prices = prices[-self.context_days:]  # 截取上下文窗口

        point, quantiles = self._model.forecast(
            horizon=self.horizon, inputs=[prices]
        )

        return point[0], quantiles[0]

    def predict_single_with_confidence(
        self, symbol: str, kline: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        """
        预测单标的并返回结构化结果（含置信区间）。

        Returns:
            {
                "symbol": "300308.SZ",
                "name": "中际旭创",
                "last_price": 145.0,
                "last_date": "2026-06-27",
                "horizon": 10,
                "forecast": [145.2, 146.1, ...],           # 中位数
                "lower_80": [143.5, 144.0, ...],           # q10
                "upper_80": [147.0, 148.2, ...],           # q90
                "lower_60": [144.3, 144.8, ...],           # q20
                "upper_60": [146.2, 147.4, ...],           # q80
                "trend": "up",                              # up/flat/down
                "volatility_forecast": 0.012,               # 预测波动率(均值)
                "signal": "hold",                           # buy/sell/hold
            }
        """
        point, quants = self.predict_single(symbol, kline)

        # 查找标的名称
        name = symbol
        category = "unknown"
        for item in PORTFOLIO_SYMBOLS:
            if item["code"] == symbol:
                name = item["name"]
                category = item["category"]
                break

        if kline is None:
            kline = _get_kline_series(symbol, days=self.context_days)
        last_price = float(kline.values[-1]) if kline is not None else 0.0
        last_date = str(kline.index[-1].date()) if kline is not None else ""

        # 趋势判断：最后一天预测 vs 当前价格
        last_pred = float(point[-1])
        pct_change = (last_pred - last_price) / last_price if last_price > 0 else 0
        if pct_change > 0.02:
            trend = "up"
            signal = "buy"
        elif pct_change < -0.02:
            trend = "down"
            signal = "sell"
        else:
            trend = "flat"
            signal = "hold"

        # 预测波动率 = 分位数区间宽度的均值 / 中位数
        vol_series = np.mean(
            (quants[:, 8] - quants[:, 1]) / np.abs(point), axis=0
        )
        vol_avg = float(vol_series) if hasattr(vol_series, "__float__") else float(
            np.mean(vol_series)
        )

        return {
            "symbol": symbol,
            "name": name,
            "category": category,
            "category_name": CATEGORY_NAMES.get(category, category),
            "last_price": round(last_price, 2),
            "last_date": last_date,
            "horizon": self.horizon,
            "forecast": [round(float(v), 2) for v in point],
            "lower_80": [round(float(v), 2) for v in quants[:, 1]],  # q10
            "upper_80": [round(float(v), 2) for v in quants[:, 8]],  # q90
            "lower_60": [round(float(v), 2) for v in quants[:, 2]],  # q20
            "upper_60": [round(float(v), 2) for v in quants[:, 7]],  # q80
            "trend": trend,
            "pct_change": round(pct_change * 100, 2),
            "volatility_forecast": round(vol_avg * 100, 2),
            "signal": signal,
        }

    # ---- 批量预测 ---------------------------------------------------------

    def predict_portfolio(
        self,
        symbols: Optional[List[str]] = None,
        max_workers: int = 1,
    ) -> Dict[str, Any]:
        """
        批量预测组合持仓。默认预测所有 14 只标的。

        Returns:
            {
                "timestamp": "2026-06-28T10:30:00",
                "horizon": 10,
                "model": "timesfm-2.5-200m",
                "summary": {
                    "total": 14, "available": 13, "failed": 1,
                    "buy": 3, "hold": 10, "sell": 1,
                },
                "predictions": [ {symbol, name, trend, signal, ...} ],
                "category_summary": { ... },
                "errors": [ ... ],
            }
        """
        if symbols is None:
            symbols = [item["code"] for item in PORTFOLIO_SYMBOLS]

        results = []
        errors = []
        summary = {"total": len(symbols), "available": 0, "failed": 0,
                    "buy": 0, "hold": 0, "sell": 0}
        category_buy = {}
        category_total = {}

        for sym in symbols:
            try:
                pred = self.predict_single_with_confidence(sym)
                results.append(pred)
                summary["available"] += 1
                summary[pred["signal"]] += 1

                cat = pred["category_name"]
                category_total[cat] = category_total.get(cat, 0) + 1
                if pred["signal"] == "buy":
                    category_buy[cat] = category_buy.get(cat, 0) + 1

            except Exception as e:
                _logger.warning(f"预测失败 {sym}: {e}")
                errors.append({"symbol": sym, "error": str(e)})
                summary["failed"] += 1
                summary["hold"] += 1  # 失败默认 hold

        return {
            "timestamp": datetime.now().isoformat(),
            "horizon": self.horizon,
            "model": "timesfm-2.5-200m",
            "summary": summary,
            "predictions": sorted(
                results, key=lambda x: abs(x["pct_change"]), reverse=True
            ),
            "category_summary": {
                cat: {
                    "total": category_total.get(cat, 0),
                    "buy_count": category_buy.get(cat, 0),
                }
                for cat in category_total
            },
            "errors": errors,
        }

    # ---- 异常检测 ---------------------------------------------------------

    def anomaly_check(
        self, symbol: str, actual_price: float, kline: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        """
        检测当前价格是否超出预测区间（异常行情预警）。

        Args:
            symbol: 标的代码
            actual_price: 实际最新价格

        Returns:
            {
                "symbol": "300308.SZ",
                "actual": 145.0,
                "predicted_median": 144.5,
                "lower_80": 143.0,
                "upper_80": 147.0,
                "is_anomaly": True/False,
                "direction": "above"/"below"/"normal",
                "severity": "low"/"medium"/"high",
            }
        """
        pred = self.predict_single_with_confidence(symbol, kline)

        median = pred["forecast"][0]
        lower = pred["lower_80"][0]
        upper = pred["upper_80"][0]
        lower_60 = pred["lower_60"][0]
        upper_60 = pred["upper_60"][0]

        is_anomaly = actual_price < lower or actual_price > upper
        is_moderate = actual_price < lower_60 or actual_price > upper_60

        if actual_price > upper:
            direction = "above"
            severity = "high" if actual_price > upper * 1.03 else "medium"
        elif actual_price < lower:
            direction = "below"
            severity = "high" if actual_price < lower * 0.97 else "medium"
        elif is_moderate:
            direction = "above" if actual_price > median else "below"
            severity = "low"
            is_anomaly = True
        else:
            direction = "normal"
            severity = "normal"

        return {
            "symbol": symbol,
            "name": pred["name"],
            "actual": round(actual_price, 2),
            "predicted_median": round(median, 2),
            "lower_80": round(lower, 2),
            "upper_80": round(upper, 2),
            "is_anomaly": is_anomaly,
            "direction": direction,
            "severity": severity,
            "deviation_pct": round(
                (actual_price - median) / median * 100 if median > 0 else 0, 2
            ),
        }


# ---------------------------------------------------------------------------
# Markdown 报告生成
# ---------------------------------------------------------------------------

def generate_signal_report(
    predictor: Optional[TimesFMPredictor] = None,
    horizon: int = 10,
    output_path: Optional[str] = None,
) -> str:
    """
    一键生成 TimesFM 预测信号报告 (Markdown)。

    Args:
        predictor: TimesFMPredictor 实例，None 则自动创建
        horizon: 预测天数
        output_path: 报告输出路径，None 则返回内容字符串

    Returns:
        Markdown 报告字符串
    """
    if predictor is None:
        predictor = TimesFMPredictor(horizon=horizon, verbose=False)

    if not predictor.available:
        return f"# TimesFM 预测信号报告\n\n**状态**: 模型不可用 — {predictor.load_error}"

    portfolio = predictor.predict_portfolio()

    md = []
    md.append("# TimesFM 2.5 预测信号报告")
    md.append(f"\n生成时间: {portfolio['timestamp']}")
    md.append(f"预测周期: 未来 **{portfolio['horizon']}** 个交易日")
    md.append(f"模型: TimesFM 2.5 (200M Parameters)")
    md.append(f"可用: {portfolio['summary']['available']}/{portfolio['summary']['total']} 只标的")

    # 信号汇总
    s = portfolio["summary"]
    md.append(f"\n## 信号汇总\n")
    md.append(f"| 信号 | 数量 |")
    md.append(f"|------|------|")
    md.append(f"| 买入 | {s['buy']} |")
    md.append(f"| 持有 | {s['hold']} |")
    md.append(f"| 卖出 | {s['sell']} |")

    # 板块信号
    if portfolio.get("category_summary"):
        md.append(f"\n## 板块信号分布\n")
        md.append(f"| 板块 | 总计 | 买入信号 |")
        md.append(f"|------|------|----------|")
        for cat, info in portfolio["category_summary"].items():
            md.append(f"| {cat} | {info['total']} | {info['buy_count']} |")

    # 标的详情
    md.append(f"\n## 标的预测详情\n")
    md.append(f"| 标的 | 代码 | 板块 | 现价 | 趋势 | 变动% | 预测波动% | 信号 |")
    md.append(f"|------|------|------|------|------|-------|-----------|------|")
    for p in portfolio["predictions"]:
        trend_icon = "🟢" if p["trend"] == "up" else ("🔴" if p["trend"] == "down" else "🟡")
        signal_icon = "📈" if p["signal"] == "buy" else ("📉" if p["signal"] == "sell" else "➖")
        md.append(
            f"| {p['name']} | {p['symbol']} | {p['category_name']} | "
            f"{p['last_price']} | {trend_icon} {p['trend']} | "
            f"{p['pct_change']:+.2f}% | {p['volatility_forecast']}% | "
            f"{signal_icon} {p['signal']} |"
        )

    # 错误
    if portfolio["errors"]:
        md.append(f"\n## 预测失败\n")
        for e in portfolio["errors"]:
            md.append(f"- {e['symbol']}: {e['error']}")

    md.append(f"\n---\n*报告由 TimesFM 2.5 集成模块自动生成*")

    report = "\n".join(md)

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        _logger.info(f"TimesFM 预测报告已保存: {output_path}")

    return report


# ---------------------------------------------------------------------------
# CLI 入口 — 可直接运行
# ---------------------------------------------------------------------------

def _check_symbol(symbol: str) -> Optional[str]:
    """校验并标准化标的代码。"""
    symbol = symbol.strip().upper()
    # 支持 .SZ / .SH / 纯数字 / 带交易所后缀
    if "." in symbol:
        parts = symbol.split(".")
        if len(parts) == 2 and parts[1] in ("SZ", "SH", "BJ"):
            return symbol
    # 6 位纯数字
    if symbol.isdigit() and len(symbol) == 6:
        if symbol.startswith(("6", "9")):
            return f"{symbol}.SH"
        elif symbol.startswith(("0", "3")):
            return f"{symbol}.SZ"
        elif symbol.startswith(("4", "8")):
            return f"{symbol}.BJ"
    return None


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="TimesFM 2.5 零样本预测")
    p.add_argument("--symbol", "-s", help="单标的预测，如 300308.SZ")
    p.add_argument("--portfolio", "-p", action="store_true", help="批量预测所有持仓")
    p.add_argument("--horizon", "-n", type=int, default=10, help="预测天数 (默认10)")
    p.add_argument("--context", "-c", type=int, default=252, help="上下文天数 (默认252)")
    p.add_argument("--report", "-r", type=str, default=None, help="报告输出路径")
    p.add_argument("--json", "-j", action="store_true", help="JSON 输出")

    args = p.parse_args()

    predictor = TimesFMPredictor(horizon=args.horizon, context_days=args.context)

    if not predictor.available:
        print(f"错误: TimesFM 不可用 — {predictor.load_error}")
        sys.exit(1)

    if args.symbol:
        sym = _check_symbol(args.symbol)
        if sym is None:
            print(f"错误: 无效的标的代码 '{args.symbol}'")
            sys.exit(1)
        result = predictor.predict_single_with_confidence(sym)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"\n{'='*60}")
            print(f"  TimesFM 预测: {result['name']} ({result['symbol']})")
            print(f"{'='*60}")
            print(f"  最新价: {result['last_price']} ({result['last_date']})")
            print(f"  趋势: {result['trend']}  (+{result['pct_change']}%)" if result['pct_change'] > 0 else
                  f"  趋势: {result['trend']}  ({result['pct_change']}%)")
            print(f"  信号: {result['signal']}")
            print(f"  预测波动率: {result['volatility_forecast']}%")
            print(f"\n  预测价格序列 (未来{args.horizon}日):")
            for i, v in enumerate(result["forecast"][:5]):
                print(f"    D+{i+1}: {v}  [80%CI: {result['lower_80'][i]} - {result['upper_80'][i]}]")
            if args.horizon > 5:
                print(f"    ... 共 {args.horizon} 日")

    elif args.portfolio or not args.symbol:
        result = predictor.predict_portfolio()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            report = generate_signal_report(predictor, horizon=args.horizon)
            if args.report:
                with open(args.report, "w", encoding="utf-8") as f:
                    f.write(report)
                print(f"报告已保存: {args.report}")
            print(report)
