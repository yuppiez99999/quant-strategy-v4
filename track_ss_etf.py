# -*- coding: utf-8 -*-
"""
国家队ETF资金流向追踪
"""

from utils.social_security_etf import SocialSecurityStyleClassifier, NationalTeamSignalDetector

def main():
    print('='*70)
    print(' 国家队ETF资金流向追踪报告')
    print('='*70)
    
    classifier = SocialSecurityStyleClassifier()
    detector = NationalTeamSignalDetector()
    
    print('\n ETF风格分类:')
    print('-'*70)
    print('{:<12} {:<20} {:<12} {:<10} {:<10}'.format(
        'ETF代码', 'ETF名称', '社保风格', '匹配度', '建议配置'
    ))
    print('-'*70)
    
    etf_classifications = classifier.get_all_etf_classifications()
    for etf in etf_classifications:
        print('{:<12} {:<20} {:<12} {:<10} {:<10}'.format(
            etf['code'], etf['name'], etf['social_style'], 
            str(etf['match_score'])+'%', etf['recommended_action']
        ))
    
    print('\n 社保基金风格配置:')
    print('-'*70)
    style_summary = classifier.get_style_summary()
    for style, info in style_summary.items():
        print('  {} (权重{}): {}'.format(style, info['weight'], info['description']))
        print('     → 建议: {}, {}'.format(info['recommended_action'], info['cycle_signal']))
        print('     → 代表ETF: {}'.format(', '.join(info['top_etfs'])))
    
    print('\n 策略建议:')
    print('  1. 关注资金持续流入的ETF标的')
    print('  2. 结合康波周期判断入场时机')
    print('  3. 注意风险控制，设置合理止损')

if __name__ == '__main__':
    main()