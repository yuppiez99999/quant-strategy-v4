import { useNavigate } from 'react-router-dom';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import {
  TrendingUp, Shield, Brain, BarChart3, Radio,
  Zap, Users, ArrowRight, CheckCircle2, Star,
} from 'lucide-react';

const features = [
  { icon: Brain, title: '19位AI分析师', desc: '融合巴菲特、芒格、达利欧等投资大师智慧的AI分析引擎' },
  { icon: Radio, title: '康波周期分析', desc: '基于第六轮康波周期模型，精准定位经济周期阶段与行业轮动' },
  { icon: TrendingUp, title: '十五五规划适配', desc: '7大战略方向对齐度评分，政策红利驱动的持仓优化' },
  { icon: Shield, title: '社保基金追踪', desc: '国家队资金流向实时监控，4大风格分类精准映射' },
  { icon: BarChart3, title: 'ETF资金流分析', desc: '24只核心ETF资金流向监控，风格轮动信号检测' },
  { icon: Zap, title: '风险监控预警', desc: '多维度风控体系，止损止盈 + VaR + 最大回撤全面覆盖' },
];

const stats = [
  { value: '99.9%', label: '系统可用率' },
  { value: '5层级', label: '数据源保障' },
  { value: '14标的', label: '组合配置' },
  { value: '17种', label: '分析模式' },
];

export function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      {/* Hero */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-blue-500/5 via-transparent to-transparent" />
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-blue-500/10 rounded-full blur-3xl" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-blue-500/20 bg-blue-500/5 mb-8">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs text-blue-400 font-mono">v5.7 · 康波周期 + 十五五规划 + AI Hedge Fund</span>
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white leading-tight font-mono">
              智能量化策略
              <br />
              <span className="gradient-text">SaaS平台</span>
            </h1>
            <p className="mt-6 text-lg text-muted-foreground max-w-2xl mx-auto">
              融合康波周期宏观分析、十五五规划政策适配、社保基金ETF追踪与19位AI投资大师智慧，
              为机构投资者提供一站式量化策略决策支持。
            </p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <button
                onClick={() => navigate('/register')}
                className="group px-8 py-3.5 rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 text-white font-medium text-base hover:from-blue-600 hover:to-blue-700 transition-all duration-200 glow-blue flex items-center gap-2"
              >
                免费开始试用
                <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
              </button>
              <button
                onClick={() => navigate('/login')}
                className="px-8 py-3.5 rounded-xl border border-white/10 text-white/80 font-medium text-base hover:bg-white/5 transition-all duration-200"
              >
                已有账号？登录
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-12 border-y border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <p className="text-3xl font-bold text-white font-mono">{stat.value}</p>
                <p className="text-sm text-muted-foreground mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white font-mono">核心功能</h2>
            <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
              覆盖宏观分析、行业配置、组合管理、风险监控全链条的专业量化策略平台
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => (
              <div key={feature.title} className="group p-6 rounded-xl glass-card hover:border-white/10 transition-all duration-300 cursor-pointer">
                <div className="h-12 w-12 rounded-lg bg-blue-500/10 flex items-center justify-center mb-4 group-hover:bg-blue-500/20 transition-colors">
                  <feature.icon className="h-6 w-6 text-blue-400" />
                </div>
                <h3 className="text-base font-semibold text-white font-mono mb-2">{feature.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Analysis Preview */}
      <section id="analysis" className="py-24 bg-white/[0.02]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white font-mono">强大的分析引擎</h2>
            <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
              4大投资理论 + 19位AI分析师 + 多层级时序预测模型，全方位赋能投资决策
            </p>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {[
              { title: '康波周期 + 十五五规划', items: ['第六轮康波阶段定位', '7大战略方向对齐度', '行业轮动映射', '政策权重调整建议'] },
              { title: 'AI Hedge Fund 分析', items: ['19位大师级AI分析师', '基本面 + 技术面 + 情绪面', '多维度估值模型', '组合管理与风险控制'] },
              { title: '社保基金ETF追踪', items: ['4大风格分类追踪', '国家队资金流向检测', '风格轮动信号', 'ETF到个股映射'] },
              { title: '时序预测与风控', items: ['TimesFM/Kronos/Qwen预测', 'VaR + CVaR风险度量', '止损止盈自动监控', '最大回撤与波动率跟踪'] },
            ].map((card) => (
              <div key={card.title} className="p-6 rounded-xl glass-card">
                <h3 className="text-lg font-semibold text-white font-mono mb-4">{card.title}</h3>
                <div className="space-y-2.5">
                  {card.items.map((item) => (
                    <div key={item} className="flex items-center gap-2.5 text-sm text-muted-foreground">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white font-mono">选择适合您的方案</h2>
            <p className="mt-4 text-muted-foreground">从个人投资者到大型机构，我们提供灵活的定价方案</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {[
              { name: '免费版', price: '0', period: '/月', features: ['基础行情数据', '3只标的跟踪', '日报摘要', '7天历史数据'], cta: '免费开始', popular: false },
              { name: '专业版', price: '299', period: '/月', features: ['全市场行情', '50只标的跟踪', '每日完整报告', '康波+十五五完整分析', '社保ETF追踪', 'AI分析师参考', '组合优化', '风险预警', '90天历史', '邮件通知'], cta: '开始试用', popular: true },
              { name: '企业版', price: '2,999', period: '/月', features: ['专业版全部功能', '无限标的', '19位AI完整报告', '自定义策略', 'API接口', '私有化部署', '专属经理', '7x24支持'], cta: '联系销售', popular: false },
            ].map((plan) => (
              <div key={plan.name} className={`relative p-6 rounded-xl flex flex-col ${plan.popular ? 'glass-card glow-blue border-blue-500/20' : 'glass-card'}`}>
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-blue-500 text-white text-xs font-medium flex items-center gap-1.5">
                    <Star className="h-3 w-3 fill-white" /> 最受欢迎
                  </div>
                )}
                <h3 className="text-lg font-semibold text-white font-mono">{plan.name}</h3>
                <div className="mt-4 mb-6">
                  <span className="text-4xl font-bold text-white font-mono">¥{plan.price}</span>
                  <span className="text-muted-foreground text-sm">{plan.period}</span>
                </div>
                <div className="flex-1 space-y-3 mb-6">
                  {plan.features.map((f) => (
                    <div key={f} className="flex items-center gap-2 text-sm text-muted-foreground">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                      {f}
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => plan.popular ? navigate('/register') : navigate('/login')}
                  className={`w-full py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${plan.popular ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white hover:from-blue-600 hover:to-blue-700' : 'border border-white/10 text-white/80 hover:bg-white/5'}`}
                >
                  {plan.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <div className="p-10 rounded-2xl bg-gradient-to-br from-blue-500/10 to-amber-500/5 border border-blue-500/10">
            <h2 className="text-2xl font-bold text-white font-mono">准备好升级您的投资决策了吗？</h2>
            <p className="mt-4 text-muted-foreground">加入数千位专业投资者，用数据驱动的方式做出更明智的投资决策</p>
            <button
              onClick={() => navigate('/register')}
              className="mt-8 px-8 py-3.5 rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 text-white font-medium hover:from-blue-600 hover:to-blue-700 transition-all duration-200 glow-blue inline-flex items-center gap-2"
            >
              立即免费试用 <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
