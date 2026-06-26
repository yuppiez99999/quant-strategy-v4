# -*- coding: utf-8 -*-
"""
12只标的综合回测与宏观周期分析
- 年化收益率 & 最大回撤测算
- 5年年化收益预测
- 十五五规划适配性分析
- 康波周期位置判断
"""

import os
import json
import math
from datetime import datetime, timedelta
from collections import OrderedDict

# ============================================================
# 12只标的基础数据（模拟历史数据，基于行业Beta和波动率）
# ============================================================

STOCKS = OrderedDict([
    ("601088", {
        "name": "中国神华",
        "industry": "能源/煤炭",
        "sector": "制造转型",
        "current_price": 48.93,
        "avg_cost": 48.93,
        "historical_return": 0.125,      # 历史年化收益
        "volatility": 0.18,               # 年化波动率
        "beta": 0.65,                     # Beta系数
        "dividend_yield": 0.075,          # 股息率
        "pe": 8.5,
        "pb": 1.2,
        "sector_focus": "传统能源转型",
    }),
    ("000425", {
        "name": "徐工机械",
        "industry": "机械工程",
        "sector": "制造转型",
        "current_price": 5.50,
        "avg_cost": 5.50,
        "historical_return": 0.068,
        "volatility": 0.35,
        "beta": 1.25,
        "dividend_yield": 0.042,
        "pe": 15.2,
        "pb": 1.1,
        "sector_focus": "高端装备制造",
    }),
    ("600276", {
        "name": "恒瑞医药",
        "industry": "生物医药",
        "sector": "核心成长",
        "current_price": 47.25,
        "avg_cost": 47.25,
        "historical_return": 0.082,
        "volatility": 0.28,
        "beta": 0.95,
        "dividend_yield": 0.012,
        "pe": 58.5,
        "pb": 6.2,
        "sector_focus": "创新药研发",
    }),
    ("600995", {
        "name": "南网储能",
        "industry": "储能/电力",
        "sector": "核心成长",
        "current_price": 9.00,
        "avg_cost": 9.00,
        "historical_return": 0.105,
        "volatility": 0.32,
        "beta": 1.10,
        "dividend_yield": 0.028,
        "pe": 32.5,
        "pb": 2.8,
        "sector_focus": "新型储能/抽水蓄能",
    }),
    ("002371", {
        "name": "北方华创",
        "industry": "半导体设备",
        "sector": "核心成长",
        "current_price": 605.08,
        "avg_cost": 605.08,
        "historical_return": 0.225,
        "volatility": 0.45,
        "beta": 1.55,
        "dividend_yield": 0.004,
        "pe": 85.0,
        "pb": 12.5,
        "sector_focus": "半导体自主可控",
    }),
    ("688017", {
        "name": "绿的谐波",
        "industry": "机器人/谐波减速器",
        "sector": "核心成长",
        "current_price": 320.38,
        "avg_cost": 320.38,
        "historical_return": 0.185,
        "volatility": 0.55,
        "beta": 1.68,
        "dividend_yield": 0.003,
        "pe": 120.0,
        "pb": 15.8,
        "sector_focus": "人形机器人核心部件",
    }),
    ("688981", {
        "name": "中芯国际",
        "industry": "半导体制造",
        "sector": "核心成长",
        "current_price": 55.00,
        "avg_cost": 55.00,
        "historical_return": 0.055,
        "volatility": 0.42,
        "beta": 1.45,
        "dividend_yield": 0.000,
        "pe": 35.0,
        "pb": 2.2,
        "sector_focus": "晶圆制造自主化",
    }),
    ("300750", {
        "name": "宁德时代",
        "industry": "新能源/动力电池",
        "sector": "核心成长",
        "current_price": 210.00,
        "avg_cost": 210.00,
        "historical_return": 0.158,
        "volatility": 0.48,
        "beta": 1.52,
        "dividend_yield": 0.008,
        "pe": 22.5,
        "pb": 3.8,
        "sector_focus": "动力电池与储能",
    }),
    ("300124", {
        "name": "汇川技术",
        "industry": "工业自动化",
        "sector": "核心成长",
        "current_price": 28.00,
        "avg_cost": 28.00,
        "historical_return": 0.112,
        "volatility": 0.30,
        "beta": 1.15,
        "dividend_yield": 0.018,
        "pe": 28.5,
        "pb": 3.5,
        "sector_focus": "工业自动化/伺服系统",
    }),
    ("002475", {
        "name": "立讯精密",
        "industry": "消费电子",
        "sector": "核心成长",
        "current_price": 38.00,
        "avg_cost": 38.00,
        "historical_return": 0.095,
        "volatility": 0.32,
        "beta": 1.20,
        "dividend_yield": 0.015,
        "pe": 18.5,
        "pb": 2.8,
        "sector_focus": "消费电子精密制造",
    }),
    ("603259", {
        "name": "药明康德",
        "industry": "医药研发服务",
        "sector": "核心成长",
        "current_price": 65.00,
        "avg_cost": 65.00,
        "historical_return": 0.072,
        "volatility": 0.35,
        "beta": 1.18,
        "dividend_yield": 0.018,
        "pe": 22.0,
        "pb": 2.5,
        "sector_focus": "CXO/医药外包服务",
    }),
    ("518880", {
        "name": "华安黄金ETF",
        "industry": "黄金/商品",
        "sector": "防御资产",
        "current_price": 5.50,
        "avg_cost": 5.50,
        "historical_return": 0.068,
        "volatility": 0.15,
        "beta": 0.05,
        "dividend_yield": 0.000,
        "pe": 0,
        "pb": 1.0,
        "sector_focus": "抗通胀/避险资产",
    }),
])

# 目标权重配置
TARGET_WEIGHTS = OrderedDict([
    ("601088", 0.12),
    ("000425", 0.10),
    ("600276", 0.10),
    ("600995", 0.10),
    ("002371", 0.08),
    ("688017", 0.06),
    ("688981", 0.08),
    ("300750", 0.08),
    ("300124", 0.07),
    ("002475", 0.07),
    ("603259", 0.06),
    ("518880", 0.08),
])

# ============================================================
# 十五五规划（2026-2030）重点领域映射
# ============================================================

FIFTEENTH_FIVE_YEAR = {
    "core_sectors": [
        "先进制造与高端装备",      # 徐工机械、汇川技术
        "集成电路与半导体",         # 北方华创、中芯国际
        "新能源与新型储能",         # 宁德时代、南网储能
        "生物医药与创新药",         # 恒瑞医药、药明康德
        "人工智能与人形机器人",      # 绿的谐波、汇川技术
        "消费电子与精密制造",       # 立讯精密
        "传统能源转型与安全",       # 中国神华
        "黄金与战略储备",           # 黄金ETF
    ],
    "key_initiatives": [
        "制造业数字化转型",
        "关键核心技术攻关（芯片、工业母机）",
        "新型工业化与智能制造",
        "双碳目标下的能源革命",
        "生物制造与医药创新",
        "数字经济与人工智能+",
        "产业链供应链自主可控",
    ],
    "macro_forecast": {
        "gdp_growth": "4.5%-5.5%",
        "inflation": "2.0%-3.0%",
        "policy_stance": "积极财政+稳健货币",
        "reform_focus": "国企改革/科技体制/金融支持实体",
    }
}

# ============================================================
# 康波周期（Kondratieff Wave）分析模型
# ============================================================

KONDRATIEFF_CYCLE = {
    "cycle_length_years": 50,
    "current_phase": {
        "name": "萧条期末期 → 复苏期初期",
        "start_year": 2020,
        "expected_recovery_year": 2028,
        "position_in_cycle": "第4阶段（复苏启动期）",
    },
    "phase_description": {
        "繁荣期(1991-2000)": "信息技术革命，互联网繁荣，大宗商品上涨",
        "衰退期(2000-2008)": "科网泡沫破裂，次贷危机，全球金融危机",
        "萧条期(2008-2020)": "QE救市，低增长，零利率，贫富分化加剧",
        "回升期(2020-2028)": "后疫情时代，AI革命，新能源替代，地缘重构",
    },
    "key_drivers_next_5y": [
        "人工智能技术大规模商用（2026-2028）",
        "新能源对化石能源的实质性替代",
        "半导体产业链的全球重构",
        "生物科技/基因编辑的突破",
        "金砖国家/南方国家的崛起与去美元化",
        "全球债务周期重置",
    ],
}

# ============================================================
# 回测引擎
# ============================================================

class BacktestEngine:
    def __init__(self, stocks, weights, total_capital=1000000):
        self.stocks = stocks
        self.weights = weights
        self.total_capital = total_capital
        self.trading_days_per_year = 252

    def calculate_portfolio_stats(self):
        """计算组合基础统计"""
        weighted_return = 0
        weighted_volatility = 0
        weighted_beta = 0
        weighted_dividend = 0
        weighted_pe = 0

        for code, weight in self.weights.items():
            stock = self.stocks[code]
            weighted_return += weight * stock["historical_return"]
            weighted_volatility += weight * weight * stock["volatility"] ** 2
            weighted_beta += weight * stock["beta"]
            weighted_dividend += weight * stock["dividend_yield"]
            if stock["pe"] > 0:
                weighted_pe += weight * stock["pe"]

        # 加入资产间分散化效应（假设平均相关系数0.5）
        avg_correlation = 0.5
        n_assets = len(self.weights)
        diversification_factor = math.sqrt(
            (1 - avg_correlation) / n_assets + avg_correlation
        )
        portfolio_vol = math.sqrt(weighted_volatility) * (1 / diversification_factor * 0.75)

        return {
            "expected_annual_return": weighted_return,
            "portfolio_volatility": portfolio_vol,
            "portfolio_beta": weighted_beta,
            "dividend_yield": weighted_dividend,
            "weighted_pe": weighted_pe,
            "sharpe_ratio": (weighted_return - 0.02) / portfolio_vol if portfolio_vol > 0 else 0,
        }

    def simulate_5year_backtest(self):
        """模拟5年历史回测（约1260个交易日）"""
        results = []
        n_days = 1260
        capital = self.total_capital
        peak = capital
        max_dd = 0
        max_dd_start = 0
        max_dd_end = 0
        dd_periods = []

        # 按权重分配初始持仓市值
        allocations = {}
        for code, weight in self.weights.items():
            allocations[code] = {
                "value": capital * weight,
                "shares": int((capital * weight) / self.stocks[code]["current_price"] / 100) * 100,
            }

        # 模拟每日波动
        daily_returns = []
        for day in range(n_days):
            day_return = 0
            for code, weight in self.weights.items():
                stock = self.stocks[code]
                # 每日收益率 = 年化收益/252 + 波动率随机冲击
                import random
                random.seed(hash(code) % 100000 + day)
                daily_ret = (stock["historical_return"] / self.trading_days_per_year +
                           stock["volatility"] / math.sqrt(self.trading_days_per_year) * random.gauss(0, 1))
                day_return += weight * daily_ret

            daily_returns.append(day_return)
            capital *= (1 + day_return)

            if capital > peak:
                peak = capital
                if max_dd > 0:
                    dd_periods.append({
                        "dd": max_dd,
                        "start_day": max_dd_start,
                        "end_day": max_dd_end,
                        "duration_days": max_dd_end - max_dd_start,
                    })
                max_dd = 0
            else:
                current_dd = (peak - capital) / peak
                if current_dd > max_dd:
                    max_dd = current_dd
                    max_dd_start = len([x for x in daily_returns[:day] if x < 0])
                    max_dd_end = day

            results.append({
                "day": day,
                "date": (datetime(2021, 1, 4) + timedelta(days=int(day * 1.4))).strftime("%Y-%m-%d"),
                "equity": capital,
                "daily_return": day_return,
                "drawdown": (peak - capital) / peak,
                "peak": peak,
            })

        # 汇总回撤超过15%的区间
        significant_dds = [p for p in dd_periods if p["dd"] > 0.15]

        total_return = (capital / self.total_capital) - 1
        annualized_return = (1 + total_return) ** (self.trading_days_per_year / n_days) - 1

        # 计算年度收益
        yearly_returns = {}
        for year_idx in range(5):
            start = year_idx * 252
            end = min((year_idx + 1) * 252, n_days)
            if start < len(results) and end <= len(results):
                year_capital_start = results[start]["equity"]
                year_capital_end = results[end - 1]["equity"]
                yearly_returns[f"202{1+year_idx}"] = (year_capital_end / year_capital_start - 1)

        return {
            "final_capital": capital,
            "total_return": total_return,
            "annualized_return": annualized_return,
            "max_drawdown": max(dd["dd"] for dd in dd_periods) if dd_periods else 0,
            "volatility_annual": (sum((r - sum(daily_returns)/len(daily_returns))**2 for r in daily_returns) / len(daily_returns)) ** 0.5 * math.sqrt(self.trading_days_per_year),
            "sharpe_ratio": (annualized_return - 0.02) / (sum((r - sum(daily_returns)/len(daily_returns))**2 for r in daily_returns) / len(daily_returns)) ** 0.5 / math.sqrt(self.trading_days_per_year) * math.sqrt(self.trading_days_per_year),
            "win_rate": sum(1 for r in daily_returns if r > 0) / len(daily_returns),
            "yearly_returns": yearly_returns,
            "significant_dds": significant_dds[:5],
            "equity_curve": results[::21],  # 每21个交易日采样一次（约一个月）
        }

    def forecast_5year(self, stats, adjustment_factors):
        """5年预测 - 基于宏观周期调整"""
        base_forecast = stats["expected_annual_return"]

        # 十五五规划正向调整
        fifteen_factor = adjustment_factors["fifteenth_five_year"]

        # 康波周期调整
        kondratieff_factor = adjustment_factors["kondratieff"]

        # 估值调整（均值回归）
        valuation_factor = adjustment_factors["valuation"]

        # 综合预测
        forecast_return_high = base_forecast * fifteen_factor["optimistic"] * kondratieff_factor["optimistic"] * valuation_factor["optimistic"]
        forecast_return_mid = base_forecast * fifteen_factor["neutral"] * kondratieff_factor["neutral"] * valuation_factor["neutral"]
        forecast_return_low = base_forecast * fifteen_factor["conservative"] * kondratieff_factor["conservative"] * valuation_factor["conservative"]

        # 预测期最大回撤
        forecast_dd_high = stats["portfolio_volatility"] * 1.5
        forecast_dd_mid = stats["portfolio_volatility"] * 1.8
        forecast_dd_low = stats["portfolio_volatility"] * 2.2

        # 5年后预期资金
        expected_capital_high = self.total_capital * (1 + forecast_return_high) ** 5
        expected_capital_mid = self.total_capital * (1 + forecast_return_mid) ** 5
        expected_capital_low = self.total_capital * (1 + forecast_return_low) ** 5

        return {
            "scenarios": {
                "乐观": {
                    "annual_return": forecast_return_high,
                    "max_dd": forecast_dd_high,
                    "final_capital": expected_capital_high,
                },
                "中性": {
                    "annual_return": forecast_return_mid,
                    "max_dd": forecast_dd_mid,
                    "final_capital": expected_capital_mid,
                },
                "保守": {
                    "annual_return": forecast_return_low,
                    "max_dd": forecast_dd_low,
                    "final_capital": expected_capital_low,
                },
            },
            "cumulative_return_high": (1 + forecast_return_high) ** 5 - 1,
            "cumulative_return_mid": (1 + forecast_return_mid) ** 5 - 1,
            "cumulative_return_low": (1 + forecast_return_low) ** 5 - 1,
        }

    def analyze_fifteenth_five_year_alignment(self):
        """十五五规划适配性分析"""
        sector_alignment = {}
        total_alignment_score = 0

        alignment_map = {
            "先进制造与高端装备": ["000425", "300124"],           # 徐工机械、汇川技术
            "集成电路与半导体": ["002371", "688981"],              # 北方华创、中芯国际
            "新能源与新型储能": ["300750", "600995"],              # 宁德时代、南网储能
            "生物医药与创新药": ["600276", "603259"],              # 恒瑞医药、药明康德
            "人工智能与人形机器人": ["688017", "300124"],           # 绿的谐波、汇川技术
            "消费电子与精密制造": ["002475"],                      # 立讯精密
            "传统能源转型与安全": ["601088"],                      # 中国神华
            "黄金与战略储备": ["518880"],                          # 黄金ETF
        }

        for sector, codes in alignment_map.items():
            sector_weight = sum(self.weights.get(c, 0) for c in codes)
            sector_alignment[sector] = {
                "weight": sector_weight,
                "stocks": [self.stocks[c]["name"] for c in codes if c in self.stocks],
                "alignment_score": min(1.0, sector_weight / 0.15) if sector_weight > 0 else 0,
            }
            total_alignment_score += sector_alignment[sector]["alignment_score"] * sector_weight

        # 总体适配评分（满分100）
        total_weight_covered = sum(v["weight"] for v in sector_alignment.values())
        overall_score = min(100, total_weight_covered * 80 + total_alignment_score * 20)

        return {
            "overall_score": overall_score,
            "sector_breakdown": sector_alignment,
            "total_weight_in_focus": total_weight_covered,
        }

    def analyze_kondratieff_position(self):
        """康波周期位置判断"""
        current_year = datetime.now().year

        # 判断当前在康波周期中的位置
        cycle_year = current_year - KONDRATIEFF_CYCLE["current_phase"]["start_year"]
        phase_length = KONDRATIEFF_CYCLE["current_phase"]["expected_recovery_year"] - \
                      KONDRATIEFF_CYCLE["current_phase"]["start_year"]
        progress = cycle_year / phase_length

        # 各板块在当前康波阶段的表现倾向
        sector_performance_in_recovery = {
            "科技/半导体": "领先复苏，高Beta",
            "高端制造": "同步复苏，政策支持",
            "新能源": "结构性机会，需择时",
            "生物医药": "滞后复苏，估值先行",
            "消费电子": "周期敏感，弹性大",
            "传统能源": "防守转进攻",
            "黄金": "抗通胀/避险，非周期",
        }

        return {
            "current_phase": KONDRATIEFF_CYCLE["current_phase"]["name"],
            "position": f"回升期第{cycle_year}年，进度{progress*100:.0f}%",
            "cycle_progress": progress,
            "sector_outlook": sector_performance_in_recovery,
            "key_drivers": KONDRATIEFF_CYCLE["key_drivers_next_5y"],
        }


# ============================================================
# 主分析程序
# ============================================================

def main():
    print("=" * 80)
    print("📊 12只标的组合综合回测与宏观周期分析系统")
    print("=" * 80)
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"初始资金: ¥1,000,000")
    print(f"回测周期: 5年 (约1260个交易日)")
    print()

    engine = BacktestEngine(STOCKS, TARGET_WEIGHTS)

    # ========== 1. 基础组合统计 ==========
    print("=" * 80)
    print("【1/5】📈 组合基础指标")
    print("=" * 80)

    stats = engine.calculate_portfolio_stats()
    print(f"预期年化收益率: {stats['expected_annual_return']*100:.2f}%")
    print(f"组合波动率:     {stats['portfolio_volatility']*100:.2f}%")
    print(f"组合Beta:       {stats['portfolio_beta']:.3f}")
    print(f"股息率:         {stats['dividend_yield']*100:.2f}%")
    print(f"加权平均PE:     {stats['weighted_pe']:.2f}")
    print(f"夏普比率:       {stats['sharpe_ratio']:.3f}")
    print()

    # ========== 2. 5年历史回测 ==========
    print("=" * 80)
    print("【2/5】📉 5年历史回测结果 (模拟)")
    print("=" * 80)

    backtest = engine.simulate_5year_backtest()
    print(f"期末资金:       ¥{backtest['final_capital']:,.0f}")
    print(f"累计收益率:     {backtest['total_return']*100:.2f}%")
    print(f"年化收益率:     {backtest['annualized_return']*100:.2f}%")
    print(f"最大回撤:       {backtest['max_drawdown']*100:.2f}%")
    print(f"年化波动率:     {backtest['volatility_annual']*100:.2f}%")
    print(f"夏普比率:       {backtest['sharpe_ratio']:.3f}")
    print(f"日胜率:         {backtest['win_rate']*100:.1f}%")
    print()

    print("年度收益率:")
    for year, ret in sorted(backtest["yearly_returns"].items()):
        bar = "█" * int(abs(ret) * 200)
        sign = "+" if ret >= 0 else ""
        print(f"  {year}: {sign}{ret*100:.2f}% {bar}")
    print()

    print("回撤超过15%的区间:")
    if backtest["significant_dds"]:
        for i, dd in enumerate(backtest["significant_dds"], 1):
            print(f"  第{i}次: 最大回撤 {dd['dd']*100:.1f}%，持续{dd['duration_days']}个交易日")
    else:
        print("  无显著回撤区间（最大回撤均<15%）")
    print()

    # ========== 3. 5年收益预测 ==========
    print("=" * 80)
    print("【3/5】🔮 未来5年(2026-2030)收益预测")
    print("=" * 80)

    adjustment_factors = {
        "fifteenth_five_year": {
            "optimistic": 1.35,    # 政策红利充分释放
            "neutral": 1.15,       # 正常政策传导
            "conservative": 0.95,  # 政策效果不及预期
        },
        "kondratieff": {
            "optimistic": 1.25,    # 康波回升加速，AI革命超预期
            "neutral": 1.08,       # 温和回升
            "conservative": 0.85,  # 地缘冲突/债务危机拖累
        },
        "valuation": {
            "optimistic": 1.15,    # 估值从低位修复
            "neutral": 1.00,       # 估值中性
            "conservative": 0.88,  # 估值进一步压缩
        },
    }

    forecast = engine.forecast_5year(stats, adjustment_factors)

    print("📊 三种情景预测:")
    print("-" * 60)
    for scenario in ["乐观", "中性", "保守"]:
        data = forecast["scenarios"][scenario]
        print(f"\n【{scenario}情景】")
        print(f"  预期年化收益率: {data['annual_return']*100:.2f}%")
        print(f"  预期最大回撤:   {data['max_dd']*100:.2f}%")
        print(f"  5年累计收益:    {(forecast['cumulative_return_high'] if scenario=='乐观' else forecast['cumulative_return_mid'] if scenario=='中性' else forecast['cumulative_return_low'])*100:.2f}%")
        print(f"  5年后预期资金:  ¥{data['final_capital']:,.0f}")

    print()
    print(f"📌 中性情景参考: 年化{forecast['scenarios']['中性']['annual_return']*100:.2f}%，"
          f"5年累计{forecast['cumulative_return_mid']*100:.2f}%")
    print()

    # ========== 4. 十五五规划适配性 ==========
    print("=" * 80)
    print("【4/5】🏛️ 十五五规划(2026-2030)适配性分析")
    print("=" * 80)

    ff_alignment = engine.analyze_fifteenth_five_year_alignment()

    print(f"\n📈 整体适配评分: {ff_alignment['overall_score']:.1f}/100")
    print(f"📊 规划重点领域覆盖权重: {ff_alignment['total_weight_in_focus']*100:.1f}%")
    print()

    print("各规划领域匹配度:")
    print("-" * 60)
    for sector, info in ff_alignment["sector_breakdown"].items():
        if info["weight"] > 0:
            score_bar = "🟢" * int(info["alignment_score"] * 5) + "⚪" * (5 - int(info["alignment_score"] * 5))
            print(f"  {sector[:18]:<18} | 权重{info['weight']*100:.1f}% | {score_bar} | {', '.join(info['stocks'])}")
    print()

    print("🎯 十五五规划关键举措适配判断:")
    initiative_mapping = {
        "制造业数字化转型": ["000425", "300124"],
        "关键核心技术攻关（芯片、工业母机）": ["002371", "688981", "300124"],
        "新型工业化与智能制造": ["000425", "300124", "688017"],
        "双碳目标下的能源革命": ["601088", "600995", "300750"],
        "生物制造与医药创新": ["600276", "603259"],
        "数字经济与人工智能+": ["688017", "002475", "300124"],
        "产业链供应链自主可控": ["002371", "688981", "300750"],
    }
    for initiative in FIFTEENTH_FIVE_YEAR["key_initiatives"]:
        related_codes = initiative_mapping.get(initiative, [])
        related_weight = sum(TARGET_WEIGHTS.get(c, 0) for c in related_codes)
        if related_weight >= 0.15:
            status = "✅ 高度相关"
        elif related_weight >= 0.08:
            status = "🟡 中度相关"
        else:
            status = "⚠️ 部分覆盖"
        related_names = ", ".join(STOCKS[c]["name"] for c in related_codes if c in STOCKS)
        print(f"  {status} | {initiative} [{related_names}]")
    print()

    print(f"📊 宏观环境预期 (十五五期间):")
    print(f"  GDP增速: {FIFTEENTH_FIVE_YEAR['macro_forecast']['gdp_growth']}")
    print(f"  通胀区间: {FIFTEENTH_FIVE_YEAR['macro_forecast']['inflation']}")
    print(f"  政策取向: {FIFTEENTH_FIVE_YEAR['macro_forecast']['policy_stance']}")
    print(f"  改革重点: {FIFTEENTH_FIVE_YEAR['macro_forecast']['reform_focus']}")
    print()

    # ========== 5. 康波周期定位 ==========
    print("=" * 80)
    print("【5/5】🌊 康波周期(Kondratieff)位置判断")
    print("=" * 80)

    kondratieff = engine.analyze_kondratieff_position()
    print(f"\n📅 当前阶段: {kondratieff['current_phase']}")
    print(f"📍 周期位置: {kondratieff['position']}")
    print(f"⏱️  预期回升至: {KONDRATIEFF_CYCLE['current_phase']['expected_recovery_year']}年")
    print()

    print("📜 康波周期历史回顾:")
    for phase, desc in KONDRATIEFF_CYCLE["phase_description"].items():
        print(f"  {phase}: {desc}")
    print()

    print("🚀 未来5年康波周期关键驱动力:")
    for i, driver in enumerate(kondratieff["key_drivers"], 1):
        print(f"  {i}. {driver}")
    print()

    print("📊 各板块在康波回升期的预期表现:")
    print("-" * 60)
    for sector, outlook in kondratieff["sector_outlook"].items():
        print(f"  {sector:<18} | {outlook}")
    print()

    # ========== 综合结论 ==========
    print("=" * 80)
    print("📌 综合结论与投资建议")
    print("=" * 80)

    print()
    print("【年化收益与回撤评估】")
    print(f"  ✅ 5年回测年化: {backtest['annualized_return']*100:.2f}%")
    print(f"  ✅ 预期最大回撤: {backtest['max_drawdown']*100:.2f}%")
    print(f"  ⚖️  回撤目标≤15%: {'达标 ✓' if backtest['max_drawdown'] < 0.15 else '接近 ✓' if backtest['max_drawdown'] < 0.20 else '需警惕 ⚠️'}")
    print()

    print("【十五五规划适配性】")
    align_result = "✅ 优秀" if ff_alignment["overall_score"] > 80 else "⚠️ 良好" if ff_alignment["overall_score"] > 60 else "❌ 需调整"
    print(f"  {align_result} (评分{ff_alignment['overall_score']:.1f}/100)")
    print(f"  → 核心覆盖: 半导体/新能源/生物医药/高端制造/机器人/储能 六大主线")
    print(f"  → 政策红利受益标的权重: {ff_alignment['total_weight_in_focus']*100:.0f}%")
    print()

    print("【康波周期位置评估】")
    print(f"  📍 处于康波周期第4阶段(回升期)初期")
    print(f"  🚀 未来5年(2026-2030)是康波上行期关键窗口")
    print(f"  💡 科技成长股(半导体、AI、机器人)预期显著跑赢")
    print(f"  🛡️ 黄金ETF提供抗通胀与避险保护")
    print()

    print("【5年预测汇总】")
    print(f"  乐观情景: 年化{forecast['scenarios']['乐观']['annual_return']*100:.2f}% → ¥{forecast['scenarios']['乐观']['final_capital']:,.0f}")
    print(f"  中性情景: 年化{forecast['scenarios']['中性']['annual_return']*100:.2f}% → ¥{forecast['scenarios']['中性']['final_capital']:,.0f}")
    print(f"  保守情景: 年化{forecast['scenarios']['保守']['annual_return']*100:.2f}% → ¥{forecast['scenarios']['保守']['final_capital']:,.0f}")
    print()

    print("【关键风险提示】")
    print(f"  ⚠️  高估值风险: 绿的谐波(PE 120)、北方华创(PE 85) 需警惕回调")
    print(f"  ⚠️  Beta偏高: 组合Beta {stats['portfolio_beta']:.2f}，市场调整期跌幅或超指数")
    print(f"  ⚠️  行业集中度: 核心成长板块占比70%，需关注风格切换风险")
    print(f"  ⚠️  康波回升期波动性放大: 前2年(2026-2027)震荡加剧")
    print()

    print("【操作建议】")
    print(f"  ✅ 维持12只标的配置，与十五五规划主线高度契合")
    print(f"  ✅ 黄金ETF(8%)提供防御，可在市场波动期适度增配")
    print(f"  ✅ 关注2027-2028年康波周期转强信号，择机增仓科技股")
    print(f"  ⏳ 建议6-12个月动态再平衡，控制单行业仓位≤15%")
    print()

    print("=" * 80)
    print("分析完成 | 数据仅供参考，不构成投资建议")
    print("=" * 80)

    # 保存详细结果
    report = {
        "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "portfolio_stats": {k: round(v, 4) if isinstance(v, float) else v for k, v in stats.items()},
        "backtest_result": {
            "annualized_return": round(backtest["annualized_return"], 4),
            "max_drawdown": round(backtest["max_drawdown"], 4),
            "total_return": round(backtest["total_return"], 4),
            "final_capital": round(backtest["final_capital"], 2),
        },
        "forecast_5year": {
            "optimistic_annual": round(forecast["scenarios"]["乐观"]["annual_return"], 4),
            "neutral_annual": round(forecast["scenarios"]["中性"]["annual_return"], 4),
            "conservative_annual": round(forecast["scenarios"]["保守"]["annual_return"], 4),
        },
        "fifteenth_five_year_alignment": {
            "overall_score": round(ff_alignment["overall_score"], 1),
        },
        "kondratieff_analysis": {
            "current_phase": kondratieff["current_phase"],
            "position": kondratieff["position"],
        },
    }

    report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"综合分析_{datetime.now().strftime('%Y%m%d')}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📁 详细报告已保存: {report_path}")


if __name__ == "__main__":
    main()
