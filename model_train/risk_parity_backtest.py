# -*- coding: utf-8 -*-
"""
风险平价模型 vs 现有组合回测对比 — v1.0
=========================================
对比两种配置方案:
  A. 当前社保基金风格固定权重 (portfolio.yaml, 65%权益)
  B. 风险平价动态权重 (等风险贡献)

周期: 最近 5 年
再平衡频率: 月度
评估指标: 年化收益、年化波动、夏普比率、最大回撤、Calmar

输出:
  - model_train/output/rp_backtest_report_YYYYMMDD.json
  - model_train/output/rp_weights_latest.csv
"""

from __future__ import annotations

import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ---- 路径 ----
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = OUTPUT_DIR / "kline_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ---- 加载组合配置 ----
try:
    import yaml
    _pf_path = BASE_DIR / "config" / "portfolio.yaml"
    with open(_pf_path, "r", encoding="utf-8") as f:
        _pf = yaml.safe_load(f)
    ASSETS = [a for a in _pf.get("assets", []) if a.get("code") != "CASH"]
    CAPITAL = _pf.get("global", {}).get("capital", {}).get("total", 1_000_000)
    EQUITY_CAPITAL = _pf.get("global", {}).get("capital", {}).get("equity_portfolio", 650_000)
except Exception:
    ASSETS = []
    CAPITAL = 1_000_000
    EQUITY_CAPITAL = 650_000

# 当前权重（权益部分归一化）
CURRENT_WEIGHTS = {}
_sum = sum(a.get("target_weight", 0) for a in ASSETS)
if _sum > 0:
    for a in ASSETS:
        CURRENT_WEIGHTS[a["code"]] = a.get("target_weight", 0) / _sum

TICKER_NAMES = {a["code"]: a.get("name", a["code"]) for a in ASSETS}
TICKERS = list(CURRENT_WEIGHTS.keys())
RP_LOOKBACK = 60          # 协方差估计窗口
REBALANCE_FREQ = "M"      # 月度再平衡
RISK_FREE_RATE = 0.02     # 无风险利率 2%


# ============================================================
#  数据获取
# ============================================================

def _akshare_code(ticker: str) -> str:
    if ticker.startswith(("51", "15")):
        return f"sh{ticker}" if ticker.startswith("51") else f"sz{ticker}"
    if ticker.startswith("6"):
        return f"sh{ticker}"
    return f"sz{ticker}"


def fetch_returns_matrix(tickers: List[str]) -> pd.DataFrame:
    """获取所有标的日收益率矩阵"""
    returns_all = {}
    for ticker in tickers:
        cache_file = CACHE_DIR / f"{ticker}.parquet"
        df = None
        if cache_file.exists():
            df = pd.read_parquet(cache_file)

        if df is None:
            try:
                import akshare as ak
                symbol = _akshare_code(ticker)
                if ticker.startswith(("51", "15", "58")):
                    df = ak.fund_etf_hist_em(
                        symbol=symbol, period="daily",
                        start_date="20180101",
                        end_date=datetime.now().strftime("%Y%m%d"), adjust="qfq",
                    )
                    df = df.rename(columns={"日期": "date", "收盘": "close"})
                else:
                    df = ak.stock_zh_a_hist(
                        symbol=ticker, period="daily",
                        start_date="20180101",
                        end_date=datetime.now().strftime("%Y%m%d"), adjust="qfq",
                    )
                    df = df.rename(columns={"日期": "date", "收盘": "close"})
                df["date"] = pd.to_datetime(df["date"])
                df["close"] = pd.to_numeric(df["close"], errors="coerce")
                df = df[df["close"] > 0][["date", "close"]]
                df.to_parquet(cache_file, index=False)
            except Exception:
                continue

        if df is not None and not df.empty:
            df = df.set_index("date").sort_index()
            returns_all[ticker] = df["close"].pct_change().dropna()

    if not returns_all:
        return pd.DataFrame()

    ret_df = pd.DataFrame(returns_all)
    return ret_df.dropna(how="all")


# ============================================================
#  风险平价权重计算
# ============================================================

def risk_parity_weights(cov_matrix: np.ndarray, max_iter: int = 1000, tol: float = 1e-8) -> np.ndarray:
    """计算风险平价权重（等风险贡献）"""
    n = cov_matrix.shape[0]
    w = np.ones(n) / n  # 初始等权

    for iteration in range(max_iter):
        sigma_w = cov_matrix @ w
        risk_contrib = w * sigma_w
        marginal_risk = sigma_w
        total_risk = np.sqrt(w @ sigma_w)

        if total_risk < 1e-10:
            break

        # 目标：每个资产风险贡献相等
        target_rc = total_risk / n
        grad = 2 * (risk_contrib - target_rc) / (total_risk + 1e-10)

        # 梯度下降 + 非负约束
        step = 0.1 / (1 + iteration * 0.005)
        w_new = w - step * grad
        w_new = np.maximum(w_new, 1e-6)
        w_new = w_new / w_new.sum()

        if np.max(np.abs(w_new - w)) < tol:
            w = w_new
            break

        w = w_new

    return w


def compute_rp_weights_history(ret_df: pd.DataFrame) -> pd.DataFrame:
    """计算整个回测期的风险平价权重序列"""
    dates = ret_df.index
    n = len(ret_df.columns)
    weights_history = []

    for i in range(RP_LOOKBACK, len(dates)):
        window = ret_df.iloc[i - RP_LOOKBACK : i]
        cov = window.cov().values
        valid_cols = ~np.isnan(cov).all(axis=0)
        if valid_cols.sum() < 2:
            w = np.ones(n) / n
        else:
            valid_idx = np.where(valid_cols)[0]
            cov_sub = cov[np.ix_(valid_idx, valid_idx)]
            w_sub = risk_parity_weights(cov_sub)
            w = np.zeros(n)
            w[valid_idx] = w_sub

        weights_history.append({
            "date": dates[i],
            **{ret_df.columns[j]: w[j] for j in range(n)},
        })

    return pd.DataFrame(weights_history).set_index("date")


# ============================================================
#  回测引擎
# ============================================================

def backtest_portfolio(
    ret_df: pd.DataFrame,
    weights_df: pd.DataFrame,
    capital: float,
    rebalance_freq: str = "M",
) -> pd.DataFrame:
    """回测组合净值曲线"""
    common_dates = ret_df.index.intersection(weights_df.index)
    common_dates = common_dates.sort_values()

    if len(common_dates) < 2:
        return pd.DataFrame()

    rebalance_dates = pd.date_range(
        start=common_dates[0], end=common_dates[-1], freq=rebalance_freq,
    )
    rebalance_dates = common_dates[common_dates.searchsorted(rebalance_dates) - 1]
    rebalance_dates = rebalance_dates[rebalance_dates >= common_dates[0]]
    if len(rebalance_dates) == 0:
        rebalance_dates = [common_dates[0]]

    portfolio_value = capital
    values = []
    current_weights = None

    for i, date in enumerate(common_dates):
        # 再平衡日更新权重
        if date in rebalance_dates or current_weights is None:
            rb_pos = weights_df.index.searchsorted(date)
            rb_pos = min(max(0, rb_pos - 1), len(weights_df.index) - 1)
            closest_rb = weights_df.index[rb_pos]
            w_series = weights_df.loc[closest_rb]
            current_weights = {c: w_series.get(c, 0) for c in ret_df.columns}
            # 归一化
            ws = sum(current_weights.values())
            if ws > 0:
                current_weights = {k: v / ws for k, v in current_weights.items()}

        # 计算日收益率
        day_return = 0
        for ticker, w in current_weights.items():
            if ticker in ret_df.columns:
                r = ret_df.loc[date, ticker]
                if not np.isnan(r):
                    day_return += w * r

        portfolio_value *= (1 + day_return)
        values.append({"date": date, "value": portfolio_value, "daily_return": day_return})

    return pd.DataFrame(values).set_index("date")


# ============================================================
#  绩效指标
# ============================================================

def compute_metrics(nav: pd.DataFrame, capital: float) -> dict:
    """计算绩效指标"""
    if nav.empty:
        return {}

    returns = nav["daily_return"].dropna()
    if len(returns) < 20:
        return {}

    total_days = len(returns)
    years = total_days / 252

    annual_return = (nav["value"].iloc[-1] / capital) ** (1 / years) - 1 if years > 0 else 0
    annual_vol = returns.std() * np.sqrt(252)
    sharpe = (annual_return - RISK_FREE_RATE) / (annual_vol + 1e-9)

    # 最大回撤
    cummax = nav["value"].cummax()
    drawdown = (nav["value"] - cummax) / cummax
    max_dd = drawdown.min()
    calmar = annual_return / (abs(max_dd) + 1e-9)

    return {
        "annual_return": round(float(annual_return), 4),
        "annual_volatility": round(float(annual_vol), 4),
        "sharpe_ratio": round(float(sharpe), 4),
        "max_drawdown": round(float(max_dd), 4),
        "calmar_ratio": round(float(calmar), 4),
        "total_days": total_days,
        "years": round(float(years), 2),
    }


# ============================================================
#  主流程
# ============================================================

def run_all():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\n{'#'*60}")
    print(f"#  风险平价 vs 固定权重 — 回测对比")
    print(f"#  标的数: {len(TICKERS)}  资本: {CAPITAL:,.0f}")
    print(f"{'#'*60}")

    # 1. 获取收益率矩阵
    print("\n[1/4] 获取历史收益率数据 ...")
    ret_df = fetch_returns_matrix(TICKERS)
    if ret_df.empty:
        print("[ERR] 无法获取任何收益率数据")
        return

    valid_tickers = [t for t in TICKERS if t in ret_df.columns]
    ret_df = ret_df[valid_tickers].dropna()
    print(f"  有效标的: {len(valid_tickers)}  日期范围: {ret_df.index[0].date()} ~ {ret_df.index[-1].date()}")

    # 2. 计算风险平价权重序列
    print("\n[2/4] 计算风险平价权重序列 ...")
    rp_weights_df = compute_rp_weights_history(ret_df)
    print(f"  权重序列长度: {len(rp_weights_df)}")

    # 3. 回测两种方案
    print("\n[3/4] 回测 ...")

    # 方案A: 固定权重
    fixed_weights = {}
    for ticker in valid_tickers:
        fixed_weights[ticker] = CURRENT_WEIGHTS.get(ticker, 0)
    ws = sum(fixed_weights.values())
    if ws > 0:
        fixed_weights = {k: v / ws for k, v in fixed_weights.items()}

    dates = ret_df.index
    fixed_weights_values = []
    for date in dates:
        row = {"date": date}
        for ticker in valid_tickers:
            row[ticker] = fixed_weights.get(ticker, 0)
        fixed_weights_values.append(row)
    fixed_weights_df = pd.DataFrame(fixed_weights_values).set_index("date")

    nav_fixed = backtest_portfolio(ret_df, fixed_weights_df, EQUITY_CAPITAL, "M")
    nav_rp = backtest_portfolio(ret_df, rp_weights_df, EQUITY_CAPITAL, "M")

    # 4. 绩效对比
    print("\n[4/4] 绩效对比 ...")
    metrics_fixed = compute_metrics(nav_fixed, EQUITY_CAPITAL)
    metrics_rp = compute_metrics(nav_rp, EQUITY_CAPITAL)

    # 当前最新风险平价权重
    latest_rp = {}
    if not rp_weights_df.empty:
        last_row = rp_weights_df.iloc[-1]
        latest_rp = {t: round(float(last_row.get(t, 0)), 4) for t in valid_tickers}
        latest_rp_sorted = sorted(latest_rp.items(), key=lambda x: x[1], reverse=True)

    # 权重对比
    weight_comparison = []
    for ticker in valid_tickers:
        weight_comparison.append({
            "ticker": ticker,
            "name": TICKER_NAMES.get(ticker, ticker),
            "current_weight": round(fixed_weights.get(ticker, 0), 4),
            "rp_weight": round(latest_rp.get(ticker, 0), 4),
            "diff": round(latest_rp.get(ticker, 0) - fixed_weights.get(ticker, 0), 4),
        })

    # 构建报告
    report = {
        "generated_at": datetime.now().isoformat(),
        "period": f"{ret_df.index[0].date()} ~ {ret_df.index[-1].date()}",
        "tickers": len(valid_tickers),
        "capital": CAPITAL,
        "equity_capital": EQUITY_CAPITAL,
        "comparison": {
            "fixed_weight": metrics_fixed,
            "risk_parity": metrics_rp,
            "sharpe_improvement": round(
                metrics_rp.get("sharpe_ratio", 0) - metrics_fixed.get("sharpe_ratio", 0), 4
            ),
            "drawdown_improvement": round(
                abs(metrics_rp.get("max_drawdown", 0)) - abs(metrics_fixed.get("max_drawdown", 0)), 4
            ),
        },
        "latest_rp_top10": latest_rp_sorted[:10] if latest_rp_sorted else [],
        "weight_comparison": weight_comparison,
    }

    # 保存
    report_path = OUTPUT_DIR / f"rp_backtest_report_{ts}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 保存最新 RP 权重
    weights_df_out = pd.DataFrame([
        {"ticker": t, "name": TICKER_NAMES.get(t, t), "rp_weight": w}
        for t, w in latest_rp.items()
    ])
    weights_df_out.to_csv(
        OUTPUT_DIR / "rp_weights_latest.csv", index=False, encoding="utf-8-sig",
    )

    # 打印结果
    print(f"\n{'='*70}")
    print(f"  {'指标':<20} {'固定权重':>15} {'风险平价':>15} {'改善':>15}")
    print(f"  {'-'*65}")
    for key, label in [
        ("annual_return", "年化收益"),
        ("annual_volatility", "年化波动"),
        ("sharpe_ratio", "夏普比率"),
        ("max_drawdown", "最大回撤"),
        ("calmar_ratio", "Calmar比率"),
    ]:
        fv = metrics_fixed.get(key, 0)
        rv = metrics_rp.get(key, 0)
        diff = rv - fv
        sign = "+" if diff > 0 else ""
        print(f"  {label:<20} {fv:>15.4f} {rv:>15.4f} {sign}{diff:>14.4f}")
    print(f"{'='*70}")

    # 推荐
    sharpe_diff = report["comparison"]["sharpe_improvement"]
    dd_diff = report["comparison"]["drawdown_improvement"]
    if sharpe_diff > 0.05 and dd_diff < 0:
        recommendation = "强烈推荐采用风险平价权重"
    elif sharpe_diff > 0:
        recommendation = "风险平价在夏普比率上表现更优，建议逐步过渡"
    elif sharpe_diff > -0.02:
        recommendation = "两种方案差异不大，维持当前配置即可"
    else:
        recommendation = "当前固定权重方案更优，不建议切换"

    print(f"\n  >>> {recommendation}")
    print(f"\n  报告: {report_path}")
    print(f"  权重: {OUTPUT_DIR / 'rp_weights_latest.csv'}")

    return report


if __name__ == "__main__":
    run_all()
