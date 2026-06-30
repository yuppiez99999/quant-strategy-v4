import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useState } from 'react';
import { Menu, X } from 'lucide-react';

export function Navbar() {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center glow-blue">
              <span className="text-white font-bold text-sm">Q</span>
            </div>
            <div>
              <h1 className="text-base font-semibold text-white font-mono">QuantMatrix</h1>
              <p className="text-[10px] text-muted-foreground -mt-0.5">智能量化策略平台</p>
            </div>
          </Link>

          <div className="hidden md:flex items-center gap-6">
            <a href="#features" className="text-sm text-muted-foreground hover:text-white transition-colors">功能</a>
            <a href="#pricing" className="text-sm text-muted-foreground hover:text-white transition-colors">定价</a>
            <a href="#analysis" className="text-sm text-muted-foreground hover:text-white transition-colors">分析能力</a>
          </div>

          <div className="hidden md:flex items-center gap-3">
            {isAuthenticated ? (
              <>
                <button onClick={() => navigate('/dashboard')} className="text-sm text-muted-foreground hover:text-white transition-colors">
                  控制台
                </button>
                <div className="flex items-center gap-2">
                  <div className="h-7 w-7 rounded-full bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
                    <span className="text-white text-[10px] font-bold">{user?.name?.[0]?.toUpperCase()}</span>
                  </div>
                  <button onClick={logout} className="text-sm text-muted-foreground hover:text-red-400 transition-colors">
                    退出
                  </button>
                </div>
              </>
            ) : (
              <>
                <button onClick={() => navigate('/login')} className="text-sm text-muted-foreground hover:text-white transition-colors">
                  登录
                </button>
                <button
                  onClick={() => navigate('/register')}
                  className="px-4 py-2 rounded-lg bg-gradient-to-r from-blue-500 to-blue-600 text-white text-sm font-medium hover:from-blue-600 hover:to-blue-700 transition-all duration-200 glow-blue"
                >
                  免费试用
                </button>
              </>
            )}
          </div>

          <button className="md:hidden p-2" onClick={() => setMobileOpen(!mobileOpen)}>
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {mobileOpen && (
          <div className="md:hidden py-4 border-t border-white/5 space-y-3">
            <a href="#features" className="block text-sm text-muted-foreground hover:text-white">功能</a>
            <a href="#pricing" className="block text-sm text-muted-foreground hover:text-white">定价</a>
            {isAuthenticated ? (
              <button onClick={() => navigate('/dashboard')} className="w-full mt-2 px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium">
                进入控制台
              </button>
            ) : (
              <button onClick={() => navigate('/register')} className="w-full mt-2 px-4 py-2 rounded-lg bg-gradient-to-r from-blue-500 to-blue-600 text-white text-sm font-medium">
                免费试用
              </button>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}
