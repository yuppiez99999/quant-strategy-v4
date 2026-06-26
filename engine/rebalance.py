# -*- coding: utf-8 -*-
"""Excel驱动再平衡引擎 (V4.3) — 5表联动，配置即策略"""

import os
import pandas as pd
from datetime import datetime
from bootstrap import logger, BASE_DIR


class ExcelDrivenRebalancingEngineV4:
    """增强版Excel驱动再平衡引擎 (V4.3专用)
    
    数据源:
    - complete_rebalancing_plan.xlsx: 12只标的完整计划
    - batch_execution_plan.xlsx: 分批执行计划
    - execution_summary_and_tips.xlsx: 执行策略建议
    - fund_flow_summary.xlsx: 资金流向汇总
    - portfolio_comparison_analysis.xlsx: 组合对比分析
    
    V4.3特性:
    - 集成策略注册表，支持策略标签化
    - 支持研究假设生命周期管理
    - 提供Connector-first数据源抽象
    """
    
    EXCEL_FILES = {
        'complete_plan': 'data_extraction_complete_rebalancing_plan.xlsx',
        'batch_plan': 'data_extraction_batch_execution_plan.xlsx',
        'summary': 'data_extraction_execution_summary_and_tips.xlsx',
        'fund_flow': 'data_extraction_fund_flow_summary.xlsx',
        'comparison': 'data_extraction_portfolio_comparison_analysis.xlsx',
    }
    
    def __init__(self, strategy_registry: 'StrategyRegistry' = None):
        self.is_loaded = False
        self.strategy_registry = strategy_registry
        self.complete_plan = []
        self.batch_plan = []
        self.summary_tips = []
        self.fund_flow = {}
        self.comparison_data = []
        self.pd = None
        self._try_import_pandas()
    
    def _try_import_pandas(self):
        """尝试加载pandas"""
        try:
            import pandas as pd
            self.pd = pd
            return True
        except ImportError:
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
        logger.info("正在加载Excel配置文件...")
        loaded_count = 0
        
        for key, filename in self.EXCEL_FILES.items():
            try:
                filepath = os.path.join(BASE_DIR, filename)
                if os.path.exists(filepath):
                    df = self.pd.read_excel(filepath)
                    # 打印列名用于调试
                    logger.info(f"  {filename} 列名: {list(df.columns)}")
                    
                    if key == 'complete_plan':
                        self.complete_plan = self._normalize_complete_plan(df)
                        logger.info(f"加载完整再平衡计划: {len(self.complete_plan)} 只标的")
                    elif key == 'batch_plan':
                        self.batch_plan = self._normalize_batch_plan(df)
                        logger.info(f"加载分批执行计划: {len(self.batch_plan)} 条")
                    elif key == 'summary':
                        self.summary_tips = df.to_dict('records')
                        logger.info(f"加载执行总结: {len(self.summary_tips)} 条")
                    elif key == 'fund_flow':
                        self.fund_flow = {'details': df.to_dict('records')}
                        logger.info(f"加载资金流向")
                    elif key == 'comparison':
                        self.comparison_data = df.to_dict('records')
                        logger.info(f"加载组合对比分析: {len(self.comparison_data)} 项")
                    loaded_count += 1
            except Exception as e:
                logger.warning(f"加载 {filename} 失败: {e}")
        
        self.is_loaded = (loaded_count >= 1)
        return self.is_loaded
    
    def _normalize_complete_plan(self, df):
        """标准化完整再平衡计划数据，自动添加别名映射"""
        records = []
        # Excel列名 -> 代码内部键名 映射表
        ALIAS_MAP = {
            '主要风格': '行业分类',
            '目标金额(元)': '预计交易金额',
            '持股数(约)': '需调整股数',
            '价格(元)': '最新价',
            '实际市值(元)': '当前市值',
            '实际权重': '风险权重',
            '说明': '操作类型',
        }
        cols = list(df.columns)
        code_col = cols.index('证券代码') if '证券代码' in cols else 0
        col_index = {c: i for i, c in enumerate(cols)}
        for row in df.itertuples(index=False):
            code_val = row[code_col]
            try:
                if self.pd.isna(code_val):
                    continue
            except Exception:
                if code_val is None or code_val == '':
                    continue
            code_str = str(code_val).strip()
            if not code_str or code_str in ('合计', '剩余现金', 'nan', 'NaN') or len(code_str) < 4:
                continue
            record = {}
            for c in cols:
                val = row[col_index[c]]
                try:
                    if self.pd.isna(val):
                        val = ''
                except Exception:
                    pass
                if isinstance(val, str) and '%' in val:
                    try:
                        val = float(val.replace('%', '')) / 100
                    except Exception:
                        pass
                record[str(c)] = val
            # 添加别名映射：让旧代码的键名也能找到值
            for excel_col, alias in ALIAS_MAP.items():
                if excel_col in record and alias not in record:
                    record[alias] = record[excel_col]
            # 补充默认字段（Excel中没有的）
            if '交易方向' not in record:
                record['交易方向'] = '买入'
            if '需调整股数' not in record:
                record['需调整股数'] = record.get('持股数(约)', 0)
            if '执行批次' not in record:
                record['执行批次'] = '第一批'
            if '风险权重' not in record:
                # 从实际权重或默认值
                record['风险权重'] = record.get('实际权重', 0.27)
            if '目标市值' not in record:
                record['目标市值'] = record.get('目标金额(元)', 0)
            if '当前市值' not in record:
                record['当前市值'] = record.get('实际市值(元)', 0)
            if '最新价' not in record:
                record['最新价'] = record.get('价格(元)', 0)
            if '止损位' not in record:
                record['止损位'] = 0
            if '止盈位' not in record:
                record['止盈位'] = 0
            if '当前股数' not in record:
                record['当前股数'] = 0
            if '目标股数' not in record:
                record['目标股数'] = record.get('持股数(约)', 0)
            if '调整幅度' not in record:
                record['调整幅度'] = 0
            if '当前仓位' not in record:
                record['当前仓位'] = 0
            records.append(record)
        return records
    
    def _normalize_batch_plan(self, df):
        """标准化分批执行计划数据，自动添加别名映射"""
        records = []
        # Excel列名 -> 代码内部键名 映射表
        ALIAS_MAP = {
            '目标持股数(约)': '股数',
            '证券代码': '代码',
            '证券名称': '名称',
            '目标金额(元)': '金额',
            '操作类型': '操作',
            '主要风格': '行业分类',
        }
        cols = list(df.columns)
        code_col = cols.index('证券代码') if '证券代码' in cols else 0
        col_index = {c: i for i, c in enumerate(cols)}
        for row in df.itertuples(index=False):
            # 跳过证券代码为空的行
            code_val = row[code_col]
            try:
                if self.pd.isna(code_val):
                    continue
            except:
                if code_val is None or code_val == '':
                    continue
            record = {}
            for c in cols:
                val = row[col_index[c]]
                try:
                    if self.pd.isna(val):
                        val = ''
                except:
                    pass
                record[str(c)] = val
            # 添加别名映射
            for excel_col, alias in ALIAS_MAP.items():
                if excel_col in record and alias not in record:
                    record[alias] = record[excel_col]
            records.append(record)
        return records
    
    def _load_fallback_config(self):
        """备选配置 — 从 portfolio.yaml 加载，硬编码已移除"""
        logger.warning("pandas不可用，尝试从portfolio.yaml加载配置")
        try:
            import yaml
            yaml_path = os.path.join(BASE_DIR, 'config', 'portfolio.yaml')
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            assets = config.get('assets', [])
            self.complete_plan = [
                {
                    '证券代码': a['code'], '证券名称': a['name'],
                    '目标权重': a.get('target_weight', 0.1),
                    '风险权重': 0.25, '当前仓位': 0, '调整幅度': 0,
                    '当前股数': 0, '最新价': 0, '当前市值': 0,
                    '目标市值': 0, '目标股数': 0, '需调整股数': 0,
                    '交易方向': '待定', '预计交易金额': 0, '操作类型': '待定',
                    '执行批次': '待定', '止损位': 0, '止盈位': 0,
                }
                for a in assets
            ]
            self.batch_plan = []
            self.summary_tips = [{'类别': '提示', '项目': '缺数据', '内容': '请安装pandas或提供Excel文件', '优先级': '高'}]
            self.fund_flow = {'total_sell': 0, 'total_buy': 0, 'net_flow': 0, 'fee': 0, 'additional': 0}
            self.comparison_data = []
            self.is_loaded = True
            logger.info(f"从portfolio.yaml加载了 {len(assets)} 只标的配置")
            return True
        except Exception as e:
            logger.error(f"加载portfolio.yaml失败: {e}")
            self.is_loaded = False
            return False

    def build_trade_orders(self, current_prices=None):
        """构建交易指令 — ⭐ 优先卖出 → 再买入"""
        if not self.is_loaded:
            return []
        
        buy_amount = sum(self._safe_float(self._get_val(item, '预计交易金额(元)', '预计交易金额', '目标金额(元)', '金额')) for item in self.complete_plan if self._get_val(item, '交易方向', '方向', '操作类型') == '买入')
        sell_amount = sum(self._safe_float(self._get_val(item, '预计交易金额(元)', '预计交易金额', '目标金额(元)', '金额')) for item in self.complete_plan if self._get_val(item, '交易方向', '方向', '操作类型') == '卖出')
        
        print(f"\n  📊 交易汇总 (策略: 先卖出回笼 → 再买入建仓):")
        print(f"    📤 卖出总金额: ￥{sell_amount:,.2f}")
        print(f"    📥 买入总金额: ￥{buy_amount:,.2f}")
        print(f"    💰 资金净需求: ￥{buy_amount - sell_amount:,.2f}")
        if buy_amount > sell_amount:
            print(f"    ⚠️  卖出回笼资金不足，需追加: ￥{buy_amount - sell_amount:,.2f}")
        else:
            print(f"    ✅ 卖出回笼资金充足，盈余: ￥{sell_amount - buy_amount:,.2f}")
        
        return self.complete_plan
    
    def get_batch_orders(self, batch_name='第二批'):
        """获取指定批次的交易计划"""
        return [item for item in self.batch_plan if item.get('批次') == batch_name]
    
    def get_stop_loss_rules(self):
        """提取止损止盈规则"""
        rules = []
        for item in self.complete_plan:
            code = str(item.get('证券代码', ''))
            name = item.get('证券名称', '')
            stop_loss = item.get('止损位', 0)
            take_profit = item.get('止盈位', 0)
            risk_w = item.get('风险权重', 0.27)
            
            current = item.get('最新价', 0)
            sl_pct = (stop_loss - current) / current if current > 0 else -0.15
            tp_pct = (take_profit - current) / current if current > 0 else 0.40
            
            rules.append({
                'code': code, 'name': name,
                'stop_loss_price': stop_loss, 'take_profit_price': take_profit,
                'stop_loss_pct': sl_pct, 'take_profit_pct': tp_pct,
                'risk_weight': risk_w
            })
        return rules
    
    def _safe_float(self, value, default=0.0):
        """安全转换为浮点数"""
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            value = value.strip()
            # 去掉百分号并转换
            if value.endswith('%'):
                try:
                    return float(value[:-1]) / 100
                except ValueError:
                    return default
            try:
                return float(value)
            except ValueError:
                return default
        return default
    
    def _safe_int(self, value, default=0):
        """安全转换为整数"""
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            value = value.strip().replace(',', '')
            try:
                return int(float(value))
            except ValueError:
                return default
        return default
    
    def _get_val(self, item, *keys):
        """尝试获取值，尝试多个可能的键名"""
        for key in keys:
            if key in item:
                return item[key]
        return None
    
    def generate_report(self, current_prices=None):
        """生成完整的再平衡执行报告"""
        if not self.is_loaded:
            return "❌ 再平衡数据未加载"
        
        lines = []
        lines.append("=" * 70)
        lines.append(" 🔄 Excel驱动再平衡执行报告 (V4.3)")
        lines.append(f" 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        
        # 战略方向
        lines.append("\n🎯 战略方向")
        for item in self.summary_tips[:3]:
            lines.append(f"  ▸ {item.get('项目', '')}: {item.get('内容', '')}")
        
        # 完整计划
        lines.append("\n[完整再平衡计划]")
        lines.append(f"  {'代码':<8} {'名称':<10} {'行业':<10} {'目标权重':>8} {'风险':>6} {'方向':>6} {'股数':>8} {'金额':>12}")
        lines.append("-" * 70)
        
        # ⭐ 优先卖出再买入排序
        sorted_plan = sorted(self.complete_plan,
            key=lambda x: (0 if str(self._get_val(x, '交易方向', '方向', '操作类型') or '') == '卖出' else 1)
        )
        
        total_buy = total_sell = 0
        for item in sorted_plan:
            code = str(self._get_val(item, '证券代码', '代码') or '')
            name = str(self._get_val(item, '证券 名称', '证券名称', '名称') or '')
            sector = str(self._get_val(item, '行业分类', '主要风格', '行业') or '')
            target_w = self._safe_float(self._get_val(item, '目标权重', '目标权重(%)'))
            risk_w = self._safe_float(self._get_val(item, '风险权重', '风险权重(%)', '实际权重'))
            direction = str(self._get_val(item, '交易方向', '方向', '操作类型') or '')
            shares = self._safe_int(self._get_val(item, '需调整股数', '持股数(约)', '目标持股数(约)', '股数'))
            amount = self._safe_float(self._get_val(item, '预计交易金额(元)', '预计交易金额', '目标金额(元)', '金额'))
            
            if direction == '买入': total_buy += amount
            elif direction == '卖出': total_sell += amount
            
            risk_flag = "🔴" if risk_w >= 0.32 else ("🟡" if risk_w >= 0.26 else "🟢")
            lines.append(f"  {code:<8} {name:<10} {sector:<10} {target_w*100:.0f}% {risk_flag} {risk_w:.2f} {direction:>6} {shares:>+8,} ￥{amount:>10,.0f}")
        
        lines.append("-" * 70)
        lines.append(f"  {'合计':<40} 买入: ￥{total_buy:>10,.0f} | 卖出: ￥{total_sell:>10,.0f}")
        
        # 分批执行
        lines.append("\n[分批执行计划]")
        # ⭐ 优先卖出再买入排序
        sorted_batch = sorted(self.batch_plan,
            key=lambda x: (0 if str(self._get_val(x, '操作类型', '操作', '类型') or '') in ('清仓', '减持') else 1)
        )
        for item in sorted_batch:
            batch = self._get_val(item, '批次', '执行批次') or ''
            timing = self._get_val(item, '执行时间', '时间') or ''
            name = self._get_val(item, '证券名称', '名称') or ''
            op = self._get_val(item, '操作类型', '操作', '类型') or ''
            shares = self._safe_int(self._get_val(item, '需调整股数', '目标持股数(约)', '股数'))
            lines.append(f"  {batch} | {timing} | {name} | {op} {abs(shares):,}股")
        
        # 资金流向
        ff = self.fund_flow
        fund_total_buy = fund_total_sell = fund_additional = 0
        if isinstance(ff, dict) and 'details' in ff:
            # 从details计算 — 遍历所有行查找关键字段
            for d in ff.get('details', []):
                item_name = str(self._get_val(d, '项目', 'item') or '')
                amount = self._safe_float(self._get_val(d, '金额(元)', '金额', 'amount') or 0)
                if '总计' in item_name and '交易' not in item_name:
                    fund_total_buy = amount
                elif '实际需追加资金' in item_name or '需追加' in item_name:
                    fund_additional = amount
                elif '剩余现金' in item_name:
                    fund_total_sell = amount  # 剩余现金视为可回笼
            # 回退：从complete_plan汇总
            if fund_total_buy == 0:
                fund_total_buy = sum(self._safe_float(self._get_val(item, '预计交易金额(元)', '预计交易金额', '目标金额(元)', '金额')) for item in self.complete_plan)
            if fund_additional == 0:
                fund_additional = self._safe_float(self._get_val(ff, 'additional_capital', 'additional', '实际需追加资金', '需追加') or 0)
        
        # 回退：fund_flow不是dict时，直接从complete_plan汇总
        if fund_total_buy == 0:
            fund_total_buy = sum(self._safe_float(self._get_val(item, '预计交易金额(元)', '预计交易金额', '目标金额(元)', '金额')) for item in self.complete_plan)
        if fund_additional == 0:
            fund_additional = fund_total_buy * 1.0003  # 默认加万三费率
        
        lines.append("\n[资金流向汇总]")
        lines.append(f"  📤 卖出回笼: ￥{fund_total_sell:>12,.0f}")
        lines.append(f"  📥 买入支出: ￥{fund_total_buy:>12,.0f}")
        lines.append(f"  💰 需追加资金: ￥{fund_additional:>12,.0f}")
        
        # 高风险提示
        high_risk = [item for item in self.complete_plan if self._safe_float(self._get_val(item, '风险权重', '风险权重(%)', '实际权重')) >= 0.32]
        if high_risk:
            lines.append("\n⚠️ 重点监控标的 (风险权重 ≥ 0.32)")
            for item in high_risk:
                name = self._get_val(item, '证券 名称', '证券名称', '名称') or ''
                code = self._get_val(item, '证券代码', '代码') or ''
                lines.append(f"  • {name}({code})")
        
        lines.append("\n" + "=" * 70)
        return "\n".join(lines)
    
    def sync_to_stop_loss_monitor(self):
        """同步止损止盈规则"""
        import json
        rules = self.get_stop_loss_rules()
        config_path = os.path.join(BASE_DIR, 'config', 'rebalance_stop_loss_v43.json')
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        logger.info(f"止损止盈规则已同步: {len(rules)} 只标的")
        return rules
