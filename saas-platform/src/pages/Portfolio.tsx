import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { mockPortfolio, mockSummary, mockRisk } from '@/lib/mock-data';
import { PieChart, Shield, TrendingUp, ArrowUpRight, ArrowDownRight, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from 'recharts';

const weightBiasData = mockPortfolio.map(a => ({
  name: a.symbol,
  fullName: a.name,
  target: a.weight,
  current: a.currentWeight,
  diff: +(a.currentWeight - a.weight).toFixed(2),
}));

const sectors = ['tech_manufacturing', 'procyclical', 'resources', 'defensive'] as const;
const sectorNames: Record<string, string> = { tech_manufacturing: '高端制造', procyclical: '顺周期', resources: '资源', defensive: '防御' };
const sectorColors: Record<string, string> = { tech_manufacturing: '#3B82F6', procyclical: '#F59E0B', resources: '#10B981', defensive: '#6B7280' };

export function Portfolio() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-white font-mono">投资组合</h2>
          <p className="text-sm text-muted-foreground mt-1">14只标的 · 4大板块 · 总资产 ¥{mockSummary.totalValue.toLocaleString()}</p>
        </div>

        {/* Risk Summary */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'VaR 95%', value: `${mockRisk.var95}%` },
            { label: 'CVaR', value: `${mockRisk.cvar}%` },
            { label: 'Beta', value: mockRisk.beta.toFixed(2) },
            { label: '止损触发', value: `${mockRisk.stopLossTriggers}只`, highlight: mockRisk.stopLossTriggers === 0 },
          ].map((m) => (
            <div key={m.label} className="p-3 rounded-lg glass-card text-center">
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{m.label}</p>
              <p className={cn('text-base font-bold font-mono mt-1', m.highlight ? 'text-emerald-400' : 'text-white')}>{m.value}</p>
            </div>
          ))}
        </div>

        {/* Holdings Table */}
        <Card className="glass-card border-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono text-white">持仓明细</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="text-left px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">标的</th>
                    <th className="text-left px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">板块</th>
                    <th className="text-right px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">目标权重</th>
                    <th className="text-right px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">当前权重</th>
                    <th className="text-right px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">偏离</th>
                    <th className="text-right px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">最新价</th>
                    <th className="text-right px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">涨跌幅</th>
                    <th className="text-right px-5 py-3 text-[10px] text-muted-foreground uppercase tracking-wider">市值</th>
                  </tr>
                </thead>
                <tbody>
                  {mockPortfolio.map((asset) => {
                    const deviation = asset.currentWeight - asset.weight;
                    const absDeviation = Math.abs(deviation);
                    return (
                      <tr key={asset.symbol} className="border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors">
                        <td className="px-5 py-3">
                          <div>
                            <p className="text-white font-medium font-mono">{asset.symbol}</p>
                            <p className="text-[10px] text-muted-foreground">{asset.name}</p>
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <span className="px-2 py-0.5 rounded text-[10px]" style={{
                            backgroundColor: `${sectorColors[asset.sector]}15`,
                            color: sectorColors[asset.sector],
                          }}>
                            {sectorNames[asset.sector]}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-right text-muted-foreground font-mono">{asset.weight}%</td>
                        <td className="px-5 py-3 text-right text-white font-mono">{asset.currentWeight}%</td>
                        <td className="px-5 py-3 text-right font-mono">
                          <span className={cn(
                            'inline-flex items-center gap-0.5',
                            absDeviation > 2 ? (deviation > 0 ? 'text-amber-400' : 'text-red-400') : 'text-muted-foreground'
                          )}>
                            {deviation > 0 ? '+' : ''}{deviation.toFixed(1)}%
                            {absDeviation > 2 && <AlertTriangle className="h-3 w-3" />}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-right text-white font-mono">¥{asset.price.toFixed(2)}</td>
                        <td className="px-5 py-3 text-right font-mono">
                          <span className={cn(asset.changePercent > 0 ? 'text-emerald-400' : 'text-red-400')}>
                            {asset.changePercent > 0 ? '+' : ''}{asset.changePercent.toFixed(2)}%
                          </span>
                        </td>
                        <td className="px-5 py-3 text-right text-white font-mono">¥{(asset.value / 10000).toFixed(1)}万</td>
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
