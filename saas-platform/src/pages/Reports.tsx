import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { mockReports } from '@/lib/mock-data';
import { FileText, Download, Eye, Calendar, Search } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useState } from 'react';
import { cn } from '@/lib/utils';

const typeLabels: Record<string, string> = { daily: '日报', weekly: '周报', monthly: '月报', custom: '定制' };
const typeColors: Record<string, string> = {
  daily: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  weekly: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  monthly: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  custom: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
};

export function Reports() {
  const [search, setSearch] = useState('');
  const filtered = mockReports.filter(r =>
    !search || r.title.includes(search) || r.summary.includes(search)
  );

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white font-mono">报告中心</h2>
            <p className="text-sm text-muted-foreground mt-1">{mockReports.length}份历史报告</p>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索报告..." className="pl-9 pr-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder:text-muted-foreground focus:border-blue-500 outline-none w-56"
            />
          </div>
        </div>

        <div className="space-y-3">
          {filtered.map((report) => (
            <Card key={report.id} className="glass-card border-0 hover:border-white/10 transition-all duration-200 cursor-pointer group">
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <span className={cn('px-2 py-0.5 rounded text-[10px] font-medium border', typeColors[report.type])}>
                        {typeLabels[report.type]}
                      </span>
                      <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <Calendar className="h-3 w-3" /> {report.date}
                      </span>
                    </div>
                    <h3 className="text-sm font-medium text-white font-mono mb-1.5">{report.title}</h3>
                    <p className="text-xs text-muted-foreground leading-relaxed">{report.summary}</p>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <button className="p-2 rounded-lg hover:bg-white/5 text-muted-foreground hover:text-blue-400 transition-colors" title="预览">
                      <Eye className="h-4 w-4" />
                    </button>
                    <button className="p-2 rounded-lg hover:bg-white/5 text-muted-foreground hover:text-emerald-400 transition-colors" title="下载">
                      <Download className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
            <p className="text-sm text-muted-foreground">没有找到匹配的报告</p>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}


