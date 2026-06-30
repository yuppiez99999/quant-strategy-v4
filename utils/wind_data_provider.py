# -*- coding: utf-8 -*-
"""
Wind MCP 数据供应器 — 为 AI 决策引擎提供动态指数行情和基本面数据
替代原有的硬编码指数数据，使 AI 基于真实市场行情做决策

特性:
- 动态获取 A 股主要指数实时行情 (上证/深证/创业板/科创50)
- 批量获取持仓标的实时价格和涨跌幅
- 获取持仓标的的基本面数据 (财务指标，用于再平衡 RAG)
- 数据源优先级: Wind MCP → sina API → 本地缓存 → 兜底价格
- 优雅降级，永不因数据源故障而崩溃

使用方式:
    from utils.wind_data_provider import WindDataProvider
    
    provider = WindDataProvider()
    market_data = provider.build_market_data(holdings_codes)
    fundamental_data = provider.get_fundamental_data(holdings_codes)
"""

import os
import sys
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field

# 添加 quant_modules 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)

# 主要A股指数 Wind 代码映射
MAJOR_INDICES = {
    "上证指数": "000001.SH",
    "深证成指": "399001.SZ",
    "创业板指": "399006.SZ",
    "科创50":  "000688.SH",
    "沪深300": "000300.SH",
    "中证500": "000905.SH",
    "中证1000": "000852.SH",
}

# 缓存配置
INDEX_CACHE_TTL = 60       # 指数行情缓存 60 秒 (盘中可高频刷新)
FUNDAMENTAL_CACHE_TTL = 3600  # 基本面数据缓存 1 小时


@dataclass
class IndexQuote:
    """指数行情快照"""
    name: str
    code: str
    price: float
    change_pct: float
    volume: float = 0.0
    timestamp: str = ""
    source: str = ""


@dataclass
class FundamentalData:
    """基本面数据"""
    code: str
    name: str
    pe_ttm: float = 0.0         # 市盈率 TTM
    pb: float = 0.0             # 市净率
    roe: float = 0.0            # ROE (%)
    revenue_yoy: float = 0.0    # 营收同比 (%)
    profit_yoy: float = 0.0     # 净利润同比 (%)
    debt_ratio: float = 0.0     # 资产负债率 (%)
    market_cap: float = 0.0     # 总市值 (亿)
    dividend_yield: float = 0.0 # 股息率 (%)
    timestamp: str = ""
    source: str = ""


class WindDataProvider:
    """
    Wind MCP 数据供应器
    
    数据优先级: Wind MCP → sina API → 本地缓存 → 兜底价格
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        self._cache_dir = Path(cache_dir) if cache_dir else (Path(__file__).parent.parent / "data" / "cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._index_cache: Dict[str, Tuple[float, IndexQuote]] = {}  # {code: (ts, quote)}
        self._fundamental_cache: Dict[str, Tuple[float, FundamentalData]] = {}
        
        # 检查 Wind MCP 可用性
        self._wind_available = self._check_wind_mcp()
        logger.info(f"WindDataProvider 初始化完成, Wind MCP: {'可用' if self._wind_available else '不可用(将使用降级数据源)'}")
    
    def _check_wind_mcp(self) -> bool:
        """检查 Wind MCP CLI 是否可用"""
        try:
            from quant_modules.wind_mcp import _wind_mcp_call
            result = _wind_mcp_call("index_data", "get_index_price_indicators", {
                "windcode": "000001.SH",
                "indexes": "最新成交价,涨跌幅"
            }, timeout=10)
            if result:
                return True
        except Exception:
            pass
        return False

    # ==================== 指数行情 ====================
    
    def get_index_quotes(self, index_names: Optional[List[str]] = None) -> Dict[str, IndexQuote]:
        """
        获取主要指数实时行情
        
        Args:
            index_names: 指数名称列表，默认获取全部主要指数
        
        Returns:
            {指数名称: IndexQuote} 字典
        """
        if index_names is None:
            index_names = list(MAJOR_INDICES.keys())
        
        results = {}
        now = time.time()
        
        for name in index_names:
            windcode = MAJOR_INDICES.get(name)
            if not windcode:
                continue
            
            # 检查缓存
            if windcode in self._index_cache:
                ts, cached = self._index_cache[windcode]
                if now - ts < INDEX_CACHE_TTL:
                    results[name] = cached
                    continue
            
            # 从 Wind MCP 获取
            quote = self._fetch_index_from_wind(name, windcode)
            if quote:
                self._index_cache[windcode] = (now, quote)
                results[name] = quote
                continue
            
            # 降级到 sina API
            quote = self._fetch_index_from_sina(name, windcode)
            if quote:
                self._index_cache[windcode] = (now, quote)
                results[name] = quote
                continue
            
            # 兜底：返回空占位
            logger.warning(f"无法获取 {name}({windcode}) 行情，所有数据源均失败")
            results[name] = IndexQuote(
                name=name, code=windcode, price=0, change_pct=0,
                timestamp=datetime.now().isoformat(), source="fallback"
            )
        
        return results
    
    def _fetch_index_from_wind(self, name: str, windcode: str) -> Optional[IndexQuote]:
        """从 Wind MCP 获取指数行情"""
        if not self._wind_available:
            return None
        
        try:
            from quant_modules.wind_mcp import _wind_mcp_call
            
            data = _wind_mcp_call("index_data", "get_index_price_indicators", {
                "windcode": windcode,
                "indexes": "最新成交价,涨跌幅,成交量,中文简称"
            }, timeout=15)
            
            if not data:
                return None
            
            columns = [c['name'] for c in data.get('columns', [])]
            rows = data.get('rows', [])
            if not rows or not rows[0]:
                return None
            
            row = rows[0]
            col_map = {c: i for i, c in enumerate(columns)}
            
            price = float(row[col_map.get('最新成交价', 1)]) if '最新成交价' in col_map else 0
            if price <= 0 or price > 1e6:
                return None
            
            return IndexQuote(
                name=name,
                code=windcode,
                price=price,
                change_pct=float(row[col_map.get('涨跌幅', 2)]) if '涨跌幅' in col_map else 0,
                volume=float(row[col_map.get('成交量', 3)]) if '成交量' in col_map else 0,
                timestamp=datetime.now().isoformat(),
                source="Wind MCP"
            )
        except Exception as e:
            logger.debug(f"Wind MCP 获取 {name} 行情失败: {e}")
            return None
    
    def _fetch_index_from_sina(self, name: str, windcode: str) -> Optional[IndexQuote]:
        """从新浪财经 API 获取指数行情 (降级)"""
        try:
            import requests
            
            # 映射 Wind 代码到新浪代码
            sina_code_map = {
                "000001.SH": "s_sh000001",
                "399001.SZ": "s_sz399001",
                "399006.SZ": "s_sz399006",
                "000688.SH": "s_sh000688",
                "000300.SH": "s_sh000300",
                "000905.SH": "s_sh000905",
                "000852.SH": "s_sh000852",
            }
            sina_code = sina_code_map.get(windcode)
            if not sina_code:
                return None
            
            url = f"https://hq.sinajs.cn/list={sina_code}"
            resp = requests.get(url, timeout=8, headers={"Referer": "https://finance.sina.com.cn"})
            resp.encoding = 'gbk'
            text = resp.text
            
            if 'var hq_str_' not in text:
                return None
            
            content = text.split('=', 1)[-1].strip().strip('"')
            parts = content.split(',')
            if len(parts) < 4:
                return None
            
            price = float(parts[1]) if parts[1] else 0
            prev_close = float(parts[2]) if parts[2] else price
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            return IndexQuote(
                name=name, code=windcode, price=price,
                change_pct=change_pct,
                timestamp=datetime.now().isoformat(),
                source="sina API"
            )
        except Exception as e:
            logger.debug(f"sina API 获取 {name} 行情失败: {e}")
            return None

    # ==================== 基本面数据 ====================
    
    def get_fundamental_data(self, codes: List[str]) -> Dict[str, FundamentalData]:
        """
        批量获取持仓标的基本面数据
        
        Args:
            codes: 股票代码列表 (如 ['300308', '688041', '002371'])
        
        Returns:
            {code: FundamentalData} 字典
        """
        results = {}
        now = time.time()
        
        for code in codes:
            # 检查缓存
            if code in self._fundamental_cache:
                ts, cached = self._fundamental_cache[code]
                if now - ts < FUNDAMENTAL_CACHE_TTL:
                    results[code] = cached
                    continue
            
            # 从 Wind MCP 获取
            fund = self._fetch_fundamental_from_wind(code)
            if fund:
                self._fundamental_cache[code] = (now, fund)
                results[code] = fund
                continue
            
            # 降级1：从缓存文件读取
            fund = self._load_fundamental_from_cache(code)
            if fund:
                self._fundamental_cache[code] = (now, fund)
                results[code] = fund
                logger.info(f"基本面数据[{code}]: 本地缓存")
                continue
            
            # 降级2：AKShare 免费数据源
            fund = self._fetch_fundamental_from_akshare(code)
            if fund:
                self._fundamental_cache[code] = (now, fund)
                self._save_fundamental_to_cache(code, fund)
                results[code] = fund
                logger.info(f"基本面数据[{code}]: AKShare (免费回退)")
                continue
            
            # 降级3：Baostock 免费数据源
            fund = self._fetch_fundamental_from_baostock(code)
            if fund:
                self._fundamental_cache[code] = (now, fund)
                self._save_fundamental_to_cache(code, fund)
                results[code] = fund
                logger.info(f"基本面数据[{code}]: Baostock (免费回退)")
                continue
            
            logger.warning(f"无法获取 {code} 基本面数据 (所有数据源均不可用)")
        
        return results
    
    def _fetch_fundamental_from_wind(self, code: str) -> Optional[FundamentalData]:
        """从 Wind MCP 获取个股基本面数据"""
        if not self._wind_available:
            return None
        
        try:
            from quant_modules.wind_mcp import _wind_code, _wind_mcp_call
            
            windcode = _wind_code(code)
            
            # 使用 stock_data.get_stock_fundamentals 的 NL 工具获取基本面
            question = (
                f"获取{windcode}的市盈率TTM、市净率、ROE、营收同比增长率、"
                f"净利润同比增长率、资产负债率、总市值、股息率"
            )
            
            data = _wind_mcp_call("stock_data", "get_stock_fundamentals", {
                "question": question,
                "lang": "zh"
            }, timeout=20)
            
            if not data:
                return None
            
            # 解析返回的结构化数据
            # Wind MCP NL 工具返回格式可能包含 columns 和 rows 或直接的文本
            fund = FundamentalData(code=code, name=code, timestamp=datetime.now().isoformat(), source="Wind MCP")
            
            # 尝试从结构化数据解析
            if 'rows' in data and data['rows']:
                row = data['rows'][0]
                columns = [c['name'] for c in data.get('columns', [])]
                col_map = {c: i for i, c in enumerate(columns)}
                
                for key, wind_key in [
                    ('pe_ttm', '市盈率TTM'), ('pb', '市净率'), ('roe', 'ROE'),
                    ('revenue_yoy', '营收同比增长率'), ('profit_yoy', '净利润同比增长率'),
                    ('debt_ratio', '资产负债率'), ('market_cap', '总市值'), ('dividend_yield', '股息率')
                ]:
                    if wind_key in col_map:
                        try:
                            setattr(fund, key, float(row[col_map[wind_key]]) if row[col_map[wind_key]] else 0)
                        except (ValueError, TypeError):
                            pass
            
            # 从文本中提取名称
            if 'name' in col_map:
                fund.name = row[col_map['name']] if row[col_map['name']] else code
            
            # 保存缓存
            self._save_fundamental_to_cache(code, fund)
            
            return fund
            
        except Exception as e:
            logger.debug(f"Wind MCP 获取 {code} 基本面失败: {e}")
            return None
    
    def _save_fundamental_to_cache(self, code: str, fund: FundamentalData):
        """保存基本面数据到本地缓存"""
        try:
            cache_file = self._cache_dir / f"fundamental_{code}.json"
            cache_data = {
                "code": fund.code,
                "name": fund.name,
                "pe_ttm": fund.pe_ttm,
                "pb": fund.pb,
                "roe": fund.roe,
                "revenue_yoy": fund.revenue_yoy,
                "profit_yoy": fund.profit_yoy,
                "debt_ratio": fund.debt_ratio,
                "market_cap": fund.market_cap,
                "dividend_yield": fund.dividend_yield,
                "timestamp": fund.timestamp,
                "source": fund.source,
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def _load_fundamental_from_cache(self, code: str) -> Optional[FundamentalData]:
        """从本地缓存加载基本面数据"""
        try:
            cache_file = self._cache_dir / f"fundamental_{code}.json"
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return FundamentalData(
                code=data.get("code", code),
                name=data.get("name", code),
                pe_ttm=data.get("pe_ttm", 0),
                pb=data.get("pb", 0),
                roe=data.get("roe", 0),
                revenue_yoy=data.get("revenue_yoy", 0),
                profit_yoy=data.get("profit_yoy", 0),
                debt_ratio=data.get("debt_ratio", 0),
                market_cap=data.get("market_cap", 0),
                dividend_yield=data.get("dividend_yield", 0),
                timestamp=data.get("timestamp", ""),
                source=data.get("source", "cache"),
            )
        except Exception:
            return None
    
    def _fetch_fundamental_from_akshare(self, code: str) -> Optional[FundamentalData]:
        """从 AKShare 获取个股基本面数据 (免费回退)"""
        try:
            import akshare as ak
            now = datetime.now()
            
            # 获取主要财务指标
            df = ak.stock_financial_abstract_ths(symbol=code, indicator="按报告期")
            if df is None or df.empty:
                return None
            
            # 取最新一期
            row = df.iloc[0]
            name = str(row.get('股票简称', code))
            
            fund = FundamentalData(
                code=code,
                name=name,
                pe_ttm=self._safe_float_ak(row.get('市盈率')),
                pb=self._safe_float_ak(row.get('市净率')),
                roe=self._safe_float_ak(row.get('净资产收益率')),
                revenue_yoy=self._safe_float_ak(row.get('营业收入增长率')),
                profit_yoy=self._safe_float_ak(row.get('净利润增长率')),
                debt_ratio=self._safe_float_ak(row.get('资产负债率')),
                market_cap=self._safe_float_ak(row.get('总市值')) / 1e8 if self._safe_float_ak(row.get('总市值')) > 0 else 0,
                dividend_yield=0,  # AKShare 该接口无股息率，由 Baostock/Wind 补充
                timestamp=now.isoformat(),
                source="AKShare",
            )
            return fund
        except ImportError:
            return None
        except Exception as e:
            logger.debug(f"AKShare 获取 {code} 基本面失败: {e}")
            return None
    
    def _fetch_fundamental_from_baostock(self, code: str) -> Optional[FundamentalData]:
        """从 Baostock 获取个股基本面数据 (免费回退)"""
        try:
            import baostock as bs
            now = datetime.now()
            
            # 确定市场后缀
            if code.startswith('6'):
                bs_code = f"sh.{code}"
            else:
                bs_code = f"sz.{code}"
            
            lg = bs.login()
            if lg.error_code != '0':
                return None
            
            fund = FundamentalData(code=code, name=code, timestamp=now.isoformat(), source="Baostock")
            
            # 查询利润表（最新一期）
            try:
                rs_profit = bs.query_profit_data(code=bs_code, year=2025, quarter=1)
                if rs_profit.error_code == '0':
                    profit_rows = []
                    while rs_profit.next():
                        profit_rows.append(rs_profit.get_row_data())
                    if profit_rows:
                        row = profit_rows[-1]  # 取最新
                        fund.revenue_yoy = self._safe_float_ak(row[4])   # 营收同比
                        fund.profit_yoy = self._safe_float_ak(row[5])    # 净利润同比
                        fund.roe = self._safe_float_ak(row[6])           # ROE
            except Exception:
                pass
            
            # 查询资产负债率（最新一期）
            try:
                rs_balance = bs.query_balance_data(code=bs_code, year=2025, quarter=1)
                if rs_balance.error_code == '0':
                    bal_rows = []
                    while rs_balance.next():
                        bal_rows.append(rs_balance.get_row_data())
                    if bal_rows:
                        row = bal_rows[-1]
                        fund.debt_ratio = self._safe_float_ak(row[5])   # 资产负债率
            except Exception:
                pass
            
            bs.logout()
            
            # 至少有一项数据有效才返回
            if fund.roe == 0 and fund.revenue_yoy == 0 and fund.profit_yoy == 0 and fund.debt_ratio == 0:
                return None
            return fund
        except ImportError:
            return None
        except Exception as e:
            logger.debug(f"Baostock 获取 {code} 基本面失败: {e}")
            return None
    
    @staticmethod
    def _safe_float_ak(val) -> float:
        """安全转换为 float，处理 AKShare/Baostock 的各种空值格式"""
        if val is None:
            return 0.0
        try:
            s = str(val).replace('%', '').replace(',', '').strip()
            if s in ('', '-', '--', 'None', 'nan', 'N/A'):
                return 0.0
            return float(s)
        except (ValueError, TypeError):
            return 0.0

    # ==================== 市场数据结构构建 ====================
    
    def build_market_data(
        self,
        positions: Dict[str, Dict] = None,
        include_fundamentals: bool = False
    ) -> Dict[str, Any]:
        """
        构建 AI 决策所需的完整市场数据结构
        
        替代原有的硬编码指数数据，使用 Wind MCP 动态获取
        
        Args:
            positions: 持仓字典 {code: {name, shares, avg_cost, category, ...}}
            include_fundamentals: 是否包含基本面数据 (再平衡时建议开启)
        
        Returns:
            市场数据字典 (兼容现有的 GLM5DecisionEngine 格式)
        """
        now = datetime.now()
        
        # 1. 获取指数行情
        index_quotes = self.get_index_quotes()
        
        market_data = {
            "日期": now.strftime('%Y-%m-%d'),
            "时间": now.strftime('%H:%M:%S'),
            "数据来源": "Wind MCP" if self._wind_available else "sina API + 本地缓存",
            "指数行情": {},
            "资金流向": {
                "数据来源": "待接入 (北向/南向资金需额外数据源)",
                "说明": "资金流数据需要专用 API，当前标记为待接入",
            },
            "板块表现": {},
        }
        
        for name, quote in index_quotes.items():
            if quote.price > 0:
                market_data["指数行情"][name] = {
                    "收盘": round(quote.price, 2),
                    "涨跌幅": f"{quote.change_pct:+.2f}%",
                    "数据源": quote.source,
                }
        
        # 2. 计算板块表现 (基于持仓)
        if positions:
            sector_perf = {}
            for code, pos in positions.items():
                category = pos.get("category", "unknown")
                if category not in sector_perf:
                    sector_perf[category] = {"name": category, "pct_changes": []}
            
            # 需要价格数据来计算板块表现 (由上层调用者提供)
            market_data["板块表现"] = sector_perf
        
        # 3. 添加基本面数据 (再平衡场景)
        if include_fundamentals and positions:
            codes = list(positions.keys())
            fundamental_data = self.get_fundamental_data(codes)
            
            market_data["基本面数据"] = {}
            for code, fund in fundamental_data.items():
                market_data["基本面数据"][code] = {
                    "名称": fund.name,
                    "市盈率TTM": fund.pe_ttm,
                    "市净率": fund.pb,
                    "ROE(%)": fund.roe,
                    "营收同比(%)": fund.revenue_yoy,
                    "利润同比(%)": fund.profit_yoy,
                    "资产负债率(%)": fund.debt_ratio,
                    "总市值(亿)": fund.market_cap,
                    "股息率(%)": fund.dividend_yield,
                    "数据源": fund.source,
                }
        
        return market_data
    
    def get_market_summary_text(self, market_data: Dict[str, Any]) -> str:
        """
        将市场数据转换为简洁的文本摘要，适合注入到 AI prompt 中
        
        Args:
            market_data: build_market_data() 的输出
        
        Returns:
            市场概况文本
        """
        lines = []
        lines.append(f"【市场快照】{market_data.get('日期', '')} {market_data.get('时间', '')}")
        lines.append(f"数据来源: {market_data.get('数据来源', '未知')}")
        lines.append("")
        
        indices = market_data.get('指数行情', {})
        if indices:
            lines.append("--- 主要指数 ---")
            for name, info in indices.items():
                close = info.get('收盘', 'N/A')
                change = info.get('涨跌幅', 'N/A')
                lines.append(f"  {name}: {close} ({change})")
            lines.append("")
        
        fundamentals = market_data.get('基本面数据', {})
        if fundamentals:
            lines.append("--- 持仓基本面 ---")
            for code, info in fundamentals.items():
                name = info.get('名称', code)
                pe = info.get('市盈率TTM', 'N/A')
                roe = info.get('ROE(%)', 'N/A')
                lines.append(f"  {code} {name}: PE={pe}, ROE={roe}%")
            lines.append("")
        
        return '\n'.join(lines)
    
    def health_check(self) -> Dict[str, Any]:
        """数据供应器健康检查"""
        return {
            "wind_mcp_available": self._wind_available,
            "index_cache_size": len(self._index_cache),
            "fundamental_cache_size": len(self._fundamental_cache),
            "cache_dir": str(self._cache_dir),
            "timestamp": datetime.now().isoformat(),
        }


# ==================== 模块级快捷函数 ====================

# 全局单例
_provider_instance: Optional[WindDataProvider] = None


def get_wind_provider() -> WindDataProvider:
    """获取全局 WindDataProvider 单例"""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = WindDataProvider()
    return _provider_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("=" * 60)
    print("Wind Data Provider 测试")
    print("=" * 60)
    
    provider = WindDataProvider()
    
    # 测试指数行情
    print("\n--- 指数行情 ---")
    quotes = provider.get_index_quotes(["上证指数", "深证成指", "创业板指"])
    for name, q in quotes.items():
        if q.price > 0:
            print(f"  {name}: {q.price} ({q.change_pct:+.2f}%) [{q.source}]")
        else:
            print(f"  {name}: 数据不可用")
    
    # 测试市场数据构建
    print("\n--- 市场数据构建 ---")
    test_positions = {
        "300308": {"name": "中际旭创", "shares": 500, "avg_cost": 128.5, "category": "高端制造"},
        "688041": {"name": "海光信息", "shares": 300, "avg_cost": 62.3, "category": "高端制造"},
        "601088": {"name": "中国神华", "shares": 1000, "avg_cost": 38.2, "category": "顺周期"},
    }
    
    market_data = provider.build_market_data(test_positions, include_fundamentals=True)
    summary = provider.get_market_summary_text(market_data)
    print(summary)
    
    # 健康检查
    print("\n--- 健康检查 ---")
    print(json.dumps(provider.health_check(), ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 60)
    print("测试完成")
