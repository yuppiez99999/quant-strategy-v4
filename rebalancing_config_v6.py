# -*- coding: utf-8 -*-
"""
量化策略系统 v5.3 - 投资组合再平衡配置模板
说明：此为示例配置，请替换为您的实际资金规模和标的

再平衡原则：
1. 权益组合维持核心-卫星策略
2. 低风险理财采用风险平价策略，确保流动性与收益平衡
3. 增加防御/红利配置，提升组合稳定性
4. 保持黄金ETF作为危机对冲工具
5. 低风险理财配置：国债逆回购 + 短债基金 + 信用债基金 + 可转债基金 + 红利ETF
"""

# ============================================================
# 投资组合配置 - 再平衡模板（示例配置）
# ============================================================

# 资产配置权重（总账户视角）
# 说明：所有标的均为示例，请替换为您的实际持仓
PORTFOLIO_ALLOCATION = {
    '权益组合': {
        'weight': 0.0698,
        'description': '核心-卫星策略',
        'sub_allocation': {
            '核心宽基ETF': {
                'weight': 0.0651,
                '标的': {
                    'EXAMPLE_ETF_1': {'name': '示例宽基ETF_1', 'weight': 0.0186, 'risk': 0.15},
                    'EXAMPLE_ETF_2': {'name': '示例宽基ETF_2', 'weight': 0.0140, 'risk': 0.18},
                    'EXAMPLE_ETF_3': {'name': '示例宽基ETF_3', 'weight': 0.0116, 'risk': 0.22},
                    'EXAMPLE_ETF_4': {'name': '示例宽基ETF_4', 'weight': 0.0116, 'risk': 0.28},
                    'EXAMPLE_ETF_5': {'name': '示例宽基ETF_5', 'weight': 0.0093, 'risk': 0.25},
                }
            },
            '科技成长个股': {
                'weight': 0.0465,
                '标的': {
                    'EXAMPLE_STOCK_1': {'name': '示例科技股_1', 'weight': 0.00698, 'risk': 0.32},
                    'EXAMPLE_STOCK_2': {'name': '示例科技股_2', 'weight': 0.00698, 'risk': 0.30},
                    'EXAMPLE_STOCK_3': {'name': '示例科技股_3', 'weight': 0.0093, 'risk': 0.28},
                    'EXAMPLE_STOCK_4': {'name': '示例科技股_4', 'weight': 0.00698, 'risk': 0.33},
                    'EXAMPLE_STOCK_5': {'name': '示例科技股_5', 'weight': 0.00698, 'risk': 0.35},
                    'EXAMPLE_STOCK_6': {'name': '示例医药股_1', 'weight': 0.0093, 'risk': 0.24},
                }
            },
            '高端制造': {
                'weight': 0.0465,
                '标的': {
                    'EXAMPLE_MFG_1': {'name': '示例制造股_1', 'weight': 0.0116, 'risk': 0.22},
                    'EXAMPLE_MFG_2': {'name': '示例制造股_2', 'weight': 0.0093, 'risk': 0.20},
                    'EXAMPLE_MFG_3': {'name': '示例制造股_3', 'weight': 0.0093, 'risk': 0.22},
                    'EXAMPLE_MFG_4': {'name': '示例制造股_4', 'weight': 0.0093, 'risk': 0.20},
                    'EXAMPLE_MFG_5': {'name': '示例能源股_1', 'weight': 0.00698, 'risk': 0.25},
                }
            },
            '防御红利': {
                'weight': 0.0349,
                '标的': {
                    'EXAMPLE_DIV_1': {'name': '示例红利ETF', 'weight': 0.0140, 'risk': 0.12},
                    'EXAMPLE_DIV_2': {'name': '示例银行股', 'weight': 0.0093, 'risk': 0.15},
                    'EXAMPLE_DIV_3': {'name': '示例电力股', 'weight': 0.00698, 'risk': 0.10},
                    'EXAMPLE_DIV_4': {'name': '示例煤炭股', 'weight': 0.0047, 'risk': 0.18},
                }
            },
            '商品避险': {
                'weight': 0.0116,
                '标的': {
                    'EXAMPLE_GOLD': {'name': '示例黄金ETF', 'weight': 0.0116, 'risk': 0.15},
                }
            },
            '现金缓冲': {
                'weight': 0.0056,
            }
        }
    },
    '低风险理财': {
        'weight': 0.9302,
        'description': '风险平价策略',
        'sub_allocation': {
            '国债逆回购': {
                'weight': 0.25,
                '标的': {
                    'EXAMPLE_REPO_1': {'name': '示例国债逆回购_1', 'weight': 0.15, 'risk': 0.005},
                    'EXAMPLE_REPO_2': {'name': '示例国债逆回购_2', 'weight': 0.10, 'risk': 0.005},
                }
            },
            '短债基金': {
                'weight': 0.20,
                '标的': {
                    'EXAMPLE_BOND_1': {'name': '示例短债基金_1', 'weight': 0.10, 'risk': 0.02},
                    'EXAMPLE_BOND_2': {'name': '示例短债基金_2', 'weight': 0.10, 'risk': 0.02},
                }
            },
            '信用债基金': {
                'weight': 0.15,
                '标的': {
                    'EXAMPLE_CREDIT_1': {'name': '示例信用债_1', 'weight': 0.075, 'risk': 0.04},
                    'EXAMPLE_CREDIT_2': {'name': '示例信用债_2', 'weight': 0.075, 'risk': 0.04},
                }
            },
            '可转债基金': {
                'weight': 0.25,
                '标的': {
                    'EXAMPLE_CONVERT_1': {'name': '示例可转债_1', 'weight': 0.10, 'risk': 0.08},
                    'EXAMPLE_CONVERT_2': {'name': '示例可转债_2', 'weight': 0.075, 'risk': 0.08},
                    'EXAMPLE_CONVERT_3': {'name': '示例可转债_3', 'weight': 0.075, 'risk': 0.08},
                }
            },
            '红利ETF': {
                'weight': 0.15,
                '标的': {
                    'EXAMPLE_DIV_ETF_1': {'name': '示例红利ETF_1', 'weight': 0.06, 'risk': 0.12},
                    'EXAMPLE_DIV_ETF_2': {'name': '示例红利ETF_2', 'weight': 0.045, 'risk': 0.10},
                    'EXAMPLE_DIV_ETF_3': {'name': '示例价值ETF', 'weight': 0.045, 'risk': 0.12},
                }
            },
        }
    }
}

# ============================================================
# 再平衡参数
# ============================================================
REBALANCE_PARAMS = {
    'threshold': 0.05,              # 再平衡阈值（权重偏差超过5%触发）
    'min_interval_days': 5,         # 最小再平衡间隔（交易日）
    'max_rebalance_per_day': 3,    # 每日最大再平衡标的数
    'priority_order': [             # 再平衡优先级
        '止损标的',
        '超配标的',
        '低配标的',
        '新增标的'
    ]
}

# ============================================================
# 风险控制参数
# ============================================================
RISK_CONTROL = {
    'max_single_position': 0.10,    # 单标的最大权重
    'max_sector_exposure': 0.25,    # 单板块最大暴露
    'stop_loss_default': -0.10,     # 默认止损线
    'take_profit_default': 0.20,    # 默认止盈线
    'max_drawdown_limit': 0.08,     # 最大回撤限制
}

# 说明：以上所有配置均为示例值，请根据您的实际投资策略和风险偏好进行调整。
