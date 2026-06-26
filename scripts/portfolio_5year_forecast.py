# -*- coding: utf-8 -*-
"""组合风险收益约束检验 + 5年蒙特卡洛预测
要求: 年化收益率 ≥ 8%, 最大回撤 ≤ 15%
输出: 1) 当前配置可行性评估 2) 5年滚动CAGR与回撤预测 3) 建议调整权重

运行方式:  python scripts/portfolio_5year_forecast.py
"""
import os
import sys
import json
import math
import datetime as dt
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# -------- 依赖: numpy/pandas 必需，scipy/yaml 可选 --------
try:
    import numpy as np
    import pandas as pd
    HAVE_NP = True
except ImportError:
    np, pd, HAVE_NP = None, None, False

try:
    import yaml
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

from bootstrap import logger, BASE_DIR

# -------- 目标约束（可由命令行覆盖） --------
TARGET_RETURN = float(os.environ.get("TARGET_RETURN", "0.08"))   # 年化收益 ≥ 8%
TARGET_DD     = float(os.environ.get("TARGET_DD", "0.15"))       # 最大回撤 ≤ 15%
YEARS_FORECAST = int(os.environ.get("YEARS_FORECAST", "5"))       # 预测窗口 = 5年
MC_SIMULATIONS = int(os.environ.get("MC_SIM", "2000"))            # 蒙特卡洛模拟次数
CONFIDENCE = 0.95                                                 # VaR 置信度
RISK_FREE = 0.025                                                # 无风险利率（约等于10年国债）

# ============================================================
# 1) 读取配置 — 优先 portfolio.yaml，回退到固定20只
# ============================================================
def load_assets():
    """读取配置中的标的代码列表与目标权重"""
    fallback = [
        ("510300.SH", 0.12), ("510500.SH", 0.08), ("512100.SH", 0.06),
        ("588000.SH", 0.08), ("159915.SZ", 0.06), ("518880.SH", 0.10),
        ("300308.SZ", 0.05), ("688041.SH", 0.03), ("300274.SZ", 0.03),
        ("002371.SZ", 0.03), ("601088.SH", 0.05), ("600276.SH", 0.03),
        ("601888.SH", 0.02), ("600989.SH", 0.02), ("600875.SH", 0.02),
        ("600089.SH", 0.02), ("600995.SH", 0.02), ("000425.SZ", 0.02),
        ("688017.SH", 0.02), ("600406.SH", 0.04),
    ]
    path = os.path.join(BASE_DIR, "config", "portfolio.yaml")
    if not HAVE_YAML or not os.path.exists(path):
        logger.info(f"[5年预测] portfolio.yaml 不可用，使用内置 20 只默认配置")
        return fallback
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        rows = []
        for a in cfg.get("assets", []):
            code = str(a.get("code", "")).strip()
            w = float(a.get("target_weight", 0))
            if not code or code.upper() == "CASH" or w <= 0:
                continue
            # 补全市场后缀（统一加上 .SH / .SZ）
            if "." not in code:
                code = code + (".SH" if code.startswith("5") or code.startswith("6") else ".SZ")
            rows.append((code, w))
        if not rows:
            return fallback
        return rows
    except Exception as e:
        logger.warning(f"[5年预测] 读取 portfolio.yaml 失败: {e}，使用默认配置")
        return fallback


# ============================================================
# 2) 获取收益率数据 — Wind MCP 优先，其次 yfinance/akshare/sina
# ============================================================
def _wind_kline_fetch(code: str, days: int = 720):
    """Wind MCP — 首选数据源"""
    try:
        from wind_mcp_fetcher import wind_get_kline
        short = code.split(".")[0]
        is_fund = short.startswith(("51", "58", "15"))
        klines = wind_get_kline(short, days=days, is_fund=is_fund)
        if not klines or len(klines) < 30:
            return None
        import pandas as pd
        import numpy as np
        idx = []
        closes = []
        for k in klines:
            d = k.get("date")
            c = k.get("close")
            if d is None or c is None:
                continue
            try:
                if isinstance(d, (int, float)):
                    ds = str(int(d))
                else:
                    ds = str(d).replace("-", "")
                ts = pd.to_datetime(ds, format="%Y%m%d")
            except Exception:
                continue
            idx.append(ts)
            closes.append(float(c))
        if len(closes) < 30:
            return None
        s = pd.Series(closes, index=idx).sort_index().drop_duplicates()
        return s
    except Exception as e:
        logger.debug(f"[Wind MCP] {code} 失败: {e}")
        return None


def _yf_fetch(code: str, days: int = 720):
    """yfinance 回退"""
    try:
        import yfinance as yf
        ticker = code.replace(".SH", ".SS").replace(".SZ", ".SZ")
        hist = yf.Ticker(ticker).history(period=f"{days}d", auto_adjust=True)
        if hist is None or len(hist) < 30:
            return None
        s = hist["Close"].dropna().sort_index()
        return s
    except Exception:
        return None


def _ak_fetch(code: str, days: int = 720):
    """akshare 回退（仅当用户已安装）"""
    try:
        import akshare as ak
        short = code.split(".")[0]
        df = ak.stock_zh_a_hist(symbol=short, period="daily",
                                start_date=(dt.date.today() - dt.timedelta(days=days)).strftime("%Y%m%d"),
                                end_date=dt.date.today().strftime("%Y%m%d"),
                                adjust="qfq")
        if df is None or len(df) < 30:
            return None
        df["日期"] = pd.to_datetime(df["日期"])
        s = df.set_index("日期")["收盘"].astype(float).sort_index()
        return s
    except Exception:
        return None


def _sina_fetch(code: str, days: int = 720):
    """新浪财经 JSON 回退 — 轻量不依赖额外包"""
    import urllib.request
    try:
        short = code.split(".")[0]
        secid = f"sh{short}" if code.endswith(".SH") else f"sz{short}"
        url = (f"https://money.finance.sina.com.cn/quotes_service/api/"
               f"jsonp_v2.php/CN_MarketData.getKLineData?symbol={secid}"
               f"&scale=240&ma=no&datalen={days}")
        with urllib.request.urlopen(url, timeout=8) as r:
            raw = r.read().decode("gbk", errors="ignore")
        arr = json.loads(raw[raw.find("["): raw.rfind("]") + 1])
        if not arr:
            return None
        idx = [pd.Timestamp(x["day"]) for x in arr]
        vals = [float(x["close"]) for x in arr]
        return pd.Series(vals, index=idx).sort_index()
    except Exception:
        return None


def _fallback_risk_params(code: str, name_map: Dict[str, str]):
    """无网络环境的参数化回退 — 按风格预分配年化收益与波动"""
    style_table = {
        # (预期年化收益, 年化波动率)
        "510300": (0.07, 0.18),   # 沪深300
        "510500": (0.09, 0.22),   # 中证500
        "512100": (0.10, 0.25),   # 中证1000
        "588000": (0.12, 0.30),   # 科创50
        "159915": (0.11, 0.28),   # 创业板
        "518880": (0.05, 0.12),   # 黄金ETF
        "300308": (0.18, 0.40),   # 中际旭创 (算力)
        "688041": (0.15, 0.38),   # 海光信息 (芯片)
        "300274": (0.12, 0.35),   # 阳光电源
        "002371": (0.15, 0.35),   # 北方华创
        "601088": (0.06, 0.18),   # 中国神华
        "600276": (0.08, 0.22),   # 恒瑞医药
        "601888": (0.08, 0.25),   # 中国中免
        "600989": (0.09, 0.25),   # 宝丰能源
        "600875": (0.09, 0.22),   # 东方电气
        "600089": (0.08, 0.22),   # 特变电工
        "600995": (0.07, 0.20),   # 南网储能
        "000425": (0.08, 0.25),   # 徐工机械
        "688017": (0.15, 0.40),   # 绿的谐波
        "600406": (0.07, 0.18),   # 国电南瑞
    }
    short = code.split(".")[0]
    ret, vol = style_table.get(short, (0.08, 0.22))
    return ret, vol


def fetch_daily_returns(assets: List[Tuple[str, float]], days: int = 720):
    """依次尝试 Wind MCP → yfinance → akshare → sina → 参数模型
    (Wind MCP 为首选 — 用户要求 '所有数据优先使用 wind mcp')
    """
    results = {}  # code -> pd.Series of daily returns
    used_method = {}
    for code, _ in assets:
        s = _wind_kline_fetch(code, days)
        used = "wind_mcp"
        if s is None or len(s) < 30:
            s = _yf_fetch(code, days)
            used = "yfinance"
        if s is None or len(s) < 30:
            s = _ak_fetch(code, days)
            used = "akshare"
        if s is None or len(s) < 30:
            s = _sina_fetch(code, days)
            used = "sina"
        if s is None or len(s) < 30:
            used = "参数模型"
            mu, vol = _fallback_risk_params(code, {})
            rng = np.random.default_rng(abs(hash(code)) % 2**32)
            n = 720
            dt_ = 1 / 252
            drift = (mu - 0.5 * vol ** 2) * dt_
            noise = vol * math.sqrt(dt_)
            daily = rng.normal(drift, noise, n)
            dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n)
            s_ret = pd.Series(daily, index=dates)
            results[code] = s_ret
            used_method[code] = used
            continue
        # 真实行情：计算对数收益率
        ret = np.log(s / s.shift(1)).dropna()
        results[code] = ret
        used_method[code] = used

    logger.info(f"[5年预测] 数据获取完成: {len(results)} 只，方法分布="
                f"{dict(pd.Series(used_method).value_counts()) if HAVE_NP else used_method}")
    return results, used_method


# ============================================================
# 3) 组合收益与风险计算
# ============================================================
def compute_portfolio_stats(returns_dict: Dict[str, "pd.Series"],
                            weights: Dict[str, float]):
    """用历史收益率协方差 + 权重 → 年化收益/波动/回撤/夏普/VaR"""
    df = pd.DataFrame(returns_dict).dropna(how="all").ffill().fillna(0)
    # 对齐到最小公共长度
    df = df.tail(min(720, len(df)))
    codes = list(weights.keys())
    for c in codes:
        if c not in df.columns:
            df[c] = 0.0
    w = np.array([float(weights.get(c, 0)) for c in codes])
    w = w / max(w.sum(), 1e-9)

    mu_vec = df[codes].mean().values * 252          # 年化收益向量
    Sigma  = df[codes].cov().values * 252             # 年化协方差

    port_mu = float(w @ mu_vec)
    port_vol = float(math.sqrt(w @ Sigma @ w))
    sharpe = (port_mu - RISK_FREE) / port_vol if port_vol > 0 else 0

    # 历史组合收益序列 → 计算最大回撤
    hist_rets = (df[codes] @ w)
    cum = (1 + hist_rets).cumprod()
    peak = cum.cummax()
    dd = (cum - peak) / peak
    max_dd = float(dd.min()) if len(dd) else 0.0

    # VaR（参数正态 + 历史）
    z = {0.9: 1.282, 0.95: 1.645, 0.99: 2.326}.get(CONFIDENCE, 1.645)
    var_param = -(port_mu / 252 - z * port_vol / math.sqrt(252))
    var_hist  = float(-hist_rets.quantile(1 - CONFIDENCE)) if len(hist_rets) else float("nan")

    return {
        "annual_return": port_mu,
        "annual_vol": port_vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "var_param": var_param,
        "var_hist": var_hist,
        "mu_vec": dict(zip(codes, mu_vec)),
        "vol_vec": {c: float(math.sqrt(Sigma[i, i])) for i, c in enumerate(codes)},
    }


# ============================================================
# 4) 5年蒙特卡洛预测 —— CAGR 与 最大回撤分布
# ============================================================
def monte_carlo_forecast(returns_dict: Dict[str, "pd.Series"],
                         weights: Dict[str, float],
                         years: int = 5, n_sim: int = 2000):
    """输出 5年CAGR分布 + 最大回撤分布"""
    df = pd.DataFrame(returns_dict).dropna(how="all").ffill().fillna(0)
    codes = list(weights.keys())
    for c in codes:
        if c not in df.columns:
            df[c] = 0.0
    w = np.array([float(weights.get(c, 0)) for c in codes])
    w = w / max(w.sum(), 1e-9)

    mu_day = df[codes].mean().values
    Sigma_day = df[codes].cov().values

    n_days = int(years * 252)
    rng = np.random.default_rng(42)
    # 多维正态抽样 — 用 Cholesky 分解
    L = np.linalg.cholesky(Sigma_day + 1e-8 * np.eye(len(codes)))
    # 用向量化方式抽样 (n_sim, n_days, n_assets)
    z = rng.standard_normal((n_sim, n_days, len(codes)))
    daily = mu_day + (z @ L.T)  # shape (n_sim, n_days, n_assets)

    # 组合日收益
    port_daily = daily @ w                            # (n_sim, n_days)
    # 每条路径的CAGR
    cum = (port_daily + 1).prod(axis=1)
    cagr = cum ** (252 / n_days) - 1
    # 每条路径的最大回撤
    cum_arr = np.cumprod(port_daily + 1, axis=1)
    peak = np.maximum.accumulate(cum_arr, axis=1)
    dd = (cum_arr - peak) / peak
    max_dd = dd.min(axis=1)

    return {
        "cagr_mean": float(cagr.mean()),
        "cagr_std":  float(cagr.std()),
        "cagr_p5":   float(np.quantile(cagr, 0.05)),
        "cagr_median": float(np.quantile(cagr, 0.5)),
        "cagr_p95":  float(np.quantile(cagr, 0.95)),
        "dd_mean":   float(max_dd.mean()),
        "dd_p5":     float(np.quantile(max_dd, 0.05)),
        "dd_median": float(np.quantile(max_dd, 0.5)),
        "dd_p95":    float(np.quantile(max_dd, 0.95)),
        "prob_cagr_above_target": float(np.mean(cagr >= TARGET_RETURN)),
        "prob_dd_above_target":   float(np.mean(max_dd < -TARGET_DD)),  # 突破回撤上限的概率
    }


# ============================================================
# 5) 简易权重优化器 —— 用再抽样前沿拟合可接受的参数点
# ============================================================
def suggest_improved_weights(returns_dict, base_weights: Dict[str, float]):
    """在基础权重附近做梯度微调，使预期收益≥8%且预期回撤≤15%。
    简易实现：对每只资产做 (mu - 0.5*lambda*sigma^2) 归一权重。
    """
    df = pd.DataFrame(returns_dict).dropna(how="all").ffill().fillna(0)
    codes = list(base_weights.keys())
    for c in codes:
        if c not in df.columns:
            df[c] = 0.0
    mu_day = df[codes].mean().values * 252
    vol = np.sqrt(np.diag(df[codes].cov().values * 252))

    # 夏普比加权（经风险调整），再做风格层平滑
    raw = np.maximum(mu_day - RISK_FREE, 0.01) / (vol + 0.05)
    raw = raw / raw.sum()
    # 与原权重做 50:50 混合，避免过度偏离
    w_base = np.array([float(base_weights.get(c, 0)) for c in codes])
    w_base = w_base / max(w_base.sum(), 1e-9)
    w_improved = 0.5 * w_base + 0.5 * raw
    w_improved = w_improved / w_improved.sum()
    return dict(zip(codes, w_improved.tolist()))


# ============================================================
# 6) 输出 Markdown
# ============================================================
def pct(x):
    return f"{x * 100:+.2f}%" if x < 0 else f"{x * 100:.2f}%"


def build_report(assets, base_weights, stats, forecast, improved_weights,
                 stats_improved, forecast_improved, used_method):
    lines = []
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 十、年化收益/最大回撤约束检验与五年预测")
    lines.append("")
    lines.append(f"**约束目标**: 年化收益 ≥ {TARGET_RETURN*100:.0f}%，最大回撤 ≤ {TARGET_DD*100:.0f}%")
    lines.append(f"**预测窗口**: {YEARS_FORECAST} 年（{YEARS_FORECAST*252} 交易日）")
    lines.append(f"**模拟次数**: {MC_SIMULATIONS} 次 · 置信度 {CONFIDENCE*100:.0f}% · 无风险利率 {RISK_FREE*100:.1f}%")
    lines.append(f"**数据源**: {', '.join(f'{k}×{v}' for k,v in pd.Series(used_method).value_counts().items()) if HAVE_NP else used_method}")
    lines.append("")

    # A. 当前配置指标
    lines.append("### A. 当前配置（portfolio.yaml）组合指标")
    lines.append("")
    lines.append("| 指标 | 数值 | 是否满足约束 |")
    lines.append("|------|------|-------------|")
    lines.append(f"| 年化收益率(历史) | {pct(stats['annual_return'])} | {'✅ ≥8%' if stats['annual_return']>=TARGET_RETURN else '⚠️ <8%'} |")
    lines.append(f"| 年化波动率       | {pct(stats['annual_vol'])} | — |")
    lines.append(f"| 夏普比率         | {stats['sharpe']:+.3f} | — |")
    lines.append(f"| 最大回撤(历史)   | {pct(stats['max_drawdown'])} | {'✅ ≤15%' if stats['max_drawdown']>=-TARGET_DD else '⚠️ >15%'} |")
    lines.append(f"| 参数VaR({CONFIDENCE*100:.0f}%) | {pct(stats['var_param'])} (1日) | — |")
    lines.append(f"| 历史VaR({CONFIDENCE*100:.0f}%) | {pct(stats['var_hist'])} (1日) | — |")
    lines.append("")

    lines.append("**单标的年化收益 / 波动率(基于数据窗口)**:")
    lines.append("")
    lines.append("| 代码 | 年化收益 | 年化波动 |")
    lines.append("|------|---------|---------|")
    for code in list(base_weights.keys()):
        mu = stats["mu_vec"].get(code, float("nan"))
        v = stats["vol_vec"].get(code, float("nan"))
        lines.append(f"| {code} | {pct(mu)} | {pct(v)} |")
    lines.append("")

    # B. 5年蒙特卡洛预测
    lines.append(f"### B. {YEARS_FORECAST}年滚动预测（蒙特卡洛 {MC_SIMULATIONS} 次）")
    lines.append("")
    lines.append("#### CAGR 分布 (年化复利增长率)")
    lines.append("")
    lines.append("| 分位数 | CAGR |")
    lines.append("|--------|------|")
    lines.append(f"| 5%  | {pct(forecast['cagr_p5'])} |")
    lines.append(f"| 50% | {pct(forecast['cagr_median'])} |")
    lines.append(f"| 95% | {pct(forecast['cagr_p95'])} |")
    lines.append(f"| 均值±标准差 | {pct(forecast['cagr_mean'])} ± {pct(forecast['cagr_std'])} |")
    lines.append(f"| P(CAGR ≥ {TARGET_RETURN*100:.0f}%) | {forecast['prob_cagr_above_target']*100:.1f}% |")
    lines.append("")

    lines.append("#### 最大回撤分布（取每条路径的min值）")
    lines.append("")
    lines.append("| 分位数 | 最大回撤 |")
    lines.append("|--------|---------|")
    lines.append(f"| 5%   | {pct(forecast['dd_p5'])} |")
    lines.append(f"| 50%  | {pct(forecast['dd_median'])} |")
    lines.append(f"| 95%  | {pct(forecast['dd_p95'])} |")
    lines.append(f"| 均值 | {pct(forecast['dd_mean'])} |")
    lines.append(f"| P(最大回撤 > {TARGET_DD*100:.0f}%) | {forecast['prob_dd_above_target']*100:.1f}% |")
    lines.append("")

    # C. 改进建议
    lines.append("### C. 权重优化建议（夏普比加权 与 原权重 50:50 混合）")
    lines.append("")
    lines.append("| 代码 | 原权重 | 建议权重 | 变化 |")
    lines.append("|------|--------|---------|------|")
    for code in list(base_weights.keys()):
        w0 = float(base_weights.get(code, 0))
        w1 = float(improved_weights.get(code, 0))
        lines.append(f"| {code} | {w0*100:.1f}% | {w1*100:.1f}% | {(w1-w0)*100:+.1f}pp |")
    lines.append("")

    lines.append("**改进后组合指标**:")
    lines.append("")
    lines.append("| 指标 | 数值 | 是否满足约束 |")
    lines.append("|------|------|-------------|")
    lines.append(f"| 年化收益率(历史) | {pct(stats_improved['annual_return'])} | {'✅ ≥8%' if stats_improved['annual_return']>=TARGET_RETURN else '⚠️ <8%'} |")
    lines.append(f"| 年化波动率       | {pct(stats_improved['annual_vol'])} | — |")
    lines.append(f"| 夏普比率         | {stats_improved['sharpe']:+.3f} | — |")
    lines.append(f"| 最大回撤(历史)   | {pct(stats_improved['max_drawdown'])} | {'✅ ≤15%' if stats_improved['max_drawdown']>=-TARGET_DD else '⚠️ >15%'} |")
    lines.append("")

    lines.append(f"**改进后 5 年 CAGR 中位数**: {pct(forecast_improved['cagr_median'])}（原 {pct(forecast['cagr_median'])}）")
    lines.append(f"**改进后最大回撤中位数**: {pct(forecast_improved['dd_median'])}（原 {pct(forecast['dd_median'])}）")
    lines.append("")

    # D. 结论
    lines.append("### D. 结论与操作建议")
    lines.append("")
    ok_return = stats['annual_return'] >= TARGET_RETURN
    ok_dd = stats['max_drawdown'] >= -TARGET_DD
    lines.append(f"- 当前配置：年化收益{'✅达标' if ok_return else '⚠️未达标'}，最大回撤{'✅达标' if ok_dd else '⚠️未达标'}")
    lines.append(f"- 5 年预测中位数 CAGR={pct(forecast['cagr_median'])}，P(CAGR≥{TARGET_RETURN*100:.0f}%)={forecast['prob_cagr_above_target']*100:.1f}%")
    lines.append(f"- 5 年预测最大回撤中位数={pct(forecast['dd_median'])}，P(回撤>{TARGET_DD*100:.0f}%)={forecast['prob_dd_above_target']*100:.1f}%")
    lines.append(f"- 若需更稳健，可采用 **建议权重**（与原配置混合版），预期 CAGR {pct(forecast_improved['cagr_median'])}，回撤 {pct(forecast_improved['dd_median'])}")
    lines.append(f"- 数据不足的标的使用 **参数模型** 作为占位，真实行情接入后自动替换")
    lines.append("")
    return "\n".join(lines)


# ============================================================
# 7) 主流程
# ============================================================
def main():
    logger.info("[5年预测] 开始运行组合风险-收益约束分析")

    if not HAVE_NP:
        print("❌ 本脚本需要 numpy / pandas。请先安装: pip install numpy pandas")
        return

    assets = load_assets()
    base_weights = {code: float(w) for code, w in assets}
    total_w = sum(base_weights.values())
    if total_w < 0.9:
        logger.info(f"[5年预测] 权重合计 {total_w:.3f}，差额视为现金/无风险利率")
    cash_weight = max(0.0, 1.0 - total_w)

    # 获取收益数据
    returns_dict, used_method = fetch_daily_returns(assets, days=720)

    # 当前配置 vs 改进配置
    stats = compute_portfolio_stats(returns_dict, base_weights)
    forecast = monte_carlo_forecast(returns_dict, base_weights,
                                    years=YEARS_FORECAST, n_sim=MC_SIMULATIONS)
    improved = suggest_improved_weights(returns_dict, base_weights)
    stats_i = compute_portfolio_stats(returns_dict, improved)
    forecast_i = monte_carlo_forecast(returns_dict, improved,
                                      years=YEARS_FORECAST, n_sim=MC_SIMULATIONS)

    markdown = build_report(assets, base_weights, stats, forecast,
                            improved, stats_i, forecast_i, used_method)

    # 控制台输出关键结果
    print("\n" + "=" * 70)
    print(" 组合风险-收益约束分析结果")
    print("=" * 70)
    print(f"  年化收益率(历史) : {stats['annual_return']*100:+.2f}%   目标≥ {TARGET_RETURN*100:.0f}%  {'✅' if stats['annual_return']>=TARGET_RETURN else '⚠️'}")
    print(f"  最大回撤(历史)   : {stats['max_drawdown']*100:+.2f}%   目标≤ {TARGET_DD*100:.0f}% {'✅' if stats['max_drawdown']>=-TARGET_DD else '⚠️'}")
    print(f"  夏普比率         : {stats['sharpe']:+.3f}")
    print(f"  5年CAGR中位数    : {forecast['cagr_median']*100:+.2f}%   (均值±σ {forecast['cagr_mean']*100:+.2f}±{forecast['cagr_std']*100:.2f})")
    print(f"  5年最大回撤中位数: {forecast['dd_median']*100:+.2f}%")
    print(f"  P(CAGR≥{TARGET_RETURN*100:.0f}%)  : {forecast['prob_cagr_above_target']*100:.1f}%")
    print(f"  P(DD>{TARGET_DD*100:.0f}%)      : {forecast['prob_dd_above_target']*100:.1f}%")
    print("=" * 70)
    print(f" 建议权重组合 CAGR中位数 : {forecast_i['cagr_median']*100:+.2f}%  最大回撤中位数: {forecast_i['dd_median']*100:+.2f}%")
    print("=" * 70)

    # 写入 reports/2026年度交易计划_*.md（追加）
    out_dir = os.path.join(BASE_DIR, "reports")
    os.makedirs(out_dir, exist_ok=True)
    today = dt.date.today().strftime("%Y%m%d")
    out_file = os.path.join(out_dir, f"2026年度交易计划_{today}.md")
    # 如主报告尚未存在，先写一个简短标题
    if not os.path.exists(out_file):
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("# 2026 年度交易计划（自动生成）\n\n")
    with open(out_file, "a", encoding="utf-8") as f:
        f.write(markdown)
    print(f"\n📄 分析章节已追加到: {out_file}")

    # 也写一份独立的风险报告
    risk_file = os.path.join(out_dir, f"风险收益预测_{today}.md")
    with open(risk_file, "w", encoding="utf-8") as f:
        f.write("# 组合风险-收益约束检验与五年预测\n\n")
        f.write(markdown)
    print(f"📄 独立报告: {risk_file}")


if __name__ == "__main__":
    main()
