import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { mockKondratiev, mockFiveYearPlan, mockMacro } from '@/lib/mock-data';
import { Radio, TrendingUp, Landmark, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';

const alignmentData = mockFiveYearPlan.map(p => ({ name: p.direction.replace('新质', '新质\n'), score: p.score, weight: p.weight }));

export function MarketAnalysis() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-white font-mono">市场分析</h2>
          <p className="text-sm text-muted-foreground mt-1">康波周期 + 十五五规划 + 宏观指标综合分析</p>
        </div>

        {/* Macro Indicators */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { label: 'PMI', value: mockMacro.pmi, change: mockMacro.pmiChange },
            { label: 'CPI', value: mockMacro.cpi, change: mockMacro.cpiChange },
            { label: 'GDP', value: mockMacro.gdp, change: mockMacro.gdpChange, suffix: '%' },
            { label: 'M2', value: mockMacro.m2, change: mockMacro.m2Change, suffix: '%' },
            { label: '社融(万亿)', value: mockMacro.socialFinance, change: mockMacro.socialFinanceChange },
          ].map((m) => (
            <div key={m.label} className="p-3 rounded-lg glass-card text-center">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{m.label}</p>
              <p className="text-lg font-bold text-white font-mono mt-1">{m.value}{m.suffix || ''}</p>
              <p className={cn('text-[10px] mt-0.5', m.change >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                {m.change >= 0 ? <ArrowUpRight className="h-3 w-3 inline" /> : <ArrowDownRight className="h-3 w-3 inline" />}
                {m.change >= 0 ? '+' : ''}{m.change}
              </p>
            </div>
          ))}
        </div>

        {/* Kondratiev & Five Year Plan */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="glass-card border-0 lg:col-span-1">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
                <Radio className="h-4 w-4 text-blue-400" /> 康波周期阶段
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center">
                <div className="h-24 w-24 mx-auto rounded-full gradient-border">
                  <div className="h-full w-full rounded-full bg-background flex items-center justify-center">
                    <div>
                      <p className="text-3xl font-bold text-white font-mono">{mockKondratiev.confidence}%</p>
                      <p className="text-[10px] text-muted-foreground">置信度</p>
                    </div>
                  </div>
                </div>
                <div className="mt-4">
                  <span className="px-3 py-1 rounded-full text-sm font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {mockKondratiev.phaseLabel}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-3 leading-relaxed">{mockKondratiev.description}</p>
              </div>
              <div className="mt-4 space-y-2">
                {mockKondratiev.sectorAllocation.map((s) => (
                  <div key={s.sector} className="flex items-center justify-between text-xs p-2 rounded bg-white/[0.02]">
                    <span className="text-muted-foreground">{s.sector}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-white font-mono">{s.recommendedWeight}%</span>
                      <span className={cn(
                        'px-1.5 py-0.5 rounded text-[10px]',
                        s.signal === 'overweight' ? 'bg-emerald-500/10 text-emerald-400' :
                        s.signal === 'underweight' ? 'bg-red-500/10 text-red-400' :
                        'bg-slate-500/10 text-slate-400'
                      )}>
                        {s.signal === 'overweight' ? '超配' : s.signal === 'underweight' ? '低配' : '标配'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card border-0 lg:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
                <Landmark className="h-4 w-4 text-amber-400" /> 十五五规划对齐度
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={alignmentData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                  <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }} />
                  <Bar dataKey="score" radius={[6, 6, 0, 0]} maxBarSize={40}>
                    {alignmentData.map((d, i) => (
                      <Cell key={i} fill={d.score >= 80 ? '#10B981' : d.score >= 60 ? '#F59E0B' : '#6B7280'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-2 mt-2">
                {mockFiveYearPlan.map((p) => (
                  <div key={p.direction} className="flex items-center justify-between p-2 rounded bg-white/[0.02] text-xs">
                    <div className="flex items-center gap-2">
                      <span className={cn('h-2 w-2 rounded-full',
                        p.score >= 80 ? 'bg-emerald-400' : p.score >= 60 ? 'bg-amber-400' : 'bg-slate-400'
                      )} />
                      <span className="text-muted-foreground">{p.direction}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-white font-mono">{p.score}分</span>
                      <span className="text-[10px] text-muted-foreground">权重{p.weight}%</span>
                    </div>
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
