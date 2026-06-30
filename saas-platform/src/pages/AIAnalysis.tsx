import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { mockAIAnalysis } from '@/lib/mock-data';
import { Brain, TrendingUp, TrendingDown, Minus, Sparkles } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

const analystColors: Record<string, string> = {
  buy: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  sell: 'bg-red-500/10 text-red-400 border-red-500/20',
  hold: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
};

export function AIAnalysis() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-white font-mono">AI分析</h2>
          <p className="text-sm text-muted-foreground mt-1">AI Hedge Fund · 19位投资大师AI分析师 · 多维度决策支持</p>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {mockAIAnalysis.map((analysis) => (
            <Card key={analysis.ticker} className="glass-card border-0">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
                    <Brain className="h-4 w-4 text-blue-400" />
                    {analysis.tickerName}
                    <span className="text-xs text-muted-foreground font-mono">{analysis.ticker}</span>
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      'h-10 w-10 rounded-xl flex items-center justify-center border',
                      analysis.overallScore >= 8 ? 'bg-emerald-500/10 border-emerald-500/20' :
                      analysis.overallScore >= 6 ? 'bg-amber-500/10 border-amber-500/20' :
                      'bg-red-500/10 border-red-500/20'
                    )}>
                      <span className={cn('text-lg font-bold font-mono',
                        analysis.overallScore >= 8 ? 'text-emerald-400' :
                        analysis.overallScore >= 6 ? 'text-amber-400' : 'text-red-400'
                      )}>{analysis.overallScore.toFixed(1)}</span>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground mb-4 leading-relaxed">{analysis.summary}</p>
                <div className="space-y-2.5">
                  {analysis.signals.map((sig) => (
                    <div key={sig.analyst} className="flex items-start gap-3 p-3 rounded-lg bg-white/[0.02] hover:bg-white/[0.04] transition-colors">
                      <div className="h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0"
                        style={{
                          backgroundColor: sig.action === 'buy' ? 'rgba(16,185,129,0.1)' :
                                           sig.action === 'sell' ? 'rgba(239,68,68,0.1)' :
                                           'rgba(245,158,11,0.1)'
                        }}>
                        {sig.action === 'buy' ? <TrendingUp className="h-4 w-4 text-emerald-400" /> :
                         sig.action === 'sell' ? <TrendingDown className="h-4 w-4 text-red-400" /> :
                         <Minus className="h-4 w-4 text-amber-400" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <p className="text-xs font-medium text-white">{sig.analyst}</p>
                          <span className={cn('px-1.5 py-0.5 rounded text-[10px] font-medium border', analystColors[sig.action])}>
                            {sig.action === 'buy' ? '买入' : sig.action === 'sell' ? '卖出' : '持有'}
                          </span>
                        </div>
                        <p className="text-[11px] text-muted-foreground leading-relaxed">{sig.reasoning}</p>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <p className="text-xs font-mono text-muted-foreground">信心</p>
                        <p className={cn('text-sm font-bold font-mono',
                          sig.confidence >= 80 ? 'text-emerald-400' :
                          sig.confidence >= 60 ? 'text-amber-400' : 'text-red-400'
                        )}>{sig.confidence}%</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Available Analysts */}
        <Card className="glass-card border-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-blue-400" /> 19位AI投资大师
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
              {[
                '巴菲特', '查理·芒格', '彼得·林奇', '格雷厄姆', '菲利普·费雪',
                '德鲁肯米勒', '比尔·阿克曼', '木头姐', '迈克尔·伯里',
                '塔勒布', '达摩达兰', '帕伯莱', '印度巴菲特',
                '基本面分析师', '技术分析师', '情绪分析师', '新闻分析师',
                '估值分析师', '风险管理师',
              ].map((name) => (
                <div key={name} className="p-2 rounded-lg bg-white/[0.02] text-center hover:bg-white/[0.04] transition-colors cursor-pointer">
                  <p className="text-xs text-muted-foreground">{name}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
