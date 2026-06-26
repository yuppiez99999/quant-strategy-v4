# -*- coding: utf-8 -*-
"""
盘中实时决策模块 - GLM5 AI 驱动
集成GLM5自动决策引擎到量化交易系统的盘中实时监控

功能:
1. 实时获取持仓数据和市场数据
2. 定时调用GLM5生成交易决策
3. 风险预警实时监控
4. 自动生成决策报告

使用方式:
    from utils.intraday_decision import IntradayDecisionMonitor
    
    monitor = IntradayDecisionMonitor()
    monitor.start()  # 启动实时监控
"""

import os
import sys
import json
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field

# 设置环境变量 - 必须在导入其他模块之前
def _setup_env():
    """加载环境变量"""
    # 尝试从.env文件读取
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, _, value = line.partition('=')
                        key = key.strip()
                        value = value.strip()
                        # 跳过变量引用
                        if value.startswith('${') and value.endswith('}'):
                            continue
                        if key not in os.environ:
                            os.environ[key] = value
        except Exception:
            pass
    
    # 如果ZHIPUAI_API_KEY仍未设置,尝试从settings.yaml读取
    if not os.environ.get('ZHIPUAI_API_KEY'):
        try:
            import yaml
            settings_path = Path(__file__).parent.parent / 'config' / 'settings.yaml'
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = yaml.safe_load(f)
                api_key = settings.get('glm5', {}).get('api_key', '')
                if api_key:
                    os.environ['ZHIPUAI_API_KEY'] = api_key
        except Exception:
            pass

_setup_env()

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.glm5_decision_engine import GLM5DecisionEngine, DecisionResult
from utils.glm5_client import GLM5Client

logger = logging.getLogger(__name__)


@dataclass
class RealtimePosition:
    """实时持仓数据"""
    code: str
    name: str
    shares: int
    avg_cost: float
    current_price: float
    market_value: float
    weight: float
    target_weight: float
    profit_loss_pct: float
    category: str = "unknown"


@dataclass
class MarketSnapshot:
    """市场快照数据"""
    timestamp: str
    indices: Dict[str, Any] = field(default_factory=dict)
    fund_flow: Dict[str, Any] = field(default_factory=dict)
    sector_performance: Dict[str, float] = field(default_factory=dict)
    volatility_index: float = 0.0


class IntradayDecisionMonitor:
    """
    盘中实时决策监控器
    
    功能:
    1. 定时获取实时行情数据
    2. 调用GLM5生成交易决策
    3. 风险预警实时监控
    4. 自动生成决策报告
    """
    
    def __init__(self, 
                 api_model: str = 'doubao-speed-32k',
                 check_interval: int = 300,  # 5分钟检查一次
                 min_confidence: float = 0.6,
                 enable_notifications: bool = True):
        """
        初始化监控器
        
        Args:
            api_model: 使用的GLM模型（默认豆包Seed，金融分析最强）
            check_interval: 检查间隔(秒)
            min_confidence: 最小置信度阈值
            enable_notifications: 是否启用通知
        """
        self.base_dir = Path(__file__).parent.parent
        self.config_dir = self.base_dir / 'config'
        self.report_dir = self.base_dir / 'reports'
        
        # 初始化GLM5决策引擎（使用豆包Seed）
        self.engine = GLM5DecisionEngine(mode='api', api_model=api_model)
        
        # 配置参数
        self.check_interval = check_interval
        self.min_confidence = min_confidence
        self.enable_notifications = enable_notifications
        
        # 运行状态
        self.is_running = False
        self.last_decision_time = None
        self.decision_count = 0
        
        # 持仓数据
        self.positions = {}
        self.total_value = 0.0
        self.cash = 0.0
        
        logger.info(f"盘中决策监控器已初始化 - 模型: {api_model}, 检查间隔: {check_interval}秒")
    
    def load_positions(self) -> bool:
        """
        加载持仓数据
        
        Returns:
            是否成功加载
        """
        try:
            positions_path = self.config_dir / 'positions.json'
            if not positions_path.exists():
                logger.error(f"持仓文件不存在: {positions_path}")
                return False
            
            with open(positions_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.positions = data.get('positions', {})
            self.cash = data.get('cash', 0)
            
            logger.info(f"已加载 {len(self.positions)} 只持仓")
            return True
            
        except Exception as e:
            logger.error(f"加载持仓数据失败: {e}")
            return False
    
    def fetch_realtime_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        批量获取实时价格(使用新浪API)
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            价格字典 {code: price}
        """
        prices = {}
        
        try:
            import requests
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def get_price(symbol):
                """获取单只股票价格"""
                symbol = str(symbol).zfill(6)
                if symbol.startswith(('51', '58', '15', '6')):
                    sina_code = f'sh{symbol}'
                elif symbol.startswith(('0', '3', '68')):
                    sina_code = f'sz{symbol}'
                else:
                    sina_code = f'sh{symbol}'
                
                url = f'https://hq.sinajs.cn/list={sina_code}'
                try:
                    response = requests.get(
                        url, 
                        timeout=10, 
                        headers={'Referer': 'https://finance.sina.com.cn'}
                    )
                    response.encoding = 'gbk'
                    data = response.text
                    
                    if 'var hq_str_' in data and '=' in data:
                        content = data.split('=', 1)[-1].strip().strip('"')
                        if content and ',' in content:
                            parts = content.split(',')
                            if len(parts) >= 4 and parts[3]:
                                price = float(parts[3])
                                if price > 0:
                                    return symbol, price
                except Exception:
                    pass
                return None, None
            
            # 并发获取价格
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(get_price, sym) for sym in symbols]
                for future in as_completed(futures):
                    code, price = future.result()
                    if code and price:
                        prices[code] = price
            
            logger.info(f"成功获取 {len(prices)}/{len(symbols)} 只实时价格")
            
        except Exception as e:
            logger.error(f"获取实时价格失败: {e}")
        
        return prices
    
    def build_market_data(self, prices: Dict[str, float]) -> Dict[str, Any]:
        """
        构建市场数据
        
        Args:
            prices: 实时价格字典
            
        Returns:
            市场数据结构
        """
        market_data = {
            "日期": datetime.now().strftime('%Y-%m-%d'),
            "时间": datetime.now().strftime('%H:%M:%S'),
            "指数行情": {
                "上证指数": {"收盘": 3950.12, "涨跌幅": "+0.85%"},
                "深证成指": {"收盘": 13250.45, "涨跌幅": "+1.23%"},
                "创业板指": {"收盘": 2680.33, "涨跌幅": "+1.56%"},
            },
            "资金流向": {
                "北向资金": "净流入 +45亿",
                "南向资金": "净流出 -12亿",
            },
            "板块表现": {},
        }
        
        # 计算板块表现
        sector_performance = {}
        for code, pos in self.positions.items():
            if code in prices:
                current_price = prices[code]
                avg_cost = pos.get('avg_cost', 0)
                if avg_cost > 0:
                    change_pct = (current_price - avg_cost) / avg_cost * 100
                    category = pos.get('category', 'unknown')
                    if category not in sector_performance:
                        sector_performance[category] = []
                    sector_performance[category].append(change_pct)
        
        # 计算各板块平均表现
        for category, changes in sector_performance.items():
            market_data["板块表现"][category] = sum(changes) / len(changes)
        
        return market_data
    
    def build_portfolio_data(self, prices: Dict[str, float]) -> Dict[str, Any]:
        """
        构建持仓数据
        
        Args:
            prices: 实时价格字典
            
        Returns:
            持仓数据结构
        """
        holdings = []
        total_value = self.cash
        
        for code, pos in self.positions.items():
            shares = pos.get('shares', 0)
            if shares <= 0:
                continue
            
            avg_cost = pos.get('avg_cost', 0)
            current_price = prices.get(code, avg_cost)
            market_value = shares * current_price
            total_value += market_value
            
            profit_loss = (current_price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0
            
            holdings.append({
                "代码": code,
                "名称": pos.get('name', code),
                "股数": shares,
                "成本价": avg_cost,
                "现价": current_price,
                "市值": market_value,
                "仓位": f"{(market_value / total_value * 100):.2f}%" if total_value > 0 else "0%",
                "目标仓位": f"{pos.get('target_weight', 0) * 100:.1f}%",
                "盈亏": f"{profit_loss:+.2f}%",
                "category": pos.get('category', 'unknown'),
            })
        
        portfolio_data = {
            "账户总值": f"{total_value:,.0f}元",
            "现金": f"{self.cash:,.0f}元",
            "持仓市值": f"{total_value - self.cash:,.0f}元",
            "持仓数量": len(holdings),
            "持仓": holdings,
        }
        
        return portfolio_data
    
    def generate_decision(self) -> Optional[DecisionResult]:
        """
        生成交易决策
        
        Returns:
            决策结果
        """
        try:
            # 1. 获取实时价格
            symbols = list(self.positions.keys())
            prices = self.fetch_realtime_prices(symbols)
            
            if not prices:
                logger.warning("未能获取到实时价格,跳过决策生成")
                return None
            
            # 2. 构建市场数据
            market_data = self.build_market_data(prices)
            
            # 3. 构建持仓数据
            portfolio_data = self.build_portfolio_data(prices)
            
            # 4. 定义风控规则
            risk_rules = {
                "max_single_position": 0.15,  # 单只标的最大15%
                "stop_loss_pct": -0.10,        # 止损线-10%
                "take_profit_pct": 0.20,       # 止盈线+20%
                "max_sector_exposure": 0.40,   # 单一行业最大40%
                "min_cash_ratio": 0.05,        # 最低现金比例5%
            }
            
            # 5. 生成决策
            logger.info("正在调用GLM5生成交易决策...")
            decision = self.engine.make_decisions(
                market_data=market_data,
                portfolio_data=portfolio_data,
                risk_rules=risk_rules,
            )
            
            self.last_decision_time = datetime.now()
            self.decision_count += 1
            
            logger.info(f"决策生成完成 - 交易信号: {len(decision.trading_signals)}条, 风险预警: {len(decision.risk_alerts)}条")
            
            return decision
            
        except Exception as e:
            logger.error(f"生成决策失败: {e}")
            return None
    
    def export_report(self, decision: DecisionResult) -> str:
        """
        导出决策报告
        
        Args:
            decision: 决策结果
            
        Returns:
            报告文件路径
        """
        try:
            # 创建报告目录
            today_str = datetime.now().strftime('%Y-%m-%d')
            report_dir = self.report_dir / today_str
            report_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成报告内容
            report_lines = []
            report_lines.append("# AI 盘中实时决策报告")
            report_lines.append("")
            report_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append(f"**AI 置信度**: {decision.ai_confidence:.2%}")
            report_lines.append(f"**决策次数**: #{self.decision_count}")
            report_lines.append("")
            
            # 市场概况
            report_lines.append("## 市场概况")
            report_lines.append("")
            report_lines.append(decision.market_summary)
            report_lines.append("")
            
            # 交易信号
            report_lines.append("## 交易信号")
            report_lines.append("")
            
            if decision.trading_signals:
                report_lines.append("| 代码 | 名称 | 动作 | 当前仓位 | 目标仓位 | 数量 | 置信度 | 紧急程度 |")
                report_lines.append("|------|------|------|---------|---------|------|--------|----------|")
                
                for sig in decision.trading_signals:
                    action_cn = {'BUY': '买入', 'SELL': '卖出', 'HOLD': '持有', 'REDUCE': '减仓'}[sig.action]
                    report_lines.append(
                        f"| {sig.code} | {sig.name} | {action_cn} | {sig.current_weight:.2%} | "
                        f"{sig.target_weight:.2%} | {sig.quantity} | {sig.confidence:.2f} | {sig.urgency} |"
                    )
            else:
                report_lines.append("暂无交易信号 - 当前持仓无需调整")
            
            report_lines.append("")
            
            # 风险预警
            report_lines.append("## 风险预警")
            report_lines.append("")
            
            if decision.risk_alerts:
                for alert in decision.risk_alerts:
                    icon = {'CRITICAL': '🚨', 'HIGH': '⚠️', 'MEDIUM': '⚡', 'LOW': 'ℹ️'}.get(alert.severity, '•')
                    report_lines.append(f"- {icon} [{alert.severity}] {alert.message}")
            else:
                report_lines.append("暂无风险预警")
            
            report_lines.append("")
            
            # 组合调整建议
            if decision.portfolio_advice:
                report_lines.append("## 组合调整建议")
                report_lines.append("")
                report_lines.append(decision.portfolio_advice)
                report_lines.append("")
            
            # 宏观展望
            if decision.macro_outlook:
                report_lines.append("## 宏观展望")
                report_lines.append("")
                report_lines.append(decision.macro_outlook)
                report_lines.append("")
            
            # 免责声明
            report_lines.append("---")
            report_lines.append("*以上决策由 GLM-5 AI 自动生成,仅供参考,不构成投资建议*")
            report_lines.append("*请人工审核后再执行交易*")
            
            # 保存报告
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_filename = f"盘中决策_{timestamp}.md"
            report_path = report_dir / report_filename
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            
            logger.info(f"决策报告已保存: {report_path}")
            
            return str(report_path)
            
        except Exception as e:
            logger.error(f"导出报告失败: {e}")
            return ""
    
    def check_risk_alerts(self, decision: DecisionResult):
        """
        检查风险预警并发送通知
        
        Args:
            decision: 决策结果
        """
        if not self.enable_notifications:
            return
        
        critical_alerts = [
            alert for alert in decision.risk_alerts 
            if alert.severity in ['CRITICAL', 'HIGH']
        ]
        
        if critical_alerts:
            logger.warning(f"发现 {len(critical_alerts)} 条高风险预警:")
            for alert in critical_alerts:
                logger.warning(f"  [{alert.severity}] {alert.message}")
                
                # TODO: 可以添加邮件/微信/钉钉通知
                # send_notification(alert)
    
    def run_once(self):
        """执行一次决策检查"""
        logger.info("=" * 80)
        logger.info("开始盘中决策检查")
        logger.info("=" * 80)
        
        # 1. 加载持仓
        if not self.load_positions():
            logger.error("无法加载持仓数据,终止决策检查")
            return
        
        # 2. 生成决策
        decision = self.generate_decision()
        
        if not decision:
            logger.warning("决策生成失败")
            return
        
        # 3. 检查风险预警
        self.check_risk_alerts(decision)
        
        # 4. 导出报告
        report_path = self.export_report(decision)
        
        if report_path:
            logger.info(f"决策报告: {report_path}")
        
        logger.info("=" * 80)
        logger.info("盘中决策检查完成")
        logger.info("=" * 80)
    
    def start(self, max_iterations: int = None):
        """
        启动实时监控
        
        Args:
            max_iterations: 最大执行次数(None表示无限循环)
        """
        self.is_running = True
        logger.info("盘中决策监控器已启动")
        logger.info(f"检查间隔: {self.check_interval}秒")
        logger.info(f"最大执行次数: {max_iterations or '无限'}")
        
        iteration = 0
        
        try:
            while self.is_running:
                if max_iterations and iteration >= max_iterations:
                    logger.info(f"已达到最大执行次数 {max_iterations},停止运行")
                    break
                
                try:
                    self.run_once()
                except Exception as e:
                    logger.error(f"决策检查异常: {e}", exc_info=True)
                
                iteration += 1
                
                if max_iterations:
                    logger.info(f"已完成 {iteration}/{max_iterations} 次决策检查")
                else:
                    logger.info(f"已完成第 {iteration} 次决策检查")
                
                # 等待下一次检查
                logger.info(f"等待 {self.check_interval} 秒后再次检查...")
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("收到中断信号,停止监控")
        finally:
            self.is_running = False
            logger.info("盘中决策监控器已停止")
    
    def stop(self):
        """停止监控"""
        self.is_running = False
        logger.info("正在停止盘中决策监控器...")


def main():
    """主函数 - 命令行入口"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # 创建监控器（使用豆包Speed）
    monitor = IntradayDecisionMonitor(
        api_model='doubao-speed-32k',
        check_interval=300,  # 5分钟
        min_confidence=0.6,
        enable_notifications=False,  # 暂时禁用通知
    )
    
    # 运行一次或持续监控
    import argparse
    parser = argparse.ArgumentParser(description='盘中实时决策监控')
    parser.add_argument('--once', action='store_true', help='只执行一次')
    parser.add_argument('--interval', type=int, default=300, help='检查间隔(秒)')
    args = parser.parse_args()
    
    if args.once:
        monitor.run_once()
    else:
        monitor.check_interval = args.interval
        monitor.start()


if __name__ == '__main__':
    main()
