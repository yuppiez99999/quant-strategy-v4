# -*- coding: utf-8 -*-
"""
GLM-5 量化交易实战演示
演示如何将GLM-5集成到你的量化系统中

运行: python glm5_demo.py
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.glm5_client import GLM5Client


def demo_basic_chat():
    """演示1：基础对话"""
    print("\n" + "=" * 60)
    print("[演示1] 基础对话功能")
    print("=" * 60)
    
    client = GLM5Client(mode="api")
    
    questions = [
        "你好，请用一句话介绍你自己",
        "分析一下当前A股市场的整体趋势",
        "给出3条今日投资建议（简短）",
    ]
    
    for q in questions:
        print(f"\n❓ 问题: {q}")
        result = client.chat(q, max_tokens=300, temperature=0.6)
        print(f"💬 回答: {result['content'][:200]}...")
        if 'usage' in result:
            print(f"   Token使用: 输入{result['usage']['prompt_tokens']} / 输出{result['usage']['completion_tokens']}")


def demo_market_analysis():
    """演示2：市场数据分析"""
    print("\n" + "=" * 60)
    print("[演示2] 市场分析报告生成")
    print("=" * 60)
    
    client = GLM5Client(mode="api")
    
    # 模拟市场数据（实际项目中替换为真实数据）
    market_data = {
        "日期": "2026-06-23",
        "指数行情": {
            "上证指数": {"收盘": 3050.12, "涨跌幅": "+0.85%", "成交量": "3500亿"},
            "深证成指": {"收盘": 9800.45, "涨跌幅": "+1.20%", "成交量": "4200亿"},
            "创业板指": {"收盘": 1920.33, "涨跌幅": "+1.50%"},
        },
        "持仓情况": {
            "中际旭创": {"仓位": "5.2%", "成本价": 128.50, "现价": 145.30, "盈亏": "+13.1%"},
            "中国神华": {"仓位": "4.8%", "成本价": 38.20, "现价": 37.90, "盈亏": "-0.8%"},
            "华安黄金ETF": {"仓位": "4.1%", "成本价": 5.12, "现价": 5.18, "盈亏": "+1.2%"},
        },
        "资金流向": {
            "北向资金": "净流入 +85.3亿元",
            "主力资金": "净流入 +120.5亿元",
            "融资余额": "增加 23.8亿元",
        },
        "技术信号": [
            "上证指数突破3000点关键位",
            "中际旭创MACD金叉确认",
            "中国神华跌破20日均线",
            "黄金ETF在支撑位企稳",
        ],
        "宏观事件": [
            "央行宣布降准0.25个百分点",
            "美联储议息会议结果偏鸽派",
            "国内PMI数据超预期",
        ]
    }
    
    print("\n📊 正在生成市场分析报告...\n")
    
    analysis = client.analyze_market(
        market_data=market_data,
        focus_areas=["大盘", "持仓标的", "资金流向", "技术指标"]
    )
    
    print(analysis)


def demo_daily_report():
    """演示3：日报生成"""
    print("\n" + "=" * 60)
    print("[演示3] 日报自动生成")
    print("=" * 60)
    
    client = GLM5Client(mode="api")
    
    report_data = {
        "date": "2026-06-23",
        "summary": {
            "账户总值": "1,052,340元",
            "当日盈亏": "+12,850元 (+1.24%)",
            "累计收益": "+52,340元 (+5.23%)",
        },
        "positions": [
            {"name": "中际旭创", "pct": "5.2%", "pnl": "+1,910", "signal": "持有"},
            {"name": "海光信息", "pct": "4.5%", "pnl": "+2,100", "signal": "加仓"},
            {"name": "北方华创", "pct": "4.0%", "pnl": "+1,800", "signal": "持有"},
            {"name": "中国神华", "pct": "4.8%", "pnl": "-380", "signal": "减仓"},
            {"name": "华安黄金ETF", "pct": "4.1%", "pnl": "+245", "signal": "持有"},
        ],
        "risk_metrics": {
            "组合波动率": "12.5%",
            "最大回撤": "-3.2%",
            "VaR(95%)": "-15,600",
            "夏普比率": "1.85",
        },
        "next_day_plan": [
            "关注美联储利率决议",
            "监控北向资金动向",
            "检查持仓标的技术面变化",
        ]
    }
    
    print("\n📝 正在生成每日报告...\n")
    
    report = client.generate_report(report_type="daily", context_data=report_data)
    
    # 保存到文件
    output_file = Path(__file__).parent.parent / "每日报告归档" / f"{report_data['date'].replace('-','')}_AI_日报.md"
    output_file.parent.mkdir(exist_ok=True=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# AI生成的每日交易报告 - {report_data['date']}\n\n")
        f.write(report)
    
    print(f"\n📄 报告已保存到: {output_file}")
    print("\n--- 报告预览 (前500字) ---\n")
    print(report[:500] + "...")


def demo_streaming():
    """演示4：流式输出"""
    print("\n" + "=" * 60)
    print("[演示4] 流式输出（逐字显示）")
    print("=" * 60)
    
    client = GLM5Client(mode="api")
    
    prompt = "用3句话概括今日A股市场要点"
    
    print(f"\n💬 提示: {prompt}\n")
    print("⏳ GLM-5 回复:\n")
    
    full_response = ""
    for chunk in client.chat_stream(prompt, max_tokens=200):
        print(chunk, end="", flush=True)
        full_response += chunk
    
    print(f"\n\n✅ 完成! 共 {len(full_response)} 字")


def demo_integration():
    """演示5：与现有系统集成示例"""
    print("\n" + "=" * 60)
    print("[演示5] 系统集成代码示例")
    print("=" * 60)
    
    example_code = '''
# ============================================================
# 示例：在你的量化系统中使用 GLM-5
# 文件位置: 11_量化策略/your_module.py
# ============================================================

from utils.glm5_client import GLM5Client

class QuantTradingSystem:
    def __init__(self):
        # 初始化 GLM-5 客户端
        self.ai = GLM5Client(mode="api")  # 已配置 API Key
        
    def generate_daily_analysis(self):
        """每日盘后分析"""
        # 获取市场数据（你的现有逻辑）
        market_data = self._collect_market_data()
        
        # 使用 GLM-5 分析
        analysis = self.ai.analyze_market(
            market_data=market_data,
            focus_areas=["大盘", "持仓", "技术指标"]
        )
        
        # 保存或发送
        self._save_report(analysis)
        return analysis
    
    def risk_warning_check(self):
        """风险预警检查"""
        risk_data = self._calculate_risk_metrics()
        
        # 如果风险过高，请求 AI 建议
        if risk_data["max_drawdown"] < -0.05:
            suggestion = self.ai.chat(
                f"当前最大回撤 {risk_data['max_drawdown']*100:.1f}%，"
                f"请给出风控建议",
                temperature=0.3
            )
            return suggestion["content"]
        
        return None
    
    def _collect_market_data(self):
        """收集市场数据（示例）"""
        return {
            "指数": {"上证": 3050, "涨跌幅": "0.85%"},
            "持仓": {},
            "资金流": {}
        }
'''
    
    print("\n📋 可直接复制使用的代码:\n")
    print(example_code)


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("  GLM-5 量化交易实战演示系统")
    print("  Powered by ZhipuAI | 集成方案 by CodeBuddy")
    print("=" * 70)
    
    demos = [
        ("1", "基础对话", demo_basic_chat),
        ("2", "市场分析报告", demo_market_analysis),
        ("3", "日报生成", demo_daily_report),
        ("4", "流式输出", demo_streaming),
        ("5", "系统集成示例", demo_integration),
        ("0", "运行全部演示", None),
    ]
    
    print("\n可用演示:")
    for code, name, _ in demos:
        print(f"  [{code}] {name}")
    print("  [q] 退出")
    
    choice = input("\n请选择演示 (默认 2): ").strip().lower()
    
    if choice == 'q':
        print("\n再见!")
        return
    
    if not choice:
        choice = "2"
    
    if choice == "0":
        # 运行全部演示
        demo_basic_chat()
        demo_market_analysis()
        demo_daily_report()
        demo_streaming()
        demo_integration()
    else:
        for code, name, func in demos:
            if code == choice and func:
                func()
                break
        else:
            print("无效选择!")
            return
    
    print("\n" + "=" * 70)
    print("  演示完成!")
    print("  下一步: 将 GLM-5 集成到你的量化系统中")
    print("  文档: utils/GLM5_集成指南.md")
    print("=" * 70)


if __name__ == "__main__":
    main()
