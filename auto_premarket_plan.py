# -*- coding: utf-8 -*-
"""
盘前交易计划自动生成器
每日早7点自动运行，读取前一交易日收盘报告，AI分析生成盘前交易计划

使用方式:
    python auto_premarket_plan.py              # 生成今日计划
    python auto_premarket_plan.py --test      # 测试模式(使用最新报告)

定时任务设置 (Windows):
    schtasks /create /tn "盘前交易计划" /tr "python path\\auto_premarket_plan.py" /sc daily /st 07:00
"""

import os
import sys
import json
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Windows编码修复
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE_DIR / 'logs' / f'premarket_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 路径配置
ARCHIVE_ROOT = BASE_DIR / '每日报告归档'
REPORTS_DIR = BASE_DIR / 'reports'


def find_latest_close_report() -> Optional[Path]:
    """查找最近一个交易日的收盘报告"""
    # 优先从 reports 目录查找
    if REPORTS_DIR.exists():
        for item in sorted(REPORTS_DIR.iterdir(), reverse=True):
            if item.is_dir():
                close_report = item / f"close_report_070030.txt"
                if close_report.exists():
                    return close_report
                # 查找其他格式的收盘报告
                for f in item.glob("close_report*.txt"):
                    return f
                for f in item.glob("收盘*.txt"):
                    return f
    
    # 从每日报告归档目录查找
    if ARCHIVE_ROOT.exists():
        for item in sorted(ARCHIVE_ROOT.iterdir(), reverse=True):
            if item.is_dir() and item.name.startswith('2026'):
                for f in item.glob("close_report*.txt"):
                    return f
                for f in item.glob("综合日报*.txt"):
                    return f
    
    return None


def parse_close_report(report_path: Path) -> Dict[str, Any]:
    """解析收盘报告，提取关键数据"""
    try:
        content = report_path.read_text(encoding='utf-8')
    except Exception:
        content = report_path.read_text(encoding='gbk', errors='replace')
    
    data = {
        'report_date': '',
        'account_total': 0.0,
        'position_value': 0.0,
        'cash': 0.0,
        'total_pnl': 0.0,
        'total_pnl_pct': 0.0,
        'profit_count': 0,
        'loss_count': 0,
        'best_performer': '',
        'worst_performer': '',
        'positions': [],
        'raw_content': content
    }
    
    # 提取报告日期
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', content)
    if date_match:
        data['report_date'] = date_match.group(1)
    
    # 提取账户总值
    total_match = re.search(r'账户总值[:：]\s*¥?\s*([\d,]+\.?\d*)', content)
    if total_match:
        data['account_total'] = float(total_match.group(1).replace(',', ''))
    
    # 提取持仓市值
    pos_match = re.search(r'持仓市值[:：]\s*¥?\s*([\d,]+\.?\d*)', content)
    if pos_match:
        data['position_value'] = float(pos_match.group(1).replace(',', ''))
    
    # 提取现金
    cash_match = re.search(r'可用现金[:：]\s*¥?\s*([\d,]+\.?\d*)', content)
    if cash_match:
        data['cash'] = float(cash_match.group(1).replace(',', ''))
    
    # 提取总盈亏
    pnl_match = re.search(r'总盈亏金额[:：]\s*¥?\s*([+-]?[\d,]+\.?\d*)', content)
    if pnl_match:
        data['total_pnl'] = float(pnl_match.group(1).replace(',', ''))
    
    pnl_pct_match = re.search(r'总盈亏比例[:：]\s*([+-]?[\d,]+\.?\d*)%?', content)
    if pnl_pct_match:
        data['total_pnl_pct'] = float(pnl_pct_match.group(1).replace(',', ''))
    
    # 提取盈利/亏损数量
    profit_match = re.search(r'盈利标的[:：]\s*(\d+)\s*只', content)
    if profit_match:
        data['profit_count'] = int(profit_match.group(1))
    
    loss_match = re.search(r'亏损标的[:：]\s*(\d+)\s*只', content)
    if loss_match:
        data['loss_count'] = int(loss_match.group(1))
    
    # 提取最佳/最差表现
    best_match = re.search(r'最佳表现[:：]\s*([^[]\s*)\s*\(([+-]?[\d.]+)%\)', content)
    if best_match:
        data['best_performer'] = f"{best_match.group(1).strip()} ({best_match.group(2)}%)"
    
    worst_match = re.search(r'最差表现[:：]\s*([^[]\s*)\s*\(([+-]?[\d.]+)%\)', content)
    if worst_match:
        data['worst_performer'] = f"{worst_match.group(1).strip()} ({worst_match.group(2)}%)"
    
    # 提取持仓明细
    position_pattern = re.compile(
        r'[🟢🔴⚪]\s+(\S+)\s+(\d+[万股])\s+¥\s*([\d.]+)\s+¥\s*([\d,]+)\s+([\d.]+)%\s*\(([\d.]+)%\)\s*([🔴🟢⚪][-+][\d.]+%)',
        re.MULTILINE
    )
    for match in position_pattern.finditer(content):
        name, shares, price, market_value, weight, target_weight, deviation = match.groups()
        data['positions'].append({
            'name': name,
            'shares': shares,
            'price': float(price),
            'market_value': float(market_value.replace(',', '')),
            'weight': float(weight),
            'target_weight': float(target_weight),
            'deviation': deviation
        })
    
    return data


def get_ai_analysis(data: Dict[str, Any]) -> str:
    """调用GLM-5 API进行AI分析"""
    try:
        from utils.glm5_client import GLM5Client
        
        # 构建分析提示词
        prompt = f"""# 盘前交易计划AI分析请求

## 账户概况 (报告日期: {data['report_date']})
- 账户总值: ¥{data['account_total']:,.2f}
- 持仓市值: ¥{data['position_value']:,.2f}
- 可用现金: ¥{data['cash']:,.2f}
- 总盈亏: ¥{data['total_pnl']:,.2f} ({data['total_pnl_pct']:+.2f}%)
- 盈利标的: {data['profit_count']} 只
- 亏损标的: {data['loss_count']} 只
- 最佳表现: {data['best_performer']}
- 最差表现: {data['worst_performer']}

## 持仓详情
"""
        for pos in data['positions'][:15]:  # 取前15个主要持仓
            prompt += f"- {pos['name']}: {pos['shares']}股, 现价¥{pos['price']}, 权重{pos['weight']}% (目标{pos['target_weight']}%), 偏差{pos['deviation']}\n"
        
        prompt += """
## 分析要求
请基于以上数据，生成今日盘前交易计划，包括：
1. 市场早盘判断（基于昨日涨跌家数和涨跌幅度）
2. 重点持仓分析（盈利标的和亏损标的的操作建议）
3. 今日操作计划（具体标的、数量、价格区间）
4. 风险提示（止损止盈建议）

请用专业的量化交易视角给出客观分析。
"""
        
        # 调用GLM-5
        client = GLM5Client(mode="api")
        result = client.chat(
            message=prompt,
            system_prompt="你是一位资深的量化交易分析师，擅长A股日内交易计划制定。",
            temperature=0.3,
            max_tokens=3000
        )
        
        return result.get('content', '')
        
    except Exception as e:
        logger.warning(f"AI分析失败: {e}")
        return f"AI分析暂时不可用: {e}"


def generate_premarket_plan(data: Dict[str, Any], ai_analysis: str = "") -> str:
    """生成盘前交易计划Markdown报告"""
    
    today = datetime.now().strftime('%Y-%m-%d')
    report_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 按盈亏分类持仓
    profit_positions = []
    loss_positions = []
    
    # 解析盈亏数据
    pnl_pattern = re.compile(r'([🟢🔴])\s+\S+\s+(\d+[万股])\s+¥\s*([\d.]+)\s+¥\s*([\d.]+)\s+¥\s*([\d,]+)\s+¥\s*([\d,]+)\s+([+-]?¥?[\d,]+)\s+([+-]?[\d.]+%)')
    
    for match in pnl_pattern.finditer(data['raw_content']):
        emoji, shares, cost, price, cost_val, current_val, pnl, pnl_pct = match.groups()
        name = ""
        # 尝试从持仓列表中获取名称
        for pos in data['positions']:
            if pos['shares'] == shares:
                name = pos['name']
                break
        
        pos_data = {
            'name': name,
            'shares': shares,
            'cost': float(cost),
            'price': float(price),
            'pnl': pnl,
            'pnl_pct': pnl_pct
        }
        
        if '🟢' in emoji or '+' in pnl_pct:
            profit_positions.append(pos_data)
        else:
            loss_positions.append(pos_data)
    
    # 生成报告
    report = f"""# 📊 盘前交易计划 — {today}

> 生成时间: {report_time}  
> 数据来源: {data['report_date']} 收盘报告 + AI分析

---

## 一、账户概览

| 指标 | 数值 |
|------|------|
| **账户总值** | ¥{data['account_total']:,.2f} |
| **持仓市值** | ¥{data['position_value']:,.2f} |
| **可用现金** | ¥{data['cash']:,.2f} |
| **总盈亏** | **¥{data['total_pnl']:,.2f} ({data['total_pnl_pct']:+.2f}%)** |
| **盈利标的** | {data['profit_count']} 只 |
| **亏损标的** | {data['loss_count']} 只 |
| **最佳表现** | {data['best_performer']} |
| **最差表现** | {data['worst_performer']} |

---

## 二、市场早盘判断

```
📊 昨日收盘分析:
   • 盈利标的: {data['profit_count']} 只
   • 亏损标的: {data['loss_count']} 只
   • 最佳表现: {data['best_performer']}
   • 最差表现: {data['worst_performer']}
   
🎯 今日建议: {'观望为主' if data['loss_count'] > data['profit_count'] else '适度积极'}
```
"""
    
    # 添加亏损标的分析
    if loss_positions:
        report += "\n## 三、重点关注（亏损标的）\n\n"
        report += "| 标的 | 持仓 | 成本 | 现价 | 盈亏 | 建议 |\n"
        report += "|------|------|------|------|------|------|\n"
        for pos in loss_positions[:8]:
            report += f"| {pos['name']} | {pos['shares']} | ¥{pos['cost']:.2f} | ¥{pos['price']:.2f} | {pos['pnl_pct']} | 观察 |\n"
    
    # 添加盈利标的分析
    if profit_positions:
        report += "\n## 四、盈利标的（可考虑减仓）\n\n"
        report += "| 标的 | 持仓 | 成本 | 现价 | 盈亏 | 建议 |\n"
        report += "|------|------|------|------|------|------|\n"
        for pos in profit_positions[:8]:
            report += f"| {pos['name']} | {pos['shares']} | ¥{pos['cost']:.2f} | ¥{pos['price']:.2f} | {pos['pnl_pct']} | 持有/止盈 |\n"
    
    # 添加AI分析
    if ai_analysis:
        report += f"""
---

## 五、AI智能分析

{ai_analysis}

"""
    
    # 添加风险提示
    report += """
---

## 六、风险控制

### ⚠️ 风险提示

| 风险项 | 阈值 | 应对措施 |
|--------|------|---------|
| 单标的亏损 | -8% | 止损出局 |
| 单日组合亏损 | -2% | 启动防御模式 |
| 仓位偏差 | >±2% | 再平衡 |

### 🛡️ 止损止盈规则

```
止损规则:
  • 单只标的亏损达到 8% 时强制止损
  • 跌破重要支撑位时考虑止损
  
止盈规则:
  • 盈利超过 15% 时考虑分批止盈
  • 到达目标价位时自动止盈
```
"""
    
    # 添加执行清单
    report += """
---

## 七、执行检查清单

- [ ] 开盘前检查美股夜盘表现
- [ ] 查看A50期指走势
- [ ] 确认隔夜外盘商品涨跌
- [ ] 设置盘中预警价格
- [ ] 记录盘中操作并更新日志
- [ ] 收盘后生成持仓报告

---

## 八、总结

```
📊 今日交易计划摘要

✅ 账户状态: """ + ('健康' if data['total_pnl'] >= 0 else '亏损') + f""" ({data['total_pnl_pct']:+.2f}%)
✅ 仓位状态: {'ETF整体低配，现金充足' if data['cash'] > data['position_value'] * 0.3 else '仓位合理'}
✅ 风险状态: {'可控' if data['loss_count'] < data['profit_count'] else '需关注'}

🎯 今日操作:
   1. 观望为主，等待明确信号
   2. 设置止损止盈提醒
   3. 关注盘中实时行情变化
   
💰 资金安排:
   • 保留 ¥{data['cash']:,.0f} 现金
   • 等待合适时机加仓
```

---

*报告生成时间: {report_time}*  
*量化策略系统 v5.1 - 康波周期 + 十五五规划 + 社保基金ETF追踪*
"""
    
    return report


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='盘前交易计划自动生成器')
    parser.add_argument('--test', action='store_true', help='测试模式')
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("盘前交易计划生成器启动")
    logger.info("=" * 60)
    
    # 查找最近收盘报告
    report_path = find_latest_close_report()
    if not report_path:
        logger.error("未找到收盘报告")
        print("❌ 错误: 未找到收盘报告")
        return
    
    logger.info(f"✓ 找到收盘报告: {report_path}")
    print(f"📄 使用报告: {report_path}")
    
    # 解析报告
    data = parse_close_report(report_path)
    logger.info(f"✓ 解析完成: 日期={data['report_date']}, 总值={data['account_total']:,.0f}")
    
    # 生成AI分析
    ai_analysis = ""
    if not args.test:
        print("🤖 正在生成AI分析...")
        ai_analysis = get_ai_analysis(data)
        if ai_analysis:
            logger.info("✓ AI分析完成")
        else:
            logger.warning("AI分析未返回结果")
    
    # 生成报告
    report = generate_premarket_plan(data, ai_analysis)
    
    # 保存报告
    today = datetime.now()
    archive_dir = ARCHIVE_ROOT / today.strftime('%Y-%m-%d')
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = archive_dir / f"盘前交易计划_{today.strftime('%Y%m%d')}.md"
    report_file.write_text(report, encoding='utf-8')
    logger.info(f"✓ 报告已保存: {report_file}")
    
    # 同时保存到 reports 目录
    reports_today = REPORTS_DIR / today.strftime('%Y-%m-%d')
    reports_today.mkdir(parents=True, exist_ok=True)
    reports_file = reports_today / f"premarket_plan_{today.strftime('%Y%m%d')}.md"
    reports_file.write_text(report, encoding='utf-8')
    logger.info(f"✓ 报告已保存: {reports_file}")
    
    print("\n" + "=" * 60)
    print("✅ 盘前交易计划生成完成!")
    print(f"📄 报告路径: {report_file}")
    print("=" * 60)
    
    return report_file


if __name__ == '__main__':
    main()
