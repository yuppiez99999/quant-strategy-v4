# -*- coding: utf-8 -*-
"""
量化策略系统 v4.2.1 - 整合版 (Excel增强版)
整合所有核心模块的统一入口，基于5个Excel表格数据驱动

版本: v4.2.1 (Excel增强版)
更新内容:
  - 新增Excel驱动再平衡引擎 (ExcelDrivenRebalancingEngine)
  - 支持5个Excel表格联动: complete_plan, batch_plan, summary, fund_flow, comparison
  - 内置备选配置 (无需pandas也能正常运行)
  - 分批执行计划支持: 第二批(1个月内), 第三批(3个月内)

功能模块:
  1. 实时行情数据获取 (Wind / iFinD / 新浪三级回退)
  2. 自动交易与盘中再平衡
  3. 增强版再平衡引擎 (Excel数据驱动 - 5表联动)
  4. 每日报告生成 (含AI分析 + 组合对比分析)
  5. 止损止盈风险监控 (基于Excel配置的动态止损)
  6. 组合管理与仓位优化 (基于Excel完整计划)

Excel数据源:
  - data_extraction_complete_rebalancing_plan.xlsx: 完整再平衡计划
  - data_extraction_batch_execution_plan.xlsx: 分批执行计划
  - data_extraction_execution_summary_and_tips.xlsx: 执行总结与策略建议
  - data_extraction_fund_flow_summary.xlsx: 资金流向汇总
  - data_extraction_portfolio_comparison_analysis.xlsx: 组合对比分析

运行模式:
  - 实时监控模式: 盘中实时行情监控 + 自动再平衡
  - 报告生成模式: 生成每日持仓报告
  - 回测模式: 历史数据回测验证
  - 再平衡模式: 执行Excel驱动的再平衡计划
  - 风险监控模式: 检查止损止盈状态
  - 检查模式: 快速检查系统状态

使用方式:
  python "量化策略系统 v4.2 - 整合版.py" --rebalance  # 执行Excel再平衡
  python "量化策略系统 v4.2 - 整合版.py" --report     # 生成报告
  python "量化策略系统 v4.2 - 整合版.py" --live       # 实时监控
  python "量化策略系统 v4.2 - 整合版.py" --risk       # 风险监控
  python "量化策略系统 v4.2 - 整合版.py" --check      # 系统检查
"""

import os
import sys
import argparse
import logging
import json
from datetime import datetime, time as dt_time

# Windows控制台UTF-8编码支持
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ============================================================
# Excel再平衡引擎 - 基于5个Excel表格驱动
# ============================================================

class ExcelDrivenRebalancingEngine:
    """增强版Excel驱动再平衡引擎
    
    数据源:
    - complete_rebalancing_plan.xlsx: 12只标的完整计划（目标权重、风险权重、止损位、止盈位等）
    - batch_execution_plan.xlsx: 分批执行计划（第二批1个月内、第三批3个月内）
    - execution_summary_and_tips.xlsx: 执行策略建议（战略方向、分批逻辑、止损纪律等）
    - fund_flow_summary.xlsx: 资金流向汇总（买入/卖出金额、需追加资金等）
    - portfolio_comparison_analysis.xlsx: 调仓前后对比分析
    """
    
    EXCEL_FILES = {
        'complete_plan': 'data_extraction_complete_rebalancing_plan.xlsx',
        'batch_plan': 'data_extraction_batch_execution_plan.xlsx',
        'summary': 'data_extraction_execution_summary_and_tips.xlsx',
        'fund_flow': 'data_extraction_fund_flow_summary.xlsx',
        'comparison': 'data_extraction_portfolio_comparison_analysis.xlsx',
    }
    
    def __init__(self):
        self.is_loaded = False
        self.complete_plan = []
        self.batch_plan = []
        self.summary_tips = []
        self.fund_flow = {}
        self.comparison_data = []
        self.pd = None
        self._try_import_pandas()
    
    def _try_import_pandas(self):
        """尝试加载pandas，失败时提供备选方案"""
        try:
            import pandas as pd
            self.pd = pd
            return True
        except ImportError:
            print("  ⚠️ 未安装pandas，将使用内置表格配置作为备选方案")
            self.pd = None
            return False
    
    def load_all(self):
        """加载所有5个Excel表格"""
        if self.pd is not None:
            return self._load_from_excel()
        else:
            return self._load_fallback_config()
    
    def _load_from_excel(self):
        """从Excel文件加载配置"""
        print(f"\n📂 正在加载Excel配置文件 (目录: {BASE_DIR})")
        
        loaded_count = 0
        
        # 1. 加载完整再平衡计划
        try:
            filepath = os.path.join(BASE_DIR, self.EXCEL_FILES['complete_plan'])
            if os.path.exists(filepath):
                df = self.pd.read_excel(filepath)
                self.complete_plan = df.to_dict('records')
                print(f"  ✅ 完整再平衡计划: {len(self.complete_plan)} 只标的")
                loaded_count += 1
            else:
                print(f"  ⚠️ 未找到: {self.EXCEL_FILES['complete_plan']}")
        except Exception as e:
            print(f"  ❌ 加载失败: {e}")
        
        # 2. 加载分批执行计划
        try:
            filepath = os.path.join(BASE_DIR, self.EXCEL_FILES['batch_plan'])
            if os.path.exists(filepath):
                df = self.pd.read_excel(filepath)
                self.batch_plan = df.to_dict('records')
                print(f"  ✅ 分批执行计划: {len(self.batch_plan)} 条交易指令")
                loaded_count += 1
            else:
                print(f"  ⚠️ 未找到: {self.EXCEL_FILES['batch_plan']}")
        except Exception as e:
            print(f"  ❌ 加载失败: {e}")
        
        # 3. 加载执行总结与建议
        try:
            filepath = os.path.join(BASE_DIR, self.EXCEL_FILES['summary'])
            if os.path.exists(filepath):
                df = self.pd.read_excel(filepath)
                self.summary_tips = df.to_dict('records')
                print(f"  ✅ 执行总结与策略建议: {len(self.summary_tips)} 条")
                loaded_count += 1
            else:
                print(f"  ⚠️ 未找到: {self.EXCEL_FILES['summary']}")
        except Exception as e:
            print(f"  ❌ 加载失败: {e}")
        
        # 4. 加载资金流向
        try:
            filepath = os.path.join(BASE_DIR, self.EXCEL_FILES['fund_flow'])
            if os.path.exists(filepath):
                df = self.pd.read_excel(filepath)
                self.fund_flow = {
                    'total_sell': 0,
                    'total_buy': 0,
                    'net_flow': 0,
                    'fee_estimate': 0,
                    'additional_capital': 0,
                    'details': []
                }
                for _, row in df.iterrows():
                    item_name = str(row.iloc[0]) if len(row) > 0 else ''
                    amount = row.iloc[1] if len(row) > 1 else 0
                    note = str(row.iloc[2]) if len(row) > 2 else ''
                    try:
                        amount_val = float(amount)
                    except (ValueError, TypeError):
                        amount_val = 0
                    self.fund_flow['details'].append({
                        'item': item_name,
                        'amount': amount_val,
                        'note': note
                    })
                    if '卖出小计' in item_name:
                        self.fund_flow['total_sell'] = amount_val
                    elif '买入小计' in item_name:
                        self.fund_flow['total_buy'] = amount_val
                    elif '资金净流动' in item_name or '净流动' in item_name:
                        self.fund_flow['net_flow'] = amount_val
                    elif '费用' in item_name or 'fee' in item_name.lower():
                        self.fund_flow['fee_estimate'] = amount_val
                    elif '追加' in item_name or 'additional' in item_name.lower():
                        self.fund_flow['additional_capital'] = amount_val
                print(f"  ✅ 资金流向汇总已加载")
                loaded_count += 1
            else:
                print(f"  ⚠️ 未找到: {self.EXCEL_FILES['fund_flow']}")
        except Exception as e:
            print(f"  ❌ 加载失败: {e}")
        
        # 5. 加载组合对比分析
        try:
            filepath = os.path.join(BASE_DIR, self.EXCEL_FILES['comparison'])
            if os.path.exists(filepath):
                df = self.pd.read_excel(filepath)
                self.comparison_data = df.to_dict('records')
                print(f"  ✅ 组合对比分析: {len(self.comparison_data)} 项指标")
                loaded_count += 1
            else:
                print(f"  ⚠️ 未找到: {self.EXCEL_FILES['comparison']}")
        except Exception as e:
            print(f"  ❌ 加载失败: {e}")
        
        self.is_loaded = (loaded_count >= 1)
        if self.is_loaded:
            print(f"\n  📊 成功加载 {loaded_count}/5 个配置文件")
        return self.is_loaded
    
    def _load_fallback_config(self):
        """内置备选配置（与Excel表格数据一致）"""
        print("  ⚠️ 使用内置配置（无pandas）")
        
        # 完整再平衡计划 - 与Excel表格一致
        self.complete_plan = [
            {'证券代码': '601088', '证券名称': '中国神华', '行业分类': '制造转型',
             '目标权重': 0.12, '风险权重': 0.22, '当前仓位(%)': 0.15, '调整幅度(%)': -0.0284,
             '当前股数': 3300, '最新价(元)': 44.98, '当前市值(元)': 148434, '目标市值(元)': 120000,
             '目标股数': 2600, '需调整股数': -700, '交易方向': '卖出', '预计交易金额(元)': 31486,
             '操作类型': '减持', '执行批次': '第二批', '止损位(元)': 38.23, '止盈位(元)': 58.47,
             '交易费用(元)': 9, '需特别注意': False},
            {'证券代码': '000425', '证券名称': '徐工机械', '行业分类': '制造转型',
             '目标权重': 0.10, '风险权重': 0.23, '当前仓位(%)': 0.10, '调整幅度(%)': 0.0006,
             '当前股数': 10300, '最新价(元)': 9.65, '当前市值(元)': 99395, '目标市值(元)': 100000,
             '目标股数': 10300, '需调整股数': 0, '交易方向': '无', '预计交易金额(元)': 0,
             '操作类型': '维持', '执行批次': '第二批', '止损位(元)': 8.20, '止盈位(元)': 12.55,
             '交易费用(元)': 0, '需特别注意': False},
            {'证券代码': '600276', '证券名称': '恒瑞医药', '行业分类': '核心成长',
             '目标权重': 0.10, '风险权重': 0.24, '当前仓位(%)': 0.05, '调整幅度(%)': 0.0546,
             '当前股数': 900, '最新价(元)': 50.47, '当前市值(元)': 45423, '目标市值(元)': 100000,
             '目标股数': 1900, '需调整股数': 1000, '交易方向': '买入', '预计交易金额(元)': 50470,
             '操作类型': '增持', '执行批次': '第二批', '止损位(元)': 42.90, '止盈位(元)': 65.61,
             '交易费用(元)': 15, '需特别注意': False},
            {'证券代码': '600995', '证券名称': '南网储能', '行业分类': '核心成长',
             '目标权重': 0.10, '风险权重': 0.22, '当前仓位(%)': 0.15, '调整幅度(%)': -0.0496,
             '当前股数': 10500, '最新价(元)': 14.25, '当前市值(元)': 149625, '目标市值(元)': 100000,
             '目标股数': 7000, '需调整股数': -3500, '交易方向': '卖出', '预计交易金额(元)': 49875,
             '操作类型': '减持', '执行批次': '第二批', '止损位(元)': 12.11, '止盈位(元)': 18.53,
             '交易费用(元)': 15, '需特别注意': False},
            {'证券代码': '002371', '证券名称': '北方华创', '行业分类': '核心成长',
             '目标权重': 0.08, '风险权重': 0.32, '当前仓位(%)': 0.07, '调整幅度(%)': 0.0131,
             '当前股数': 100, '最新价(元)': 669.00, '当前市值(元)': 66900, '目标市值(元)': 80000,
             '目标股数': 100, '需调整股数': 0, '交易方向': '无', '预计交易金额(元)': 0,
             '操作类型': '维持', '执行批次': '第二批', '止损位(元)': 568.65, '止盈位(元)': 869.70,
             '交易费用(元)': 0, '需特别注意': True},
            {'证券代码': '688017', '证券名称': '绿的谐波', '行业分类': '核心成长',
             '目标权重': 0.06, '风险权重': 0.35, '当前仓位(%)': 0.03, '调整幅度(%)': 0.0258,
             '当前股数': 100, '最新价(元)': 342.00, '当前市值(元)': 34200, '目标市值(元)': 60000,
             '目标股数': 100, '需调整股数': 0, '交易方向': '无', '预计交易金额(元)': 0,
             '操作类型': '维持', '执行批次': '第二批', '止损位(元)': 290.70, '止盈位(元)': 444.60,
             '交易费用(元)': 0, '需特别注意': True},
            {'证券代码': '688981', '证券名称': '中芯国际', '行业分类': '核心成长',
             '目标权重': 0.08, '风险权重': 0.30, '当前仓位(%)': 0.00, '调整幅度(%)': 0.0800,
             '当前股数': 0, '最新价(元)': 55.20, '当前市值(元)': 0, '目标市值(元)': 80000,
             '目标股数': 1400, '需调整股数': 1400, '交易方向': '买入', '预计交易金额(元)': 77280,
             '操作类型': '新增', '执行批次': '第二批', '止损位(元)': 46.92, '止盈位(元)': 71.76,
             '交易费用(元)': 23, '需特别注意': False},
            {'证券代码': '300750', '证券名称': '宁德时代', '行业分类': '核心成长',
             '目标权重': 0.08, '风险权重': 0.31, '当前仓位(%)': 0.00, '调整幅度(%)': 0.0800,
             '当前股数': 0, '最新价(元)': 216.50, '当前市值(元)': 0, '目标市值(元)': 80000,
             '目标股数': 300, '需调整股数': 300, '交易方向': '买入', '预计交易金额(元)': 64950,
             '操作类型': '新增', '执行批次': '第二批', '止损位(元)': 184.03, '止盈位(元)': 281.45,
             '交易费用(元)': 19, '需特别注意': True},
            {'证券代码': '300124', '证券名称': '汇川技术', '行业分类': '核心成长',
             '目标权重': 0.07, '风险权重': 0.28, '当前仓位(%)': 0.00, '调整幅度(%)': 0.0700,
             '当前股数': 0, '最新价(元)': 68.80, '当前市值(元)': 0, '目标市值(元)': 70000,
             '目标股数': 1000, '需调整股数': 1000, '交易方向': '买入', '预计交易金额(元)': 68800,
             '操作类型': '新增', '执行批次': '第二批', '止损位(元)': 58.48, '止盈位(元)': 89.44,
             '交易费用(元)': 21, '需特别注意': False},
            {'证券代码': '002475', '证券名称': '立讯精密', '行业分类': '核心成长',
             '目标权重': 0.07, '风险权重': 0.26, '当前仓位(%)': 0.00, '调整幅度(%)': 0.0700,
             '当前股数': 0, '最新价(元)': 38.50, '当前市值(元)': 0, '目标市值(元)': 70000,
             '目标股数': 1800, '需调整股数': 1800, '交易方向': '买入', '预计交易金额(元)': 69300,
             '操作类型': '新增', '执行批次': '第二批', '止损位(元)': 32.73, '止盈位(元)': 50.05,
             '交易费用(元)': 21, '需特别注意': False},
            {'证券代码': '603259', '证券名称': '药明康德', '行业分类': '核心成长',
             '目标权重': 0.06, '风险权重': 0.29, '当前仓位(%)': 0.00, '调整幅度(%)': 0.0600,
             '当前股数': 0, '最新价(元)': 45.60, '当前市值(元)': 0, '目标市值(元)': 60000,
             '目标股数': 1300, '需调整股数': 1300, '交易方向': '买入', '预计交易金额(元)': 59280,
             '操作类型': '新增', '执行批次': '第二批', '止损位(元)': 38.76, '止盈位(元)': 59.28,
             '交易费用(元)': 18, '需特别注意': False},
            {'证券代码': '518880', '证券名称': '黄金ETF', '行业分类': '防御资产',
             '目标权重': 0.08, '风险权重': 0.18, '当前仓位(%)': 0.02, '调整幅度(%)': 0.0601,
             '当前股数': 2100, '最新价(元)': 9.46, '当前市值(元)': 19866, '目标市值(元)': 80000,
             '目标股数': 8400, '需调整股数': 6300, '交易方向': '买入', '预计交易金额(元)': 59598,
             '操作类型': '增持', '执行批次': '第二批', '止损位(元)': 8.04, '止盈位(元)': 12.30,
             '交易费用(元)': 18, '需特别注意': False},
        ]
        
        # 分批执行计划
        self.batch_plan = [
            {'批次': '第二批', '执行时间': '1个月内', '证券代码': '518880', '证券名称': '黄金ETF',
             '操作类型': '增持', '需调整股数': 6300, '预计交易金额(元)': 59598,
             '资金流向': '流出', '累计资金变化(元)': -368317, '操作说明': '加仓至8%仓位,防御资产核心标的'},
            {'批次': '第二批', '执行时间': '1个月内', '证券代码': '600276', '证券名称': '恒瑞医药',
             '操作类型': '增持', '需调整股数': 1000, '预计交易金额(元)': 50470,
             '资金流向': '流出', '累计资金变化(元)': -18984, '操作说明': '加仓至10%仓位,核心成长核心标的'},
            {'批次': '第二批', '执行时间': '1个月内', '证券代码': '600995', '证券名称': '南网储能',
             '操作类型': '减持', '需调整股数': -3500, '预计交易金额(元)': 49875,
             '资金流向': '流入', '累计资金变化(元)': 30891, '操作说明': '减持至10%仓位,释放资金4.99万元'},
            {'批次': '第三批', '执行时间': '3个月内', '证券代码': '002475', '证券名称': '立讯精密',
             '操作类型': '新增', '需调整股数': 1800, '预计交易金额(元)': 69300,
             '资金流向': '流出', '累计资金变化(元)': -249439, '操作说明': '新增7%仓位,核心成长配置'},
            {'批次': '第三批', '执行时间': '3个月内', '证券代码': '300124', '证券名称': '汇川技术',
             '操作类型': '新增', '需调整股数': 1000, '预计交易金额(元)': 68800,
             '资金流向': '流出', '累计资金变化(元)': -180139, '操作说明': '新增7%仓位,核心成长配置'},
            {'批次': '第三批', '执行时间': '3个月内', '证券代码': '300750', '证券名称': '宁德时代',
             '操作类型': '新增', '需调整股数': 300, '预计交易金额(元)': 64950,
             '资金流向': '流出', '累计资金变化(元)': -111339, '操作说明': '新增8%仓位,核心成长配置'},
            {'批次': '第三批', '执行时间': '3个月内', '证券代码': '603259', '证券名称': '药明康德',
             '操作类型': '新增', '需调整股数': 1300, '预计交易金额(元)': 59280,
             '资金流向': '流出', '累计资金变化(元)': -308719, '操作说明': '新增6%仓位,核心成长配置'},
            {'批次': '第三批', '执行时间': '3个月内', '证券代码': '688981', '证券名称': '中芯国际',
             '操作类型': '新增', '需调整股数': 1400, '预计交易金额(元)': 77280,
             '资金流向': '流出', '累计资金变化(元)': -46389, '操作说明': '新增8%仓位,核心成长配置'},
        ]
        
        # 执行总结与策略建议
        self.summary_tips = [
            {'类别': '战略方向', '项目': '核心成长聚焦', '内容': '以核心成长(75%)为主轴,制造转型(17%)+防御资产(8%)为两翼', '优先级': '高'},
            {'类别': '行业配置', '项目': '科技+医药+高端制造', '内容': '新增半导体/新能源/自动化/消费电子/CXO子行业', '优先级': '高'},
            {'类别': '风险管控', '项目': '风险权重分层', '内容': '高风险(≥0.32):北方华创/绿的谐波;中风险(0.26-0.31):恒瑞/宁德/中芯/药明/汇川;低风险(≤0.25):其余', '优先级': '高'},
            {'类别': '第一批(本周内)', '项目': '高估值标的清理', '内容': '绿的谐波清仓(如有持仓),北方华创减持至8%', '优先级': '高'},
            {'类别': '第二批(1个月内)', '项目': '核心成长建仓', '内容': '增持恒瑞医药/南网储能/中芯国际/宁德时代/汇川技术/立讯精密/药明康德', '优先级': '中'},
            {'类别': '第三批(3个月内)', '项目': '防御资产配置', '内容': '黄金ETF加仓至8%', '优先级': '中'},
            {'类别': '需追加资金', '项目': '视持仓情况而定', '内容': '新增标的较多,建议提前准备资金', '优先级': '高'},
            {'类别': '行业分布优化', '项目': '降低单一行业依赖', '内容': '核心成长覆盖5个子行业,分散度提升', '优先级': '高'},
            {'类别': '止损纪律', '项目': '严格止损', '内容': '所有标的设置-15%止损位,高风险标的(-25%)', '优先级': '高'},
            {'类别': '止盈策略', '项目': '分批止盈', '内容': '核心成长+40%止盈,防御资产+20%止盈', '优先级': '中'},
            {'类别': '再平衡频率', '项目': '每季度审视', '内容': '权重偏离±5%时触发再平衡', '优先级': '中'},
            {'类别': '组合特征', '项目': '成长型偏进攻', '内容': '预期波动率较高,适合风险承受能力较强的投资者', '优先级': '中'},
        ]
        
        # 资金流向汇总
        self.fund_flow = {
            'total_sell': 81361.0,
            'total_buy': 449678.0,
            'net_flow': 368317.0,
            'fee_estimate': 159.0,
            'additional_capital': 368476.0,
            'details': [
                {'item': '卖出南网储能', 'amount': 49875, 'note': '3500股 x 14.25元/股'},
                {'item': '卖出中国神华', 'amount': 31486, 'note': '700股 x 44.98元/股'},
                {'item': '卖出小计', 'amount': 81361, 'note': '卖出交易合计'},
                {'item': '买入中芯国际', 'amount': 77280, 'note': '1400股 x 55.2元/股'},
                {'item': '买入立讯精密', 'amount': 69300, 'note': '1800股 x 38.5元/股'},
                {'item': '买入汇川技术', 'amount': 68800, 'note': '1000股 x 68.8元/股'},
                {'item': '买入宁德时代', 'amount': 64950, 'note': '300股 x 216.5元/股'},
                {'item': '买入黄金ETF', 'amount': 59598, 'note': '6300股 x 9.46元/股'},
                {'item': '买入药明康德', 'amount': 59280, 'note': '1300股 x 45.6元/股'},
                {'item': '买入恒瑞医药', 'amount': 50470, 'note': '1000股 x 50.47元/股'},
                {'item': '买入小计', 'amount': 449678, 'note': '买入交易合计'},
                {'item': '资金净流动', 'amount': 368317, 'note': '买入449678-卖出81361=需追加368317元'},
                {'item': '交易费用估算', 'amount': 159, 'note': '总交易金额531039 x 0.03%'},
                {'item': '实际需追加资金', 'amount': 368476, 'note': '资金净流动+交易费用'},
            ]
        }
        
        # 组合对比分析
        self.comparison_data = [
            {'指标类别': '配置结构', '指标名称': '标的数量', '调仓前数值': '12只', '调仓后数值': '12只', '变化幅度': '-', '变化方向': '-', '说明': '精简聚焦核心标的'},
            {'指标类别': '配置结构', '指标名称': '核心成长占比', '调仓前数值': '58%', '调仓后数值': '75%', '变化幅度': '+29%', '变化方向': '提升', '说明': '大幅提升成长暴露'},
            {'指标类别': '配置结构', '指标名称': '制造转型占比', '调仓前数值': '17%', '调仓后数值': '17%', '变化幅度': '0%', '变化方向': '持平', '说明': '中国神华+徐工机械'},
            {'指标类别': '配置结构', '指标名称': '防御资产占比', '调仓前数值': '8%', '调仓后数值': '8%', '变化幅度': '0%', '变化方向': '持平', '说明': '黄金ETF维持'},
            {'指标类别': '配置结构', '指标名称': '行业数量', '调仓前数值': '6个', '调仓后数值': '7个', '变化幅度': '+1', '变化方向': '增加', '说明': '新增半导体/CXO子行业'},
            {'指标类别': '风险指标', '指标名称': '最高风险权重', '调仓前数值': '0.35', '调仓后数值': '0.35', '变化幅度': '0%', '变化方向': '持平', '说明': '绿的谐波保持最高风险'},
            {'指标类别': '风险指标', '指标名称': '平均风险权重', '调仓前数值': '0.27', '调仓后数值': '0.27', '变化幅度': '0%', '变化方向': '持平', '说明': '整体风险水平相当'},
            {'指标类别': '风险指标', '指标名称': '低风险标的占比', '调仓前数值': '25%', '调仓后数值': '25%', '变化幅度': '0%', '变化方向': '持平', '说明': '神华/徐工/南网/黄金ETF'},
            {'指标类别': '收益指标', '指标名称': '加权目标收益率', '调仓前数值': '10-15%', '调仓后数值': '12-18%', '变化幅度': '+20%', '变化方向': '提升', '说明': '核心成长拉动'},
            {'指标类别': '收益指标', '指标名称': '股息率贡献', '调仓前数值': '1.8%', '调仓后数值': '1.2%', '变化幅度': '-33%', '变化方向': '下降', '说明': '防御仓位比例下降'},
            {'指标类别': '行业分布', '指标名称': '半导体', '调仓前数值': '0%', '调仓后数值': '17%(中芯+北方)', '变化幅度': '新增', '变化方向': '-', '说明': '新增半导体双龙头'},
            {'指标类别': '行业分布', '指标名称': '医药生物', '调仓前数值': '8%', '调仓后数值': '16%(恒瑞+药明)', '变化幅度': '+100%', '变化方向': '翻倍', '说明': '创新药+CXO双配置'},
            {'指标类别': '行业分布', '指标名称': '新能源', '调仓前数值': '10%', '调仓后数值': '8%(宁德)', '变化幅度': '-20%', '变化方向': '下降', '说明': '聚焦电池龙头'},
            {'指标类别': '行业分布', '指标名称': '工业自动化', '调仓前数值': '0%', '调仓后数值': '7%(汇川)', '变化幅度': '新增', '变化方向': '-', '说明': '工控龙头'},
            {'指标类别': '行业分布', '指标名称': '消费电子', '调仓前数值': '0%', '调仓后数值': '7%(立讯)', '变化幅度': '新增', '变化方向': '-', '说明': '苹果链核心'},
            {'指标类别': '行业分布', '指标名称': '煤炭', '调仓前数值': '15%', '调仓后数值': '12%', '变化幅度': '-20%', '变化方向': '下降', '说明': '神华降权重'},
            {'指标类别': '行业分布', '指标名称': '机械设备', '调仓前数值': '10%', '调仓后数值': '10%', '变化幅度': '0%', '变化方向': '持平', '说明': '徐工机械维持'},
        ]
        
        self.is_loaded = True
        print(f"\n  📊 成功加载内置配置 (12只标的 + 9条分批指令 + 12项策略建议)")
        return True
    
    def build_trade_orders(self, current_prices=None):
        """基于Excel配置 + 实时行情，构建交易指令"""
        if not self.is_loaded:
            return []
        
        print(f"\n📋 构建交易指令...")
        
        # 使用Excel配置的最新价作为基准
        if current_prices:
            print(f"  📈 已接入实时行情数据，共 {len(current_prices)} 只标的")
        else:
            print(f"  ⚠️ 使用Excel配置价格作为参考（共 {len(self.complete_plan)} 只标的）")
        
        # 汇总统计
        buy_amount = sum(float(item.get('预计交易金额(元)', 0)) for item in self.complete_plan if item.get('交易方向') == '买入' and float(item.get('需调整股数', 0)) > 0)
        sell_amount = sum(float(item.get('预计交易金额(元)', 0)) for item in self.complete_plan if item.get('交易方向') == '卖出')
        net_flow = buy_amount - sell_amount
        
        print(f"\n  📊 交易汇总:")
        print(f"    📥 买入总金额: ¥{buy_amount:,.2f}")
        print(f"    📤 卖出总金额: ¥{sell_amount:,.2f}")
        print(f"    💰 资金净需求: ¥{net_flow:,.2f}" if net_flow > 0 else f"    💰 资金净剩余: ¥{-net_flow:,.2f}")
        print(f"    🔖 预估交易费用: ¥{sum(float(item.get('交易费用(元)', 0)) for item in self.complete_plan):,.2f}")
        
        return self.complete_plan
    
    def get_batch_orders(self, batch_name='第二批'):
        """获取指定批次的交易计划"""
        return [item for item in self.batch_plan if item.get('批次') == batch_name]
    
    def get_stop_loss_rules(self):
        """从Excel配置中提取止损止盈规则（用于同步到监控系统）"""
        rules = []
        for item in self.complete_plan:
            code = str(item.get('证券代码', ''))
            name = item.get('证券名称', '')
            stop_loss = item.get('止损位(元)', 0)
            take_profit = item.get('止盈位(元)', 0)
            risk_weight = item.get('风险权重', 0.27)
            special = item.get('需特别注意', False)
            
            # 动态计算止损百分比
            current_price = item.get('最新价(元)', 0)
            if current_price > 0 and stop_loss > 0:
                sl_pct = (stop_loss - current_price) / current_price
            else:
                sl_pct = -0.15  # 默认-15%
            
            if current_price > 0 and take_profit > 0:
                tp_pct = (take_profit - current_price) / current_price
            else:
                tp_pct = 0.40  # 默认+40%
            
            rules.append({
                'code': code,
                'name': name,
                'stop_loss_price': stop_loss,
                'take_profit_price': take_profit,
                'stop_loss_pct': sl_pct,
                'take_profit_pct': tp_pct,
                'risk_weight': risk_weight,
                'special_monitoring': special
            })
        return rules
    
    def generate_comparison_report(self):
        """生成组合对比分析报告（调仓前后对比）"""
        lines = []
        lines.append("=" * 70)
        lines.append("📊 组合对比分析 - 调仓前后对比")
        lines.append("=" * 70)
        
        # 按指标类别分组
        categories = {}
        for item in self.comparison_data:
            cat = item.get('指标类别', '其他')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        for cat_name, items in categories.items():
            lines.append(f"\n[{cat_name}]")
            lines.append(f"  {'指标':<15} {'调仓前':>12} {'调仓后':>12} {'变化':>10} {'方向':<6}")
            lines.append("-" * 70)
            for item in items:
                name = item.get('指标名称', '')
                before = str(item.get('调仓前数值', '-'))
                after = str(item.get('调仓后数值', '-'))
                change = str(item.get('变化幅度', '-'))
                direction = str(item.get('变化方向', '-'))
                lines.append(f"  {name:<15} {before:>12} {after:>12} {change:>10} {direction:<6}")
        
        lines.append("\n" + "=" * 70)
        return "\n".join(lines)
    
    def generate_report(self, current_prices=None):
        """生成完整的再平衡执行报告"""
        if not self.is_loaded:
            return "❌ 再平衡数据未加载，请先检查Excel文件或调用load_all()"
        
        lines = []
        lines.append("=" * 70)
        lines.append(" 🔄 Excel驱动再平衡执行报告")
        lines.append(f" 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        
        # 战略方向
        strategic_items = [item for item in self.summary_tips if '战略' in str(item.get('类别', '')) or '行业' in str(item.get('类别', ''))]
        if strategic_items:
            lines.append(f"\n🎯 战略方向 (来自 execution_summary_and_tips.xlsx)")
            lines.append("-" * 70)
            for item in strategic_items[:3]:
                lines.append(f"  ▸ {item.get('项目', '')}: {item.get('内容', '')}")
        
        # 完整再平衡计划
        lines.append(f"\n[完整再平衡计划] (complete_rebalancing_plan.xlsx)")
        lines.append(f"  {'代码':<8} {'名称':<10} {'行业':<10} {'目标权重':>8} {'风险':>6} {'方向':>6} {'股数':>8} {'金额':>12} {'批次':>8}")
        lines.append("-" * 80)
        
        total_buy = 0
        total_sell = 0
        for item in self.complete_plan:
            code = str(item.get('证券代码', ''))
            name = str(item.get('证券名称', ''))
            sector = str(item.get('行业分类', ''))
            target_w = item.get('目标权重', 0)
            risk_w = item.get('风险权重', 0)
            direction = item.get('交易方向', '')
            shares = item.get('需调整股数', 0)
            amount = float(item.get('预计交易金额(元)', 0))
            batch = item.get('执行批次', '')
            
            if direction == '买入':
                total_buy += amount
            elif direction == '卖出':
                total_sell += amount
            
            risk_flag = "🔴" if risk_w >= 0.32 else ("🟡" if risk_w >= 0.26 else "🟢")
            lines.append(f"  {code:<8} {name:<10} {sector:<10} {float(target_w)*100:.0f}% {risk_flag} {float(risk_w):.2f} {direction:>6} {shares:>+8,} ¥{amount:>10,.0f} {batch:>8}")
        
        lines.append("-" * 80)
        lines.append(f"  {'合计':<40} 买入: ¥{total_buy:>12,.0f} | 卖出: ¥{total_sell:>12,.0f} | 净需求: ¥{total_buy-total_sell:>12,.0f}")
        
        # 分批执行计划
        lines.append(f"\n[分批执行计划] (batch_execution_plan.xlsx)")
        lines.append(f"  {'批次':<8} {'时间':<10} {'代码':<8} {'名称':<10} {'类型':>6} {'股数':>8} {'金额':>12}")
        lines.append("-" * 80)
        for item in self.batch_plan:
            batch = item.get('批次', '')
            timing = item.get('执行时间', '')
            code = str(item.get('证券代码', ''))
            name = str(item.get('证券名称', ''))
            op_type = item.get('操作类型', '')
            shares = item.get('需调整股数', 0)
            amount = float(item.get('预计交易金额(元)', 0))
            flow = item.get('资金流向', '')
            flow_icon = "📥" if flow == '流出' else "📤"
            lines.append(f"  {batch:<8} {timing:<10} {code:<8} {name:<10} {op_type:>6} {shares:>+8,} {flow_icon} ¥{amount:>10,.0f}")
        
        # 资金流向
        lines.append(f"\n[资金流向汇总] (fund_flow_summary.xlsx)")
        lines.append(f"  📤 卖出回笼: ¥{self.fund_flow.get('total_sell', 0):>12,.0f}")
        lines.append(f"  📥 买入支出: ¥{self.fund_flow.get('total_buy', 0):>12,.0f}")
        lines.append(f"  💰 资金净流动: ¥{self.fund_flow.get('net_flow', 0):>12,.0f} (需追加)")
        lines.append(f"  🔖 预估交易费用: ¥{self.fund_flow.get('fee_estimate', 0):>12,.0f}")
        lines.append(f"  📌 实际需追加: ¥{self.fund_flow.get('additional_capital', 0):>12,.0f}")
        
        # 策略建议
        lines.append(f"\n[执行策略建议] (execution_summary_and_tips.xlsx)")
        for item in self.summary_tips:
            priority = item.get('优先级', '')
            priority_icon = "🔴" if priority == '高' else ("🟡" if priority == '中' else "🟢")
            lines.append(f"  {priority_icon} {item.get('类别', '')} - {item.get('项目', '')}: {item.get('内容', '')}")
        
        # 高风险提示
        lines.append(f"\n⚠️ 重点监控标的 (风险权重 ≥ 0.32)")
        high_risk = [item for item in self.complete_plan if float(item.get('风险权重', 0)) >= 0.32]
        for item in high_risk:
            lines.append(f"  • {item.get('证券名称', '')}({item.get('证券代码', '')}) 风险权重: {item.get('风险权重', 0):.2f}")
        
        # 需特别注意
        special_items = [item for item in self.complete_plan if item.get('需特别注意', False)]
        if special_items:
            lines.append(f"\n📌 需特别注意标的")
            for item in special_items:
                lines.append(f"  • {item.get('证券名称', '')}({item.get('证券代码', '')}) - 建议密切跟踪估值变化")
        
        lines.append("\n" + "=" * 70)
        return "\n".join(lines)
    
    def sync_to_stop_loss_monitor(self):
        """同步止损止盈规则到监控系统"""
        rules = self.get_stop_loss_rules()
        print(f"\n🛡️ 同步止损止盈规则 - 共 {len(rules)} 只标的")
        
        # 保存配置文件
        config_path = os.path.join(BASE_DIR, 'config', 'rebalance_stop_loss.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        print(f"  ✅ 已保存到: {config_path}")
        return rules


# ============================================================
# 数据源连接器抽象 - Connector-first架构
# ============================================================

class DataConnector:
    """数据源连接器基类"""
    name = "base"
    priority = 0
    available = False

    def __init__(self):
        self._connected = False

    def connect(self) -> bool:
        """建立连接"""
        self._connected = True
        return True

    def disconnect(self):
        """断开连接"""
        self._connected = False

    def get_quote(self, code: str):
        """获取单个标的行情"""
        raise NotImplementedError

    def get_quotes_batch(self, codes: list) -> dict:
        """批量获取行情"""
        raise NotImplementedError

    def get_history(self, code: str, start_date: str, end_date: str):
        """获取历史数据"""
        raise NotImplementedError

    @property
    def connected(self) -> bool:
        return self._connected


class DataConnectorManager:
    """连接器管理器 - 支持优先级回退"""

    def __init__(self):
        self.connectors = []
        self._active_connector = None

    def register_connector(self, connector: DataConnector):
        """注册连接器"""
        self.connectors.append(connector)
        self.connectors.sort(key=lambda x: x.priority, reverse=True)

    def get_active_connector(self):
        """获取当前活跃连接器"""
        if self._active_connector and self._active_connector.connected:
            return self._active_connector

        for connector in self.connectors:
            if connector.available:
                try:
                    if connector.connect():
                        self._active_connector = connector
                        print(f"✅ 已激活数据源连接器: {connector.name}")
                        return connector
                except Exception as e:
                    print(f"⚠️ 连接器 {connector.name} 连接失败: {e}")

        return None

    def get_quote(self, code: str):
        """获取行情（自动降级）"""
        connector = self.get_active_connector()
        if connector:
            try:
                return connector.get_quote(code)
            except Exception as e:
                print(f"⚠️ 连接器 {connector.name} 获取行情失败: {e}")
                self._active_connector = None

        return None

    def get_quotes_batch(self, codes: list) -> dict:
        """批量获取行情"""
        connector = self.get_active_connector()
        if connector:
            try:
                return connector.get_quotes_batch(codes)
            except Exception as e:
                print(f"⚠️ 连接器 {connector.name} 批量获取失败: {e}")
                self._active_connector = None

        return {}

    def list_connectors(self) -> list:
        """列出所有连接器"""
        return [
            {
                'name': c.name,
                'priority': c.priority,
                'available': c.available,
                'connected': c.connected
            }
            for c in self.connectors
        ]


# ============================================================
# ETF国家队资金流向监控器
# ============================================================

class ETFFundFlowMonitor:
    """
    ETF国家队资金流向监控器
    用于追踪中央汇金等国家队ETF持仓变化，作为投资决策参考

    功能:
    1. 监控19只主流宽基ETF实时行情
    2. 计算资金流向趋势
    3. 检测国家队加仓/减仓信号
    4. 生成投资决策建议
    """

    # ETF配置列表
    ETF_LIST = [
        # 宽基指数ETF - 核心配置
        {"code": "510300", "name": "沪深300ETF华泰柏瑞", "market": "sh", "category": "宽基核心"},
        {"code": "510310", "name": "沪深300ETF易方达", "market": "sh", "category": "宽基核心"},
        {"code": "159919", "name": "沪深300ETF嘉实", "market": "sz", "category": "宽基核心"},
        {"code": "510500", "name": "中证500ETF南方", "market": "sh", "category": "宽基核心"},
        {"code": "510050", "name": "上证50ETF华夏", "market": "sh", "category": "蓝筹核心"},
        {"code": "159915", "name": "创业板ETF易方达", "market": "sz", "category": "成长科技"},
        {"code": "588000", "name": "科创50ETF华夏", "market": "sh", "category": "成长科技"},
        {"code": "588080", "name": "科创50ETF易方达", "market": "sh", "category": "成长科技"},
        # 中证1000/国证2000 - 小盘风格
        {"code": "560010", "name": "中证1000ETF富国", "market": "sh", "category": "小盘风格"},
        {"code": "512100", "name": "中证1000ETF南方", "market": "sh", "category": "小盘风格"},
        # 红利/低波 - 防御型
        {"code": "515080", "name": "中证红利ETF易方达", "market": "sh", "category": "防御红利"},
        {"code": "512890", "name": "红利低波100ETF华泰柏瑞", "market": "sh", "category": "防御红利"},
        # 行业主题ETF - 国家队关注
        {"code": "512880", "name": "证券ETF国泰", "market": "sh", "category": "金融主题"},
        {"code": "512800", "name": "银行ETF华宝", "market": "sh", "category": "金融主题"},
        {"code": "512170", "name": "医疗ETF华宝", "market": "sh", "category": "医药主题"},
        {"code": "512010", "name": "医药ETF易方达", "market": "sh", "category": "医药主题"},
        {"code": "512760", "name": "半导体ETF国泰", "market": "sh", "category": "科技主题"},
        {"code": "515030", "name": "新能源车ETF华夏", "market": "sh", "category": "新能源主题"},
        {"code": "518880", "name": "黄金ETF华安", "market": "sh", "category": "避险资产"},
    ]

    # 信号阈值（净流入）
    SIGNAL_THRESHOLD = {
        "high": 50_000_000_000,    # 50亿以上 - 高置信度
        "medium": 10_000_000_000,  # 10亿以上 - 中等置信度
        "low": 2_000_000_000,      # 2亿以上 - 关注级别
    }

    def __init__(self, data_connector_manager: DataConnectorManager = None):
        self.data_manager = data_connector_manager
        self.signals = []
        self.flow_data = {}
        self.last_update = None

    def get_etf_quotes(self) -> dict:
        """获取ETF实时行情"""
        quotes = {}
        if self.data_manager:
            codes = [etf["code"] for etf in self.ETF_LIST]
            quotes = self.data_manager.get_quotes_batch(codes)
        return quotes

    def analyze_fund_flow(self, days: int = 5) -> list:
        """
        分析ETF资金流向
        返回: 按净流入排序的ETF列表
        """
        results = []
        quotes = self.get_etf_quotes()

        for etf in self.ETF_LIST:
            code = etf["code"]
            quote = quotes.get(code, {})

            # 简化版资金流估算：使用成交额 * 涨跌方向
            if quote.get('price', 0) > 0:
                change_pct = quote.get('change_pct', 0)
                amount = quote.get('amount', 0) or quote.get('volume', 0) * quote.get('price', 0)

                # 估算净流入（简化版）
                net_flow = amount * (1 if change_pct >= 0 else -1)

                results.append({
                    "code": code,
                    "name": etf["name"],
                    "category": etf["category"],
                    "price": quote.get('price', 0),
                    "change_pct": change_pct,
                    "amount_yi": round(amount / 1e8, 2) if amount else 0,
                    "net_flow_yi": round(net_flow / 1e8, 2) if net_flow else 0,
                    "trend": "流入" if net_flow > 0 else "流出" if net_flow < 0 else "中性"
                })

        # 按净流入排序
        results.sort(key=lambda x: x["net_flow_yi"], reverse=True)
        self.flow_data = {r["code"]: r for r in results}
        return results

    def detect_signals(self) -> list:
        """
        检测国家队加仓/减仓信号
        返回: 信号列表
        """
        signals = []

        for code, data in self.flow_data.items():
            net_flow_yi = data["net_flow_yi"]
            trend = data["trend"]

            # 加仓信号
            if net_flow_yi >= 50:
                confidence = "高"
                signal_type = "强加仓信号"
            elif net_flow_yi >= 10:
                confidence = "中"
                signal_type = "加仓信号"
            elif net_flow_yi >= 2:
                confidence = "低"
                signal_type = "关注信号"
            # 减仓信号
            elif net_flow_yi <= -50:
                confidence = "高"
                signal_type = "强减仓信号"
            elif net_flow_yi <= -10:
                confidence = "中"
                signal_type = "减仓信号"
            elif net_flow_yi <= -2:
                confidence = "低"
                signal_type = "关注信号(流出)"
            else:
                continue

            signals.append({
                **data,
                "signal_type": signal_type,
                "confidence": confidence,
            })

        # 按置信度和净流入排序
        signals.sort(key=lambda x: (0 if x["confidence"] == "高" else 1 if x["confidence"] == "中" else 2,
                                    -x["net_flow_yi"]))
        self.signals = signals
        return signals

    def get_investment_suggestion(self) -> dict:
        """
        生成投资决策建议
        基于ETF资金流向信号，给出风格配置建议
        """
        self.analyze_fund_flow()
        signals = self.detect_signals()

        # 统计各风格资金流向
        style_flows = {}
        for data in self.flow_data.values():
            category = data["category"]
            if category not in style_flows:
                style_flows[category] = {"total_flow": 0, "count": 0, "positive": 0}
            style_flows[category]["total_flow"] += data["net_flow_yi"]
            style_flows[category]["count"] += 1
            if data["net_flow_yi"] > 0:
                style_flows[category]["positive"] += 1

        # 生成建议
        suggestions = {
            "overall_trend": "净流入" if sum(s["net_flow_yi"] for s in self.flow_data.values()) > 0 else "净流出",
            "high_confidence_signals": [s for s in signals if s["confidence"] == "高"],
            "style_rotation": {},
            "recommendations": []
        }

        # 风格轮动建议
        for style, data in sorted(style_flows.items(), key=lambda x: x[1]["total_flow"], reverse=True):
            avg_flow = data["total_flow"] / data["count"] if data["count"] > 0 else 0
            if avg_flow > 5:
                suggestions["style_rotation"][style] = "增持"
            elif avg_flow < -5:
                suggestions["style_rotation"][style] = "减持"
            else:
                suggestions["style_rotation"][style] = "持有"

        # 具体建议
        if suggestions["high_confidence_signals"]:
            top_signal = suggestions["high_confidence_signals"][0]
            if "加仓" in top_signal["signal_type"]:
                suggestions["recommendations"].append(
                    f"国家队资金大幅流入{top_signal['name']}，建议关注相关板块机会"
                )
            else:
                suggestions["recommendations"].append(
                    f"国家队资金大幅流出{top_signal['name']}，建议谨慎"
                )

        return suggestions

    def generate_report(self) -> str:
        """生成ETF资金流向报告"""
        self.analyze_fund_flow()
        signals = self.detect_signals()
        suggestions = self.get_investment_suggestion()

        report_lines = [
            "# ETF国家队资金流向监控报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**监测标的**: {len(self.ETF_LIST)} 只主流ETF",
            "",
            "---",
            "",
            "## 资金流向概览",
            "",
            f"- **整体趋势**: {suggestions['overall_trend']}",
            f"- **高置信度信号**: {len(suggestions['high_confidence_signals'])} 条",
            "",
            "## 信号详情",
            "",
        ]

        if signals:
            report_lines.extend([
                "| ETF名称 | 代码 | 净流入(亿) | 信号类型 | 置信度 |",
                "|---------|------|-----------|---------|--------|",
            ])
            for s in signals[:10]:
                report_lines.append(
                    f"| {s['name']} | {s['code']} | {s['net_flow_yi']} | {s['signal_type']} | {s['confidence']} |"
                )
        else:
            report_lines.append("> 未检测到明显信号")

        report_lines.extend([
            "",
            "## 风格轮动建议",
            "",
        ])

        for style, action in suggestions["style_rotation"].items():
            icon = "📈" if action == "增持" else "📉" if action == "减持" else "➡️"
            report_lines.append(f"- {icon} **{style}**: {action}")

        if suggestions["recommendations"]:
            report_lines.extend([
                "",
                "## 投资建议",
                "",
            ])
            for rec in suggestions["recommendations"]:
                report_lines.append(f"- {rec}")

        report_lines.extend([
            "",
            "---",
            "*本报告由ETF资金流向监控模块自动生成*",
        ])

        return "\n".join(report_lines)


# 全局连接器管理器实例
connector_manager = DataConnectorManager()


# ============================================================
# 模块导入 (优雅降级)
# ============================================================

class ModuleLoader:
    """模块加载器，支持优雅降级"""
    
    def __init__(self):
        self._modules = {}
    
    def load(self, module_name, import_dict):
        """尝试加载模块，失败时记录但不抛出异常"""
        try:
            module = __import__(module_name, fromlist=import_dict.keys())
            self._modules[module_name] = module
            result = {}
            for attr, alias in import_dict.items():
                result[alias] = getattr(module, attr, None)
            return result
        except ImportError as e:
            print(f"⚠️ 模块 {module_name} 加载失败: {e}")
            return {alias: None for alias in import_dict.values()}
        except Exception as e:
            print(f"⚠️ 模块 {module_name} 初始化失败: {e}")
            return {alias: None for alias in import_dict.values()}

# 加载核心模块
loader = ModuleLoader()

# 数据提供层
data_provider = loader.load('wind_data_provider', {
    'get_quotes_batch': 'get_quotes_batch',
    'get_quote': 'get_quote',
    'get_stats': 'get_wind_stats',
    'reset_stats': 'reset_stats'
})

# 自动交易系统
auto_trading = loader.load('auto_trading_system', {
    'AutoTradingSystem': 'AutoTradingSystem'
})

# 再平衡引擎（使用增强版）
rebalance_engine = loader.load('rebalancing_engine', {
    'RebalancingEngine': 'RebalancingEngine'
})

# 每日报告
daily_report = loader.load('daily_report', {
    'generate_daily_report': 'generate_daily_report'
})

# 止损止盈监控
stop_loss = loader.load('stop_loss_monitor', {
    'StopLossMonitor': 'StopLossMonitor',
    'generate_risk_alert_report': 'generate_risk_alert_report'
})

# ============================================================
# 配置管理
# ============================================================

def load_portfolio_config():
    """加载组合配置"""
    import yaml
    config_path = os.path.join(BASE_DIR, 'config', 'portfolio.yaml')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return None

# ============================================================
# 进度显示工具
# ============================================================

class ProgressIndicator:
    """实时进度指示器"""

    def __init__(self, task_name: str, total_steps: int = 100):
        self.task_name = task_name
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = None
        self._spinner_chars = ['|', '/', '-', '\\']
        self._spinner_index = 0

    def update(self, step: int, message: str = ""):
        """更新进度"""
        import time
        if self.start_time is None:
            self.start_time = time.time()

        self.current_step = min(step, self.total_steps)
        elapsed = time.time() - self.start_time
        progress = (self.current_step / self.total_steps) * 100

        # 显示进度条
        bar_length = 20
        filled = int(bar_length * (self.current_step / self.total_steps))
        bar = '█' * filled + '░' * (bar_length - filled)

        # 显示旋转指示器
        self._spinner_index = (self._spinner_index + 1) % 4
        spinner = self._spinner_chars[self._spinner_index]

        # 计算ETA
        eta = "计算中..."
        if self.current_step > 0:
            eta_seconds = (elapsed / self.current_step) * (self.total_steps - self.current_step)
            if eta_seconds < 60:
                eta = f"ETA: {int(eta_seconds)}s"
            else:
                eta = f"ETA: {int(eta_seconds / 60)}m"

        print(f"\r{spinner} {self.task_name}: [{bar}] {progress:.1f}% {eta} {message}", end='')
        sys.stdout.flush()

    def complete(self, message: str = "完成"):
        """标记完成"""
        import time
        elapsed = time.time() - self.start_time if self.start_time else 0
        print(f"\r✓ {self.task_name}: [{''.join(['█'] * 20)}] 100% 耗时: {elapsed:.2f}s {message}")
        sys.stdout.flush()


# ============================================================
# 运行模式实现
# ============================================================

def run_live_monitoring(args):
    """实时监控模式 - 盘中实时行情监控 + 自动再平衡"""
    print("🚀 启动实时监控模式")
    print("=" * 70)
    
    AutoTradingSystem = auto_trading.get('AutoTradingSystem')
    if AutoTradingSystem:
        system = AutoTradingSystem()
        system.run()
    else:
        print("❌ 自动交易系统模块不可用")
        
def run_report_generation(args):
    """报告生成模式 - 生成每日持仓报告"""
    print("📝 生成每日报告")
    print("=" * 70)
    
    generate_daily_report = daily_report.get('generate_daily_report')
    if generate_daily_report:
        try:
            portfolio_file = os.path.join(BASE_DIR, 'config', 'portfolio.yaml')
            report_content = generate_daily_report(
                portfolio_file=portfolio_file,
                enable_ai_analysis=not args.no_ai
            )
            
            # 保存到归档目录
            archive_dir = os.path.join(BASE_DIR, '..', '每日报告归档', datetime.now().strftime('%Y-%m-%d'))
            os.makedirs(archive_dir, exist_ok=True)
            archive_path = os.path.join(archive_dir, f'综合日报_{datetime.now().strftime("%Y%m%d")}.txt')
            with open(archive_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"\n✅ 报告已归档到: {archive_path}")
            
        except Exception as e:
            print(f"❌ 报告生成失败: {e}")
    else:
        print("❌ 每日报告模块不可用")

def run_rebalance(args):
    """再平衡模式 - 执行Excel驱动的再平衡计划"""
    print("🔄 执行再平衡")
    print("=" * 70)
    
    RebalancingEngine = rebalance_engine.get('RebalancingEngine')
    if RebalancingEngine:
        engine = RebalancingEngine()
        engine.load_all()
        
        if engine.is_loaded:
            # 获取实时行情
            get_quotes_batch = data_provider.get('get_quotes_batch')
            if get_quotes_batch:
                config = load_portfolio_config()
                if config:
                    stocks = [a['code'] for a in config.get('assets', []) if not a['code'].startswith('5')]
                    funds = [a['code'] for a in config.get('assets', []) if a['code'].startswith('5')]
                    prices = get_quotes_batch(stocks, funds)
                    engine.build_trade_orders(current_prices={k: v['price'] for k, v in prices.items() if v['price'] > 0})
            
            # 生成报告
            report = engine.generate_report()
            print(report)
            
            # 同步止损止盈规则
            if args.sync_sl:
                engine.sync_to_stop_loss_monitor()
                print("\n✅ 止损止盈规则已同步")
            
            # 保存报告
            if args.output:
                report_dir = os.path.join(BASE_DIR, 'reports')
                os.makedirs(report_dir, exist_ok=True)
                report_path = os.path.join(report_dir, args.output)
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"\n✅ 报告已保存: {report_path}")
        else:
            print("❌ 无法加载再平衡数据")
    else:
        print("❌ 再平衡引擎模块不可用")

def run_backtest(args):
    """回测模式 - 历史数据回测验证"""
    print("📊 运行回测")
    print("=" * 70)
    
    # 尝试导入并运行回测
    try:
        from fast_backtest import run_fast_backtest
        result = run_fast_backtest()
        print(result)
    except ImportError:
        try:
            from backtest_engine import BacktestEngine
            from portfolio_config import PortfolioConfig
            
            config = load_portfolio_config()
            if config:
                portfolio = PortfolioConfig()
                settings = {
                    'capital': {'total': 1000000},
                    'rebalance': {'threshold': 0.06, 'min_interval_days': 5},
                    'targets': {'annual_return': 0.08, 'max_drawdown': 0.15}
                }
                engine = BacktestEngine(portfolio, settings)
                
                # 查找历史数据文件
                excel_files = [f for f in os.listdir(BASE_DIR) if f.startswith('data_extraction') and f.endswith('.xlsx')]
                if excel_files:
                    result = engine.run_backtest(os.path.join(BASE_DIR, excel_files[0]))
                    print("\n✅ 回测完成")
                else:
                    print("❌ 未找到历史数据文件")
        except Exception as e:
            print(f"❌ 回测模块不可用: {e}")

def run_risk_monitor(args):
    """风险监控模式 - 检查止损止盈状态"""
    print("🛡️ 运行风险监控")
    print("=" * 70)
    
    StopLossMonitor = stop_loss.get('StopLossMonitor')
    generate_risk_alert_report = stop_loss.get('generate_risk_alert_report')
    
    if StopLossMonitor and generate_risk_alert_report:
        monitor = StopLossMonitor()
        
        # 获取实时行情
        quotes = {}
        get_quotes_batch = data_provider.get('get_quotes_batch')
        if get_quotes_batch:
            config = load_portfolio_config()
            if config:
                codes = [a['code'] for a in config.get('assets', [])]
                stocks = [c for c in codes if not c.startswith('5')]
                funds = [c for c in codes if c.startswith('5')]
                prices = get_quotes_batch(stocks, funds)
                quotes = {k: {'price': v['price']} for k, v in prices.items() if v['price'] > 0}
        
        # 如果没有实时行情，使用模拟数据
        if not quotes:
            print("⚠️ 使用模拟数据进行风险监控")
            quotes = {
                '600989': {'price': 23.50},
                '600276': {'price': 45.00},
                '300274': {'price': 165.00},
                '601088': {'price': 47.80},
                '002371': {'price': 520.00},
            }
        
        alerts = monitor.check_all(quotes)
        report = generate_risk_alert_report(alerts)
        print(report)
    else:
        print("❌ 止损止盈监控模块不可用")

def run_etf_flow_monitor(args):
    """ETF资金流向监控模式 - 追踪国家队资金动向"""
    print("\n📊 ETF国家队资金流向监控")
    print("=" * 70)

    progress = ProgressIndicator("ETF资金流向分析", 4)

    progress.update(1, "初始化监控器...")
    monitor = ETFFundFlowMonitor(data_connector_manager=connector_manager)

    progress.update(2, "获取ETF行情数据...")
    flow_data = monitor.analyze_fund_flow()

    progress.update(3, "检测国家队信号...")
    signals = monitor.detect_signals()

    progress.update(4, "生成投资建议...")
    suggestions = monitor.get_investment_suggestion()

    # 生成报告
    report = monitor.generate_report()
    print("\n" + report)

    # 保存报告
    if args.output:
        report_dir = os.path.join(BASE_DIR, 'reports')
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, args.output)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n✅ 报告已保存: {report_path}")

    # 归档到每日报告目录
    archive_dir = os.path.join(BASE_DIR, '..', '每日报告归档', datetime.now().strftime('%Y-%m-%d'))
    os.makedirs(archive_dir, exist_ok=True)
    archive_path = os.path.join(archive_dir, f'ETF资金流向_{datetime.now().strftime("%Y%m%d")}.md')
    with open(archive_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"✅ 报告已归档: {archive_path}")

    progress.complete(f"检测到 {len(signals)} 条信号")

    return monitor

def run_quick_check(args):
    """快速检查模式 - 检查系统状态"""
    print("🔍 系统状态快速检查")
    print("=" * 70)

    # 检查模块可用性
    modules = {
        '数据提供层': data_provider.get('get_quotes_batch') is not None,
        '自动交易系统': auto_trading.get('AutoTradingSystem') is not None,
        '再平衡引擎': rebalance_engine.get('RebalancingEngine') is not None,
        '每日报告': daily_report.get('generate_daily_report') is not None,
        '止损止盈监控': stop_loss.get('StopLossMonitor') is not None,
        'ETF资金流向监控': True,  # 内置模块，始终可用
    }

    print("\n📦 模块状态:")
    for name, available in modules.items():
        status = "✅" if available else "❌"
        print(f"  {status} {name}")

    # ETF资金流向监控详情
    print("\n📊 ETF资金流向监控:")
    print(f"  ✅ 监控标的: {len(ETFFundFlowMonitor.ETF_LIST)} 只ETF")
    print(f"  ✅ 信号阈值: 高50亿/中10亿/低2亿")

    # 检查配置文件
    print("\n📋 配置文件:")
    config_files = [
        'config/portfolio.yaml',
        'config/settings.yaml',
        'config/positions.json',
    ]
    for config_file in config_files:
        path = os.path.join(BASE_DIR, config_file)
        exists = os.path.exists(path)
        status = "✅" if exists else "❌"
        print(f"  {status} {config_file}")
    
    # 检查数据缓存
    print("\n💾 数据缓存:")
    cache_dir = os.path.join(BASE_DIR, 'data', 'cache')
    if os.path.exists(cache_dir):
        cache_files = [f for f in os.listdir(cache_dir) if f.endswith('.parquet')]
        print(f"  ✅ 缓存目录存在，{len(cache_files)}个文件")
    else:
        print("  ❌ 缓存目录不存在")
    
    # 检查报告目录
    print("\n📄 报告目录:")
    reports_dir = os.path.join(BASE_DIR, 'reports')
    if os.path.exists(reports_dir):
        report_days = len(os.listdir(reports_dir))
        print(f"  ✅ 报告目录存在，{report_days}天报告")
    else:
        print("  ❌ 报告目录不存在")
    
    print("\n" + "=" * 70)

# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='量化策略系统 v4.2 - 整合版',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
运行模式:
  --live        实时监控模式 - 盘中实时行情监控 + 自动再平衡
  --report      报告生成模式 - 生成每日持仓报告
  --rebalance   再平衡模式 - 执行Excel驱动的再平衡计划
  --backtest    回测模式 - 历史数据回测验证
  --risk        风险监控模式 - 检查止损止盈状态
  --etf-flow    ETF资金流向监控 - 追踪国家队资金动向
  --check       快速检查模式 - 检查系统状态

示例:
  python quant_strategy_main.py --live       # 启动实时监控
  python quant_strategy_main.py --report     # 生成报告
  python quant_strategy_main.py --rebalance  # 执行再平衡
  python quant_strategy_main.py --risk       # 风险监控
  python quant_strategy_main.py --etf-flow   # ETF资金流向监控
  python quant_strategy_main.py --check      # 系统检查
        """
    )

    # 运行模式
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--live', action='store_true', help='实时监控模式')
    mode_group.add_argument('--report', action='store_true', help='报告生成模式')
    mode_group.add_argument('--rebalance', action='store_true', help='再平衡模式')
    mode_group.add_argument('--backtest', action='store_true', help='回测模式')
    mode_group.add_argument('--risk', action='store_true', help='风险监控模式')
    mode_group.add_argument('--etf-flow', action='store_true', help='ETF资金流向监控模式')
    mode_group.add_argument('--check', action='store_true', help='快速检查模式')

    # 通用选项
    parser.add_argument('--no-ai', action='store_true', help='禁用AI分析模块')
    parser.add_argument('--output', '-o', default=None, help='输出报告文件名')
    parser.add_argument('--sync-sl', action='store_true', help='同步止损止盈规则')

    args = parser.parse_args()

    # 根据模式执行
    if args.live:
        run_live_monitoring(args)
    elif args.report:
        run_report_generation(args)
    elif args.rebalance:
        run_rebalance(args)
    elif args.backtest:
        run_backtest(args)
    elif args.risk:
        run_risk_monitor(args)
    elif args.etf_flow:
        run_etf_flow_monitor(args)
    elif args.check:
        run_quick_check(args)

if __name__ == '__main__':
    main()