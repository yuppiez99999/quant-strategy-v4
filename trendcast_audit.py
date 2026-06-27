"""
TrendCast Pro 审计桥接模块
===========================
将 TrendCast Pro 的预测审计系统适配到量化策略系统的每日报告流程中。

核心功能:
    1. record_prediction()  — 在生成预测时记录到 JSONL 审计文件
    2. verify_predictions()  — 到期后回溯验证预测准确率
    3. generate_audit_report() — 生成 Markdown 格式审计报告（按周期/标的/板块统计）
    4. detect_drift()       — 检测模型漂移（近30天命中率 vs 整体命中率）

审计文件存放位置:
    11_量化策略/logs/trendcast_audit/predictions.jsonl
    11_量化策略/reports/trendcast_audit_report.md

用法:
    from trendcast_audit import TrendCastAudit

    audit = TrendCastAudit()
    audit.record_prediction(symbol="300308.SZ", horizon="short_term_5d",
                            direction="看涨", probability=0.72, latest_close=150.0)
    verified = audit.verify_predictions(data_fetcher=my_price_fetcher)
    report = audit.generate_audit_report()

集成点:
    - daily_runner.py: step_trendcast_predict() 中调用
    - daily_trading_workflow.py: PremarketPlanGenerator 中调用
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class TrendCastAudit:
    """预测审计器 — 量化策略系统适配版

    基于 TrendCast Pro 的 PredictionAudit 核心逻辑，
    适配量化策略系统的目录结构和数据获取方式。
    """

    def __init__(self, base_dir: str | None = None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_dir = Path(base_dir)

        # 审计数据目录
        self.audit_dir = self.base_dir / "logs" / "trendcast_audit"
        self.audit_dir.mkdir(parents=True, exist_ok=True)

        self.record_file = self.audit_dir / "predictions.jsonl"
        self.report_file = self.base_dir / "reports" / "trendcast_audit_report.md"
        self.report_file.parent.mkdir(parents=True, exist_ok=True)

    # ========== 记录 ==========

    def record_prediction(self, symbol: str, horizon: str,
                          direction: str, probability: float,
                          latest_close: float | None = None,
                          latest_date: str | None = None,
                          source: str = "trendcast_pro") -> str:
        """记录一条预测到审计文件

        Args:
            symbol:     标的代码，如 "300308.SZ"
            horizon:    预测周期，如 "short_term_5d"/"mid_term_10d"/"long_term_20d"
            direction:  预测方向，"看涨"/"看跌"
            probability: 预测概率 0.0~1.0
            latest_close: 预测时最新收盘价
            latest_date: 预测时最新日期
            source:     信号来源标识

        Returns:
            预测记录ID
        """
        horizon_days_map = {
            "short_term_5d": 5, "mid_term_10d": 10, "long_term_20d": 20,
        }
        horizon_days = horizon_days_map.get(horizon, 5)
        prediction_code = 1 if direction == "看涨" else 0

        entry_id = f"{symbol}_{horizon}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        entry = {
            "id": entry_id,
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "horizon": horizon,
            "horizon_days": horizon_days,
            "direction": direction,
            "prediction": prediction_code,
            "probability": round(probability, 4),
            "confidence": round(probability, 4),
            "latest_date": latest_date or datetime.now().strftime("%Y-%m-%d"),
            "latest_close": latest_close,
            "source": source,
            "verified": False,
            "actual_direction": None,
            "hit": None,
            "actual_return": None,
        }

        with open(self.record_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        logger.debug(f"审计记录: {entry_id} ({symbol} {direction})")
        return entry_id

    def record_batch(self, predictions: list[dict[str, Any]]) -> int:
        """批量记录预测

        Args:
            predictions: [{"symbol":..., "horizon":..., "direction":..., "probability":...}, ...]

        Returns:
            记录数量
        """
        count = 0
        for p in predictions:
            try:
                self.record_prediction(
                    symbol=p.get("symbol", ""),
                    horizon=p.get("horizon", "short_term_5d"),
                    direction=p.get("direction", "未知"),
                    probability=p.get("probability", 0.5),
                    latest_close=p.get("latest_close"),
                    latest_date=p.get("latest_date"),
                    source=p.get("source", "trendcast_pro"),
                )
                count += 1
            except Exception as e:
                logger.warning(f"记录预测失败: {p.get('symbol', '?')} - {e}")
        return count

    # ========== 加载 ==========

    def _load_records(self) -> list[dict]:
        """加载所有预测记录"""
        if not self.record_file.exists():
            return []
        records = []
        with open(self.record_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records

    # ========== 验证 ==========

    def verify_predictions(self,
                           data_fetcher: Callable[[str, str, str], Any] | None = None,
                           price_cache: dict[str, float] | None = None) -> int:
        """回溯验证已到期的预测

        Args:
            data_fetcher: (symbol, start_date, end_date) -> DataFrame with 'close' column
                          或返回价格字典 {date: close_price}
            price_cache:  直接提供当前价格字典 {symbol: latest_price}，用于快速验证

        Returns:
            新验证的预测数量
        """
        records = self._load_records()
        verified_count = 0
        now = datetime.now()

        updated = []
        for rec in records:
            if rec.get("verified"):
                updated.append(rec)
                continue

            pred_time = datetime.fromisoformat(rec["timestamp"])
            horizon_days = rec.get("horizon_days", 5)
            verify_date = pred_time + timedelta(days=horizon_days)

            if now < verify_date:
                updated.append(rec)
                continue

            # 已到期，验证
            try:
                symbol = rec["symbol"]
                pred_close = rec.get("latest_close")

                # 方法1: 使用价格缓存（最快）
                if price_cache and symbol in price_cache:
                    current_close = price_cache[symbol]
                elif data_fetcher:
                    # 方法2: 使用数据获取函数
                    latest_date = rec.get("latest_date", pred_time.strftime("%Y-%m-%d"))
                    df = data_fetcher(symbol, latest_date, now.strftime("%Y-%m-%d"))
                    if df is None or len(df) < 2:
                        updated.append(rec)
                        continue
                    current_close = float(df.iloc[-1]["close"])
                    pred_close = float(df.iloc[0]["close"])
                else:
                    updated.append(rec)
                    continue

                if pred_close is None or pred_close == 0:
                    updated.append(rec)
                    continue

                actual_return = (current_close - float(pred_close)) / float(pred_close)
                actual_direction = 1 if actual_return > 0 else 0

                rec["verified"] = True
                rec["actual_direction"] = actual_direction
                rec["actual_return"] = round(actual_return, 6)
                rec["hit"] = (rec["prediction"] == actual_direction)
                verified_count += 1

            except Exception as e:
                logger.warning(f"验证 {rec.get('id')} 失败: {e}")

            updated.append(rec)

        # 回写
        with open(self.record_file, "w", encoding="utf-8") as f:
            for rec in updated:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        logger.info(f"审计验证完成: 新验证 {verified_count} 条")
        return verified_count

    # ========== 报告生成 ==========

    def generate_audit_report(self) -> str:
        """生成 Markdown 格式审计报告

        包含：
        - 总览（总数/验证数/命中率）
        - 按预测周期统计
        - 按标的统计
        - 按信号来源统计
        - 模型漂移检测
        """
        now = datetime.now()
        records = self._load_records()
        verified = [r for r in records if r.get("verified")]

        if not verified:
            return "暂无已验证的预测记录"

        total_all = len(records)
        total = len(verified)
        hits = sum(1 for r in verified if r.get("hit"))
        hit_rate = hits / total if total > 0 else 0

        # 按周期统计
        by_horizon: dict[str, dict] = {}
        for r in verified:
            h = r.get("horizon", "unknown")
            if h not in by_horizon:
                by_horizon[h] = {"total": 0, "hits": 0}
            by_horizon[h]["total"] += 1
            if r.get("hit"):
                by_horizon[h]["hits"] += 1

        # 按标的统计
        by_symbol: dict[str, dict] = {}
        for r in verified:
            s = r.get("symbol", "unknown")
            if s not in by_symbol:
                by_symbol[s] = {"total": 0, "hits": 0}
            by_symbol[s]["total"] += 1
            if r.get("hit"):
                by_symbol[s]["hits"] += 1

        # 按来源统计
        by_source: dict[str, dict] = {}
        for r in verified:
            src = r.get("source", "unknown")
            if src not in by_source:
                by_source[src] = {"total": 0, "hits": 0}
            by_source[src]["total"] += 1
            if r.get("hit"):
                by_source[src]["hits"] += 1

        lines = [
            "# TrendCast Pro 预测审计报告",
            "",
            f"生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 总览",
            "",
            "| 指标 | 值 |",
            "|------|-----|",
            f"| 总预测记录数 | {total_all} |",
            f"| 已验证数 | {total} |",
            f"| 命中数 | {hits} |",
            f"| 整体命中率 | {hit_rate:.2%} |",
            "",
            "## 按预测周期",
            "",
            "| 周期 | 验证数 | 命中数 | 命中率 |",
            "|------|--------|--------|--------|",
        ]
        for h, stats in sorted(by_horizon.items()):
            hr = stats["hits"] / stats["total"] if stats["total"] > 0 else 0
            lines.append(f"| {h} | {stats['total']} | {stats['hits']} | {hr:.2%} |")

        lines.extend([
            "",
            "## 按标的（Top 10）",
            "",
            "| 标的 | 验证数 | 命中数 | 命中率 |",
            "|------|--------|--------|--------|",
        ])
        top_symbols = sorted(by_symbol.items(), key=lambda x: x[1]["total"], reverse=True)[:10]
        for s, stats in top_symbols:
            hr = stats["hits"] / stats["total"] if stats["total"] > 0 else 0
            lines.append(f"| {s} | {stats['total']} | {stats['hits']} | {hr:.2%} |")

        if len(by_source) > 1:
            lines.extend([
                "",
                "## 按信号来源",
                "",
                "| 来源 | 验证数 | 命中数 | 命中率 |",
                "|------|--------|--------|--------|",
            ])
            for src, stats in by_source.items():
                hr = stats["hits"] / stats["total"] if stats["total"] > 0 else 0
                lines.append(f"| {src} | {stats['total']} | {stats['hits']} | {hr:.2%} |")

        # 模型漂移检测
        recent = [r for r in verified if
                  (now - datetime.fromisoformat(r["timestamp"])).days <= 30]
        recent_hits = sum(1 for r in recent if r.get("hit"))
        recent_rate = recent_hits / len(recent) if recent else 0

        drift_warning = ""
        if recent_rate < hit_rate - 0.1 and len(recent) > 10:
            drift_warning = "⚠ 警告: 近30天命中率显著下降，建议检查模型并考虑重训练"
        else:
            drift_warning = "正常"

        lines.extend([
            "",
            "## 模型漂移检测",
            "",
            "| 指标 | 值 |",
            "|------|-----|",
            f"| 近30天验证数 | {len(recent)} |",
            f"| 近30天命中率 | {recent_rate:.2%} |",
            f"| 整体命中率 | {hit_rate:.2%} |",
            f"| 漂移信号 | {drift_warning} |",
        ])

        report = "\n".join(lines)

        # 保存报告
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"审计报告已保存到 {self.report_file}")
        return report

    # ========== 统计接口 ==========

    def get_stats(self) -> dict[str, Any]:
        """获取审计统计摘要（JSON 格式）"""
        records = self._load_records()
        verified = [r for r in records if r.get("verified")]
        total = len(verified)
        hits = sum(1 for r in verified if r.get("hit"))

        return {
            "total_records": len(records),
            "verified": total,
            "unverified": len(records) - total,
            "hits": hits,
            "misses": total - hits,
            "hit_rate": round(hits / total, 4) if total > 0 else 0,
            "last_updated": datetime.now().isoformat(),
        }


# ==================== 便捷函数 ====================

def run_audit_cycle(audit_dir: str | None = None,
                    price_cache: dict[str, float] | None = None) -> str:
    """运行一次完整的审计周期：验证到期预测 + 生成报告

    Args:
        audit_dir:  审计目录（默认自动检测）
        price_cache: 当前价格缓存 {symbol: price}

    Returns:
        Markdown 格式审计报告
    """
    audit = TrendCastAudit(audit_dir) if audit_dir else TrendCastAudit()
    audit.verify_predictions(price_cache=price_cache)
    return audit.generate_audit_report()


# ==================== 自测 ====================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    audit = TrendCastAudit()
    print(f"审计目录: {audit.audit_dir}")
    print(f"记录文件: {audit.record_file}")
    print(f"报告文件: {audit.report_file}")

    # 模拟记录一条预测
    pred_id = audit.record_prediction(
        symbol="300308.SZ",
        horizon="short_term_5d",
        direction="看涨",
        probability=0.72,
        latest_close=150.0,
    )
    print(f"\n新增记录: {pred_id}")

    # 获取统计
    stats = audit.get_stats()
    print(f"\n审计统计: {json.dumps(stats, ensure_ascii=False, indent=2)}")

    # 验证并生成报告
    report = audit.generate_audit_report()
    print(f"\n{report}")
