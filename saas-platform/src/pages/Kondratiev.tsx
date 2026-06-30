import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { mockKondratiev } from '@/lib/mock-data';
import { Radio, ArrowRight, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const phases = [
  { phase: 'recession', label: '衰退期', desc: '经济下行，通缩压力，债券为王，现金宝贵', active: false, color: 'slate' },
  { phase: 'recovery', label: '复苏期', desc: '经济触底回升，货币政策宽松，股市启动，成长占优', active: true, color: 'emerald' },
  { phase: 'prosperity', label: '繁荣期', desc: '经济过热，通胀上升，大宗商品暴涨，周期为王', active: false, color: 'amber' },
  { phase: 'stagflation', label: '滞胀期', desc: '增长停滞+通胀高企，现金+黄金+防御板块', active: false, color: 'red' },
];

const phaseColors: Record<string, string> = {
  slate: { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/20', bar: 'bg-slate-500' },
  emerald: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20', bar: 'bg-emerald-500' },
  amber: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20', bar: 'bg-amber-500' },
  red: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20', bar: 'bg-red-500' },
};

export function Kondratiev() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-white font-mono">康波周期分析</h2>
          <p className="text-sm text-muted-foreground mt-1">第六轮康波周期 · AI/算力驱动 · 四阶段定位</p>
        </div>

        {/* Phase Timeline */}
        <Card className="glass-card border-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
              <Radio className="h-4 w-4 text-blue-400" /> 周期阶段
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-2 mb-6">
              {phases.map((p, i) => (
                <div key={p.phase} className={cn(
                  'p-3 rounded-xl text-center transition-all',
                  p.active ? 'glass-card glow-blue' : 'bg-white/[0.02] opacity-60'
                )}>
                  <p className={cn('text-xs font-bold mb-1', p.active ? 'text-white' : 'text-muted-foreground')}>{p.label}</p>
                  {p.active && <p className="text-[10px] text-emerald-400 font-medium">● 当前</p>}
                </div>
              ))}
            </div>
            <div className="h-2 rounded-full bg-white/5 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-slate-500 via-emerald-500 to-blue-500" style={{ width: '45%' }} />
            </div>
            <p className="text-xs text-muted-foreground mt-2 text-center">复苏期 → 繁荣期过渡中</p>
          </CardContent>
        </Card>

        {/* Cycle Details */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="glass-card border-0">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-mono text-white">当前阶段特征</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground leading-relaxed mb-4">{mockKondratiev.description}</p>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: '置信度', value: `${mockKondratiev.confidence}%`, color: 'emerald' },
                  { label: '商品信号', value: mockKondratiev.commoditySignal === 'bullish' ? '看多' : '看空', color: 'emerald' },
                  { label: '周期轮', value: '第六轮', color: 'blue' },
                  { label: '驱动因素', value: 'AI/算力', color: 'blue' },
                ].map((m) => (
                  <div key={m.label} className="p-3 rounded-lg bg-white/[0.02]">
                    <p className="text-[10px] text-muted-foreground">{m.label}</p>
                    <p className="text-sm font-bold text-white font-mono mt-0.5">{m.value}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="glass-card border-0">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-mono text-white">行业配置建议</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {mockKondratiev.sectorAllocation.map((s) => (
                  <div key={s.sector} className="p-3 rounded-lg bg-white/[0.02]">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-white font-medium">{s.sector}</span>
                      <span className={cn(
                        'px-2 py-0.5 rounded text-[10px] font-medium border',
                        s.signal === 'overweight' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                        s.signal === 'underweight' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                        'bg-slate-500/10 text-slate-400 border-slate-500/20'
                      )}>
                        {s.signal === 'overweight' ? '超配' : s.signal === 'underweight' ? '低配' : '标配'}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
                        <div className="h-full rounded-full bg-gradient-to-r from-blue-500 to-emerald-500"
                          style={{ width: `${s.recommendedWeight * 2}%` }} />
                      </div>
                      <span className="text-xs font-mono text-muted-foreground w-16 text-right">{s.recommendedWeight}%</span>
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
