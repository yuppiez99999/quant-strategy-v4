#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
200万资金五年交易计划生成器
基于康波周期 + 十五五规划 + 大炼化观察仓
生成详细的建仓计划、年化收益预测和回撤分析
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import math


class FiveYearTradingPlan:
    """五年交易计划生成器"""
    
    def __init__(self, total_capital: float = 2_000_000):
        """
        初始化
        
        Args:
            total_capital: 总资金（默认200万）
        """
        self.total_capital = total_capital
        self.start_date = datetime.now()
        
        # 持仓配置（从图片中提取）
        self.portfolio_config = {
            # ========== 科技成长板块 (35%) ==========
            'tech_growth': {
                'allocation': 0.35,
                'stocks': [
                    {'code': '300308', 'name': '中际旭创', 'weight': 0.08, 'sector': '光模块'},
                    {'code': '688041', 'name': '海光信息', 'weight': 0.07, 'sector': 'AI芯片'},
                    {'code': '588000', 'name': '科创50ETF华夏', 'weight': 0.10, 'sector': '科创板指数'},
                    {'code': '159915', 'name': '创业板ETF易方达', 'weight': 0.10, 'sector': '创业板指数'},
                ]
            },
            
            # ========== 能源转型板块 (25%) ==========
            'energy_transition': {
                'allocation': 0.25,
                'stocks': [
                    {'code': '601088', 'name': '中国神华', 'weight': 0.06, 'sector': '煤炭龙头'},
                    {'code': '600989', 'name': '宝丰能源', 'weight': 0.05, 'sector': '煤化工'},
                    {'code': '600875', 'name': '东方电气', 'weight': 0.05, 'sector': '电力设备'},
                    {'code': '600089', 'name': '特变电工', 'weight': 0.05, 'sector': '输变电'},
                    {'code': '300274', 'name': '阳光电源', 'weight': 0.04, 'sector': '光伏逆变器'},
                ]
            },
            
            # ========== 高端制造板块 (20%) ==========
            'advanced_manufacturing': {
                'allocation': 0.20,
                'stocks': [
                    {'code': '600406', 'name': '国电南瑞', 'weight': 0.05, 'sector': '电网自动化'},
                    {'code': '600995', 'name': '南网储能', 'weight': 0.04, 'sector': '储能'},
                    {'code': '000425', 'name': '徐工机械', 'weight': 0.04, 'sector': '工程机械'},
                    {'code': '688017', 'name': '绿的谐波', 'weight': 0.04, 'sector': '机器人减速器'},
                    {'code': '002371', 'name': '北方华创', 'weight': 0.03, 'sector': '半导体设备'},
                ]
            },
            
            # ========== 大炼化一体化板块 (15%) ==========
            'petrochemical': {
                'allocation': 0.15,
                'stocks': [
                    {'code': '002648', 'name': '卫星化学', 'weight': 0.05, 'sector': '轻烃化工'},
                    {'code': '600346', 'name': '恒力石化', 'weight': 0.04, 'sector': '炼化一体化'},
                    {'code': '601233', 'name': '桐昆股份', 'weight': 0.03, 'sector': '涤纶长丝'},
                    {'code': '002493', 'name': '荣盛石化', 'weight': 0.03, 'sector': '炼化一体化'},
                ]
            },
            
            # ========== 防御性配置 (5%) ==========
            'defensive': {
                'allocation': 0.05,
                'stocks': [
                    {'code': '518880', 'name': '黄金ETF华安', 'weight': 0.02, 'sector': '黄金'},
                    {'code': '600276', 'name': '恒瑞医药', 'weight': 0.02, 'sector': '创新药'},
                    {'code': '601888', 'name': '中国中免', 'weight': 0.01, 'sector': '免税零售'},
                ]
            }
        }
        
        # 宽基指数ETF（作为基准对比）
        self.benchmark_etfs = [
            {'code': '512100', 'name': '中证1000ETF南方', 'weight': 0.33},
            {'code': '510500', 'name': '中证500ETF南方', 'weight': 0.33},
            {'code': '510300', 'name': '沪深300ETF华泰柏瑞', 'weight': 0.34},
        ]
    
    def generate_detailed_plan(self) -> Dict:
        """生成详细交易计划"""
        
        plan = {
            '基本信息': self._get_basic_info(),
            '资产配置方案': self._generate_asset_allocation(),
            '分阶段建仓计划': self._generate_phased_building_plan(),
            '五年收益预测': self._generate_five_year_forecast(),
            '风险分析': self._generate_risk_analysis(),
            '监控与调整策略': self._generate_monitoring_strategy(),
            '关键时间节点': self._generate_key_milestones(),
        }
        
        return plan
    
    def _get_basic_info(self) -> Dict:
        """获取基本信息"""
        return {
            '总资金': f'¥{self.total_capital:,.0f}',
            '计划起始日': self.start_date.strftime('%Y-%m-%d'),
            '计划结束日': (self.start_date + timedelta(days=5*365)).strftime('%Y-%m-%d'),
            '持有周期': '5年',
            '投资理念': '康波周期理论 + 十五五规划 + 价值成长双轮驱动',
            '风险偏好': '中等偏进取',
            '预期年化收益': '15-25%',
            '最大可接受回撤': '25%',
        }
    
    def _generate_asset_allocation(self) -> Dict:
        """生成资产配置方案"""
        allocation = {}
        
        for sector_name, sector_data in self.portfolio_config.items():
            sector_allocation = {
                '配置比例': f"{sector_data['allocation']*100:.0f}%",
                '金额': f"¥{self.total_capital * sector_data['allocation']:,.0f}",
                '标的数量': len(sector_data['stocks']),
                '个股明细': []
            }
            
            for stock in sector_data['stocks']:
                amount = self.total_capital * sector_data['allocation'] * stock['weight'] / sum(s['weight'] for s in sector_data['stocks'])
                shares = int(amount / self._estimate_price(stock['code']))
                
                sector_allocation['个股明细'].append({
                    '代码': stock['code'],
                    '名称': stock['name'],
                    '细分仓位': f"{stock['weight']*100:.0f}%",
                    '预估金额': f"¥{amount:,.0f}",
                    '预估股数': f"{shares:,}股",
                    '所属细分': stock['sector'],
                })
            
            allocation[self._get_sector_name(sector_name)] = sector_allocation
        
        return allocation
    
    def _estimate_price(self, code: str) -> float:
        """估算股价（用于计算股数）"""
        # 简化版：根据代码范围估算
        if code.startswith('688'):  # 科创板，通常较高
            return 100.0
        elif code.startswith('300') or code.startswith('159'):  # 创业板/ETF
            return 50.0
        elif code.startswith('51') or code.startswith('58'):  # ETF
            return 1.0
        else:  # 主板
            return 20.0
    
    def _get_sector_name(self, key: str) -> str:
        """获取板块中文名称"""
        names = {
            'tech_growth': '科技成长板块',
            'energy_transition': '能源转型板块',
            'advanced_manufacturing': '高端制造板块',
            'petrochemical': '大炼化一体化',
            'defensive': '防御性配置',
        }
        return names.get(key, key)
    
    def _generate_phased_building_plan(self) -> List[Dict]:
        """生成分阶段建仓计划"""
        phases = []
        
        # 第一阶段：核心建仓期（第1-3个月）
        phase1 = {
            '阶段': '第一阶段 - 核心建仓期',
            '时间窗口': f'{self.start_date.strftime("%Y-%m-%d")} ~ {(self.start_date + timedelta(days=90)).strftime("%Y-%m-%d")}',
            '目标仓位': '50-60%',
            '重点标的': ['卫星化学', '恒力石化', '中际旭创', '中国神华', '科创50ETF'],
            '操作策略': [
                '分批买入低估值蓝筹（恒力、神华）',
                '等待回调后介入成长股（中际旭创、卫星化学）',
                '定投方式建仓指数ETF',
            ],
            '风险控制': '单只不超过总仓位10%，设置-15%止损',
        }
        phases.append(phase1)
        
        # 第二阶段：进攻加仓期（第4-9个月）
        phase2 = {
            '阶段': '第二阶段 - 进攻加仓期',
            '时间窗口': f'{(self.start_date + timedelta(days=91)).strftime("%Y-%m-%d")} ~ {(self.start_date + timedelta(days=270)).strftime("%Y-%m-%d")}',
            '目标仓位': '75-85%',
            '重点标的': ['海光信息', '阳光电源', '国电南瑞', '桐昆股份', '绿的谐波'],
            '操作策略': [
                '确认趋势后加仓科技成长股',
                '能源转型板块逢低吸纳',
                '高端制造板块右侧交易',
            ],
            '风险控制': '动态止盈，涨幅超30%减半仓',
        }
        phases.append(phase2)
        
        # 第三阶段：优化调整期（第10-18个月）
        phase3 = {
            '阶段': '第三阶段 - 优化调整期',
            '时间窗口': f'{(self.start_date + timedelta(days=271)).strftime("%Y-%m-%d")} ~ {(self.start_date + timedelta(days=540)).strftime("%Y-%m-%d")}',
            '目标仓位': '85-95%',
            '重点标的': ['全组合动态平衡'],
            '操作策略': [
                '去弱留强，淘汰表现不佳标的',
                '增加强势股仓位',
                '引入新机会（如有）',
            ],
            '风险控制': '整体回撤控制在20%以内',
        }
        phases.append(phase3)
        
        # 第四阶段：长期持有期（第19-60个月）
        phase4 = {
            '阶段': '第四阶段 - 长期持有期',
            '时间窗口': f'{(self.start_date + timedelta(days=541)).strftime("%Y-%m-%d")} ~ {(self.start_date + timedelta(days=1825)).strftime("%Y-%m-%d")}',
            '目标仓位': '90-100%',
            '重点标的': ['核心持仓长期持有'],
            '操作策略': [
                '享受复利增长',
                '定期再平衡（每季度）',
                '分红再投资',
            ],
            '风险控制': '极端行情下适度减仓至70%',
        }
        phases.append(phase4)
        
        return phases
    
    def _generate_five_year_forecast(self) -> Dict:
        """生成五年收益预测"""
        
        # 各板块预期年化收益
        sector_returns = {
            '科技成长板块': {'保守': 0.20, '中性': 0.30, '乐观': 0.45},
            '能源转型板块': {'保守': 0.12, '中性': 0.18, '乐观': 0.25},
            '高端制造板块': {'保守': 0.15, '中性': 0.22, '乐观': 0.35},
            '大炼化一体化': {'保守': 0.10, '中性': 0.15, '乐观': 0.22},
            '防御性配置': {'保守': 0.05, '中性': 0.08, '乐观': 0.12},
        }
        
        # 加权计算组合收益
        weights = {
            '科技成长板块': 0.35,
            '能源转型板块': 0.25,
            '高端制造板块': 0.20,
            '大炼化一体化': 0.15,
            '防御性配置': 0.05,
        }
        
        portfolio_return = {'保守': 0, '中性': 0, '乐观': 0}
        for sector, weight in weights.items():
            for scenario in ['保守', '中性', '乐观']:
                portfolio_return[scenario] += sector_returns[sector][scenario] * weight
        
        # 五年复合收益预测
        five_year_forecast = {}
        for scenario in ['保守', '中性', '乐观']:
            annual_return = portfolio_return[scenario]
            final_value = self.total_capital * ((1 + annual_return) ** 5)
            total_profit = final_value - self.total_capital
            
            five_year_forecast[scenario] = {
                '年化收益率': f"{annual_return*100:.1f}%",
                '五年后资产': f"¥{final_value:,.0f}",
                '累计收益': f"¥{total_profit:,.0f}",
                '收益倍数': f"{final_value/self.total_capital:.2f}倍",
            }
        
        # 年度分解
        yearly_breakdown = []
        current_value = self.total_capital
        for year in range(1, 6):
            year_scenario = {}
            for scenario in ['保守', '中性', '乐观']:
                annual_return = portfolio_return[scenario]
                year_end_value = current_value * (1 + annual_return)
                year_profit = year_end_value - current_value
                
                year_scenario[scenario] = {
                    '年末资产': f"¥{year_end_value:,.0f}",
                    '当年收益': f"¥{year_profit:,.0f}",
                    '当年收益率': f"{annual_return*100:.1f}%",
                }
            
            yearly_breakdown.append({
                '年份': f'第{year}年 ({self.start_date.year + year - 1})',
                '情景预测': year_scenario,
            })
            
            # 使用中性情景作为下一年的起点
            current_value = current_value * (1 + portfolio_return['中性'])
        
        return {
            '总体预测': five_year_forecast,
            '年度分解': yearly_breakdown,
            '关键假设': [
                '中国经济保持5-6%增速',
                '康波周期进入上行阶段',
                '十五五规划政策持续支持',
                '无系统性金融风险',
                '通胀温和（2-3%）',
            ],
        }
    
    def _generate_risk_analysis(self) -> Dict:
        """生成风险分析"""
        
        return {
            '市场风险': {
                '描述': '股市系统性下跌',
                '概率': '中等',
                '影响': '组合整体回撤15-25%',
                '应对': '保持20%现金，极端行情减仓至70%',
            },
            '行业风险': {
                '描述': '单一行业政策利空或景气度下行',
                '概率': '中等',
                '影响': '相关板块回撤20-30%',
                '应对': '分散配置5大板块，单板块不超35%',
            },
            '个股风险': {
                '描述': '个股黑天鹅事件',
                '概率': '低',
                '影响': '单只股票损失15-50%',
                '应对': '单只不超10%，设置-15%硬止损',
            },
            '流动性风险': {
                '描述': '急需用钱时无法及时变现',
                '概率': '低',
                '影响': '被迫低价卖出',
                '应对': '保留应急资金，避免满仓',
            },
            '汇率风险': {
                '描述': '人民币贬值影响进口成本',
                '概率': '低',
                '影响': '炼化板块成本上升',
                '应对': '关注美元走势，适当配置黄金',
            },
            '最大回撤预测': {
                '保守估计': '15-20%',
                '中性估计': '20-25%',
                '极端情况': '30-35%',
                '历史参考': '类似组合在2018年回撤约22%',
            },
            '夏普比率预测': {
                '保守': 0.8,
                '中性': 1.2,
                '乐观': 1.5,
                '说明': '>1为良好，>1.5为优秀',
            },
        }
    
    def _generate_monitoring_strategy(self) -> Dict:
        """生成监控与调整策略"""
        
        return {
            '日常监控': {
                '频率': '每日收盘后',
                '内容': [
                    '检查持仓盈亏',
                    '监控触发止损/止盈条件',
                    '关注重大新闻事件',
                ],
            },
            '周度复盘': {
                '频率': '每周日晚',
                '内容': [
                    '统计本周盈亏',
                    '评估各板块相对强弱',
                    '检查是否需要调仓',
                    '更新交易日志',
                ],
            },
            '月度调整': {
                '频率': '每月最后一个交易日',
                '内容': [
                    '计算月度收益率',
                    '对比基准指数表现',
                    '执行再平衡（偏离>5%时）',
                    '评估是否新增/剔除标的',
                ],
            },
            '季度审视': {
                '频率': '每季度末',
                '内容': [
                    '深度复盘季度表现',
                    '调整下半年策略',
                    '评估宏观环境变化',
                    '更新五年计划假设',
                ],
            },
            '年度总结': {
                '频率': '每年12月31日',
                '内容': [
                    '全年收益总结',
                    '与五年计划对比',
                    '制定下一年度计划',
                    '税务规划',
                ],
            },
            '调仓触发条件': [
                '单只股票涨幅>50% → 减半仓锁定利润',
                '单只股票跌幅>-15% → 坚决止损',
                '板块连续3月跑输基准 → 考虑替换',
                '基本面恶化（业绩下滑>30%）→ 立即离场',
                '政策重大利空 → 快速减仓',
            ],
        }
    
    def _generate_key_milestones(self) -> List[Dict]:
        """生成关键时间节点"""
        
        milestones = []
        
        # 2026年
        milestones.append({
            '日期': '2026-06-16',
            '事件': '周一开盘执行建仓',
            '操作': '买入第一批核心标的（卫星化学、恒力石化、中国神华）',
            '目标': '建立10-15%底仓',
        })
        
        milestones.append({
            '日期': '2026-06-30',
            '事件': '半年报预告披露',
            '操作': '验证基本面，去弱留强',
            '目标': '仓位提升至30%',
        })
        
        milestones.append({
            '日期': '2026-09-30',
            '事件': '三季报披露',
            '操作': '评估Q3表现，调整Q4策略',
            '目标': '仓位达到50-60%',
        })
        
        # 2027年
        milestones.append({
            '日期': '2027-03-31',
            '事件': '年报+一季报',
            '操作': '全面审视持仓，优化组合',
            '目标': '仓位达到75-85%',
        })
        
        milestones.append({
            '日期': '2027-10-31',
            '事件': '三季报+十五五规划中期评估',
            '操作': '根据政策导向调整',
            '目标': '仓位达到85-95%',
        })
        
        # 2028-2030年
        for year in [2028, 2029, 2030]:
            milestones.append({
                '日期': f'{year}-12-31',
                '事件': f'{year}年度总结',
                '操作': '年度复盘，制定下一年计划',
                '目标': '保持90-100%仓位，享受复利',
            })
        
        # 2031年
        milestones.append({
            '日期': '2031-06-12',
            '事件': '五年计划到期',
            '操作': '全面评估五年表现，决定下一步',
            '目标': '实现15-25%年化收益',
        })
        
        return milestones
    
    def export_to_markdown(self, filename: str = None) -> str:
        """导出为Markdown格式"""
        
        if filename is None:
            filename = f"200万五年交易计划_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        plan = self.generate_detailed_plan()
        
        md_content = []
        md_content.append("# 200万资金五年交易计划\n")
        md_content.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md_content.append(f"**计划周期**: 5年 ({plan['基本信息']['计划起始日']} ~ {plan['基本信息']['计划结束日']})\n")
        md_content.append(f"**总资金**: {plan['基本信息']['总资金']}\n")
        md_content.append("---\n")
        
        # 基本信息
        md_content.append("## 📋 基本信息\n")
        for key, value in plan['基本信息'].items():
            md_content.append(f"- **{key}**: {value}\n")
        md_content.append("\n---\n")
        
        # 资产配置
        md_content.append("## 💼 资产配置方案\n")
        for sector_name, sector_data in plan['资产配置方案'].items():
            md_content.append(f"\n### {sector_name} ({sector_data['配置比例']})\n")
            md_content.append(f"**配置金额**: {sector_data['金额']}\n")
            md_content.append(f"**标的数量**: {sector_data['标的数量']}只\n")
            md_content.append("\n| 代码 | 名称 | 仓位 | 金额 | 股数 | 细分 |\n")
            md_content.append("|------|------|------|------|------|------|\n")
            for stock in sector_data['个股明细']:
                md_content.append(f"| {stock['代码']} | {stock['名称']} | {stock['细分仓位']} | {stock['预估金额']} | {stock['预估股数']} | {stock['所属细分']} |\n")
        
        md_content.append("\n---\n")
        
        # 分阶段建仓
        md_content.append("## 📅 分阶段建仓计划\n")
        for phase in plan['分阶段建仓计划']:
            md_content.append(f"\n### {phase['阶段']}\n")
            md_content.append(f"**时间**: {phase['时间窗口']}\n")
            md_content.append(f"**目标仓位**: {phase['目标仓位']}\n")
            md_content.append(f"**重点标的**: {', '.join(phase['重点标的'])}\n")
            md_content.append("\n**操作策略**:\n")
            for strategy in phase['操作策略']:
                md_content.append(f"- {strategy}\n")
            md_content.append(f"\n**风险控制**: {phase['风险控制']}\n")
        
        md_content.append("\n---\n")
        
        # 五年收益预测
        md_content.append("## 📈 五年收益预测\n")
        md_content.append("\n### 总体预测\n")
        md_content.append("\n| 情景 | 年化收益 | 五年后资产 | 累计收益 | 收益倍数 |\n")
        md_content.append("|------|---------|-----------|---------|----------|\n")
        for scenario, data in plan['五年收益预测']['总体预测'].items():
            md_content.append(f"| {scenario} | {data['年化收益率']} | {data['五年后资产']} | {data['累计收益']} | {data['收益倍数']} |\n")
        
        md_content.append("\n### 年度分解（中性情景）\n")
        md_content.append("\n| 年份 | 年末资产 | 当年收益 | 当年收益率 |\n")
        md_content.append("|------|---------|---------|------------|\n")
        for year_data in plan['五年收益预测']['年度分解']:
            neutral = year_data['情景预测']['中性']
            md_content.append(f"| {year_data['年份']} | {neutral['年末资产']} | {neutral['当年收益']} | {neutral['当年收益率']} |\n")
        
        md_content.append("\n**关键假设**:\n")
        for assumption in plan['五年收益预测']['关键假设']:
            md_content.append(f"- {assumption}\n")
        
        md_content.append("\n---\n")
        
        # 风险分析
        md_content.append("## ⚠️ 风险分析\n")
        for risk_type, risk_data in plan['风险分析'].items():
            if isinstance(risk_data, dict):
                md_content.append(f"\n### {risk_type}\n")
                for key, value in risk_data.items():
                    md_content.append(f"- **{key}**: {value}\n")
        
        md_content.append("\n---\n")
        
        # 监控策略
        md_content.append("## 🔍 监控与调整策略\n")
        for freq, strategy in plan['监控与调整策略'].items():
            if isinstance(strategy, dict):
                md_content.append(f"\n### {freq}\n")
                if '频率' in strategy:
                    md_content.append(f"**频率**: {strategy['频率']}\n")
                if '内容' in strategy:
                    md_content.append("**监控内容**:\n")
                    for item in strategy['内容']:
                        md_content.append(f"- {item}\n")
            elif isinstance(strategy, list):
                md_content.append(f"\n### {freq}\n")
                for item in strategy:
                    md_content.append(f"- {item}\n")
        
        md_content.append("\n---\n")
        
        # 关键节点
        md_content.append("##  关键时间节点\n")
        md_content.append("\n| 日期 | 事件 | 操作 | 目标 |\n")
        md_content.append("|------|------|------|------|\n")
        for milestone in plan['关键时间节点']:
            md_content.append(f"| {milestone['日期']} | {milestone['事件']} | {milestone['操作']} | {milestone['目标']} |\n")
        
        md_content.append("\n---\n")
        md_content.append("\n**分析师**: AI量化助手\n")
        md_content.append(f"**报告生成**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md_content.append("\n*免责声明: 本计划仅供参考，不构成投资建议。投资有风险，入市需谨慎。*\n")
        
        content = ''.join(md_content)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 交易计划已生成: {filename}")
        return content
    
    def print_summary(self):
        """打印摘要"""
        plan = self.generate_detailed_plan()
        
        print("=" * 80)
        print("📊 200万资金五年交易计划 - 摘要")
        print("=" * 80)
        print(f"\n💰 总资金: {plan['基本信息']['总资金']}")
        print(f"📅 计划周期: 5年 ({plan['基本信息']['计划起始日']} ~ {plan['基本信息']['计划结束日']})")
        print(f"🎯 预期年化: {plan['基本信息']['预期年化收益']}")
        print(f"⚠️  最大回撤: {plan['基本信息']['最大可接受回撤']}")
        
        print("\n📈 五年收益预测:")
        print("-" * 80)
        for scenario, data in plan['五年收益预测']['总体预测'].items():
            print(f"  {scenario:6s}: 年化{data['年化收益率']:6s} | 五年后 {data['五年后资产']:15s} | 累计 {data['累计收益']:15s}")
        
        print("\n💼 资产配置:")
        print("-" * 80)
        for sector_name, sector_data in plan['资产配置方案'].items():
            print(f"  {sector_name:12s}: {sector_data['配置比例']:6s} ({sector_data['金额']:15s})")
        
        print("\n📅 第一阶段建仓 (2026-06-16 周一开盘):")
        print("-" * 80)
        phase1 = plan['分阶段建仓计划'][0]
        print(f"  目标仓位: {phase1['目标仓位']}")
        print(f"  重点标的: {', '.join(phase1['重点标的'])}")
        
        print("\n⚠️  风险提示:")
        print("-" * 80)
        max_drawdown = plan['风险分析']['最大回撤预测']
        print(f"  保守: {max_drawdown['保守估计']}")
        print(f"  中性: {max_drawdown['中性估计']}")
        print(f"  极端: {max_drawdown['极端情况']}")
        
        print("\n" + "=" * 80)


if __name__ == '__main__':
    # 创建交易计划
    planner = FiveYearTradingPlan(total_capital=2_000_000)
    
    # 打印摘要
    planner.print_summary()
    
    # 导出完整计划
    filename = "e:/各种PY程序/11_量化策略/reports/2026-06-12/200万五年交易计划_康波周期+十五五规划.md"
    planner.export_to_markdown(filename)
    
    print(f"\n✅ 完整交易计划已保存至: {filename}")
    print("💡 建议: 在Typora中打开查看格式化版本")
