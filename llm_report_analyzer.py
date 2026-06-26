# -*- coding: utf-8 -*-
"""
大模型报告解读模块
使用 LLM 对持仓报告进行深度解读，生成投资建议

支持模型:
  - 火山引擎豆包 Seed 2.0 Pro (默认 - 最强分析)
  - 智谱AI GLM-4-Flash (免费备用)
  - SiliconFlow API (备用)
  - OpenAI API (可选)
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Windows编码修复
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

logger = logging.getLogger('LLMReportAnalyzer')

# ── 加载 .env 文件（在读取环境变量之前） ──────────────────
def _load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    k, v = k.strip(), v.strip()
                    if k not in os.environ:
                        os.environ[k] = v
_load_dotenv()

# ── API 配置 ────────────────────────────────────────
# 火山引擎豆包 Seed (主模型 - 最强分析)
VOLCENGINE_API_URL = "https://ark.cn-beijing.volces.com/api/v3/responses"
VOLCENGINE_API_KEY = os.environ.get("VOLCENGINE_API_KEY", "")
VOLCENGINE_DEFAULT_MODEL = "doubao-speed-32k"

# 智谱AI GLM (备用 - 免费)
ZHIPUAI_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
ZHIPUAI_API_KEY = os.environ.get("ZHIPUAI_API_KEY", "")
ZHIPUAI_DEFAULT_MODEL = "glm-4-flash"

# SiliconFlow API (备用)
SILICONFLOW_API_URL = "https://api.siliconflow.cn/v1/chat/completions"

# 支持的模型（按优先级排序）
SUPPORTED_MODELS = {
    'volc_doubao_speed': 'doubao-speed-32k',
    'glm4_flash': 'glm-4-flash',
    'deepseek_v4': 'deepseek-chat',
    'deepseek_r1': 'deepseek-reasoner',
    'volc_doubao_pro': 'doubao-pro-32k',  # 备选模型
    'qwen_7b': 'Qwen/Qwen2.5-7B-Instruct',
    'qwen_32b': 'Qwen/Qwen2.5-32B-Instruct',
    'deepseek_v3': 'deepseek-ai/DeepSeek-V3',
}


class LLMReportAnalyzer:
    """
    大模型报告解读器
    自动调用 LLM 对持仓报告进行深度分析和解读
    支持: 豆包 Seed 2.0 Pro (默认), 智谱AI GLM, SiliconFlow
    """

    def __init__(self, api_key: str = None, model: str = None, provider: str = 'volcengine'):
        """
        初始化LLM分析器

        Args:
            api_key: API Key (为空时使用环境变量)
            model: 模型名称 (默认: doubao-speed-32k)
            provider: API提供商 ('volcengine', 'zhipuai', 'deepseek', 'siliconflow')
        """
        self.provider = provider
        self._client = None

        if provider == 'volcengine':
            self.api_key = api_key or VOLCENGINE_API_KEY
            self.model = model or os.environ.get("VOLCENGINE_MODEL", "doubao-speed-32k")
            self.api_url = VOLCENGINE_API_URL
        elif provider == 'zhipuai':
            self.api_key = api_key or ZHIPUAI_API_KEY
            self.model = model or "glm-4-flash"
            self.api_url = ZHIPUAI_API_URL
        elif provider == 'deepseek':
            self.api_key = api_key or DEEPSEEK_API_KEY
            self.model = model or DEEPSEEK_DEFAULT_MODEL
            self.api_url = DEEPSEEK_API_URL
        else:
            self.api_key = api_key or self._get_api_key()
            self.model = model or "Qwen/Qwen2.5-7B-Instruct"
            self.api_url = SILICONFLOW_API_URL

    def _get_api_key(self) -> Optional[str]:
        """从多个来源获取API Key"""
        # 1. 优先从环境变量
        api_key = os.environ.get('SILICONFLOW_API_KEY') or os.environ.get('OPENAI_API_KEY')
        if api_key:
            return api_key

        # 2. 尝试从 .env 文件读取
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                if key.strip() in ('SILICONFLOW_API_KEY', 'OPENAI_API_KEY'):
                                    return value.strip()
            except Exception as e:
                logger.warning(f"读取.env文件失败: {e}")

        return None

    def _get_client(self):
        """获取HTTP客户端 (延迟初始化)"""
        if self._client is None:
            try:
                import requests
                # 清除代理设置，避免代理连接失败
                for k in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
                    os.environ.pop(k, None)
                os.environ['no_proxy'] = '*'
                self._client = requests
            except ImportError:
                logger.error("请安装 requests 库: pip install requests")
                return None
        return self._client

    def analyze_report(self, report_content: str, include_positions: bool = True) -> Dict[str, Any]:
        """
        使用LLM深度分析报告内容

        Args:
            report_content: 报告文本内容
            include_positions: 是否包含持仓分析

        Returns:
            分析结果字典
        """
        if not self.api_key:
            logger.warning("未配置API Key，使用模拟分析")
            return self._generate_mock_analysis("API Key未配置")

        # 构建分析提示词
        prompt = self._build_analysis_prompt(report_content, include_positions)

        last_error = None
        for attempt in range(len(SUPPORTED_MODELS)):
            try:
                result = self._call_llm(prompt)
                if result and not result.startswith("API调用失败"):
                    # 正常返回内容
                    return self._parse_llm_response(result)
                elif result:
                    # 返回的是错误信息
                    last_error = result
                # 如果返回None或错误，尝试下一个模型
                break
            except Exception as e:
                last_error = str(e)
                logger.error(f"LLM分析失败: {e}")
                continue

        return self._generate_mock_analysis(last_error)

    def _build_analysis_prompt(self, report_content: str, include_positions: bool) -> str:
        """构建分析提示词"""
        prompt = f"""你是专业量化投资顾问，请对以下持仓报告做简要深度解读。

## 报告:
```
{report_content[:4000]}
```

## 请分析(每项3-5句话):
1. **行情解读**: 市场整体表现与涨跌分析
2. **持仓诊断**: 配置合理性与再平衡建议
3. **风险评估**: 主要风险与止损状态
4. **操作建议**: 具体买卖建议(优先级排序)

用中文，简洁专业。"""
        return prompt

    def _call_llm(self, prompt: str, max_retries: int = 2) -> Optional[str]:
        """调用LLM API"""
        client = self._get_client()
        if not client:
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 火山引擎新API (responses端点) 格式
        if 'responses' in self.api_url:
            payload = {
                "model": self.model,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
        # 智谱AI GLM API 格式 (与 OpenAI 兼容)
        elif 'bigmodel.cn' in self.api_url:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一位专业的量化投资顾问，擅长A股投资分析。你的分析专业、客观、有深度，但语言简洁易懂。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
        else:
            # SiliconFlow/OpenAI 格式
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一位专业的量化投资顾问，擅长A股投资分析。你的分析专业、客观、有深度，但语言简洁易懂。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }

        for attempt in range(max_retries):
            try:
                response = client.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=120
                )

                if response.status_code == 200:
                    data = response.json()
                    # 火山引擎 responses API 格式
                    if 'output' in data:
                        for output in data.get('output', []):
                            # output_text 类型
                            if output.get('type') == 'message':
                                for content_item in output.get('content', []):
                                    if content_item.get('type') == 'output_text':
                                        return content_item.get('text', '')
                            # 兼容其他格式
                            elif output.get('type') == 'output_text':
                                content = output.get('content', [])
                                if isinstance(content, list) and content:
                                    return content[0].get('text', '')
                                elif isinstance(content, str):
                                    return content
                    # 智谱AI GLM / SiliconFlow / OpenAI 格式
                    return data.get('choices', [{}])[0].get('message', {}).get('content', '')
                elif response.status_code == 429:
                    logger.warning("API调用频率限制，等待后重试...")
                    time.sleep(5)
                elif response.status_code == 403 or response.status_code == 401:
                    error_msg = response.text
                    if 'insufficient' in error_msg.lower():
                        logger.warning("账户余额不足，尝试备用模型...")
                        # 尝试备用免费模型
                        for model_name, model_id in SUPPORTED_MODELS.items():
                            if model_id != self.model:
                                self.model = model_id
                                logger.info(f"切换到备用模型: {model_id}")
                                payload['model'] = model_id
                                break
                    elif 'disabled' in error_msg.lower():
                        logger.warning(f"模型 {self.model} 不可用，尝试备用模型...")
                        # 尝试其他可用模型
                        for model_name, model_id in SUPPORTED_MODELS.items():
                            if model_id != self.model:
                                self.model = model_id
                                payload['model'] = model_id
                                break
                else:
                    logger.error(f"API调用失败: {response.status_code} - {response.text}")
                    # 返回错误信息字符串，供上层捕获
                    return f"API调用失败: {response.status_code} - {response.text}"

            except Exception as e:
                logger.error(f"API调用异常: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    # 返回错误信息
                    return f"API调用异常: {str(e)}"

        return None

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        return {
            'has_llm_analysis': True,
            'raw_analysis': response,
            'sections': self._extract_sections(response),
            'recommendations': self._extract_recommendations(response),
            'risk_level': self._assess_risk_level(response),
            'confidence': 0.85
        }

    def _extract_sections(self, response: str) -> Dict[str, str]:
        """提取分析章节"""
        sections = {}
        current_section = '概述'
        current_content = []

        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue

            # 检测章节标题
            section_keywords = ['行情解读', '持仓诊断', '策略建议', '风险评估',
                              '操作建议', '投资洞察', '今日分析', '综合判断']
            is_section = False
            for kw in section_keywords:
                if kw in line and (line.startswith('#') or '##' in line or
                                   line.startswith('【') or line.startswith('[')):
                    is_section = True
                    break

            if is_section and current_content:
                sections[current_section] = '\n'.join(current_content)
                current_content = []

                # 提取新章节名
                for kw in section_keywords:
                    if kw in line:
                        current_section = kw
                        break
            else:
                current_content.append(line)

        if current_content:
            sections[current_section] = '\n'.join(current_content)

        return sections

    def _extract_recommendations(self, response: str) -> List[Dict]:
        """提取操作建议"""
        recommendations = []

        # 简单的关键词匹配
        action_keywords = {
            '买入': 'buy', '加仓': 'buy', '增持': 'buy',
            '卖出': 'sell', '减仓': 'sell', '清仓': 'sell',
            '持有': 'hold', '观望': 'hold', '等待': 'hold'
        }

        for line in response.split('\n'):
            for keyword, action in action_keywords.items():
                if keyword in line:
                    recommendations.append({
                        'action': action,
                        'content': line.strip(),
                        'priority': 'high' if action in ('buy', 'sell') else 'medium'
                    })
                    break

        return recommendations[:5]  # 最多5条

    def _assess_risk_level(self, response: str) -> str:
        """评估风险等级"""
        risk_keywords = {
            '高风险': 'high', '风险较大': 'high', '谨慎': 'medium',
            '中等风险': 'medium', '低风险': 'low', '风险可控': 'low'
        }

        for keyword, level in risk_keywords.items():
            if keyword in response:
                return level

        return 'medium'  # 默认中等风险

    def _generate_mock_analysis(self, error_info: str = None) -> Dict[str, Any]:
        """生成模拟分析（当API不可用时）"""
        error_msg = ""
        if error_info:
            if 'insufficient' in error_info.lower() or 'balance' in error_info.lower():
                error_msg = "\n\n⚠️ 账户余额不足，请前往平台控制台充值"
            elif 'invalid' in error_info.lower() or 'AuthenticationError' in error_info:
                error_msg = "\n\n⚠️ API Key无效或已过期，请检查Key是否正确"
            elif 'disabled' in error_info.lower():
                error_msg = "\n\n⚠️ 当前模型不可用，可能需要升级账户套餐"
            else:
                error_msg = f"\n\n⚠️ API错误: {error_info}"

        return {
            'has_llm_analysis': False,
            'mock': True,
            'raw_analysis': '【模拟分析】API调用失败' + error_msg,
            'sections': {
                '概述': f'大模型分析功能遇到问题。{error_msg}\n\n请检查API配置：\n1. 如果使用火山引擎：请确认API Key来自豆包模型API（ark-*格式），而非Agent平台\n2. 如果使用SiliconFlow：访问 https://cloud.siliconflow.cn 确认账户有余额\n3. 检查.env文件中的API配置是否正确',
                '操作建议': '• 账户配置正确时可获取完整LLM深度分析\n• 当前建议参考现有的AI策略分析模块\n• 关注止损止盈风险监控'
            },
            'recommendations': [
                {'action': 'hold', 'content': '请检查API配置后重新运行', 'priority': 'low'}
            ],
            'risk_level': 'medium',
            'confidence': 0.0
        }


def format_llm_analysis_for_report(analysis: Dict[str, Any]) -> str:
    """
    将LLM分析结果格式化为报告文本

    Args:
        analysis: LLM分析结果

    Returns:
        格式化后的报告文本
    """
    lines = []
    lines.append("")
    lines.append("=" * 80)
    lines.append("🧠 大模型深度解读 (AI)")
    lines.append("=" * 80)
    lines.append("")

    if analysis.get('mock'):
        # 使用analysis中的sections内容
        sections = analysis.get('sections', {})
        raw_error = analysis.get('raw_analysis', '')

        # 显示错误信息
        if 'ModelNotOpen' in raw_error:
            lines.append("📌 模型未开通")
            lines.append("-" * 60)
            lines.append("  ⚠️ 需要在火山引擎控制台开通模型")
            lines.append("")
            lines.append("  开通步骤:")
            lines.append("  1. 访问 https://console.volcengine.com/ark")
            lines.append("  2. 选择『在线推理』或『模型广场』")
            lines.append("  3. 找到并开通: doubao-speed-32k 或 doubao-pro-32k")
            lines.append("  4. 开通后重新运行即可")
            lines.append("")
            lines.append(f"  错误: {raw_error[:150]}...")
        elif 'InvalidEndpointOrModel' in raw_error or 'NotFound' in raw_error:
            lines.append("📌 模型不可用")
            lines.append("-" * 60)
            lines.append("  ⚠️ 当前模型未在账户中开通")
            lines.append("")
            lines.append("  解决方案:")
            lines.append("  • 请使用您curl示例中的模型: doubao-speed-32k")
            lines.append("  • 或前往控制台开通其他豆包模型")
            lines.append(f"  • 错误: {raw_error[:150]}...")
        else:
            lines.append("📌 功能提示")
            lines.append("-" * 60)
            lines.append("  ⚠️ 大模型分析功能需要配置有效的 API Key")
            lines.append("")
            lines.append("  获取免费API Key:")
            lines.append("  1. 访问火山引擎 https://console.volcengine.com/ark 开通豆包模型")
            lines.append("  2. 或访问 SiliconFlow https://cloud.siliconflow.cn")
            lines.append("  3. 获取API Key后在.env文件中配置")
            lines.append("")

        lines.append("")
        return '\n'.join(lines)

    # 输出各章节
    sections = analysis.get('sections', {})
    for section_name in ['行情解读', '持仓诊断', '策略建议', '风险评估',
                         '操作建议', '投资洞察', '概述', '综合判断']:
        if section_name in sections:
            lines.append(f"📊 {section_name}")
            lines.append("-" * 60)
            content = sections[section_name]
            for line in content.split('\n')[:15]:  # 限制每节行数
                if line.strip():
                    lines.append(f"  {line}")
            lines.append("")

    # 风险等级
    risk_level = analysis.get('risk_level', 'medium')
    risk_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
    risk_text = {'high': '高风险', 'medium': '中等风险', 'low': '低风险'}

    lines.append("")
    lines.append("🎯 风险等级评估")
    lines.append("-" * 60)
    lines.append(f"  {risk_emoji.get(risk_level, '🟡')} {risk_text.get(risk_level, '中等风险')}")

    # 置信度
    confidence = analysis.get('confidence', 0)
    if confidence > 0:
        lines.append(f"  分析置信度: {confidence*100:.0f}%")

    return '\n'.join(lines)


def analyze_portfolio_with_llm(
    report_content: str,
    api_key: str = None,
    model: str = None
) -> str:
    """
    便捷函数: 对持仓报告进行LLM分析并返回格式化的报告文本

    Args:
        report_content: 报告内容
        api_key: API密钥
        model: 模型名称

    Returns:
        格式化的分析报告
    """
    analyzer = LLMReportAnalyzer(api_key=api_key, model=model)
    analysis = analyzer.analyze_report(report_content)
    return format_llm_analysis_for_report(analysis)


# ============================================================
# LLM 盘中决策与再平衡顾问 (豆包 Seed 2.0 Pro)
# ============================================================
class LLMTradingAdvisor(LLMReportAnalyzer):
    """
    盘中计划制定 + 再平衡决策顾问
    继承 LLMReportAnalyzer 复用 _call_llm / .env 加载 / 多模型回退
    """

    def generate_intraday_plan(self, portfolio_state: Dict[str, Any],
                               market_context: str = "") -> Dict[str, Any]:
        """
        盘中交易计划制定

        Args:
            portfolio_state: {"positions":{code:{"shares","avg_cost"}},"prices":{code:float},
                              "names":{code:str},"target_weights":{code:float},
                              "total_value":float,"cash":float}
            market_context: 市场环境描述（如"沪深300 -0.8%，创业板 -1.2%"）

        Returns:
            {"plan": str, "actions": [...], "source": "volcengine_seed"/"mock"}
        """
        if not self.api_key:
            return {"plan": "API Key未配置，使用规则引擎","actions": [], "source": "mock"}

        summary = self._build_portfolio_summary(portfolio_state)
        prompt = f"""你是专业量化交易AI，请基于以下持仓状态制定今日盘中交易计划。

## 当前持仓
{summary}

## 市场环境
{market_context or '未提供'}

## 要求
1. 分析各标的权重偏差与动量趋势
2. 制定盘中操作计划（分批/一次性/观望）
3. 返回严格的JSON数组，每个元素代表一条操作建议：
   {{"code":"601088","action":"buy|sell|hold","shares":200,"reason":"超配2.5%，减仓锁定收益"}}
   shares必须为100的整数倍，hold时shares为0

只返回JSON数组，不要markdown标记，不要解释文字。"""

        result = self._call_llm(prompt)
        if not result or result.startswith("API调用失败"):
            return {"plan": "LLM调用失败，回退规则引擎","actions": [], "source": "mock"}

        actions = self._parse_json_actions(result)
        return {"plan": result, "actions": actions, "source": "volcengine_seed"}

    def generate_rebalance_decision(self, portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLM驱动的再平衡决策（豆包 Seed 2.0 Pro）

        Returns:
            {"actions":[{"code","action","shares","reason"}], "rationale": str, "source": str}
        """
        if not self.api_key:
            return {"actions": [], "rationale": "API Key未配置，使用规则引擎", "source": "mock"}

        summary = self._build_portfolio_summary(portfolio_state)
        total_value = portfolio_state.get("total_value", 0)
        cash = portfolio_state.get("cash", 0)

        prompt = f"""你是专业量化再平衡决策AI。请基于以下持仓执行再平衡决策。

## 当前持仓
{summary}

## 账户状态
- 账户总值: ￥{total_value:,.0f}
- 可用现金: ￥{cash:,.0f}

## 决策规则
1. 权重偏差>2%的标的需调整
2. 优先卖出超配标的回笼资金，再买入低配标的
3. 单笔交易不超过账户总值的10%
4. shares必须为100的整数倍
5. 考虑交易成本（佣金0.05%）

返回严格JSON：
{{"actions":[{{"code":"601088","action":"sell","shares":200,"reason":"超配3.2%"}}],"rationale":"简要说明决策逻辑（1-2句）"}}

只返回JSON，不要markdown标记。"""

        result = self._call_llm(prompt)
        if not result or result.startswith("API调用失败"):
            return {"actions": [], "rationale": "LLM调用失败，回退规则引擎", "source": "mock"}

        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
                decision["source"] = "volcengine_seed"
                return decision
        except (json.JSONDecodeError, AttributeError):
            pass

        # JSON解析失败，尝试提取操作列表
        actions = self._parse_json_actions(result)
        return {"actions": actions, "rationale": result[:500], "source": "volcengine_seed"}

    def _build_portfolio_summary(self, state: Dict[str, Any]) -> str:
        """构建持仓摘要文本"""
        positions = state.get("positions", {})
        prices = state.get("prices", {})
        names = state.get("names", {})
        targets = state.get("target_weights", {})
        total_value = state.get("total_value", 0)

        lines = []
        for code, pos in positions.items():
            shares = pos.get("shares", 0)
            avg_cost = pos.get("avg_cost", 0)
            price = prices.get(code, 0) or avg_cost
            mv = shares * price
            cur_w = (mv / total_value * 100) if total_value > 0 else 0
            tgt_w = targets.get(code, 0) * 100
            diff = cur_w - tgt_w
            name = names.get(code, code)
            lines.append(
                f"  {name}({code}): {shares}股 成本￥{avg_cost:.2f} 现价￥{price:.2f} "
                f"市值￥{mv:,.0f} 权重{cur_w:.1f}%(目标{tgt_w:.1f}%) 偏差{diff:+.1f}%"
            )
        return "\n".join(lines) if lines else "  (无持仓)"

    @staticmethod
    def _parse_json_actions(text: str) -> List[Dict]:
        """从LLM响应中提取JSON操作列表"""
        import re
        # 尝试提取JSON数组
        arr_match = re.search(r'\[.*\]', text, re.DOTALL)
        if arr_match:
            try:
                return json.loads(arr_match.group())
            except json.JSONDecodeError:
                pass
        # 尝试提取单个JSON对象中的actions字段
        obj_match = re.search(r'\{.*\}', text, re.DOTALL)
        if obj_match:
            try:
                obj = json.loads(obj_match.group())
                if "actions" in obj:
                    return obj["actions"]
            except json.JSONDecodeError:
                pass
        return []


# ============================================================
# 测试
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("  大模型报告解读模块测试")
    print("=" * 60)

    # 测试分析器初始化
    analyzer = LLMReportAnalyzer()

    if analyzer.api_key:
        print(f"\n✅ API Key 已配置: {analyzer.api_key[:10]}...")
        print(f"   使用模型: {analyzer.model}")
    else:
        print("\n⚠️ 未配置 API Key")
        print("   将使用模拟分析模式")

    # 生成模拟报告内容进行测试
    sample_report = """
    账户总值: ¥2,215,403.54
    持仓市值: ¥2,112,159.20
    可用现金: ¥103,244.34

    持仓明细:
    - 中国神华 601088: 权重 11.80% (目标15.0%) 低配 -3.20%
    - 恒瑞医药 600276: 权重 10.15% (目标10.0%) 正常 +0.15%
    - 沪深300ETF 510300: 权重 15.02% (目标15.0%) 正常 +0.02%
    - 科创50ETF 588000: 权重 14.91% (目标20.0%) 低配 -5.09%
    - 创业板ETF 159915: 权重 12.01% (目标15.0%) 低配 -2.99%
    - 华安黄金ETF 518880: 权重 12.06% (目标15.0%) 低配 -2.94%

    组合实时收益: -1.52%
    表现最佳: 恒瑞医药 (+1.36%)
    表现最弱: 中国神华 (-3.00%)
    """

    print("\n正在生成分析...")
    result = analyzer.analyze_report(sample_report)
    formatted = format_llm_analysis_for_report(result)

    print("\n" + formatted)
