#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Qwen Financial Predictor v2.0 — 基于 llama.cpp server 的本地推理模块
为量化策略系统 v5.1 提供本地 LLM 增强预测

后端: llama-server.exe (CPU, D:\models\llama_cpp_bin\)
模型: Qwen2.5-1.5B-Instruct-GGUF Q4_K_M (1.1GB, D:\models\Qwen\)
协议: OpenAI-compatible HTTP API (/completion)
特性: 自动启动/停止服务器, 健康检查, 超时重试, 多模式推理
"""
import os
import sys
import json
import time
import signal
import subprocess as sp
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# ============================================================
#  服务器管理
# ============================================================

class QwenServerManager:
    """管理 llama-server 的启动/停止/健康检查"""

    _instance: Optional['QwenServerManager'] = None

    def __init__(
        self,
        model_path: str = None,
        server_exe: str = None,
        port: int = 8100,
        host: str = "127.0.0.1",
        context_length: int = 2048,
        n_threads: int = 4,
    ):
        try:
            from utils.paths import get_qwen_model_path, get_llama_server_exe
            model_path = model_path or get_qwen_model_path()
            server_exe = server_exe or get_llama_server_exe()
        except ImportError:
            model_path = model_path or r"D:\models\Qwen\Qwen2.5-1.5B-Instruct\qwen2.5-1.5b-instruct-q4_k_m.gguf"
            server_exe = server_exe or r"D:\models\llama_cpp_bin\llama-server.exe"
        self.model_path = model_path
        self.server_exe = server_exe
        self.port = port
        self.host = host
        self.base_url = f"http://{host}:{port}"
        self.context_length = context_length
        self.n_threads = n_threads
        self._process: Optional[sp.Popen] = None

    @classmethod
    def get_instance(cls) -> 'QwenServerManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _check_exe(self) -> bool:
        return os.path.exists(self.server_exe)

    def _check_model(self) -> bool:
        return os.path.exists(self.model_path)

    def health(self) -> bool:
        """检查服务器是否健康运行"""
        try:
            req = urllib.request.Request(f"{self.base_url}/health")
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read().decode())
            return data.get('status') == 'ok'
        except Exception:
            return False

    def start(self) -> bool:
        """启动 llama-server"""
        if self.health():
            return True
        if not self._check_exe():
            raise FileNotFoundError(f"llama-server 未找到: {self.server_exe}")
        if not self._check_model():
            raise FileNotFoundError(f"Qwen 模型未找到: {self.model_path}")

        env = os.environ.copy()
        env.pop('http_proxy', None)
        env.pop('https_proxy', None)
        env['GGML_CPU_OPT_DEBUG'] = '0'

        cmd = [
            self.server_exe,
            '-m', self.model_path,
            '--port', str(self.port),
            '--host', self.host,
            '-ngl', '0',
            '-c', str(self.context_length),
            '-t', str(self.n_threads),
        ]

        try:
            self._process = sp.Popen(
                cmd,
                stdout=sp.DEVNULL,
                stderr=sp.DEVNULL,
                text=True,
                env=env,
                cwd=os.path.dirname(self.server_exe),
            )
        except Exception as e:
            raise RuntimeError(f"启动 llama-server 失败: {e}")

        # 等待服务器就绪 (最多 30s)
        for _ in range(30):
            time.sleep(1)
            if self._process.poll() is not None:
                raise RuntimeError(f"llama-server 异常退出, code={self._process.returncode}")
            if self.health():
                return True
        raise TimeoutError("llama-server 启动超时")

    def stop(self):
        """停止 llama-server"""
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
        self._process = None

    def ensure_running(self) -> bool:
        if self.health():
            return True
        return self.start()

    def __del__(self):
        self.stop()


# ============================================================
#  HTTP 推理客户端
# ============================================================

class QwenHTTPClient:
    """通过 HTTP API 调用 Qwen 模型 (OpenAI-compatible completion)"""

    def __init__(self, server: QwenServerManager = None):
        self.server = server or QwenServerManager.get_instance()

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 512,
        stop: Optional[List[str]] = None,
        timeout: int = 60,
        retries: int = 2,
    ) -> str:
        """生成回复

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度 (0-2)
            max_tokens: 最大生成token数
            stop: 停止词列表
            timeout: 请求超时秒数
            retries: 重试次数

        Returns:
            生成的文本
        """
        # 构造 Qwen ChatML 格式的 prompt
        if system_prompt:
            full_prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
        else:
            full_prompt = f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"

        if stop is None:
            stop = ["<|im_end|>", "<|im_start|>"]

        payload = json.dumps({
            'prompt': full_prompt,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stop': stop,
            'stream': False,
        }).encode('utf-8')

        last_error = None
        for attempt in range(retries + 1):
            try:
                self.server.ensure_running()
                req = urllib.request.Request(
                    f"{self.server.base_url}/completion",
                    data=payload,
                    headers={'Content-Type': 'application/json'},
                )
                resp = urllib.request.urlopen(req, timeout=timeout)
                data = json.loads(resp.read().decode())
                content = data.get('content', '')
                # 如果设置了stop词, 检查是否以 stop 结束
                if stop:
                    for s in stop:
                        if content.endswith(s):
                            content = content[:-len(s)]
                            break
                return content.strip()
            except (urllib.error.URLError, ConnectionRefusedError, TimeoutError) as e:
                last_error = e
                if attempt < retries:
                    time.sleep(2 * (attempt + 1))
                    # 尝试重启服务器
                    try:
                        self.server.stop()
                        self.server.start()
                    except Exception:
                        pass

        raise RuntimeError(f"Qwen HTTP 请求失败 (已重试{retries}次): {last_error}")


# ============================================================
#  Qwen 金融预测器
# ============================================================

class QwenFinancialPredictor:
    """Qwen2.5-1.5B 金融预测器 — HTTP API 后端"""

    SYSTEM_PROMPT = "你是专业的A股量化分析师。你会根据提供的股票技术数据给出精确、量化的分析。回复简洁精准。"

    PRICE_PREDICTION_PROMPT = """分析以下A股技术数据,预测{horizon}价格走势:

股票: {name} ({code})
当前价格: {price:.2f}元
近{lookback}日走势: {trend_desc}
近5日涨跌幅: {pct5d:+.2f}%
近20日涨跌幅: {pct20d:+.2f}%
成交量变化: {vol_desc}
最高价/最低价比值: {hl_ratio:.2f}
均线: MA5={ma5:.2f}, MA10={ma10:.2f}, MA20={ma20:.2f}
RSI(14): {rsi:.1f}
波动率(20日): {volatility:.1f}%

请输出JSON:
{{
  "direction": "up/down/flat",
  "target_price": 数字,
  "confidence": 0-100,
  "risk_level": "low/medium/high",
  "key_factors": ["因素1","因素2"],
  "suggested_action": "buy/hold/sell",
  "suggested_position_pct": 0-100
}}"""

    SIGNAL_VALIDATION_PROMPT = """请验证以下Kronos模型的预测信号是否合理:

股票: {name} ({code})
当前价格: {price:.2f}
Kronos预测: {kronos_signal} (预期收益 {kronos_return:+.2f}%)
基本面判断: {fundamental}

请输出JSON验证结果:
{{
  "agreement": true/false,
  "confidence": 0-100,
  "adjusted_signal": "buy/hold/sell",
  "adjusted_return": 数字(预期收益%),
  "risk_warning": "如有风险预警,否则为空字符串",
  "reasoning": "简短理由"
}}"""

    def __init__(
        self,
        temperature: float = 0.3,
        max_tokens: int = 400,
    ):
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.server = QwenServerManager.get_instance()
        self._client: Optional[QwenHTTPClient] = None

    @property
    def client(self) -> QwenHTTPClient:
        if self._client is None:
            self._client = QwenHTTPClient(self.server)
        return self._client

    @property
    def available(self) -> bool:
        try:
            return self.server._check_model() and self.server._check_exe()
        except Exception:
            return False

    # ============================================================
    #  技术指标计算
    # ============================================================

    def _calc_indicators(self, df: pd.DataFrame) -> Dict:
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['volume'].values

        def safe_mean(arr, n):
            return float(np.mean(arr[-n:])) if len(arr) >= n else float(arr[-1])

        ma5 = safe_mean(close, 5)
        ma10 = safe_mean(close, 10)
        ma20 = safe_mean(close, 20)

        delta = np.diff(close)
        gain = np.sum(delta[delta > 0])
        loss = -np.sum(delta[delta < 0])
        n_periods = max(len(close) - 1, 1)
        avg_gain = gain / n_periods
        avg_loss = loss / n_periods
        rsi = 100 - (100 / (1 + avg_gain / max(avg_loss, 1e-9))) if avg_loss > 0 else 100

        returns = np.diff(close) / close[:-1]
        volatility = float(np.std(returns) * 100 * np.sqrt(252)) if len(returns) > 1 else 0.0

        if len(close) >= 5 and close[-5] > 0:
            pct5d = (close[-1] / close[-5] - 1) * 100
        else:
            pct5d = 0.0

        if len(close) >= 20 and close[-20] > 0:
            pct20d = (close[-1] / close[-20] - 1) * 100
        else:
            pct20d = 0.0

        if len(close) >= 5:
            if all(close[-1 - i] > close[-5 - i] for i in range(4) if close[-5 - i] > 0):
                trend_desc = "连续上涨"
            elif all(close[-1 - i] < close[-5 - i] for i in range(4) if close[-5 - i] > 0):
                trend_desc = "连续下跌"
            elif close[-1] > close[-5]:
                trend_desc = "震荡上行"
            elif close[-1] < close[-5]:
                trend_desc = "震荡下行"
            else:
                trend_desc = "横盘整理"
        else:
            trend_desc = "数据不足"

        if len(volume) >= 10:
            vol_ma5 = np.mean(volume[-5:])
            vol_ma10 = np.mean(volume[-10:])
            ratio = vol_ma5 / max(vol_ma10, 1e-9)
            if ratio > 1.5:
                vol_desc = "显著放量"
            elif ratio > 1.1:
                vol_desc = "温和放量"
            elif ratio < 0.7:
                vol_desc = "显著缩量"
            elif ratio < 0.9:
                vol_desc = "温和缩量"
            else:
                vol_desc = "平稳"
        else:
            vol_desc = "数据不足"

        hl_ratio = high[-1] / max(low[-1], 1e-9)

        return {
            'ma5': ma5, 'ma10': ma10, 'ma20': ma20,
            'rsi': rsi, 'volatility': volatility,
            'pct5d': pct5d, 'pct20d': pct20d,
            'trend_desc': trend_desc, 'vol_desc': vol_desc, 'hl_ratio': hl_ratio,
        }

    # ============================================================
    #  核心预测方法
    # ============================================================

    def predict_price(
        self, code: str, name: str, df: pd.DataFrame,
        horizon: str = "短期(1-5日)", lookback: int = 20,
    ) -> Dict:
        """Qwen 价格预测"""
        if not self.available:
            return {'error': 'Qwen模型不可用', 'signal': 'hold', 'direction': 'flat'}

        price = float(df['close'].iloc[-1])
        indicators = self._calc_indicators(df.tail(max(lookback, 30)))

        prompt = self.PRICE_PREDICTION_PROMPT.format(
            horizon=horizon, name=name, code=code,
            price=price, lookback=lookback, **indicators
        )

        try:
            response = self.client.generate(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            result = self._parse_json(response)
            result['raw_response'] = response
            return result
        except Exception as e:
            return {'error': str(e)[:100], 'signal': 'hold', 'direction': 'flat'}

    def validate_signal(
        self, code: str, name: str, df: pd.DataFrame,
        kronos_signal: str, kronos_return: float,
    ) -> Dict:
        """验证 Kronos 信号"""
        if not self.available:
            return {'agreement': True, 'adjusted_signal': kronos_signal}

        price = float(df['close'].iloc[-1])
        indicators = self._calc_indicators(df.tail(30))

        fundamental = ""
        if indicators['rsi'] > 70:
            fundamental += "RSI超买; "
        elif indicators['rsi'] < 30:
            fundamental += "RSI超卖; "
        if indicators['pct20d'] > 20:
            fundamental += "短期涨幅过大; "
        elif indicators['pct20d'] < -20:
            fundamental += "短期跌幅过大; "
        if not fundamental:
            fundamental = "技术面中性"

        prompt = self.SIGNAL_VALIDATION_PROMPT.format(
            name=name, code=code, price=price,
            kronos_signal=kronos_signal,
            kronos_return=kronos_return * 100,
            fundamental=fundamental,
        )

        try:
            response = self.client.generate(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=300,
            )
            result = self._parse_json(response)
            result['raw_response'] = response
            return result
        except Exception:
            return {'agreement': True, 'adjusted_signal': kronos_signal}

    # ============================================================
    #  融合预测
    # ============================================================

    def fused_predict(
        self, code: str, name: str, df: pd.DataFrame,
        kronos_result: Dict, weight_qwen: float = 0.4,
    ) -> Dict:
        """融合 Kronos + Qwen 预测"""
        current_price = kronos_result.get('current_price', float(df['close'].iloc[-1]))
        result = {
            'code': code, 'name': name,
            'current_price': current_price,
            'kronos_signal': kronos_result.get('signal', 'hold'),
            'kronos_return': kronos_result.get('return_pct', 0),
            'kronos_target': kronos_result.get('predicted_price', 0),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'qwen_available': self.available,
        }

        if not self.available:
            result['final_signal'] = result['kronos_signal']
            result['final_return'] = result['kronos_return']
            result['final_target'] = result['kronos_target']
            result['fusion_note'] = 'Qwen不可用,仅Kronos'
            return result

        qwen_pred = self.predict_price(code, name, df)
        qwen_validation = self.validate_signal(
            code, name, df,
            kronos_result.get('signal', 'hold'),
            kronos_result.get('return_pct', 0),
        )

        qwen_direction = qwen_pred.get('direction', 'flat')
        qwen_confidence = qwen_pred.get('confidence', 50) / 100.0

        if qwen_direction == 'up':
            qwen_return = qwen_confidence * 0.05
        elif qwen_direction == 'down':
            qwen_return = -qwen_confidence * 0.05
        else:
            qwen_return = 0.0

        if not qwen_validation.get('agreement', True):
            weight_qwen *= 0.5

        weight_kronos = 1.0 - weight_qwen
        final_return = weight_kronos * kronos_result.get('return_pct', 0) + weight_qwen * qwen_return

        adjusted_signal = qwen_validation.get('adjusted_signal', kronos_result.get('signal', 'hold'))
        if adjusted_signal == 'hold':
            final_signal = 'hold'
        elif final_return > 0.02:
            final_signal = 'buy'
        elif final_return < -0.02:
            final_signal = 'sell'
        else:
            final_signal = adjusted_signal

        final_target = current_price * (1 + final_return)

        result.update({
            'qwen_signal': qwen_pred.get('suggested_action', 'hold'),
            'qwen_direction': qwen_direction,
            'qwen_confidence': qwen_confidence,
            'qwen_return': qwen_return,
            'validation_agreement': qwen_validation.get('agreement', True),
            'risk_warning': qwen_validation.get('risk_warning', ''),
            'final_signal': final_signal,
            'final_return': float(final_return),
            'final_target': float(final_target),
            'fusion_weights': {'kronos': weight_kronos, 'qwen': weight_qwen},
            'fusion_note': 'Kronos+Qwen融合预测',
        })
        return result

    # ============================================================
    #  JSON 解析
    # ============================================================

    def _parse_json(self, text: str) -> Dict:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        import re
        for pattern in [r'```json\s*(\{.*?\})\s*```', r'```\s*(\{.*?\})\s*```']:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

        brace_start = text.find('{')
        if brace_start >= 0:
            depth = 0
            for i in range(brace_start, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[brace_start:i+1])
                        except json.JSONDecodeError:
                            break
        return {'error': '无法解析JSON', 'direction': 'flat', 'confidence': 40}


# ============================================================
#  单例
# ============================================================

_qwen_predictor: Optional[QwenFinancialPredictor] = None


def get_qwen_predictor() -> QwenFinancialPredictor:
    global _qwen_predictor
    if _qwen_predictor is None:
        _qwen_predictor = QwenFinancialPredictor()
    return _qwen_predictor


def qwen_available() -> bool:
    return get_qwen_predictor().available


# ============================================================
#  测试
# ============================================================

if __name__ == "__main__":
    print(f"Qwen 模型可用: {qwen_available()}")
    print(f"模型路径: {QwenServerManager.get_instance().model_path}")
    print(f"模型文件大小: {os.path.getsize(QwenServerManager.get_instance().model_path)/1e9:.2f} GB")

    predictor = get_qwen_predictor()
    if predictor.available:
        # 测试推理
        np.random.seed(42)
        n = 30
        price = 40.0
        closes = [price * np.prod(1 + np.random.normal(0.0005, 0.02, n)) for _ in range(1)]
        closes = [price]
        for i in range(n - 1):
            closes.append(closes[-1] * (1 + np.random.normal(0.0005, 0.02)))
        df = pd.DataFrame({
            'timestamp': pd.date_range('2026-05-01', periods=n, freq='B'),
            'open': np.array(closes) * np.random.uniform(0.98, 1.0, n),
            'high': np.array(closes) * np.random.uniform(1.0, 1.05, n),
            'low': np.array(closes) * np.random.uniform(0.95, 1.0, n),
            'close': closes,
            'volume': np.random.uniform(1e7, 5e7, n),
        })

        kronos_fake = {
            'signal': 'buy', 'return_pct': 0.035,
            'current_price': closes[-1],
            'predicted_price': closes[-1] * 1.035,
        }

        print("\n执行融合预测...")
        result = predictor.fused_predict('601088', '中国神华', df, kronos_fake)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
