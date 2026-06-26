# -*- coding: utf-8 -*-
"""
信号合成桥接器 — 三源模型信号 → 量化策略调仓
===============================================
数据源:
  1. XGBoost 5日方向预测 → xgb_signals_latest.csv
  2. 风险平价权重      → rp_weights_latest.csv
  3. FinBERT 情感评分   → sentiment_signals_latest.csv

合成规则:
  - XGBoost 信号: 涨 + 高置信度 → 权重 +0.10
  - FinBERT 信号: POSITIVE → 权重 +0.05, NEGATIVE → 权重 -0.05
  - 风险平价基准: 取 RP 权重 × 0.5 + 当前权重 × 0.5 (平滑过渡)

输出:
  - model_train/output/composite_signals_latest.csv (可直接被 prediction_bridge 读取)
  - model_train/output/composite_report_YYYYMMDD.json
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
BASE_DIR = Path(__file__).resolve().parent.parent


def load_xgb_signals() -> pd.DataFrame:
    """加载 XGBoost 信号"""
    path = OUTPUT_DIR / "xgb_signals_latest.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"ticker": str})
    # 确保 ticker 为 6 位数字格式
    df["ticker"] = df["ticker"].str.zfill(6)
    return df


def load_rp_weights() -> pd.DataFrame:
    """加载风险平价权重"""
    path = OUTPUT_DIR / "rp_weights_latest.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"ticker": str})
    df["ticker"] = df["ticker"].str.zfill(6)
    return df


def load_sentiment_signals() -> pd.DataFrame:
    """加载情感信号"""
    path = OUTPUT_DIR / "sentiment_signals_latest.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"ticker": str})
    df["ticker"] = df["ticker"].str.zfill(6)
    return df


def load_current_weights() -> Dict[str, float]:
    """从 portfolio.yaml 加载当前权重"""
    try:
        import yaml
        path = BASE_DIR / "config" / "portfolio.yaml"
        with open(path, "r", encoding="utf-8") as f:
            pf = yaml.safe_load(f)

        weights = {}
        for a in pf.get("assets", []):
            code = a.get("code", "")
            if code != "CASH":
                weights[code] = a.get("target_weight", 0)
        # 归一化
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        return weights
    except Exception:
        return {}


def synthesize(
    xgb_weight: float = 0.3,
    sentiment_weight: float = 0.15,
    rp_weight: float = 0.25,
    base_weight: float = 0.30,
) -> pd.DataFrame:
    """
    三源信号合成

    Args:
        xgb_weight: XGBoost 信号权重
        sentiment_weight: 情感信号权重
        rp_weight: 风险平价权重
        base_weight: 基础(当前)权重

    Returns:
        合成后的调仓建议 DataFrame
    """
    current_weights = load_current_weights()
    xgb_df = load_xgb_signals()
    rp_df = load_rp_weights()
    sentiment_df = load_sentiment_signals()

    if not current_weights:
        print("[WARN] 无法加载当前权重")
        return pd.DataFrame()

    all_tickers = sorted(current_weights.keys())
    rows = []

    for ticker in all_tickers:
        base_w = current_weights.get(ticker, 0)
        name = ""

        # XGBoost 调整
        xgb_adj = 0.0
        if not xgb_df.empty:
            xgb_row = xgb_df[xgb_df["ticker"] == ticker]
            if not xgb_row.empty:
                name = xgb_row.iloc[0].get("name", ticker)
                direction = xgb_row.iloc[0].get("direction", "")
                confidence = float(xgb_row.iloc[0].get("confidence", 0))
                if direction == "UP" and confidence > 0.55:
                    xgb_adj = 0.10 * xgb_weight
                elif direction == "DOWN" and confidence > 0.55:
                    xgb_adj = -0.08 * xgb_weight

        # 情感调整
        sent_adj = 0.0
        if not sentiment_df.empty:
            sent_row = sentiment_df[sentiment_df["ticker"] == ticker]
            if not sent_row.empty:
                if not name:
                    name = sent_row.iloc[0].get("name", ticker)
                score = float(sent_row.iloc[0].get("avg_weighted_score", 0))
                sent_adj = np.clip(score * 0.10 * sentiment_weight, -0.08, 0.08)

        # 风险平价锚定
        rp_w = base_w
        if not rp_df.empty:
            rp_row = rp_df[rp_df["ticker"] == ticker]
            if not rp_row.empty:
                rp_w = float(rp_row.iloc[0].get("rp_weight", base_w))

        # 合成 = 当前权重和RP权重的加权平均 + XGBoost/情感调整
        composite = (
            base_w * (base_weight + rp_weight)
            + rp_w * rp_weight
            + xgb_adj
            + sent_adj
        )

        rows.append({
            "ticker": ticker,
            "name": name or ticker,
            "current_weight": round(base_w, 4),
            "rp_weight": round(rp_w, 4),
            "xgb_adjustment": round(xgb_adj, 4),
            "sentiment_adjustment": round(sent_adj, 4),
            "composite_weight_raw": round(composite, 6),
        })

    result = pd.DataFrame(rows)

    # 归一化（确保权重和=1）
    total = result["composite_weight_raw"].sum()
    if total > 0:
        result["composite_weight"] = result["composite_weight_raw"] / total
    else:
        result["composite_weight"] = result["current_weight"]

    result["weight_change"] = (result["composite_weight"] - result["current_weight"]).round(4)
    result["composite_weight"] = result["composite_weight"].round(4)
    result["action"] = result["weight_change"].apply(
        lambda x: "BUY" if x > 0.004 else ("SELL" if x < -0.004 else "HOLD")
    )

    # 清理临时列
    result = result.drop(columns=["composite_weight_raw"])

    return result.sort_values("composite_weight", ascending=False)


def run_synthesis() -> pd.DataFrame:
    """运行合成并保存输出"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'#'*60}")
    print(f"#  三源信号合成器 — {datetime.now():%Y-%m-%d %H:%M}")
    print(f"{'#'*60}")

    df = synthesize()

    if df.empty:
        print("[ERR] 无可用信号，跳过合成")
        return df

    # 保存
    latest_path = OUTPUT_DIR / "composite_signals_latest.csv"
    df.to_csv(latest_path, index=False, encoding="utf-8-sig")
    df.to_csv(OUTPUT_DIR / f"composite_signals_{ts}.csv", index=False, encoding="utf-8-sig")

    # 报告
    buy_count = int((df["action"] == "BUY").sum())
    sell_count = int((df["action"] == "SELL").sum())
    hold_count = int((df["action"] == "HOLD").sum())

    report = {
        "generated_at": datetime.now().isoformat(),
        "total_tickers": len(df),
        "actions": {"buy": buy_count, "sell": sell_count, "hold": hold_count},
        "signals": df.to_dict(orient="records"),
    }
    with open(OUTPUT_DIR / f"composite_report_{ts}.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 打印
    print(f"\n  交易建议: BUY={buy_count}  SELL={sell_count}  HOLD={hold_count}")
    print(f"\n  {'标的':<10} {'名称':<8} {'当前':>8} {'合成':>8} {'变动':>8} {'操作':>6}")
    print(f"  {'-'*50}")
    for _, row in df.iterrows():
        sign = "+" if row["weight_change"] > 0 else ""
        action_icon = {"BUY": "[+]", "SELL": "[-]", "HOLD": "[=]"}.get(row["action"], "[=]")
        print(f"  {action_icon} {row['ticker']:<8} {row['name']:<8} "
              f"{row['current_weight']:>8.4f} {row['composite_weight']:>8.4f} "
              f"{sign}{row['weight_change']:>7.4f} {row['action']:<6}")

    print(f"\n  信号文件: {latest_path}")
    print(f"  报告:     {OUTPUT_DIR / f'composite_report_{ts}.json'}")

    return df


if __name__ == "__main__":
    run_synthesis()
