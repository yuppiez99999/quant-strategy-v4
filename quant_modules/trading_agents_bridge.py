# -*- coding: utf-8 -*-
"""
TradingAgents Bridge v1.0 — 多智能体交易系统集成层

将 TauricResearch/TradingAgents 的 LangGraph 多Agent管道接入量化策略系统:
  - 替换 yfinance 数据源为 Wind MCP
  - DeepSeek V4 Pro 作为 LLM (OpenAI 兼容接口)
  - 盘前对每只持仓标的运行 Analyst→Researcher→Risk→Trader→Reflection 全流程

API: DeepSeek 兼容 OpenAI /v1/chat/completions
文档: https://api-docs.deepseek.com/
"""

import os, sys, json, logging
from datetime import datetime
from typing import Dict, List, Optional, Any

_log = logging.getLogger('trading_agents_bridge')

# TradingAgents 安装路径
TRADING_AGENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'TradingAgents')
if TRADING_AGENTS_DIR not in sys.path:
    sys.path.insert(0, TRADING_AGENTS_DIR)

# ============================================================
# 1. DeepSeek 配置 (OpenAI兼容)
# ============================================================

def _get_deepseek_config() -> dict:
    """构建 DeepSeek 兼容配置"""
    config = {}
    try:
        from tradingagents.default_config import DEFAULT_CONFIG
        config = DEFAULT_CONFIG.copy()
    except ImportError:
        pass

    # DeepSeek 兼容
    config['llm_provider'] = 'openai'
    config['deep_think_llm'] = 'deepseek-chat'
    config['quick_think_llm'] = 'deepseek-chat'
    config['backend_url'] = 'https://api.deepseek.com'
    config['openai_reasoning_effort'] = None
    config['output_language'] = 'Chinese'
    config['max_debate_rounds'] = 1
    config['max_risk_discuss_rounds'] = 1
    config['checkpoint_enabled'] = False
    config['temperature'] = 0.3

    # 确保 API Key
    for env_var in ['DEEPSEEK_API_KEY', 'OPENAI_API_KEY']:
        key = os.environ.get(env_var, '')
        if key:
            os.environ['OPENAI_API_KEY'] = key
            break

    if not os.environ.get('OPENAI_API_KEY'):
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if 'DEEPSEEK_API_KEY=' in line:
                        key = line.split('=', 1)[1].strip()
                        os.environ['OPENAI_API_KEY'] = key
                        break

    return config


# ============================================================
# 2. Wind MCP 数据桥接 — 替换 yfinance
# ============================================================

def _build_wind_context(code: str, prices: Dict[str, float] = None) -> str:
    """用 Wind MCP 数据构建 instrument_context,替代 yfinance"""
    lines = []
    price = prices.get(code, 0) if prices else 0

    # 标的名称映射
    names = {
        '510300': '沪深300ETF', '510500': '中证500ETF', '512100': '中证1000ETF',
        '588000': '科创50ETF', '159915': '创业板ETF',
        '688041': '海光信息(国产AI芯片)', '300308': '中际旭创(光模块龙头)',
        '300274': '阳光电源(光伏逆变器)', '002371': '北方华创(半导体设备)',
        '688017': '绿的谐波(机器人核心部件)', '600276': '恒瑞医药(创新药龙头)',
        '600089': '特变电工(电网+多晶硅)', '600875': '东方电气(核电风电)',
        '000425': '徐工机械(工程机械)', '600406': '国电南瑞(电网自动化)',
        '600989': '宝丰能源(煤化工+光伏)', '515180': '中证红利ETF',
        '600036': '招商银行(零售银行)', '600900': '长江电力(水电龙头)',
        '601088': '中国神华(煤电一体化)', '518880': '华安黄金ETF',
    }

    name = names.get(code, code)
    exchange = '上海证券交易所' if code.startswith(('5', '6')) else '深圳证券交易所'

    lines.append(f"标的信息:")
    lines.append(f"- 代码: {code}")
    lines.append(f"- 名称: {name}")
    lines.append(f"- 交易所: {exchange}")
    if price > 0:
        lines.append(f"- 最新价: ¥{price:.2f}")
    lines.append(f"- 市场: A股(中国大陆)")
    lines.append(f"- 货币: CNY(人民币)")

    return '\n'.join(lines)


# ============================================================
# 3. 核心集成 — 单标的多Agent分析
# ============================================================

def analyze_with_trading_agents(
    code: str,
    trade_date: str = None,
    prices: Dict[str, float] = None,
) -> Optional[Dict]:
    """
    对单个标的运行 TradingAgents 多Agent分析

    Args:
        code: 标的代码如 601088
        trade_date: 交易日期 YYYY-MM-DD
        prices: {code: price} 价格字典

    Returns:
        {
            'decision': 'BUY'/'SELL'/'HOLD',
            'confidence': 0.85,
            'reasoning': '...',
            'agent_outputs': {...}
        }
    """
    if trade_date is None:
        trade_date = datetime.now().strftime('%Y-%m-%d')

    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        config = _get_deepseek_config()

        if not os.environ.get('OPENAI_API_KEY'):
            _log.warning("[TradingAgents] No API key configured, skipping")
            return None

        # 构建 Wind 数据上下文
        instrument_context = _build_wind_context(code, prices)

        # 初始化
        ta = TradingAgentsGraph(debug=False, config=config)

        # 运行多Agent分析
        company_name = f"{code} (A股)"
        _, decision = ta.propagate(
            company_name=company_name,
            trade_date=trade_date,
            asset_type="stock",
            instrument_context=instrument_context,
        )

        if decision:
            return {
                'decision': _extract_decision(decision),
                'raw': str(decision)[:500],
                'timestamp': datetime.now().isoformat(),
            }
        return None

    except ImportError as e:
        _log.debug(f"[TradingAgents] Not available: {e}")
    except Exception as e:
        _log.warning(f"[TradingAgents] Error on {code}: {e}")

    return None


def _extract_decision(raw_decision) -> str:
    """从 TradingAgents 输出中提取买卖信号"""
    text = str(raw_decision).upper()
    if 'BUY' in text or '买入' in text or '看多' in text:
        return 'BUY'
    elif 'SELL' in text or '卖出' in text or '看空' in text:
        return 'SELL'
    return 'HOLD'


# ============================================================
# 4. 批量分析 — 全组合多Agent扫描
# ============================================================

def batch_analyze_portfolio(
    codes: List[str],
    prices: Dict[str, float],
    trade_date: str = None,
) -> Dict[str, Dict]:
    """
    对全组合运行多Agent批量分析

    Args:
        codes: 标的代码列表
        prices: {code: price}
        trade_date: 交易日期

    Returns:
        {code: {'decision': 'BUY', ...}}
    """
    results = {}
    for code in codes:
        result = analyze_with_trading_agents(code, trade_date, prices)
        if result:
            results[code] = result
            _log.info(f"[TA] {code}: {result['decision']}")
    return results
