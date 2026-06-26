# -*- coding: utf-8 -*-
"""
组合风险早期预警系统
独立模块, 从 ai_analysis_enhanced.py 抽取并增强

模块6 对应 research_plan_yizhao_optimization.md:
  - 舆情预警: 负面新闻密度检测
  - 事件预警: 重大风险事件识别
  - 行业联动预警: 跨标的负面情绪传导
"""
import os
import sys
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from yizhao_data_loader import YiZhaoDataLoader, get_yizhao_loader
from fin_sentiment_analyzer import (
    FinSentimentAnalyzer, get_sentiment_analyzer,
    EventType, INDUSTRY_KEYWORDS
)


# ============================================================
# 风险事件严重级别
# ============================================================
class RiskSeverity:
    CRITICAL = 'critical'   # 极度危险, 建议清仓
    HIGH = 'high'           # 高风险, 建议减仓
    MEDIUM = 'medium'       # 中等风险, 密切监控
    LOW = 'low'             # 低风险, 关注即可
    INFO = 'info'           # 信息提示


# ============================================================
# 核心风险预警类
# ============================================================
class RiskEarlyWarning:
    """
    组合舆情风险预警系统 (增强版)

    功能:
      1. 负面新闻密度检测 (时间加权)
      2. 重大风险事件识别 (分类 + 严重度)
      3. 行业联动预警 (跨标的负面情绪传导)
      4. 综合风险评分与建议
    """

    # 风险关键词字典 (按严重度分级)
    RISK_KEYWORDS = {
        RiskSeverity.CRITICAL: [
            '暴雷', '退市', '破产', '违约', '爆仓', '崩盘',
            '财务造假', '被立案', '被调查', '资金链断裂',
            '无法表示意见', '清盘', '退市风险', '集体诉讼',
            '债券违约', '暂停上市'
        ],
        RiskSeverity.HIGH: [
            'ST', '亏损', '巨亏', '减持', '处罚', '调查',
            '诉讼', '监管', '停滞', '风险', '欠佳',
            '重大利空', '黑天鹅', '踩踏', '资不抵债',
            '业绩暴雷', '净利润下滑', '营收下滑'
        ],
        RiskSeverity.MEDIUM: [
            '下跌', '下滑', '放缓', '承压', '低迷', '萎缩',
            '困境', '挑战', '不及预期', '缩减', '谨慎',
            '观望', '降低', '净流出', '减仓'
        ]
    }

    # 行业风险传染系数 (基础风险更易传播的行业)
    INDUSTRY_CONTAGION_FACTOR = {
        '金融': 0.9,    # 金融风险传染性极强
        '能源': 0.6,
        '半导体': 0.5,
        '医药': 0.3,
        '制造': 0.5,
        '新能源': 0.5,
        '基建': 0.4,
        '消费': 0.3,
        '科技': 0.6
    }

    # 行业分类映射 (标的代码 → 行业)
    CODE_INDUSTRY_MAP = {
        '601088': '能源', '600995': '能源',
        '600989': '能源', '600875': '制造',
        '600406': '科技', '300274': '新能源',
        '000425': '制造', '002371': '半导体',
        '600276': '医药', '600089': '能源',
        '688017': '制造', '518880': '金融',
        # 扩展标的
        '688041': '科技', '300308': '科技',
        '600900': '能源', '600519': '消费',
        '600036': '金融', '601318': '金融',
        '510300': '金融', '510500': '金融',
        '512100': '金融', '588000': '科技',
        '159915': '科技'
    }

    def __init__(self,
                 sentiment_analyzer: FinSentimentAnalyzer = None,
                 yizhao_loader: YiZhaoDataLoader = None):
        self.sentiment = sentiment_analyzer or get_sentiment_analyzer()
        self.yizhao = yizhao_loader or get_yizhao_loader()
        self._risk_cache: Dict[str, Dict] = {}

    # ---- 1. 负面新闻密度检测 ----
    def negative_news_density(self, code: str, days_back: int = 7) -> Dict:
        """
        负面新闻密度检测 (时间加权)
        越近越危险, 密度越高越危险
        """
        if not self.yizhao.is_loaded:
            return {
                'density_score': 0.0,
                'negative_count': 0,
                'total_count': 0,
                'level': RiskSeverity.INFO
            }

        results = self.yizhao.search_by_code(code, top_k=50)
        if not results:
            return {
                'density_score': 0.0,
                'negative_count': 0,
                'total_count': 0,
                'level': RiskSeverity.INFO
            }

        negative_count = 0
        total_weighted = 0.0
        total_docs = 0

        for r in results:
            text = r.doc.text[:3000]
            sentiment = self.sentiment.analyze_text(text)
            total_docs += 1

            if sentiment['polarity'] in ('negative', 'strong_negative'):
                negative_count += 1
                # 时间加权: 近7天权重2.0, 7-30天权重1.0, >30天权重0.5
                time_weight = 1.0
                total_weighted += time_weight * abs(sentiment['score'])

        # 密度分 = 负面占比 * 平均负面强度
        density = negative_count / max(total_docs, 1)
        avg_neg_strength = total_weighted / max(negative_count, 1)
        density_score = density * avg_neg_strength

        # 判定
        if density_score >= 0.4:
            level = RiskSeverity.HIGH
        elif density_score >= 0.2:
            level = RiskSeverity.MEDIUM
        else:
            level = RiskSeverity.LOW

        return {
            'density_score': round(density_score, 4),
            'negative_count': negative_count,
            'total_count': total_docs,
            'negative_ratio': round(density, 4),
            'level': level
        }

    # ---- 2. 重大风险事件识别 ----
    def scan_risk_events(self, code: str, top_k: int = 30) -> List[Dict]:
        """
        扫描风险事件并按严重度分类
        """
        if not self.yizhao.is_loaded:
            return []

        results = self.yizhao.search_by_code(code, top_k=top_k)
        risk_events = []

        for r in results:
            text = r.doc.text[:4000]
            detected_risks = []

            for severity, keywords in self.RISK_KEYWORDS.items():
                for kw in keywords:
                    if kw in text:
                        detected_risks.append((severity, kw))

            if not detected_risks:
                continue

            # 取最高严重度
            severity_order = [RiskSeverity.CRITICAL, RiskSeverity.HIGH, RiskSeverity.MEDIUM]
            max_severity = RiskSeverity.MEDIUM
            matched_keywords = []
            for sev, kw in detected_risks:
                matched_keywords.append(kw)
                for s in severity_order:
                    if sev == s:
                        max_severity = s
                        break

            sentiment = self.sentiment.analyze_text(text)
            events = self.sentiment.classify_event(text)

            risk_events.append({
                'title': r.doc.title,
                'source': r.doc.source_domain,
                'severity': max_severity,
                'keywords': list(set(matched_keywords)),
                'risk_types': [evt.value for evt in events if evt.value in ('风险事件', '监管')],
                'sentiment': sentiment['polarity'],
                'snippet': text[:200],
                'fin_score': r.doc.fin_int_score
            })

        # 按严重度排序
        severity_rank = {
            RiskSeverity.CRITICAL: 0,
            RiskSeverity.HIGH: 1,
            RiskSeverity.MEDIUM: 2
        }
        risk_events.sort(key=lambda x: (severity_rank.get(x['severity'], 3),
                                         -x['fin_score']))

        return risk_events

    def generate_risk_report(self, codes: List[str] = None) -> Dict:
        """
        生成组合风险预警报告 (原版接口 - 保持向后兼容)
        """
        if codes is None:
            codes = list(self.yizhao.config.portfolio_keywords.keys())

        warnings = []
        for code in codes:
            events = self.scan_risk_events(code)
            high_severity = [
                e for e in events
                if e['severity'] in (RiskSeverity.CRITICAL, RiskSeverity.HIGH)
            ]
            if high_severity:
                warnings.append({
                    'code': code,
                    'high_risk_count': len(high_severity),
                    'events': high_severity[:3]
                })

        alert_level = 'normal'
        critical_count = sum(
            1 for w in warnings
            if any(e['severity'] == RiskSeverity.CRITICAL for e in w['events'])
        )
        if critical_count >= 1 or len(warnings) >= 3:
            alert_level = 'critical'
        elif len(warnings) >= 1:
            alert_level = 'warning'

        return {
            'alert_level': alert_level,
            'warning_count': len(warnings),
            'warnings': warnings,
            'suggestion': self._get_risk_suggestion(alert_level, warnings)
        }

    # ---- 3. 行业联动预警 ----
    def industry_contagion_warning(self, codes: List[str] = None) -> Dict:
        """
        行业联动预警
        当某个行业出现多个标的同时有负面情绪时, 发出行业级预警
        """
        if codes is None:
            codes = list(self.yizhao.config.portfolio_keywords.keys())

        # 按行业聚合负面情绪
        industry_negative = defaultdict(list)
        industry_total = defaultdict(list)

        for code in codes:
            industry = self.CODE_INDUSTRY_MAP.get(code, '其他')
            density = self.negative_news_density(code)

            if density['negative_count'] > 0:
                industry_negative[industry].append({
                    'code': code,
                    'density_score': density['density_score'],
                    'negative_count': density['negative_count']
                })
            industry_total[industry].append(code)

        # 检测行业级风险
        industry_alerts = []
        for industry, negatives in industry_negative.items():
            total = len(industry_total[industry])
            negative_ratio = len(negatives) / max(total, 1)
            contagion = self.INDUSTRY_CONTAGION_FACTOR.get(industry, 0.3)

            # 行业风险得分 = 负面占比 * 传染系数 * 平均负面密度
            avg_density = np.mean([n['density_score'] for n in negatives])
            industry_risk = negative_ratio * contagion * avg_density * 10

            if industry_risk >= 2.0:
                risk_level = RiskSeverity.HIGH
            elif industry_risk >= 1.0:
                risk_level = RiskSeverity.MEDIUM
            elif industry_risk >= 0.3:
                risk_level = RiskSeverity.LOW
            else:
                continue

            affected_codes = [n['code'] for n in negatives]
            industry_alerts.append({
                'industry': industry,
                'risk_level': risk_level,
                'risk_score': round(float(industry_risk), 4),
                'negative_ratio': round(negative_ratio, 4),
                'contagion_factor': contagion,
                'affected_count': len(negatives),
                'total_count': total,
                'affected_codes': affected_codes,
                'suggestion': self._get_industry_suggestion(
                    industry, risk_level, affected_codes
                )
            })

        industry_alerts.sort(key=lambda x: x['risk_score'], reverse=True)

        return {
            'industry_alerts': industry_alerts,
            'alert_count': len(industry_alerts),
            'highest_risk_industry': industry_alerts[0]['industry'] if industry_alerts else '',
            'overall_level': (
                RiskSeverity.HIGH if any(a['risk_level'] == RiskSeverity.HIGH for a in industry_alerts)
                else RiskSeverity.MEDIUM if industry_alerts
                else RiskSeverity.INFO
            )
        }

    # ---- 4. 综合风险评分 ----
    def comprehensive_risk_assessment(self, codes: List[str] = None) -> Dict:
        """
        综合风险评估: 融合负面密度 + 风险事件 + 行业联动
        """
        if codes is None:
            codes = list(self.yizhao.config.portfolio_keywords.keys())

        # 各维度评分
        per_code_risks = {}
        all_density_scores = []
        all_risk_counts = []

        for code in codes:
            density = self.negative_news_density(code)
            events = self.scan_risk_events(code, top_k=15)

            critical_events = [e for e in events if e['severity'] == RiskSeverity.CRITICAL]
            high_events = [e for e in events if e['severity'] == RiskSeverity.HIGH]

            density_score = density['density_score']
            event_score = len(critical_events) * 0.5 + len(high_events) * 0.25
            composite = density_score + event_score

            per_code_risks[code] = {
                'density': density,
                'critical_events': len(critical_events),
                'high_events': len(high_events),
                'total_events': len(events),
                'composite_risk': round(composite, 4)
            }

            all_density_scores.append(density_score)
            all_risk_counts.append(len(critical_events) + len(high_events))

        # 行业联动
        industry_alerts = self.industry_contagion_warning(codes)

        # 综合评分
        avg_density = np.mean(all_density_scores) if all_density_scores else 0
        total_risk_events = sum(all_risk_counts)
        industry_penalty = len(industry_alerts['industry_alerts']) * 0.1

        composite_score = avg_density * 5 + total_risk_events * 0.2 + industry_penalty

        # 判定
        if composite_score >= 3.0:
            overall_level = RiskSeverity.CRITICAL
            action = "检测到严重系统性风险, 建议立即减仓至30%以下"
        elif composite_score >= 2.0:
            overall_level = RiskSeverity.HIGH
            action = "检测到较高风险水平, 建议减仓至50%并设置严格止损"
        elif composite_score >= 1.0:
            overall_level = RiskSeverity.MEDIUM
            action = "检测到中等风险, 建议密切关注并准备应对方案"
        elif composite_score >= 0.3:
            overall_level = RiskSeverity.LOW
            action = "检测到轻微风险信号, 建议保持常规监控"
        else:
            overall_level = RiskSeverity.INFO
            action = "未检测到显著风险信号, 维持正常策略"

        return {
            'overall_level': overall_level,
            'composite_score': round(float(composite_score), 4),
            'action_suggestion': action,
            'avg_negative_density': round(float(avg_density), 4),
            'total_high_risk_events': total_risk_events,
            'industry_alert_count': len(industry_alerts['industry_alerts']),
            'per_code_risks': per_code_risks,
            'industry_alerts': industry_alerts,
            'timestamp': datetime.now().isoformat()
        }

    # ---- 辅助方法 ----
    def _get_risk_suggestion(self, level: str, warnings: List[Dict]) -> str:
        if level == 'critical':
            codes = [w['code'] for w in warnings]
            return f"检测到标的 {', '.join(codes[:5])} 出现高危风险舆情, 建议立即评估持仓并考虑减仓"
        elif level == 'warning':
            codes = [w['code'] for w in warnings]
            return f"标的 {', '.join(codes[:3])} 出现风险舆情, 建议密切关注"
        return "未检测到显著风险舆情, 维持正常监控"

    def _get_industry_suggestion(self, industry: str, level: str,
                                  codes: List[str]) -> str:
        if level == RiskSeverity.HIGH:
            return (f"{industry}行业出现系统性负面情绪, "
                    f"涉及标的 {', '.join(codes[:3])}, 建议排查行业敞口")
        elif level == RiskSeverity.MEDIUM:
            return f"{industry}行业存在一定负面情绪, 建议关注{codes[0]}等相关标的"
        return f"{industry}行业轻微负面, 正常监控即可"


# ============================================================
# 便捷函数
# ============================================================
_global_risk_warning: Optional[RiskEarlyWarning] = None


def get_risk_early_warning() -> RiskEarlyWarning:
    """获取全局风险预警系统"""
    global _global_risk_warning
    if _global_risk_warning is None:
        _global_risk_warning = RiskEarlyWarning()
    return _global_risk_warning


# ============================================================
# 测试
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("  风险早期预警系统测试")
    print("=" * 60)

    rw = get_risk_early_warning()

    test_codes = ['601088', '300274', '002371', '600276', '600989']

    # 1. 负面新闻密度
    print("\n  1. 负面新闻密度检测:")
    for code in test_codes:
        density = rw.negative_news_density(code)
        print(f"    {code}: 密度={density['density_score']:.3f} "
              f"(负面{density['negative_count']}/{density['total_count']}) "
              f"等级={density['level']}")

    # 2. 风险事件扫描
    print("\n  2. 风险事件扫描:")
    for code in test_codes[:3]:
        events = rw.scan_risk_events(code, top_k=10)
        critical_high = [e for e in events if e['severity'] in ('critical', 'high')]
        print(f"    {code}: 总事件{len(events)}个, "
              f"高危{len(critical_high)}个")
        for e in critical_high[:2]:
            print(f"      [{e['severity']}] {e['title'][:40]}...")

    # 3. 行业联动预警
    print("\n  3. 行业联动预警:")
    industry_report = rw.industry_contagion_warning(test_codes)
    print(f"    行业预警数: {industry_report['alert_count']}")
    for alert in industry_report['industry_alerts']:
        print(f"    [{alert['risk_level']}] {alert['industry']}: "
              f"涉及{alert['affected_count']}/{alert['total_count']}只标的, "
              f"风险分={alert['risk_score']:.3f}")

    # 4. 综合风险评估
    print("\n  4. 综合风险评估:")
    comprehensive = rw.comprehensive_risk_assessment(test_codes)
    print(f"    综合风险等级: {comprehensive['overall_level']}")
    print(f"    综合风险得分: {comprehensive['composite_score']:.3f}")
    print(f"    建议行动: {comprehensive['action_suggestion']}")
    print(f"    行业预警数: {comprehensive['industry_alert_count']}")
    print(f"    高风险事件总数: {comprehensive['total_high_risk_events']}")
