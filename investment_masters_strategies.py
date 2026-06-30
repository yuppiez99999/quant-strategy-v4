"""
投资大师策略模块
包含四位著名投资大师的理论策略实现：
- Benjamin Graham: 价值投资策略
- Warren Buffett: 护城河策略  
- Peter Lynch: PEG增长策略
- Philip Fisher: 质量增长策略
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum


class ConvictionLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SignalType(Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


@dataclass
class InvestmentSignal:
    """投资信号数据类"""
    ticker: str
    signal_type: SignalType
    score: float  # 0.0-1.0
    conviction: ConvictionLevel
    strategy: str
    reason: str
    metadata: Dict = None


class BaseInvestmentMaster(ABC):
    """投资大师策略基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        
    @abstractmethod
    def analyze_stock(self, ticker: str, data: Dict) -> InvestmentSignal:
        """分析个股并返回投资信号"""
        pass
    
    @abstractmethod
    def calculate_score(self, data: Dict) -> float:
        """计算策略得分"""
        pass


class GrahamValueStrategy(BaseInvestmentMaster):
    """
    Benjamin Graham 价值投资策略
    基于深度价值分析、PE、PEG、PB比率、安全边际、内在价值计算
    """
    
    def __init__(self):
        super().__init__(
            "GrahamValueStrategy", 
            "Benjamin Graham深度价值投资策略"
        )
        self.min_pe = 0
        self.max_pe = 15
        self.min_pb = 0
        self.max_pb = 3
        self.min_div_yield = 0.02
        self.margin_of_safety_ratio = 0.7
        
    def analyze_stock(self, ticker: str, data: Dict) -> InvestmentSignal:
        """分析价值投资信号"""
        score = self.calculate_score(data)
        
        # 判断信号类型
        if score >= 0.7:
            signal_type = SignalType.BUY
            conviction = ConvictionLevel.HIGH
        elif score >= 0.4:
            signal_type = SignalType.HOLD
            conviction = ConvictionLevel.MEDIUM
        else:
            signal_type = SignalType.SELL
            conviction = ConvictionLevel.LOW
            
        reason = self._generate_reason(data, score)
        
        return InvestmentSignal(
            ticker=ticker,
            signal_type=signal_type,
            score=score,
            conviction=conviction,
            strategy=self.name,
            reason=reason,
            metadata=self._extract_metadata(data)
        )
    
    def calculate_score(self, data: Dict) -> float:
        """计算价值投资得分"""
        score = 0.0
        factors = 0
        
        # PE比率分析
        if 'pe_ratio' in data and data['pe_ratio']:
            pe = float(data['pe_ratio'])
            if pe <= self.max_pe:
                pe_score = max(0, (self.max_pe - pe) / self.max_pe)
                score += pe_score * 0.3
            factors += 1
        
        # PB比率分析  
        if 'pb_ratio' in data and data['pb_ratio']:
            pb = float(data['pb_ratio'])
            if pb <= self.max_pb:
                pb_score = max(0, (self.max_pb - pb) / self.max_pb)
                score += pb_score * 0.25
            factors += 1
        
        # 股息收益率分析
        if 'dividend_yield' in data and data['dividend_yield']:
            div_yield = float(data['dividend_yield'])
            if div_yield >= self.min_div_yield:
                div_score = min(1.0, div_yield / self.min_div_yield)
                score += div_score * 0.25
            factors += 1
        
        # PEG比率分析
        if 'peg_ratio' in data and data['peg_ratio'] and 'growth_rate' in data:
            peg = float(data['peg_ratio'])
            growth_rate = float(data['growth_rate'])
            if peg <= 1.5 and growth_rate > 0:
                peg_score = max(0, (1.5 - peg) / 1.5)
                score += peg_score * 0.2
            factors += 1
        
        # ROE分析
        if 'roe' in data and data['roe']:
            roe = float(data['roe'])
            if roe > 0.1:  # ROE > 10%
                roe_score = min(1.0, roe / 0.3)
                score += roe_score * 0.15
            factors += 1
        
        # 安全边际计算
        if 'intrinsic_value' in data and data['intrinsic_value'] and 'current_price' in data:
            intrinsic_value = float(data['intrinsic_value'])
            current_price = float(data['current_price'])
            margin = (intrinsic_value - current_price) / intrinsic_value
            if margin > 0:
                margin_score = min(1.0, margin / self.margin_of_safety_ratio)
                score += margin_score * 0.1
            factors += 1
        
        # 标准化得分
        if factors > 0:
            score = min(1.0, score / factors)
            
        return score
    
    def _generate_reason(self, data: Dict, score: float) -> str:
        """生成投资理由"""
        reasons = []
        
        if 'pe_ratio' in data and data['pe_ratio']:
            pe = float(data['pe_ratio'])
            if pe <= 10:
                reasons.append(f"PE比率{pe:.1f}较低，具有价值优势")
            elif pe <= 15:
                reasons.append(f"PE比率{pe:.1f}适中，处于合理估值区间")
        
        if 'pb_ratio' in data and data['pb_ratio']:
            pb = float(data['pb_ratio'])
            if pb <= 2:
                reasons.append(f"PB比率{pb:.1f}显示资产价值良好")
        
        if 'dividend_yield' in data and data['dividend_yield']:
            div_yield = float(data['dividend_yield'])
            if div_yield >= 0.03:
                reasons.append(f"股息收益率{div_yield:.1%}提供稳定现金流")
        
        if 'intrinsic_value' in data and data['intrinsic_value'] and 'current_price' in data:
            intrinsic_value = float(data['intrinsic_value'])
            current_price = float(data['current_price'])
            if intrinsic_value > current_price:
                margin = (intrinsic_value - current_price) / intrinsic_value * 100
                reasons.append(f"当前价格{current_price:.1f}低于内在价值{intrinsic_value:.1f}，安全边际{margin:.1f}%")
        
        return "；".join(reasons) if reasons else "价值因素中性"
    
    def _extract_metadata(self, data: Dict) -> Dict:
        """提取相关元数据"""
        metadata = {}
        key_fields = ['pe_ratio', 'pb_ratio', 'dividend_yield', 'peg_ratio', 
                     'roe', 'growth_rate', 'intrinsic_value', 'current_price']
        
        for field in key_fields:
            if field in data and data[field]:
                metadata[field] = float(data[field])
                
        return metadata


class BuffettMungerStrategy(BaseInvestmentMaster):
    """
    Warren Buffett护城河策略
    基于经济护城河、竞争优势、财务强度分析
    """
    
    def __init__(self):
        super().__init__(
            "BuffettMungerStrategy",
            "Warren Buffett护城河投资策略"
        )
        
    def analyze_stock(self, ticker: str, data: Dict) -> InvestmentSignal:
        """分析护城河投资信号"""
        score = self.calculate_score(data)
        
        if score >= 0.75:
            signal_type = SignalType.BUY
            conviction = ConvictionLevel.HIGH
        elif score >= 0.5:
            signal_type = SignalType.HOLD
            conviction = ConvictionLevel.MEDIUM
        else:
            signal_type = SignalType.SELL
            conviction = ConvictionLevel.LOW
            
        reason = self._generate_reason(data, score)
        
        return InvestmentSignal(
            ticker=ticker,
            signal_type=signal_type,
            score=score,
            conviction=conviction,
            strategy=self.name,
            reason=reason,
            metadata=self._extract_metadata(data)
        )
    
    def calculate_score(self, data: Dict) -> float:
        """计算护城河得分"""
        score = 0.0
        factors = 0
        
        # 品牌价值分析
        if 'brand_strength' in data and data['brand_strength']:
            brand_score = float(data['brand_strength'])
            score += brand_score * 0.2
            factors += 1
        
        # 转换成本分析
        if 'switching_costs' in data and data['switching_costs']:
            switch_score = float(data['switching_costs'])
            score += switch_score * 0.2
            factors += 1
        
        # 网络效应
