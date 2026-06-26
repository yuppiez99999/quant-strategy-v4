# -*- coding: utf-8 -*-
"""预测信号桥接器 — 将 TrendCast Pro 预测信号接入量化策略调仓

数据来源: 22_auto_金融市场预测模型 的 PredictionEngine
接入方式: 预测方向(涨/跌) + 置信度 → 调整目标权重 → 再平衡

信号逻辑:
  - 预测看涨 + 高置信度 → 增持（权重 × 信号倍数）
  - 预测看跌 + 高置信度 → 减持（权重 × (1-信号倍数)）
  - 置信度低 → 维持原权重（信号中性）

支持两种接入模式:
  1. 实时模式: 调用 PredictionEngine 实时预测（需要模型已训练）
  2. 离线模式: 从 JSON 文件加载预先生成的预测信号
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

# 预测模型项目路径
PREDICTION_MODEL_DIR = Path(__file__).parent.parent.parent / "22_auto_金融市场预测模型"


class PredictionSignalBridge:
    """预测信号桥接器 — TrendCast Pro → 量化策略"""

    def __init__(
        self,
        model_config_path: str | None = None,
        signal_file: str | None = None,
        signal_weight: float = 0.3,
        min_confidence: float = 0.55,
        horizon: str = "mid_term",
    ):
        """
        Args:
            model_config_path: 预测模型配置文件路径（实时模式）
            signal_file: 预信号 JSON 文件路径（离线模式，优先于实时模式）
            signal_weight: 信号对权重的最大影响比例（0.3=最多调整30%）
            min_confidence: 最小置信度阈值，低于此值不调整
            horizon: 使用哪个周期的预测（short_term/mid_term/long_term）
        """
        self.signal_weight = signal_weight
        self.min_confidence = min_confidence
        self.horizon = horizon
        self.signal_file = signal_file
        self._engine = None
        self._signals_cache: Dict[str, dict] = {}

        # 离线模式：加载信号文件
        if signal_file and os.path.exists(signal_file):
            self._load_signal_file(signal_file)
            logger.info(f"预测信号桥接器（离线模式）: 已加载 {len(self._signals_cache)} 个信号")
        elif model_config_path:
            # 实时模式：初始化预测引擎
            self._init_engine(model_config_path)
        else:
            # 默认：尝试自动发现
            self._auto_init()

    def _auto_init(self):
        """自动发现预测模型并初始化"""
        pro_config = PREDICTION_MODEL_DIR / "configs" / "config_pro.yaml"
        std_config = PREDICTION_MODEL_DIR / "configs" / "config.yaml"
        config_path = str(pro_config) if pro_config.exists() else str(std_config)
        self._init_engine(config_path)

    def _init_engine(self, config_path: str):
        """初始化预测引擎（实时模式）"""
        try:
            # 将预测模型目录加入 sys.path
            if str(PREDICTION_MODEL_DIR) not in sys.path:
                sys.path.insert(0, str(PREDICTION_MODEL_DIR))

            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            # 切换工作目录到预测模型项目，使相对路径（models/、data/）生效
            original_cwd = os.getcwd()
            os.chdir(str(PREDICTION_MODEL_DIR))

            from src.inference.predictor import PredictionEngine

            self._engine = PredictionEngine(config)
            model_type = config["model"]["type"]
            self._engine.load_models(model_type)

            # 恢复原工作目录
            os.chdir(original_cwd)

            logger.info(f"预测信号桥接器（实时模式）: 已加载 {model_type} 模型")
        except Exception as e:
            logger.warning(f"预测引擎初始化失败，信号桥接器降级为中性: {e}")
            self._engine = None

    def _load_signal_file(self, filepath: str):
        """从 JSON 文件加载预生成的预测信号"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 支持两种格式：单标的 dict 或 多标的 list
        if isinstance(data, list):
            for item in data:
                symbol = item.get("symbol", "")
                self._signals_cache[symbol] = item
        elif isinstance(data, dict) and "predictions" in data:
            symbol = data.get("symbol", "")
            for h, pred in data["predictions"].items():
                if h == self.horizon and "error" not in pred:
                    self._signals_cache[symbol] = pred
        elif isinstance(data, dict):
            symbol = data.get("symbol", "")
            self._signals_cache[symbol] = data

    def get_signal(self, code: str, name: str = "") -> dict[str, Any]:
        """获取单个标的的预测信号

        Args:
            code: 标的代码（如 "600519" 或 "600519.SH"）
            name: 标的名称（用于日志）

        Returns:
            {
                "direction": "bullish"/"bearish"/"neutral",
                "confidence": float,  # 0-1
                "signal_factor": float,  # 权重调整因子 0.7-1.3
                "source": "realtime"/"offline"/"neutral",
            }
        """
        # 标准化代码：去掉交易所后缀
        code_clean = code.replace(".SH", "").replace(".SZ", "").replace(".SHF", "")

        # 离线模式：从缓存查找
        for key, signal in self._signals_cache.items():
            if code_clean in key or key in code_clean:
                return self._parse_signal(signal, "offline")

        # 实时模式：调用预测引擎
        if self._engine:
            try:
                # 转换为 Wind 代码格式
                if code_clean.startswith("6"):
                    wind_code = f"{code_clean}.SH"
                elif code_clean.startswith(("0", "3")):
                    wind_code = f"{code_clean}.SZ"
                else:
                    wind_code = code_clean

                # 切换到预测模型目录（相对路径）
                original_cwd = os.getcwd()
                os.chdir(str(PREDICTION_MODEL_DIR))
                try:
                    result = self._engine.predict(wind_code, self.horizon)
                finally:
                    os.chdir(original_cwd)

                if "error" not in result:
                    return self._parse_signal(result, "realtime")
            except Exception as e:
                logger.debug(f"实时预测 {code} 失败: {e}")

        # 无信号：返回中性
        return {
            "direction": "neutral",
            "confidence": 0.5,
            "signal_factor": 1.0,
            "source": "neutral",
        }

    def _parse_signal(self, signal: dict, source: str) -> dict[str, Any]:
        """解析预测信号为标准化格式"""
        direction_raw = signal.get("direction", "")
        confidence = signal.get("confidence", 0.5)
        probability = signal.get("probability", 0.5)

        # 方向映射
        if "涨" in direction_raw:
            direction = "bullish"
        elif "跌" in direction_raw:
            direction = "bearish"
        else:
            direction = "neutral"

        # 计算信号因子（权重调整倍数）
        if confidence < self.min_confidence or direction == "neutral":
            signal_factor = 1.0  # 中性：不调整
        elif direction == "bullish":
            # 看涨：权重提升（最多 +signal_weight）
            boost = self.signal_weight * (confidence - self.min_confidence) / (1 - self.min_confidence)
            signal_factor = 1.0 + boost
        else:
            # 看跌：权重降低（最多 -signal_weight）
            cut = self.signal_weight * (confidence - self.min_confidence) / (1 - self.min_confidence)
            signal_factor = 1.0 - cut

        signal_factor = round(signal_factor, 4)

        return {
            "direction": direction,
            "confidence": round(confidence, 4),
            "probability": round(probability, 4),
            "signal_factor": signal_factor,
            "source": source,
        }

    def adjust_weights(
        self,
        base_weights: dict[str, float],
        codes: list[str],
        names: dict[str, str] | None = None,
    ) -> dict[str, dict]:
        """根据预测信号调整目标权重

        Args:
            base_weights: 原始目标权重 {code: weight}
            codes: 标的代码列表
            names: 标的名称映射 {code: name}

        Returns:
            {
                "adjusted_weights": {code: new_weight},
                "signals": {code: signal_dict},
                "total_adjustment": float,
            }
        """
        names = names or {}
        adjusted_weights = {}
        signals = {}
        adjustments = []

        for code in codes:
            if code == "CASH":
                adjusted_weights[code] = base_weights.get(code, 0)
                continue

            signal = self.get_signal(code, names.get(code, ""))
            signals[code] = signal

            base_w = base_weights.get(code, 0)
            adjusted_w = base_w * signal["signal_factor"]
            adjusted_weights[code] = adjusted_w

            if signal["signal_factor"] != 1.0:
                adjustments.append({
                    "code": code,
                    "name": names.get(code, code),
                    "base_weight": round(base_w, 4),
                    "adjusted_weight": round(adjusted_w, 4),
                    "direction": signal["direction"],
                    "confidence": signal["confidence"],
                    "factor": signal["signal_factor"],
                })

        # 归一化：确保权重总和不变（将调整差额分配到 CASH）
        total_base = sum(base_weights.get(c, 0) for c in codes if c != "CASH")
        total_adjusted = sum(adjusted_weights.get(c, 0) for c in codes if c != "CASH")
        diff = total_base - total_adjusted

        if "CASH" in adjusted_weights:
            adjusted_weights["CASH"] = base_weights.get("CASH", 0) + diff
        else:
            # 无现金项：等比缩放回原总权重
            if total_adjusted > 0:
                scale = total_base / total_adjusted
                for c in codes:
                    if c != "CASH":
                        adjusted_weights[c] *= scale

        logger.info(
            f"信号调仓完成: {len(adjustments)} 个标的调整, "
            f"现金变动={diff:+.4f}"
        )

        return {
            "adjusted_weights": adjusted_weights,
            "signals": signals,
            "adjustments": adjustments,
            "cash_change": round(diff, 4),
        }

    def batch_predict_to_file(
        self,
        codes: list[str],
        output_path: str,
        horizon: str = "mid_term",
    ):
        """批量预测并保存为信号文件（供离线模式使用）

        Args:
            codes: 标的代码列表
            output_path: 输出 JSON 文件路径
            horizon: 预测周期
        """
        if not self._engine:
            raise RuntimeError("预测引擎未初始化，无法批量预测")

        results = []
        for code in codes:
            # 转换代码格式
            code_clean = code.replace(".SH", "").replace(".SZ", "")
            if code_clean.startswith("6"):
                wind_code = f"{code_clean}.SH"
            elif code_clean.startswith(("0", "3")):
                wind_code = f"{code_clean}.SZ"
            else:
                wind_code = code

            try:
                pred = self._engine.predict(wind_code, horizon)
                pred["symbol"] = wind_code
                results.append(pred)
                logger.info(f"  {code}: {pred.get('direction', '?')} ({pred.get('confidence', 0):.1%})")
            except Exception as e:
                logger.warning(f"  {code} 预测失败: {e}")
                results.append({"symbol": wind_code, "error": str(e)})

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"已保存 {len(results)} 个预测信号到 {output_path}")
        return results


def integrate_with_trading_engine(trading_engine, bridge: PredictionSignalBridge):
    """将信号桥接器集成到 TradingEngine（monkey-patch rebalance 方法）

    用法:
        from quant_modules.prediction_bridge import PredictionSignalBridge, integrate_with_trading_engine
        bridge = PredictionSignalBridge()
        engine = TradingEngine()
        integrate_with_trading_engine(engine, bridge)
        engine.run_backtest()  # 现在会自动根据预测信号调仓
    """
    original_rebalance = trading_engine.rebalance

    def signal_enhanced_rebalance(prices, date):
        """带预测信号的再平衡"""
        # 1. 获取预测信号调整权重
        result = bridge.adjust_weights(
            base_weights=trading_engine.target_weights,
            codes=trading_engine.codes,
            names=trading_engine.names,
        )

        # 2. 临时替换目标权重
        original_weights = trading_engine.target_weights.copy()
        trading_engine.target_weights = result["adjusted_weights"]

        # 3. 打印信号调仓信息
        for adj in result.get("adjustments", []):
            icon = "📈" if adj["direction"] == "bullish" else "📉"
            print(
                f"  {icon} {adj['name']}: {adj['base_weight']:.1%} → {adj['adjusted_weight']:.1%} "
                f"({adj['direction']}, 置信度={adj['confidence']:.1%})"
            )

        # 4. 执行原始再平衡
        original_rebalance(prices, date)

        # 5. 恢复原始权重（避免累积偏移）
        trading_engine.target_weights = original_weights

    trading_engine.rebalance = signal_enhanced_rebalance
    logger.info("预测信号桥接器已集成到 TradingEngine")
    return trading_engine
