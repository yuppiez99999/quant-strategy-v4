# -*- coding: utf-8 -*-
"""
XGBoost 5日涨跌方向预测器 — v1.0
=================================
数据源: AKShare (免费, 5年+日线)
模型:   XGBoost 二分类 (涨/跌)
目标:   T+5 收盘价方向 → 增强信号层

输出:
  - model_train/output/xgb_model_YYYYMMDD.json       (模型)
  - model_train/output/xgb_signals_YYYYMMDD.csv       (当日信号)
  - model_train/output/xgb_feature_importance.png     (特征重要性)

集成方式: 信号文件被 prediction_bridge.py 读取，权重调整 ±0.15×置信度
"""

from __future__ import annotations

import json
import os
import sys
import time
import warnings
from datetime import datetime, timedelta
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

# ---- 持仓标的 ----
# 读 portfolio.yaml 获取标的列表
try:
    import yaml
    _pf_path = BASE_DIR / "config" / "portfolio.yaml"
    with open(_pf_path, "r", encoding="utf-8") as f:
        _pf = yaml.safe_load(f)
    TICKERS = [
        a["code"] for a in _pf.get("assets", [])
        if a.get("code") != "CASH"
    ]
    TICKER_NAMES = {
        a["code"]: a.get("name", a["code"]) for a in _pf.get("assets", [])
        if a.get("code") != "CASH"
    }
except Exception:
    # 硬编码兜底
    TICKERS = [
        "510300", "510500", "512100", "588000", "159915",
        "688041", "300308", "300274", "600900", "600519",
        "601088", "600036", "601318", "518880", "600989",
        "600276", "002371", "600995", "600875", "600406",
        "000425", "600089", "688017",
    ]
    TICKER_NAMES = {t: t for t in TICKERS}

FORWARD_DAYS = 5        # 预测未来 N 天方向
MIN_TRAIN_YEARS = 5     # 最少训练数据年数
LOOKBACK_WINDOW = 60    # 特征窗口


# ============================================================
#  数据下载 (AKShare)
# ============================================================

def _clean_code(ticker: str) -> str:
    """去掉 .SZ/.SH 后缀，返回纯6位数字代码"""
    return ticker.split(".")[0].strip()


def _akshare_code(ticker: str) -> str:
    """将代码转为 AKShare symbol（纯数字）"""
    return _clean_code(ticker)


def _is_etf(ticker: str) -> bool:
    """判断是否为ETF"""
    code = _clean_code(ticker)
    return code.startswith(("51", "15", "56", "58", "16", "159"))


def fetch_kline_akshare(ticker: str, use_cache: bool = True) -> pd.DataFrame:
    """通过 AKShare 拉取一只标的的历史日线，并缓存"""
    cache_file = CACHE_DIR / f"{ticker}.parquet"
    if use_cache and cache_file.exists():
        df = pd.read_parquet(cache_file)
        if len(df) > 200:
            return df

    try:
        import akshare as ak

        symbol = _akshare_code(ticker)
        if _is_etf(ticker):
            # ETF
            df = ak.fund_etf_hist_em(
                symbol=symbol,
                period="daily",
                start_date="20180101",
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="qfq",
            )
            df = df.rename(columns={
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume",
            })
        else:
            # 股票
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date="20180101",
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="qfq",
            )
            df = df.rename(columns={
                "日期": "date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "volume",
            })

        # 统一处理
        df["date"] = pd.to_datetime(df["date"])
        df = df[["date", "open", "close", "high", "low", "volume"]]
        for c in ["open", "close", "high", "low", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["close"])
        df = df[df["close"] > 0]
        df = df.sort_values("date").reset_index(drop=True)

        # 缓存
        df.to_parquet(cache_file, index=False)
        return df
    except Exception as e:
        print(f"  [WARN] AKShare {ticker} 拉取失败: {e}")
        # 回退：读缓存
        if cache_file.exists():
            return pd.read_parquet(cache_file)
        return pd.DataFrame()


# ============================================================
#  特征工程
# ============================================================

def engineer_features(df: pd.DataFrame, ticker: str = "") -> pd.DataFrame:
    """从 OHLCV 计算特征集"""
    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)

    # 收益率
    for d in [1, 3, 5, 10, 20]:
        df[f"ret_{d}d"] = df["close"].pct_change(d)

    # 波动率
    for d in [5, 10, 20]:
        df[f"vol_{d}d"] = df["close"].pct_change().rolling(d).std()

    # 量比
    df["vol_ma5"] = df["volume"].rolling(5).mean()
    df["vol_ma20"] = df["volume"].rolling(20).mean()
    df["vol_ratio_5"] = df["volume"] / (df["vol_ma5"] + 1e-9)
    df["vol_ratio_20"] = df["volume"] / (df["vol_ma20"] + 1e-9)

    # RSI
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    for d in [6, 14]:
        avg_gain = gain.rolling(d).mean()
        avg_loss = loss.rolling(d).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        df[f"rsi_{d}"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # 均线偏离
    for d in [5, 10, 20, 60]:
        ma = df["close"].rolling(d).mean()
        df[f"ma_dev_{d}d"] = (df["close"] - ma) / (ma + 1e-9)

    # 价格位置
    df["high_20d"] = df["high"].rolling(20).max()
    df["low_20d"] = df["low"].rolling(20).min()
    df["price_position"] = (df["close"] - df["low_20d"]) / (
        df["high_20d"] - df["low_20d"] + 1e-9
    )

    # 目标标签：T+N 日涨跌
    df["future_close"] = df["close"].shift(-FORWARD_DAYS)
    df["future_ret"] = df["close"].pct_change(FORWARD_DAYS).shift(-FORWARD_DAYS)
    df["label"] = (df["future_ret"] > 0).astype(int)

    return df.dropna()


# ============================================================
#  模型训练
# ============================================================

def train_single_ticker(ticker: str) -> Optional[Dict]:
    """为单只标的训练 XGBoost 模型，返回性能指标"""
    print(f"\n{'='*50}")
    print(f"  [{ticker}] {TICKER_NAMES.get(ticker, '')}")
    print(f"{'='*50}")

    df_raw = fetch_kline_akshare(ticker)
    if df_raw.empty or len(df_raw) < 500:
        print(f"  [SKIP] {ticker} 数据不足 ({len(df_raw)} 条)")
        return None

    df = engineer_features(df_raw, ticker)
    if df.empty:
        print(f"  [SKIP] {ticker} 特征不足")
        return None

    # 特征列（排除标签/日期/目标）
    exclude = ["date", "future_close", "future_ret", "label",
               "vol_ma5", "vol_ma20", "high_20d", "low_20d"]
    feature_cols = [c for c in df.columns if c not in exclude]

    # 时间序列切分：最近 20% 作为测试集
    n = len(df)
    split = int(n * 0.8)
    train = df.iloc[:split]
    test = df.iloc[split:]

    X_train = train[feature_cols].values
    y_train = train["label"].values
    X_test = test[feature_cols].values
    y_test = test["label"].values

    if len(X_train) < 100 or len(X_test) < 20:
        print(f"  [SKIP] {ticker} 样本不足")
        return None

    # 标签平衡检查
    pos_ratio = y_train.mean()
    scale_pos_weight = (1 - pos_ratio) / (pos_ratio + 1e-6) if 0 < pos_ratio < 1 else 1

    try:
        import xgboost as xgb

        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)

        # 评估
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
        )

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        metrics = {
            "ticker": ticker,
            "name": TICKER_NAMES.get(ticker, ticker),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
            "auc": round(float(roc_auc_score(y_test, y_proba)), 4),
            "label_ratio": round(float(pos_ratio), 4),
        }

        # 特征重要性 Top10
        importance = sorted(
            zip(feature_cols, model.feature_importances_),
            key=lambda x: x[1], reverse=True,
        )[:10]
        metrics["top_features"] = [
            {"feature": f, "importance": round(v, 4)} for f, v in importance
        ]

        # 保存模型
        model_path = OUTPUT_DIR / f"xgb_{ticker}_{datetime.now():%Y%m%d}.json"
        model.save_model(str(model_path))

        # 对最新一天生成预测信号
        latest_features = df[feature_cols].iloc[-1:].values
        latest_proba = model.predict_proba(latest_features)[0]
        signal = {
            "ticker": ticker,
            "name": TICKER_NAMES.get(ticker, ticker),
            "direction": "UP" if latest_proba[1] > 0.5 else "DOWN",
            "confidence": round(float(max(latest_proba)), 4),
            "prob_up": round(float(latest_proba[1]), 4),
            "prob_down": round(float(latest_proba[0]), 4),
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
        metrics["signal"] = signal

        status = "OK" if metrics["auc"] > 0.55 else "--"
        print(f"  {status} AUC={metrics['auc']:.4f}  Acc={metrics['accuracy']:.4f}  "
              f"F1={metrics['f1']:.4f}  信号={signal['direction']}({signal['confidence']:.2f})")

        return metrics

    except ImportError:
        print("  [ERR] xgboost/scikit-learn 未安装，请 pip install xgboost scikit-learn")
        return None
    except Exception as e:
        print(f"  [ERR] {ticker} 训练失败: {e}")
        return None


# ============================================================
#  批量训练 + 信号汇总
# ============================================================

def run_all():
    """批量训练所有标的，输出汇总信号文件"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"\n{'#'*60}")
    print(f"#  XGBoost 5日方向预测 — {datetime.now():%Y-%m-%d %H:%M}")
    print(f"#  标的数: {len(TICKERS)}")
    print(f"{'#'*60}")

    results = []
    signals = []
    for i, ticker in enumerate(TICKERS, 1):
        print(f"\n[{i}/{len(TICKERS)}] 处理 {ticker} ...")
        r = train_single_ticker(ticker)
        if r:
            results.append(r)
            signals.append(r["signal"])

    if not results:
        print("\n[ERR] 无任何标的训练成功")
        return

    # 汇总指标
    avg_auc = np.mean([r["auc"] for r in results])
    avg_acc = np.mean([r["accuracy"] for r in results])
    good_count = sum(1 for r in results if r["auc"] > 0.55)
    up_count = sum(1 for s in signals if s["direction"] == "UP")

    summary = {
        "generated_at": datetime.now().isoformat(),
        "forward_days": FORWARD_DAYS,
        "total_tickers": len(TICKERS),
        "trained": len(results),
        "avg_auc": round(float(avg_auc), 4),
        "avg_accuracy": round(float(avg_acc), 4),
        "good_models": good_count,
        "buy_signals": up_count,
        "sell_signals": len(signals) - up_count,
        "details": results,
    }

    # 保存汇总报告
    report_path = OUTPUT_DIR / f"xgb_summary_{ts}.json"
    # 递归转换 numpy 类型为 Python 原生类型
    def _convert(o):
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return float(o)
        if isinstance(o, np.ndarray): return o.tolist()
        if isinstance(o, dict): return {k: _convert(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)): return [_convert(v) for v in o]
        return o
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(_convert(summary), f, ensure_ascii=False, indent=2)

    # 保存信号 CSV（供 prediction_bridge 读取）
    signal_path = OUTPUT_DIR / f"xgb_signals_{ts}.csv"
    pd.DataFrame(signals).to_csv(signal_path, index=False, encoding="utf-8-sig")

    # 最新信号链接（固定文件名，方便读取）
    latest_signal = OUTPUT_DIR / "xgb_signals_latest.csv"
    pd.DataFrame(signals).to_csv(latest_signal, index=False, encoding="utf-8-sig")

    print(f"\n{'='*60}")
    print(f"  训练完成: {len(results)}/{len(TICKERS)} 只标的")
    print(f"  平均 AUC: {avg_auc:.4f}")
    print(f"  优质模型 (AUC>0.55): {good_count}")
    print(f"  看涨信号: {up_count}  看跌信号: {len(signals)-up_count}")
    print(f"  报告: {report_path}")
    print(f"  信号: {signal_path}")
    print(f"{'='*60}")

    return summary


if __name__ == "__main__":
    run_all()
