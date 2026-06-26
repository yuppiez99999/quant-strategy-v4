# -*- coding: utf-8 -*-
"""
十五五规划适配分析模块 v1.0
借鉴：TradingAgents-AShare macro_analyst + QuantDinger policy 矩阵 + FinceptTerminal policy_analysis

功能：
  1. 十五五规划（2026-2030）核心产业方向映射
  2. 持仓标的与规划方向对齐度评分
  3. 政策驱动的权重调整建议
  4. 生成十五五适配报告
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional


# ============================================================
# 十五五规划核心产业方向定义
# 借鉴 QuantDinger 的 broker-market policy 矩阵设计
# ============================================================

# 十五五规划（2026-2030）七大战略方向
FIFTEEN_FIVE_POLICIES = {
    "新质生产力": {
        "weight": 0.25,
        "description": "以科技创新为核心驱动力，培育新产业、新模式、新动能",
        "keywords": ["AI", "人工智能", "大模型", "算力", "机器人", "量子计算",
                      "低空经济", "商业航天", "6G", "脑机接口"],
        "target_sectors": ["半导体", "AI算力", "软件服务", "通信设备", "航空航天"],
        "relevance_score": 95,  # 政策优先级 0-100
    },
    "制造强国": {
        "weight": 0.20,
        "description": "推动制造业高端化、智能化、绿色化发展",
        "keywords": ["高端装备", "智能制造", "数控机床", "工业母机", "新材料",
                      "新能源汽车", "轨道交通", "船舶制造", "航空航天"],
        "target_sectors": ["高端制造", "机械设备", "汽车", "新材料", "军工"],
        "relevance_score": 90,
    },
    "数字中国": {
        "weight": 0.15,
        "description": "加快数字化发展，建设数字中国",
        "keywords": ["数据要素", "大数据", "云计算", "物联网", "区块链",
                      "工业互联网", "智慧城市", "数字政府", "数字人民币"],
        "target_sectors": ["软件服务", "云计算", "数据要素", "金融科技", "通信"],
        "relevance_score": 88,
    },
    "绿色低碳": {
        "weight": 0.15,
        "description": "推动能源革命，实现碳达峰碳中和目标",
        "keywords": ["光伏", "风电", "储能", "氢能", "核能", "碳交易",
                      "新型电力系统", "特高压", "节能环保", "新能源车"],
        "target_sectors": ["新能源", "储能", "电力", "环保", "新能源汽车"],
        "relevance_score": 85,
    },
    "健康中国": {
        "weight": 0.10,
        "description": "全面推进健康中国建设，发展生物医药产业",
        "keywords": ["创新药", "生物制药", "医疗器械", "精准医疗", "基因治疗",
                      "中医药", "智慧医疗", "养老产业", "健康管理"],
        "target_sectors": ["医药", "医疗器械", "生物科技", "医疗服务"],
        "relevance_score": 80,
    },
    "安全发展": {
        "weight": 0.10,
        "description": "统筹发展和安全，保障粮食/能源/产业链安全",
        "keywords": ["粮食安全", "能源安全", "种业", "关键矿产", "稀土",
                      "信创", "国产替代", "网络安全", "军工"],
        "target_sectors": ["农业", "能源", "矿产", "信息安全", "军工"],
        "relevance_score": 82,
    },
    "区域协调": {
        "weight": 0.05,
        "description": "推进区域协调发展和新型城镇化",
        "keywords": ["城市群", "都市圈", "县域经济", "乡村振兴", "新型城镇化"],
        "target_sectors": ["基建", "建材", "交通运输", "房地产"],
        "relevance_score": 65,
    },
}


# ============================================================
# 持仓标的与十五五方向对齐映射表
# ============================================================

# 当前持仓标的的十五五适配评分（0-100）
# 评分依据：公司主营业务与十五五规划七大方向的匹配度
STOCK_POLICY_ALIGNMENT = {
    # 个股
    "601088": {  # 中国神华
        "name": "中国神华",
        "alignments": {
            "绿色低碳": 75,    # 煤炭清洁利用+能源安全
            "安全发展": 85,    # 能源安全核心标的
        },
        "overall_score": 78,
        "rationale": "煤炭龙头+能源安全核心标的，十五五期间受益于能源保供政策",
    },
    "600276": {  # 恒瑞医药
        "name": "恒瑞医药",
        "alignments": {
            "健康中国": 92,    # 创新药龙头，健康中国核心受益
            "新质生产力": 80,  # 生物科技创新
        },
        "overall_score": 88,
        "rationale": "创新药龙头，健康中国+新质生产力双驱动",
    },

    # ETF
    "510300": {  # 沪深300ETF
        "name": "沪深300ETF",
        "alignments": {
            "制造强国": 80,
            "数字中国": 75,
            "绿色低碳": 70,
            "新质生产力": 75,
        },
        "overall_score": 75,
        "rationale": "宽基指数覆盖十五五全方向，但缺乏聚焦",
    },
    "512100": {  # 中证1000ETF
        "name": "中证1000ETF",
        "alignments": {
            "新质生产力": 85,
            "制造强国": 82,
            "数字中国": 80,
        },
        "overall_score": 82,
        "rationale": "小盘成长覆盖大量专精特新企业，与十五五新质生产力高度匹配",
    },
    "588000": {  # 科创50ETF
        "name": "科创50ETF",
        "alignments": {
            "新质生产力": 95,
            "数字中国": 90,
            "制造强国": 85,
            "健康中国": 80,
        },
        "overall_score": 92,
        "rationale": "科创板核心标的，十五五规划最直接受益的ETF，新质生产力旗舰",
    },
    "159915": {  # 创业板ETF
        "name": "创业板ETF",
        "alignments": {
            "新质生产力": 88,
            "数字中国": 85,
            "绿色低碳": 82,
            "健康中国": 78,
        },
        "overall_score": 85,
        "rationale": "创业板覆盖成长创新企业，十五五多方向受益",
    },
    "518880": {  # 华安黄金ETF
        "name": "华安黄金ETF",
        "alignments": {
            "安全发展": 70,    # 避险资产，安全底线
        },
        "overall_score": 45,
        "rationale": "黄金ETF与十五五产业政策关联度低，主要作为避险配置和康波周期对冲",
    },
}


# ============================================================
# 十五五适配分析器
# ============================================================

class FifteenFivePlanAnalyzer:
    """
    十五五规划适配分析器 v1.0
    借鉴 FinceptTerminal policy_analysis 的政策分析框架
    """

    def __init__(self):
        self.policies = FIFTEEN_FIVE_POLICIES
        self.alignments = STOCK_POLICY_ALIGNMENT

    # ---------- 政策概览 ----------

    def get_policy_overview(self) -> List[Dict]:
        """获取十五五政策方向概览"""
        overview = []
        for name, detail in self.policies.items():
            overview.append({
                "direction": name,
                "weight": detail["weight"],
                "description": detail["description"],
                "relevance_score": detail["relevance_score"],
                "target_sectors": detail["target_sectors"],
                "keywords": detail["keywords"][:5],  # 前5个关键词
            })
        # 按权重排序
        overview.sort(key=lambda x: x["weight"], reverse=True)
        return overview

    # ---------- 持仓适配分析 ----------

    def analyze_holdings(self, positions: Dict = None) -> List[Dict]:
        """
        分析持仓与十五五规划的对齐度

        Args:
            positions: 持仓字典 {code: {shares, avg_cost, ...}}，None则使用内置映射

        Returns:
            每个标的的对齐分析结果列表
        """
        results = []

        for code, alignment in self.alignments.items():
            pos_info = positions.get(code, {}) if positions else {}
            shares = pos_info.get("shares", 0) if pos_info else 0

            result = {
                "code": code,
                "name": alignment["name"],
                "shares": shares,
                "overall_score": alignment["overall_score"],
                "rationale": alignment["rationale"],
                "alignments": alignment["alignments"],
                "top_policies": sorted(
                    alignment["alignments"].items(),
                    key=lambda x: x[1], reverse=True
                )[:3],
            }

            # 分级判定
            if alignment["overall_score"] >= 90:
                result["grade"] = "A - 高度契合"
            elif alignment["overall_score"] >= 75:
                result["grade"] = "B - 良好契合"
            elif alignment["overall_score"] >= 60:
                result["grade"] = "C - 一般契合"
            else:
                result["grade"] = "D - 关联度低"

            results.append(result)

        results.sort(key=lambda x: x["overall_score"], reverse=True)
        return results

    # ---------- 权重调整建议 ----------

    def get_weight_adjustments(self, positions: Dict = None) -> List[Dict]:
        """
        基于十五五适配评分生成权重调整建议
        借鉴 QuantDinger policy 矩阵的配置推荐逻辑
        """
        analysis = self.analyze_holdings(positions)
        adjustments = []

        # 计算加权平均适配分
        total_score = sum(a["overall_score"] for a in analysis)
        avg_score = total_score / max(len(analysis), 1)

        for a in analysis:
            deviation = a["overall_score"] - avg_score

            if deviation >= 10:
                suggestion = "强烈建议超配"
                adjust_pct = min(5.0, round(deviation / 10, 1))
            elif deviation >= 5:
                suggestion = "建议超配"
                adjust_pct = min(3.0, round(deviation / 15, 1))
            elif deviation >= -5:
                suggestion = "维持当前权重"
                adjust_pct = 0
            elif deviation >= -10:
                suggestion = "建议适度低配"
                adjust_pct = max(-3.0, round(deviation / 15, 1))
            else:
                suggestion = "建议低配"
                adjust_pct = max(-5.0, round(deviation / 10, 1))

            adjustments.append({
                "code": a["code"],
                "name": a["name"],
                "grade": a["grade"],
                "fifteen_score": a["overall_score"],
                "deviation_from_avg": round(deviation, 1),
                "suggestion": suggestion,
                "weight_adjust_pct": adjust_pct,
            })

        return adjustments

    # ---------- 报告生成 ----------

    def generate_report(self, positions: Dict = None, save_dir: str = None) -> str:
        """生成十五五适配分析报告"""
        overview = self.get_policy_overview()
        analysis = self.analyze_holdings(positions)
        adjustments = self.get_weight_adjustments(positions)

        lines = []
        lines.append("# 十五五规划适配分析报告")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**分析引擎**: FifteenFivePlanAnalyzer v1.0")
        lines.append(f"**规划周期**: 2026-2030（十五五规划）")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 一、十五五政策概览
        lines.append("## 一、十五五规划七大战略方向")
        lines.append("")
        lines.append("| 战略方向 | 权重 | 政策优先级 | 核心领域 |")
        lines.append("|---------|------|-----------|---------|")
        for o in overview:
            keywords_str = "、".join(o["keywords"][:3])
            lines.append(f"| **{o['direction']}** | {o['weight']:.0%} | {o['relevance_score']} | {keywords_str} |")
        lines.append("")

        # 二、持仓适配评级
        lines.append("---")
        lines.append("## 二、持仓标的十五五适配评级")
        lines.append("")
        lines.append("| 标的 | 代码 | 适配评分 | 等级 | 核心契合方向 | 投资逻辑 |")
        lines.append("|------|------|---------|------|------------|---------|")
        for a in analysis:
            top = a["top_policies"]
            top_str = " / ".join(f"{p[0]}({p[1]})" for p in top)
            lines.append(f"| **{a['name']}** | {a['code']} | {a['overall_score']} | {a['grade']} | {top_str} | {a['rationale']} |")
        lines.append("")

        # 三、权重调整建议
        lines.append("---")
        lines.append("## 三、十五五驱动的权重调整建议")
        lines.append("")
        lines.append("| 标的 | 十五五评分 | 偏离均值 | 建议 | 调整幅度 |")
        lines.append("|------|-----------|---------|------|---------|")
        for adj in adjustments:
            direction = "+" if adj["weight_adjust_pct"] > 0 else ""
            lines.append(f"| {adj['name']} | {adj['fifteen_score']} | {adj['deviation_from_avg']:+.1f} | **{adj['suggestion']}** | {direction}{adj['weight_adjust_pct']:.1f}% |")
        lines.append("")

        # 四、综合建议
        lines.append("---")
        lines.append("## 四、综合投资建议")
        lines.append("")

        # 找出前3名和后3名
        top3 = [a for a in analysis[:3]]
        bottom3 = [a for a in analysis[-3:] if a["overall_score"] < 60]

        lines.append("### 核心配置（十五五高适配）")
        for t in top3:
            lines.append(f"- **{t['name']}**：十五五适配评分 {t['overall_score']}，{t['rationale']}")
        lines.append("")

        if bottom3:
            lines.append("### 关注标的（十五五低适配）")
            for b in bottom3:
                lines.append(f"- **{b['name']}**：十五五适配评分 {b['overall_score']}，{b['rationale']}")
            lines.append("")

        lines.append("---")
        lines.append(f"*本报告由十五五规划适配分析引擎 v1.0 自动生成*")
        lines.append(f"*数据参考: TradingAgents-AShare / QuantDinger / FinceptTerminal*")

        report = "\n".join(lines)

        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            filepath = os.path.join(save_dir,
                f"十五五规划适配_{datetime.now().strftime('%Y%m%d')}.md")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"[FifteenFive] 报告已保存: {filepath}")

        return report


# ============================================================
# 快速测试
# ============================================================

if __name__ == "__main__":
    analyzer = FifteenFivePlanAnalyzer()

    print("\n=== 十五五政策概览 ===")
    for o in analyzer.get_policy_overview():
        print(f"  {o['direction']}: 权重={o['weight']:.0%}, 优先级={o['relevance_score']}")

    print("\n=== 持仓适配分析 ===")
    for a in analyzer.analyze_holdings():
        print(f"  {a['name']}: 评分={a['overall_score']}, 等级={a['grade']}")

    print("\n=== 权重调整建议 ===")
    for adj in analyzer.get_weight_adjustments():
        print(f"  {adj['name']}: {adj['suggestion']} ({adj['weight_adjust_pct']:+.1f}%)")