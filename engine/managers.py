# -*- coding: utf-8 -*-
"""引擎管理器模块"""

import os, time, json, sys
from datetime import datetime
from typing import Dict, Any, Optional, List

from bootstrap import logger, BASE_DIR


class PortfolioOptimizationEngine:
    """
    投资组合优化与回测引擎
    支持: 等权重 / 风险平价 / 风险配比 / 因子配比 / 自定义配置 + 回测对比
    """
    
    # 默认组合配置 (来自投资组合优化系统)
    DEFAULT_PORTFOLIO = {
        '511360': {'name': '短融ETF海富通', 'type': 'money', 'risk': 'low'},
        '518880': {'name': '黄金ETF华安', 'type': 'commodity', 'risk': 'medium'},
        '159980': {'name': '有色ETF大成', 'type': 'industry', 'risk': 'high'},
        '511260': {'name': '十年国债ETF国泰', 'type': 'bond', 'risk': 'low'},
        '511520': {'name': '政金债ETF富国', 'type': 'bond', 'risk': 'low'},
        '601088': {'name': '中国神华', 'type': 'stock', 'risk': 'medium'},
        '510880': {'name': '红利ETF华泰柏瑞', 'type': 'equity', 'risk': 'medium'},
        '512890': {'name': '红利低波ETF华泰柏瑞', 'type': 'equity', 'risk': 'low'},
        '159981': {'name': '能源化工ETF建信', 'type': 'industry', 'risk': 'high'}
    }
    
    def __init__(self, portfolio=None):
        self.portfolio = portfolio or self.DEFAULT_PORTFOLIO.copy()
        self.data = {}
        self.results = {}
        self.corr_matrix = None
        self.pd = None
        self.np = None
        self._try_import_libraries()
    
    def _try_import_libraries(self):
        """尝试导入必要的库"""
        try:
            import pandas as pd
            import numpy as np
            self.pd = pd
            self.np = np
            return True
        except ImportError:
            logger.warning("pandas/numpy 未安装，投资组合优化功能不可用")
            return False
    
    def generate_simulation_data(self, start_date='2020-01-01', end_date='2026-05-01'):
        """生成持仓模拟数据"""
        if self.pd is None or self.np is None:
            logger.error("缺少依赖库，无法生成模拟数据")
            return False
        
        logger.info("生成持仓模拟数据...")
        dates = self.pd.date_range(start=start_date, end=end_date, freq='B')
        for code, info in self.portfolio.items():
            self.np.random.seed(int(code[-3:]))
            vol, trend = {'low': (0.01, 0.0002), 'medium': (0.02, 0.0003), 'high': (0.03, 0.0001)}.get(info['risk'], (0.02, 0.0002))
            returns = self.np.random.normal(trend, vol, len(dates))
            prices = self.np.cumprod(1 + returns)
            if info['type'] == 'bond':
                prices *= (1 + self.np.linspace(0.02, 0.03, len(dates)))
            elif info['type'] == 'commodity':
                prices *= (1 + self.np.sin(self.np.arange(len(dates)) / 60) * 0.005)
            df = self.pd.DataFrame({'date': dates, 'price': prices})
            df['returns'] = df['price'].pct_change()
            df = df.set_index('date')
            self.data[code] = df
        logger.info(f"成功生成 {len(self.data)} 只标的的模拟数据")
        return True
    
    def calculate_correlation_matrix(self):
        """计算资产相关性矩阵"""
        if not self.data:
            logger.warning("无数据可计算相关性矩阵")
            return None
        ret_df = self.pd.DataFrame({c: d['returns'] for c, d in self.data.items()})
        self.corr_matrix = ret_df.corr()
        logger.info("资产相关性矩阵计算完成")
        return self.corr_matrix
    
    def optimize_equal_weight(self):
        """等权重优化"""
        n = len(self.portfolio)
        return {c: 1.0 / n for c in self.portfolio}
    
    def optimize_risk_parity(self):
        """风险平价优化"""
        if not self.data:
            logger.warning("无数据可执行风险平价优化")
            return self.optimize_equal_weight()
        
        cov = self.pd.DataFrame({c: d['returns'] for c, d in self.data.items()}).cov().values * 252
        n = len(self.portfolio)
        w = self.np.ones(n) / n
        for _ in range(200):
            rc = w * (cov @ w)
            rc = self.np.maximum(rc, 1e-10)
            w_new = w * (1/n) / rc
            w_new /= w_new.sum()
            if self.np.max(self.np.abs(w_new - w)) < 1e-6:
                w = w_new
                break
            w = w_new
        w = self.np.clip(w, 0.01, 0.3)
        w /= w.sum()
        result = {list(self.portfolio.keys())[i]: w[i] for i in range(n)}
        logger.info("风险平价优化完成")
        return result
    
    def optimize_risk_based(self):
        """风险配比优化"""
        if not self.data:
            logger.warning("无数据可执行风险配比优化")
            return self.optimize_equal_weight()
        
        risk = self.pd.DataFrame({c: d['returns'] for c, d in self.data.items()}).std().values * self.np.sqrt(252)
        inv = 1 / self.np.maximum(risk, 1e-10)
        w = inv / inv.sum()
        w = self.np.clip(w, 0.01, 0.3)
        w /= w.sum()
        result = {list(self.portfolio.keys())[i]: w[i] for i in range(len(self.portfolio))}
        logger.info("风险配比优化完成")
        return result
    
    def optimize_factor_based(self):
        """因子配比优化"""
        fmap = {'low': 0.15, 'medium': 0.10, 'high': 0.07}
        raw = {c: fmap[self.portfolio[c]['risk']] for c in self.portfolio}
        t = sum(raw.values())
        result = {k: v/t for k, v in raw.items()}
        logger.info("因子配比优化完成")
        return result
    
    def optimize_custom(self):
        """自定义配置"""
        raw = {
            '511360': 0.15, '518880': 0.12, '159980': 0.08,
            '511260': 0.15, '511520': 0.15, '601088': 0.10,
            '510880': 0.10, '512890': 0.10, '159981': 0.05,
        }
        t = sum(raw.values())
        result = {k: v/t for k, v in raw.items()}
        logger.info("自定义配置完成")
        return result
    
    def backtest_portfolio(self, weights, name, initial_capital=3000000):
        """回测投资组合"""
        if not self.data:
            logger.warning("无数据可回测")
            return None
        
        dates = next(iter(self.data.values())).index
        port_ret = self.pd.DataFrame(index=dates).fillna(0)
        for code, w in weights.items():
            if code in self.data:
                port_ret[name] = self.data[code]['returns'].reindex(dates) * w
        daily_r = port_ret.fillna(0).sum(axis=1)
        equity = initial_capital * (1 + daily_r).cumprod()
        returns = equity.pct_change()
        
        total_r = (equity.iloc[-1] / initial_capital - 1) * 100
        nd = len(equity)
        annual_r = ((1 + total_r / 100) ** (252 / max(nd, 1)) - 1) * 100
        sharpe = returns.mean() / returns.std() * self.np.sqrt(252) if returns.std() > 0 else 0
        dd = equity / equity.cummax() - 1
        max_dd = dd.min() * 100
        calmar = abs(annual_r / max_dd) if max_dd != 0 else 0
        win = (returns > 0).mean() * 100
        
        self.results[name] = {
            'total_return': total_r, 'annual_return': annual_r,
            'sharpe_ratio': sharpe, 'max_drawdown': max_dd,
            'calmar_ratio': calmar, 'win_rate': win,
            'final_equity': equity.iloc[-1], 'weights': weights,
        }
        logger.info(f"{name}: 收益率 {total_r:.2f}%, 夏普 {sharpe:.2f}, 回撤 {max_dd:.2f}%")
        return self.results[name]
    
    def run_all_strategies(self):
        """运行所有优化策略"""
        strategies = [
            ('等权重', self.optimize_equal_weight),
            ('风险平价', self.optimize_risk_parity),
            ('风险配比', self.optimize_risk_based),
            ('因子配比', self.optimize_factor_based),
            ('自定义配置', self.optimize_custom),
        ]
        
        for name, func in strategies:
            w = func()
            self.backtest_portfolio(w, name)
        
        return self.results
    
    def compare_strategies(self):
        """对比各策略表现"""
        if not self.results:
            logger.warning("无回测结果可对比")
            return None
        
        rows = []
        for n, r in self.results.items():
            rows.append({
                '策略': n,
                '总收益率': f"{r['total_return']:.2f}%",
                '年化收益': f"{r['annual_return']:.2f}%",
                '夏普比率': f"{r['sharpe_ratio']:.2f}",
                '最大回撤': f"{r['max_drawdown']:.2f}%",
                'Calmar比率': f"{r['calmar_ratio']:.2f}",
                '胜率': f"{r['win_rate']:.2f}%",
            })
        df = self.pd.DataFrame(rows)
        best = max(self.results.items(), key=lambda x: x[1]['sharpe_ratio'])
        logger.info(f"最佳策略: {best[0]} 夏普={best[1]['sharpe_ratio']:.2f} 收益={best[1]['total_return']:.2f}%")
        return df
    
    def generate_report(self, save_dir=None):
        """生成投资组合优化报告"""
        if not self.results:
            return "❌ 无回测结果"
        
        lines = []
        lines.append("=" * 70)
        lines.append("📊 投资组合优化与回测报告")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        
        lines.append("\n📋 持仓清单:")
        for c, i in self.portfolio.items():
            lines.append(f"  {c} - {i['name']} ({i['type']}, {i['risk']})")
        
        lines.append("\n📈 策略表现汇总:")
        for n, r in self.results.items():
            lines.append(f"\n{n}策略:")
            lines.append(f"  总收益率: {r['total_return']:.2f}%")
            lines.append(f"  年化收益: {r['annual_return']:.2f}%")
            lines.append(f"  夏普比率: {r['sharpe_ratio']:.2f}")
            lines.append(f"  最大回撤: {r['max_drawdown']:.2f}%")
            lines.append(f"  Calmar比率: {r['calmar_ratio']:.2f}")
            lines.append(f"  胜率: {r['win_rate']:.2f}%")
            lines.append(f"  最终资金: {r['final_equity']:,.2f}")
            lines.append("  权重配置:")
            for c, w in sorted(r['weights'].items(), key=lambda x: -x[1]):
                lines.append(f"    {self.portfolio[c]['name']}: {w*100:.1f}%")
        
        best = max(self.results.items(), key=lambda x: x[1]['sharpe_ratio'])
        lines.append(f"\n{'='*70}")
        lines.append(f"🏆 最佳策略: {best[0]}")
        lines.append(f"   夏普比率: {best[1]['sharpe_ratio']:.2f}")
        lines.append(f"   收益率: {best[1]['total_return']:.2f}%")
        lines.append("=" * 70)
        
        report = "\n".join(lines)
        
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            rp = os.path.join(save_dir, f"投资组合优化报告_{datetime.now().strftime('%Y%m%d')}.txt")
            with open(rp, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"报告已保存: {rp}")
        
        return report


class KommoCommodityMonitor:
    """
    康波周期大宗商品投研监控系统
    数据源: yfinance(国际商品) + tushare(国内期货) + MySQL(可选存储)
    维度: 商品价格 + 宏观指标 + 产业库存
    """
    
    COMMODITY_LIST = [
        {"symbol": "GC=F",      "name": "黄金",   "category": "康波压舱石", "high": 2800, "low": 2200},
        {"symbol": "SI=F",      "name": "白银",   "category": "康波压舱石", "high": 35,   "low": 20},
        {"symbol": "HG=F",      "name": "铜",     "category": "AI算力核心", "high": 5.0,  "low": 3.2},
        {"symbol": "TIN=F",     "name": "锡",     "category": "AI算力核心", "high": 35000,"low": 22000},
        {"symbol": "ALI=F",     "name": "铝",     "category": "AI算力核心", "high": 1.2,  "low": 0.8},
        {"symbol": "CL=F",      "name": "原油",   "category": "能源周期",   "high": 90,   "low": 60},
    ]
    
    MACRO_SYMBOLS = {
        "美元指数": "DX=F",
        "美债10年期收益率": "^TNX",
    }
    
    def __init__(self, ts_token=None):
        self.ts_token = ts_token or os.environ.get("TS_TOKEN", "")
        self.yf_available = False
        self.ts_available = False
        self._check_dependencies()
    
    def _check_dependencies(self):
        """检查依赖库"""
        try:
            import yfinance as yf
            self.yf_available = True
            logger.info("yfinance 可用")
        except ImportError:
            logger.warning("yfinance 未安装，国际商品数据不可用")
        
        if self.ts_token:
            try:
                import tushare as ts
                ts.set_token(self.ts_token)
                self.ts_pro = ts.pro_api()
                self.ts_available = True
                logger.info("tushare 可用")
            except Exception as e:
                logger.warning(f"tushare 初始化失败: {e}")
        else:
            logger.warning("TS_TOKEN 未设置，国内期货/CPI数据不可用")
    
    def get_intl_commodity(self, symbol):
        """获取国际商品价格 (yfinance)"""
        if not self.yf_available:
            return None
        try:
            import yfinance as yf
            df = yf.Ticker(symbol).history(period="30d")
            if df.empty or len(df) < 2:
                return None
            latest = df.iloc[-1]
            return {
                "price": round(latest['Close'], 2),
                "daily": round((latest['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close'] * 100, 2),
                "monthly": round((latest['Close'] - df.iloc[0]['Close']) / df.iloc[0]['Close'] * 100, 2),
            }
        except Exception as e:
            logger.debug(f"获取 {symbol} 失败: {e}")
            return None
    
    def get_cn_future(self, symbol):
        """获取国内期货价格 (tushare)"""
        if not self.ts_available:
            return None
        try:
            df = self.ts_pro.future_quote(symbol=symbol)
            if df.empty:
                return None
            return {
                "price": round(df.iloc[0]['price'], 2),
                "daily": round(df.iloc[0]['change'], 2),
                "monthly": 0,
            }
        except Exception as e:
            logger.debug(f"获取期货 {symbol} 失败: {e}")
            return None
    
    def get_macro_indicators(self):
        """获取宏观指标"""
        macro = {}
        for name, symbol in self.MACRO_SYMBOLS.items():
            d = self.get_intl_commodity(symbol)
            macro[name] = d["price"] if d else 0
        
        if self.ts_available:
            try:
                macro["美国CPI同比"] = round(self.ts_pro.us_cpi().iloc[0]['cpi'], 2)
                macro["中国CPI同比"] = round(self.ts_pro.cn_cpi().iloc[0]['cpi'], 2)
            except Exception as e:
                logger.debug(f"获取CPI数据失败: {e}")
                macro.setdefault("美国CPI同比", 0)
                macro.setdefault("中国CPI同比", 0)
        else:
            macro["美国CPI同比"] = 0
            macro["中国CPI同比"] = 0
        return macro
    
    @staticmethod
    def judge_trend(monthly):
        """判断趋势"""
        if monthly > 3:
            return "多头趋势"
        elif monthly < -3:
            return "空头趋势"
        else:
            return "震荡趋势"
    
    @staticmethod
    def price_alert(price, high, low, name):
        """价格预警"""
        if price >= high:
            return f"{name}突破预警上限"
        elif price <= low:
            return f"{name}跌破预警下限"
        return "正常"
    
    def monitor(self):
        """执行一次完整监控"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print("\n" + "=" * 110)
        print(f"康波周期大宗商品全维度监控 | 更新时间：{now}")
        print("=" * 110)
        
        macro = self.get_macro_indicators()
        commodity_result = []
        
        print("\n【商品价格 | 康波分类 + 趋势 + 预警】")
        print(f"{'品种':<6} {'分类':<12} {'价格':<10} {'日涨幅(%)':<10} {'月涨幅(%)':<10} {'趋势':<10} {'预警状态'}")
        print("-" * 85)
        
        for item in self.COMMODITY_LIST:
            symbol, name, cate, high, low = item.values()
            data = self.get_intl_commodity(symbol) if "=F" in symbol else self.get_cn_future(symbol)
            if not data:
                print(f"{name:<6} {cate:<12} 数据获取失败")
                continue
            
            price = data["price"]
            trend = self.judge_trend(data["monthly"])
            alert = self.price_alert(price, high, low, name)
            print(f"{name:<6} {cate:<12} {price:<10} {data['daily']:<10} {data['monthly']:<10} {trend:<10} {alert}")
            
            res = {"名称": name, "分类": cate, "最新价格": price,
                   "日涨幅": data["daily"], "月涨幅": data["monthly"],
                   "趋势": trend, "预警": alert}
            commodity_result.append(res)
        
        print("\n【宏观指标 | 货币信用 + 资产估值 + 通胀周期】")
        print("-" * 45)
        for k, v in macro.items():
            print(f"{k:<18} : {v}")
        
        print("=" * 110)
        return commodity_result, macro
    
    def generate_report(self, save_dir=None):
        """生成康波周期监控报告"""
        commodity_result, macro = self.monitor()
        
        lines = []
        lines.append("# 康波周期大宗商品监控报告")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**监测标的**: {len(self.COMMODITY_LIST)} 只大宗商品")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 商品价格概览")
        lines.append("")
        lines.append("| 品种 | 分类 | 价格 | 日涨幅% | 月涨幅% | 趋势 | 预警 |")
        lines.append("|------|------|------|---------|---------|------|------|")
        
        for item in commodity_result:
            lines.append(f"| {item['名称']} | {item['分类']} | {item['最新价格']} | {item['日涨幅']} | {item['月涨幅']} | {item['趋势']} | {item['预警']} |")
        
        lines.append("")
        lines.append("## 宏观指标")
        lines.append("")
        for k, v in macro.items():
            lines.append(f"- **{k}**: {v}")
        
        lines.append("")
        lines.append("---")
        lines.append("*本报告由康波周期监控模块自动生成*")
        
        report = "\n".join(lines)
        
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            rp = os.path.join(save_dir, f"康波周期监控_{datetime.now().strftime('%Y%m%d')}.md")
            with open(rp, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"报告已保存: {rp}")
        
        return report


class ETFFundFlowMonitor:
    """
    ETF国家队资金流向监控器
    用于追踪中央汇金等国家队ETF持仓变化，作为投资决策参考
    
    功能:
    1. 监控24只主流宽基ETF实时行情
    2. 计算5日资金流向趋势
    3. 检测国家队加仓/减仓信号
    4. 生成投资决策建议
    """
    
    # ETF配置列表
    ETF_LIST = [
        # 宽基指数ETF - 核心配置
        {"code": "510300", "name": "沪深300ETF华泰柏瑞", "market": "sh", "category": "宽基核心"},
        {"code": "510310", "name": "沪深300ETF易方达", "market": "sh", "category": "宽基核心"},
        {"code": "159919", "name": "沪深300ETF嘉实", "market": "sz", "category": "宽基核心"},
        {"code": "510500", "name": "中证500ETF南方", "market": "sh", "category": "宽基核心"},
        {"code": "510050", "name": "上证50ETF华夏", "market": "sh", "category": "蓝筹核心"},
        {"code": "159915", "name": "创业板ETF易方达", "market": "sz", "category": "成长科技"},
        {"code": "588000", "name": "科创50ETF华夏", "market": "sh", "category": "成长科技"},
        {"code": "588080", "name": "科创50ETF易方达", "market": "sh", "category": "成长科技"},
        # 中证1000/国证2000 - 小盘风格
        {"code": "560010", "name": "中证1000ETF富国", "market": "sh", "category": "小盘风格"},
        {"code": "512100", "name": "中证1000ETF南方", "market": "sh", "category": "小盘风格"},
        # 红利/低波 - 防御型
        {"code": "515080", "name": "中证红利ETF易方达", "market": "sh", "category": "防御红利"},
        {"code": "512890", "name": "红利低波100ETF华泰柏瑞", "market": "sh", "category": "防御红利"},
        # 行业主题ETF - 国家队关注
        {"code": "512880", "name": "证券ETF国泰", "market": "sh", "category": "金融主题"},
        {"code": "512800", "name": "银行ETF华宝", "market": "sh", "category": "金融主题"},
        {"code": "512170", "name": "医疗ETF华宝", "market": "sh", "category": "医药主题"},
        {"code": "512010", "name": "医药ETF易方达", "market": "sh", "category": "医药主题"},
        {"code": "512760", "name": "半导体ETF国泰", "market": "sh", "category": "科技主题"},
        {"code": "515030", "name": "新能源车ETF华夏", "market": "sh", "category": "新能源主题"},
        {"code": "518880", "name": "黄金ETF华安", "market": "sh", "category": "避险资产"},
    ]
    
    # 信号阈值（5日累计净流入）
    SIGNAL_THRESHOLD = {
        "high": 50_000_000_000,    # 50亿以上 - 高置信度
        "medium": 10_000_000_000,  # 10亿以上 - 中等置信度
        "low": 2_000_000_000,      # 2亿以上 - 关注级别
    }
    
    def __init__(self, data_connector_manager: 'DataConnectorManager' = None):
        self.data_manager = data_connector_manager
        self.signals = []
        self.flow_data = {}
        self.last_update = None
        
    def get_etf_quotes(self) -> Dict[str, Dict]:
        """获取ETF实时行情"""
        quotes = {}
        if self.data_manager:
            codes = [etf["code"] for etf in self.ETF_LIST]
            quotes = self.data_manager.get_quotes_batch(codes)
        return quotes
    
    def analyze_fund_flow(self, days: int = 5) -> List[Dict]:
        """
        分析ETF资金流向
        返回: 按净流入排序的ETF列表
        """
        results = []
        quotes = self.get_etf_quotes()
        
        for etf in self.ETF_LIST:
            code = etf["code"]
            quote = quotes.get(code, {})
            
            # 简化版资金流估算：使用成交额 * 涨跌方向
            if quote.get('price', 0) > 0:
                change_pct = quote.get('change_pct', 0)
                amount = quote.get('amount', 0) or quote.get('volume', 0) * quote.get('price', 0)
                
                # 估算净流入（简化版）
                net_flow = amount * (1 if change_pct >= 0 else -1)
                
                results.append({
                    "code": code,
                    "name": etf["name"],
                    "category": etf["category"],
                    "price": quote.get('price', 0),
                    "change_pct": change_pct,
                    "amount_yi": round(amount / 1e8, 2) if amount else 0,
                    "net_flow_yi": round(net_flow / 1e8, 2) if net_flow else 0,
                    "trend": "流入" if net_flow > 0 else "流出" if net_flow < 0 else "中性"
                })
        
        # 按净流入排序
        results.sort(key=lambda x: x["net_flow_yi"], reverse=True)
        self.flow_data = {r["code"]: r for r in results}
        return results
    
    def detect_signals(self) -> List[Dict]:
        """
        检测国家队加仓/减仓信号
        返回: 信号列表
        """
        signals = []
        
        for code, data in self.flow_data.items():
            net_flow_yi = data["net_flow_yi"]
            trend = data["trend"]
            
            # 加仓信号
            if net_flow_yi >= 50:
                confidence = "高"
                signal_type = "强加仓信号"
            elif net_flow_yi >= 10:
                confidence = "中"
                signal_type = "加仓信号"
            elif net_flow_yi >= 2:
                confidence = "低"
                signal_type = "关注信号"
            # 减仓信号
            elif net_flow_yi <= -50:
                confidence = "高"
                signal_type = "强减仓信号"
            elif net_flow_yi <= -10:
                confidence = "中"
                signal_type = "减仓信号"
            elif net_flow_yi <= -2:
                confidence = "低"
                signal_type = "关注信号(流出)"
            else:
                continue
            
            signals.append({
                **data,
                "signal_type": signal_type,
                "confidence": confidence,
            })
        
        # 按置信度和净流入排序
        signals.sort(key=lambda x: (0 if x["confidence"] == "高" else 1 if x["confidence"] == "中" else 2, 
                                    -x["net_flow_yi"]))
        self.signals = signals
        return signals
    
    def get_investment_suggestion(self) -> Dict[str, Any]:
        """
        生成投资决策建议
        基于ETF资金流向信号，给出风格配置建议
        """
        self.analyze_fund_flow()
        signals = self.detect_signals()
        
        # 统计各风格资金流向
        style_flows = {}
        for data in self.flow_data.values():
            category = data["category"]
            if category not in style_flows:
                style_flows[category] = {"total_flow": 0, "count": 0, "positive": 0}
            style_flows[category]["total_flow"] += data["net_flow_yi"]
            style_flows[category]["count"] += 1
            if data["net_flow_yi"] > 0:
                style_flows[category]["positive"] += 1
        
        # 生成建议
        suggestions = {
            "overall_trend": "净流入" if sum(s["net_flow_yi"] for s in self.flow_data.values()) > 0 else "净流出",
            "high_confidence_signals": [s for s in signals if s["confidence"] == "高"],
            "style_rotation": {},
            "recommendations": []
        }
        
        # 风格轮动建议
        for style, data in sorted(style_flows.items(), key=lambda x: x[1]["total_flow"], reverse=True):
            avg_flow = data["total_flow"] / data["count"] if data["count"] > 0 else 0
            if avg_flow > 5:
                suggestions["style_rotation"][style] = "增持"
            elif avg_flow < -5:
                suggestions["style_rotation"][style] = "减持"
            else:
                suggestions["style_rotation"][style] = "持有"
        
        # 具体建议
        if suggestions["high_confidence_signals"]:
            top_signal = suggestions["high_confidence_signals"][0]
            if "加仓" in top_signal["signal_type"]:
                suggestions["recommendations"].append(
                    f"国家队资金大幅流入{top_signal['name']}，建议关注相关板块机会"
                )
            else:
                suggestions["recommendations"].append(
                    f"国家队资金大幅流出{top_signal['name']}，建议谨慎"
                )
        
        return suggestions
    
    def generate_report(self) -> str:
        """生成ETF资金流向报告"""
        self.analyze_fund_flow()
        signals = self.detect_signals()
        suggestions = self.get_investment_suggestion()
        
        report_lines = [
            "# ETF国家队资金流向监控报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**监测标的**: {len(self.ETF_LIST)} 只主流ETF",
            "",
            "---",
            "",
            "## 资金流向概览",
            "",
            f"- **整体趋势**: {suggestions['overall_trend']}",
            f"- **高置信度信号**: {len(suggestions['high_confidence_signals'])} 条",
            "",
            "## 信号详情",
            "",
        ]
        
        if signals:
            report_lines.extend([
                "| ETF名称 | 代码 | 净流入(亿) | 信号类型 | 置信度 |",
                "|---------|------|-----------|---------|--------|",
            ])
            for s in signals[:10]:
                report_lines.append(
                    f"| {s['name']} | {s['code']} | {s['net_flow_yi']} | {s['signal_type']} | {s['confidence']} |"
                )
        else:
            report_lines.append("> 未检测到明显信号")
        
        report_lines.extend([
            "",
            "## 风格轮动建议",
            "",
        ])
        
        for style, action in suggestions["style_rotation"].items():
            icon = "📈" if action == "增持" else "📉" if action == "减持" else "➡️"
            report_lines.append(f"- {icon} **{style}**: {action}")
        
        if suggestions["recommendations"]:
            report_lines.extend([
                "",
                "## 投资建议",
                "",
            ])
            for rec in suggestions["recommendations"]:
                report_lines.append(f"- {rec}")
        
        report_lines.extend([
            "",
            "---",
            "*本报告由ETF资金流向监控模块自动生成*",
        ])
        
        return "\n".join(report_lines)
