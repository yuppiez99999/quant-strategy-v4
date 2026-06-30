import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import { mockPlans } from '@/lib/mock-data';
import { CheckCircle2, Star, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function Pricing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <div className="pt-24 pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h1 className="text-4xl font-bold text-white font-mono">选择适合您的方案</h1>
            <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
              从个人投资者到大型机构，我们提供灵活的定价方案，匹配不同规模的投资需求
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {mockPlans.map((plan) => (
              <div key={plan.id} className={`relative p-8 rounded-2xl flex flex-col ${
                plan.highlighted
                  ? 'glass-card glow-blue border-blue-500/20 bg-gradient-to-b from-blue-500/5 to-transparent'
                  : 'glass-card'
              }`}>
                {plan.highlighted && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-blue-500 text-white text-xs font-medium flex items-center gap-1.5">
                    <Star className="h-3 w-3 fill-white" /> 最受欢迎
                  </div>
                )}
                <h3 className="text-lg font-semibold text-white font-mono">{plan.name}</h3>
                <div className="mt-4 mb-6">
                  <span className="text-4xl font-bold text-white font-mono">¥{plan.price}</span>
                  <span className="text-muted-foreground text-sm">{plan.period}</span>
                </div>
                <div className="flex-1 space-y-3 mb-8">
                  {plan.features.map((f) => (
                    <div key={f} className="flex items-center gap-2.5 text-sm text-muted-foreground">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                      {f}
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => navigate(plan.highlighted ? '/register' : '/login')}
                  className={`w-full py-3 rounded-xl text-sm font-medium transition-all duration-200 flex items-center justify-center gap-2 ${
                    plan.highlighted
                      ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white hover:from-blue-600 hover:to-blue-700 glow-blue'
                      : 'border border-white/10 text-white/80 hover:bg-white/5'
                  }`}
                >
                  {plan.highlighted ? '开始试用' : plan.id === 'enterprise' ? '联系销售' : '免费开始'}
                  {plan.highlighted && <ArrowRight className="h-4 w-4" />}
                </button>
              </div>
            ))}
          </div>

          {/* Enterprise CTA */}
          <div className="mt-16 max-w-3xl mx-auto text-center p-8 rounded-2xl glass-card">
            <h3 className="text-lg font-semibold text-white font-mono mb-2">需要定制方案？</h3>
            <p className="text-sm text-muted-foreground mb-6">联系我们获取专属的企业级量化策略解决方案，包含私有化部署、数据接口和定制开发</p>
            <button className="px-8 py-3 rounded-xl border border-blue-500/20 text-blue-400 hover:bg-blue-500/10 transition-all duration-200 text-sm font-medium">
              联系销售团队
            </button>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
