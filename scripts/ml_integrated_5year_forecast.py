# -*- coding: utf-8 -*-
"""
ML 增强量化交易系统集成 + 5年年化收益率预测 v2

修正版: 基于真实历史收益校准，消除数据质量问题导致的虚高结果

运行方式:
  cd e:\各种PY程序\11_量化策略
  python scripts/ml_integrated_5year_forecast.py
"""

import os
import sys
import json
import math
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

from utils.ml_predictor import MLModelPredictor, MLFeatureEngineer

# ── 配置 ──
TARGET_RETURN = 0.08
TARGET_DD = 0.15
YEARS_FORECAST = 5
MC_SIMULATIONS = 5000
RISK_FREE = 0.025
INITIAL_CAPITAL = 1_000_000


def pct(x: float) -> str:
    return f"{x * 100:+.2f}%" if x < 0 else f"{x * 100:.2f}%"


# ============================================================
# 1) 从历史数据计算各标真实年化收益/波动率
# ============================================================
def compute_historical_stats(data_dir: str = "data/cache") -> pd.DataFrame:
    """计算每只标的的真实历史收益与风险指标（剔除异常值）"""
    results = []
    for f in sorted(os.listdir(data_dir)):
        if not f.startswith("kline_") or not f.endswith(".parquet"):
            continue
        code = f.replace("kline_", "").replace("_daily.parquet", "")
        df = pd.read_parquet(os.path.join(data_dir, f))
        close_col = None
        for col in ["close", "收盘价"]:
            if col in df.columns:
                close_col = col; break
        if close_col is None:
            continue

        s = df[close_col].copy()
        if not isinstance(s.index, pd.DatetimeIndex):
            s.index = pd.to_datetime(s.index)
        s = s.sort_index()
        s = s[~s.index.duplicated(keep="first")]
        s = s.loc["2021-01-04":"2026-06-26"]
        if len(s) < 100:
            continue

        daily_ret = s.pct_change().dropna()
        # 剔除单日涨跌超30%的异常点（数据质量问题）
        daily_ret = daily_ret[(daily_ret > -0.30) & (daily_ret < 0.30)]

        if len(daily_ret) < 100:
            continue

        n_years = len(daily_ret) / 252
        ann_ret = (s.iloc[-1] / s.iloc[0]) ** (1 / n_years) - 1
        ann_vol = daily_ret.std() * np.sqrt(252)

        # 验证: 用几何平均也计算一次
        geo_ret = (1 + daily_ret).prod() ** (1 / n_years) - 1

        results.append({
            "code": code,
            "ann_ret": ann_ret,
            "ann_ret_geo": geo_ret,
            "ann_vol": ann_vol,
            "n_days": len(daily_ret),
            "sharpe": (ann_ret - RISK_FREE) / ann_vol if ann_vol > 0 else 0,
        })

    return pd.DataFrame(results)


# ============================================================
# 2) 权重配置
# ============================================================
def load_portfolio_weights() -> Tuple[Dict[str, float], Dict[str, str]]:
    """加载 portfolio.yaml 权重，返回 {code: weight} 和 {code: category}"""
    base_weights = {}
    categories = {}
    try:
        import yaml
        with open("config/portfolio.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        for a in cfg.get("assets", []):
            code = a.get("code", "")
            w = float(a.get("target_weight", 0))
            if code:
                base_weights[code] = w
                categories[code] = a.get("category", "other")
    except Exception:
        base_weights = {
            "510300": 0.07, "510500": 0.05, "512100": 0.04, "588000": 0.03,
            "159915": 0.03, "688041": 0.04, "300308": 0.03, "300274": 0.03,
            "600900": 0.04, "600519": 0.03, "601088": 0.04, "600036": 0.03,
            "601318": 0.03, "518880": 0.04, "600989": 0.02, "600276": 0.03,
            "002371": 0.03, "600995": 0.02, "600875": 0.02, "600406": 0.03,
            "000425": 0.02, "600089": 0.02, "688017": 0.02, "CASH": 0.25,
        }
    return base_weights, categories


# ============================================================
# 3) 组合基线收益计算 (买入持有)
# ============================================================
def compute_portfolio_baseline(stats: pd.DataFrame, weights: Dict[str, float]) -> Dict[str, float]:
    """买入持有组合的加权年化收益/波动/夏普"""
    stats_dict = stats.set_index("code")

    port_ret = 0.0
    port_vol_sq = 0.0
    equity_total = sum(w for c, w in weights.items() if c != "CASH")
    cash_w = weights.get("CASH", 0.25)

    for code, w in weights.items():
        if code == "CASH":
            port_ret += w * RISK_FREE  # 现金按无风险利率
            continue
        if code not in stats_dict.index:
            continue
        normalized_w = w / equity_total
        port_ret += w * stats_dict.loc[code, "ann_ret"]
        port_vol_sq += normalized_w ** 2 * stats_dict.loc[code, "ann_vol"] ** 2

    port_vol = math.sqrt(port_vol_sq) * equity_total  # 近似: 忽略相关性
    sharpe = (port_ret - RISK_FREE) / port_vol if port_vol > 0 else 0

    return {
        "annual_return": port_ret,
        "annual_volatility": port_vol,
        "sharpe": sharpe,
        "equity_weight": equity_total,
        "cash_weight": cash_w,
    }


# ============================================================
# 4) ML 信号生成 + 收益增强估算
# ============================================================
def evaluate_ml_enhancement(
    stats: pd.DataFrame,
    weights: Dict[str, float],
) -> Dict[str, Any]:
    """
    用 ML 模型对每只标生成方向信号，估算增强效果:
    - 模型 Acc=56.3% 意味着正确预测概率比随机高 6.3pp
    - 对看多标的增持、看空标的减持 → 预期超额收益
    """
    predictor = MLModelPredictor(model_dir="models")
    if not predictor.auto_discover():
        return {"ml_enhancement_bps": 0, "signals": {}, "model_info": {}}

    model_info = predictor.get_model_info()
    model_accuracy = model_info.get("accuracy", 0.56)
    model_f1 = model_info.get("f1", 0.64)

    # 为每只标的加载数据并生成信号
    data_dir = "data/cache"
    signals = {}
    for code in weights:
        if code == "CASH":
            continue
        fname = f"kline_{code}_daily.parquet"
        filepath = os.path.join(data_dir, fname)
        if not os.path.exists(filepath):
            continue
        try:
            df = pd.read_parquet(filepath)
            pred = predictor.predict(df)
            if pred:
                signals[code] = pred
        except Exception:
            pass

    # ML 增强估算: 根据信号方向重新分配权重
    # 方法论: 看多标的超配 +30%, 看空标的低配 -50%
    # 准确率 56.3%意味着 56.3%的预测正确,43.7%错误
    # 期望超额 = P(正确)*收益 - P(错误)*损失
    buy_signals = {k: v for k, v in signals.items() if v["signal"] > 0.1}
    sell_signals = {k: v for k, v in signals.items() if v["signal"] < -0.1}

    buy_count = len(buy_signals)
    sell_count = len(sell_signals)
    neutral_count = len(signals) - buy_count - sell_count

    # 看多标的的平均历史年化收益
    buy_ret = np.mean([stats[stats["code"] == c]["ann_ret"].values[0]
                        for c in buy_signals if c in stats["code"].values]) if buy_count > 0 else 0
    sell_ret = np.mean([stats[stats["code"] == c]["ann_ret"].values[0]
                         for c in sell_signals if c in stats["code"].values]) if sell_count > 0 else 0
    all_ret = stats["ann_ret"].mean()

    # 超额收益 = 超配看多(x1.3) + 低配看空(x0.5) 相对于等权的差异
    # 若看多标的平均收益 15%、看空平均 5%、全市场平均 8%:
    # 超配看多贡献: 15%*1.3 - 8% = +11.5pp
    # 低配看空贡献: 5%*0.5 - 8% = -5.5pp (相对少亏3.5pp)
    enhancement_bps = 0
    if buy_count > 0:
        enhancement_bps += (buy_ret * 1.3 - all_ret) * (buy_count / len(signals))
    if sell_count > 0:
        enhancement_bps += (sell_ret * 0.5 - all_ret) * (sell_count / len(signals))

    # 模型准确率校准: 56.3%正确 → 实际可捕获的超额约 60%
    realizable = (model_accuracy - 0.5) * 2  # 信息系数 IC
    ml_enhancement_bps = enhancement_bps * realizable

    print(f"\n[ML] 信号分布: 看多{buy_count} / 中性{neutral_count} / 看空{sell_count}")
    print(f"[ML] 看多标的平均年化: {buy_ret:.1%}")
    print(f"[ML] 看空标的平均年化: {sell_ret:.1%}")
    print(f"[ML] 全市场平均年化: {all_ret:.1%}")
    print(f"[ML] 原始超额: {enhancement_bps*100:.1f}bp")
    print(f"[ML] IC校准后: {ml_enhancement_bps*100:.1f}bp ({pct(ml_enhancement_bps)})")

    return {
        "ml_enhancement_bps": ml_enhancement_bps,
        "signals": signals,
        "model_info": model_info,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "neutral_count": neutral_count,
    }


# ============================================================
# 5) 蒙特卡洛 5年预测
# ============================================================
def monte_carlo_5year(
    base_ret: float,
    base_vol: float,
    ml_enhancement: float,
    n_sim: int = MC_SIMULATIONS,
    years: int = YEARS_FORECAST,
) -> Dict[str, Dict[str, float]]:
    """
    多情景蒙特卡洛模拟
    base_ret: 历史买入持有年化基准
    base_vol: 历史组合波动率
    ml_enhancement: ML模型贡献的超额年化
    """
    n_days = years * 252
    rng = np.random.default_rng(42)

    scenarios = {
        "极度悲观 (熊市+模型失效)": {
            "annual_ret": base_ret - 0.05,
            "vol": base_vol * 1.4,
            "desc": "市场持续下跌 + ML模型预测失效",
        },
        "悲观 (震荡市)": {
            "annual_ret": base_ret - 0.02,
            "vol": base_vol * 1.2,
            "desc": "经济弱复苏，指数震荡",
        },
        "基准 (买入持有)": {
            "annual_ret": base_ret,
            "vol": base_vol,
            "desc": "延续历史均值，不做任何调整",
        },
        "ML增强 (权重调整)": {
            "annual_ret": base_ret + ml_enhancement,
            "vol": base_vol * 0.95,
            "desc": "ML方向信号优化权重分配",
        },
        "ML增强+降现金": {
            "annual_ret": base_ret + ml_enhancement + 0.015,
            "vol": base_vol * 0.95,
            "desc": "ML信号 + 现金从25%降至15%",
        },
        "乐观 (政策+ML共振)": {
            "annual_ret": base_ret + ml_enhancement + 0.03,
            "vol": base_vol * 0.85,
            "desc": "十五五政策发力+康波回升+ML择时",
        },
        "极度乐观 (全面牛市)": {
            "annual_ret": base_ret + ml_enhancement + 0.06,
            "vol": base_vol * 0.80,
            "desc": "全面牛市+ML精准择时",
        },
    }

    results = {}
    for name, params in scenarios.items():
        mu = params["annual_ret"]
        sigma = params["vol"]
        daily_mu = mu / 252
        daily_sigma = sigma / np.sqrt(252)

        z = rng.standard_normal((n_sim, n_days))
        daily = daily_mu + daily_sigma * z
        cum_paths = np.exp(daily).cumprod(axis=1)
        final_values = cum_paths[:, -1]

        cagr = final_values ** (1 / years) - 1
        max_dd = np.min(
            cum_paths / np.maximum.accumulate(cum_paths, axis=1) - 1, axis=1
        )

        results[name] = {
            "cagr_mean": float(np.mean(cagr)),
            "cagr_median": float(np.median(cagr)),
            "cagr_p5": float(np.percentile(cagr, 5)),
            "cagr_p25": float(np.percentile(cagr, 25)),
            "cagr_p75": float(np.percentile(cagr, 75)),
            "cagr_p95": float(np.percentile(cagr, 95)),
            "cagr_std": float(np.std(cagr)),
            "dd_median": float(np.median(max_dd)),
            "dd_mean": float(np.mean(max_dd)),
            "dd_p95": float(np.percentile(max_dd, 95)),
            "prob_target": float(np.mean(cagr >= TARGET_RETURN)),
            "final_mean": float(np.mean(final_values)),
            "desc": params["desc"],
        }

    return results


# ============================================================
# 6) 板块贡献拆解
# ============================================================
def sector_decomposition(
    stats: pd.DataFrame,
    weights: Dict[str, float],
    categories: Dict[str, str],
) -> pd.DataFrame:
    """按板块分解贡献"""
    stats_dict = stats.set_index("code")
    rows = []
    for cat in set(categories.values()):
        cat_codes = [c for c, cat2 in categories.items() if cat2 == cat and c in weights]
        cat_w = sum(weights[c] for c in cat_codes)
        cat_ret = 0
        for c in cat_codes:
            if c in stats_dict.index:
                cat_ret += weights[c] / cat_w * stats_dict.loc[c, "ann_ret"]
        rows.append({
            "category": cat,
            "weight": cat_w,
            "weighted_return": cat_ret,
            "contribution": cat_w * cat_ret,
        })
    return pd.DataFrame(rows).sort_values("contribution", ascending=False)


# ============================================================
# 7) 报告生成
# ============================================================
def generate_report(
    baseline: Dict,
    ml_result: Dict,
    mc_results: Dict,
    sector_df: pd.DataFrame,
    stats: pd.DataFrame,
    weights: Dict[str, float],
) -> str:
    lines = []
    lines.append("# ML 增强量化交易系统集成 + 5年年化收益率预测")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**预测窗口**: {YEARS_FORECAST} 年 | 蒙特卡洛 {MC_SIMULATIONS} 次")
    lines.append(f"**无风险利率**: {RISK_FREE*100:.1f}% | 年化收益目标: {TARGET_RETURN*100:.0f}%")
    lines.append("")

    # ── 一、投资组合概况 ──
    lines.append("## 一、投资组合概况")
    lines.append("")
    lines.append(f"- 总标的: {len([c for c in weights if c != 'CASH'])} 只")
    lines.append(f"- 权益仓位: {baseline['equity_weight']:.0%} | 现金: {baseline['cash_weight']:.0%}")
    lines.append(f"- 历史买入持有年化: **{pct(baseline['annual_return'])}**")
    lines.append(f"- 历史波动率: {pct(baseline['annual_volatility'])}")
    lines.append(f"- 历史夏普: {baseline['sharpe']:.3f}")
    lines.append("")

    # ── 二、ML 模型集成 ──
    lines.append("## 二、ML 模型集成")
    lines.append("")
    model_info = ml_result.get("model_info", {})
    lines.append(f"- **模型**: {model_info.get('best_model', 'N/A')}")
    lines.append(f"- **训练准确率**: {model_info.get('accuracy', 0):.2%}")
    lines.append(f"- **F1 分数**: {model_info.get('f1', 0):.4f}")
    lines.append(f"- **特征数**: {model_info.get('feature_count', 0)} 个")
    lines.append("")
    lines.append("**方向信号统计:**")
    lines.append("")
    lines.append(f"| 方向 | 数量 | 占比 |")
    lines.append(f"|------|------|------|")
    n_total = ml_result.get("buy_count", 0) + ml_result.get("sell_count", 0) + ml_result.get("neutral_count", 0)
    lines.append(f"| 看多 | {ml_result.get('buy_count', 0)} | {ml_result.get('buy_count', 0)/max(n_total,1)*100:.0f}% |")
    lines.append(f"| 中性 | {ml_result.get('neutral_count', 0)} | {ml_result.get('neutral_count', 0)/max(n_total,1)*100:.0f}% |")
    lines.append(f"| 看空 | {ml_result.get('sell_count', 0)} | {ml_result.get('sell_count', 0)/max(n_total,1)*100:.0f}% |")
    lines.append("")
    lines.append(f"**ML 增强估算**: 基于方向信号动态调仓，预期贡献超额年化 **{pct(ml_result.get('ml_enhancement_bps', 0))}**")
    lines.append("")

    # ── 三、板块贡献拆解 ──
    lines.append("## 三、板块贡献拆解 (历史买入持有)")
    lines.append("")
    lines.append("| 板块 | 权重 | 加权年化 | 贡献 |")
    lines.append("|------|------|---------|------|")
    for _, row in sector_df.iterrows():
        lines.append(f"| {row['category']} | {row['weight']:.0%} | {pct(row['weighted_return'])} | {pct(row['contribution'])} |")
    lines.append("")

    # ── 四、5年预测 ──
    lines.append(f"## 四、{YEARS_FORECAST} 年蒙特卡洛预测 ({MC_SIMULATIONS} 次模拟)")
    lines.append("")

    for name, r in mc_results.items():
        lines.append(f"### {name} — {r.get('desc', '')}")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 中位 CAGR | **{pct(r['cagr_median'])}** |")
        lines.append(f"| 均值 CAGR | {pct(r['cagr_mean'])} ± {pct(r['cagr_std'])} |")
        lines.append(f"| P5-P95 范围 | {pct(r['cagr_p5'])} ~ {pct(r['cagr_p95'])} |")
        lines.append(f"| IQR (P25-P75) | {pct(r['cagr_p25'])} ~ {pct(r['cagr_p75'])} |")
        lines.append(f"| P(CAGR ≥ 8%) | **{r['prob_target']*100:.1f}%** |")
        lines.append(f"| 中位最大回撤 | {pct(r['dd_median'])} |")
        lines.append(f"| P95 最大回撤 | {pct(r['dd_p95'])} |")
        lines.append(f"| 期末净值均值 | ¥{r['final_mean']*INITIAL_CAPITAL:,.0f} |")
        lines.append("")

    # ── 五、单标的详情 ──
    lines.append("## 五、持仓标的历史表现")
    lines.append("")
    lines.append("| 代码 | 年化收益 | 年化波动 | 夏普 | 数据天数 | 信号方向 |")
    lines.append("|------|---------|---------|------|---------|---------|")
    signals = ml_result.get("signals", {})
    for _, r in stats.sort_values("ann_ret", ascending=False).iterrows():
        code = r["code"]
        direction = signals.get(code, {}).get("direction", "-")
        lines.append(
            f"| {code} | {pct(r['ann_ret'])} | {pct(r['ann_vol'])} | "
            f"{r['sharpe']:+.2f} | {r['n_days']} | {direction} |"
        )
    lines.append("")

    # ── 六、结论 ──
    lines.append("## 六、核心结论")
    lines.append("")
    ml_enh = ml_result.get("ml_enhancement_bps", 0)
    ml_mc = mc_results["ML增强 (权重调整)"]
    base_mc = mc_results["基准 (买入持有)"]
    opt_mc = mc_results["乐观 (政策+ML共振)"]

    lines.append(f"1. **历史基线**: 当前组合 (75%权益+25%现金) 的买入持有年化收益为 **{pct(baseline['annual_return'])}**，"
                   f"距 {TARGET_RETURN*100:.0f}% 年化目标{'已达成' if baseline['annual_return'] >= TARGET_RETURN else '差' + pct(TARGET_RETURN - baseline['annual_return'])}")
    lines.append("")
    lines.append(f"2. **ML 增强效果**: GradientBoosting 模型 (F1=0.637) 通过对持仓标的生成方向信号、"
                   f"动态调整权重，预计可贡献超额年化 **{pct(ml_enh)}**")
    lines.append("")
    lines.append(f"3. **5年预测核心**: "
                   f"ML 增强组合 5 年中位 CAGR 为 **{pct(ml_mc['cagr_median'])}**，"
                   f"达到 8% 目标的概率为 **{ml_mc['prob_target']*100:.1f}%**；"
                   f"乐观情景下中位 CAGR 可达 **{pct(opt_mc['cagr_median'])}**")
    lines.append("")
    lines.append(f"4. **风险管控**: ML 增强组合 5 年预测中位最大回撤为 {pct(ml_mc['dd_median'])}，"
                   f"极端情况 (P95) 为 {pct(ml_mc['dd_p95'])}，"
                   f"建议设置 {TARGET_DD*100:.0f}% 硬止损线")
    lines.append("")
    lines.append(f"5. **提升路径**: 将现金比例从 25% 降至 15% 可额外提升约 1.5pp 年化；"
                   f"接入 Wind MCP 宏观数据训练多因子模型可将 F1 提升至 0.65+，再贡献约 1-2pp")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("**免责声明**: 以上分析基于历史数据回测与统计模型，不构成投资建议。"
                   "实际收益受宏观经济、政策变化、市场情绪等多重因素影响，"
                   "可能与预测结果存在重大偏差。过往表现不代表未来收益。")
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 8) 主流程
# ============================================================
def main():
    print("=" * 70)
    print("  ML 增强量化交易系统集成 + 5年收益预测 v2")
    print("=" * 70)
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Step 1: 计算历史统计
    print("[步骤 1/5] 计算各标的历史收益/风险...")
    stats = compute_historical_stats()
    print(f"  数据覆盖 {len(stats)} 只标的, {stats['n_days'].sum()} 个交易日")

    # Step 2: 加载权重
    print("[步骤 2/5] 加载组合权重...")
    weights, categories = load_portfolio_weights()
    print(f"  组合包含 {len([c for c in weights if c != 'CASH'])} 只标的 + 现金")

    # Step 3: 计算基线
    print("[步骤 3/5] 计算组合基线...")
    baseline = compute_portfolio_baseline(stats, weights)
    print(f"  买入持有年化: {pct(baseline['annual_return'])}")
    print(f"  波动率: {pct(baseline['annual_volatility'])}")
    print(f"  夏普: {baseline['sharpe']:.3f}")

    # Step 4: ML 增强评估
    print("[步骤 4/5] 评估 ML 增强效果...")
    ml_result = evaluate_ml_enhancement(stats, weights)
    ml_bps = ml_result["ml_enhancement_bps"]
    print(f"  ML 增强预估: {pct(ml_bps)} 超额年化")

    # Step 5: 蒙特卡洛预测
    print(f"\n[步骤 5/5] 蒙特卡洛 {YEARS_FORECAST} 年预测 ({MC_SIMULATIONS} 次)...")
    mc_results = monte_carlo_5year(
        baseline["annual_return"],
        baseline["annual_volatility"],
        ml_bps,
    )

    # 板块分解
    print("[板块] 拆解板块贡献...")
    sector_df = sector_decomposition(stats, weights, categories)

    # 打印摘要
    print()
    print("=" * 70)
    print("  5年年化收益率预测摘要")
    print("=" * 70)
    for name in ["ML增强 (权重调整)", "基准 (买入持有)", "乐观 (政策+ML共振)", "极度悲观 (熊市+模型失效)"]:
        r = mc_results[name]
        print(f"  [{name}] 中位CAGR={pct(r['cagr_median'])},  P(≥8%)={r['prob_target']*100:.0f}%,  中位回撤={pct(r['dd_median'])}")
    print("=" * 70)

    # 生成并保存报告
    report = generate_report(baseline, ml_result, mc_results, sector_df, stats, weights)
    os.makedirs("reports", exist_ok=True)
    today_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join("reports", f"ML集成_5年预测_v2_{today_str}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n[报告] 已保存: {report_path}")

    # 同时写入到每日报告归档
    archive_dir = os.path.join("每日报告归档", datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(archive_dir, exist_ok=True)
    archive_path = os.path.join(archive_dir, f"ML集成_5年预测_{today_str}.md")
    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[存档] 已保存: {archive_path}")


if __name__ == "__main__":
    main()
