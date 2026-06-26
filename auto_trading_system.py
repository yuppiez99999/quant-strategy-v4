# -*- coding: utf-8 -*-
"""
自动交易系统 - 盘中再平衡 + 收盘报告
功能: 实时行情监控、自动再平衡、收盘报告自动生成
"""

import os
import sys
import time
import yaml
import json
import subprocess
import schedule
from datetime import datetime, time as dt_time
from threading import Thread

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WIND_CLI = os.environ.get(
    "WIND_CLI_PATH",
    os.path.expandvars(r"%USERPROFILE%\.agents\skills\wind-mcp-skill\scripts\cli.mjs")
)

class WindDataProvider:
    # 价格合理范围 (防止API返回错误数据)
    PRICE_RANGES = {
        'etf': (0.5, 50),       # ETF通常在1-20元
        'stock': (1, 5000),     # A股1-5000元
        'bond_fund': (0.8, 1.5), # 债券基金净值范围
        'enhanced_fund': (0.5, 5), # 增强型基金净值范围
    }

    @staticmethod
    def _validate_price(code, price):
        """校验价格是否在合理范围"""
        # ===== 权益组合标的 =====
        if code == '518880':
            return 5 <= price <= 15  # 华安黄金ETF合理范围
        if code == '510300':
            return 3 <= price <= 8   # 沪深300ETF
        if code == '510500':
            return 4 <= price <= 12  # 中证500ETF
        if code == '512100':
            return 1 <= price <= 8   # 中证1000ETF
        if code == '588000':
            return 0.5 <= price <= 3 # 科创50ETF
        if code == '159915':
            return 1 <= price <= 5   # 创业板ETF
        if code == '515180':
            return 0.8 <= price <= 3 # 中证红利ETF
        if code == '512890':
            return 0.8 <= price <= 3 # 红利低波ETF
        if code == '510030':
            return 0.8 <= price <= 3 # 沪深300价值ETF
        if code == '515080':
            return 0.8 <= price <= 3 # 中证红利ETF(另一只)
        
        # ===== 低风险理财标的 =====
        if code in ('000105', '000084'):
            return 0.9 <= price <= 1.2  # 短债基金
        if code in ('000236', '000267'):
            return 0.8 <= price <= 1.3  # 信用债基金
        if code in ('340001', '001816', '040022'):
            return 0.8 <= price <= 2.0  # 可转债基金
        if code in ('000311', '163407'):
            return 0.5 <= price <= 3.0  # 增强型指数基金
        
        # 科创板688开头可能价格较高
        if code.startswith('688'):
            return 10 <= price <= 3000
        
        # 国债逆回购代码（204xxx沪/1318xx深）- 特殊处理（利率而非价格）
        if code.startswith('204') or code.startswith('1318'):
            return True  # 逆回购利率范围较广，由业务逻辑处理
        
        return True

    @staticmethod
    def get_realtime_price(code):
        """获取实时价格，按优先级降级: Wind MCP > iFinD MCP > 腾讯财经 > 新浪财经 > akshare"""
        # 1. Wind MCP (P0)
        price = WindDataProvider._get_wind_price(code)
        if price > 0:
            return price
        print(f"  🔄 {code}: Wind MCP不可用，尝试 iFinD MCP...", flush=True)

        # 1.5. iFinD MCP (P1)
        price = WindDataProvider._get_ifind_price(code)
        if price > 0:
            return price
        print(f"  🔄 {code}: iFinD MCP不可用，尝试腾讯财经...", flush=True)

        # 2. 腾讯财经 (P2)
        price = WindDataProvider._get_tencent_price(code)
        if price > 0:
            return price
        print(f"  🔄 {code}: 腾讯财经不可用，尝试新浪财经...", flush=True)

        # 3. 新浪财经 (P3)
        price = WindDataProvider._get_sina_price(code)
        if price > 0:
            return price
        print(f"  🔄 {code}: 新浪财经不可用，尝试akshare...", flush=True)

        # 4. akshare (P4 - 最终兜底)
        price = WindDataProvider._get_akshare_price(code)
        if price > 0:
            return price

        return 0

    @staticmethod
    def _get_wind_price(code):
        """通过Wind MCP获取实时价格 (P0)"""
        is_fund = code.startswith('5') or code in ('159915',)
        server = 'fund_data' if is_fund else 'stock_data'
        tool = 'get_fund_price_indicators' if is_fund else 'get_stock_price_indicators'

        if code.startswith('6') or code.startswith('5'):
            windcode = f'{code}.SH'
        else:
            windcode = f'{code}.SZ'

        payload = json.dumps({"windcode": windcode, "indexes": "最新成交价"})
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                r = subprocess.run(
                    ['node', WIND_CLI, 'call', server, tool, payload],
                    capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30
                )
                if r.stdout:
                    d = json.loads(r.stdout)
                    if d.get('content'):
                        rows = json.loads(d['content'][0]['text'])['data']['rows'][0]
                        price = float(rows[0])
                        if not WindDataProvider._validate_price(code, price):
                            print(f"  ⚠️ {code}: 价格异常 ￥{price:.2f}，已忽略", flush=True)
                            return 0
                        print(f"  📡 [Wind] {code}: ￥{price:.2f}", flush=True)
                        return price
                    elif d.get('ok') == False:
                        error_code = d.get('error', {}).get('code', '')
                        if 'QUOTA' in error_code:
                            print(f"  ⚠️ {code}: Wind配额超限", flush=True)
                            return 0
            except subprocess.TimeoutExpired:
                if attempt < max_retries:
                    print(f"  ⏱️ {code}: 获取超时，3秒后重试({attempt+1}/{max_retries})...", flush=True)
                    time.sleep(3)
                    continue
                print(f"  ⏱️ {code}: Wind获取超时", flush=True)
            except Exception as e:
                print(f"  ❌ {code}: Wind错误 {e}", flush=True)
        return 0

    @staticmethod
    def _get_ifind_price(code):
        """通过iFinD MCP获取实时价格 (P1)"""
        token = os.environ.get('IFIND_TOKEN', '')
        if not token:
            return 0
        try:
            from ifind_client import IFindClient, _parse_ifind_response, _col
            client = IFindClient(auth_token=token, max_concurrency=2)
            is_fund = code.startswith('5') or code in ('159915',)
            if is_fund:
                quotes = client.get_etf_quotes([code])
                if code in quotes:
                    q = quotes[code]
                    price = q.get('price', 0)
                    if WindDataProvider._validate_price(code, price) and price > 0:
                        print(f"  📡 [iFinD] {code}: ￥{price:.2f}", flush=True)
                        return price
            else:
                result = client.call("stock", "stock_daily", {
                    "query": f"{code}最近一天的开盘价、收盘价、最高价、最低价"
                })
                parsed = _parse_ifind_response(result)
                tables = parsed.get("tables", [])
                if tables:
                    last_row = tables[-1]
                    close_str = _col(last_row, "收盘价", "收盘") or "0"
                    try:
                        price = float(close_str)
                        if WindDataProvider._validate_price(code, price) and price > 0:
                            print(f"  📡 [iFinD] {code}: ￥{price:.2f}", flush=True)
                            return price
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            pass  # 静默失败，回退到下一层
        return 0

    @staticmethod
    def _get_tencent_price(code):
        """通过腾讯财经获取实时价格 (P2)"""
        try:
            import requests
            # 沪市: sh, 深市: sz
            if code.startswith('6') or code.startswith('5'):
                symbol = f'sh{code}'
            else:
                symbol = f'sz{code}'

            url = f'http://qt.gtimg.cn/q={symbol}'
            response = requests.get(url, timeout=10)
            response.encoding = 'gbk'

            if response.status_code == 200 and response.text:
                # 格式: v_sh600519="1~贵州茅台~600519~1800.00~...""
                text = response.text.strip()
                if '~' in text:
                    parts = text.split('"')[1].split('~')
                    if len(parts) > 3:
                        price = float(parts[3])
                        if WindDataProvider._validate_price(code, price) and price > 0:
                            print(f"  📡 [腾讯] {code}: ￥{price:.2f}", flush=True)
                            return price
        except Exception as e:
            print(f"  ❌ {code}: 腾讯财经失败 {e}", flush=True)
        return 0

    @staticmethod
    def _get_sina_price(code):
        """通过新浪财经获取实时价格 (P3)"""
        try:
            import requests
            if code.startswith('6') or code.startswith('5'):
                symbol = f'sh{code}'
            else:
                symbol = f'sz{code}'

            url = f'http://hq.sinajs.cn/list={symbol}'
            headers = {
                'Referer': 'https://finance.sina.com.cn',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'gbk'

            if response.status_code == 200 and response.text:
                # 格式: var hq_str_sh600519="贵州茅台,1800.00,..."
                parts = response.text.split('"')
                if len(parts) >= 2:
                    data = parts[1].split(',')
                    if len(data) >= 4:
                        # 当前价格(字段3)
                        price = float(data[3])
                        if WindDataProvider._validate_price(code, price) and price > 0:
                            print(f"  📡 [新浪] {code}: ￥{price:.2f}", flush=True)
                            return price
        except Exception as e:
            print(f"  ❌ {code}: 新浪财经失败 {e}", flush=True)
        return 0

    @staticmethod
    def _get_akshare_price(code):
        """通过akshare获取实时价格 (P4 - 最终兜底)"""
        try:
            os.environ.pop('HTTP_PROXY', None)
            os.environ.pop('HTTPS_PROXY', None)
            os.environ.pop('http_proxy', None)
            os.environ.pop('https_proxy', None)

            import akshare as ak

            if code.startswith('5') or code in ('159915',):
                df = ak.fund_etf_hist_em(symbol=code)
                if df is not None and len(df) > 0:
                    price = float(df.iloc[-1]['收盘'])
                    if WindDataProvider._validate_price(code, price):
                        print(f"  📡 [akshare] {code}: ￥{price:.2f}", flush=True)
                        return price
            else:
                df = ak.stock_zh_a_spot_em()
                if df is not None and len(df) > 0:
                    row = df[df['代码'] == code]
                    if not row.empty:
                        price = float(row.iloc[0]['最新价'])
                        if WindDataProvider._validate_price(code, price):
                            print(f"  📡 [akshare] {code}: ￥{price:.2f}", flush=True)
                            return price
        except Exception as e:
            print(f"  ❌ {code}: akshare失败 {e}", flush=True)
        return 0

class AutoTradingSystem:
    def __init__(self):
        self.load_config()
        self.initialize_account()
        self.is_running = False
        self.rebalance_threshold = 0.02
        self.last_rebalance_time = None
        
        # 豆包 Seed 2.0 Pro LLM 顾问（延迟初始化）
        self._llm_advisor = None
        try:
            from llm_report_analyzer import LLMTradingAdvisor
            self._llm_advisor = LLMTradingAdvisor(provider='volcengine')
            if self._llm_advisor.api_key:
                print(f"✅ 豆包 LLM顾问已就绪 (模型: {self._llm_advisor.model})")
            else:
                print("⚠️ VOLCENGINE_API_KEY 未配置，LLM决策不可用，将使用规则引擎")
                self._llm_advisor = None
        except ImportError:
            print("⚠️ llm_report_analyzer 未找到，将使用规则引擎")

    def _llm_rebalance(self, prices: dict, total_value: float) -> bool:
        """
        LLM驱动的再平衡决策。成功执行返回True，不可用时返回False回退规则引擎。
        """
        if not self._llm_advisor:
            return False

        portfolio_state = {
            "positions": self.positions,
            "prices": prices,
            "names": self.names,
            "target_weights": self.target_weights,
            "total_value": total_value,
            "cash": self.cash,
        }

        try:
            decision = self._llm_advisor.generate_rebalance_decision(portfolio_state)
        except Exception as e:
            print(f"  ⚠️ LLM决策异常: {e}，回退规则引擎", flush=True)
            return False

        if decision.get("source") == "mock" or not decision.get("actions"):
            return False

        print(f"  🧠 豆包 Seed 2.0 Pro 决策: {decision.get('rationale', '')}", flush=True)

        trades_executed = 0
        for act in decision["actions"]:
            code = act.get("code", "")
            action = act.get("action", "hold")
            shares = act.get("shares", 0)

            # 安全校验
            if code not in self.codes or action == "hold":
                continue
            if not isinstance(shares, (int, float)) or shares < 100:
                continue
            shares = int(shares // 100) * 100  # 强制100整数倍
            if shares < 100:
                continue
            if code not in prices or prices[code] <= 0:
                continue

            # 单笔上限：不超过总仓位10%
            max_amount = total_value * 0.10
            if shares * prices[code] > max_amount:
                shares = int(max_amount / prices[code] / 100) * 100
                if shares < 100:
                    continue

            success, msg = self.execute_trade(code, action, shares, prices[code])
            if success:
                print(f"  🤖 {msg} (LLM: {act.get('reason', '')})", flush=True)
                trades_executed += 1
            else:
                print(f"  ⚠️ {code} {action}失败: {msg}", flush=True)

        if trades_executed == 0:
            print("  ✅ LLM判断当前无需调仓", flush=True)
        return True
        
    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'portfolio.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.assets = self.config['assets']
        self.codes = [asset['code'] for asset in self.assets]
        self.names = {asset['code']: asset['name'] for asset in self.assets}
        self.target_weights = {asset['code']: asset['target_weight'] for asset in self.assets}
        self.commissions = {asset['code']: asset.get('commission', 0.0005) for asset in self.assets}
        
    def initialize_account(self):
        self.initial_capital = 3000000
        self.cash = self.initial_capital
        self.positions = {}
        self.trade_history = []
        self.load_positions()
        
    def load_positions(self):
        positions_file = os.path.join(os.path.dirname(__file__), 'config', 'positions.json')
        if os.path.exists(positions_file):
            try:
                with open(positions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.positions = data.get('positions', {})
                    self.cash = data.get('cash', self.initial_capital)
                    print(f"✅ 已加载持仓数据")
            except Exception as e:
                print(f"加载持仓失败，使用初始状态: {e}")
                
    def save_positions(self, prices=None):
        positions_file = os.path.join(os.path.dirname(__file__), 'config', 'positions.json')
        now = datetime.now()
        data = {
            'positions': self.positions,
            'cash': self.cash,
            'last_update': now.isoformat()
        }
        if prices:
            data['prices'] = prices
            data['total_value'] = self.get_total_value(prices)
        with open(positions_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 追加价格历史快照
        if prices:
            history_file = os.path.join(os.path.dirname(__file__), 'config', 'price_history.jsonl')
            snapshot = {
                'time': now.strftime('%H:%M:%S'),
                'timestamp': now.isoformat(),
                'prices': prices,
                'total_value': data.get('total_value', 0),
                'cash': self.cash,
                'positions': {k: v.get('shares', 0) for k, v in self.positions.items()}
            }
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(snapshot, ensure_ascii=False) + '\n')
            
    def get_realtime_prices(self):
        prices = {}
        for code in self.codes:
            price = WindDataProvider.get_realtime_price(code)
            if price > 0:
                prices[code] = price
        return prices
    
    def get_total_value(self, prices):
        """计算账户总值（优先实时价，回退成本价）"""
        total = self.cash
        for code, pos in self.positions.items():
            price = prices.get(code, 0) or pos.get('avg_cost', 0)
            total += pos['shares'] * price
        return total
    
    def execute_trade(self, code, side, shares, price):
        name = self.names.get(code, code)
        commission = self.commissions.get(code, 0.0005)
        
        if side == 'buy':
            cost = shares * price
            commission_fee = cost * commission
            total_cost = cost + commission_fee
            
            if total_cost > self.cash:
                return False, f"资金不足"
            
            self.cash -= total_cost
            
            if code not in self.positions:
                self.positions[code] = {'shares': 0, 'avg_cost': 0}
            
            old_cost = self.positions[code]['shares'] * self.positions[code]['avg_cost']
            self.positions[code]['shares'] += shares
            self.positions[code]['avg_cost'] = (old_cost + cost) / self.positions[code]['shares']
            
            result = f"买入 {name} {shares}股 @ ￥{price:.2f}"
        
        else:
            if code not in self.positions or self.positions[code]['shares'] < shares:
                return False, "持仓不足"
            
            revenue = shares * price
            commission_fee = revenue * commission
            net_revenue = revenue - commission_fee
            
            self.positions[code]['shares'] -= shares
            if self.positions[code]['shares'] == 0:
                del self.positions[code]
            
            self.cash += net_revenue
            result = f"卖出 {name} {shares}股 @ ￥{price:.2f}"
        
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.trade_history.append({
            'datetime': now_str,
            'code': code,
            'name': name,
            'side': side,
            'shares': shares,
            'price': price,
            'commission': commission_fee
        })
        
        self.save_positions()
        return True, result
    
    def rebalance(self):
        now = datetime.now()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n📊 [{now_str}] 执行自动再平衡...", flush=True)
        prices = self.get_realtime_prices()

        if not prices:
            print("❌ 无法获取行情数据", flush=True)
            return

        total_value = self.get_total_value(prices)
        print(f"账户总值: ￥{total_value:,.2f}", flush=True)
        
        # ── 优先使用豆包 Seed 2.0 Pro LLM 决策 ──
        if self._llm_rebalance(prices, total_value):
            self.save_positions(prices)
            self.last_rebalance_time = datetime.now()
            return

        # ── LLM 不可用时回退到规则引擎 ──
        print("  ⚙️ 使用规则引擎再平衡...", flush=True)
        trades_executed = 0
        
        # 第一遍：先卖出超配标的（回笼资金）
        for code in self.codes:
            if code not in prices or prices[code] <= 0:
                continue
            
            target_weight = self.target_weights[code]
            target_amount = total_value * target_weight
            
            current_shares = self.positions.get(code, {}).get('shares', 0)
            current_amount = current_shares * prices[code]
            
            diff_amount = target_amount - current_amount
            diff_ratio = abs(diff_amount) / total_value
            
            # 只处理卖出（超配）
            if diff_ratio < self.rebalance_threshold:
                continue
            if diff_amount >= 0:
                continue  # 跳过买入，第二轮处理
            
            price = prices[code]
            shares = int(abs(diff_amount) / price / 100) * 100
            
            if shares >= 100:
                success, msg = self.execute_trade(code, 'sell', shares, price)
                if success:
                    print(f"  📤 {msg}", flush=True)
                    trades_executed += 1
                else:
                    print(f"  ❌ {msg}", flush=True)
        
        # 第二遍：再买入低配标的（使用卖出回笼的资金）
        for code in self.codes:
            if code not in prices or prices[code] <= 0:
                continue
            
            target_weight = self.target_weights[code]
            target_amount = total_value * target_weight
            
            current_shares = self.positions.get(code, {}).get('shares', 0)
            current_amount = current_shares * prices[code]
            
            diff_amount = target_amount - current_amount
            diff_ratio = abs(diff_amount) / total_value
            
            if diff_ratio < self.rebalance_threshold:
                continue
            if diff_amount <= 0:
                continue  # 卖出已在第一轮处理
            
            price = prices[code]
            shares = int(abs(diff_amount) / price / 100) * 100
            
            if shares >= 100:
                success, msg = self.execute_trade(code, 'buy', shares, price)
                if success:
                    print(f"  📥 {msg}", flush=True)
                    trades_executed += 1
                else:
                    print(f"  ❌ {msg}", flush=True)
        
        if trades_executed == 0:
            print("  ✅ 当前权重在阈值范围内，无需操作")
        
        # 保存持仓和价格快照
        self.save_positions(prices)
        
        self.last_rebalance_time = datetime.now()

    def generate_daily_report(self):
        now = datetime.now()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')
        today_str = now.strftime('%Y-%m-%d')
        print(f"\n📝 [{now_str}] 生成收盘报告...")
        prices = self.get_realtime_prices()
        total_value = self.get_total_value(prices)

        report = f"""================================================================================
📊 {today_str} 收盘持仓报告
生成时间: {now_str}
================================================================================

💰 账户总览
------------------------------------------------------------
  持仓市值: ￥{total_value - self.cash:,.2f}
  可用现金: ￥{self.cash:,.2f}
  账户总值: ￥{total_value:,.2f}
  总收益率: {(total_value - self.initial_capital) / self.initial_capital * 100:+.2f}%

📋 持仓明细
------------------------------------------------------------
"""
        
        for code in self.codes:
            if code in self.positions:
                shares = self.positions[code]['shares']
                price = prices.get(code, 0) or self.positions[code].get('avg_cost', 0)
                market_value = shares * price
                weight = (market_value / total_value) * 100 if total_value > 0 else 0
                target_weight = self.target_weights[code] * 100
                diff = weight - target_weight
                
                status = "✅" if abs(diff) < 2 else "⚠️"
                report += f"  {status} {self.names[code]:<12} {code:<10} {shares:>6}股  @ ￥{price:>7.2f}  市值: ￥{market_value:>10,.2f}  权重: {weight:>5.1f}% (目标:{target_weight:.1f}%) [偏差:{diff:+.1f}%]\n"
        
        report += f"""
📈 今日交易记录
------------------------------------------------------------
"""
        
        today_trades = [t for t in self.trade_history if t['datetime'].startswith(today_str)]

        if today_trades:
            for trade in today_trades:
                report += f"  • {trade['datetime']} {trade['side']} {trade['name']} {trade['shares']}股 @ ￥{trade['price']:.2f}\n"
        else:
            report += "  • 今日无交易\n"

        report += f"""
================================================================================
报告已归档 | 数据来源: Wind API
================================================================================
"""

        report_dir = os.path.join(os.path.dirname(__file__), 'reports', today_str)
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, f'daily_report_{now.strftime("%H%M%S")}.txt')
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        archive_dir = os.path.join(os.path.dirname(__file__), '..', '每日报告归档', today_str)
        os.makedirs(archive_dir, exist_ok=True)
        archive_path = os.path.join(archive_dir, f'综合日报_{now.strftime("%Y%m%d")}.txt')
        
        with open(archive_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ 报告已保存: {report_path}")
        print(f"✅ 报告已归档: {archive_path}")
        
        return report
    
    def is_trading_hours(self):
        now = datetime.now().time()
        return dt_time(9, 30) <= now <= dt_time(11, 30) or dt_time(13, 0) <= now <= dt_time(15, 0)
    
    def run(self, until_time=None, pidfile=None):
        """
        启动实时监控循环
        :param until_time: 可选的自动退出时间，格式 'HH:MM'（例如 '15:00'）。
                           到点后会生成一次收盘报告再退出。
        :param pidfile:    可选的 PID 文件路径，用于外部监控。
        """
        print("🚀 自动交易系统启动")
        print(f"{'='*70}")
        print(f"📊 标的数量: {len(self.codes)}")
        print(f"💰 初始资金: ￥{self.initial_capital:,.0f}")
        print(f"⏱️ 再平衡间隔: 每30分钟")
        print(f"🎯 再平衡阈值: ±{self.rebalance_threshold*100}%")
        if until_time:
            print(f"🛑 自动退出时间: {until_time}")
        print(f"{'='*70}", flush=True)

        # PID 文件，便于外部监控
        if pidfile:
            try:
                with open(pidfile, 'w', encoding='utf-8') as f:
                    f.write(str(os.getpid()))
                print(f"🪪 PID 已写入: {pidfile}", flush=True)
            except Exception as e:
                print(f"⚠️  写入 PID 失败: {e}", flush=True)

        schedule.clear()
        schedule.every(30).minutes.do(self.scheduled_rebalance)
        schedule.every().day.at("15:05").do(self.generate_daily_report)

        # 解析 until_time: HH:MM 或 datetime
        until_dt = None
        if isinstance(until_time, str) and len(until_time) >= 5:
            try:
                hh, mm = until_time.split(':')[:2]
                now = datetime.now()
                today = now.date()
                until_dt = datetime.combine(today, dt_time(int(hh), int(mm)))
                if until_dt < now:
                    from datetime import timedelta
                    until_dt = until_dt + timedelta(days=1)
                print(f"🛑 已设置自动退出时间: {until_dt:%Y-%m-%d %H:%M}", flush=True)
            except Exception as e:
                print(f"⚠️  无法解析 until_time '{until_time}': {e}，将持续运行", flush=True)
                until_dt = None

        # 启动时立即执行一次再平衡（如果在交易时间内）
        if self.is_trading_hours():
            print("⚡ 启动时立即执行首次再平衡...", flush=True)
            try:
                self.rebalance()
            except Exception as e:
                print(f"⚠️  首次再平衡出现异常：{e}", flush=True)
        else:
            print("⏰ 当前非交易时间，等待开盘...", flush=True)

        self.is_running = True
        last_heartbeat = 0

        try:
            while self.is_running:
                if until_dt and datetime.now() >= until_dt:
                    print(f"\n🛑 到达自动退出时间 {until_time}，执行收尾...", flush=True)
                    try:
                        self.generate_daily_report()
                    except Exception as e:
                        print(f"⚠️  退出前报告生成异常：{e}", flush=True)
                    self.stop()
                    break
                schedule.run_pending()
                time.sleep(60)
                # 每5分钟输出心跳
                now_abs = int(time.time())
                if now_abs - last_heartbeat >= 300:
                    print(f"💓 [{datetime.now().strftime('%H:%M:%S')}] 系统运行中... (下次检查: {schedule.next_run()})", flush=True)
        except KeyboardInterrupt:
            print("\n⏹️ 用户中断", flush=True)
        finally:
            # 退出前再强制尝试一次收尾报告（如果还没生成过）
            if self.is_running:
                try:
                    self.generate_daily_report()
                except Exception:
                    pass
            self.stop()
            if pidfile and os.path.exists(pidfile):
                try:
                    os.remove(pidfile)
                except OSError:
                    pass
    
    def scheduled_rebalance(self):
        if self.is_trading_hours():
            self.rebalance()
        else:
            print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 非交易时间，跳过再平衡", flush=True)
    
    def stop(self):
        self.is_running = False
        print("\n✅ 系统已停止")

def main():
    system = AutoTradingSystem()
    system.run()

if __name__ == "__main__":
    main()