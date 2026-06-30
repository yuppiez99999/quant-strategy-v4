import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { mockMacro, mockKondratiev, mockFiveYearPlan } from '@/lib/mock-data';
import { Landmark, TrendingUp, Radio, Activity } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip } from 'recharts';

const radarData = [
  { metric: 'PMI', score: (mockMacro.pmi / 60) * 100 },
  { metric: 'GDP', score: (mockMacro.gdp / 6) * 100 },
  { metric: 'CPI适中', score: 85 },
  { metric: 'M2充裕', score: (mockMacro.m2 / 12) * 100 },
  { metric: '社融', score: (mockMacro.socialFinance / 3) * 100 },
  { metric: '政策支持', score: 88 },
];

export function Macro() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-white font-mono">宏观数据</h2>
          <p className="text-sm text-muted-foreground mt-1">宏观经济指标 · 康波周期 · 十五五规划 综合分析</p>
        </div>

        {/* Macro Indicators Table */}
        <Card className="glass-card border-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
              <Landmark className="h-4 w-4 text-amber-400" /> 核心宏观指标
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="text-left px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">指标</th>
                    <th className="text-right px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">当前值</th>
                    <th className="text-right px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">变动</th>
                    <th className="text-center px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">趋势</th>
                    <th className="text-left px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">解读</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { name: '制造业PMI', value: mockMacro.pmi, change: mockMacro.pmiChange, unit: '', desc: '连续3月扩张区间，经济复苏动能增强' },
                    { name: 'CPI同比', value: mockMacro.cpi, change: mockMacro.cpiChange, unit: '%', desc: '通胀温和，政策空间充足' },
                    { name: 'GDP增速', value: mockMacro.gdp, change: mockMacro.gdpChange, unit: '%', desc: '全年5%目标有望实现' },
                    { name: 'M2同比', value: mockMacro.m2, change: mockMacro.m2Change, unit: '%', desc: '流动性合理充裕，略低于年度目标' },
                    { name: '社会融资规模', value: mockMacro.socialFinance, change: mockMacro.socialFinanceChange, unit: '万亿', desc: '社融超预期，企业和居民中长期贷款改善' },
                  ].map((row) => (
                    <tr key={row.name} className="border-b border-white/[0.02] hover:bg-white/[0.02]">
                      <td className="px-5 py-3 text-white font-medium text-xs">{row.name}</td>
                      <td className="px-5 py-3 text-right font-mono text-white">{row.value}{row.unit}</td>
                      <td className="px-5 py-3 text-right font-mono">
                        <span className={cn(row.change >= 0 ? 'text-emerald-400' : 'text-red-400')}>
                          {row.change >= 0 ? '+' : ''}{row.change}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-center">
                        <span className={cn('px-2 py-0.5 rounded text-[10px]',
                          row.change >= 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400')}>
                          {row.change >= 0 ? '↑ 上行' : '↓ 下行'}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-xs text-muted-foreground">{row.desc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Radar + Summary */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="glass-card border-0">
            <CardHeader className="pb-0">
              <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
                <Activity className="h-4 w-4 text-blue-400" /> 宏观雷达图
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="rgba(255,255,255,0.05)" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 9 }} />
                  <Radar name="当前" dataKey="score" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.15} />
                  <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }} />
                </RadarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="glass-card border-0">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-emerald-400" /> 综合判断
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-400" />
                    <span className="text-xs font-medium text-emerald-400">康波周期</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">当前处于第六轮康波复苏期，AI/算力为核心驱动。建议超配科技成长，标配顺周期与资源。</p>
                </div>
                <div className="p-4 rounded-lg bg-blue-500/5 border border-blue-500/10">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="h-2 w-2 rounded-full bg-blue-400" />
                    <span className="text-xs font-medium text-blue-400">十五五规划</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">持仓组合与十五五规划对齐度良好，新质生产力方向覆盖充分。建议补充安全发展方向标的。</p>
                </div>
                <div className="p-4 rounded-lg bg-amber-500/5 border border-amber-500/10">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="h-2 w-2 rounded-full bg-amber-400" />
                    <span className="text-xs font-medium text-amber-400">宏观判断</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">经济温和复苏，通胀可控，流动性充裕。风险点：外部地缘政治扰动，关注出口数据变化。</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
