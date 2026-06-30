import {
  SidebarProvider,
  Sidebar as ShadSidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
} from '@/components/ui/sidebar';
import {
  LayoutDashboard, PieChart, TrendingUp, BarChart3,
  Bot, FileText, Settings, LogOut, Landmark, Radio,
} from 'lucide-react';
import { useLocation, Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';

const navItems = [
  { title: '仪表盘', icon: LayoutDashboard, path: '/dashboard' },
  { title: '投资组合', icon: PieChart, path: '/portfolio' },
  { title: '市场分析', icon: TrendingUp, path: '/market' },
  { title: '康波周期', icon: Radio, path: '/kondratiev' },
  { title: 'ETF资金流', icon: BarChart3, path: '/etf' },
  { title: 'AI分析', icon: Bot, path: '/ai-analysis' },
  { title: '宏观数据', icon: Landmark, path: '/macro' },
  { title: '报告中心', icon: FileText, path: '/reports' },
  { title: '系统设置', icon: Settings, path: '/settings' },
];

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { user, logout } = useAuth();

  return (
    <SidebarProvider defaultOpen={true}>
      <div className="flex h-screen w-full overflow-hidden bg-background">
        <ShadSidebar className="border-r border-white/5">
          <SidebarHeader className="px-4 py-6">
            <Link to="/dashboard" className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center glow-blue">
                <span className="text-white font-bold text-sm">Q</span>
              </div>
              <div>
                <h1 className="text-sm font-semibold text-white font-mono">QuantMatrix</h1>
                <p className="text-[10px] text-muted-foreground">智能量化策略平台</p>
              </div>
            </Link>
          </SidebarHeader>
          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupLabel className="text-[10px] uppercase tracking-wider">主导航</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {navItems.map((item) => (
                    <SidebarMenuItem key={item.path}>
                      <SidebarMenuButton
                        asChild
                        isActive={location.pathname === item.path}
                        tooltip={item.title}
                      >
                        <Link to={item.path} className={cn(
                          'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-200',
                          location.pathname === item.path
                            ? 'bg-primary/10 text-primary font-medium'
                            : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
                        )}>
                          <item.icon className="h-4 w-4" />
                          <span>{item.title}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>
          <SidebarFooter className="p-4 border-t border-white/5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 min-w-0">
                <div className="h-8 w-8 rounded-full bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xs font-bold">
                    {user?.name?.[0]?.toUpperCase() || 'U'}
                  </span>
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-white truncate">{user?.name || '用户'}</p>
                  <p className="text-[10px] text-muted-foreground capitalize">{user?.plan || 'free'}</p>
                </div>
              </div>
              <button
                onClick={logout}
                className="p-1.5 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-colors"
                title="退出登录"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </SidebarFooter>
        </ShadSidebar>
        <main className="flex-1 overflow-auto">
          <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-white/5">
            <div className="flex items-center justify-between px-6 h-14">
              <div className="flex items-center gap-3">
                <SidebarTrigger />
                <div className="h-4 w-px bg-white/10" />
                <span className="text-sm text-muted-foreground font-mono">
                  {navItems.find(i => i.path === location.pathname)?.title || ''}
                </span>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-xs text-emerald-400 font-mono">系统正常</span>
                </div>
              </div>
            </div>
          </div>
          <div className="p-6">
            {children}
          </div>
        </main>
      </div>
    </SidebarProvider>
  );
}
