# -*- coding: utf-8 -*-
"""
GLM-5 自动决策引擎 - 集成示例
演示如何将决策引擎集成到你的量化系统中

运行: python integrate_example.py
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from utils.console_encoding import setup_utf8_console
from utils.env_loader import load_dotenv

setup_utf8_console()
load_dotenv()
if not os.environ.get('ZHIPUAI_API_KEY'):
    print('未检测到 ZHIPUAI_API_KEY，请在 .env 中配置后重试。')
    sys.exit(1)

from utils.glm5_decision_engine import GLM5DecisionEngine


class QuantSystemWithAI:
    """
    带 AI 决策的量化交易系统示例
    
    这是一个完整的集成模板，你可以复制到你的项目中
    """
    
    def __init__(self):
        """初始化系统"""
        print("[INIT] 初始化量化交易系统...")
        
        # 初始化 AI 决策引擎
        self.ai_engine = GLM5DecisionEngine(
            mode='api',
            api_model='glm-4-plus',
            temperature=0.3,  # 低温度，更确定性
        )
        
        print("[OK] 系统初始化完成\n")
    
    def collect_market_data(self):
        """
        收集市场数据
        
        在实际系统中，这里应该调用你的数据获取函数
        例如: wind_data_provider.py 或 akshare
        """
        # 示例数据（替换为你的真实数据）
        return {
            "日期": datetime.now().strftime("%Y-%m-%d"),
            "指数行情": {
                "上证指数": {"收盘": 3050.12, "涨跌幅": "+0.85%"},
                "深证成指": {"收盘": 9800.45, "涨跌幅": "+1.20%"},
                "创业板指": {"收盘": 1920.33, "涨跌幅": "+1.50%"},
            },
            "板块表现": {
                "科技": "+2.1%",
                "消费": "-0.5%",
                "能源": "+0.3%",
            },
            "资金流向": {
                "北向资金": "净流入 +85亿",
                "主力资金": "净流入 +120亿",
            },
            "技术指标": [
                "上证指数突破3000点关键位",
                "MACD金叉确认",
                "RSI处于中性区域",
            ],
        }
    
    def get_portfolio_data(self):
        """
        获取持仓数据
        
        在实际系统中，这里应该从你的持仓管理系统读取
        例如: config/positions.json 或数据库
        """
        # 示例数据（替换为你的真实数据）
        return {
            "账户总值": "1,052,340元",
            "当日盈亏": "+12,850元 (+1.24%)",
            "累计收益": "+52,340元 (+5.23%)",
            "持仓": [
                {
                    "代码": "300308",
                    "名称": "中际旭创",
                    "仓位": "5.2%",
                    "成本价": 128.50,
                    "现价": 145.30,
                    "盈亏": "+13.1%",
                },
                {
                    "代码": "601088",
                    "名称": "中国神华",
                    "仓位": "4.8%",
                    "成本价": 38.20,
                    "现价": 37.90,
                    "盈亏": "-0.8%",
                },
                {
                    "代码": "518880",
                    "名称": "华安黄金ETF",
                    "仓位": "4.1%",
                    "成本价": 5.12,
                    "现价": 5.18,
                    "盈亏": "+1.2%",
                },
            ],
            "目标仓位": {
                "中际旭创": "5%",
                "中国神华": "4%",
                "华安黄金ETF": "4%",
            },
        }
    
    def get_risk_rules(self):
        """
        获取风控规则
        
        根据你的风险偏好调整
        """
        return {
            "max_single_position": 0.10,  # 单只标的最大10%
            "stop_loss_pct": -0.08,        # 止损线-8%
            "take_profit_pct": 0.15,       # 止盈线+15%
            "max_sector_exposure": 0.30,   # 单一行业最大30%
            "min_cash_ratio": 0.05,        # 最低现金比例5%
        }
    
    def daily_trading_workflow(self):
        """
        每日交易工作流
        
        这是核心集成点，将 AI 决策融入你的日常流程
        """
        print("=" * 70)
        print("每日交易工作流 - AI 决策引擎")
        print("=" * 70)
        
        # Step 1: 收集市场数据
        print("\n[Step 1] 收集市场数据...")
        market_data = self.collect_market_data()
        print(f"  [OK] 市场数据已获取")
        
        # Step 2: 获取持仓数据
        print("\n[Step 2] 获取持仓数据...")
        portfolio_data = self.get_portfolio_data()
        print(f"  [OK] 持仓数据已获取 ({len(portfolio_data['持仓'])} 只标的)")
        
        # Step 3: 获取风控规则
        print("\n[Step 3] 加载风控规则...")
        risk_rules = self.get_risk_rules()
        print(f"  [OK] 风控规则已加载")
        
        # Step 4: AI 生成交易决策
        print("\n[Step 4] AI 正在分析市场...")
        print("  [WAIT] 这通常需要 10-30 秒，请稍候...")
        
        try:
            decision = self.ai_engine.make_decisions(
                market_data=market_data,
                portfolio_data=portfolio_data,
                risk_rules=risk_rules,
            )
            print("  [OK] 决策生成完成")
            
        except Exception as e:
            print(f"  [FAIL] 决策生成失败: {e}")
            return None
        
        # Step 5: 处理交易信号
        print("\n[Step 5] 处理交易信号...")
        if decision.trading_signals:
            print(f"  [INFO] 共 {len(decision.trading_signals)} 条交易信号:")
            for sig in decision.trading_signals:
                print(f"    [{sig.action}] {sig.code} {sig.name}")
                print(f"      仓位: {sig.current_weight:.1%} → {sig.target_weight:.1%}")
                print(f"      理由: {sig.reason[:60]}")
                print(f"      置信度: {sig.confidence:.2f} | 紧急程度: {sig.urgency}")
        else:
            print("  [INFO] 暂无交易信号（当前持仓无需调整）")
        
        # Step 6: 检查风险预警
        print("\n[Step 6] 检查风险预警...")
        if decision.risk_alerts:
            print(f"  [INFO] 共 {len(decision.risk_alerts)} 条风险预警:")
            for alert in decision.risk_alerts:
                icon = "🚨" if alert.severity == "CRITICAL" else "⚠️"
                print(f"    {icon} [{alert.severity}] {alert.message[:80]}")
                
                # 对于高风险预警，可以触发自动操作
                if alert.severity in ["CRITICAL", "HIGH"]:
                    print(f"      -> 建议立即处理!")
        else:
            print("  [OK] 无风险预警")
        
        # Step 7: 查看组合建议
        if decision.portfolio_advice:
            print(f"\n[Step 7] 组合调整建议:")
            print(f"  {decision.portfolio_advice[:300]}...")
        
        # Step 8: 查看宏观展望
        if decision.macro_outlook:
            print(f"\n[Step 8] 宏观展望:")
            print(f"  {decision.macro_outlook[:300]}...")
        
        # Step 9: 导出报告
        print("\n[Step 9] 导出决策报告...")
        report_path = self.ai_engine.export_decisions(decision)
        print(f"  [OK] 报告已保存: {report_path}")
        
        # Step 10: 总结
        print("\n" + "=" * 70)
        print("每日交易工作流完成!")
        print("=" * 70)
        print(f"\nAI 整体置信度: {decision.ai_confidence:.2%}")
        print(f"报告路径: {report_path}")
        print("\n下一步:")
        print("  1. 人工审核 AI 决策建议")
        print("  2. 确认交易信号后执行")
        print("  3. 监控风险预警并及时处理")
        
        return decision
    
    def quick_risk_check(self):
        """
        快速风险检查（简化版，仅检查持仓风险）
        
        适用于盘中快速检查
        """
        print("\n" + "=" * 70)
        print("快速风险检查")
        print("=" * 70)
        
        portfolio_data = self.get_portfolio_data()
        
        print("\n[CHECK] 正在检查持仓风险...")
        decision = self.ai_engine.quick_check(portfolio_data)
        
        print(f"\n市场概况: {decision.market_summary[:150]}...")
        
        if decision.risk_alerts:
            print(f"\n风险预警 ({len(decision.risk_alerts)} 条):")
            for alert in decision.risk_alerts:
                print(f"  [{alert.severity}] {alert.message[:80]}")
        
        print(f"\n[OK] 快速检查完成")
        
        return decision


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("  GLM-5 自动决策引擎 - 集成示例")
    print("  功能: 自动分析市场 + 生成交易信号 + 风险预警")
    print("=" * 70)
    
    # 创建系统实例
    system = QuantSystemWithAI()
    
    # 选择运行模式
    print("\n可选模式:")
    print("  [1] 完整交易工作流（推荐首次运行）")
    print("  [2] 快速风险检查")
    print("  [q] 退出")
    
    choice = input("\n请选择 (默认 1): ").strip().lower()
    
    if choice == 'q':
        print("\n再见!")
        return
    
    if choice == "2":
        # 快速风险检查
        system.quick_risk_check()
    else:
        # 完整交易工作流
        system.daily_trading_workflow()
    
    print("\n" + "=" * 70)
    print("  集成示例运行完成!")
    print("  下一步:")
    print("    - 将代码复制到你的量化系统中")
    print("    - 替换示例数据为真实数据")
    print("    - 设置定时任务自动运行")
    print("=" * 70)


if __name__ == "__main__":
    main()
