import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { mockETFData } from '@/lib/mock-data';
import { BarChart3, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { ResponsiveContainer, Treemap, Tooltip } from 'recharts';

const styleNames: Record<string, string> = { tech_manufacturing: '高端制造', procyclical: '顺周期', resources: '资源', defensive: '防御' };
const styleColors: Record<string, string> = { tech_manufacturing: '#3B82F6', procyclical: '#F59E0B', resources: '#10B981', defensive: '#6B7280' };

const treemapData = mockETFData.map(e => ({
  name: e.etfName, size: e.totalAsset, style: e.style,
  inflow: e.netInflow, color: styleColors[e.style] || '#6B7280',
}));

const signalMap = {
  strong_inflow: { label: '大幅流入', icon: TrendingUp, bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20' },
  inflow: { label: '流入', icon: TrendingUp, bg: 'bg-emerald-500/5', text: 'text-emerald-300', border: 'border-emerald-500/10' },
  neutral: { label: '中性', icon: Minus, bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/20' },
  outflow: { label: '流出', icon: TrendingDown, bg: 'bg-red-500/5', text: 'text-red-300', border: 'border-red-500/10' },
  strong_outflow: { label: '大幅流出', icon: TrendingDown, bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20' },
};

export function ETFTracking() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-white font-mono">ETF资金流向</h2>
          <p className="text-sm text-muted-foreground mt-1">24只核心ETF实时监控 · 国家队信号 · 风格轮动</p>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {(['tech_manufacturing', 'procyclical', 'resources', 'defensive'] as const).map((style) => {
            const styleEtfs = mockETFData.filter(e => e.style === style);
            const totalInflow = styleEtfs.reduce((s, e) => s + e.netInflow, 0);
            return (
              <div key={style} className="p-4 rounded-lg glass-card">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] text-muted-foreground uppercase tracking-wider">{styleNames[style]}</span>
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: styleColors[style] }} />
                </div>
                <p className="text-xl font-bold text-white font-mono">
                  {totalInflow > 0 ? '+' : ''}{totalInflow.toFixed(1)}
                </p>
                <p className="text-[10px] text-muted-foreground">亿元净流入</p>
              </div>
            );
          })}
        </div>

        {/* Treemap */}
        <Card className="glass-card border-0">
          <CardHeader className="pb-0">
            <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-blue-400" /> ETF资产规模分布
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={320}>
              <Treemap data={treemapData} dataKey="size" stroke="#0d1117" fill="#8884d8">
                <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff' }}
                  formatter={(value: number, name: string, props: any) => {
                    if (name === 'size') return [`¥${(value / 100).toFixed(0)}亿`, props.payload.name];
                    return [value, name];
                  }} />
                {treemapData.map((item, index) => (
                  <Cell key={index} fill={item.color} fillOpacity={0.6 + (item.size / 350000) * 0.4} />
                ))}
              </Treemap>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* ETF Table */}
        <Card className="glass-card border-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono text-white">全部ETF监控</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="text-left px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">ETF</th>
                    <th className="text-left px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">风格</th>
                    <th className="text-right px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">总资产</th>
                    <th className="text-right px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">净流入</th>
                    <th className="text-right px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">比例</th>
                    <th className="text-center px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">信号</th>
                  </tr>
                </thead>
                <tbody>
                  {mockETFData.map((etf) => {
                    const sig = signalMap[etf.signal];
                    const Icon = sig.icon;
                    return (
                      <tr key={etf.etfCode} className="border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors">
                        <td className="px-5 py-3">
                          <div>
                            <p className="text-white font-medium font-mono">{etf.etfCode}</p>
                            <p className="text-[10px] text-muted-foreground">{etf.etfName}</p>
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <span className="px-2 py-0.5 rounded text-[10px]" style={{
                            backgroundColor: `${styleColors[etf.style]}15`,
                            color: styleColors[etf.style],
                          }}>
                            {styleNames[etf.style]}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-right text-white font-mono">¥{etf.totalAsset.toLocaleString()}亿</td>
                        <td className="px-5 py-3 text-right font-mono">
                          <span className={cn(etf.netInflow > 0 ? 'text-emerald-400' : 'text-red-400')}>
                            {etf.netInflow > 0 ? '+' : ''}{etf.netInflow.toFixed(2)}亿
                          </span>
                        </td>
                        <td className="px-5 py-3 text-right font-mono">
                          <span className={cn(etf.netInflowPercent > 0 ? 'text-emerald-400' : 'text-red-400')}>
                            {etf.netInflowPercent > 0 ? '+' : ''}{etf.netInflowPercent.toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-5 py-3 text-center">
                          <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium', sig.bg, sig.text, sig.border)}>
                            <Icon className="h-3 w-3" /> {sig.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
