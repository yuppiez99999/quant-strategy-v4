# -*- coding: utf-8 -*-
"""
每日盘前再平衡流水线 — v1.0
=============================
运行时间: 每日 08:30 (A股盘前 1 小时)
执行顺序:
  步骤1: XGBoost 5日方向预测
  步骤2: 风险平价回测
  步骤3: FinBERT 情感分析
  步骤4: 三源信号合成 -> 调仓信号
  步骤5: 生成盘前 MD 报告

输出: 每日报告归档/YYYY-MM-DD/盘前再平衡报告.md
依赖: model_train/ 下各模块 + portfolio.yaml
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

# ---- 路径 ----
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "model_train" / "output"
REPORT_ARCHIVE = BASE_DIR / "每日报告归档"
sys.path.insert(0, str(BASE_DIR))

# ---- 日志 ----
def _log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


# ============================================================
#  步骤 1: XGBoost 方向预测
# ============================================================
def step1_xgboost() -> bool:
    _log("步骤1/4: XGBoost 5日方向预测...")
    try:
        from model_train.xgboost_direction import run_all
        result = run_all()
        ok = result is not None and len(result.get("details", [])) > 0
        if ok:
            _log(f"  完成: {result.get('trained',0)} 只标的, 看涨={result.get('buy_signals',0)}")
        return ok
    except Exception as e:
        _log(f"[FAIL] XGBoost: {e}")
        traceback.print_exc()
        return False


# ============================================================
#  步骤 2: 风险平价回测
# ============================================================
def step2_risk_parity() -> bool:
    _log("步骤2/4: 风险平价回测...")
    try:
        from model_train.risk_parity_backtest import run_all
        result = run_all()
        ok = bool(result) and OUTPUT_DIR.joinpath("rp_weights_latest.csv").exists()
        return ok
    except Exception as e:
        _log(f"[FAIL] 风险平价: {e}")
        traceback.print_exc()
        return False


# ============================================================
#  步骤 3: FinBERT 情感分析
# ============================================================
def step3_sentiment() -> bool:
    _log("步骤3/4: FinBERT 情感分析...")
    try:
        from model_train.finbert_sentiment import daily_sentiment_run
        daily_sentiment_run()
        return OUTPUT_DIR.joinpath("sentiment_signals_latest.csv").exists()
    except Exception as e:
        _log(f"[FAIL] 情感分析: {e}")
        traceback.print_exc()
        return False


# ============================================================
#  步骤 4: 三源信号合成
# ============================================================
def step4_composer() -> Optional[pd.DataFrame]:
    _log("步骤4/4: 三源信号合成...")
    try:
        from model_train.signal_composer import run_synthesis
        df = run_synthesis()
        return df if (df is not None and not df.empty) else None
    except Exception as e:
        _log(f"[FAIL] 信号合成: {e}")
        traceback.print_exc()
        return None


# ============================================================
#  步骤 5: 生成盘前报告
# ============================================================
def step5_report(composite_df: Optional[pd.DataFrame], results: dict) -> str:
    """生成 Markdown 盘前报告"""
    today = datetime.now()
    report_dir = REPORT_ARCHIVE / today.strftime("%Y-%m-%d")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "盘前再平衡报告.md"

    lines = []
    lines.append(f"# 盘前再平衡报告")
    lines.append(f"")
    lines.append(f"**生成时间**: {today:%Y-%m-%d %H:%M:%S}")
    lines.append(f"**执行模式**: 自动 (每日 08:30)")
    lines.append(f"")

    # ---- 执行摘要 ----
    lines.append(f"## 一、执行摘要")
    lines.append(f"")
    ok_count = sum(1 for v in results.values() if v)
    lines.append(f"四步流水线: {ok_count}/4 成功完成。")
    for step, ok in results.items():
        status = "PASS" if ok else "FAIL"
        lines.append(f"- {step}: {status}")
    lines.append(f"")

    # ---- 模型预测信号 ----
    lines.append(f"## 二、XGBoost 方向预测")
    lines.append(f"")
    xgb_path = OUTPUT_DIR / "xgb_signals_latest.csv"
    if xgb_path.exists():
        try:
            xgb_df = pd.read_csv(xgb_path, dtype={"ticker": str})
            xgb_df["ticker"] = xgb_df["ticker"].str.zfill(6)
            up_count = (xgb_df["direction"] == "UP").sum()
            down_count = (xgb_df["direction"] == "DOWN").sum()
            lines.append(f"训练标的: {len(xgb_df)} 只 | 看涨: {up_count} | 看跌: {down_count}")
            lines.append(f"")
            lines.append(f"| 标的 | 方向 | 置信度 |")
            lines.append(f"|------|------|--------|")
            for _, row in xgb_df.iterrows():
                direction = "看涨" if row["direction"] == "UP" else "看跌"
                lines.append(f"| {row['ticker']} {row.get('name','')} | {direction} | {row['confidence']:.2%} |")
            lines.append(f"")
        except Exception as e:
            lines.append(f"> 读取失败: {e}")
            lines.append(f"")
    else:
        lines.append(f"> 信号文件不存在，该步骤未成功执行。")
        lines.append(f"")

    # ---- 风险平价 ----
    lines.append(f"## 三、风险平价回测")
    lines.append(f"")
    rp_path = OUTPUT_DIR / "rp_weights_latest.csv"
    rp_json_max = max(
        OUTPUT_DIR.glob("rp_summary_*.json"),
        key=lambda p: p.stat().st_mtime,
        default=None,
    )
    if rp_json_max:
        try:
            with open(rp_json_max, "r", encoding="utf-8") as f:
                rp_data = json.load(f)
            lines.append(f"| 策略 | 年化收益 | 年化波动 | 夏普比率 | 最大回撤 |")
            lines.append(f"|------|----------|----------|----------|----------|")
            fixed = rp_data.get("fixed_weight", {})
            erc = rp_data.get("risk_parity", {})
            if fixed:
                lines.append(
                    f"| 固定权重 | {fixed.get('annual_return',0):.2%} | "
                    f"{fixed.get('annual_volatility',0):.2%} | "
                    f"{fixed.get('sharpe',0):.2f} | {fixed.get('max_drawdown',0):.2%} |"
                )
            if erc:
                lines.append(
                    f"| 风险平价 | {erc.get('annual_return',0):.2%} | "
                    f"{erc.get('annual_volatility',0):.2%} | "
                    f"{erc.get('sharpe',0):.2f} | {erc.get('max_drawdown',0):.2%} |"
                )
            lines.append(f"")
        except Exception as e:
            lines.append(f"> 读取失败: {e}")
            lines.append(f"")
    else:
        lines.append(f"> 无回测结果。")
        lines.append(f"")

    # ---- 权重变化 Top5 ----
    if rp_path.exists():
        try:
            rp_df = pd.read_csv(rp_path, dtype={"ticker": str})
            rp_df["ticker"] = rp_df["ticker"].str.zfill(6)
            lines.append(f"### 风险平价权重 Top5")
            lines.append(f"")
            lines.append(f"| 标的 | RP 权重 |")
            lines.append(f"|------|---------|")
            for _, row in rp_df.head(5).iterrows():
                lines.append(f"| {row['ticker']} {row.get('name','')} | {row.get('rp_weight',0):.4f} |")
            lines.append(f"")
        except Exception as e:
            lines.append(f"> 读取失败: {e}")
            lines.append(f"")

    # ---- 情感分析 ----
    lines.append(f"## 四、FinBERT 情感分析")
    lines.append(f"")
    sent_path = OUTPUT_DIR / "sentiment_signals_latest.csv"
    if sent_path.exists():
        try:
            sent_df = pd.read_csv(sent_path, dtype={"ticker": str})
            sent_df["ticker"] = sent_df["ticker"].str.zfill(6)
            pos = (sent_df["sentiment"] == "POSITIVE").sum()
            neg = (sent_df["sentiment"] == "NEGATIVE").sum()
            neu = (sent_df["sentiment"] == "NEUTRAL").sum()
            lines.append(f"分析条目: {sent_df['article_count'].sum() if 'article_count' in sent_df.columns else 'N/A'}")
            lines.append(f"正面: {pos} | 负面: {neg} | 中性: {neu}")
            lines.append(f"")
            if not sent_df.empty:
                lines.append(f"| 标的 | 情感 | 平均得分 |")
                lines.append(f"|------|------|----------|")
                for _, row in sent_df.iterrows():
                    lines.append(
                        f"| {row['ticker']} {row.get('name','')} | "
                        f"{row.get('sentiment','?')} | {row.get('avg_weighted_score',0):+.3f} |"
                    )
                lines.append(f"")
        except Exception as e:
            lines.append(f"> 读取失败: {e}")
            lines.append(f"")
    else:
        lines.append(f"> 信号文件不存在。")
        lines.append(f"")

    # ---- 合成调仓信号 (核心) ----
    lines.append(f"## 五、三源合成调仓信号 (核心)")
    lines.append(f"")
    if composite_df is not None and not composite_df.empty:
        buy_df = composite_df[composite_df["action"] == "BUY"].sort_values("weight_change", ascending=False)
        sell_df = composite_df[composite_df["action"] == "SELL"].sort_values("weight_change")
        hold_df = composite_df[composite_df["action"] == "HOLD"]

        lines.append(f"| 类型 | 数量 |")
        lines.append(f"|------|------|")
        lines.append(f"| BUY (增持) | {len(buy_df)} |")
        lines.append(f"| SELL (减持) | {len(sell_df)} |")
        lines.append(f"| HOLD (持有) | {len(hold_df)} |")
        lines.append(f"")

        if not buy_df.empty:
            lines.append(f"### 买入建议 (权重变动 > 0.4%)")
            lines.append(f"")
            lines.append(f"| 标的 | 名称 | 当前权重 | 目标权重 | 变动 |")
            lines.append(f"|------|------|----------|----------|------|")
            for _, row in buy_df.iterrows():
                sign = "+"
                lines.append(
                    f"| {row['ticker']} | {row.get('name','')} | "
                    f"{row['current_weight']:.4f} | {row['composite_weight']:.4f} | "
                    f"{sign}{row['weight_change']:.4f} |"
                )
            lines.append(f"")

        if not sell_df.empty:
            lines.append(f"### 卖出建议 (权重变动 < -0.4%)")
            lines.append(f"")
            lines.append(f"| 标的 | 名称 | 当前权重 | 目标权重 | 变动 |")
            lines.append(f"|------|------|----------|----------|------|")
            for _, row in sell_df.iterrows():
                lines.append(
                    f"| {row['ticker']} | {row.get('name','')} | "
                    f"{row['current_weight']:.4f} | {row['composite_weight']:.4f} | "
                    f"{row['weight_change']:.4f} |"
                )
            lines.append(f"")

        # 板块汇总
        lines.append(f"### 板块汇总")
        lines.append(f"")
        try:
            import yaml
            pf_path = BASE_DIR / "config" / "portfolio.yaml"
            with open(pf_path, "r", encoding="utf-8") as f:
                pf = yaml.safe_load(f)
            cat_map = {}
            for a in pf.get("assets", []):
                code = a.get("code", "")
                if code != "CASH":
                    cat_map[code] = a.get("category", "unknown")
            cat_buy = {}
            cat_sell = {}
            for _, row in buy_df.iterrows():
                cat = cat_map.get(row["ticker"], "unknown")
                cat_buy[cat] = cat_buy.get(cat, 0) + 1
            for _, row in sell_df.iterrows():
                cat = cat_map.get(row["ticker"], "unknown")
                cat_sell[cat] = cat_sell.get(cat, 0) + 1
            lines.append(f"| 板块 | 买入 | 卖出 | 净方向 |")
            lines.append(f"|------|------|------|--------|")
            all_cats = sorted(set(list(cat_buy.keys()) + list(cat_sell.keys())))
            for cat in all_cats:
                b = cat_buy.get(cat, 0)
                s = cat_sell.get(cat, 0)
                net = "偏多" if b > s else ("偏空" if s > b else "中性")
                lines.append(f"| {cat} | {b} | {s} | {net} |")
            lines.append(f"")
        except Exception:
            pass

    else:
        lines.append(f"> 合成信号不可用，请检查上游步骤是否成功。")
        lines.append(f"")

    # ---- 当日执行建议 ----
    lines.append(f"## 六、当日执行建议")
    lines.append(f"")
    if composite_df is not None and not composite_df.empty:
        buy_count = int((composite_df["action"] == "BUY").sum())
        sell_count = int((composite_df["action"] == "SELL").sum())
        if buy_count > 0:
            buy_list = composite_df[composite_df["action"] == "BUY"]["ticker"].tolist()
            lines.append(f"**买入清单** (共 {buy_count} 只): {', '.join(buy_list)}")
        if sell_count > 0:
            sell_list = composite_df[composite_df["action"] == "SELL"]["ticker"].tolist()
            lines.append(f"**卖出清单** (共 {sell_count} 只): {', '.join(sell_list)}")
        lines.append(f"")
        lines.append(f"> 以上信号由三源模型合成 (XGBoost + 风险平价 + FinBERT)，仅作参考。")
        lines.append(f"> 实际执行前请确认市场流动性及当日重大事件。")
    else:
        lines.append(f"> 无可用信号，建议维持现有仓位不变。")
    lines.append(f"")

    # ---- 附注 ----
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"*本报告由 daily_pre_market.py 自动生成，数据来源: AKShare + 本地模型*")
    lines.append(f"*生成时间: {today:%Y-%m-%d %H:%M:%S}*")

    # 写入
    content = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)

    # 同时复制最新链接
    latest_link = REPORT_ARCHIVE / "最新盘前报告.md"
    try:
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        latest_link.write_text(content, encoding="utf-8")
    except Exception:
        pass

    _log(f"报告已保存: {report_path}")
    return str(report_path)


# ============================================================
#  主入口
# ============================================================
def run_daily_pipeline() -> str:
    """执行完整每日盘前流水线，返回报告路径"""
    start = time.time()
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"\n{'#'*70}")
    print(f"#  每日盘前再平衡流水线 — {today}")
    print(f"#  启动时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"{'#'*70}\n")

    results = {
        "XGBoost 方向预测": False,
        "风险平价回测": False,
        "FinBERT 情感分析": False,
        "三源信号合成": False,
    }

    # 依次执行 (步骤间有依赖，不能完全并行)
    results["XGBoost 方向预测"] = step1_xgboost()
    results["风险平价回测"] = step2_risk_parity()
    results["FinBERT 情感分析"] = step3_sentiment()

    composite_df = None
    if results["XGBoost 方向预测"] or results["风险平价回测"] or results["FinBERT 情感分析"]:
        composite_df = step4_composer()
        results["三源信号合成"] = composite_df is not None
    else:
        _log("[WARN] 前三个步骤全部失败，跳过信号合成")

    # 生成报告
    report_path = step5_report(composite_df, results)

    elapsed = time.time() - start
    ok_count = sum(1 for v in results.values() if v)
    _log(f"流水线完成: {ok_count}/4 步骤成功, 耗时 {elapsed:.0f}s")
    _log(f"报告路径: {report_path}")

    print(f"\n{'#'*70}")
    print(f"#  流水线执行完毕 — {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"{'#'*70}\n")

    return report_path


if __name__ == "__main__":
    run_daily_pipeline()
