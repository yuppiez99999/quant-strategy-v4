import { useState } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { mockPortfolio, mockSummary, mockKondratiev, mockAIAnalysis, mockETFData } from '@/lib/mock-data';
import {
  TrendingUp, TrendingDown, PieChart, Shield, Zap, Radio,
  DollarSign, Activity, BarChart3, ArrowUpRight, ArrowDownRight,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { AreaChart, Area, PieChart as RPieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from 'recharts';

const pieData = mockPortfolio.map(a => ({ name: a.name, value: a.value }));
const PIE_COLORS = ['#3B82F6', '#2563EB', '#1D4ED8', '#60A5FA', '#93C5FD', '#DBEAFE', '#F59E0B', '#D97706', '#B45309', '#FCD34D', '#FBBF24', '#10B981', '#059669', '#047857'];

const sectorData = [
  { name: '高端制造', value: mockPortfolio.filter(a => a.sector === 'tech_manufacturing').reduce((s, a) => s + a.value, 0) },
  { name: '顺周期', value: mockPortfolio.filter(a => a.sector === 'procyclical').reduce((s, a) => s + a.value, 0) },
  { name: '资源', value: mockPortfolio.filter(a => a.sector === 'resources').reduce((s, a) => s + a.value, 0) },
  { name: '防御', value: mockPortfolio.filter(a => a.sector === 'defensive').reduce((s, a) => s + a.value, 0) },
];

const etfFlowBarData = mockETFData.slice(0, 8).map(e => ({
  name: e.etfName.replace('ETF', ''),
  inflow: e.netInflow,
}));

export function Dashboard() {
  const summary = mockSummary;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-white font-mono">仪表盘</h2>
          <p className="text-sm text-muted-foreground mt-1">投资组合实时概览 · 最后更新 2026-06-28 13:30</p>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: '组合总资产', value: `¥${(summary.totalValue / 10000).toFixed(0)}万`, change: `+${summary.totalChangePercent}%`, icon: DollarSign, up: true },
            { label: '今日盈亏', value: `¥${(summary.dailyPL).toLocaleString()}`, change: `+1.23%`, icon: Activity, up: true },
            { label: '累计收益', value: `+${summary.totalReturn}%`, change: `Sharpe ${summary.sharpeRatio}`, icon: TrendingUp, up: true },
            { label: '最大回撤', value: `${summary.maxDrawdown}%`, change: `波动率 ${summary.volatility}%`, icon: Shield, up: false },
          ].map((metric) => (
            <Card key={metric.label} className="glass-card border-0">
              <CardContent className="p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-muted-foreground">{metric.label}</span>
                  <div className={cn('h-8 w-8 rounded-lg flex items-center justify-center', metric.up ? 'bg-emerald-500/10' : 'bg-amber-500/10')}>
                    <metric.icon className={cn('h-4 w-4', metric.up ? 'text-emerald-400' : 'text-amber-400')} />
                  </div>
                </div>
                <p className="text-xl font-bold text-white font-mono">{metric.value}</p>
                <p className={cn('text-xs mt-1', metric.up ? 'text-emerald-400' : 'text-amber-400')}>
                  {metric.up ? <ArrowUpRight className="h-3 w-3 inline" /> : <ArrowDownRight className="h-3 w-3 inline" />}
                  {' '}{metric.change}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Portfolio Pie */}
          <Card className="glass-card border-0">
            <CardHeader className="pb-0">
              <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
                <PieChart className="h-4 w-4 text-blue-400" /> 持仓分布
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <div className="h-[220px] w-[220px]">
                  <ResponsiveContainer>
                    <RPieChart>
                      <Pie data={sectorData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={85} innerRadius={50}>
                        {sectorData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
                      </Pie>
                      <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }} />
                    </RPieChart>
                  </ResponsiveContainer>
                </div>
                <div className="space-y-2 flex-1">
                  {sectorData.map((s, i) => (
                    <div key={s.name} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: PIE_COLORS[i] }} />
                        <span className="text-muted-foreground">{s.name}</span>
                      </div>
                      <span className="text-white font-mono">¥{(s.value / 10000).toFixed(1)}万</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* ETF Flow */}
          <Card className="glass-card border-0">
            <CardHeader className="pb-0">
              <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-amber-400" /> ETF资金流向 (亿元)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={etfFlowBarData} layout="vertical" margin={{ left: 60 }}>
                  <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis dataKey="name" type="category" tick={{ fill: '#e2e8f0', fontSize: 11 }} axisLine={false} tickLine={false} width={55} />
                  <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }} />
                  <Bar dataKey="inflow" radius={[0, 4, 4, 0]}>
                    {etfFlowBarData.map((e, i) => (
                      <Cell key={i} fill={e.inflow > 0 ? '#10B981' : '#EF4444'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Konratiev & AI Analysis */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="glass-card border-0">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
                <Radio className="h-4 w-4 text-blue-400" /> 康波周期信号
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4 mb-4">
                <div className="h-16 w-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                  <span className="text-2xl font-bold text-blue-400 font-mono">{mockKondratiev.confidence}%</span>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      {mockKondratiev.phaseLabel}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed line-clamp-3">{mockKondratiev.description}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card border-0">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-400" /> AI分析师推荐
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {mockAIAnalysis[0].signals.slice(0, 3).map((sig) => (
                  <div key={sig.analyst} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02]">
                    <div className="flex items-center gap-3">
                      <div className={cn('h-8 w-8 rounded-lg flex items-center justify-center text-xs font-bold font-mono',
                        sig.action === 'buy' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400')}>
                        {sig.action === 'buy' ? 'B' : 'H'}
                      </div>
                      <div>
                        <p className="text-xs text-white font-medium">{sig.analyst}</p>
                        <p className="text-[10px] text-muted-foreground truncate max-w-[180px]">{sig.reasoning}</p>
                      </div>
                    </div>
                    <span className="text-xs font-mono text-muted-foreground">{sig.confidence}%</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
