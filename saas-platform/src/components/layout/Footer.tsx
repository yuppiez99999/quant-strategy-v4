import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer className="border-t border-white/5 bg-card/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center glow-blue">
                <span className="text-white font-bold text-xs">Q</span>
              </div>
              <span className="font-mono font-semibold text-white text-sm">QuantMatrix</span>
            </div>
            <p className="text-sm text-muted-foreground">基于康波周期 + 十五五规划 + 社保基金ETF追踪的新一代智能量化策略平台</p>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-4">产品</h4>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">投资组合管理</p>
              <p className="text-sm text-muted-foreground">市场分析</p>
              <p className="text-sm text-muted-foreground">AI智能分析</p>
              <p className="text-sm text-muted-foreground">风险监控</p>
            </div>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-4">资源</h4>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">API文档</p>
              <p className="text-sm text-muted-foreground">研究报告</p>
              <p className="text-sm text-muted-foreground">策略回测</p>
              <p className="text-sm text-muted-foreground">社区</p>
            </div>
          </div>
          <div>
            <h4 className="text-xs font-semibold text-white uppercase tracking-wider mb-4">公司</h4>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">关于我们</p>
              <p className="text-sm text-muted-foreground">联系销售</p>
              <p className="text-sm text-muted-foreground">隐私政策</p>
              <p className="text-sm text-muted-foreground">服务条款</p>
            </div>
          </div>
        </div>
        <div className="mt-8 pt-8 border-t border-white/5 text-center">
          <p className="text-xs text-muted-foreground">© 2026 QuantMatrix. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
