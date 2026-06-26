# -*- coding: utf-8 -*-
"""
大炼化一体化观察仓 Wind MCP 分析工具
使用Wind MCP对观察仓中的7只股票进行深度分析
"""

import os
import sys
import json
import yaml
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

# 导入Wind数据提供者
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wind_data_provider import get_quotes_batch, get_stats

def load_watchlist():
    """加载观察仓配置"""
    watchlist_path = os.path.join(os.path.dirname(__file__), 'config', 'watchlist.yaml')
    with open(watchlist_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def analyze_stocks(watchlist):
    """分析观察仓股票"""
    stock_codes = [item['code'] for item in watchlist['watchlist']]
    stock_names = {item['code']: item['name'] for item in watchlist['watchlist']}
    
    print("\n" + "="*80)
    print("🎯 大炼化一体化观察仓 Wind MCP 深度分析")
    print("="*80)
    print(f"分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"标的数量: {len(stock_codes)} 只")
    print("-"*80)
    
    # 使用Wind MCP查询行情
    print("\n🔄 正在通过Wind MCP获取实时行情数据...")
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
    
    return results, stock_names

def generate_report(results, stock_names, watchlist):
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
    
    for item in watchlist['watchlist']:
        code = item['code']
        name = item['name']
        data = results.get(code, {})
        price = data.get('price', 0)
        change = data.get('change', 0)
        
        print(f"\n[{code}] {name}")
        print("-" * (len(name) + 10))
        print(f"• 行业: {item.get('sector', '-')} > {item.get('subsector', '-')}")
        print(f"• 市值: {item.get('market_cap', '-')}")
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
    
    strategy = watchlist.get('strategy', {})
    
    if strategy.get('short_term'):
        print("\n🔥 短期关注 (业绩确定性高):")
        for code in strategy['short_term']:
            name = stock_names.get(code, code)
            price = results.get(code, {}).get('price', 0)
            print(f"  • [{code}] {name} - 最新价: ¥{price:.2f}")
    
    if strategy.get('medium_term'):
        print("\n📈 中期布局 (估值修复空间大):")
        for code in strategy['medium_term']:
            name = stock_names.get(code, code)
            price = results.get(code, {}).get('price', 0)
            print(f"  • [{code}] {name} - 最新价: ¥{price:.2f}")
    
    if strategy.get('long_term'):
        print("\n🎯 长期持有 (转型价值):")
        for code in strategy['long_term']:
            name = stock_names.get(code, code)
            price = results.get(code, {}).get('price', 0)
            print(f"  • [{code}] {name} - 最新价: ¥{price:.2f}")
    
    # 统计摘要
    stats = get_stats()
    print("\n" + "="*80)
    print("📊 查询统计摘要")
    print("="*80)
    print(f"• 总调用次数: {stats['total_calls']}")
    print(f"• Wind分析接口成功: {stats['wind_analytics_ok']}")
    print(f"• Wind直连接口成功: {stats['wind_direct_ok']}")
    print(f"• iFinD成功: {stats['ifind_ok']}")
    print(f"• 新浪财经成功: {stats['sina_ok']}")
    print(f"• 全部失败: {stats['all_failed']}")
    
    # 保存报告
    report_path = save_report(results, stock_names, watchlist)
    print(f"\n📁 报告已保存: {report_path}")

def save_report(results, stock_names, watchlist):
    """保存分析报告到文件"""
    report_dir = os.path.join(os.path.dirname(__file__), 'reports', datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(report_dir, exist_ok=True)
    
    report_data = {
        'title': '大炼化一体化观察仓分析报告',
        'date': datetime.now().isoformat(),
        'watchlist': watchlist['watchlist'],
        'results': results,
        'stock_names': stock_names,
        'stats': get_stats()
    }
    
    report_file = os.path.join(report_dir, f"观察仓分析_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    # 同时保存MD格式报告
    md_report_file = report_file.replace('.json', '.md')
    with open(md_report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 大炼化一体化观察仓分析报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**标的数量**: {len(watchlist['watchlist'])} 只\n\n")
        f.write("## 📈 行情概览\n\n")
        f.write("| 股票代码 | 名称 | 最新价 | 涨跌幅 |\n")
        f.write("|---------|------|--------|--------|\n")
        
        for item in watchlist['watchlist']:
            code = item['code']
            data = results.get(code, {})
            f.write(f"| {code} | {item['name']} | ¥{data.get('price', 0):.2f} | {data.get('change', 0):+.2f}% |\n")
        
        f.write("\n## 🏷️ 标的详情\n\n")
        for item in watchlist['watchlist']:
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
        # 加载观察仓
        watchlist = load_watchlist()
        print(f"✅ 成功加载观察仓配置")
        
        # 分析股票
        results, stock_names = analyze_stocks(watchlist)
        
        # 生成报告
        generate_report(results, stock_names, watchlist)
        
        print("\n🎉 分析完成!")
        
    except Exception as e:
        print(f"\n❌ 分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()