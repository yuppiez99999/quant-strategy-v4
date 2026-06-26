#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
盘中监控脚本 - 股票及国家队ETF加仓异动监控
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Optional

# 设置编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 导入新浪API
try:
    from sina_api_helper import batch_get_sina_prices, get_sina_kline_latest
except ImportError:
    print("错误: 请确保 sina_api_helper.py 在同一目录")
    sys.exit(1)

# 监控配置
class MonitorConfig:
    # 国家队ETF列表
    ETF_LIST = [
        {"code": "sh510300", "name": "沪深300ETF华泰柏瑞", "category": "宽基核心"},
        {"code": "sh510310", "name": "沪深300ETF易方达", "category": "宽基核心"},
        {"code": "sz159919", "name": "沪深300ETF嘉实", "category": "宽基核心"},
        {"code": "sh510500", "name": "中证500ETF南方", "category": "宽基核心"},
        {"code": "sh510050", "name": "上证50ETF华夏", "category": "蓝筹核心"},
        {"code": "sz159915", "name": "创业板ETF易方达", "category": "成长科技"},
        {"code": "sh588000", "name": "科创50ETF华夏", "category": "成长科技"},
        {"code": "sh560010", "name": "中证1000ETF富国", "category": "小盘风格"},
        {"code": "sh515080", "name": "中证红利ETF易方达", "category": "防御红利"},
        {"code": "sh512880", "name": "证券ETF国泰", "category": "金融主题"},
        {"code": "sh512800", "name": "银行ETF华宝", "category": "金融主题"},
        {"code": "sh512170", "name": "医疗ETF华宝", "category": "医药主题"},
        {"code": "sh512760", "name": "半导体ETF国泰", "category": "科技主题"},
        {"code": "sh515030", "name": "新能源车ETF华夏", "category": "新能源主题"},
        {"code": "sh518880", "name": "黄金ETF华安", "category": "避险资产"},
    ]
    
    # 股票监控列表
    STOCK_LIST = [
        {"code": "sh601088", "name": "中国神华"},
        {"code": "sh600995", "name": "南网储能"},
        {"code": "sh600276", "name": "恒瑞医药"},
        {"code": "sz002371", "name": "北方华创"},
        {"code": "sh688017", "name": "绿的谐波"},
        {"code": "sh688981", "name": "中芯国际"},
        {"code": "sz300750", "name": "宁德时代"},
        {"code": "sz300124", "name": "汇川技术"},
        {"code": "sz002475", "name": "立讯精密"},
        {"code": "sh603259", "name": "药明康德"},
    ]
    
    # 异动阈值
    THRESHOLD = {
        "price_change_high": 5.0,      # 涨幅>5%为强烈信号
        "price_change_medium": 3.0,    # 涨幅>3%为中等信号
        "price_change_low": 2.0,       # 涨幅>2%为关注信号
        "volume_threshold": 20000000,  # 成交额>2亿关注
        "etf_flow_high": 50,           # ETF净流入>50亿为强烈信号
        "etf_flow_medium": 10,         # ETF净流入>10亿为中等信号
        "etf_flow_low": 2,             # ETF净流入>2亿为关注信号
    }

class LiveMonitor:
    def __init__(self):
        self.etf_data = {}
        self.stock_data = {}
        self.signals = []
        self.last_update = None
    
    def fetch_data(self):
        """获取实时行情数据"""
        print("📡 正在获取实时行情数据...")
        
        # 获取ETF数据
        etf_codes = [etf["code"] for etf in MonitorConfig.ETF_LIST]
        print(f"   获取 {len(etf_codes)} 只ETF数据...")
        self.etf_data = batch_get_sina_prices(etf_codes)
        
        # 获取股票数据
        stock_codes = [stock["code"] for stock in MonitorConfig.STOCK_LIST]
        print(f"   获取 {len(stock_codes)} 只股票数据...")
        self.stock_data = batch_get_sina_prices(stock_codes)
        
        self.last_update = datetime.now()
        print(f"✅ 数据获取完成 ({self.last_update.strftime('%H:%M:%S')})")
    
    def detect_etf_signals(self) -> List[Dict]:
        """检测ETF异动信号"""
        signals = []
        
        for etf in MonitorConfig.ETF_LIST:
            code = etf["code"]
            data = self.etf_data.get(code)
            
            if not data:
                continue
            
            price = data.get("price", 0)
            change = data.get("change", 0)
            amount = data.get("amount", 0)
            volume = data.get("volume", 0)
            
            # 估算资金流向（简化版）
            net_flow_yi = (amount / 1e8) * (1 if change >= 0 else -1)
            
            # 检测信号
            if net_flow_yi >= MonitorConfig.THRESHOLD["etf_flow_high"]:
                signals.append({
                    "type": "ETF",
                    "code": code,
                    "name": etf["name"],
                    "category": etf["category"],
                    "signal": "强加仓信号",
                    "confidence": "高",
                    "change": change,
                    "price": price,
                    "net_flow_yi": net_flow_yi,
                    "amount_yi": amount / 1e8
                })
            elif net_flow_yi >= MonitorConfig.THRESHOLD["etf_flow_medium"]:
                signals.append({
                    "type": "ETF",
                    "code": code,
                    "name": etf["name"],
                    "category": etf["category"],
                    "signal": "加仓信号",
                    "confidence": "中",
                    "change": change,
                    "price": price,
                    "net_flow_yi": net_flow_yi,
                    "amount_yi": amount / 1e8
                })
            elif net_flow_yi >= MonitorConfig.THRESHOLD["etf_flow_low"]:
                signals.append({
                    "type": "ETF",
                    "code": code,
                    "name": etf["name"],
                    "category": etf["category"],
                    "signal": "关注信号",
                    "confidence": "低",
                    "change": change,
                    "price": price,
                    "net_flow_yi": net_flow_yi,
                    "amount_yi": amount / 1e8
                })
            elif net_flow_yi <= -MonitorConfig.THRESHOLD["etf_flow_high"]:
                signals.append({
                    "type": "ETF",
                    "code": code,
                    "name": etf["name"],
                    "category": etf["category"],
                    "signal": "强减仓信号",
                    "confidence": "高",
                    "change": change,
                    "price": price,
                    "net_flow_yi": net_flow_yi,
                    "amount_yi": amount / 1e8
                })
        
        return signals
    
    def detect_stock_signals(self) -> List[Dict]:
        """检测股票异动信号"""
        signals = []
        
        for stock in MonitorConfig.STOCK_LIST:
            code = stock["code"]
            data = self.stock_data.get(code)
            
            if not data:
                continue
            
            price = data.get("price", 0)
            change = data.get("change", 0)
            amount = data.get("amount", 0)
            volume = data.get("volume", 0)
            high = data.get("high", 0)
            low = data.get("low", 0)
            
            # 检测价格异动
            if abs(change) >= MonitorConfig.THRESHOLD["price_change_high"]:
                signals.append({
                    "type": "STOCK",
                    "code": code,
                    "name": stock["name"],
                    "signal": "强烈异动" if change > 0 else "强烈下跌",
                    "confidence": "高",
                    "change": change,
                    "price": price,
                    "high": high,
                    "low": low,
                    "amount_yi": amount / 1e8,
                    "volume": volume
                })
            elif abs(change) >= MonitorConfig.THRESHOLD["price_change_medium"]:
                signals.append({
                    "type": "STOCK",
                    "code": code,
                    "name": stock["name"],
                    "signal": "中等异动" if change > 0 else "中等下跌",
                    "confidence": "中",
                    "change": change,
                    "price": price,
                    "high": high,
                    "low": low,
                    "amount_yi": amount / 1e8,
                    "volume": volume
                })
            elif abs(change) >= MonitorConfig.THRESHOLD["price_change_low"]:
                signals.append({
                    "type": "STOCK",
                    "code": code,
                    "name": stock["name"],
                    "signal": "小幅异动" if change > 0 else "小幅下跌",
                    "confidence": "低",
                    "change": change,
                    "price": price,
                    "high": high,
                    "low": low,
                    "amount_yi": amount / 1e8,
                    "volume": volume
                })
        
        return signals
    
    def generate_report(self) -> str:
        """生成监控报告"""
        etf_signals = self.detect_etf_signals()
        stock_signals = self.detect_stock_signals()
        
        report_lines = []
        now = datetime.now()
        
        report_lines.append("=" * 80)
        report_lines.append(f"📊 盘中监控报告 - 股票及国家队ETF异动监控")
        report_lines.append(f"生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 80)
        
        # ETF资金流向概览
        report_lines.append("\n📈 ETF国家队资金流向")
        report_lines.append("-" * 60)
        
        total_flow = 0
        positive_count = 0
        
        for etf in MonitorConfig.ETF_LIST:
            code = etf["code"]
            data = self.etf_data.get(code)
            
            if data:
                change = data.get("change", 0)
                amount = data.get("amount", 0)
                net_flow = (amount / 1e8) * (1 if change >= 0 else -1)
                total_flow += net_flow
                if net_flow > 0:
                    positive_count += 1
        
        report_lines.append(f"  监测ETF数: {len(MonitorConfig.ETF_LIST)}")
        report_lines.append(f"  净流入ETF: {positive_count}只")
        report_lines.append(f"  合计净流入: {total_flow:+.2f}亿")
        
        # ETF详细数据
        report_lines.append("\n  ETF详情:")
        report_lines.append("  " + "-" * 56)
        report_lines.append(f"  {'名称':<16} {'代码':<10} {'价格':>8} {'涨跌':>8} {'成交额(亿)':>12}")
        report_lines.append("  " + "-" * 56)
        
        for etf in MonitorConfig.ETF_LIST:
            code = etf["code"]
            data = self.etf_data.get(code)
            
            if data:
                price = data.get("price", 0)
                change = data.get("change", 0)
                amount = data.get("amount", 0)
                
                icon = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                report_lines.append(
                    f"  {icon} {etf['name'][:15]:<16} {code:<10} {price:>8.2f} {change:>+8.2f}% {amount/1e8:>12.2f}"
                )
            else:
                report_lines.append(f"  ❓ {etf['name'][:15]:<16} {code:<10} {'-':>8} {'-':>8} {'-':>12}")
        
        # 股票监控概览
        report_lines.append("\n📉 持仓股票监控")
        report_lines.append("-" * 60)
        
        up_count = sum(1 for stock in MonitorConfig.STOCK_LIST 
                       if self.stock_data.get(stock["code"]) and self.stock_data.get(stock["code"]).get("change", 0) > 0)
        
        report_lines.append(f"  监测股票数: {len(MonitorConfig.STOCK_LIST)}")
        report_lines.append(f"  上涨股票: {up_count}只")
        report_lines.append(f"  下跌股票: {len(MonitorConfig.STOCK_LIST) - up_count}只")
        
        # 股票详细数据
        report_lines.append("\n  股票详情:")
        report_lines.append("  " + "-" * 56)
        report_lines.append(f"  {'名称':<12} {'代码':<10} {'价格':>8} {'涨跌':>8} {'成交额(亿)':>12}")
        report_lines.append("  " + "-" * 56)
        
        for stock in MonitorConfig.STOCK_LIST:
            code = stock["code"]
            data = self.stock_data.get(code)
            
            if data:
                price = data.get("price", 0)
                change = data.get("change", 0)
                amount = data.get("amount", 0)
                
                icon = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                report_lines.append(
                    f"  {icon} {stock['name'][:11]:<12} {code:<10} {price:>8.2f} {change:>+8.2f}% {amount/1e8:>12.2f}"
                )
            else:
                report_lines.append(f"  ❓ {stock['name'][:11]:<12} {code:<10} {'-':>8} {'-':>8} {'-':>12}")
        
        # 异动信号汇总
        all_signals = etf_signals + stock_signals
        all_signals.sort(key=lambda x: (0 if x["confidence"] == "高" else 1 if x["confidence"] == "中" else 2), reverse=False)
        
        report_lines.append("\n🚨 异动信号汇总")
        report_lines.append("-" * 60)
        
        if all_signals:
            for sig in all_signals:
                conf_icon = "🔴" if sig["confidence"] == "高" else "🟡" if sig["confidence"] == "中" else "🟢"
                type_icon = "ETF" if sig["type"] == "ETF" else "股票"
                
                if sig["type"] == "ETF":
                    report_lines.append(
                        f"  {conf_icon} [{type_icon}] {sig['name']} ({sig['code']}): {sig['signal']} "
                        f"(净流入 {sig['net_flow_yi']:.2f}亿, 置信度:{sig['confidence']})"
                    )
                else:
                    report_lines.append(
                        f"  {conf_icon} [{type_icon}] {sig['name']} ({sig['code']}): {sig['signal']} "
                        f"(涨跌 {sig['change']:.2f}%, 置信度:{sig['confidence']})"
                    )
        else:
            report_lines.append("  ✅ 暂无明显异动信号")
        
        report_lines.append("\n" + "=" * 80)
        
        return "\n".join(report_lines)
    
    def run(self):
        """运行监控"""
        self.fetch_data()
        report = self.generate_report()
        print(report)
        
        # 保存报告
        report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, f'live_monitor_{datetime.now():%Y%m%d_%H%M%S}.md')
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(self.generate_report())
        
        print(f"\n📁 报告已保存: {report_path}")

def main():
    print("=" * 80)
    print("🚀 盘中监控系统启动 - 股票及国家队ETF加仓异动监控")
    print("=" * 80)
    
    monitor = LiveMonitor()
    monitor.run()
    
    print("\n✅ 监控完成")

if __name__ == '__main__':
    main()
