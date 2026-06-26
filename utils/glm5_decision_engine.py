# -*- coding: utf-8 -*-
"""
GLM-5 自动决策引擎 - 量化交易系统 AI 决策模块
自动分析市场数据并生成交易决策建议

使用方式:
    from utils.glm5_decision_engine import GLM5DecisionEngine
    
    engine = GLM5DecisionEngine()
    decisions = engine.make_decisions(market_data, portfolio_data)
    print(decisions['trading_signals'])
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.glm5_client import GLM5Client

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """交易信号"""
    action: str  # "BUY" / "SELL" / "HOLD" / "REDUCE"
    code: str
    name: str
    current_weight: float  # 当前仓位占比
    target_weight: float  # 目标仓位占比
    weight_change: float  # 仓位变化
    quantity: int  # 建议数量（股/手）
    price: float  # 参考价格
    confidence: float  # 置信度 (0-1)
    reason: str  # 决策理由
    urgency: str  # "LOW" / "MEDIUM" / "HIGH" / "URGENT"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class RiskAlert:
    """风险预警"""
    alert_type: str  # "STOP_LOSS" / "TAKE_PROFIT" / "OVERWEIGHT" / "UNDERWEIGHT"
    severity: str  # "LOW" / "MEDIUM" / "HIGH" / "CRITICAL"
    code: str
    message: str
    action_required: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DecisionResult:
    """决策结果"""
    timestamp: str
    market_summary: str  # 市场概况
    trading_signals: List[TradingSignal] = field(default_factory=list)
    risk_alerts: List[RiskAlert] = field(default_factory=list)
    portfolio_advice: str = ""  # 组合调整建议
    macro_outlook: str = ""  # 宏观展望
    ai_confidence: float = 0.0  # AI 整体置信度
    raw_analysis: str = ""  # 原始分析文本


class GLM5DecisionEngine:
    """
    GLM-5 自动决策引擎
    
    功能:
    1. 自动分析市场数据（指数、板块、资金流）
    2. 评估持仓风险（止损/止盈/仓位偏离）
    3. 生成交易信号（买卖建议）
    4. 风险预警（异常波动/极端行情）
    5. 组合再平衡建议
    """
    
    def __init__(self, config: Optional[Dict] = None, **kwargs):
        """
        初始化决策引擎
        
        Args:
            config: 配置字典
            **kwargs: 传递给 GLM5Client 的参数
        """
        # 默认配置（豆包Speed，最快响应）
        self.config = config or {
            "mode": "api",
            "api_model": "doubao-speed-32k",  # 豆包Speed，最快响应
            "temperature": 0.3,  # 低温度，更确定性
            "max_tokens": 3000,  # 长输出，详细分析
            "enable_risk_check": True,
            "enable_signal_generation": True,
            "enable_rebalance": True,
        }
        
        # 合并用户配置
        if kwargs:
            self.config.update(kwargs)
        
        # 初始化 GLM-5 客户端
        try:
            self.client = GLM5Client(
                mode=self.config.get("mode", "api"),
                api_model=self.config.get("api_model", "doubao-speed-32k"),
                temperature=self.config.get("temperature", 0.3),
                max_new_tokens=self.config.get("max_tokens", 3000),
            )
            logger.info("✓ GLM-5 决策引擎初始化成功")
        except Exception as e:
            logger.error(f"GLM-5 决策引擎初始化失败: {e}")
            raise
        
        # 系统提示词（金融决策优化）
        self.system_prompt = """你是一位资深的量化交易决策官，拥有20年以上的A股交易经验。
你的职责是根据市场数据和持仓信息，做出客观、理性的交易决策。

决策原则:
1. 严格遵循风控优先原则，任何交易建议必须包含风险控制
2. 基于数据说话，不凭感觉，不追涨杀跌
3. 仓位管理要科学，单只标的不超过10%，单一行业不超过30%
4. 止损纪律严格执行，亏损达到8%必须减仓，达到12%必须清仓
5. 止盈策略灵活，盈利超过15%可考虑分批止盈

输出格式要求:
- 使用清晰的 Markdown 格式
- 每个交易信号必须包含：代码、名称、动作、仓位变化、理由、置信度
- 风险预警必须标注严重程度（LOW/MEDIUM/HIGH/CRITICAL）
- 给出明确的数字建议（目标仓位、止损价位、止盈价位）

语气要求:
- 专业、冷静、客观
- 避免模糊表述（如"可能"、"也许"），给出明确判断
- 数据支撑结论，引用具体数值"""

    def make_decisions(
        self,
        market_data: Dict[str, Any],
        portfolio_data: Dict[str, Any],
        risk_rules: Optional[Dict[str, Any]] = None,
        macro_indicators: Optional[Dict[str, Any]] = None
    ) -> DecisionResult:
        """
        生成综合交易决策
        
        Args:
            market_data: 市场数据
                {
                    "日期": "2026-06-23",
                    "指数行情": {"上证指数": {"收盘": 3050, "涨跌幅": "+0.85%"}},
                    "板块表现": {"科技": "+2.1%", "消费": "-0.5%"},
                    "资金流向": {"北向资金": "净流入 +85亿"},
                    "技术指标": ["MACD金叉", "RSI超买"],
                }
            portfolio_data: 持仓数据
                {
                    "账户总值": 1052340,
                    "当日盈亏": "+12850",
                    "持仓": [
                        {"代码": "300308", "名称": "中际旭创", "仓位": "5.2%", "成本价": 128.5, "现价": 145.3, "盈亏": "+13.1%"},
                    ],
                    "目标仓位": {"中际旭创": "5%", "中国神华": "4%"},
                }
            risk_rules: 风控规则（可选）
                {
                    "max_single_position": 0.10,  # 单只标的最大仓位
                    "stop_loss_pct": -0.08,  # 止损线
                    "take_profit_pct": 0.15,  # 止盈线
                }
            macro_indicators: 宏观指标（可选）
                {
                    "PMI": 50.5,
                    "CPI": 2.1,
                    "M2增速": "10.2%",
                    "社融增量": "3.2万亿",
                }
        
        Returns:
            DecisionResult 对象，包含所有交易信号和风险预警
        """
        logger.info("开始生成交易决策...")
        
        # 构建决策提示词
        prompt = self._build_decision_prompt(
            market_data=market_data,
            portfolio_data=portfolio_data,
            risk_rules=risk_rules,
            macro_indicators=macro_indicators
        )
        
        # 调用 GLM-5 分析
        try:
            result = self.client.chat(
                message=prompt,
                system_prompt=self.system_prompt,
                temperature=self.config.get("temperature", 0.3),
                max_tokens=self.config.get("max_tokens", 3000),
            )
            
            raw_analysis = result.get("content", "")
            logger.info(f"GLM-5 分析完成，输出 {len(raw_analysis)} 字")
            
        except Exception as e:
            logger.error(f"GLM-5 分析失败: {e}")
            return self._create_error_result(str(e))
        
        # 解析决策结果
        decision = self._parse_decision_result(
            raw_analysis=raw_analysis,
            market_data=market_data,
            portfolio_data=portfolio_data,
            risk_rules=risk_rules,
        )
        
        return decision
    
    def _build_decision_prompt(
        self,
        market_data: Dict,
        portfolio_data: Dict,
        risk_rules: Optional[Dict],
        macro_indicators: Optional[Dict],
    ) -> str:
        """构建决策提示词"""
        
        prompt = f"""# 交易决策请求

【日期】: {market_data.get('日期', datetime.now().strftime('%Y-%m-%d'))}

## 一、市场数据

### 1. 指数行情
{json.dumps(market_data.get('指数行情', {}), ensure_ascii=False, indent=2)}

### 2. 板块表现
{json.dumps(market_data.get('板块表现', {}), ensure_ascii=False, indent=2)}

### 3. 资金流向
{json.dumps(market_data.get('资金流向', {}), ensure_ascii=False, indent=2)}

### 4. 技术指标
{json.dumps(market_data.get('技术指标', []), ensure_ascii=False, indent=2)}

"""
        
        # 宏观指标
        if macro_indicators:
            prompt += f"""
## 二、宏观指标

{json.dumps(macro_indicators, ensure_ascii=False, indent=2)}

"""
        
        # 持仓数据
        prompt += f"""
## 三、持仓数据

### 1. 账户概况
- 账户总值: {portfolio_data.get('账户总值', 'N/A')}
- 当日盈亏: {portfolio_data.get('当日盈亏', 'N/A')}
- 累计收益: {portfolio_data.get('累计收益', 'N/A')}

### 2. 持仓明细
{json.dumps(portfolio_data.get('持仓', []), ensure_ascii=False, indent=2)}

### 3. 目标仓位
{json.dumps(portfolio_data.get('目标仓位', {}), ensure_ascii=False, indent=2)}

"""
        
        # 风控规则
        if risk_rules:
            prompt += f"""
## 四、风控规则

- 单只标的最大仓位: {risk_rules.get('max_single_position', 0.10) * 100:.0f}%
- 止损线: {risk_rules.get('stop_loss_pct', -0.08) * 100:.0f}%
- 止盈线: {risk_rules.get('take_profit_pct', 0.15) * 100:.0f}%

"""
        
        # 决策要求
        prompt += """
## 五、决策要求

请根据以上数据，做出以下决策：

### 1. 交易信号（必须给出明确建议）
对每只持仓标的，给出：
- 动作: BUY（买入）/ SELL（卖出）/ HOLD（持有）/ REDUCE（减仓）
- 目标仓位: 建议的目标占比
- 仓位变化: 需要增减的百分点
- 建议数量: 建议买卖的股数
- 置信度: 0-1 之间的数值
- 理由: 基于数据的分析
- 紧急程度: LOW / MEDIUM / HIGH / URGENT

### 2. 风险预警
检查以下风险：
- 止损触发: 是否有标的亏损超过止损线
- 止盈机会: 是否有标的盈利超过止盈线
- 仓位超标: 是否有标的超过最大仓位限制
- 行业集中: 是否有行业过度集中
- 市场风险: 大盘是否出现危险信号

### 3. 组合调整建议
- 是否需要再平衡
- 建议调仓方向
- 现金比例建议

### 4. 宏观展望
- 短期（1-3天）市场走势判断
- 中期（1-4周）趋势预判
- 重点关注的事件和风险

请严格按照以下格式输出：

## 交易信号
| 代码 | 名称 | 动作 | 当前仓位 | 目标仓位 | 变化 | 数量 | 置信度 | 紧急程度 | 理由 |
|------|------|------|---------|---------|------|------|--------|---------|------|
| 300308 | 中际旭创 | BUY | 4.5% | 5.0% | +0.5% | 100股 | 0.85 | MEDIUM | MACD金叉确认，资金流入 |

## 风险预警
- [CRITICAL] 中国神华亏损-9.2%，触发止损线，建议立即减仓50%
- [HIGH] 科技板块仓位已达35%，接近上限，建议控制新增买入

## 组合调整建议
- 建议将现金比例从5%提升至8%
- 减持中国神华2%，增持中际旭创1%

## 宏观展望
- 短期：震荡上行，关注3050点压力位
- 中期：结构性行情，科技板块占优
- 风险：美联储议息会议结果不确定

## AI 决策总结
（用3-5句话总结最重要的决策建议）
"""
        
        return prompt
    
    def _parse_decision_result(
        self,
        raw_analysis: str,
        market_data: Dict,
        portfolio_data: Dict,
        risk_rules: Optional[Dict],
    ) -> DecisionResult:
        """解析 GLM-5 的输出结果"""
        
        # 提取交易信号（从 Markdown 表格中解析）
        trading_signals = self._extract_trading_signals(raw_analysis)
        
        # 提取风险预警
        risk_alerts = self._extract_risk_alerts(raw_analysis)
        
        # 提取组合建议
        portfolio_advice = self._extract_section(raw_analysis, "组合调整建议")
        
        # 提取宏观展望
        macro_outlook = self._extract_section(raw_analysis, "宏观展望")
        
        # 提取市场概况
        market_summary = self._extract_section(raw_analysis, "AI 决策总结") or "AI 分析完成"
        
        # 计算整体置信度
        if trading_signals:
            avg_confidence = sum(s.confidence for s in trading_signals) / len(trading_signals)
        else:
            avg_confidence = 0.0
        
        return DecisionResult(
            timestamp=datetime.now().isoformat(),
            market_summary=market_summary,
            trading_signals=trading_signals,
            risk_alerts=risk_alerts,
            portfolio_advice=portfolio_advice,
            macro_outlook=macro_outlook,
            ai_confidence=avg_confidence,
            raw_analysis=raw_analysis,
        )
    
    def _extract_trading_signals(self, text: str) -> List[TradingSignal]:
        """从文本中提取交易信号"""
        signals = []
        
        # 尝试从 Markdown 表格中提取
        lines = text.split('\n')
        in_table = False
        table_rows = []
        
        for line in lines:
            if '|' in line and ('代码' in line or '标的' in line):
                in_table = True
                continue
            if in_table:
                if line.strip().startswith('|') and '---' not in line:
                    table_rows.append(line)
                else:
                    in_table = False
        
        # 解析表格行
        for row in table_rows:
            cells = [c.strip() for c in row.split('|')[1:-1]]
            if len(cells) >= 8:
                try:
                    signal = TradingSignal(
                        action=cells[2],
                        code=cells[0],
                        name=cells[1],
                        current_weight=float(cells[3].replace('%', '')) / 100,
                        target_weight=float(cells[4].replace('%', '')) / 100,
                        weight_change=0,  # 可以从 cells[5] 解析
                        quantity=int(cells[6].replace('股', '').replace('手', '')) if cells[6] else 0,
                        price=0,
                        confidence=float(cells[7]),
                        reason=cells[8] if len(cells) > 8 else "",
                        urgency=cells[6] if len(cells) > 6 and cells[6] in ["LOW", "MEDIUM", "HIGH", "URGENT"] else "MEDIUM",
                    )
                    signals.append(signal)
                except (ValueError, IndexError):
                    continue
        
        # 如果没有表格，尝试从文本中提取
        if not signals:
            signals = self._extract_signals_from_text(text)
        
        return signals
    
    def _extract_signals_from_text(self, text: str) -> List[TradingSignal]:
        """从纯文本中提取交易信号（备用方案）"""
        signals = []
        
        # 简单正则匹配
        import re
        patterns = [
            r'(BUY|SELL|HOLD|REDUCE)\s+([A-Z0-9]+)\s+([^\s,]+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                signals.append(TradingSignal(
                    action=match.group(1).upper(),
                    code=match.group(2),
                    name=match.group(3),
                    current_weight=0,
                    target_weight=0,
                    weight_change=0,
                    quantity=0,
                    price=0,
                    confidence=0.7,
                    reason="AI 自动判断",
                    urgency="MEDIUM",
                ))
        
        return signals
    
    def _extract_risk_alerts(self, text: str) -> List[RiskAlert]:
        """从文本中提取风险预警"""
        alerts = []
        
        import re
        # 匹配 [CRITICAL]/[HIGH]/[MEDIUM]/[LOW] 格式
        pattern = r'\[(CRITICAL|HIGH|MEDIUM|LOW)\]\s+(.+?)(?=\n\[-|\n##|$)'
        matches = re.finditer(pattern, text, re.DOTALL)
        
        for match in matches:
            severity = match.group(1)
            message = match.group(2).strip()
            
            # 简单提取股票代码
            code_match = re.search(r'([A-Z0-9]{6})', message)
            code = code_match.group(1) if code_match else "UNKNOWN"
            
            alerts.append(RiskAlert(
                alert_type="RISK_WARNING",
                severity=severity,
                code=code,
                message=message,
                action_required="请人工审核"
            ))
        
        return alerts
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """提取指定章节内容"""
        import re
        pattern = rf'##\s*{section_name}\s*\n(.*?)(?=\n##|\n#|$)'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    def _create_error_result(self, error_msg: str) -> DecisionResult:
        """创建错误结果"""
        return DecisionResult(
            timestamp=datetime.now().isoformat(),
            market_summary=f"决策生成失败: {error_msg}",
            trading_signals=[],
            risk_alerts=[RiskAlert(
                alert_type="SYSTEM_ERROR",
                severity="CRITICAL",
                code="SYSTEM",
                message=error_msg,
                action_required="检查系统配置和网络连接"
            )],
            ai_confidence=0.0,
        )
    
    def quick_check(self, portfolio_data: Dict) -> DecisionResult:
        """
        快速检查（简化版，仅检查持仓风险）
        
        Args:
            portfolio_data: 持仓数据
        
        Returns:
            DecisionResult
        """
        market_data = {
            "日期": datetime.now().strftime("%Y-%m-%d"),
            "指数行情": {},
            "板块表现": {},
            "资金流向": {},
            "技术指标": [],
        }
        
        return self.make_decisions(
            market_data=market_data,
            portfolio_data=portfolio_data,
            risk_rules={
                "max_single_position": 0.10,
                "stop_loss_pct": -0.08,
                "take_profit_pct": 0.15,
            }
        )
    
    def export_decisions(self, decision: DecisionResult, output_dir: str = None) -> str:
        """
        导出决策结果为 Markdown 文件
        
        Args:
            decision: 决策结果
            output_dir: 输出目录（默认: 每日报告归档/YYYY-MM-DD/）
        
        Returns:
            输出文件路径
        """
        if output_dir is None:
            base_dir = Path(__file__).parent.parent.parent / "每日报告归档"
            date_str = datetime.now().strftime("%Y-%m-%d")
            output_dir = base_dir / date_str
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"AI决策_{timestamp}.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# AI 交易决策报告\n\n")
            f.write(f"**生成时间**: {decision.timestamp}\n")
            f.write(f"**AI 置信度**: {decision.ai_confidence:.2%}\n\n")
            
            # 市场概况
            f.write(f"## 市场概况\n\n{decision.market_summary}\n\n")
            
            # 交易信号
            if decision.trading_signals:
                f.write(f"## 交易信号\n\n")
                f.write("| 代码 | 名称 | 动作 | 当前仓位 | 目标仓位 | 数量 | 置信度 | 紧急程度 |\n")
                f.write("|------|------|------|---------|---------|------|--------|----------|\n")
                for sig in decision.trading_signals:
                    f.write(f"| {sig.code} | {sig.name} | {sig.action} | "
                           f"{sig.current_weight:.1%} | {sig.target_weight:.1%} | "
                           f"{sig.quantity} | {sig.confidence:.2f} | {sig.urgency} |\n")
                f.write("\n")
            
            # 风险预警
            if decision.risk_alerts:
                f.write(f"## 风险预警\n\n")
                for alert in decision.risk_alerts:
                    f.write(f"- **[{alert.severity}]** {alert.message}\n")
                f.write("\n")
            
            # 组合建议
            if decision.portfolio_advice:
                f.write(f"## 组合调整建议\n\n{decision.portfolio_advice}\n\n")
            
            # 宏观展望
            if decision.macro_outlook:
                f.write(f"## 宏观展望\n\n{decision.macro_outlook}\n\n")
            
            # 原始分析
            f.write(f"---\n\n*以上决策由 GLM-5 AI 自动生成，仅供参考，不构成投资建议*\n")
            f.write("*请人工审核后再执行交易*\n")
        
        logger.info(f"决策报告已保存: {output_file}")
        return str(output_file)


# ==================== 快捷函数 ====================

def auto_trade_decision(
    market_data: Dict,
    portfolio_data: Dict,
    **kwargs
) -> DecisionResult:
    """
    一键生成交易决策
    
    Args:
        market_data: 市场数据
        portfolio_data: 持仓数据
        **kwargs: 传递给 GLM5DecisionEngine 的参数
    
    Returns:
        DecisionResult
    """
    engine = GLM5DecisionEngine(**kwargs)
    return engine.make_decisions(market_data, portfolio_data)


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("GLM-5 自动决策引擎测试")
    print("=" * 60)
    
    # 模拟市场数据
    market_data = {
        "日期": "2026-06-23",
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
    
    # 模拟持仓数据
    portfolio_data = {
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
    
    # 风控规则
    risk_rules = {
        "max_single_position": 0.10,
        "stop_loss_pct": -0.08,
        "take_profit_pct": 0.15,
    }
    
    try:
        # 生成决策
        print("\n正在生成交易决策...\n")
        decision = auto_trade_decision(
            market_data=market_data,
            portfolio_data=portfolio_data,
            risk_rules=risk_rules,
        )
        
        # 打印结果
        print("=" * 60)
        print("决策结果")
        print("=" * 60)
        print(f"\n市场概况: {decision.market_summary}")
        
        if decision.trading_signals:
            print(f"\n交易信号 ({len(decision.trading_signals)} 条):")
            for sig in decision.trading_signals:
                print(f"  [{sig.action}] {sig.code} {sig.name} "
                      f"(仓位: {sig.current_weight:.1%} → {sig.target_weight:.1%}, "
                      f"置信度: {sig.confidence:.2f})")
                print(f"    理由: {sig.reason}")
        
        if decision.risk_alerts:
            print(f"\n风险预警 ({len(decision.risk_alerts)} 条):")
            for alert in decision.risk_alerts:
                print(f"  [{alert.severity}] {alert.message}")
        
        if decision.portfolio_advice:
            print(f"\n组合建议: {decision.portfolio_advice[:200]}...")
        
        print(f"\nAI 整体置信度: {decision.ai_confidence:.2%}")
        
        # 导出报告
        output_file = auto_trade_decision.__globals__['GLM5DecisionEngine']().__class__.__module__
        engine = GLM5DecisionEngine()
        file_path = engine.export_decisions(decision)
        print(f"\n报告已保存: {file_path}")
        
        print("\n" + "=" * 60)
        print("✅ 决策引擎测试完成!")
        
    except Exception as e:
        print(f"\n❌ 决策引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
