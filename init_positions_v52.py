# -*- coding: utf-8 -*-
"""
初始化 positions.json - 示例模板
说明：此为示例配置，请替换为您的实际资金规模和标的
根据交易计划生成初始空仓状态
"""
import json
import os

# 配置标的（空仓状态）- 示例标的列表
# 说明：所有代码均为示例，请替换为您的实际持仓标的
INITIAL_POSITIONS = {
    # ===== 权益组合（示例配置）=====

    # 核心宽基 ETF（示例）
    "EXAMPLE_ETF_1": {"shares": 0, "avg_cost": 0, "category": "core_etf", "target_weight": 0.08},
    "EXAMPLE_ETF_2": {"shares": 0, "avg_cost": 0, "category": "core_etf", "target_weight": 0.06},
    "EXAMPLE_ETF_3": {"shares": 0, "avg_cost": 0, "category": "core_etf", "target_weight": 0.05},

    # 科技成长个股（示例）
    "EXAMPLE_STOCK_1": {"shares": 0, "avg_cost": 0, "category": "tech_growth", "target_weight": 0.03},
    "EXAMPLE_STOCK_2": {"shares": 0, "avg_cost": 0, "category": "tech_growth", "target_weight": 0.03},

    # 高端制造（示例）
    "EXAMPLE_MFG_1": {"shares": 0, "avg_cost": 0, "category": "manufacturing", "target_weight": 0.05},

    # 防御/红利（示例）
    "EXAMPLE_DIV_1": {"shares": 0, "avg_cost": 0, "category": "defensive", "target_weight": 0.06},

    # 商品/避险（示例）
    "EXAMPLE_GOLD": {"shares": 0, "avg_cost": 0, "category": "commodity", "target_weight": 0.05},

    # ===== 低风险理财配置（示例）=====

    # 国债逆回购（示例）
    "EXAMPLE_REPO_1": {"shares": 0, "avg_cost": 0, "category": "repo", "target_weight": 0.15},

    # 短债基金（示例）
    "EXAMPLE_BOND_1": {"shares": 0, "avg_cost": 0, "category": "short_term_bond", "target_weight": 0.10},

    # 信用债基金（示例）
    "EXAMPLE_CREDIT_1": {"shares": 0, "avg_cost": 0, "category": "credit_bond", "target_weight": 0.075},

    # 可转债基金（示例）
    "EXAMPLE_CONVERT_1": {"shares": 0, "avg_cost": 0, "category": "convertible_bond", "target_weight": 0.10},

    # 红利/价值ETF（示例）
    "EXAMPLE_DIV_ETF_1": {"shares": 0, "avg_cost": 0, "category": "dividend_etf", "target_weight": 0.06},

    # 增强型指数基金（示例）
    "EXAMPLE_ENHANCE_1": {"shares": 0, "avg_cost": 0, "category": "enhanced_index", "target_weight": 0.05},

    # 现金缓冲
    "CASH": {"shares": 0, "avg_cost": 0, "category": "cash", "target_weight": 0.08}
}

def init_positions():
    """初始化 positions.json"""
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
    positions_file = os.path.join(config_dir, 'positions.json')

    # 示例资金配置（请替换为您的实际资金规模）
    total_capital = 1_000_000      # 示例：100万
    equity_portfolio = 700_000     # 示例：权益组合 70万
    low_risk_portfolio = 300_000   # 示例：低风险理财 30万
    cash_buffer = 30_000           # 现金缓冲
    initial_cash = total_capital - cash_buffer

    data = {
        "positions": INITIAL_POSITIONS,
        "cash": initial_cash,
        "last_update": "2026-06-20T12:00:00",
        "prices": {},
        "total_value": total_capital,
        "version": "template_v1.0",
        "notes": "示例模板 - 请替换为您的实际资金规模和标的",
        "equity_portfolio": equity_portfolio,
        "low_risk_portfolio": low_risk_portfolio
    }

    with open(positions_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[OK] positions.json 已初始化: {positions_file}")
    print(f"  总资金: {total_capital}（示例值，请替换）")
    print(f"  权益组合: {equity_portfolio}")
    print(f"  低风险理财: {low_risk_portfolio}")
    print(f"  现金储备: {initial_cash}")
    print(f"  现金缓冲: {cash_buffer}")
    print(f"  标的数量: {len(INITIAL_POSITIONS)} 只（空仓）")
    print(f"  状态: 等待建仓")

if __name__ == "__main__":
    init_positions()
