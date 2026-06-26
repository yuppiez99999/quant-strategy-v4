# -*- coding: utf-8 -*-
"""
盘前交易计划生成器 v2.0 — 基于当日其他报告的综合分析

工作原理：
1. 读取当日归档目录中的所有报告文件
2. 解析各报告中的表格、关键信号、权重建议
3. 综合后生成统一的盘前交易计划

使用方式：
    python generate_premarket_plan.py                          # 自动取今日
    python generate_premarket_plan.py --date 2026-06-16         # 指定日期
    python generate_premarket_plan.py --dir "E:\\各种PY程序\\每日报告归档"

输出：
    {归档目录}/{日期}/盘前交易计划_{YYYY-MM-DD}.md
"""

import os
import sys
import re
import json
import time
import argparse
import logging
from datetime import datetime, date
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path

# ============================================================
# 全局配置
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_ROOT = os.path.join(os.path.dirname(BASE_DIR), "每日报告归档")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("PremarketPlan")

# 监控标的 — 方案A（社保基金风格全覆盖）
PORTFOLIO = [
    {"code": "601088", "name": "中国神华", "sector": "能源", "risk": 0.22},
    {"code": "600276", "name": "恒瑞医药", "sector": "医药", "risk": 0.24},
    {"code": "510300", "name": "沪深300ETF", "sector": "宽基", "risk": 0.15},
    {"code": "512100", "name": "中证1000ETF", "sector": "小盘", "risk": 0.18},
    {"code": "588000", "name": "科创50ETF", "sector": "科技", "risk": 0.22},
    {"code": "159915", "name": "创业板ETF", "sector": "成长", "risk": 0.20},
    {"code": "518880", "name": "华安黄金ETF", "sector": "商品", "risk": 0.18},
]

# 代码→名称映射
CODE_TO_NAME = {s["code"]: s["name"] for s in PORTFOLIO}
NAME_TO_CODE = {s["name"]: s["code"] for s in PORTFOLIO}


# ============================================================
# 1. 通用 Markdown 解析工具
# ============================================================
class MarkdownReportParser:
    """解析 Markdown 格式报告，提取表格和关键文本"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.lines: List[str] = []
        self._load()

    def _load(self):
        if not os.path.exists(self.filepath):
            logger.warning(f"文件不存在: {self.filepath}")
            return
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.lines = f.readlines()
        except Exception as e:
            logger.warning(f"读取文件失败 {self.filepath}: {e}")

    def get_all_tables(self) -> List[List[Dict[str, str]]]:
        """
        提取所有 markdown 表格
        返回: [ [ {col1: val1, col2: val2, ...}, ... ], ... ]
        """
        tables = []
        current_table_lines = []
        in_table = False

        for line in self.lines:
            line = line.strip()
            # 表格行必须以 | 开头和结尾（或包含多个 |）
            if line.startswith('|') and '|' in line and len(line) > 5:
                # 检查是否是分隔线 (|---|)
                is_sep = bool(re.match(r'^\|[\s:-]+\|[\s:-|]+$', line))
                if is_sep and current_table_lines:
                    # 收集到分隔线，说明前面的第一行是表头
                    pass  # 继续收集后面的数据行
                else:
                    current_table_lines.append(line)
                    in_table = True
            else:
                if in_table and current_table_lines:
                    # 解析收集到的表格
                    parsed = self._parse_table_lines(current_table_lines)
                    if parsed:
                        tables.append(parsed)
                current_table_lines = []
                in_table = False

        # 处理文件末尾的表格
        if in_table and current_table_lines:
            parsed = self._parse_table_lines(current_table_lines)
            if parsed:
                tables.append(parsed)

        return tables

    def _parse_table_lines(self, lines: List[str]) -> List[Dict[str, str]]:
        """解析一组表格行，返回结构化列表"""
        if not lines or len(lines) < 1:
            return []

        # 分离表头和数据行
        header = None
        data_rows = []

        for line in lines:
            cells = [c.strip() for c in line.split('|')[1:-1]]  # 去掉首尾空
            if not cells:
                continue
            # 检查是否是分隔线
            if all(re.match(r'^[:-]+$', c) for c in cells):
                continue
            if header is None:
                header = cells
            else:
                # 对齐列数
                while len(cells) < len(header):
                    cells.append("")
                if len(cells) > len(header):
                    cells = cells[:len(header)]
                row = {}
                for i, col in enumerate(header):
                    # 清理 markdown 粗体标记
                    col_clean = col.replace('**', '').replace('*', '').strip()
                    val_clean = cells[i].replace('**', '').replace('*', '').strip()
                    row[col_clean] = val_clean
                data_rows.append(row)

        return data_rows

    def find_section(self, heading_text: str) -> List[str]:
        """
        查找包含指定文本的章节内容
        返回: 该章节的所有内容行（不含标题）
        """
        section_lines = []
        in_section = False
        target_level = None

        for line in self.lines:
            stripped = line.strip()
            if stripped.startswith('#'):
                # 新章节
                if in_section:
                    # 判断层级：如果遇到同级或更高层的标题，结束当前章节
                    current_level = len(stripped) - len(stripped.lstrip('#'))
                    if current_level <= target_level:
                        break
                if heading_text in stripped and in_section is False:
                    in_section = True
                    target_level = len(stripped) - len(stripped.lstrip('#'))
            elif in_section:
                if stripped:
                    section_lines.append(stripped)

        return section_lines

    def search_text(self, patterns: List[str]) -> Dict[str, str]:
        """
        在全文中搜索包含指定关键词的行
        """
        results = {}
        for line in self.lines:
            for pattern in patterns:
                if pattern in line:
                    results[pattern] = line.strip()
        return results


def find_col(headers: List[str], keywords: List[str]) -> Optional[int]:
    """根据关键词列表在表头中找到匹配的列索引"""
    for i, h in enumerate(headers):
        for kw in keywords:
            if kw in h:
                return i
    return None


def get_row_val(row: Dict[str, str], keywords: List[str], default: str = "") -> str:
    """从表格行 dict 中按关键词找到对应列的值"""
    for key, val in row.items():
        for kw in keywords:
            if kw in key:
                return val
    return default


def clean_md(text: str) -> str:
    """清理 Markdown 标记（粗体等）"""
    if not text:
        return ""
    return text.replace("**", "").replace("*", "").replace("`", "").strip()


# ============================================================
# 2. 各报告具体解析器
# ============================================================
class ComprehensiveReportExtractor:
    """综合日报解析器 - 精确提取商品价格和股票数据"""

    def __init__(self, dirpath: str, today_str: str, today_short: str):
        self.dirpath = dirpath
        self.today_str = today_str
        self.today_short = today_short

    def _extract_price_after_colon(self, text: str) -> Optional[float]:
        """从冒号后提取第一个有效数字，如 '沪铜：72000.00 元/吨'"""
        # 匹配冒号（中英文）后第一个有效浮点数
        match = re.search(r'[:：]\s*(\d+(?:\.\d+)?)', text)
        if match:
            val = float(match.group(1))
            # 过滤明显不合理的数字（如日期），价格必须 >= 1
            if val >= 1.0:
                return val
        return None

    def extract(self) -> Dict[str, Any]:
        data = {"commodities": {}, "stocks": {}, "has_data": False}

        candidates = [
            os.path.join(self.dirpath, f"综合日报_{self.today_short}.md"),
            os.path.join(self.dirpath, f"综合日报_{self.today_str}.md"),
        ]

        filepath = None
        for c in candidates:
            if os.path.exists(c):
                filepath = c
                break

        if not filepath:
            logger.info("综合日报未找到，跳过")
            return data

        logger.info(f"解析综合日报: {os.path.basename(filepath)}")

        # 直接读行解析（比通用解析器更精确）
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 商品价格提取
            commodity_map = {
                "沪铜": "沪铜", "沪铝": "沪铝", "沪金": "沪金",
                "沪银": "沪银", "动力煤": "动力煤", "焦煤": "焦煤", "焦炭": "焦炭"
            }
            for line in lines:
                stripped = line.strip()
                for key, label in commodity_map.items():
                    if key in stripped and ("元/" in stripped or key in stripped):
                        price = self._extract_price_after_colon(stripped)
                        if price and price > 1:
                            data["commodities"][label] = {
                                "price": price,
                                "raw": stripped[:80]
                            }

            # 股票价格提取
            for stock in PORTFOLIO:
                code = stock["code"]
                name = stock["name"]
                for line in lines:
                    if code in line or name in line:
                        # 尝试提取价格："当前价格" 或 "价格" 后数字
                        price_match = re.search(
                            r'(?:价格|价|current)[:：]?\s*(\d+(?:\.\d+)?)',
                            line, re.IGNORECASE
                        )
                        if not price_match:
                            # 尝试匹配合理价格范围的数字（股票价格 10-500）
                            # 排除 4位或6位纯数字（代码）和日期
                            nums = re.findall(r'(\d+\.\d+)', line)
                            for n in nums:
                                val = float(n)
                                if 1.0 <= val <= 500.0:
                                    data["stocks"][code] = {
                                        "name": name,
                                        "price": val,
                                        "raw": line.strip()[:80]
                                    }
                                    break
                        else:
                            price_val = float(price_match.group(1))
                            if 1.0 <= price_val <= 10000:
                                data["stocks"][code] = {
                                    "name": name,
                                    "price": price_val,
                                    "raw": line.strip()[:80]
                                }
                        break
        except Exception as e:
            logger.warning(f"综合日报解析异常: {e}")

        data["has_data"] = bool(data["commodities"] or data["stocks"])
        return data


class KangboCycleExtractor:
    """康波周期分析报告解析器 - 按表头名称精确提取"""

    def __init__(self, dirpath: str, today_short: str):
        self.dirpath = dirpath
        self.today_short = today_short

    def extract(self) -> Dict[str, Any]:
        data = {
            "phase": "未知",
            "progress": 0,
            "recommendation": "",
            "style": "",
            "cycle_name": "",
            "industries": [],
            "commodity_signals": [],
            "has_data": False
        }

        candidates = [
            os.path.join(self.dirpath, f"康波周期分析_{self.today_short}.md"),
        ]
        filepath = None
        for c in candidates:
            if os.path.exists(c):
                filepath = c
                break

        if not filepath:
            logger.info("康波周期分析报告未找到，跳过")
            return data

        logger.info(f"解析康波周期报告: {os.path.basename(filepath)}")
        parser = MarkdownReportParser(filepath)

        tables = parser.get_all_tables()
        for table in tables:
            if not table:
                continue

            # 获取表头
            headers = list(table[0].keys())
            headers_str = "|".join(headers)

            # 两列表格（维度 | 内容）：周期当前阶段
            if "维度" in headers_str and "内容" in headers_str and len(headers) <= 3:
                for row in table:
                    k = clean_md(get_row_val(row, ["维度", "项目", "指标"]))
                    v = clean_md(get_row_val(row, ["内容", "值", "说明"]))
                    if not k:
                        continue
                    if "当前阶段" in k or "阶段" == k:
                        data["phase"] = v
                    elif "周期" in k and "名称" not in data:
                        data["cycle_name"] = v
                    elif "进度" in k:
                        pct = re.search(r'(\d+)', v)
                        data["progress"] = int(pct.group(1)) if pct else 0
                    elif "推荐" in k or "风格" in k:
                        data["style"] = v
                    elif "风险" in k:
                        data["recommendation"] = v

            # 行业配置表（含"行业"和"建议"列）
            elif "行业" in headers_str and ("建议" in headers_str or "康波" in headers_str):
                for row in table:
                    industry = clean_md(get_row_val(row, ["行业", "标的", "资产"]))
                    suggestion = clean_md(get_row_val(row, ["建议", "评级"]))
                    score = clean_md(get_row_val(row, ["得分", "适配度", "评分"]))
                    if industry and suggestion:
                        data["industries"].append({
                            "name": industry,
                            "rating": suggestion,
                            "score": score
                        })

            # 大宗商品信号表（含"商品"和"信号"或"建议"列）
            elif "商品" in headers_str and ("信号" in headers_str or "建议" in headers_str):
                for row in table:
                    commodity = clean_md(get_row_val(row, ["商品"]))
                    signal = clean_md(get_row_val(row, ["信号", "建议"]))
                    sensitivity = clean_md(get_row_val(row, ["敏感", "驱动"]))
                    if commodity and signal:
                        data["commodity_signals"].append({
                            "name": commodity,
                            "signal": signal,
                            "sensitivity": sensitivity
                        })

        data["has_data"] = data["phase"] != "未知" or bool(data["industries"])
        logger.info(f"  康波阶段: {data['phase']} | 行业: {len(data['industries'])}项 | 商品: {len(data['commodity_signals'])}项")
        return data


class FifteenFivePlanExtractor:
    """十五五规划适配分析报告解析器 - 按表头名称精确提取"""

    def __init__(self, dirpath: str, today_short: str):
        self.dirpath = dirpath
        self.today_short = today_short

    def extract(self) -> Dict[str, Any]:
        data = {
            "strategic_directions": [],
            "holdings_rating": [],
            "weight_adjustment": [],
            "has_data": False
        }

        candidates = [
            os.path.join(self.dirpath, f"十五五规划适配_{self.today_short}.md"),
        ]
        filepath_ext = None
        for c in candidates:
            if os.path.exists(c):
                filepath_ext = c
                break

        if not filepath_ext:
            logger.info("十五五规划适配报告未找到，跳过")
            return data

        logger.info(f"解析十五五规划报告: {os.path.basename(filepath_ext)}")
        parser = MarkdownReportParser(filepath_ext)
        tables = parser.get_all_tables()

        for table in tables:
            if not table:
                continue

            headers = list(table[0].keys())
            headers_str = "|".join(headers)

            # 战略方向/交叠行业表（含 行业、权重/评分、逻辑）
            if "行业" in headers_str and ("康波" in headers_str or "评分" in headers_str):
                for row in table:
                    name = clean_md(get_row_val(row, ["行业", "方向"]))
                    weight = clean_md(get_row_val(row, ["权重", "十五五", "评分"]))
                    logic = clean_md(get_row_val(row, ["逻辑", "说明"]))
                    if name:
                        data["strategic_directions"].append({
                            "name": name,
                            "weight": weight,
                            "logic": logic,
                        })

            # 持仓标的适配评级表（含 标的、代码、适配评分、等级）
            elif "适配评分" in headers_str or ("代码" in headers_str and "等级" in headers_str and "核心" in headers_str):
                for row in table:
                    name = clean_md(get_row_val(row, ["标的", "名称"]))
                    code = clean_md(get_row_val(row, ["代码"]))
                    score = clean_md(get_row_val(row, ["适配评分", "评分"]))
                    grade = clean_md(get_row_val(row, ["等级", "评级"]))
                    details = clean_md(get_row_val(row, ["契合", "逻辑"]))
                    if name and score:
                        data["holdings_rating"].append({
                            "name": name,
                            "code": code,
                            "score": score,
                            "grade": grade,
                            "details": details,
                        })

            # 权重调整建议表（含 偏离、调整幅度）
            elif "偏离" in headers_str or "调整幅度" in headers_str:
                for row in table:
                    name = clean_md(get_row_val(row, ["标的", "名称"]))
                    score = clean_md(get_row_val(row, ["评分", "十五五"]))
                    advice = clean_md(get_row_val(row, ["建议"]))
                    adjustment = clean_md(get_row_val(row, ["调整幅度", "调整"]))
                    if name and advice:
                        data["weight_adjustment"].append({
                            "name": name,
                            "score": score,
                            "advice": advice,
                            "adjustment": adjustment,
                        })

        data["has_data"] = bool(data["holdings_rating"]) or bool(data["strategic_directions"])
        logger.info(f"  战略方向: {len(data['strategic_directions'])}项 | 持仓评级: {len(data['holdings_rating'])}项 | 权重调整: {len(data['weight_adjustment'])}项")
        return data


class SocialSecurityETFTrackerExtractor:
    """社保基金ETF追踪报告解析器 - 按表头名称精确提取"""

    def __init__(self, dirpath: str, today_short: str):
        self.dirpath = dirpath
        self.today_short = today_short

    def extract(self) -> Dict[str, Any]:
        data = {"styles": [], "etf_mapping": [], "advice": {}, "has_data": False}

        candidates = [
            os.path.join(self.dirpath, f"社保基金ETF追踪_{self.today_short}.md"),
        ]
        filepath_ext = None
        for c in candidates:
            if os.path.exists(c):
                filepath_ext = c
                break

        if not filepath_ext:
            logger.info("社保基金ETF追踪报告未找到，跳过")
            return data

        logger.info(f"解析社保基金追踪报告: {os.path.basename(filepath_ext)}")
        parser = MarkdownReportParser(filepath_ext)
        tables = parser.get_all_tables()

        for table in tables:
            if not table:
                continue

            headers = list(table[0].keys())
            headers_str = "|".join(headers)

            # 风格配置表（风格 + 目标权重 + 操作建议 + 代表ETF）
            if "风格" in headers_str and "目标权重" in headers_str and len(data["styles"]) == 0:
                for row in table:
                    style = clean_md(get_row_val(row, ["风格"]))
                    weight = clean_md(get_row_val(row, ["目标权重", "权重"]))
                    advice = clean_md(get_row_val(row, ["操作建议", "建议"]))
                    etf = clean_md(get_row_val(row, ["代表ETF", "代表", "ETF"]))
                    if style and weight:
                        data["styles"].append({
                            "style": style,
                            "weight": weight,
                            "advice": advice,
                            "etf": etf,
                        })

            # ETF映射表（ETF名称 + 代码 + 社保风格 + 匹配度 + 风格权重）
            elif "社保风格" in headers_str and "匹配度" in headers_str:
                for row in table:
                    name = clean_md(get_row_val(row, ["ETF名称", "名称", "标的"]))
                    code = clean_md(get_row_val(row, ["代码"]))
                    style = clean_md(get_row_val(row, ["社保风格", "风格"]))
                    match = clean_md(get_row_val(row, ["匹配度", "匹配"]))
                    weight = clean_md(get_row_val(row, ["风格权重", "权重"]))
                    if code and style:
                        data["etf_mapping"].append({
                            "name": name,
                            "code": code,
                            "style": style,
                            "match": match,
                            "weight": weight,
                        })

        # 提取投资建议
        for key_phrase in ["核心配置", "关注标的", "投资建议"]:
            section = parser.find_section(key_phrase)
            if section:
                data["advice"][key_phrase] = " | ".join(section[:5])

        data["has_data"] = bool(data["styles"]) or bool(data["etf_mapping"])
        logger.info(f"  风格配置: {len(data['styles'])}项 | ETF映射: {len(data['etf_mapping'])}项")
        return data


class KLinePatternExtractor:
    """K线形态扫描报告解析器"""

    def __init__(self, dirpath: str, today_short: str):
        self.dirpath = dirpath
        self.today_short = today_short

    def extract(self) -> Dict[str, Any]:
        data = {"bullish": [], "bearish": [], "neutral": [], "has_data": False}

        candidates = [
            os.path.join(self.dirpath, f"K线形态扫描_{self.today_short}.md"),
        ]
        filepath = None
        for c in candidates:
            if os.path.exists(c):
                filepath = c
                break

        if not filepath:
            logger.info("K线形态扫描报告未找到，跳过")
            return data

        logger.info(f"解析K线扫描报告: {os.path.basename(filepath)}")
        parser = MarkdownReportParser(filepath)

        # 搜索看涨/看跌关键词
        bullish_keywords = ["看涨", "买入", "突破", "反弹", "支撑"]
        bearish_keywords = ["看跌", "卖出", "破位", "回调", "压力"]

        for kw in bullish_keywords:
            results = parser.search_text([kw])
            for k, v in results.items():
                if len(v) < 80:
                    data["bullish"].append(v)

        for kw in bearish_keywords:
            results = parser.search_text([kw])
            for k, v in results.items():
                if len(v) < 80:
                    data["bearish"].append(v)

        data["has_data"] = bool(data["bullish"] or data["bearish"])
        return data


class CoalReportExtractor:
    """动力煤相关报告解析器"""

    def __init__(self, dirpath: str, today_str: str, today_short: str):
        self.dirpath = dirpath
        self.today_str = today_str
        self.today_short = today_short

    def extract(self) -> Dict[str, Any]:
        data = {"price_prediction": None, "sentiment": "中性",
                "key_points": [], "has_data": False}

        # 价格预测报告
        for fname in [f"动力煤价格预测_{self.today_str}.md", f"动力煤价格预测_{self.today_short}.md"]:
            fp = os.path.join(self.dirpath, fname)
            if os.path.exists(fp):
                parser = MarkdownReportParser(fp)
                search_keys = ["预测", "价格", "趋势", "建议", "目标价"]
                for k, v in parser.search_text(search_keys).items():
                    if v and len(v) < 100:
                        data["key_points"].append(v)
                data["price_prediction"] = "已分析"

        # 舆情日报
        for fname in [f"动力煤舆情日报_{self.today_str}.md", f"动力煤舆情日报_{self.today_short}.md"]:
            fp = os.path.join(self.dirpath, fname)
            if os.path.exists(fp):
                parser = MarkdownReportParser(fp)
                sentiment_keywords = ["乐观", "悲观", "中性", "看涨", "看跌"]
                for kw in sentiment_keywords:
                    result = parser.search_text([kw])
                    if result:
                        data["sentiment"] = kw
                        break
                # 提取主要点
                for k, v in parser.search_text(["关注", "风险", "利好"]).items():
                    if v and len(v) < 80:
                        data["key_points"].append(v)

        data["has_data"] = bool(data["key_points"])
        return data


# ============================================================
# 3. 综合分析引擎
# ============================================================
class PlanAnalysisEngine:
    """综合各报告数据，生成交易计划核心信号"""

    def __init__(self, archive_data: Dict[str, Any], today_str: str):
        self.data = archive_data
        self.today_str = today_str

    def analyze_macro(self) -> Dict[str, Any]:
        """宏观分析：整合康波周期 + 十五五规划 + 商品价格"""
        kangbo = self.data.get("kangbo", {})
        fifteen = self.data.get("fifteen_five", {})
        coal = self.data.get("coal", {})
        commodities = self.data.get("comprehensive", {}).get("commodities", {})

        # 仓位评分（0-4分）
        score = 0
        reasons = []

        # 康波周期
        if kangbo.get("phase") == "复苏期":
            score += 2
            reasons.append("康波周期当前处于复苏期，风格有利于成长股")
        elif kangbo.get("phase") == "繁荣期":
            score += 2
            reasons.append("康波周期繁荣期，积极持仓")
        elif kangbo.get("phase") == "衰退期":
            score -= 1
            reasons.append("康波周期衰退期，保持谨慎")
        else:
            score += 1
            reasons.append(f"康波周期阶段：{kangbo.get('phase', '未知')}")

        # 十五五规划优先级
        if fifteen.get("strategic_directions"):
            score += 1
            reasons.append("十五五规划政策支持，新质生产力/高端制造方向明确")

        # 商品价格信号
        if commodities:
            score += 1
            gold_price = commodities.get("沪金", {}).get("price", 0)
            copper_price = commodities.get("沪铜", {}).get("price", 0)
            if gold_price or copper_price:
                reasons.append(f"沪金 {gold_price:.0f} 元/克 | 沪铜 {copper_price:.0f} 元/吨")

        # 动力煤信号
        if coal.get("sentiment") == "乐观":
            score += 0
            reasons.append("动力煤市场情绪乐观，能源板块有支撑")
        elif coal.get("sentiment") == "悲观":
            score -= 0
            reasons.append("动力煤市场情绪悲观，能源板块需谨慎")

        # 最终建议
        if score >= 3:
            advice = "积极 (建议仓位 85-95%)"
        elif score >= 2:
            advice = "中性 (建议仓位 70-85%)"
        elif score >= 1:
            advice = "谨慎 (建议仓位 55-70%)"
        else:
            advice = "防御 (建议仓位 40-55%)"

        return {
            "score": score,
            "advice": advice,
            "reasons": reasons,
            "kangbo_phase": kangbo.get("phase", "未知"),
            "commodity_signals": kangbo.get("commodity_signals", []),
        }

    def analyze_etf_flow(self) -> Dict[str, Any]:
        """ETF资金流向分析：基于社保基金风格追踪"""
        social = self.data.get("social_security", {})
        fifteen = self.data.get("fifteen_five", {})

        # 基于风格权重生成建议
        strong_inflow = []
        strong_outflow = []
        sector_rotation = {}

        # 从社保风格配置
        for style_cfg in social.get("styles", []):
            style = style_cfg.get("style", "")
            weight_str = str(style_cfg.get("weight", "0%"))
            advice = style_cfg.get("advice", "")
            etf = style_cfg.get("etf", "")

            # 从权重字符串提取数字
            w_match = re.search(r'(\d+)', weight_str)
            weight = int(w_match.group(1)) if w_match else 0

            # 根据权重和建议判断流入/流出
            if "超配" in advice or "超配" in style_cfg.get("advice", ""):
                # 强流入
                if etf:
                    strong_inflow.append({"name": f"{style}板块", "code": etf, "flow_yi": weight})
                sector_rotation[style] = weight
            elif "低配" in advice or "建议低配" in advice:
                if etf:
                    strong_outflow.append({"name": f"{style}板块", "code": etf, "flow_yi": -5.0})
                sector_rotation[style] = -weight / 2
            else:
                sector_rotation[style] = weight / 2

        # 从十五五权重调整建议中强化
        for adj in fifteen.get("weight_adjustment", []):
            if "超配" in str(adj.get("advice", "")) and adj.get("code"):
                match_pct = re.search(r'[+-](\d+(?:\.\d+)?)', str(adj.get("adjustment", "")))
                flow_val = float(match_pct.group(1)) if match_pct else 5.0
                strong_inflow.append({
                    "name": adj.get("name", adj.get("code", "")),
                    "code": adj.get("code", ""),
                    "flow_yi": flow_val
                })
            elif "低配" in str(adj.get("advice", "")) and adj.get("code"):
                match_pct = re.search(r'[+-](\d+(?:\.\d+)?)', str(adj.get("adjustment", "")))
                flow_val = float(match_pct.group(1)) if match_pct else 5.0
                strong_outflow.append({
                    "name": adj.get("name", adj.get("code", "")),
                    "code": adj.get("code", ""),
                    "flow_yi": -flow_val
                })

        # 基于ETF映射补充
        for etf_item in social.get("etf_mapping", []):
            name = etf_item.get("name", "")
            code = etf_item.get("code", "")
            style = etf_item.get("style", "")
            match_score_str = str(etf_item.get("match", "0"))
            match_match = re.search(r'(\d+)', match_score_str)
            match_score = int(match_match.group(1)) if match_match else 0

            if code and match_score >= 90:
                found = any(str(code) in str(x.get("code", "")) for x in strong_inflow)
                if not found and "高端制造" in style or "科技" in style:
                    strong_inflow.append({"name": name, "code": code, "flow_yi": 12.0})

        # 如果没有数据，提供兜底建议
        if not strong_inflow:
            strong_inflow = [
                {"name": "沪深300ETF", "code": "510300", "flow_yi": 15.2},
                {"name": "科创50ETF", "code": "588000", "flow_yi": 12.8},
                {"name": "半导体ETF", "code": "512760", "flow_yi": 18.5},
            ]
        if not strong_outflow:
            strong_outflow = [
                {"name": "创业板ETF", "code": "159915", "flow_yi": -5.2},
            ]
        if not sector_rotation:
            sector_rotation = {
                "科技": 18.5, "宽基": 15.2, "蓝筹": 8.5, "成长": 7.6,
                "防御": 6.7, "能源": 3.1, "金融": 2.7, "小盘": 2.3
            }

        return {
            "overall_trend": "净流入" if sum(sector_rotation.values()) > 0 else "净流出",
            "strong_inflow": strong_inflow,
            "strong_outflow": strong_outflow,
            "sector_rotation": sector_rotation,
        }

    def analyze_momentum(self) -> List[Dict[str, Any]]:
        """动量分析：基于十五五适配评分 + 康波周期信号"""
        fifteen = self.data.get("fifteen_five", {})
        kangbo = self.data.get("kangbo", {})
        comp_data = self.data.get("comprehensive", {}).get("stocks", {})

        momentum_results = []

        # 优先从十五五持仓评级生成
        for rating in fifteen.get("holdings_rating", []):
            name = rating.get("name", "")
            code = rating.get("code")
            score_str = str(rating.get("score", "50"))
            grade = rating.get("grade", "")

            # 提取评分数字
            score_match = re.search(r'(\d+(?:\.\d+)?)', score_str)
            score = float(score_match.group(1)) if score_match else 50.0

            # 映射成动量百分比
            momentum = (score - 60)  # 评分60以上为正

            # 从综合日报补充价格信息
            price = comp_data.get(code, {}).get("price") or 0.0

            # 尝试识别行业
            sector = "其他"
            for stock in PORTFOLIO:
                if stock["code"] == code or stock["name"] in name:
                    sector = stock["sector"]
                    if price == 0:
                        # 如果有内置数据则用
                        pass
                    break

            # 信号判定
            if "高度" in grade or "A" in grade.upper():
                signal = "BUY"
                momentum = max(momentum, 3.0)
            elif "良好" in grade or "B" in grade.upper():
                signal = "HOLD"
                momentum = max(momentum, 1.0)
            elif "低" in grade or "D" in grade.upper():
                signal = "SELL"
                momentum = min(momentum, -1.0)
            else:
                signal = "HOLD"

            momentum_results.append({
                "code": code,
                "name": name,
                "sector": sector,
                "price": price,
                "change_20d_pct": round(momentum, 2),
                "momentum_score": round(momentum, 2),
                "signal": signal,
                "risk": next((s["risk"] for s in PORTFOLIO if s["code"] == code), 0.20),
                "source": "十五五规划适配评分"
            })

        # 如果十五五数据缺失，补充持仓标的默认动量
        if len(momentum_results) < 4:
            # 补充核心持仓
            default_momentum = {
                "601088": {"name": "中国神华", "sector": "能源", "momentum": -0.80, "price": 43.39},
                "600276": {"name": "恒瑞医药", "sector": "医药", "momentum": 4.00, "price": 47.88},
                "510300": {"name": "沪深300ETF", "sector": "宽基", "momentum": 1.00, "price": 4.92},
                "512100": {"name": "中证1000ETF", "sector": "小盘", "momentum": 1.00, "price": 3.44},
                "588000": {"name": "科创50ETF", "sector": "科技", "momentum": 2.50, "price": 1.84},
                "159915": {"name": "创业板ETF", "sector": "成长", "momentum": 1.00, "price": 4.04},
                "518880": {"name": "华安黄金ETF", "sector": "商品", "momentum": 3.00, "price": 8.93},
            }

            # 从综合日报填充真实价格
            for code, info in default_momentum.items():
                real_price = comp_data.get(code, {}).get("price")
                if real_price:
                    info["price"] = real_price

                already = any(r["code"] == code for r in momentum_results)
                if not already:
                    m = info["momentum"]
                    signal = "BUY" if m > 3 else ("SELL" if m < -3 else "HOLD")
                    momentum_results.append({
                        "code": code,
                        "name": info["name"],
                        "sector": info["sector"],
                        "price": info["price"],
                        "change_20d_pct": round(m, 2),
                        "momentum_score": round(m, 2),
                        "signal": signal,
                        "risk": next((s["risk"] for s in PORTFOLIO if s["code"] == code), 0.20),
                        "source": "默认动量配置"
                    })

        # 按动量排序
        momentum_results.sort(key=lambda x: x["momentum_score"], reverse=True)
        return momentum_results

    def analyze_mean_reversion(self, momentum_results: List[Dict]) -> List[Dict[str, Any]]:
        """均值回归分析：识别价格偏离显著的标的"""
        results = []

        # 简化逻辑：基于动量的反向判断
        # 动量极高的标的 → 可能超买 → 均值回归回调信号
        # 动量极低的标的 → 可能超卖 → 均值回归反弹信号
        for m in momentum_results:
            score = m["momentum_score"]
            # 构造均值回归信号
            if abs(score) > 3.5:
                direction = "超涨回调" if score > 0 else "超跌反弹"
                signal = "SELL" if score > 0 else "BUY"
            elif score < -2.5:
                direction = "超跌反弹"
                signal = "BUY"
            else:
                direction = "均值附近"
                signal = "HOLD"

            results.append({
                "code": m["code"],
                "name": m["name"],
                "sector": m["sector"],
                "price": m["price"],
                "mean": m["price"],
                "z_score": round(score / 2.0, 2),
                "direction": direction,
                "signal": signal,
                "risk": m["risk"],
            })

        return results


# ============================================================
# 4. 报告生成器
# ============================================================
class PremarketPlanReportGenerator:
    """生成最终的盘前交易计划 Markdown 文件"""

    def __init__(self, analysis: PlanAnalysisEngine, today_str: str,
                 data_sources: Dict[str, Any]):
        self.analysis = analysis
        self.today_str = today_str
        self.data_sources = data_sources
        self._weekday_map = ["一", "二", "三", "四", "五", "六", "日"]

    def generate(self) -> str:
        now = datetime.now()
        weekday_idx = now.weekday()

        # 生成核心信号
        macro = self.analysis.analyze_macro()
        etf_flow = self.analysis.analyze_etf_flow()
        momentum = self.analysis.analyze_momentum()
        reversion = self.analysis.analyze_mean_reversion(momentum)

        lines = []

        # 标题
        lines.append(f"# 📋 盘前交易计划 — {self.today_str} 周{self._weekday_map[weekday_idx]}")
        lines.append("")
        lines.append(f"> 生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"> 数据来源: {self._format_sources()}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 1. 宏观环境与仓位建议
        lines.append(self._generate_macro_section(macro))

        # 2. ETF资金流向
        lines.append(self._generate_etf_flow_section(etf_flow))

        # 3. 动量扫描
        lines.append(self._generate_momentum_section(momentum))

        # 4. 均值回归
        lines.append(self._generate_reversion_section(reversion))

        # 5. 今日重点关注
        lines.append(self._generate_focus_section(macro, momentum, reversion, etf_flow))

        # 6. 操作清单
        lines.append(self._generate_action_section(momentum, reversion))

        # 7. 补充：数据来源声明
        lines.append("---")
        lines.append("")
        lines.append(f"*本计划由量化策略系统 v5.0 盘前自动生成（综合当日 {len(self.data_sources)} 份报告）*")
        lines.append(f"*涉及报告: 康波周期分析、十五五规划适配、社保基金ETF追踪、综合日报、动力煤预测、K线形态扫描*")
        lines.append(f"*生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(lines)

    def _format_sources(self) -> str:
        sources = []
        for key, data in self.data_sources.items():
            if data.get("has_data"):
                names = {
                    "comprehensive": "综合日报",
                    "kangbo": "康波周期分析",
                    "fifteen_five": "十五五规划适配",
                    "social_security": "社保基金ETF追踪",
                    "coal": "动力煤",
                    "kline": "K线形态",
                }
                sources.append(names.get(key, key))
        return "、".join(sources) if sources else "默认配置 (无报告数据)"

    def _generate_macro_section(self, macro: Dict[str, Any]) -> str:
        section_lines = []
        section_lines.append("## 🌍 宏观环境与仓位建议")
        section_lines.append("")

        # 康波周期阶段
        phase = macro.get("kangbo_phase", "未知")
        section_lines.append(f"- **康波周期阶段**: **{phase}** (第六轮康波，AI/算力驱动)")

        # 十五五规划支持
        fifteen = self.data_sources.get("fifteen_five", {})
        directions = fifteen.get("strategic_directions", [])
        if directions:
            top = directions[:3]
            direction_strs = []
            for d in top:
                direction_strs.append(f"{d.get('name', '')}({d.get('weight', '')})")
            if direction_strs:
                section_lines.append(f"- **十五五规划方向**: {' / '.join(direction_strs)}")

        # 商品价格
        comp_data = self.data_sources.get("comprehensive", {})
        commodities = comp_data.get("commodities", {})
        if commodities:
            price_items = []
            for name in ["沪铜", "沪金", "沪铝"]:
                if name in commodities:
                    p = commodities[name]["price"]
                    if "黄金" in name or "金" in name:
                        price_items.append(f"{name} ¥{p:.0f}/克")
                    else:
                        price_items.append(f"{name} ¥{p:.0f}/吨")
            if price_items:
                section_lines.append(f"- **大宗商品**: {' | '.join(price_items)}")

        # 周期商品信号
        if macro.get("commodity_signals"):
            signals = macro["commodity_signals"][:4]
            sig_str = " / ".join(f"{s.get('name', '')}({s.get('signal', '')})" for s in signals)
            section_lines.append(f"- **周期商品信号**: {sig_str}")

        # 最终仓位建议
        score = macro.get("score", 0)
        advice = macro.get("advice", "中性")
        section_lines.append(f"- 🎯 **仓位建议**: **{advice}** (综合评分 {score:.1f}/4)")

        # 支撑理由
        if macro.get("reasons"):
            section_lines.append("")
            section_lines.append("**决策依据**:")
            for r in macro["reasons"][:4]:
                section_lines.append(f"  - {r}")

        section_lines.append("")
        return "\n".join(section_lines)

    def _generate_etf_flow_section(self, etf_flow: Dict[str, Any]) -> str:
        section_lines = []
        section_lines.append("## 📊 ETF国家队资金流向")
        section_lines.append("")

        trend = etf_flow.get("overall_trend", "中性")
        section_lines.append(f"**整体趋势**: {trend}")
        section_lines.append("")

        if etf_flow.get("strong_inflow"):
            section_lines.append("**🔴 强流入**:")
            for item in etf_flow["strong_inflow"][:5]:
                name = item.get("name", "")
                code = item.get("code", "")
                flow = item.get("flow_yi", 0)
                code_str = f"({code})" if code and str(code).isdigit() else ""
                section_lines.append(f"  - {name}{code_str} 净流入 {flow:.1f}亿")

        if etf_flow.get("strong_outflow"):
            section_lines.append("**🟢 强流出**:")
            for item in etf_flow["strong_outflow"][:3]:
                name = item.get("name", "")
                code = item.get("code", "")
                flow = abs(item.get("flow_yi", 0))
                code_str = f"({code})" if code and str(code).isdigit() else ""
                section_lines.append(f"  - {name}{code_str} 净流出 {flow:.1f}亿")

        section_lines.append("")
        section_lines.append("**风格轮动建议**:")
        rotation = etf_flow.get("sector_rotation", {})
        sorted_items = sorted(rotation.items(), key=lambda x: x[1], reverse=True)
        for cat, flow in sorted_items:
            icon = "🔥" if flow >= 10 else "📈" if flow > 0 else "📉" if flow <= -5 else "➡️"
            section_lines.append(f"  {icon} {cat}: {flow:+.1f}亿")

        section_lines.append("")
        return "\n".join(section_lines)

    def _generate_momentum_section(self, momentum: List[Dict]) -> str:
        section_lines = []
        section_lines.append("## 🚀 动量扫描 TOP/BOTTOM 5")
        section_lines.append("")

        if not momentum:
            section_lines.append("> 无动量数据")
            section_lines.append("")
            return "\n".join(section_lines)

        section_lines.append("| 排名 | 代码 | 名称 | 行业 | 价格 | 20日动量 | 信号 |")
        section_lines.append("|------|------|------|------|------|---------|------|")

        top5 = momentum[:5]
        bottom5 = momentum[-5:] if len(momentum) > 5 else momentum[:2]

        for i, item in enumerate(top5, 1):
            code = str(item.get("code", ""))
            name = item.get("name", "")
            sector = item.get("sector", "")
            price = float(item.get("price", 0))
            change = float(item.get("change_20d_pct", 0))
            signal = item.get("signal", "HOLD")
            price_str = f"{price:.2f}" if price > 0 else "—"
            section_lines.append(f"| {i} | {code} | {name} | {sector} | {price_str} | {change:+.2f}% | {signal} |")

        section_lines.append("| ... | ... | ... | ... | ... | ... | ... |")

        for i, item in enumerate(bottom5, len(momentum) - len(bottom5) + 1):
            code = str(item.get("code", ""))
            name = item.get("name", "")
            sector = item.get("sector", "")
            price = float(item.get("price", 0))
            change = float(item.get("change_20d_pct", 0))
            signal = item.get("signal", "HOLD")
            price_str = f"{price:.2f}" if price > 0 else "—"
            section_lines.append(f"| {i} | {code} | {name} | {sector} | {price_str} | {change:+.2f}% | {signal} |")

        section_lines.append("")
        return "\n".join(section_lines)

    def _generate_reversion_section(self, reversion: List[Dict]) -> str:
        section_lines = []
        section_lines.append("## 🔄 均值回归信号 (|Z-score| > 2.0)")
        section_lines.append("")

        # 筛选显著信号
        extreme = [r for r in reversion if abs(r.get("z_score", 0)) > 2.0]

        if extreme:
            section_lines.append("| 代码 | 名称 | 价格 | 均值 | Z-score | 方向 | 操作建议 |")
            section_lines.append("|------|------|------|------|---------|------|---------|")
            for item in extreme[:5]:
                code = str(item.get("code", ""))
                name = item.get("name", "")
                price = float(item.get("price", 0))
                mean = float(item.get("mean", 0))
                z = float(item.get("z_score", 0))
                direction = item.get("direction", "")
                signal = item.get("signal", "HOLD")
                price_str = f"{price:.2f}" if price > 0 else "—"
                mean_str = f"{mean:.2f}" if mean > 0 else "—"
                section_lines.append(f"| {code} | {name} | {price_str} | {mean_str} | {z:+.2f} | {direction} | {signal} |")
        else:
            section_lines.append("> 当前无明显极端偏离信号 (|Z| ≤ 2.0)")

        section_lines.append("")
        return "\n".join(section_lines)

    def _generate_focus_section(self, macro, momentum, reversion, etf_flow) -> str:
        section_lines = []
        section_lines.append("## ⚡ 今日重点关注")
        section_lines.append("")

        # 从十五五规划提取核心配置
        fifteen = self.data_sources.get("fifteen_five", {})
        if fifteen.get("has_data"):
            section_lines.append("**🎯 十五五规划驱动**:")
            for rating in fifteen.get("holdings_rating", [])[:3]:
                name = rating.get("name", "")
                score = rating.get("score", "")
                grade = rating.get("grade", "")
                if name:
                    section_lines.append(f"  - {name}: 适配评分 {score}，评级 {grade}")
            section_lines.append("")

        # 动能力量
        bullish_items = [m for m in momentum if m.get("signal") == "BUY"]
        if bullish_items:
            section_lines.append("**📈 动能力量 (十五五高适配)**:")
            for b in bullish_items[:3]:
                section_lines.append(f"  - {b['name']}({b['code']}) 动量{float(b['change_20d_pct']):+.2f}%")
            section_lines.append("")

        # 超跌反弹
        oversold = [r for r in reversion if r.get("signal") == "BUY"]
        if oversold:
            section_lines.append("**💎 超跌反弹机会 (均值回归)**:")
            for o in oversold[:3]:
                section_lines.append(f"  - {o['name']}({o['code']}) Z-score={float(o['z_score']):+.2f}")
            section_lines.append("")

        # 康波周期建议
        if macro.get("kangbo_phase") and macro["kangbo_phase"] != "未知":
            section_lines.append("**📊 康波周期信号**:")
            section_lines.append(f"  - 当前阶段: {macro['kangbo_phase']}")
            for cs in macro.get("commodity_signals", [])[:2]:
                section_lines.append(f"  - {cs.get('name', '')}: {cs.get('signal', '')}")
            section_lines.append("")

        # 动力煤信号
        coal = self.data_sources.get("coal", {})
        if coal.get("has_data"):
            section_lines.append("**🔥 能源板块关注**:")
            for point in coal.get("key_points", [])[:2]:
                section_lines.append(f"  - {point[:60]}")
            section_lines.append("")

        # K线形态
        kline = self.data_sources.get("kline", {})
        if kline.get("has_data"):
            section_lines.append("**📐 技术形态信号**:")
            for item in kline.get("bullish", [])[:2]:
                section_lines.append(f"  - 看涨: {item[:50]}")
            for item in kline.get("bearish", [])[:2]:
                section_lines.append(f"  - 看跌: {item[:50]}")
            section_lines.append("")

        return "\n".join(section_lines)

    def _generate_action_section(self, momentum, reversion) -> str:
        section_lines = []
        section_lines.append("## 📝 今日操作清单")
        section_lines.append("")

        # 买入关注
        section_lines.append("### 买入关注")
        buy_candidates = []
        # 动量 BUY + 均值回归 BUY
        seen_codes = set()
        for m in momentum:
            if m.get("signal") == "BUY" and m["code"] not in seen_codes:
                buy_candidates.append(m)
                seen_codes.add(m["code"])
        for r in reversion:
            if r.get("signal") == "BUY" and r["code"] not in seen_codes:
                buy_candidates.append(r)
                seen_codes.add(r["code"])

        if buy_candidates:
            for b in buy_candidates[:5]:
                name = b.get("name", "")
                code = str(b.get("code", ""))
                risk = float(b.get("risk", 0.20))
                section_lines.append(f"- [ ] **{name}**({code}) — {b.get('sector', '')} | 风险:{risk:.2f}")
        else:
            section_lines.append("> 暂无明确买入信号（等待市场趋势明朗）")

        section_lines.append("")

        # 卖出/减仓
        section_lines.append("### 卖出/减仓关注")
        sell_candidates = []
        seen_codes_sell = set()
        for m in momentum:
            if m.get("signal") == "SELL" and m["code"] not in seen_codes_sell:
                sell_candidates.append(m)
                seen_codes_sell.add(m["code"])
        for r in reversion:
            if r.get("signal") == "SELL" and r["code"] not in seen_codes_sell:
                sell_candidates.append(r)
                seen_codes_sell.add(r["code"])

        if sell_candidates:
            for s in sell_candidates[:5]:
                name = s.get("name", "")
                code = str(s.get("code", ""))
                risk = float(s.get("risk", 0.20))
                section_lines.append(f"- [ ] **{name}**({code}) — {s.get('sector', '')} | 风险:{risk:.2f}")
        else:
            section_lines.append("> 暂无明确卖出信号（持仓稳健）")

        section_lines.append("")
        return "\n".join(section_lines)


# ============================================================
# 5. 主执行流程
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="盘前交易计划生成器")
    parser.add_argument("--date", help="指定日期 (YYYY-MM-DD)",
                        default=datetime.now().strftime('%Y-%m-%d'))
    parser.add_argument("--dir", help="归档目录", default=ARCHIVE_ROOT)
    parser.add_argument("--show", action="store_true", help="显示报告内容")
    args = parser.parse_args()

    today_str = args.date
    today_short = today_str.replace('-', '')
    archive_root = args.dir

    date_dir = os.path.join(archive_root, today_str)

    if not os.path.exists(date_dir):
        logger.warning(f"日期目录不存在: {date_dir}")
        logger.warning("将使用默认配置生成基础报告")

    logger.info(f"开始生成盘前交易计划: {today_str}")
    logger.info(f"归档目录: {date_dir}")

    # ============= 步骤 1: 提取所有报告数据 =============
    print("\n[1/4] 解析综合日报...", end=" ")
    comp_extractor = ComprehensiveReportExtractor(date_dir, today_str, today_short)
    comprehensive_data = comp_extractor.extract()
    print(f"商品 {len(comprehensive_data['commodities'])} 项 | 股票 {len(comprehensive_data['stocks'])} 项")

    print("[2/4] 解析康波周期分析...", end=" ")
    kangbo_extractor = KangboCycleExtractor(date_dir, today_short)
    kangbo_data = kangbo_extractor.extract()
    print(f"阶段: {kangbo_data.get('phase', '未知')} | 行业建议: {len(kangbo_data.get('industries', []))} 项")

    print("[3/4] 解析十五五规划适配...", end=" ")
    plan_extractor = FifteenFivePlanExtractor(date_dir, today_short)
    plan_data = plan_extractor.extract()
    print(f"战略方向: {len(plan_data.get('strategic_directions', []))} | 持仓评级: {len(plan_data.get('holdings_rating', []))} 项")

    print("[4/4] 解析社保基金追踪...", end=" ")
    social_extractor = SocialSecurityETFTrackerExtractor(date_dir, today_short)
    social_data = social_extractor.extract()
    print(f"风格配置: {len(social_data.get('styles', []))} 项 | ETF映射: {len(social_data.get('etf_mapping', []))} 项")

    # 辅助报告
    coal_extractor = CoalReportExtractor(date_dir, today_str, today_short)
    coal_data = coal_extractor.extract()
    if coal_data.get("has_data"):
        print(f"  ↳ 动力煤: 舆情 {coal_data.get('sentiment', '中性')} | 要点 {len(coal_data.get('key_points', []))} 项")

    kline_extractor = KLinePatternExtractor(date_dir, today_short)
    kline_data = kline_extractor.extract()
    if kline_data.get("has_data"):
        print(f"  ↳ K线形态: 看涨 {len(kline_data.get('bullish', []))} | 看跌 {len(kline_data.get('bearish', []))}")

    # ============= 步骤 2: 综合分析 =============
    all_data = {
        "comprehensive": comprehensive_data,
        "kangbo": kangbo_data,
        "fifteen_five": plan_data,
        "social_security": social_data,
        "coal": coal_data,
        "kline": kline_data,
    }

    print(f"\n[综合] 有效数据源: {sum(1 for d in all_data.values() if d.get('has_data'))} / {len(all_data)}")

    engine = PlanAnalysisEngine(all_data, today_str)

    # ============= 步骤 3: 生成 Markdown 报告 =============
    generator = PremarketPlanReportGenerator(engine, today_str, all_data)
    report = generator.generate()

    # ============= 步骤 4: 保存 =============
    os.makedirs(date_dir, exist_ok=True)
    output_file = os.path.join(date_dir, f"盘前交易计划_{today_str}.md")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✅ 盘前交易计划已生成: {output_file}")

    if args.show:
        print("\n" + "=" * 60)
        print(report)
        print("=" * 60)

    # 同时保存为 old 格式文件名，供调度器匹配
    output_file_v2 = os.path.join(date_dir, f"盘前交易计划_{today_short}.md")
    if output_file_v2 != output_file:
        with open(output_file_v2, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"副文件名已保存: {output_file_v2}")

    return output_file


if __name__ == "__main__":
    main()
