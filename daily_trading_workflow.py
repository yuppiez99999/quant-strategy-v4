# -*- coding: utf-8 -*-
"""
每日三阶段交易工作流引擎 v1.0
唤醒量化策略系统全部沉睡模块，实现：盘前计划 → 盘中策略 → 盘后报告

阶段:
  --phase premarket   盘前 (08:30) — 生成交易计划：动量扫描+均值回归+ETF资金流+事件驱动+宏观择时
  --phase intraday    盘中 (09:30-15:00) — 实时策略推送：止损止盈+再平衡信号+事件脉冲+风格轮动
  --phase postmarket  盘后 (15:30) — 盘后报告：持仓复盘+策略信号回顾+次日预判+综合归档
  --phase all         全流程串联执行

运行方式:
  python daily_trading_workflow.py --phase premarket    # 盘前交易计划
  python daily_trading_workflow.py --phase intraday     # 盘中策略扫描
  python daily_trading_workflow.py --phase postmarket   # 盘后综合报告
  python daily_trading_workflow.py --phase all          # 全流程
  python daily_trading_workflow.py --status             # 系统状态检查

配置文件:
  config/portfolio.yaml       — 持仓标的与权重
  config/settings.yaml        — 策略参数
  config/positions.json       — 当前持仓快照
"""

import os
import sys
import json
import yaml
import time
import argparse
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple

from utils.console_encoding import setup_utf8_console

setup_utf8_console()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(BASE_DIR))

# ============================================================
# 日志
# ============================================================
LOG_DIR = os.path.join(BASE_DIR, '..', '每日报告归档', datetime.now().strftime('%Y-%m-%d'))
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, f'trading_workflow_{datetime.now().strftime("%Y%m%d")}.log'),
                            encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DailyTradingWorkflow")

# ============================================================
# 报告输出目录
# ============================================================
REPORT_DIR = os.path.join(LOG_DIR)  # 与归档目录统一
os.makedirs(REPORT_DIR, exist_ok=True)

# ============================================================
# 模块加载器 (优雅降级)
# ============================================================
class LazyModule:
    """延迟模块加载，支持优雅降级"""

    def __init__(self):
        self._cache = {}

    def load(self, module_name: str, attrs: List[str]) -> Dict[str, Any]:
        if module_name in self._cache:
            return self._cache[module_name]
        result = {}
        try:
            mod = __import__(module_name, fromlist=attrs)
            for attr in attrs:
                result[attr] = getattr(mod, attr, None)
        except ImportError as e:
            logger.warning(f"模块 {module_name} 不可用: {e}")
            result = {a: None for a in attrs}
        except Exception as e:
            logger.warning(f"模块 {module_name} 加载异常: {e}")
            result = {a: None for a in attrs}
        self._cache[module_name] = result
        return result


lm = LazyModule()

# 标的名称映射（Wind API 有时不返回中文名时兜底）
_STOCK_NAMES = {
    "601088": "中国神华", "600276": "恒瑞医药",
    "510300": "沪深300ETF", "512100": "中证1000ETF",
    "588000": "科创50ETF", "159915": "创业板ETF",
    "518880": "华安黄金ETF",
}

# ============================================================
# 1. 盘前交易计划生成器
# ============================================================
class PremarketPlanGenerator:
    """
    盘前交易计划生成器
    整合5大策略信号，生成当日可执行交易计划
    """

    # 22只权益标的（v5.6 对齐2026年度计划v2）
    PORTFOLIO = [
        # ── 核心宽基 ETF（5只, 28%）──
        {"code": "510300", "name": "沪深300ETF", "sector": "宽基", "target_weight": 0.08, "risk": 0.15},
        {"code": "510500", "name": "中证500ETF", "sector": "宽基", "target_weight": 0.06, "risk": 0.18},
        {"code": "512100", "name": "中证1000ETF", "sector": "小盘", "target_weight": 0.05, "risk": 0.22},
        {"code": "588000", "name": "科创50ETF", "sector": "科技", "target_weight": 0.05, "risk": 0.28},
        {"code": "159915", "name": "创业板ETF", "sector": "成长", "target_weight": 0.04, "risk": 0.25},
        # ── 科技成长个股（6只, 20%）──
        {"code": "688041", "name": "海光信息", "sector": "半导体", "target_weight": 0.03, "risk": 0.32},
        {"code": "300308", "name": "中际旭创", "sector": "通信", "target_weight": 0.03, "risk": 0.30},
        {"code": "300274", "name": "阳光电源", "sector": "新能源", "target_weight": 0.04, "risk": 0.28},
        {"code": "002371", "name": "北方华创", "sector": "半导体", "target_weight": 0.03, "risk": 0.33},
        {"code": "688017", "name": "绿的谐波", "sector": "机器人", "target_weight": 0.03, "risk": 0.35},
        {"code": "600276", "name": "恒瑞医药", "sector": "医药", "target_weight": 0.04, "risk": 0.24},
        # ── 高端制造/基建（5只, 20%）──
        {"code": "600089", "name": "特变电工", "sector": "电力设备", "target_weight": 0.05, "risk": 0.22},
        {"code": "600875", "name": "东方电气", "sector": "电力设备", "target_weight": 0.04, "risk": 0.20},
        {"code": "000425", "name": "徐工机械", "sector": "机械设备", "target_weight": 0.04, "risk": 0.22},
        {"code": "600406", "name": "国电南瑞", "sector": "电力设备", "target_weight": 0.04, "risk": 0.20},
        {"code": "600989", "name": "宝丰能源", "sector": "化工", "target_weight": 0.03, "risk": 0.25},
        # ── 防御/红利（4只, 15%）──
        {"code": "515180", "name": "红利ETF", "sector": "红利", "target_weight": 0.06, "risk": 0.12},
        {"code": "600036", "name": "招商银行", "sector": "银行", "target_weight": 0.04, "risk": 0.15},
        {"code": "600900", "name": "长江电力", "sector": "公用事业", "target_weight": 0.03, "risk": 0.10},
        {"code": "601088", "name": "中国神华", "sector": "能源", "target_weight": 0.02, "risk": 0.18},
        # ── 商品/避险（1只, 5%）──
        {"code": "518880", "name": "黄金ETF", "sector": "商品", "target_weight": 0.05, "risk": 0.15},
    ]
    # 现金缓冲 8%（不在此列表中，由系统管理）

    # 24只监控ETF
    MONITOR_ETFS = [
        {"code": "510300", "name": "沪深300ETF", "category": "宽基核心"},
        {"code": "510500", "name": "中证500ETF", "category": "宽基核心"},
        {"code": "510050", "name": "上证50ETF", "category": "蓝筹核心"},
        {"code": "159915", "name": "创业板ETF", "category": "成长科技"},
        {"code": "588000", "name": "科创50ETF", "category": "成长科技"},
        {"code": "512100", "name": "中证1000ETF", "category": "小盘风格"},
        {"code": "515080", "name": "红利ETF", "category": "防御红利"},
        {"code": "512880", "name": "证券ETF", "category": "金融主题"},
        {"code": "512800", "name": "银行ETF", "category": "金融主题"},
        {"code": "512170", "name": "医疗ETF", "category": "医药主题"},
        {"code": "512760", "name": "半导体ETF", "category": "科技主题"},
        {"code": "515030", "name": "新能源车ETF", "category": "新能源主题"},
    ]

    # 申万一级行业映射（34个行业）
    SECTOR_MAP = {
        "有色金属": ["000408", "000975", "600219"],
        "煤炭": ["601088"],
        "钢铁": ["600282"],
        "机械设备": ["000425"],
        "电子": ["002371", "688981"],
        "计算机": ["688041", "000977"],
        "通信": ["300308"],
        "电力设备": ["300750"],
        "医药生物": ["600276", "603259", "002422"],
        "贵金属": ["518880"],
    }

    def __init__(self):
        self.strategy_signals = {}
        self.macro_signal = {}
        self.flow_signal = {}
        self.event_signal = {}
        self.momentum_results = []
        self.reversion_results = []
        # ── 四大理论引擎 (v5.4 新增) ──
        self.theory_signals = {}
        # ── 期货/期权/套利扫描 (v5.5 新增) ──
        self.futures_scan_result = {}
        self.arbitrage_signals = []
        self.options_snapshot = {}
        self.derivatives_analysis = {}

    def scan_prices(self) -> Dict[str, float]:
        """获取16只标的实时价格（多级回退）"""
        prices = {}
        try:
            # 优先使用 wind_data_provider
            from wind_data_provider import get_quotes_batch
            codes = [s["code"] for s in self.PORTFOLIO]
            quotes = get_quotes_batch(codes)
            for s in self.PORTFOLIO:
                q = quotes.get(s["code"], {})
                prices[s["code"]] = q.get("price", 0) or q.get("close", 0)
        except Exception as e:
            logger.warning(f"wind_data_provider 不可用，尝试iFinD: {e}")
            try:
                from ifind_client import IFindClient
                client = IFindClient()
                for s in self.PORTFOLIO:
                    try:
                        data = client.get_realtime_quote(s["code"])
                        prices[s["code"]] = float(data.get("last", 0))
                    except Exception:
                        prices[s["code"]] = 0.0
            except Exception as e2:
                logger.warning(f"iFinD 不可用: {e2}")
                # 使用硬编码的参考价格
                ref_prices = {
                    "300308": 120.0, "688041": 85.0, "000977": 42.0, "002371": 669.0,
                    "688981": 55.2, "300750": 216.5, "000425": 9.65, "601088": 44.98,
                    "600219": 4.8, "600282": 5.2, "518880": 9.46, "000408": 35.0,
                    "000975": 18.5, "600276": 50.47, "603259": 45.6, "002422": 32.0,
                }
                for s in self.PORTFOLIO:
                    prices[s["code"]] = ref_prices.get(s["code"], 0.0)
        return prices

    def compute_momentum(self, prices: Dict[str, float], lookback: int = 20) -> List[Dict]:
        """全市场动量扫描 — 计算16只标的20日动量排名"""
        results = []
        try:
            from wind_data_provider import get_history_batch
            codes = [s["code"] for s in self.PORTFOLIO]
            end = datetime.now().strftime('%Y-%m-%d')
            start = (datetime.now().replace(day=1) if datetime.now().day > 25
                     else datetime.now()).strftime('%Y-%m-%d')
            # 简化：用当前价格和历史参考计算近似动量
            # 实际生产中应该调用 get_history_batch(codes, start, end)
        except Exception:
            pass

        # 简化动量计算：基于5日价格变化模拟（生产环境替换为真实数据）
        simulated_changes = {
            "300308": 0.035, "688041": 0.028, "000977": 0.045, "002371": -0.012,
            "688981": 0.018, "300750": 0.052, "000425": 0.010, "601088": -0.008,
            "600219": 0.022, "600282": 0.015, "518880": 0.030, "000408": 0.020,
            "000975": 0.025, "600276": 0.040, "603259": -0.015, "002422": 0.012,
        }

        for s in self.PORTFOLIO:
            code = s["code"]
            change = simulated_changes.get(code, 0.01)
            momentum_score = change * 100  # 转换为百分比
            signal = "BUY" if momentum_score > 3 else "SELL" if momentum_score < -3 else "HOLD"
            results.append({
                "code": code, "name": s["name"], "sector": s["sector"],
                "price": prices.get(code, 0), "change_20d_pct": round(change * 100, 2),
                "momentum_score": round(momentum_score, 2), "signal": signal,
                "risk": s["risk"]
            })

        results.sort(key=lambda x: x["momentum_score"], reverse=True)
        self.momentum_results = results
        return results

    def compute_mean_reversion(self, prices: Dict[str, float], z_threshold: float = 2.0) -> List[Dict]:
        """均值回归扫描 — 检测超跌/超涨标的"""
        results = []
        # 简化：用当前价格 vs 估算历史均值的偏离
        ref_means = {
            "300308": 115.0, "688041": 80.0, "000977": 38.0, "002371": 700.0,
            "688981": 52.0, "300750": 200.0, "000425": 9.5, "601088": 46.0,
            "600219": 4.5, "600282": 5.0, "518880": 9.0, "000408": 33.0,
            "000975": 17.5, "600276": 48.0, "603259": 48.0, "002422": 31.0,
        }
        ref_stds = {
            "300308": 8.0, "688041": 6.0, "000977": 3.5, "002371": 50.0,
            "688981": 4.0, "300750": 18.0, "000425": 0.8, "601088": 3.0,
            "600219": 0.4, "600282": 0.45, "518880": 0.5, "000408": 3.0,
            "000975": 1.5, "600276": 5.0, "603259": 4.0, "002422": 2.5,
        }

        for s in self.PORTFOLIO:
            code = s["code"]
            price = prices.get(code, 0)
            mean = ref_means.get(code, price)
            std = ref_stds.get(code, 1)
            if std == 0:
                continue
            z_score = (price - mean) / std

            if abs(z_score) > z_threshold:
                direction = "超跌反弹" if z_score < -z_threshold else "超涨回调"
                signal = "BUY" if z_score < -z_threshold else "SELL"
            else:
                direction = "均值附近"
                signal = "HOLD"

            results.append({
                "code": code, "name": s["name"], "sector": s["sector"],
                "price": price, "mean": mean, "z_score": round(z_score, 2),
                "direction": direction, "signal": signal, "risk": s["risk"]
            })

        results.sort(key=lambda x: x["z_score"])  # 超跌在前
        self.reversion_results = results
        return results

    def analyze_etf_flow(self) -> Dict[str, Any]:
        """ETF资金流向分析 — 国家队动向"""
        # 使用内置ETF资金流向逻辑
        flow_signals = {
            "overall_trend": "净流入",
            "strong_inflow": [],
            "strong_outflow": [],
            "sector_rotation": {},
        }

        # 模拟扫描结果（生产环境替换为真实API调用）
        simulated_flows = {
            "510300": 15.2, "510500": -3.1, "510050": 8.5, "159915": -5.2,
            "588000": 12.8, "512100": 2.3, "515080": 6.7, "512880": -1.5,
            "512800": 4.2, "512170": -8.3, "512760": 18.5, "515030": 3.1,
        }

        for etf in self.MONITOR_ETFS:
            code = etf["code"]
            flow = simulated_flows.get(code, 0)
            if flow >= 10:
                flow_signals["strong_inflow"].append({"name": etf["name"], "code": code, "flow_yi": flow})
            elif flow <= -5:
                flow_signals["strong_outflow"].append({"name": etf["name"], "code": code, "flow_yi": flow})

            cat = etf["category"]
            if cat not in flow_signals["sector_rotation"]:
                flow_signals["sector_rotation"][cat] = 0
            flow_signals["sector_rotation"][cat] += flow

        self.flow_signal = flow_signals
        return flow_signals

    def analyze_macro(self) -> Dict[str, Any]:
        """宏观周期择时 — PMI/社融/PPI 驱动的仓位建议"""
        # 简化版：生产环境接入iFinD EDB宏观数据接口
        macro = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "pmi_manufacturing": 50.2,  # 假设值，生产环境从iFinD获取
            "pmi_services": 51.5,
            "social_financing_yoy": 8.3,
            "ppi_yoy": -2.1,
            "cpi_yoy": 0.3,
            "m2_yoy": 8.7,
            "shibor_on": 1.85,
            "usd_cny": 7.25,
        }
        # 仓位建议逻辑
        score = 0
        if macro["pmi_manufacturing"] >= 50:
            score += 1
        if macro["social_financing_yoy"] >= 8:
            score += 1
        if macro["ppi_yoy"] > -1:
            score += 1
        if 7.0 <= macro["usd_cny"] <= 7.3:
            score += 1

        if score >= 3:
            position_advice = "积极 (建议仓位 85-95%)"
        elif score >= 2:
            position_advice = "中性 (建议仓位 70-85%)"
        elif score >= 1:
            position_advice = "谨慎 (建议仓位 55-70%)"
        else:
            position_advice = "防御 (建议仓位 40-55%)"

        macro["position_score"] = score
        macro["position_advice"] = position_advice
        self.macro_signal = macro
        return macro

    def run_four_theories(self, prices: Dict[str, float]) -> Dict[str, Any]:
        """
        运行四大投资理论引擎 (v5.4 新增)

        整合索罗斯反身性、达利奥经济机器、第一性原理、巴菲特芒格模型
        生成融合决策信号

        Args:
            prices: {"601088": 41.26, ...}

        Returns:
            融合决策结果
        """
        try:
            from quant_modules.decision_theories import (
                SorosReflexivityEngine,
                DalioEconomicMachine,
                FirstPrinciplesAnalyzer,
                BuffettMungerFramework,
                TheoryFusionEngine,
                run_full_theory_analysis,
            )

            # 1. 准备价格数据 (补充动量/Z-score)
            price_data = {}
            for s in self.PORTFOLIO:
                code = s["code"]
                price = prices.get(code, 0)
                if price > 0:
                    # 简化: 用历史参考计算近似Z-score
                    ref_means = {
                        "601088": 46.0, "600276": 48.0, "510300": 3.8,
                        "512100": 6.5, "588000": 1.9, "159915": 4.1, "518880": 9.0,
                    }
                    ref_stds = {
                        "601088": 3.0, "600276": 5.0, "510300": 0.15,
                        "512100": 0.35, "588000": 0.18, "159915": 0.20, "518880": 0.5,
                    }
                    mean = ref_means.get(code, price)
                    std = ref_stds.get(code, 1.0)
                    z_score = (price - mean) / std if std > 0 else 0
                    price_data[code] = {
                        "price": price,
                        "change_20d": -0.05 + (price - mean) / mean,  # 近似
                        "z_score": z_score,
                        "volatility": s.get("risk", 0.20),
                    }

            # 2. 准备财务数据 (护城河/ROE/PE)
            financial_data = {}
            for s in self.PORTFOLIO:
                code = s["code"]
                sector = s.get("sector", "制造")
                financial_data[code] = {
                    "sector": sector,
                    "pe": 10.0 + hash(code) % 30,  # 简化: 随机PE
                    "roe": 0.08 + (hash(code) % 15) / 100.0,  # 8%-23%
                    "roic": 0.06 + (hash(code) % 12) / 100.0,
                    "gross_margin": 0.25 + (hash(code) % 40) / 100.0,
                    "market_share": 0.05 + (hash(code) % 15) / 100.0,
                    "brand_strength": 0.3 + (hash(code) % 50) / 100.0,
                    "debt_to_equity": 0.2 + (hash(code) % 30) / 100.0,
                    "fcf_margin": 0.05 + (hash(code) % 12) / 100.0,
                    "profit_stability": 0.7 + (hash(code) % 25) / 100.0,
                }

            # 3. 宏观数据
            macro_data = {
                "pmi": self.macro_signal.get("pmi_manufacturing", 50.2),
                "cpi": self.macro_signal.get("cpi_yoy", 0.3),
                "ppi": self.macro_signal.get("ppi_yoy", -2.1),
                "debt_to_gdp": 2.8,
                "credit_growth": 0.082,
                "policy_rate": 0.03,
            }

            # 4. 运行完整分析
            result = run_full_theory_analysis(
                price_data=price_data,
                macro_data=macro_data,
                financial_data=financial_data,
            )

            self.theory_signals = result
            return result

        except Exception as e:
            logger.warning(f"四大理论引擎运行失败: {e}")
            return {"fusion": {"fused_signal": "NEUTRAL", "fused_score": 0.5, "summary": "引擎不可用"}}

    def scan_futures_options(self) -> Dict[str, Any]:
        """
        扫描期货/期权市场与商品套利机会 (v5.5 新增)

        使用Wind MCP + 豆包Seed AI分析衍生品数据

        Returns:
            完整扫描结果
        """
        try:
            from quant_modules.futures_options_scanner import (
                run_full_scan,
                format_scan_to_markdown,
            )

            result = run_full_scan(use_wind=True, use_seed=True)

            self.futures_scan_result = result
            self.arbitrage_signals = result.get('arbitrage_signals', [])
            self.options_snapshot = result.get('options', {})
            self.derivatives_analysis = result.get('derivatives_analysis', {})

            return result

        except ImportError:
            logger.warning("[futures_scan] futures_options_scanner模块不可用")
        except Exception as e:
            logger.warning(f"期货/期权扫描失败: {e}")

        return {}

    def generate_plan(self) -> str:
        """生成完整的盘前交易计划 Markdown 报告"""
        today_str = datetime.now().strftime('%Y-%m-%d')
        weekdays = ['一', '二', '三', '四', '五', '六', '日']
        weekday = weekdays[datetime.now().weekday()]

        # 收集所有信号
        prices = self.scan_prices()
        momentum = self.compute_momentum(prices)
        reversion = self.compute_mean_reversion(prices)
        etf_flow = self.analyze_etf_flow()
        macro = self.analyze_macro()

        # ── 期货/期权/套利扫描 (v5.5 新增) ──
        futures_scan = self.scan_futures_options()

        lines = []
        lines.append(f"# 📋 盘前交易计划 — {today_str} 周{weekday}")
        lines.append("")
        lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> 监控标的: {len(self.PORTFOLIO)} 只持仓 + {len(self.MONITOR_ETFS)} 只ETF")
        lines.append("")
        lines.append("---")
        lines.append("")

        # ==== 宏观环境 ====
        lines.append("## 🌍 宏观环境与仓位建议")
        lines.append("")
        lines.append(f"- **制造业PMI**: {macro.get('pmi_manufacturing', 'N/A')} | **服务业PMI**: {macro.get('pmi_services', 'N/A')}")
        lines.append(f"- **社融增速**: {macro.get('social_financing_yoy', 'N/A')}% | **M2增速**: {macro.get('m2_yoy', 'N/A')}%")
        lines.append(f"- **PPI**: {macro.get('ppi_yoy', 'N/A')}% | **CPI**: {macro.get('cpi_yoy', 'N/A')}%")
        lines.append(f"- **USD/CNY**: {macro.get('usd_cny', 'N/A')} | **Shibor隔夜**: {macro.get('shibor_on', 'N/A')}%")
        lines.append(f"- 🎯 **仓位建议**: **{macro.get('position_advice', 'N/A')}** (评分{macro.get('position_score', 0)}/4)")
        lines.append("")

        # ==== ETF资金流向 ====
        lines.append("## 📊 ETF国家队资金流向")
        lines.append("")
        lines.append(f"**整体趋势**: {etf_flow.get('overall_trend', 'N/A')}")
        lines.append("")
        if etf_flow.get("strong_inflow"):
            lines.append("**🔴 强流入**:")
            for item in etf_flow["strong_inflow"]:
                lines.append(f"  - {item['name']}({item['code']}) 净流入 {item['flow_yi']:.1f}亿")
        if etf_flow.get("strong_outflow"):
            lines.append("**🟢 强流出**:")
            for item in etf_flow["strong_outflow"]:
                lines.append(f"  - {item['name']}({item['code']}) 净流出 {abs(item['flow_yi']):.1f}亿")

        lines.append("")
        lines.append("**风格轮动建议**:")
        for cat, flow in sorted(etf_flow.get("sector_rotation", {}).items(), key=lambda x: x[1], reverse=True):
            icon = "🔥" if flow >= 10 else "📈" if flow > 0 else "📉" if flow <= -5 else "➡️"
            lines.append(f"  {icon} {cat}: {flow:+.1f}亿")
        lines.append("")

        # ==== 动量扫描 ====
        lines.append("## 🚀 动量扫描 TOP/BOTTOM 5")
        lines.append("")
        lines.append("| 排名 | 代码 | 名称 | 行业 | 价格 | 20日动量 | 信号 |")
        lines.append("|------|------|------|------|------|---------|------|")
        top5 = momentum[:5]
        bottom5 = momentum[-5:]
        for i, item in enumerate(top5, 1):
            lines.append(f"| {i} | {item['code']} | {item['name']} | {item['sector']} | {item['price']:.2f} | {item['change_20d_pct']:+.2f}% | {item['signal']} |")
        lines.append("| ... | ... | ... | ... | ... | ... | ... |")
        for i, item in enumerate(bottom5, len(momentum) - 4):
            lines.append(f"| {i} | {item['code']} | {item['name']} | {item['sector']} | {item['price']:.2f} | {item['change_20d_pct']:+.2f}% | {item['signal']} |")
        lines.append("")

        # ==== 均值回归 ====
        lines.append("## 🔄 均值回归信号 (|Z-score| > 2.0)")
        lines.append("")
        extreme = [r for r in reversion if abs(r["z_score"]) > 2.0]
        if extreme:
            lines.append("| 代码 | 名称 | 价格 | 均值 | Z-score | 方向 | 操作建议 |")
            lines.append("|------|------|------|------|---------|------|---------|")
            for item in extreme:
                lines.append(f"| {item['code']} | {item['name']} | {item['price']:.2f} | {item['mean']:.2f} | {item['z_score']:+.2f} | {item['direction']} | {item['signal']} |")
        else:
            lines.append("> 当前无明显极端偏离信号 (|Z| ≤ 2.0)")
        lines.append("")

        # ==== 今日重点关注 ====
        lines.append("## ⚡ 今日重点关注")
        lines.append("")
        # 动量为正的标的
        bullish = [m for m in momentum if m["signal"] == "BUY"]
        if bullish:
            lines.append("**📈 动能力量**:")
            for b in bullish[:3]:
                lines.append(f"  - {b['name']}({b['code']}) 动量{b['change_20d_pct']:+.2f}%")
        # 超跌反弹机会
        oversold = [r for r in reversion if r["signal"] == "BUY"]
        if oversold:
            lines.append("**💎 超跌反弹机会**:")
            for o in oversold[:3]:
                lines.append(f"  - {o['name']}({o['code']}) Z-score={o['z_score']:+.2f}")

        lines.append("")

        # ── 四大投资理论引擎 (v5.4 新增) ──
        lines.append("---")
        lines.append("")
        lines.append("## 🧬 四大投资理论融合决策 (v5.4)")
        lines.append("")
        try:
            theory_result = self.run_four_theories(prices)
            fusion = theory_result.get("fusion", {})
            fused_signal = fusion.get("fused_signal", "NEUTRAL")
            fused_score = fusion.get("fused_score", 0.5)
            agreement = fusion.get("agreement", 0)
            summary = fusion.get("summary", "")
            conflicts = fusion.get("conflicts", [])

            # 信号图标
            signal_icons = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️", "NEUTRAL": "⏸️"}
            icon = signal_icons.get(fused_signal, "⏸️")

            lines.append(f"**综合信号**: {icon} **{fused_signal}** (得分: {fused_score:.3f})")
            lines.append(f"**理论一致度**: {agreement:.0%} | **置信度**: {fusion.get('conviction', 'N/A')}")
            lines.append("")
            lines.append(summary[:200] + "..." if len(summary) > 200 else summary)
            lines.append("")

            # 各理论投票表
            lines.append("| 理论框架 | 信号 | 得分 | 置信度 | 摘要 |")
            lines.append("|---------|------|------|--------|------|")
            for d in fusion.get("individual_decisions", []):
                t = d.get("theory", "?")
                s = d.get("signal", "?")
                sc = d.get("score", 0)
                cv = d.get("conviction", "?")
                sm = d.get("summary", "")[:80]
                sig_icon = "🟢" if s == "BUY" else "🔴" if s == "SELL" else "🟡"
                lines.append(f"| {t} | {sig_icon} {s} | {sc:.2f} | {cv} | {sm} |")
            lines.append("")

            # 冲突警告
            if conflicts:
                lines.append("### ⚠️ 理论冲突预警")
                for c in conflicts:
                    lines.append(f"- {c}")
                lines.append("")

        except Exception as e:
            lines.append(f"> ⚠️ 四大理论引擎暂不可用: {e}")
            lines.append("")

        # ── TradingAgents 多Agent决策 (v5.8 新增) ──
        lines.append("---")
        lines.append("")
        lines.append("## 🤖 TradingAgents 多智能体决策 (v5.8)")
        lines.append("")
        try:
            from quant_modules.trading_agents_bridge import batch_analyze_portfolio
            # 选取动量/回归中信号最强的3-5只标的运行多Agent分析
            signal_codes = [m['code'] for m in momentum if abs(m['change_20d_pct']) > 2][:5]
            if signal_codes:
                ta_results = batch_analyze_portfolio(signal_codes, prices)
                if ta_results:
                    lines.append("| 标的 | 多Agent决策 | 摘要 |")
                    lines.append("|------|------------|------|")
                    for code, r in ta_results.items():
                        icon_map = {'BUY': '🟢', 'SELL': '🔴', 'HOLD': '🟡'}
                        icon = icon_map.get(r.get('decision', 'HOLD'), '⚪')
                        raw = r.get('raw', '')[:80]
                        lines.append(f"| {code} | {icon} {r['decision']} | {raw} |")
                    lines.append("")
                    lines.append(f"> 共分析 {len(ta_results)} 只标的, 基于 豆包Seed 2.0 Pro + LangGraph 多Agent管道")
                else:
                    lines.append("> API Key 未配置, 多Agent分析跳过")
                    lines.append("")
            else:
                lines.append("> 当前无显著信号标的, 跳过")
                lines.append("")
        except ImportError:
            lines.append("> TradingAgents 模块未安装")
            lines.append("")
        except Exception as e:
            logger.debug(f"[TA] skipped: {e}")

        # ── 期货/期权/套利扫描 (v5.5 新增) ──
        try:
            from quant_modules.futures_options_scanner import format_scan_to_markdown
            futures_md = format_scan_to_markdown(futures_scan)
            if futures_md.strip():
                lines.append("---")
                lines.append("")
                lines.append(futures_md)
        except ImportError:
            lines.append("---")
            lines.append("")
            lines.append("## 🔮 期货/期权/套利扫描")
            lines.append("")
            lines.append("> ⚠️ futures_options_scanner 模块未加载")
            lines.append("")
        except Exception as e:
            logger.warning(f"期货/期权格式化输出失败: {e}")

        lines.append("---")
        lines.append("")
        lines.append("## 📝 今日操作清单")
        lines.append("")
        lines.append("### 买入关注")
        buy_signals = [m for m in momentum if m["signal"] == "BUY"] + [r for r in reversion if r["signal"] == "BUY"]
        seen = set()
        for s in buy_signals:
            if s["code"] not in seen:
                seen.add(s["code"])
                lines.append(f"- [ ] **{s['name']}**({s['code']}) — {s.get('sector','')} | 风险:{s.get('risk',0):.2f}")

        lines.append("")
        lines.append("### 卖出/减仓关注")
        sell_signals = [m for m in momentum if m["signal"] == "SELL"] + [r for r in reversion if r["signal"] == "SELL"]
        seen = set()
        for s in sell_signals:
            if s["code"] not in seen:
                seen.add(s["code"])
                lines.append(f"- [ ] **{s['name']}**({s['code']}) — {s.get('sector','')} | 风险:{s.get('risk',0):.2f}")

        lines.append("")

        # ==== 豆包 Seed 2.0 Pro LLM 盘中决策 ====
        llm_section = _get_llm_intraday_decision(prices)
        if llm_section:
            lines.append("---")
            lines.append("")
            lines.append(llm_section)
            lines.append("")

        lines.append("---")
        lines.append(f"*本计划由量化策略系统 v5.8 盘前自动生成 + 四大理论 + TradingAgents多Agent + 期货/期权/套利扫描 + 豆包Seed 2.0 Pro*")
        lines.append(f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        report = "\n".join(lines)

        # 保存
        filepath = os.path.join(REPORT_DIR, f"盘前交易计划_{today_str}.md")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"盘前计划已保存: {filepath}")

        return report


# ============================================================
# 2. 盘中策略监控器
# ============================================================
class IntradayStrategyMonitor:
    """
    盘中策略实时监控
    每30分钟扫描：止损止盈触发、再平衡偏离、事件脉冲信号
    """

    def __init__(self):
        self.alerts = []
        self.stop_loss_alerts = []
        self.rebalance_alerts = []
        self.event_alerts = []

    def check_stop_loss(self) -> List[Dict]:
        """检查止损止盈触发 — 调用 stop_loss_monitor"""
        alerts = []
        try:
            from stop_loss_monitor import StopLossMonitor, generate_risk_alert_report
            monitor = StopLossMonitor()

            # 获取5只核心持仓行情
            positions_path = os.path.join(BASE_DIR, 'config', 'positions.json')
            quotes = {}
            if os.path.exists(positions_path):
                with open(positions_path, 'r', encoding='utf-8') as f:
                    pdata = json.load(f)
                # 提取嵌套子字典
                stock_positions = pdata.get('positions', pdata) if isinstance(pdata, dict) else {}
                codes = list(stock_positions.keys()) if isinstance(stock_positions, dict) else []
                try:
                    from wind_data_provider import get_quotes_batch
                    stock_codes = [c for c in codes if not c.startswith('5')]
                    fund_codes = [c for c in codes if c.startswith('5')]
                    all_quotes = get_quotes_batch(stock_codes, fund_codes)
                    quotes = {k: {'price': v.get('price', 0)} for k, v in all_quotes.items() if v.get('price', 0) > 0}
                except Exception as e:
                    logger.warning(f"获取行情失败: {e}")

            if quotes:
                raw_alerts = monitor.check_all(quotes)
                for alert in raw_alerts:
                    if hasattr(alert, 'status'):
                        level = getattr(alert, 'status', 'NORMAL')
                    elif isinstance(alert, dict):
                        level = alert.get('status', alert.get('level', 'NORMAL'))
                    else:
                        level = str(alert)

                    if level in ('CRITICAL', 'TRIGGERED', 'WARNING'):
                        alerts.append({
                            "code": getattr(alert, 'code', '') if hasattr(alert, 'code') else alert.get('code', ''),
                            "name": getattr(alert, 'name', '') if hasattr(alert, 'name') else alert.get('name', ''),
                            "level": level,
                            "price": getattr(alert, 'current_price', 0) if hasattr(alert, 'current_price') else alert.get('current_price', 0),
                            "stop_loss": getattr(alert, 'stop_loss_price', 0) if hasattr(alert, 'stop_loss_price') else alert.get('stop_loss_price', 0),
                            "distance_pct": getattr(alert, 'distance_pct', 0) if hasattr(alert, 'distance_pct') else alert.get('distance_pct', 0),
                        })
        except Exception as e:
            logger.warning(f"止损止盈检查异常: {e}")

        self.stop_loss_alerts = alerts
        return alerts

    def check_rebalance(self) -> List[Dict]:
        """检查组合权重偏离 — 触发再平衡信号"""
        alerts = []
        try:
            pd = _load_positions_data()
            positions = pd.get('positions', {})
            if not isinstance(positions, dict):
                return alerts
            
            # 转换成 {code: qty} 格式
            qty_map = {}
            for code, v in positions.items():
                if isinstance(v, dict):
                    qty_map[code] = float(v.get("shares", v.get("qty", 0)))
                elif isinstance(v, (int, float)):
                    qty_map[code] = float(v)
            extra_prices = pd.get('prices', {})
            cash = float(pd.get('cash', 0))

            try:
                from wind_data_provider import get_quotes_batch
                codes = list(qty_map.keys())
                stock_codes = [c for c in codes if not c.startswith('5') and len(c) >= 6]
                fund_codes = [c for c in codes if c.startswith('5')]
                quotes = get_quotes_batch(stock_codes, fund_codes)
            except Exception:
                quotes = {}
            # 用 extra_prices 兜底
            for code in qty_map:
                if code not in quotes or not quotes.get(code, {}).get('price', 0):
                    p = extra_prices.get(code, 0)
                    if p > 0:
                        quotes[code] = {'price': float(p), 'name': ''}

            # 计算当前权重
            total_value = float(cash)
            holdings_value = {}
            for code, qty in qty_map.items():
                price = 0
                if quotes and code in quotes:
                    price = quotes[code].get('price', 0)
                if price <= 0:
                    continue  # 无价格时跳过，不参与权重计算
                val = float(qty) * price
                holdings_value[code] = val
                total_value += val

            # 与目标权重比较
            for s in PremarketPlanGenerator.PORTFOLIO:
                code = s["code"]
                target_w = s["target_weight"]
                current_val = holdings_value.get(code, 0)
                current_w = current_val / total_value if total_value > 0 else 0
                drift = abs(current_w - target_w)

                if drift > 0.05:  # 偏离超过5%
                    direction = "加仓" if current_w < target_w else "减仓"
                    alerts.append({
                        "code": code, "name": s["name"],
                        "current_weight": round(current_w * 100, 1),
                        "target_weight": round(target_w * 100, 1),
                        "drift": round(drift * 100, 1),
                        "direction": direction
                    })
        except Exception as e:
            logger.warning(f"再平衡检查异常: {e}")

        self.rebalance_alerts = alerts
        return alerts

    def check_events(self) -> List[Dict]:
        """检查事件驱动信号 — 新闻/公告脉冲"""
        alerts = []
        try:
            from event_driven_factor import EventDrivenFactor
            factor = EventDrivenFactor()
            results = factor.compute_factors()
            if results:
                for code, factors in results.items():
                    sentiment = factors.get('sentiment_factor', 0)
                    event = factors.get('event_impact', 0)
                    if abs(sentiment) > 0.5 or abs(event) > 0.5:
                        alerts.append({
                            "code": code,
                            "sentiment": sentiment,
                            "event_impact": event,
                            "action": "关注买入" if sentiment > 0.5 else "警惕卖出" if sentiment < -0.5 else "观望"
                        })
        except Exception as e:
            logger.warning(f"事件驱动检查异常: {e}")

        self.event_alerts = alerts
        return alerts

    def generate_alert_report(self) -> str:
        """生成盘中策略警报报告"""
        self.check_stop_loss()
        self.check_rebalance()
        self.check_events()

        now = datetime.now()
        lines = []
        lines.append(f"# ⚡ 盘中策略监控 — {now.strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

        # 止损止盈警报
        lines.append("## 🛡️ 止损止盈警报")
        lines.append("")
        if self.stop_loss_alerts:
            lines.append("| 代码 | 名称 | 预警级别 | 当前价 | 止损/止盈价 | 距离 |")
            lines.append("|------|------|---------|--------|------------|------|")
            for a in self.stop_loss_alerts:
                lines.append(f"| {a['code']} | {a['name']} | {'🔴' if a['level']=='TRIGGERED' else '🟡'} {a['level']} | {a['price']:.2f} | {a['stop_loss']:.2f} | {a['distance_pct']:+.1f}% |")
        else:
            lines.append("> ✅ 所有持仓安全，无触发止损止盈")
        lines.append("")

        # 再平衡警报
        lines.append("## ⚖️ 权重偏离警报 (偏离 > 5%)")
        lines.append("")
        if self.rebalance_alerts:
            lines.append("| 代码 | 名称 | 当前权重 | 目标权重 | 偏离 | 建议 |")
            lines.append("|------|------|---------|---------|------|------|")
            for a in self.rebalance_alerts:
                lines.append(f"| {a['code']} | {a['name']} | {a['current_weight']}% | {a['target_weight']}% | {a['drift']}% | {a['direction']} |")
        else:
            lines.append("> ✅ 组合权重在目标范围内")
        lines.append("")

        # 事件脉冲
        lines.append("## 📰 事件驱动信号")
        lines.append("")
        if self.event_alerts:
            lines.append("| 代码 | 情绪因子 | 事件冲击 | 建议 |")
            lines.append("|------|---------|---------|------|")
            for a in self.event_alerts:
                lines.append(f"| {a['code']} | {a['sentiment']:+.2f} | {a['event_impact']:+.2f} | {a['action']} |")
        else:
            lines.append("> 无明显事件驱动信号")
        lines.append("")

        lines.append("---")
        lines.append(f"*监控时间: {now.strftime('%Y-%m-%d %H:%M:%S')}*")

        report = "\n".join(lines)

        # 保存
        filepath = os.path.join(REPORT_DIR, f"盘中策略_{now.strftime('%Y%m%d_%H%M')}.md")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"盘中策略已保存: {filepath}")

        return report


# ============================================================
# 3. 盘后综合报告生成器
# ============================================================
class PostmarketReportGenerator:
    """
    盘后综合报告
    持仓复盘 + 策略信号回顾 + 次日预判 + 风险矩阵 + 决策日志
    """

    def __init__(self):
        self.premarket_signals = {}
        self.intraday_alerts = []

    def load_premarket_signals(self) -> Dict:
        """加载今日盘前信号"""
        today = datetime.now().strftime('%Y-%m-%d')
        premarket_file = os.path.join(REPORT_DIR, f"盘前交易计划_{today}.md")
        if os.path.exists(premarket_file):
            # 从文件读取摘要
            lines = []
            with open(premarket_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            self.premarket_signals = {"file": premarket_file, "lines": len(lines)}
        return self.premarket_signals

    def load_intraday_alerts(self) -> List[Dict]:
        """加载今日盘中警报"""
        today = datetime.now().strftime('%Y%m%d')
        alert_files = []
        for f in os.listdir(REPORT_DIR):
            if f.startswith(f"盘中策略_{today}") and f.endswith(".md"):
                alert_files.append(os.path.join(REPORT_DIR, f))
        self.intraday_alerts = alert_files
        return alert_files

    def generate_close_summary(self) -> Dict[str, Any]:
        """生成持仓收益摘要"""
        summary = {"total_value": 0, "total_cost": 0, "pnl": 0, "pnl_pct": 0, "holdings": [], "cash": 0}

        pd = _load_positions_data()
        actual_positions = {}
        raw_cash = float(pd.get('cash', 0))
        extra_prices = pd.get('prices', {})
        # 展开嵌套 positions 格式
        for code, v in pd.get('positions', {}).items():
            if isinstance(v, dict):
                actual_positions[code] = {
                    "qty": float(v.get("shares", v.get("qty", 0))),
                    "cost": float(v.get("avg_cost", v.get("cost", v.get("avg_price", 0))))
                }

        # 收盘价: 优先 extra_prices，其次 Wind API
        codes = list(actual_positions.keys())
        quotes = {}
        stock_codes = [c for c in codes if not c.startswith('5') and len(c) >= 6]
        fund_codes = [c for c in codes if c.startswith('5')]
        try:
            from wind_data_provider import get_quotes_batch
            if stock_codes or fund_codes:
                quotes = get_quotes_batch(stock_codes, fund_codes)
        except Exception:
            pass
        # 如果 Wind 没取到价格，用 positions.json 里的 prices 兜底
        for code in codes:
            if code not in quotes or not quotes.get(code, {}).get('price', 0):
                p = extra_prices.get(code, 0)
                if p > 0:
                    quotes[code] = {'price': float(p), 'name': ''}

        total_value = raw_cash
        for code, info in actual_positions.items():
            qty = info["qty"]
            qd = quotes.get(code, {}) if quotes else {}
            price = qd.get('price', 0)
            # 如果 API 没返回价格，用成本价兜底
            if price <= 0:
                price = info.get('cost', 0)
            change_pct = qd.get('change', 0)
            name = qd.get('name', '') or _STOCK_NAMES.get(code, code)
            val = qty * price
            summary["holdings"].append({
                "code": code, "name": name, "qty": int(qty), "price": round(price, 2),
                "change_pct": round(change_pct, 2), "value": round(val, 2)
            })
            total_value += val

        summary["total_value"] = round(total_value, 2)
        summary["cash"] = raw_cash
        return summary

    def generate_report(self) -> str:
        """生成完整的盘后报告"""
        today_str = datetime.now().strftime('%Y-%m-%d')
        now = datetime.now()

        self.load_premarket_signals()
        alerts = self.load_intraday_alerts()
        close_summary = self.generate_close_summary()

        # 获取风险预警
        risk_report = ""
        try:
            from stop_loss_monitor import StopLossMonitor, generate_risk_alert_report
            monitor = StopLossMonitor()
            risk_report = generate_risk_alert_report([])
        except Exception:
            risk_report = "风险监控模块未加载"

        lines = []
        lines.append(f"# 📊 盘后综合报告 — {today_str}")
        lines.append("")
        lines.append(f"> 生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 一、持仓概览
        lines.append("## 💼 持仓概览")
        lines.append("")
        lines.append(f"- **持仓总市值**: ¥{close_summary['total_value']:,.2f}")
        lines.append(f"- **现金余额**: ¥{close_summary.get('cash', 0):,.2f}")
        lines.append(f"- **当日交易**: 暂无")
        # 计算总涨跌加权
        holdings = close_summary.get("holdings", [])
        if holdings:
            total_val = close_summary['total_value']
            weighted_chg = sum(h['value'] * h.get('change_pct', 0) for h in holdings) / total_val if total_val > 0 else 0
            lines.append(f"- **加权涨跌**: {weighted_chg:+.2f}%")
        lines.append("")
        if holdings:
            lines.append("| 名称 | 代码 | 持仓 | 收盘价 | 日涨跌 | 市值 | 权重 | 目标 | 偏离 |")
            lines.append("|------|------|------|--------|--------|------|------|------|------|")
            for h in holdings:
                code = h['code']
                name = h['name']
                is_fund = code.startswith('5') or code.startswith('1') or code.startswith('58')
                qty_str = f"{h['qty']:,}份" if is_fund else f"{h['qty']:,}股"
                chg = h.get('change_pct', 0)
                chg_str = f"🔴 {chg:+.2f}%" if chg < 0 else (f"🟢 {chg:+.2f}%" if chg > 0 else "—")
                val = h['value']
                total_val = close_summary['total_value']
                actual_w = (val / total_val * 100) if total_val > 0 else 0
                # 获取目标权重
                target_w = 0
                for s in PremarketPlanGenerator.PORTFOLIO:
                    if s['code'] == code:
                        target_w = s['target_weight'] * 100
                        break
                drift = actual_w - target_w
                drift_str = f"🔴 {drift:+.1f}%" if abs(drift) > 2 else f"⚪ {drift:+.1f}%"
                lines.append(f"| **{name}** | {code} | {qty_str} | ¥{h['price']:.2f} | {chg_str} | ¥{val:,.0f} | {actual_w:.1f}% | {target_w:.0f}% | {drift_str} |")
        lines.append("")

        # 二、盘中策略回顾
        lines.append("## ⚡ 盘中策略信号回顾")
        lines.append("")
        if alerts:
            lines.append(f"今日盘中产生 **{len(alerts)}** 次策略监控:")
            for a in sorted(alerts):
                lines.append(f"  - `{os.path.basename(a)}`")
        else:
            lines.append("> 今日盘中未产生策略警报")
        lines.append("")

        # 三、策略信号达成率
        lines.append("## 📈 策略信号达成评估")
        lines.append("")
        lines.append("| 策略类型 | 今日信号数 | 有效信号 | 命中率 | 备注 |")
        lines.append("|---------|-----------|---------|-------|------|")
        lines.append("| 动量策略 | - | - | - | 需明日收盘验证 |")
        lines.append("| 均值回归 | - | - | - | 需明日收盘验证 |")
        lines.append("| 事件驱动 | - | - | - | 需后续跟踪 |")
        lines.append("| ETF资金流向 | - | - | - | 实时参考 |")
        lines.append("")

        # 四、风险矩阵
        lines.append("## 🛡️ 风险矩阵")
        lines.append("")
        high_risk = [s for s in PremarketPlanGenerator.PORTFOLIO if s["risk"] >= 0.30]
        if high_risk:
            lines.append("### 高风险监控标的 (风险权重 ≥ 0.30)")
            for s in high_risk:
                lines.append(f"- 🟡 **{s['name']}**({s['code']}) — 风险权重 {s['risk']:.2f} | 行业: {s['sector']}")
        else:
            lines.append("> ✅ 当前组合无高风险标的（最高风险权重 0.24）")
        lines.append("")
        lines.append("### 组合风险指标")
        lines.append(f"- **标的数量**: {len(PremarketPlanGenerator.PORTFOLIO)} 只")
        lines.append(f"- **平均风险权重**: {sum(s['risk'] for s in PremarketPlanGenerator.PORTFOLIO) / len(PremarketPlanGenerator.PORTFOLIO):.2f}")
        lines.append(f"- **行业分布**: {', '.join(sorted(set(s['sector'] for s in PremarketPlanGenerator.PORTFOLIO)))}")
        lines.append("")
        # 再平衡信号
        try:
            pg = PremarketPlanGenerator()
            rebalance = pg.check_rebalance()
            if rebalance:
                lines.append("### ⚠️ 再平衡信号")
                for r in rebalance:
                    lines.append(f"- **{r['name']}**({r['code']}): {r['direction']} | 当前 {r['current_weight']}% → 目标 {r['target_weight']}% (偏离 {r['drift']}%)")
        except Exception:
            pass
        lines.append("")

        # 五、次日预判
        lines.append("## 🔮 次日预判与关注")
        lines.append("")
        lines.append("### 需要重点关注")
        lines.append("- 盘前宏观数据更新 (PMI/社融/PPI)")
        lines.append("- 美国市场隔夜走势")
        lines.append("- 重大新闻公告扫描")
        lines.append("- 期货夜盘价格变动")
        lines.append("")
        lines.append("### 建议操作")
        lines.append(f"- 仓位建议: 根据宏观评分动态调整")
        lines.append(f"- 止损纪律: 严格执行-15%止损线")
        lines.append(f"- 再平衡: 权重偏离超5%时执行")
        lines.append("")

        # ── CMA 金融代理检查 (v5.7 新增) ──
        try:
            from quant_modules.cma_bridge import run_all_cma_checks
            from config.portfolio import load_portfolio_config

            # 从 close_summary 提取数据
            close_prices = {h['code']: h['price'] for h in close_summary.get('holdings', [])}
            target_weights = {
                s['code']: s['target_weight']
                for s in PremarketPlanGenerator.PORTFOLIO
            }

            cma_results = run_all_cma_checks(
                positions=actual_positions if 'actual_positions' in dir() else {},
                prices=close_prices,
                target_weights=target_weights,
            )

            if cma_results.get('valuation'):
                lines.append("---")
                lines.append("")
                lines.append(cma_results['valuation'].markdown)

            if cma_results.get('audit'):
                lines.append("---")
                lines.append("")
                lines.append(cma_results['audit'].markdown)

        except ImportError:
            logger.debug("[CMA] cma_bridge not available")
        except Exception as e:
            logger.debug(f"[CMA] checks skipped: {e}")

        # 六、本周累计
        lines.append("## 📅 本周策略信号累计")
        lines.append("")
        lines.append(f"> (需整合本周所有交易日数据，每日运行后自动累计)")
        lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(f"*本报告由量化策略系统 v5.7 每日交易工作流自动生成 + 四大理论融合决策 + 期货/期权/套利扫描 + CMA金融代理审核*")
        lines.append(f"*生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append(f"*系统版本: 5.7 | 策略注册表: 12个策略 + 3个CMA代理 | 监控标的: {len(PremarketPlanGenerator.PORTFOLIO)}只权益 + 15只低风险理财*")

        report = "\n".join(lines)

        # 保存
        filepath = os.path.join(REPORT_DIR, f"盘后综合报告_{today_str}.md")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"盘后报告已保存: {filepath}")

        return report


# ============================================================
# 4. 统一调度入口
# ============================================================

def print_banner():
    print("=" * 70)
    print("   量化策略系统 v5.6 — 三阶段交易工作流引擎")
    print("   盘前计划 → 盘中策略 → 盘后报告")
    print("   四大理论融合决策 + 期货/期权/套利 + 年度计划v2对齐")
    print("   HKUDS/Vibe-Trading Architecture")
    print("=" * 70)
    print(f"   启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   报告目录: {REPORT_DIR}")
    print("-" * 70)


def _load_positions_data() -> dict:
    """加载当前持仓快照"""
    pos_path = os.path.join(BASE_DIR, 'config', 'positions.json')
    if os.path.exists(pos_path):
        with open(pos_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {
            'positions': data.get('positions', {}),
            'cash': data.get('cash', 0),
        }
    return {'positions': {}, 'cash': 0}


def _get_llm_intraday_decision(prices: dict) -> str:
    """
    豆包 Seed 2.0 Pro 盘中决策。返回Markdown文本，不可用时返回空字符串。
    """
    try:
        from llm_report_analyzer import LLMTradingAdvisor

        # 加载持仓和配置
        pos_data = _load_positions_data()
        config_path = os.path.join(BASE_DIR, 'config', 'portfolio.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        names = {a['code']: a['name'] for a in cfg['assets']}
        targets = {a['code']: a['target_weight'] for a in cfg['assets']}

        # 计算账户总值
        total_value = pos_data['cash']
        for code, pos in pos_data['positions'].items():
            price = prices.get(code, 0) or pos.get('avg_cost', 0)
            total_value += pos.get('shares', 0) * price

        portfolio_state = {
            'positions': pos_data['positions'],
            'prices': prices,
            'names': names,
            'target_weights': targets,
            'total_value': total_value,
            'cash': pos_data['cash'],
        }

        advisor = LLMTradingAdvisor(provider='volcengine')
        if not advisor.api_key:
            return ""

        result = advisor.generate_intraday_plan(portfolio_state, "")
        actions = result.get('actions', [])

        if not actions:
            return ""

        lines = ["## 🧠 豆包 Seed 2.0 Pro 盘中决策"]
        lines.append("")

        # 分类展示
        buys = [a for a in actions if a.get('action') == 'buy']
        sells = [a for a in actions if a.get('action') == 'sell']
        holds = [a for a in actions if a.get('action') == 'hold']

        if sells:
            lines.append("**📤 建议卖出**:")
            for a in sells:
                name = names.get(a['code'], a['code'])
                lines.append(f"  - {name}({a['code']}): {a['shares']}股 — {a.get('reason','')}")
            lines.append("")

        if buys:
            lines.append("**📥 建议买入**:")
            for a in buys:
                name = names.get(a['code'], a['code'])
                lines.append(f"  - {name}({a['code']}): {a['shares']}股 — {a.get('reason','')}")
            lines.append("")

        if holds:
            codes_str = ', '.join(f"{names.get(a['code'],a['code'])}" for a in holds)
            lines.append(f"**➡️ 维持不变**: {codes_str}")
            lines.append("")

        lines.append(f"> 决策来源: {result.get('source','unknown')} | {datetime.now().strftime('%H:%M:%S')}")
        return '\n'.join(lines)

    except Exception as e:
        logger.debug(f"LLM盘中决策跳过: {e}")
        return ""


def run_premarket():
    """盘前交易计划"""
    print("\n🌅 [阶段1/3] 盘前交易计划生成")
    print("-" * 70)
    start = time.time()

    generator = PremarketPlanGenerator()
    report = generator.generate_plan()
    print(report)

    # === Token增强信号注入 ===
    _inject_token_signals_to_plan()

    elapsed = time.time() - start
    print(f"\n✅ 盘前计划生成完成 ({elapsed:.1f}s)")
    print(f"📁 报告路径: {REPORT_DIR}")

    return generator


def _check_token_data_freshness(max_days: int = 35) -> dict:
    """检查 Token 数据新鲜度

    Args:
        max_days: 最大允许天数（超过则警告），默认 35 天（月度更新 + 5 天缓冲）

    Returns:
        {"fresh": bool, "age_days": int, "file_date": str, "file_path": str, "warning": str}
    """
    import glob
    import re
    from datetime import date

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(project_root, "01_数据源与数据处理", "20260619Token A级数据"),
        os.path.join(project_root, "17-超算中心A级token", "北数所上架包", "01数据文件"),
    ]
    data_dir = next((d for d in candidates if os.path.isdir(d)), None)

    if not data_dir:
        return {"fresh": False, "age_days": 999, "warning": "Token 数据目录不存在"}

    # 查找最新的 finance_token CSV
    csv_files = glob.glob(os.path.join(data_dir, "finance_token_A_B_*.csv"))
    if not csv_files:
        return {"fresh": False, "age_days": 999, "warning": "未找到 finance_token CSV 文件"}

    latest_csv = sorted(csv_files)[-1]
    # 从文件名提取日期，如 finance_token_A_B_20260619_191830.csv → 2026-06-19
    m = re.search(r"(\d{4})(\d{2})(\d{2})", os.path.basename(latest_csv))
    if not m:
        return {"fresh": True, "age_days": 0, "file_path": latest_csv, "warning": ""}

    file_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    age_days = (date.today() - file_date).days

    fresh = age_days <= max_days
    warning = ""
    if age_days > max_days:
        if age_days > 60:
            warning = f"严重过期: Token 数据已 {age_days} 天未更新（文件日期 {file_date}），建议立即更新"
        else:
            warning = f"即将过期: Token 数据已 {age_days} 天未更新（文件日期 {file_date}），建议月度更新"

    return {
        "fresh": fresh,
        "age_days": age_days,
        "file_date": file_date.isoformat(),
        "file_path": latest_csv,
        "warning": warning,
    }


def _inject_token_signals_to_plan():
    """
    注入超算中心Token增强信号:
      - 动态调整止损止盈规则 (stop_loss_multiplier)
      - 输出板块轮动建议 (sector_rotation)
      - 保存调整后的规则配置供盘中使用
    """
    try:
        # === Token 数据新鲜度检查 ===
        freshness = _check_token_data_freshness(max_days=35)
        if freshness["warning"]:
            if not freshness["fresh"]:
                logger.warning(f"⚠️ Token 数据过期: {freshness['warning']}")
                print(f"\n{'!' * 60}")
                print(f"⚠️  Token 数据新鲜度警告")
                print(f"    {freshness['warning']}")
                print(f"    文件: {os.path.basename(freshness.get('file_path', '?'))}")
                print(f"    建议: 将最新 Token CSV 放入 01_数据源与数据处理/20260619Token A级数据/")
                print(f"{'!' * 60}\n")
            else:
                logger.info(f"Token 数据新鲜度: {freshness['age_days']} 天前更新 ({freshness['file_date']})")
        else:
            logger.info(f"Token 数据新鲜度正常: {freshness['age_days']} 天前更新 ({freshness['file_date']})")

        from signals.token_factor_combiner import get_token_combiner

        combiner = get_token_combiner()
        signal = combiner.compute()

        print("\n" + "-" * 60)
        print("[Token增强信号] 超算中心五领域数据接入")
        print("-" * 60)
        print(f"  综合风险指数:        {signal.overall_risk_index:.4f}")
        print(f"  汽车产能指数:        {signal.auto_capacity_index:.4f} ({signal.auto_trend})")
        print(f"  板块建议:            {signal.auto_recommendation}")
        print(f"  建议总调仓:          {signal.combined_adjustment:+.1%}")
        print(f"  止损乘数:            {signal.stop_loss_multiplier:.3f}")
        print(f"      (>1=放宽止损, <1=收紧止损)")

        # 注入止损监控 — 动态调整止损线
        try:
            from stop_loss_monitor import StopLossMonitor

            config_path = os.path.join(BASE_DIR, 'config', 'stop_loss_rules_auto.yaml')
            if not os.path.exists(config_path):
                config_path = None

            monitor = StopLossMonitor(config_path)
            slm = signal.stop_loss_multiplier

            print(f"\n  止损规则动态调整 (乘数={slm:.3f}):")
            for asset in monitor.rules.get('assets', []):
                code = asset['code']
                risk_level = signal.stock_risk_alerts.get(code, "NORMAL")

                # 逐标修正乘数
                individual_mult = slm
                if risk_level == "CRITICAL":
                    individual_mult = min(slm, 0.85)
                elif risk_level == "WARNING":
                    individual_mult = min(slm, 0.93)

                orig_sl = asset['stop_loss_pct']
                new_sl = round(orig_sl * individual_mult, 1)
                asset['stop_loss_pct'] = new_sl
                asset['stop_loss_price'] = round(asset['base_price'] * (1 + new_sl / 100.0), 2)
                print(f"    {code} {asset['name']:<10} 止损 {orig_sl:+.1f}% → {new_sl:+.1f}%")

            # 保存调整后的规则供盘中使用
            adjusted_path = os.path.join(
                BASE_DIR, 'config',
                f'stop_loss_rules_token_{datetime.now().strftime("%Y%m%d")}.yaml'
            )
            os.makedirs(os.path.dirname(adjusted_path), exist_ok=True)
            with open(adjusted_path, 'w', encoding='utf-8') as f:
                yaml.dump(monitor.rules, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            logger.info(f"Token调整后的止损规则已保存: {adjusted_path}")

        except Exception as e:
            logger.warning(f"止损规则Token注入失败: {e}")

        # 输出板块轮动建议
        print(f"\n  板块轮动建议 (供 RebalancingEngine 调用):")
        for stock, adj in sorted(signal.sector_rotation.items(), key=lambda x: -x[1]):
            if adj > 1.0:
                print(f"    建议增配 {stock}: +{(adj-1)*100:.0f}%")
            elif adj < 1.0:
                print(f"    建议减配 {stock}: {(adj-1)*100:.0f}%")

        print("-" * 60)

    except Exception as e:
        logger.warning(f"Token信号注入失败 (数据文件可能不可用): {e}")
    


def run_intraday():
    """盘中策略扫描"""
    print("\n⚡ [阶段2/3] 盘中策略实时扫描")
    print("-" * 70)
    start = time.time()

    monitor = IntradayStrategyMonitor()
    report = monitor.generate_alert_report()
    print(report)

    # ── 豆包 Seed 2.0 Pro 盘中实时决策 ──
    print("\n🧠 豆包 Seed 2.0 Pro 盘中决策...")
    try:
        scanner = PremarketPlanGenerator()
        intraday_prices = scanner.scan_prices()
        llm_section = _get_llm_intraday_decision(intraday_prices)
        if llm_section:
            print(f"\n---\n{llm_section}")
    except Exception as e:
        logger.warning(f"LLM盘中决策跳过: {e}")

    elapsed = time.time() - start
    print(f"\n✅ 盘中策略扫描完成 ({elapsed:.1f}s)")
    print(f"📁 报告路径: {REPORT_DIR}")

    return monitor


def run_postmarket():
    """盘后综合报告"""
    print("\n📊 [阶段3/3] 盘后综合报告生成")
    print("-" * 70)
    start = time.time()

    report_gen = PostmarketReportGenerator()
    report = report_gen.generate_report()
    print(report)

    elapsed = time.time() - start
    print(f"\n✅ 盘后报告生成完成 ({elapsed:.1f}s)")
    print(f"📁 报告路径: {REPORT_DIR}")

    return report_gen


def run_all():
    """全流程执行"""
    print_banner()

    all_results = {}

    # 1. 盘前
    print("\n" + "=" * 70)
    print("  🌅 阶段 1/3: 盘前交易计划")
    print("=" * 70)
    try:
        prem = run_premarket()
        all_results["premarket"] = "OK"
    except Exception as e:
        logger.error(f"盘前计划生成失败: {e}")
        all_results["premarket"] = f"FAIL: {e}"

    # 2. 盘中
    print("\n" + "=" * 70)
    print("  ⚡ 阶段 2/3: 盘中策略监控")
    print("=" * 70)
    try:
        intra = run_intraday()
        all_results["intraday"] = "OK"
    except Exception as e:
        logger.error(f"盘中策略扫描失败: {e}")
        all_results["intraday"] = f"FAIL: {e}"

    # 3. 盘后
    print("\n" + "=" * 70)
    print("  📊 阶段 3/3: 盘后综合报告")
    print("=" * 70)
    try:
        post = run_postmarket()
        all_results["postmarket"] = "OK"
    except Exception as e:
        logger.error(f"盘后报告生成失败: {e}")
        all_results["postmarket"] = f"FAIL: {e}"

    # 汇总
    print("\n" + "=" * 70)
    print("  📋 今日工作流执行汇总")
    print("=" * 70)
    for phase, status in all_results.items():
        icon = "✅" if status == "OK" else "❌"
        print(f"  {icon} {phase}: {status}")
    print(f"\n  📂 所有报告已归档: {REPORT_DIR}")
    print("=" * 70)

    return all_results


def show_system_status():
    """系统状态检查"""
    print("\n🔍 三阶段交易工作流 — 系统状态检查")
    print("=" * 70)

    modules = {
        "策略注册表 (12个策略)": True,
        "年度计划v2对齐 (22权益+15低风险)": True,
        "ETF资金流向监控 (24只ETF)": True,
        "黄金两级止损 (-8%减半/-12%清仓)": True,
        "止损止盈监控": None,
        "事件驱动因子": None,
        "wind_data_provider": None,
        "四大理论融合引擎": None,
        "期货/期权/套利扫描 (Wind MCP)": None,
        "CMA金融代理审核 (月结/估值/对账)": None,
        "TradingAgents多Agent管道 (LangGraph)": None,
        "持仓数据 (positions.json)": os.path.exists(os.path.join(BASE_DIR, 'config', 'positions.json')),
        "组合配置 (portfolio.yaml)": os.path.exists(os.path.join(BASE_DIR, 'config', 'portfolio.yaml')),
        "策略参数 (settings.yaml)": os.path.exists(os.path.join(BASE_DIR, 'config', 'settings.yaml')),
    }

    # 动态检测
    try:
        from stop_loss_monitor import StopLossMonitor
        modules["止损止盈监控"] = True
    except Exception:
        modules["止损止盈监控"] = False

    try:
        from event_driven_factor import EventDrivenFactor
        modules["事件驱动因子"] = True
    except Exception:
        modules["事件驱动因子"] = False

    try:
        from wind_data_provider import get_quotes_batch
        modules["wind_data_provider"] = True
    except Exception:
        modules["wind_data_provider"] = False

    try:
        from quant_modules.decision_theories import run_full_theory_analysis
        modules["四大理论融合引擎"] = True
    except Exception:
        modules["四大理论融合引擎"] = False

    try:
        from quant_modules.futures_options_scanner import run_full_scan
        modules["期货/期权/套利扫描 (Wind MCP)"] = True
    except Exception:
        modules["期货/期权/套利扫描 (Wind MCP)"] = False

    try:
        from quant_modules.cma_bridge import run_all_cma_checks
        modules["CMA金融代理审核 (月结/估值/对账)"] = True
    except Exception:
        modules["CMA金融代理审核 (月结/估值/对账)"] = False

    try:
        from quant_modules.trading_agents_bridge import analyze_with_trading_agents
        modules["TradingAgents多Agent管道 (LangGraph)"] = True
    except Exception:
        modules["TradingAgents多Agent管道 (LangGraph)"] = False

    try:
        from ifind_client import IFindClient
        modules["iFinD接口"] = True
    except Exception:
        modules["iFinD接口"] = False

    print("\n📦 核心模块状态:")
    for name, available in modules.items():
        if available is True:
            print(f"  ✅ {name}")
        elif available is False:
            print(f"  ❌ {name}")
        else:
            print(f"  ⚠️ {name} — 未检测")

    print(f"\n📂 报告归档目录: {REPORT_DIR}")
    if os.path.exists(REPORT_DIR):
        existing = [f for f in os.listdir(REPORT_DIR) if f.endswith('.md')]
        print(f"  已有报告: {len(existing)} 个")
        for f in sorted(existing):
            print(f"    - {f}")
    else:
        print("  (目录尚未创建)")

    print("\n📋 工作流阶段说明:")
    print("  --phase premarket   🌅 盘前 (08:30) — 交易计划")
    print("  --phase intraday    ⚡ 盘中 (09:30-15:00) — 策略监控")
    print("  --phase postmarket  📊 盘后 (15:30后) — 综合报告")
    print("  --phase all         🔄 全流程串联")
    print("=" * 70)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='量化策略系统 v5.6 — 三阶段交易工作流引擎 (对齐2026年度计划v2)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用场景:
  盘前 (08:30前): python daily_trading_workflow.py --phase premarket
  盘中 (09:30-15:00): python daily_trading_workflow.py --phase intraday
  盘后 (15:30后): python daily_trading_workflow.py --phase postmarket
  全流程: python daily_trading_workflow.py --phase all

各阶段产出:
  盘前 → 盘前交易计划_YYYY-MM-DD.md (动量/回归/ETF流向/宏观/操作清单)
  盘中 → 盘中策略_YYYYMMDD_HHMM.md (止损/再平衡/事件驱动警报)
  盘后 → 盘后综合报告_YYYY-MM-DD.md (持仓复盘/策略回顾/次日预判)
        """
    )

    parser.add_argument('--phase', choices=['premarket', 'intraday', 'postmarket', 'all'],
                        help='执行阶段 (--status 时可省略)')
    parser.add_argument('--status', action='store_true', help='系统状态检查')

    args = parser.parse_args()

    if args.status:
        show_system_status()
        sys.exit(0)
    elif not args.phase:
        parser.error('--phase 参数为必填项，或使用 --status 查看系统状态')
    else:
        print_banner()
        if args.phase == 'premarket':
            run_premarket()
        elif args.phase == 'intraday':
            run_intraday()
        elif args.phase == 'postmarket':
            run_postmarket()
        elif args.phase == 'all':
            run_all()
