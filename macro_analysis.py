# -*- coding: utf-8 -*-
"""
宏观分析模块 - 结合康波周期和中国十五五规划预测持仓收益率
"""

import pandas as pd
import numpy as np
import yaml

class MacroAnalyzer:
    def __init__(self, config_path='config/portfolio.yaml'):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.assets = self.config['assets']
        self.codes = [a['code'] for a in self.assets]
        self.target_weights = {a['code']: a['target_weight'] for a in self.assets}
        self.names = {a['code']: a['name'] for a in self.assets}
        
        self.kangbo_phases = {
            'recovery': {'name': '回升期', 'years': [2024, 2025, 2026], 'factor': 1.15},
            'prosperity': {'name': '繁荣期', 'years': [2027, 2028, 2029, 2030, 2031], 'factor': 1.25},
            'recession': {'name': '衰退期', 'years': [2032, 2033, 2034], 'factor': 0.90},
            'depression': {'name': '萧条期', 'years': [2035, 2036, 2037], 'factor': 0.75}
        }
        
        self.fifteen_five_themes = {
            '科技创新': {'weight': 0.3, 'beneficiaries': ['北方华创', '阳光电源', '国电南瑞', '绿的谐波']},
            '绿色发展': {'weight': 0.25, 'beneficiaries': ['南网储能', '阳光电源', '东方电气', '中国神华']},
            '高端制造': {'weight': 0.2, 'beneficiaries': ['徐工机械', '特变电工', '东方电气']},
            '医药健康': {'weight': 0.15, 'beneficiaries': ['恒瑞医药']},
            '能源安全': {'weight': 0.1, 'beneficiaries': ['中国神华', '宝丰能源', '特变电工']}
        }
    
    def load_historical_data(self, excel_path):
        raw_df = pd.read_excel(excel_path)
        df = raw_df.copy()
        df['日期'] = pd.to_datetime(df['日期'])
        df['code'] = df['Wind代码'].str.split('.').str[0]
        self.df = df.sort_values('日期')
        
        self.historical_returns = pd.DataFrame()
        for code in self.codes:
            prices = self.df[self.df['code'] == code][['日期', '收盘价']].set_index('日期')
            prices.columns = ['close']
            prices['return'] = prices['close'].pct_change().fillna(0)
            self.historical_returns[code] = prices['return']
        
        self.historical_returns = self.historical_returns.dropna()
        self.base_annual_return = self.historical_returns.mean().mean() * 252
        
        print(f"📊 历史年化收益基准: {self.base_annual_return:.2%}")
    
    def get_kangbo_factor(self, year):
        for phase, info in self.kangbo_phases.items():
            if year in info['years']:
                return info['factor'], info['name']
        return 1.0, '平稳期'
    
    def get_theme_exposure(self, stock_name):
        exposure = 0
        themes = []
        for theme, info in self.fifteen_five_themes.items():
            if stock_name in info['beneficiaries']:
                exposure += info['weight']
                themes.append(theme)
        return exposure, themes
    
    def analyze_portfolio_theme_exposure(self):
        print("\n🎯 持仓标的十五五规划主题敞口分析")
        print("-" * 70)
        
        total_exposure = 0
        for code in self.codes:
            name = self.names[code]
            weight = self.target_weights[code]
            exposure, themes = self.get_theme_exposure(name)
            
            weighted_exposure = exposure * weight
            total_exposure += weighted_exposure
            
            themes_str = ", ".join(themes) if themes else "无"
            print(f"{name:<10} 权重:{weight*100:>4.1f}% 主题敞口:{exposure*100:>5.1f}% 相关主题: {themes_str}")
        
        print("-" * 70)
        print(f"📊 组合整体主题敞口: {total_exposure*100:.1f}%")
        return total_exposure
    
    def predict_by_kangbo_cycle(self, start_year=2026, years=10):
        print("\n" + "="*70)
        print("🔄 康波周期分析")
        print("="*70)
        
        annual_factors = []
        total_factor = 1.0
        
        for year in range(start_year, start_year + years):
            factor, phase = self.get_kangbo_factor(year)
            annual_factors.append({'year': year, 'phase': phase, 'factor': factor})
            total_factor *= factor
        
        print("\n📅 康波周期阶段划分:")
        for item in annual_factors:
            print(f"  {item['year']}年: {item['phase']} (乘数:{item['factor']:.2f})")
        
        compound_factor = total_factor ** (1/years)
        print(f"\n📊 10年复合周期因子: {compound_factor:.2f}")
        
        return compound_factor, annual_factors
    
    def predict_with_macro_factors(self):
        print("\n" + "="*70)
        print("🎯 综合宏观因素预测")
        print("="*70)
        
        kangbo_factor, _ = self.predict_by_kangbo_cycle()
        theme_exposure = self.analyze_portfolio_theme_exposure()
        
        base_return = self.base_annual_return
        
        kangbo_adjustment = kangbo_factor - 1
        
        theme_boost = theme_exposure * 0.05
        
        policy_risk = 0.95
        
        adjusted_return = (1 + base_return) * (1 + kangbo_adjustment) * (1 + theme_boost) * policy_risk - 1
        
        print(f"\n📈 收益率分解:")
        print(f"  历史基准收益: {base_return:.2%}")
        print(f"  康波周期调整: +{kangbo_adjustment:.2%}")
        print(f"  十五五主题溢价: +{theme_boost:.2%}")
        print(f"  政策风险系数: ×{policy_risk}")
        print(f"  ───────────────────────")
        print(f"  🎯 调整后预期年化: {adjusted_return:.2%}")
        
        return {
            'base_return': base_return,
            'kangbo_factor': kangbo_factor,
            'kangbo_adjustment': kangbo_adjustment,
            'theme_exposure': theme_exposure,
            'theme_boost': theme_boost,
            'policy_risk': policy_risk,
            'adjusted_return': adjusted_return
        }
    
    def generate_comprehensive_report(self):
        print("\n" + "="*70)
        print("📋 综合分析报告 - 康波周期 × 十五五规划")
        print("="*70)
        
        predictions = self.predict_with_macro_factors()
        
        initial_capital = 3000000
        years = 10
        final_value = initial_capital * (1 + predictions['adjusted_return']) ** years
        
        print(f"\n💰 10年投资回报预测 (初始资金 ¥{initial_capital/10000:.0f}万)")
        print(f"  预期最终净值: ¥{final_value/10000:.1f}万")
        print(f"  总收益率: {(final_value/initial_capital - 1):.2%}")
        
        print(f"\n⚡ 关键假设:")
        print(f"  • 康波周期当前处于回升期，2027-2031年进入繁荣期")
        print(f"  • 十五五规划重点支持科技创新、绿色发展等领域")
        print(f"  • 当前持仓与十五五主题契合度: {predictions['theme_exposure']*100:.1f}%")
        
        print(f"\n💡 投资建议:")
        if predictions['adjusted_return'] >= 0.15:
            print("  ✅ 当前宏观环境有利，建议适度增加权益仓位")
        elif predictions['adjusted_return'] >= 0.08:
            print("  ⚠️ 预期收益尚可，建议保持现有配置")
        else:
            print("  📉 建议降低风险资产比例，增加防御性配置")
        
        return predictions
    
    def run(self, excel_path):
        print("""
╔═══════════════════════════════════════════════════════════╗
║         宏观分析模块 - 康波周期 × 十五五规划             ║
║                    持仓收益率预测                        ║
╚═══════════════════════════════════════════════════════════╝
        """)
        
        self.load_historical_data(excel_path)
        return self.generate_comprehensive_report()

def main():
    excel_path = r'e:\各种PY程序\12个标的2024年12月1日至2026年5月25日完整日度行情数据.xlsx'
    
    analyzer = MacroAnalyzer()
    analyzer.run(excel_path)

if __name__ == '__main__':
    main()