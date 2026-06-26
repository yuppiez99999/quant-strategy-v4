# -*- coding: utf-8 -*-
"""
FinBERT 中文情感标注 — v1.0
=============================
模型: bert-base-chinese 微调的 FinBERT (ProsusAI/finBERT 同类)
      优先使用本地 model_train/models/finbert-chinese/
      回退到 HuggingFace Hub: adamlin/FinBERT-Chinese

输入: 每日舆情文本 (txt 文件 或 CSV news_text 列)
输出: 每篇文本的 POSITIVE/NEGATIVE/NEUTRAL 情感分数

集成方式:
  - 情感分数写入 model_train/output/sentiment_daily_YYYYMMDD.csv
  - quant_modules/prediction_bridge.py 读取加权到信号合成
  - 每日报告自动引用情感热力图
"""

from __future__ import annotations

import json
import os
import re
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
MODEL_DIR = Path(__file__).resolve().parent / "models" / "finbert-chinese"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ---- 标的名称 → 关键词映射（用于从文本匹配标的） ----
try:
    import yaml
    _pf_path = BASE_DIR / "config" / "portfolio.yaml"
    with open(_pf_path, "r", encoding="utf-8") as f:
        _pf = yaml.safe_load(f)
    TICKER_KEYWORDS = {}
    for a in _pf.get("assets", []):
        code = a.get("code", "")
        name = a.get("name", "")
        if code != "CASH" and name:
            TICKER_KEYWORDS[code] = {
                "name": name,
                "keywords": [
                    name,
                    code,
                    name[:2],
                    name[1:3] if len(name) > 2 else name,
                ],
            }
except Exception:
    TICKER_KEYWORDS = {}

# ---- 标签映射 ----
LABEL_MAP = {0: "NEGATIVE", 1: "NEUTRAL", 2: "POSITIVE"}
SCORE_MAP = {"NEGATIVE": -1.0, "NEUTRAL": 0.0, "POSITIVE": 1.0}


# ============================================================
#  模型加载
# ============================================================

_model = None
_tokenizer = None
_model_load_attempted = False  # 防止重复尝试加载


def load_model():
    """加载 FinBERT 中文模型（带缓存 + 回退）"""
    global _model, _tokenizer, _model_load_attempted

    if _model is not None or _model_load_attempted:
        return _model, _tokenizer

    _model_load_attempted = True

    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch

        # 尝试本地模型
        model_path = str(MODEL_DIR) if (MODEL_DIR.exists() and any(MODEL_DIR.iterdir())) else "adamlin/FinBERT-Chinese"

        print(f"[FinBERT] 加载模型: {model_path} ...")
        _tokenizer = AutoTokenizer.from_pretrained(model_path)
        _model = AutoModelForSequenceClassification.from_pretrained(
            model_path, num_labels=3,
        )
        _model.eval()

        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = _model.to(device)
        print(f"[FinBERT] 设备: {device}")

        return _model, _tokenizer

    except ImportError:
        print("[FinBERT] transformers/torch 未安装，使用关键词回退模式")
        return None, None
    except Exception as e:
        print(f"[FinBERT] 模型加载失败({e})，使用关键词回退模式")
        return None, None


# ============================================================
#  情感分析
# ============================================================

def analyze_single(text: str, max_length: int = 256) -> dict:
    """对单条文本进行情感分析"""
    model, tokenizer = load_model()

    if model is None:
        # 回退: 基于关键词的情感打分
        return _fallback_sentiment(text)

    try:
        import torch

        inputs = tokenizer(
            text, return_tensors="pt", truncation=True,
            max_length=max_length, padding=True,
        )
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1).cpu().numpy()[0]

        label_idx = int(np.argmax(probs))
        sentiment = LABEL_MAP.get(label_idx, "NEUTRAL")

        return {
            "sentiment": sentiment,
            "score": float(probs[label_idx]),
            "positive": float(probs[2]),
            "neutral": float(probs[1]),
            "negative": float(probs[0]),
            "weighted_score": float(
                probs[2] * 1.0 + probs[1] * 0.0 + probs[0] * -1.0
            ),
        }
    except Exception as e:
        print(f"[WARN] 分析失败: {e}")
        return _fallback_sentiment(text)


def _fallback_sentiment(text: str) -> dict:
    """基于关键词的简单情感回退"""
    positive_words = [
        "涨", "突破", "利好", "增长", "买入", "增持", "上行",
        "反弹", "强势", "新高", "超预期", "扩大", "加速",
        "盈利", "分红", "回购", "政策支持", "扶持",
    ]
    negative_words = [
        "跌", "下跌", "利空", "下滑", "卖出", "减持", "下行",
        "回调", "弱势", "新低", "不及预期", "收缩", "放缓",
        "亏损", "风险", "监管", "处罚", "退市",
    ]

    pos_count = sum(1 for w in positive_words if w in text)
    neg_count = sum(1 for w in negative_words if w in text)

    total = pos_count + neg_count
    if total == 0:
        return {
            "sentiment": "NEUTRAL", "score": 0.33,
            "positive": 0.33, "neutral": 0.34, "negative": 0.33,
            "weighted_score": 0.0,
        }

    pos_prob = pos_count / (total * 3) + 0.33
    neg_prob = neg_count / (total * 3) + 0.33
    neu_prob = 1.0 - pos_prob - neg_prob

    if pos_prob > neg_prob and pos_prob > neu_prob:
        sentiment = "POSITIVE"
        score = pos_prob
    elif neg_prob > neu_prob:
        sentiment = "NEGATIVE"
        score = neg_prob
    else:
        sentiment = "NEUTRAL"
        score = neu_prob

    return {
        "sentiment": sentiment,
        "score": round(score, 4),
        "positive": round(pos_prob, 4),
        "neutral": round(neu_prob, 4),
        "negative": round(neg_prob, 4),
        "weighted_score": round(pos_prob - neg_prob, 4),
    }


# ============================================================
#  标的匹配
# ============================================================

def match_ticker(text: str) -> List[str]:
    """从文本中匹配涉及的标的代码"""
    matched = []
    for code, info in TICKER_KEYWORDS.items():
        for kw in info["keywords"]:
            if kw in text and len(kw) >= 2:
                matched.append(code)
                break
    return list(set(matched)) if matched else ["OTHER"]


# ============================================================
#  批量处理
# ============================================================

def batch_analyze(texts: List[str], source: str = "unknown") -> pd.DataFrame:
    """批量情感分析"""
    if not texts:
        return pd.DataFrame()

    results = []
    for i, text in enumerate(texts):
        if not text or len(text.strip()) < 4:
            continue

        result = analyze_single(text.strip())
        tickers = match_ticker(text)

        results.append({
            "id": i,
            "source": source,
            "text": text[:200],  # 截断存储
            "tickers": "|".join(tickers),
            **result,
        })

        if (i + 1) % 50 == 0:
            print(f"  已处理 {i + 1}/{len(texts)} ...")

    return pd.DataFrame(results)


def analyze_from_file(file_path: str) -> pd.DataFrame:
    """从文件读取文本进行批量分析"""
    path = Path(file_path)
    if not path.exists():
        print(f"[ERR] 文件不存在: {file_path}")
        return pd.DataFrame()

    texts = []
    if path.suffix == ".csv":
        df = pd.read_csv(path, encoding="utf-8-sig")
        # 尝试找到文本列
        text_cols = [c for c in df.columns if "text" in c.lower() or "content" in c.lower() or "news" in c.lower()]
        if text_cols:
            texts = df[text_cols[0]].dropna().astype(str).tolist()
        else:
            texts = df.iloc[:, 0].dropna().astype(str).tolist()
    elif path.suffix in (".txt", ".md"):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            # 按段落分割
            texts = [p.strip() for p in re.split(r"\n\s*\n", content) if len(p.strip()) > 10]
    elif path.suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            texts = [str(item) for item in data]
        else:
            texts = [str(v) for v in data.values()]

    if not texts:
        print("[WARN] 未提取到有效文本")
        return pd.DataFrame()

    print(f"[FinBERT] 开始分析 {len(texts)} 条文本 (来源: {path.name})")
    return batch_analyze(texts, source=path.name)


# ============================================================
#  按标的聚合 + 信号输出
# ============================================================

def aggregate_by_ticker(df: pd.DataFrame) -> pd.DataFrame:
    """按标的聚合成情感信号"""
    if df.empty:
        return pd.DataFrame()

    rows = []
    for ticker in TICKER_KEYWORDS:
        # 筛选涉及该标的的行
        mask = df["tickers"].str.contains(ticker, na=False)
        subset = df[mask]

        if subset.empty:
            rows.append({
                "ticker": ticker,
                "name": TICKER_KEYWORDS[ticker]["name"],
                "article_count": 0,
                "avg_weighted_score": 0.0,
                "sentiment": "NEUTRAL",
                "positive_pct": 0.0,
                "negative_pct": 0.0,
            })
            continue

        avg_score = float(subset["weighted_score"].mean())
        pos_pct = float((subset["sentiment"] == "POSITIVE").mean())
        neg_pct = float((subset["sentiment"] == "NEGATIVE").mean())

        if avg_score > 0.1:
            sentiment = "POSITIVE"
        elif avg_score < -0.1:
            sentiment = "NEGATIVE"
        else:
            sentiment = "NEUTRAL"

        rows.append({
            "ticker": ticker,
            "name": TICKER_KEYWORDS[ticker]["name"],
            "article_count": len(subset),
            "avg_weighted_score": round(avg_score, 4),
            "sentiment": sentiment,
            "positive_pct": round(pos_pct, 4),
            "negative_pct": round(neg_pct, 4),
        })

    result = pd.DataFrame(rows)
    return result.sort_values("avg_weighted_score", ascending=False)


# ============================================================
#  每日统一入口
# ============================================================

def daily_sentiment_run(news_dir: str = None, output_signal: bool = True) -> pd.DataFrame:
    """
    每日情感分析统一入口

    Args:
        news_dir: 舆情文本目录，None 则自动搜索 11_量化策略 下的 reports/ 和 每日报告归档/
        output_signal: 是否输出信号文件供 prediction_bridge 读取

    Returns:
        按标的聚合的情感信号 DataFrame
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 自动搜索新闻来源
    all_texts = []
    search_dirs = []

    if news_dir:
        search_dirs.append(Path(news_dir))
    else:
        # 默认搜索路径
        today = datetime.now().strftime("%Y-%m-%d")
        search_dirs = [
            BASE_DIR / "每日报告归档" / today,
            BASE_DIR / "reports",
            BASE_DIR.parent / "02_舆情与竞品监控",
        ]

    for d in search_dirs:
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if f.suffix in (".txt", ".md", ".csv"):
                try:
                    content = f.read_text(encoding="utf-8")
                    # 分句
                    sentences = re.split(r"[。！？\n]+", content)
                    all_texts.extend([s.strip() for s in sentences if len(s.strip()) > 10])
                except Exception:
                    pass

    if not all_texts:
        print("[WARN] 未找到舆情文本，跳过情感分析")
        return pd.DataFrame()

    print(f"[FinBERT] 从 {len(search_dirs)} 个目录提取了 {len(all_texts)} 条文本片段")

    # 批量分析
    df_all = batch_analyze(all_texts, source=f"daily_{ts}")

    if df_all.empty:
        return pd.DataFrame()

    # 保存全量结果
    df_all.to_csv(OUTPUT_DIR / f"sentiment_all_{ts}.csv", index=False, encoding="utf-8-sig")

    # 按标的聚合
    df_ticker = aggregate_by_ticker(df_all)

    if output_signal and not df_ticker.empty:
        # 最新信号（固定文件名）
        df_ticker.to_csv(
            OUTPUT_DIR / "sentiment_signals_latest.csv",
            index=False, encoding="utf-8-sig",
        )

        # 生成 JSON 报告
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_articles": len(df_all),
            "positive_ratio": round(float((df_all["sentiment"] == "POSITIVE").mean()), 4),
            "negative_ratio": round(float((df_all["sentiment"] == "NEGATIVE").mean()), 4),
            "ticker_signals": df_ticker.to_dict(orient="records"),
        }
        with open(OUTPUT_DIR / f"sentiment_report_{ts}.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 链到最新
        df_ticker.to_csv(
            OUTPUT_DIR / "sentiment_signals_latest.csv",
            index=False, encoding="utf-8-sig",
        )

    # 打印摘要
    if not df_ticker.empty:
        print(f"\n[FinBERT] 情感信号摘要:")
        for _, row in df_ticker.iterrows():
            icon = "[+]" if row["sentiment"] == "POSITIVE" else ("[-]" if row["sentiment"] == "NEGATIVE" else "[=]")
            print(f"  {icon} {row['ticker']} {row['name']:<8} "
                  f"score={row['avg_weighted_score']:+.3f}  "
                  f"articles={row['article_count']}")

    return df_ticker


# ============================================================
#  API: 供 prediction_bridge 调用
# ============================================================

def get_latest_signals() -> dict:
    """获取最新情感信号 (供 prediction_bridge.py 读取)"""
    signal_file = OUTPUT_DIR / "sentiment_signals_latest.csv"
    if not signal_file.exists():
        return {}

    df = pd.read_csv(signal_file, encoding="utf-8-sig")
    signals = {}
    for _, row in df.iterrows():
        signals[row["ticker"]] = {
            "sentiment": row["sentiment"],
            "score": float(row["avg_weighted_score"]),
            "weight_adjustment": float(row["avg_weighted_score"]) * 0.1,
        }
    return signals


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FinBERT 中文情感标注")
    parser.add_argument("--file", "-f", type=str, help="指定输入文件")
    parser.add_argument("--news-dir", "-d", type=str, help="舆情文本目录")
    parser.add_argument("--text", "-t", type=str, help="直接分析一段文本")
    args = parser.parse_args()

    if args.text:
        result = analyze_single(args.text)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.file:
        df = analyze_from_file(args.file)
        if not df.empty:
            print(df[["sentiment", "weighted_score", "tickers"]].head(20))
    else:
        daily_sentiment_run(news_dir=args.news_dir)
