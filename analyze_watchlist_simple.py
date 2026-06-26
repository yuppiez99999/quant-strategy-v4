# -*- coding: utf-8 -*-
"""
大炼化一体化观察仓 Wind MCP 分析工具 - 简化版
"""

import os
import sys
import json
import time
from datetime import datetime

# 设置UTF-8输出
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 观察仓股票配置
WATCHLIST_STOCKS = [
    {'code': '600346', 'name': '恒力石化', 'sector': '石油化工', 'subsector': '炼化一体化', 
     'pe_ttm': 17.78, 'pb': 2.2, 'roe': 8.5, 'risk_rating': '中高',
     'catalysts': ['业绩超预期，Q1净利润+90.65%', '炼化价差扩大', '库存收益'],
     'risks': ['美国SDN制裁不确定性'],
     'notes': '中国最大民营炼化企业，2000万吨/年炼油+150万吨/年乙烯'},
    
    {'code': '002493', 'name': '荣盛石化', 'sector': '石油化工', 'subsector': '炼化一体化',
     'pe_ttm': '低位', 'pb': 1.8, 'roe': '回升中', 'risk_rating': '中高',
     'catalysts': ['浙石化4000万吨产能优势', '硫磺涨价提供业绩弹性', 'PX-PTA-聚酯链盈利修复'],
     'risks': ['行业产能过剩'],
     'notes': '全球最大PX、PTA生产商'},
    
    {'code': '000301', 'name': '东方盛虹', 'sector': '石油化工', 'subsector': '炼化新材料',
     'pe_ttm': '扭亏修复', 'pb': 1.6, 'roe': '1-2%', 'risk_rating': '高',
     'catalysts': ['2025年扭亏为盈', 'EVA、POE光伏材料布局领先', '盛虹炼化1600万吨产能'],
     'risks': ['前期亏损包袱'],
     'notes': '油头、煤头、气头多头并举'},
    
    {'code': '000059', 'name': '华锦股份', 'sector': '石油化工', 'subsector': '炼化一体化',
     'pe_ttm': '修复中', 'pb': 1.4, 'roe': '改善中', 'risk_rating': '中',
     'catalysts': ['央企背景，兵器工业集团', '向化工新材料转型', '碳捕集项目符合ESG'],
     'risks': ['传统业务占比高'],
     'notes': '辽宁、新疆双基地布局'},
    
    {'code': '002648', 'name': '卫星化学', 'sector': '化学原料', 'subsector': '轻烃化工',
     'pe_ttm': 12, 'pb': 1.91, 'roe': 20, 'risk_rating': '中',
     'catalysts': ['全球最大乙烷制乙烯生产商', 'α-烯烃产业园2026年投产', '新能源材料业务增长80.77%'],
     'risks': ['乙烷价格波动'],
     'notes': 'PB折价42.6%，上行空间约74%'},
    
    {'code': '601233', 'name': '桐昆股份', 'sector': '化纤', 'subsector': '涤纶长丝',
     'pe_ttm': 11, 'pb': 1.5, 'roe': '回升中', 'risk_rating': '中',
     'catalysts': ['全球涤纶长丝市占率18%', '2026Q1净利润+210.59%', '浙石化20%权益'],
     'risks': ['PTA价格承压'],
     'notes': '长丝产能1350万吨，PTA自给率87%'},
    
    {'code': '603225', 'name': '新凤鸣', 'sector': '化纤', 'subsector': '涤纶长丝',
     'pe_ttm': 14, 'pb': 1.8, 'roe': '改善中', 'risk_rating': '中',
     'catalysts': ['行业格局优化', 'PTA自给率137%', '印度出口改善'],
     'risks': ['产能过剩风险'],
     'notes': '涤纶长丝行业老二，长丝产能845万吨'},
]

# 投资策略分类
STRATEGY = {
    'short_term': ['600346', '601233'],      # 业绩确定性高
    'medium_term': ['002648', '002493'],      # 估值修复空间大
    'long_term': ['000301', '603225', '000059']  # 长期转型价值
}

def get_stock_names():
    """获取股票代码到名称的映射"""
    return {item['code']: item['name'] for item in WATCHLIST_STOCKS}

def analyze_stocks():
    """分析观察仓股票"""
    stock_codes = [item['code'] for item in WATCHLIST_STOCKS]
    stock_names = get_stock_names()
    
    print("\n" + "="*80)
    print("🎯 大炼化一体化观察仓 Wind MCP 深度分析")
    print("="*80)
    print(f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"标的数量: {len(stock_codes)} 只")
    print("-"*80)
    
    # 尝试导入并使用Wind数据提供者
    print("\n🔄 正在获取实时行情数据...")
    
    try:
        from wind_data_provider import get_quotes_batch, get_stats
        results = get_quotes_batch(stock_codes, [], max_workers=5)
        
        # 统计数据来源
        source_counts = {}
        for r in results.values():
            s = r.get('source', 'unknown')
            source_counts[s] = source_counts.get(s, 0) + 1
        
        print("\n📊 数据来源统计:")
        source_mapping = {
            'wind_analytics': 'Wind分析接口',
            'wind_direct': 'Wind直连接口',
            'ifind': 'iFinD',
            'akshare': 'akshare',
            'efinance': 'efinance',
            'sina': '新浪财经',
            'local_cache': '本地缓存',
            'fallback': '兜底价格',
            'failed': '查询失败'
        }
        for src, cnt in source_counts.items():
            print(f"  • {source_mapping.get(src, src)}: {cnt} 只")
    
    except Exception as e:
        print(f"⚠️ 无法连接Wind MCP，使用模拟数据: {e}")
        # 使用模拟数据
        results = {}
        for code in stock_codes:
            results[code] = {
                'price': 10.0 + (hash(code) % 100) / 10,
                'change': (hash(code) % 21 - 10) / 2,
                'source': 'simulation',
                'elapsed': 0.1
            }
    
    return results, stock_names

def generate_report(results, stock_names):
    """生成分析报告"""
    print("\n" + "="*80)
    print("📈 观察仓股票行情分析报告")
    print("="*80)
    
    # 按涨跌幅排序
    sorted_results = sorted(results.items(), key=lambda x: x[1]['change'], reverse=True)
    
    print(f"\n{'排名':<6} {'股票名称':<10} {'代码':<10} {'最新价':>10} {'涨跌幅':>10} {'数据来源':<12}")
    print("-"*80)
    
    for i, (code, data) in enumerate(sorted_results, 1):
        price = data['price']
        change = data['change']
        source = data['source']
        name = stock_names.get(code, code)
        
        source_icon = {
            'wind_analytics': '☁️Wind分析',
            'wind_direct': '⚡Wind直连',
            'ifind': '📡iFinD',
            'akshare': '📊akshare',
            'efinance': '💰efinance',
            'sina': '🌐新浪',
            'local_cache': '💾缓存',
            'fallback': '📌兜底',
            'simulation': '🔧模拟',
            'failed': '❌失败'
        }.get(source, source)
        
        if change >= 0:
            trend = "📈"
            change_str = f"+{change:.2f}%"
        else:
            trend = "📉"
            change_str = f"{change:.2f}%"
        
        print(f"{i:<6} {trend} {name:<10} {code:<10} ¥{price:>9.2f} {change_str:>10} {source_icon:<12}")
    
    # 详细分析
    print("\n" + "="*80)
    print("🔍 各股详细分析")
    print("="*80)
    
    for item in WATCHLIST_STOCKS:
        code = item['code']
        name = item['name']
        data = results.get(code, {})
        price = data.get('price', 0)
        change = data.get('change', 0)
        
        print(f"\n[{code}] {name}")
        print("-" * (len(name) + 10))
        print(f"• 行业: {item.get('sector', '-')} > {item.get('subsector', '-')}")
        print(f"• PE(TTM): {item.get('pe_ttm', '-')}")
        print(f"• PB: {item.get('pb', '-')}")
        print(f"• ROE: {item.get('roe', '-')}")
        print(f"• 风险评级: {item.get('risk_rating', '-')}")
        print(f"• 最新价: ¥{price:.2f}")
        print(f"• 涨跌幅: {'+' if change >= 0 else ''}{change:.2f}%")
        
        catalysts = item.get('catalysts', [])
        if catalysts:
            print(f"\n📊 催化剂:")
            for cat in catalysts:
                print(f"  → {cat}")
        
        risks = item.get('risks', [])
        if risks:
            print(f"\n⚠️ 风险因素:")
            for risk in risks:
                print(f"  → {risk}")
        
        notes = item.get('notes', '')
        if notes:
            print(f"\n📝 备注: {notes}")
    
    # 投资建议
    print("\n" + "="*80)
    print("💡 投资建议分类")
    print("="*80)
    
    if STRATEGY.get('short_term'):
        print("\n🔥 短期关注 (业绩确定性高):")
        for code in STRATEGY['short_term']:
            name = stock_names.get(code, code)
            price = results.get(code, {}).get('price', 0)
            print(f"  • [{code}] {name} - 最新价: ¥{price:.2f}")
    
    if STRATEGY.get('medium_term'):
        print("\n📈 中期布局 (估值修复空间大):")
        for code in STRATEGY['medium_term']:
            name = stock_names.get(code, code)
            price = results.get(code, {}).get('price', 0)
            print(f"  • [{code}] {name} - 最新价: ¥{price:.2f}")
    
    if STRATEGY.get('long_term'):
        print("\n🎯 长期持有 (转型价值):")
        for code in STRATEGY['long_term']:
            name = stock_names.get(code, code)
            price = results.get(code, {}).get('price', 0)
            print(f"  • [{code}] {name} - 最新价: ¥{price:.2f}")
    
    # 保存报告
    report_path = save_report(results, stock_names)
    print(f"\n📁 报告已保存: {report_path}")

def save_report(results, stock_names):
    """保存分析报告到文件"""
    report_dir = os.path.join(os.path.dirname(__file__), 'reports', datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(report_dir, exist_ok=True)
    
    # 保存MD格式报告
    md_report_file = os.path.join(report_dir, f"观察仓分析_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    with open(md_report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 大炼化一体化观察仓分析报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**标的数量**: {len(WATCHLIST_STOCKS)} 只\n\n")
        f.write("## 📈 行情概览\n\n")
        f.write("| 股票代码 | 名称 | 最新价 | 涨跌幅 |\n")
        f.write("|---------|------|--------|--------|\n")
        
        for item in WATCHLIST_STOCKS:
            code = item['code']
            data = results.get(code, {})
            f.write(f"| {code} | {item['name']} | ¥{data.get('price', 0):.2f} | {data.get('change', 0):+.2f}% |\n")
        
        f.write("\n## 🏷️ 标的详情\n\n")
        for item in WATCHLIST_STOCKS:
            f.write(f"### [{item['code']}] {item['name']}\n\n")
            f.write(f"- 行业: {item.get('sector', '-')}\n")
            f.write(f"- 子行业: {item.get('subsector', '-')}\n")
            f.write(f"- PE(TTM): {item.get('pe_ttm', '-')}\n")
            f.write(f"- PB: {item.get('pb', '-')}\n")
            f.write(f"- ROE: {item.get('roe', '-')}\n")
            f.write(f"- 风险评级: {item.get('risk_rating', '-')}\n\n")
    
    return md_report_file

def main():
    try:
        # 分析股票
        results, stock_names = analyze_stocks()
        
        # 生成报告
        generate_report(results, stock_names)
        
        print("\n🎉 分析完成!")
        
    except Exception as e:
        print(f"\n❌ 分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()