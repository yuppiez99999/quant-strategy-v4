import type { PortfolioAsset, PortfolioSummary, KondratievSignal, FiveYearPlanAlignment, ETFFlowData, AIAnalysisResult, MacroSnapshot, RiskMetrics, Report, SubscriptionPlan } from '@/types';

export const mockPortfolio: PortfolioAsset[] = [
  { symbol: '300308', name: '中际旭创', sector: 'tech_manufacturing', weight: 10, currentWeight: 10.8, price: 156.42, change: 3.28, changePercent: 2.14, value: 108000, shares: 690 },
  { symbol: '688041', name: '海光信息', sector: 'tech_manufacturing', weight: 8, currentWeight: 8.3, price: 87.15, change: -1.22, changePercent: -1.38, value: 83000, shares: 952 },
  { symbol: '002371', name: '北方华创', sector: 'tech_manufacturing', weight: 8, currentWeight: 7.6, price: 342.8, change: 5.6, changePercent: 1.66, value: 76000, shares: 221 },
  { symbol: '688981', name: '中芯国际', sector: 'tech_manufacturing', weight: 7, currentWeight: 6.8, price: 48.22, change: -0.56, changePercent: -1.15, value: 68000, shares: 1410 },
  { symbol: '300750', name: '宁德时代', sector: 'tech_manufacturing', weight: 7, currentWeight: 7.4, price: 228.5, change: 4.2, changePercent: 1.87, value: 74000, shares: 324 },
  { symbol: '000425', name: '徐工机械', sector: 'tech_manufacturing', weight: 5, currentWeight: 4.8, price: 7.83, change: 0.12, changePercent: 1.56, value: 48000, shares: 6130 },
  { symbol: '601088', name: '中国神华', sector: 'procyclical', weight: 10, currentWeight: 10.5, price: 37.56, change: -0.44, changePercent: -1.16, value: 105000, shares: 2795 },
  { symbol: '600219', name: '南山铝业', sector: 'procyclical', weight: 5, currentWeight: 5.2, price: 4.68, change: 0.08, changePercent: 1.74, value: 52000, shares: 11111 },
  { symbol: '600019', name: '宝钢股份', sector: 'procyclical', weight: 5, currentWeight: 4.7, price: 6.82, change: -0.13, changePercent: -1.87, value: 47000, shares: 6891 },
  { symbol: '518880', name: '华安黄金ETF', sector: 'resources', weight: 12, currentWeight: 12.3, price: 5.42, change: 0.06, changePercent: 1.12, value: 123000, shares: 22694 },
  { symbol: '000408', name: '藏格矿业', sector: 'resources', weight: 8, currentWeight: 7.5, price: 28.15, change: -0.85, changePercent: -2.93, value: 75000, shares: 2664 },
  { symbol: '600276', name: '恒瑞医药', sector: 'defensive', weight: 6, currentWeight: 6.1, price: 43.28, change: 0.92, changePercent: 2.17, value: 61000, shares: 1409 },
  { symbol: '603259', name: '药明康德', sector: 'defensive', weight: 5, currentWeight: 5.5, price: 62.15, change: 1.35, changePercent: 2.22, value: 55000, shares: 885 },
  { symbol: '002422', name: '科伦药业', sector: 'defensive', weight: 4, currentWeight: 4.2, price: 28.9, change: 0.35, changePercent: 1.23, value: 42000, shares: 1453 },
];

export const mockSummary: PortfolioSummary = {
  totalValue: 1017000,
  totalChange: 17000,
  totalChangePercent: 1.70,
  dailyPL: 12400,
  totalReturn: 12.8,
  sharpeRatio: 1.86,
  maxDrawdown: -8.2,
  volatility: 14.5,
};

export const mockKondratiev: KondratievSignal = {
  phase: 'recovery',
  phaseLabel: '复苏期',
  confidence: 78,
  description: '第六轮康波周期（AI/算力驱动）处于复苏向繁荣过渡阶段。AI基础设施建设加速，算力需求爆发式增长，半导体周期触底回升。十五五规划政策红利持续释放，新质生产力成为核心主线。建议超配高端制造与算力赛道，适当配置顺周期资源品，防御板块维持标配。',
  sectorAllocation: [
    { sector: '高端制造(含算力)', recommendedWeight: 45, currentWeight: 44.7, signal: 'overweight' },
    { sector: '顺周期', recommendedWeight: 20, currentWeight: 20.4, signal: 'neutral' },
    { sector: '资源', recommendedWeight: 20, currentWeight: 19.8, signal: 'neutral' },
    { sector: '防御', recommendedWeight: 15, currentWeight: 15.8, signal: 'underweight' },
  ],
  commoditySignal: 'bullish',
};

export const mockFiveYearPlan: FiveYearPlanAlignment[] = [
  { direction: '新质生产力', weight: 25, score: 92, holdingCount: 4, description: '算力基础设施、半导体设备、光模块等核心标的高度契合新质生产力方向' },
  { direction: '制造强国', weight: 20, score: 85, holdingCount: 3, description: '高端装备、精密制造龙头全面覆盖制造强国战略要求' },
  { direction: '数字中国', weight: 15, score: 88, holdingCount: 3, description: 'AI芯片、数据中心相关标的与数字经济战略高度一致' },
  { direction: '绿色低碳', weight: 12, score: 72, holdingCount: 2, description: '新能源电池龙头匹配碳中和目标，铝业龙头受益于绿色转型' },
  { direction: '健康中国', weight: 10, score: 78, holdingCount: 3, description: '创新药、CXO龙头受益于医疗健康产业升级' },
  { direction: '安全发展', weight: 10, score: 65, holdingCount: 1, description: '半导体自主可控标的覆盖供应链安全方向' },
  { direction: '乡村振兴', weight: 8, score: 40, holdingCount: 0, description: '持仓中暂无直接匹配乡村振兴方向的标的' },
];

export const mockETFData: ETFFlowData[] = [
  { etfCode: '510050', etfName: '上证50ETF', style: 'procyclical', netInflow: 2.85, netInflowPercent: 1.2, totalAsset: 238500, signal: 'strong_inflow' },
  { etfCode: '510300', etfName: '沪深300ETF', style: 'tech_manufacturing', netInflow: 5.62, netInflowPercent: 1.8, totalAsset: 312800, signal: 'strong_inflow' },
  { etfCode: '159915', etfName: '创业板ETF', style: 'tech_manufacturing', netInflow: -1.24, netInflowPercent: -0.8, totalAsset: 155600, signal: 'outflow' },
  { etfCode: '512880', etfName: '证券ETF', style: 'procyclical', netInflow: 0.85, netInflowPercent: 0.5, totalAsset: 168200, signal: 'inflow' },
  { etfCode: '512480', etfName: '半导体ETF', style: 'tech_manufacturing', netInflow: 3.45, netInflowPercent: 2.1, totalAsset: 164500, signal: 'strong_inflow' },
  { etfCode: '159941', etfName: '纳指ETF', style: 'tech_manufacturing', netInflow: 1.12, netInflowPercent: 0.9, totalAsset: 124300, signal: 'inflow' },
  { etfCode: '518880', etfName: '黄金ETF', style: 'resources', netInflow: 2.38, netInflowPercent: 1.5, totalAsset: 158900, signal: 'strong_inflow' },
  { etfCode: '159865', etfName: '养殖ETF', style: 'procyclical', netInflow: -0.45, netInflowPercent: -0.4, totalAsset: 115600, signal: 'neutral' },
  { etfCode: '512100', etfName: '中证1000ETF', style: 'tech_manufacturing', netInflow: 0.98, netInflowPercent: 0.6, totalAsset: 162300, signal: 'inflow' },
  { etfCode: '159845', etfName: '中证1000ETF', style: 'tech_manufacturing', netInflow: 0.76, netInflowPercent: 0.5, totalAsset: 152400, signal: 'inflow' },
  { etfCode: '510880', etfName: '红利ETF', style: 'procyclical', netInflow: 1.55, netInflowPercent: 1.1, totalAsset: 141200, signal: 'strong_inflow' },
  { etfCode: '159928', etfName: '消费ETF', style: 'defensive', netInflow: -0.92, netInflowPercent: -0.7, totalAsset: 131500, signal: 'outflow' },
  { etfCode: '512690', etfName: '酒ETF', style: 'defensive', netInflow: -1.56, netInflowPercent: -1.2, totalAsset: 128900, signal: 'strong_outflow' },
  { etfCode: '159766', etfName: '旅游ETF', style: 'procyclical', netInflow: -0.32, netInflowPercent: -0.3, totalAsset: 98400, signal: 'neutral' },
  { etfCode: '512010', etfName: '医药ETF', style: 'defensive', netInflow: 1.78, netInflowPercent: 1.3, totalAsset: 136700, signal: 'strong_inflow' },
  { etfCode: '159606', etfName: 'A50ETF', style: 'procyclical', netInflow: 2.15, netInflowPercent: 1.4, totalAsset: 153800, signal: 'strong_inflow' },
];

export const mockAIAnalysis: AIAnalysisResult[] = [
  {
    ticker: '300308', tickerName: '中际旭创', overallScore: 8.5,
    signals: [
      { analyst: '巴菲特', action: 'buy', confidence: 75, reasoning: '光模块龙头地位稳固，AI算力需求驱动业绩持续高增，净资产收益率优秀' },
      { analyst: '彼得林奇', action: 'buy', confidence: 85, reasoning: 'PEG比率极具吸引力，800G/1.6T光模块进入放量期，成长性确定' },
      { analyst: '达摩达兰', action: 'buy', confidence: 80, reasoning: 'DCF估值模型显示当前价格处于合理偏低区间，技术壁垒带来超额收益' },
      { analyst: '德鲁肯米勒', action: 'buy', confidence: 90, reasoning: 'AI基础设施建设周期确定性最强标的，宏观流动性宽松背景利好成长股' },
    ],
    summary: '中际旭创作为光模块赛道绝对龙头，在AI算力大爆发背景下确定性极高。多位分析师一致看多，建议维持现有仓位。',
    timestamp: '2026-06-28T09:30:00',
  },
  {
    ticker: '688041', tickerName: '海光信息', overallScore: 7.8,
    signals: [
      { analyst: '木头姐', action: 'buy', confidence: 88, reasoning: 'GPU国产替代核心标的，信创和AI算力双重催化，颠覆性创新潜力巨大' },
      { analyst: '巴菲特', action: 'hold', confidence: 60, reasoning: '估值偏高，虽然赛道好但护城河需要进一步验证，等待更好买点' },
      { analyst: '塔勒布', action: 'buy', confidence: 72, reasoning: '在中美科技博弈背景下，国产GPU的黑天鹅对冲价值显著' },
    ],
    summary: '海光信息受益于国产替代与AI算力双主线，长期逻辑清晰但短期估值偏高，适合逢低布局。',
    timestamp: '2026-06-28T09:30:00',
  },
];

export const mockMacro: MacroSnapshot = {
  pmi: 50.8, pmiChange: 0.3, cpi: 0.2, cpiChange: -0.1,
  gdp: 5.2, gdpChange: 0.0, m2: 8.3, m2Change: -0.2,
  socialFinance: 2.06, socialFinanceChange: 0.15,
};

export const mockRisk: RiskMetrics = {
  var95: 2.35, var99: 4.12, cvar: 3.28, beta: 0.92,
  correlation: 0.85, stopLossTriggers: 0,
};

export const mockReports: Report[] = [
  { id: '1', title: '量化策略日报 - 2026年6月28日', type: 'daily', date: '2026-06-28', summary: '组合总收益+1.70%，康波周期处于复苏期，AI算力板块领涨，黄金ETF持续获资金流入', url: '#' },
  { id: '2', title: '量化策略周报 - 第26周', type: 'weekly', date: '2026-06-27', summary: '本周组合净值+3.2%，超额收益+0.8%，康波周期信号维持复苏，十五五规划对齐度92分', url: '#' },
  { id: '3', title: '月度宏观分析报告 - 2026年6月', type: 'monthly', date: '2026-06-25', summary: '宏观环境整体向好，PMI连续3个月处于扩张区间，M2增速平稳，社融数据超预期', url: '#' },
  { id: '4', title: 'AI Hedge Fund 综合分析报告', type: 'custom', date: '2026-06-26', summary: '19位AI分析师综合评分：高端制造板块获一致看多，防御板块分歧加大，建议适度减仓消费品', url: '#' },
];

export const mockPlans: SubscriptionPlan[] = [
  {
    id: 'free', name: '免费版', price: 0, period: 'monthly', highlighted: false,
    features: ['基础行情数据', '3只标的跟踪', '日报摘要', '康波周期阶段查看', '7天历史数据'],
  },
  {
    id: 'pro', name: '专业版', price: 299, period: 'monthly', highlighted: true,
    features: ['全市场行情数据', '50只标的跟踪', '每日完整报告', '康波周期 + 十五五规划完整分析', '社保基金ETF追踪', 'AI分析师参考意见', '组合优化建议', '风险监控预警', '90天历史数据', '邮件通知'],
  },
  {
    id: 'enterprise', name: '企业版', price: 2999, period: 'monthly', highlighted: false,
    features: ['专业版全部功能', '无限标的跟踪', '19位AI分析师完整报告', '自定义策略开发', 'API数据接口', '私有化部署选项', '专属客户经理', '定制化报告', '1年历史数据', '电话 + 邮件 7x24支持'],
  },
];
