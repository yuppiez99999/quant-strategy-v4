import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Mail, Lock, User, Building2, ArrowRight } from 'lucide-react';
import { Navbar } from '@/components/layout/Navbar';

export function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [company, setCompany] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(name, email, password, company);
      navigate('/dashboard');
    } catch {
      setError('注册失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="flex items-center justify-center min-h-screen pt-16 pb-8">
        <div className="w-full max-w-md px-4">
          <div className="glass-card p-8">
            <div className="text-center mb-8">
              <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center glow-blue mx-auto mb-4">
                <span className="text-white font-bold text-lg">Q</span>
              </div>
              <h2 className="text-xl font-bold text-white font-mono">开始免费试用</h2>
              <p className="text-sm text-muted-foreground mt-2">创建您的 QuantMatrix 账号，体验专业量化策略分析</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-muted-foreground mb-1.5">姓名</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                    placeholder="您的姓名" required
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-muted-foreground/50 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all text-sm" />
                </div>
              </div>

              <div>
                <label className="block text-sm text-muted-foreground mb-1.5">邮箱地址</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com" required
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-muted-foreground/50 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all text-sm" />
                </div>
              </div>

              <div>
                <label className="block text-sm text-muted-foreground mb-1.5">公司/机构</label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input type="text" value={company} onChange={(e) => setCompany(e.target.value)}
                    placeholder="您的公司或机构名称" required
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-muted-foreground/50 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all text-sm" />
                </div>
              </div>

              <div>
                <label className="block text-sm text-muted-foreground mb-1.5">密码</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                    placeholder="至少8位字符" required minLength={8}
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white placeholder:text-muted-foreground/50 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all text-sm" />
                </div>
              </div>

              {error && <p className="text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2">{error}</p>}

              <button type="submit" disabled={loading}
                className="w-full py-2.5 rounded-lg bg-gradient-to-r from-blue-500 to-blue-600 text-white font-medium hover:from-blue-600 hover:to-blue-700 transition-all duration-200 glow-blue flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {loading ? '注册中...' : '创建免费账号'} {!loading && <ArrowRight className="h-4 w-4" />}
              </button>
            </form>

            <p className="mt-6 text-xs text-muted-foreground text-center">
              注册即表示您同意我们的 <span className="text-blue-400 cursor-pointer hover:underline">服务条款</span> 和 <span className="text-blue-400 cursor-pointer hover:underline">隐私政策</span>
            </p>

            <div className="mt-4 text-center">
              <p className="text-sm text-muted-foreground">
                已有账号？{' '}
                <Link to="/login" className="text-blue-400 hover:text-blue-300 transition-colors font-medium">
                  立即登录
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
