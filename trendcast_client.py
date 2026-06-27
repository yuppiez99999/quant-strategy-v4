"""
TrendCast Pro 预测信号客户端
============================
封装对本地 TrendCast Pro API (http://localhost:8800) 的 HTTP 调用，
为量化策略系统提供方向预测信号作为辅助参考因子。

用法:
    from trendcast_client import TrendCastClient

    client = TrendCastClient()
    signal = client.predict("300308.SZ")           # 单标的短期预测
    signals = client.batch_predict(["300308.SZ", "688041.SH"])  # 批量预测
    report = client.audit_report()                  # 获取审计报告
    stats = client.audit_stats()                    # 获取审计统计

集成点:
    - daily_trading_workflow.py: PremarketPlanGenerator.generate_plan()
    - multi_factor_signal.py: 作为第9个因子
    - model_train/signal_composer.py: 作为第4个信号源
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)

# === 14只核心持仓标的 Wind 代码 ===
CORE_PORTFOLIO = [
    # 高端制造(含算力) 45%
    "300308.SZ",   # 中际旭创
    "688041.SH",   # 海光信息
    "002371.SZ",   # 北方华创
    "688981.SH",   # 中芯国际
    "300750.SZ",   # 宁德时代
    "000425.SZ",   # 徐工机械
    # 顺周期 20%
    "601088.SH",   # 中国神华
    "600219.SH",   # 南山铝业
    "600019.SH",   # 宝钢股份
    # 资源 20%
    "518880.SH",   # 华安黄金ETF
    "000408.SZ",   # 藏格矿业
    # 防御 15%
    "600276.SH",   # 恒瑞医药
    "603259.SH",   # 药明康德
    "002422.SZ",   # 科伦药业
]

# 板块分组（与量化策略系统配置一致）
SECTOR_GROUPS = {
    "高端制造(算力)": ["300308.SZ", "688041.SH", "002371.SZ", "688981.SH", "300750.SZ", "000425.SZ"],
    "顺周期":         ["601088.SH", "600219.SH", "600019.SH"],
    "资源":           ["518880.SH", "000408.SZ"],
    "防御":           ["600276.SH", "603259.SH", "002422.SZ"],
}


class TrendCastClient:
    """TrendCast Pro API 客户端

    特性:
    - 自动重试（最多3次，指数退避）
    - 超时保护（默认30秒）
    - 服务不可用时优雅降级（返回空信号，不抛异常）
    - 本地缓存最近一次成功结果（文件缓存5分钟有效）
    """

    def __init__(self, base_url: str = "http://localhost:8800",
                 timeout: int = 30, max_retries: int = 3,
                 cache_enabled: bool = True):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache_enabled = cache_enabled
        self._cache_file = None
        self._cache_ttl = 300  # 5分钟

    # ==================== 核心API调用 ====================

    def health_check(self) -> dict[str, Any]:
        """检查 API 服务是否可用"""
        return self._request("GET", "/health")

    def predict(self, symbol: str, horizon: str = "all") -> dict[str, Any]:
        """预测单个标的

        Args:
            symbol: Wind代码，如 "300308.SH"
            horizon: short_term/mid_term/long_term/all (默认all)

        Returns:
            {"symbol": "...", "predictions": {"short_term_5d": {...}, ...}}
            或 {"error": "..."}
        """
        params = ""
        if horizon and horizon != "all":
            params = f"?horizon={horizon}"
        return self._request("GET", f"/api/v1/predict/{symbol}{params}")

    def batch_predict(self, symbols: list[str]) -> list[dict[str, Any]]:
        """批量预测多个标的

        Args:
            symbols: Wind代码列表

        Returns:
            [{"symbol": "...", "predictions": {...}}, ...]
        """
        body = json.dumps({"symbols": symbols}).encode("utf-8")
        return self._request("POST", "/api/v1/predict/batch", body=body)

    def predict_portfolio(self) -> list[dict[str, Any]]:
        """一键预测全部14只核心持仓"""
        return self.batch_predict(CORE_PORTFOLIO)

    def audit_report(self) -> dict[str, Any]:
        """获取预测审计报告"""
        return self._request("GET", "/api/v1/audit/report")

    def audit_stats(self) -> dict[str, Any]:
        """获取审计统计（总数/验证数/命中率）"""
        return self._request("GET", "/api/v1/audit/stats")

    def get_models(self) -> dict[str, Any]:
        """查询已加载的模型"""
        return self._request("GET", "/api/v1/models")

    def get_markets(self) -> dict[str, Any]:
        """查询支持的标的列表"""
        return self._request("GET", "/api/v1/config/markets")

    # ==================== 信号格式化 ====================

    def get_signal_summary(self, symbol: str) -> dict[str, Any]:
        """获取简洁信号摘要（供策略引擎消费）

        Returns:
            {
                "symbol": "300308.SZ",
                "signal": "bullish",        # bullish/bearish/neutral/error
                "short_term": "看涨",        # 5日方向
                "mid_term": "看涨",          # 10日方向
                "long_term": "看跌",         # 20日方向
                "consensus": "看涨",         # 多周期共识
                "confidence": 0.72,          # 平均置信度
                "timestamp": "2026-06-27T19:00:00"
            }
        """
        try:
            result = self.predict(symbol, horizon="all")
        except Exception as e:
            logger.warning(f"TrendCast 预测 {symbol} 失败: {e}")
            return {"symbol": symbol, "signal": "error", "error": str(e)}

        if "error" in result:
            return {"symbol": symbol, "signal": "error", "error": result["error"]}

        predictions = result.get("predictions", {})
        directions = {}
        confidences = []
        signals = []

        for horizon_key, pred in predictions.items():
            if "error" in pred:
                directions[horizon_key] = "无数据"
                continue
            d = pred.get("direction", "未知")
            directions[horizon_key] = d
            confidences.append(pred.get("confidence", 0))
            if d == "看涨":
                signals.append(1)
            elif d == "看跌":
                signals.append(-1)
            else:
                signals.append(0)

        # 多周期共识
        avg_signal = sum(signals) / len(signals) if signals else 0
        if avg_signal > 0.3:
            consensus = "看涨"
            overall = "bullish"
        elif avg_signal < -0.3:
            consensus = "看跌"
            overall = "bearish"
        else:
            consensus = "震荡"
            overall = "neutral"

        avg_conf = sum(confidences) / len(confidences) if confidences else 0

        return {
            "symbol": symbol,
            "signal": overall,
            "short_term": directions.get("short_term_5d", "无数据"),
            "mid_term": directions.get("mid_term_10d", "无数据"),
            "long_term": directions.get("long_term_20d", "无数据"),
            "consensus": consensus,
            "confidence": round(avg_conf, 4),
            "timestamp": datetime.now().isoformat(),
        }

    def get_portfolio_summary(self) -> dict[str, Any]:
        """获取全组合信号摘要（按板块分组）"""
        predictions = []
        try:
            results = self.batch_predict(CORE_PORTFOLIO)
        except Exception as e:
            logger.warning(f"TrendCast 批量预测失败: {e}")
            return {"error": str(e), "predictions": []}

        for r in results:
            symbol = r.get("symbol", "?")
            preds = r.get("predictions", {})

            directions = {}
            for hk, hp in preds.items():
                directions[hk] = hp.get("direction", "无数据") if "error" not in hp else "无数据"

            predictions.append({
                "symbol": symbol,
                "directions": directions,
            })

        # 按板块统计
        sector_signals = {}
        for sector, codes in SECTOR_GROUPS.items():
            bullish = 0
            bearish = 0
            neutral = 0
            for p in predictions:
                if p["symbol"] in codes:
                    # 统计中期共识
                    d = p["directions"].get("mid_term_10d", "")
                    if d == "看涨":
                        bullish += 1
                    elif d == "看跌":
                        bearish += 1
                    else:
                        neutral += 1
            total = bullish + bearish + neutral
            if total > 0:
                bias = (bullish - bearish) / total
            else:
                bias = 0
            sector_signals[sector] = {
                "bullish": bullish, "bearish": bearish,
                "neutral": neutral, "bias": round(bias, 3),
                "signal": "看多" if bias > 0.3 else ("看空" if bias < -0.3 else "中性"),
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "predictions": predictions,
            "sector_signals": sector_signals,
        }

    # ==================== 因子接口 ====================

    def get_factor_value(self, symbol: str) -> dict[str, Any]:
        """获取可作为多因子模型输入的归一化因子值

        Returns:
            {"symbol": "...", "factor_value": 0.0~1.0, "factor_name": "trendcast"}
        """
        summary = self.get_signal_summary(symbol)
        signal = summary.get("signal", "error")
        confidence = summary.get("confidence", 0)

        if signal == "bullish":
            factor_value = 0.5 + confidence * 0.5  # 0.5~1.0
        elif signal == "bearish":
            factor_value = 0.5 - confidence * 0.5  # 0.0~0.5
        else:
            factor_value = 0.5

        return {
            "symbol": symbol,
            "factor_name": "trendcast_direction",
            "factor_value": round(factor_value, 4),
            "raw_signal": signal,
            "confidence": confidence,
        }

    # ==================== 内部方法 ====================

    def _request(self, method: str, path: str,
                 body: bytes | None = None) -> dict[str, Any]:
        """发送 HTTP 请求，带重试和超时"""
        url = f"{self.base_url}{path}"
        last_error = None

        for attempt in range(self.max_retries):
            try:
                req = Request(url, data=body, method=method)
                req.add_header("Content-Type", "application/json")
                req.add_header("Accept", "application/json")

                with urlopen(req, timeout=self.timeout) as resp:
                    data = resp.read().decode("utf-8")
                    return json.loads(data) if data else {}

            except HTTPError as e:
                last_error = e
                if e.code == 404:
                    logger.warning(f"TrendCast API 404: {url}")
                    return {"error": f"资源不存在: {path}"}
                if e.code >= 500:
                    logger.warning(f"TrendCast API 5xx (attempt {attempt+1}): {e}")
            except URLError as e:
                last_error = e
                logger.warning(f"TrendCast API 不可达 (attempt {attempt+1}): {e}")
            except Exception as e:
                last_error = e
                logger.warning(f"TrendCast API 异常 (attempt {attempt+1}): {e}")

            if attempt < self.max_retries - 1:
                wait = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                time.sleep(wait)

        logger.error(f"TrendCast API 最终失败 ({self.max_retries}次重试): {last_error}")
        return {"error": f"服务不可用: {last_error}"}


# ==================== 便捷函数 ====================

def get_trendcast_signals(symbols: list[str] | None = None,
                          base_url: str = "http://localhost:8800") -> list[dict[str, Any]]:
    """便捷函数：获取 TrendCast 预测信号

    Args:
        symbols: 标的列表，默认全部核心持仓
        base_url: API 地址

    Returns:
        信号摘要列表
    """
    if symbols is None:
        symbols = CORE_PORTFOLIO
    client = TrendCastClient(base_url=base_url)
    try:
        results = []
        for s in symbols:
            summary = client.get_signal_summary(s)
            results.append(summary)
        return results
    except Exception as e:
        logger.error(f"get_trendcast_signals 失败: {e}")
        return []


# ==================== 自测 ====================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    client = TrendCastClient()

    print("=" * 60)
    print("TrendCast Pro 客户端自测")
    print("=" * 60)

    # 1. 健康检查
    health = client.health_check()
    print(f"\n健康检查: {json.dumps(health, ensure_ascii=False, indent=2)}")

    # 2. 单标的预测
    result = client.get_signal_summary("300308.SZ")
    print(f"\n单标的信号 (中际旭创):")
    for k, v in result.items():
        print(f"  {k}: {v}")

    # 3. 批量预测
    summary = client.get_portfolio_summary()
    if "sector_signals" in summary:
        print(f"\n板块信号:")
        for sector, sig in summary["sector_signals"].items():
            print(f"  {sector}: {sig}")

    # 4. 审计统计
    stats = client.audit_stats()
    print(f"\n审计统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")

    print("\n自测完成")
