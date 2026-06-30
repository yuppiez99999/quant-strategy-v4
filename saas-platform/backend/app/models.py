"""Pydantic models for QuantMatrix SaaS API"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SectorType(str, Enum):
    TECH_MANUFACTURING = "tech_manufacturing"
    PROCYCLICAL = "procyclical"
    RESOURCES = "resources"
    DEFENSIVE = "defensive"


class SignalType(str, Enum):
    STRONG_INFLOW = "strong_inflow"
    INFLOW = "inflow"
    NEUTRAL = "neutral"
    OUTFLOW = "outflow"
    STRONG_OUTFLOW = "strong_outflow"


class ActionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


# Auth
class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    company: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    company: str
    plan: PlanType


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Portfolio
class PortfolioAsset(BaseModel):
    symbol: str
    name: str
    sector: SectorType
    weight: float
    current_weight: float
    price: float
    change: float
    change_percent: float
    value: float
    shares: int


class PortfolioSummary(BaseModel):
    total_value: float
    total_change: float
    total_change_percent: float
    daily_pl: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float


class RiskMetrics(BaseModel):
    var95: float
    var99: float
    cvar: float
    beta: float
    correlation: float
    stop_loss_triggers: int


# Market Analysis
class SectorAllocation(BaseModel):
    sector: str
    recommended_weight: float
    current_weight: float
    signal: str


class KondratievSignal(BaseModel):
    phase: str
    phase_label: str
    confidence: float
    description: str
    sector_allocation: List[SectorAllocation]
    commodity_signal: str


class FiveYearPlanAlignment(BaseModel):
    direction: str
    weight: float
    score: float
    holding_count: int
    description: str


class MacroSnapshot(BaseModel):
    pmi: float
    pmi_change: float
    cpi: float
    cpi_change: float
    gdp: float
    gdp_change: float
    m2: float
    m2_change: float
    social_finance: float
    social_finance_change: float


# ETF
class ETFFlowData(BaseModel):
    etf_code: str
    etf_name: str
    style: SectorType
    net_inflow: float
    net_inflow_percent: float
    total_asset: float
    signal: SignalType


# AI Analysis
class AnalystSignal(BaseModel):
    analyst: str
    action: ActionType
    confidence: float
    reasoning: str


class AIAnalysisResult(BaseModel):
    ticker: str
    ticker_name: str
    overall_score: float
    signals: List[AnalystSignal]
    summary: str
    timestamp: str


# Reports
class ReportResponse(BaseModel):
    id: str
    title: str
    type: str
    date: str
    summary: str
    url: str


# Generic
class StatusResponse(BaseModel):
    status: str
    message: str
    timestamp: str
