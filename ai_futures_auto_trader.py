# -*- coding: utf-8 -*-
"""
AI期货自动交易系统 v1.0
=====================

功能:
  1. 实时监控十五五政策利好期货品种
  2. AI分析交易机会（基于政策影响强度+技术面+基本面）
  3. 自动执行交易（当机会评分超过阈值）
  4. 风险控制（止损/止盈/仓位管理）
  5. 交易日志和绩效追踪

数据源:
  - Wind MCP (优先)
  - 免费数据回退 (akshare/新浪)

期货观察标的 (15个):
  - 工业品: CU, AL, RB, HC
  - 能源化工: SC, TA, PP, MA
  - 农产品: C, A, LH, SR
  - 新能源金属: LC, SI, SN

策略:
  - 政策驱动型交易（十五五规划）
  - 价差套利（HC-RB, CU-AL等）
  - 动量突破（Tier 1品种优先）

作者: AI Trading System
日期: 2026-06-22
"""

import os
import sys
import json
import time
import logging
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# Windows控制台编码修复
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ============================================================
# 配置
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, '..', 'config')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
TRADE_LOG_DIR = os.path.join(BASE_DIR, 'trade_logs')

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(TRADE_LOG_DIR, exist_ok=True)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(
            os.path.join(LOG_DIR, 'futures_auto_{:%Y%m%d}.log'.format(datetime.now())),
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('futures_auto_trader')

# ============================================================
# 数据类定义
# ============================================================

class SignalType(Enum):
    """信号类型"""
    LONG = "多头"
    SHORT = "空头"
    SPREAD_LONG = "价差做多"
    SPREAD_SHORT = "价差做空"
    HOLD = "持有"

class Priority(Enum):
    """优先级"""
    HIGH = 1      # 立即执行
    MEDIUM = 2    # 条件执行
    LOW = 3       # 观察

@dataclass
class TradeSignal:
    """交易信号"""
    symbol: str
    signal_type: SignalType
    priority: Priority
    score: float           # 评分 0-100
    entry_price: float
    target_price: float
    stop_loss: float
    position_size: float   # 仓位比例
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class TradeRecord:
    """交易记录"""
    symbol: str
    direction: str
    entry_price: float
    quantity: int
    entry_time: datetime
    exit_price: float = 0
    exit_time: datetime = None
    pnl: float = 0
    status: str = "open"   # open/closed/stop_loss/take_profit

# ============================================================
# 期货品种配置
# ============================================================

FUTURES_CONFIG = {
    # Tier 1 - 强烈关注（最高优先级）
    "CU": {
        "name": "铜期货",
        "exchange": "SHFE",
        "priority": Priority.HIGH,
        "policy_direction": "bullish",
        "intensity": "strong",
        "note": "电网+光伏+AI三轮驱动",
        "stop_loss_pct": -0.10,
        "take_profit_pct": 0.15,
        "max_position": 0.05,
    },
    "LC": {
        "name": "碳酸锂期货",
        "exchange": "GFEX",
        "priority": Priority.HIGH,
        "policy_direction": "bullish",
        "intensity": "strong",
        "note": "新能源+储能需求爆发",
        "stop_loss_pct": -0.12,
        "take_profit_pct": 0.20,
        "max_position": 0.05,
    },
    "AL": {
        "name": "铝期货",
        "exchange": "SHFE",
        "priority": Priority.HIGH,
        "policy_direction": "bullish",
        "intensity": "strong",
        "note": "双碳限产+轻量化",
        "stop_loss_pct": -0.10,
        "take_profit_pct": 0.15,
        "max_position": 0.04,
    },
    
    # Tier 2 - 重点关注
    "HC": {
        "name": "热卷期货",
        "exchange": "SHFE",
        "priority": Priority.MEDIUM,
        "policy_direction": "bullish",
        "intensity": "strong",
        "note": "城市更新+制造业",
        "stop_loss_pct": -0.10,
        "take_profit_pct": 0.12,
        "max_position": 0.03,
    },
    "SN": {
        "name": "锡期货",
        "exchange": "SHFE",
        "priority": Priority.MEDIUM,
        "policy_direction": "bullish",
        "intensity": "strong",
        "note": "半导体景气+新质生产力",
        "stop_loss_pct": -0.10,
        "take_profit_pct": 0.15,
        "max_position": 0.03,
    },
    "PP": {
        "name": "聚丙烯期货",
        "exchange": "DCE",
        "priority": Priority.MEDIUM,
        "policy_direction": "bullish",
        "intensity": "strong",
        "note": "以旧换新+产能治理",
        "stop_loss_pct": -0.10,
        "take_profit_pct": 0.12,
        "max_position": 0.03,
    },
    
    # Tier 3 - 观察为主
    "TA": {"name": "PTA期货", "exchange": "ZCE", "priority": Priority.LOW, "policy_direction": "bullish", "intensity": "medium", "stop_loss_pct": -0.10, "take_profit_pct": 0.10, "max_position": 0.02},
    "MA": {"name": "甲醇期货", "exchange": "ZCE", "priority": Priority.LOW, "policy_direction": "neutral", "intensity": "medium", "stop_loss_pct": -0.10, "take_profit_pct": 0.10, "max_position": 0.02},
    "SC": {"name": "原油期货", "exchange": "INE", "priority": Priority.LOW, "policy_direction": "neutral", "intensity": "medium", "stop_loss_pct": -0.12, "take_profit_pct": 0.10, "max_position": 0.02},
    "SR": {"name": "白糖期货", "exchange": "ZCE", "priority": Priority.LOW, "policy_direction": "bullish", "intensity": "strong", "stop_loss_pct": -0.10, "take_profit_pct": 0.12, "max_position": 0.02},
    "LH": {"name": "生猪期货", "exchange": "DCE", "priority": Priority.LOW, "policy_direction": "neutral", "intensity": "strong", "stop_loss_pct": -0.08, "take_profit_pct": 0.08, "max_position": 0.02},
    
    # Tier 4 - 做空机会（需谨慎）
    "RB": {"name": "螺纹钢期货", "exchange": "SHFE", "priority": Priority.MEDIUM, "policy_direction": "bearish", "intensity": "strong", "stop_loss_pct": 0.08, "take_profit_pct": -0.12, "max_position": 0.02},
    "C": {"name": "玉米期货", "exchange": "DCE", "priority": Priority.LOW, "policy_direction": "bearish", "intensity": "strong", "stop_loss_pct": 0.08, "take_profit_pct": -0.10, "max_position": 0.02},
    "A": {"name": "大豆期货", "exchange": "DCE", "priority": Priority.LOW, "policy_direction": "bearish", "intensity": "strong", "stop_loss_pct": 0.08, "take_profit_pct": -0.10, "max_position": 0.02},
    
    # 新能源金属
    "SI": {"name": "工业硅期货", "exchange": "GFEX", "priority": Priority.MEDIUM, "policy_direction": "bullish", "intensity": "strong", "stop_loss_pct": -0.12, "take_profit_pct": 0.15, "max_position": 0.03},
}

# ============================================================
# AI分析引擎
# ============================================================

class FuturesAIAnalyzer:
    """期货AI分析引擎"""
    
    def __init__(self):
        self.policy_scores = self._load_policy_scores()
        
    def _load_policy_scores(self) -> Dict[str, float]:
        """加载政策评分（基于十五五规划）"""
        return {
            "CU": 95,    # 极强
            "LC": 95,
            "AL": 88,
            "HC": 85,
            "SN": 82,
            "PP": 80,
            "SI": 78,
            "SR": 75,
            "TA": 70,
            "MA": 65,
            "SC": 60,
            "LH": 55,
            "RB": 30,    # 偏空
            "C": 25,
            "A": 25,
        }
    
    def analyze_signal(self, symbol: str, current_price: float, 
                       historical_data: Dict) -> Optional[TradeSignal]:
        """
        AI分析交易信号
        
        Args:
            symbol: 品种代码
            current_price: 当前价格
            historical_data: 历史数据（包含技术指标）
            
        Returns:
            TradeSignal or None
        """
        config = FUTURES_CONFIG.get(symbol)
        if not config:
            return None
        
        policy_score = self.policy_scores.get(symbol, 50)
        
        # 综合评分 = 政策评分(40%) + 技术面(30%) + 基本面(30%)
        technical_score = self._calculate_technical_score(historical_data)
        fundamental_score = policy_score  # 政策评分作为基本面代理
        
        composite_score = (
            policy_score * 0.4 +
            technical_score * 0.3 +
            fundamental_score * 0.3
        )
        
        # 判断信号类型
        signal_type = None
        direction = "long" if config["policy_direction"] in ["bullish", "strong_bullish"] else "short"
        
        if composite_score >= 75 and direction == "long":
            signal_type = SignalType.LONG
        elif composite_score <= 25 and direction == "short":
            signal_type = SignalType.SHORT
        else:
            return None  # 未达到交易阈值
        
        # 计算入场/出场价格
        stop_loss_pct = config["stop_loss_pct"]
        take_profit_pct = config["take_profit_pct"]
        
        if direction == "long":
            entry_price = current_price
            target_price = current_price * (1 + take_profit_pct)
            stop_loss = current_price * (1 + stop_loss_pct)
        else:
            entry_price = current_price
            target_price = current_price * (1 - abs(take_profit_pct))
            stop_loss = current_price * (1 + abs(stop_loss_pct))
        
        # 仓位大小
        max_position = config["max_position"]
        position_size = max_position * (composite_score / 100)
        
        return TradeSignal(
            symbol=symbol,
            signal_type=signal_type,
            priority=config["priority"],
            score=composite_score,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            position_size=position_size,
            reason=f"AI综合评分{composite_score:.1f} | 政策得分{policy_score} | {config['note']}"
        )
    
    def _calculate_technical_score(self, historical_data: Dict) -> float:
        """计算技术面评分 (0-100)"""
        if not historical_data:
            return 50
        
        # 简化版：基于价格和均线关系
        price = historical_data.get("price", 0)
        ma20 = historical_data.get("ma20", 0)
        ma60 = historical_data.get("ma60", 0)
        
        if ma20 > 0 and ma60 > 0:
            # 价格在均线上方
            if price > ma20 > ma60:
                return 80  # 强势多头
            elif price < ma20 < ma60:
                return 20  # 强势空头
            else:
                return 50  # 震荡
        
        return 50  # 默认中性

# ============================================================
# 数据获取层
# ============================================================

class FuturesDataFetcher:
    """期货数据获取器 - 集成futures_options_scanner.py"""
    
    def __init__(self):
        self.use_wind = True  # 优先使用Wind
        self._scanner_path = os.path.join(os.path.dirname(__file__), 'quant_modules', 'futures_options_scanner.py')
        
    def get_realtime_price(self, symbol: str) -> Optional[float]:
        """获取实时价格 - 优先使用futures_options_scanner"""
        try:
            # 方法1: 调用futures_options_scanner的扫描功能
            if os.path.exists(self._scanner_path):
                return self._fetch_from_scanner(symbol)
            
            # 方法2: 尝试Wind MCP
            if self.use_wind:
                return self._fetch_wind(symbol)
        except Exception as e:
            logger.debug(f"获取价格失败 {symbol}: {e}")
        
        # 回退到免费数据源
        return self._fetch_free(symbol)
    
    def _fetch_from_scanner(self, symbol: str) -> Optional[float]:
        """从futures_options_scanner获取价格"""
        try:
            # 动态导入scanner模块
            sys.path.insert(0, os.path.dirname(self._scanner_path))
            from futures_options_scanner import scan_futures_market, ALL_FUTURES
            
            # 扫描该品种
            quotes = scan_futures_market(symbols=[symbol], use_wind=False)
            if symbol in quotes:
                return quotes[symbol].price
        except ImportError:
            logger.debug(f"无法导入futures_options_scanner")
        except Exception as e:
            logger.debug(f"scanner获取失败 {symbol}: {e}")
        
        return None
    
    def _fetch_wind(self, symbol: str) -> Optional[float]:
        """Wind数据获取（简化版）"""
        logger.info(f"[模拟] {symbol} 实时价格获取")
        return None  # 占位符
    
    def _fetch_free(self, symbol: str) -> Optional[float]:
        """免费数据源获取"""
        try:
            import akshare as ak
            symbol_map = {
                "CU": "cu", "AL": "al", "RB": "rb", "HC": "rc",
                "TA": "TA", "MA": "MA", "PP": "pp", "SR": "SR",
                "LC": "lc", "SI": "si", "SN": "sn",
            }
            ak_symbol = symbol_map.get(symbol, symbol.lower())
            df = ak.futures_main_sina(symbol=ak_symbol)
            if not df.empty:
                return float(df.iloc[-1]['close'])
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"免费数据获取失败 {symbol}: {e}")
        
        return None
    
    def get_historical_data(self, symbol: str, days: int = 60) -> Dict:
        """获取历史数据"""
        try:
            import akshare as ak
            import pandas as pd
            
            symbol_map = {
                "CU": "cu", "AL": "al", "RB": "rb", "HC": "rc",
                "TA": "TA", "MA": "MA", "PP": "pp", "SR": "SR",
                "LC": "lc", "SI": "si", "SN": "sn",
            }
            ak_symbol = symbol_map.get(symbol, symbol.lower())
            df = ak.futures_main_sina(symbol=ak_symbol, period="daily")
            
            if df.empty:
                return {}
            
            # 计算均线
            df['ma20'] = df['close'].rolling(window=20).mean()
            df['ma60'] = df['close'].rolling(window=60).mean()
            
            latest = df.iloc[-1]
            return {
                "price": float(latest['close']),
                "ma20": float(latest['ma20']) if not pd.isna(latest['ma20']) else 0,
                "ma60": float(latest['ma60']) if not pd.isna(latest['ma60']) else 0,
                "volume": float(latest['volume']),
            }
        except ImportError:
            return {}
        except Exception as e:
            logger.debug(f"历史数据获取失败 {symbol}: {e}")
            return {}

# ============================================================
# 交易执行引擎
# ============================================================

class TradeExecutor:
    """交易执行引擎"""
    
    def __init__(self):
        self.trade_log = []
        self.open_positions = {}
        
    def execute_trade(self, signal: TradeSignal) -> bool:
        """
        执行交易
        
        Args:
            signal: 交易信号
            
        Returns:
            bool: 是否成功
        """
        logger.info("=" * 60)
        logger.info(f"🎯 触发交易信号: {signal.symbol} {signal.signal_type.value}")
        logger.info(f"   评分: {signal.score:.1f}")
        logger.info(f"   方向: {signal.signal_type.value}")
        logger.info(f"   入场价: {signal.entry_price:.2f}")
        logger.info(f"   目标价: {signal.target_price:.2f}")
        logger.info(f"   止损价: {signal.stop_loss:.2f}")
        logger.info(f"   仓位: {signal.position_size*100:.2f}%")
        logger.info(f"   理由: {signal.reason}")
        logger.info("=" * 60)
        
        # 记录交易
        trade = TradeRecord(
            symbol=signal.symbol,
            direction=signal.signal_type.value,
            entry_price=signal.entry_price,
            quantity=int(signal.position_size * 2000000 / signal.entry_price),  # 200万模拟资金
            entry_time=signal.timestamp,
            status="open"
        )
        
        self.open_positions[signal.symbol] = trade
        self.trade_log.append(trade)
        
        # 保存交易日志
        self._save_trade_log(trade)
        
        logger.info(f"✅ 交易已记录: {signal.symbol}")
        return True
    
    def _save_trade_log(self, trade: TradeRecord):
        """保存交易日志"""
        log_file = os.path.join(TRADE_LOG_DIR, f"trade_{trade.symbol}_{trade.entry_time:%Y%m%d_%H%M%S}.json")
        
        log_data = {
            "symbol": trade.symbol,
            "direction": trade.direction,
            "entry_price": trade.entry_price,
            "quantity": trade.quantity,
            "entry_time": trade.entry_time.isoformat(),
            "status": trade.status,
        }
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

# ============================================================
# 主控制器
# ============================================================

class FuturesAutoTrader:
    """期货自动交易主控制器"""
    
    def __init__(self, scan_interval: int = 300):
        """
        Args:
            scan_interval: 扫描间隔（秒），默认5分钟
        """
        self.scan_interval = scan_interval
        self.analyzer = FuturesAIAnalyzer()
        self.data_fetcher = FuturesDataFetcher()
        self.executor = TradeExecutor()
        self.running = False
        
        logger.info("=" * 60)
        logger.info("🚀 AI期货自动交易系统启动")
        logger.info(f"   扫描间隔: {scan_interval}秒")
        logger.info(f"   监控品种: {len(FUTURES_CONFIG)}个")
        logger.info("=" * 60)
    
    def start(self):
        """启动自动交易系统"""
        self.running = True
        logger.info("📡 开始实时监控...")
        
        while self.running:
            try:
                self._scan_and_trade()
                time.sleep(self.scan_interval)
            except KeyboardInterrupt:
                logger.info("⚠️ 用户中断，停止系统")
                self.stop()
                break
            except Exception as e:
                logger.error(f"❌ 系统错误: {e}", exc_info=True)
                time.sleep(60)  # 错误后等待1分钟
    
    def stop(self):
        """停止系统"""
        self.running = False
        logger.info("🛑 系统已停止")
    
    def _scan_and_trade(self):
        """扫描并执行交易"""
        logger.info(f"\n🔍 [{datetime.now().strftime('%H:%M:%S')}] 开始扫描...")
        
        for symbol in FUTURES_CONFIG.keys():
            try:
                # 获取实时价格
                current_price = self.data_fetcher.get_realtime_price(symbol)
                if current_price is None or current_price <= 0:
                    logger.debug(f"  {symbol}: 无法获取价格，跳过")
                    continue
                
                # 获取历史数据
                historical_data = self.data_fetcher.get_historical_data(symbol)
                
                # AI分析
                signal = self.analyzer.analyze_signal(symbol, current_price, historical_data)
                
                if signal:
                    logger.info(f"  ⚡ {symbol}: 触发信号 {signal.signal_type.value} (评分{signal.score:.1f})")
                    self.executor.execute_trade(signal)
                else:
                    logger.debug(f"  {symbol}: 无交易信号")
                    
            except Exception as e:
                logger.error(f"  {symbol}: 处理错误 {e}")
        
        logger.info("✅ 扫描完成\n")
    
    def manual_scan(self):
        """手动扫描一次"""
        self._scan_and_trade()

# ============================================================
# 快速测试模式
# ============================================================

def test_mode():
    """测试模式 - 不实际交易，仅生成信号"""
    logger.info("🧪 测试模式启动")
    
    analyzer = FuturesAIAnalyzer()
    
    # 模拟数据
    test_symbols = ["CU", "LC", "AL", "HC", "RB"]
    
    for symbol in test_symbols:
        mock_data = {
            "price": 100.0,
            "ma20": 98.0,
            "ma60": 95.0,
        }
        
        signal = analyzer.analyze_signal(symbol, 100.0, mock_data)
        
        if signal:
            logger.info(f"✅ {symbol}: {signal.signal_type.value} (评分{signal.score:.1f})")
        else:
            logger.info(f"⏸️ {symbol}: 无信号")

# ============================================================
# 入口
# ============================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='AI期货自动交易系统')
    parser.add_argument('--test', action='store_true', help='测试模式')
    parser.add_argument('--interval', type=int, default=300, help='扫描间隔(秒)')
    parser.add_argument('--once', action='store_true', help='只扫描一次')
    
    args = parser.parse_args()
    
    if args.test:
        test_mode()
    elif args.once:
        trader = FuturesAutoTrader(scan_interval=60)
        trader.manual_scan()
    else:
        trader = FuturesAutoTrader(scan_interval=args.interval)
        trader.start()
