export interface User {
  id: string;
  email: string;
  name: string;
  company: string;
  plan: 'free' | 'pro' | 'enterprise';
  avatar?: string;
}

export interface PortfolioAsset {
  symbol: string;
  name: string;
  sector: 'tech_manufacturing' | 'procyclical' | 'resources' | 'defensive';
  weight: number;
  currentWeight: number;
  price: number;
  change: number;
  changePercent: number;
  value: number;
  shares: number;
}

export interface PortfolioSummary {
  totalValue: number;
  totalChange: number;
  totalChangePercent: number;
  dailyPL: number;
  totalReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
  volatility: number;
}

export interface KondratievSignal {
  phase: 'recession' | 'recovery' | 'prosperity' | 'stagflation';
  phaseLabel: string;
  confidence: number;
  description: string;
  sectorAllocation: SectorAllocation[];
  commoditySignal: 'bullish' | 'bearish' | 'neutral';
}

export interface SectorAllocation {
  sector: string;
  recommendedWeight: number;
  currentWeight: number;
  signal: 'overweight' | 'underweight' | 'neutral';
}

export interface FiveYearPlanAlignment {
  direction: string;
  weight: number;
  score: number;
  holdingCount: number;
  description: string;
}

export interface ETFFlowData {
  etfCode: string;
  etfName: string;
  style: 'procyclical' | 'tech_manufacturing' | 'resources' | 'defensive';
  netInflow: number;
  netInflowPercent: number;
  totalAsset: number;
  signal: 'strong_inflow' | 'inflow' | 'neutral' | 'outflow' | 'strong_outflow';
}

export interface AIAnalysisResult {
  ticker: string;
  tickerName: string;
  overallScore: number;
  signals: AnalystSignal[];
  summary: string;
  timestamp: string;
}

export interface AnalystSignal {
  analyst: string;
  action: 'buy' | 'sell' | 'hold';
  confidence: number;
  reasoning: string;
}

export interface MacroSnapshot {
  pmi: number;
  pmiChange: number;
  cpi: number;
  cpiChange: number;
  gdp: number;
  gdpChange: number;
  m2: number;
  m2Change: number;
  socialFinance: number;
  socialFinanceChange: number;
}

export interface RiskMetrics {
  var95: number;
  var99: number;
  cvar: number;
  beta: number;
  correlation: number;
  stopLossTriggers: number;
}

export interface Report {
  id: string;
  title: string;
  type: 'daily' | 'weekly' | 'monthly' | 'custom';
  date: string;
  summary: string;
  url: string;
}

export interface SubscriptionPlan {
  id: string;
  name: string;
  price: number;
  period: 'monthly' | 'yearly';
  features: string[];
  highlighted: boolean;
}
