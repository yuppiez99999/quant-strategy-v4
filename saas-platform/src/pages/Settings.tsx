import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { useAuth } from '@/contexts/AuthContext';
import { mockPlans } from '@/lib/mock-data';
import { User, Mail, Building2, CreditCard, Bell, Shield, Key, Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function Settings() {
  const { user } = useAuth();

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-3xl">
        <div>
          <h2 className="text-2xl font-bold text-white font-mono">系统设置</h2>
          <p className="text-sm text-muted-foreground mt-1">账号管理 · 订阅 · 通知偏好</p>
        </div>

        {/* Profile */}
        <Card className="glass-card border-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
              <User className="h-4 w-4 text-blue-400" /> 个人资料
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4 pb-4 border-b border-white/5">
              <div className="h-14 w-14 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center flex-shrink-0">
                <span className="text-white text-xl font-bold">{user?.name?.[0]?.toUpperCase() || 'U'}</span>
              </div>
              <div>
                <p className="text-white font-medium">{user?.name || '用户'}</p>
                <p className="text-xs text-muted-foreground">{user?.email}</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1.5">姓名</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <input defaultValue={user?.name || ''} className="w-full pl-9 pr-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white focus:border-blue-500 outline-none" />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1.5">邮箱</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <input defaultValue={user?.email || ''} className="w-full pl-9 pr-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white focus:border-blue-500 outline-none" />
                </div>
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1.5">公司</label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <input defaultValue={user?.company || ''} className="w-full pl-9 pr-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white focus:border-blue-500 outline-none" />
                </div>
              </div>
            </div>
            <button className="px-4 py-2 rounded-lg bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 transition-colors">保存修改</button>
          </CardContent>
        </Card>

        {/* Subscription */}
        <Card className="glass-card border-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-amber-400" /> 当前订阅
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between p-4 rounded-lg bg-blue-500/5 border border-blue-500/10">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                  <Zap className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white capitalize">{user?.plan || 'free'} 版</p>
                  <p className="text-[10px] text-muted-foreground">
                    {user?.plan === 'enterprise' ? '无限功能 · 专属支持' :
                     user?.plan === 'pro' ? '完整功能 · 50只标的' : '基础功能 · 3只标的'}
                  </p>
                </div>
              </div>
              <button className="px-4 py-2 rounded-lg border border-blue-500/20 text-blue-400 text-xs font-medium hover:bg-blue-500/10 transition-colors">升级方案</button>
            </div>
          </CardContent>
        </Card>

        {/* Preferences */}
        <Card className="glass-card border-0">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-mono text-white flex items-center gap-2">
              <Bell className="h-4 w-4 text-purple-400" /> 通知偏好
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { label: '每日报告推送', desc: '每个交易日收盘后发送日报', enabled: true },
                { label: '风险预警通知', desc: '止损止盈触发时立即通知', enabled: true },
                { label: 'ETF资金流提醒', desc: '大额资金流向异常提醒', enabled: true },
                { label: 'AI分析更新', desc: 'AI分析师完成分析后通知', enabled: false },
                { label: '产品更新', desc: '新功能上线和版本更新', enabled: false },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02]">
                  <div>
                    <p className="text-xs text-white font-medium">{item.label}</p>
                    <p className="text-[10px] text-muted-foreground">{item.desc}</p>
                  </div>
                  <button className={`relative w-9 h-5 rounded-full transition-colors ${item.enabled ? 'bg-blue-500' : 'bg-white/10'}`}>
                    <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${item.enabled ? 'translate-x-4' : 'translate-x-0.5'}`} />
                  </button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
