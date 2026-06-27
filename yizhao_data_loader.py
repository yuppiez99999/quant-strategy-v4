# -*- coding: utf-8 -*-
"""
YiZhao-FinDataSet 数据加载与预处理模块 v2.0
功能: 基于D盘原始数据 + E盘过滤索引的高效检索

数据存储:
  D:\YiZhao-FinDataSet\data\full\._____temp\cn\  — 原始 34GB 中文分片
  E:\各种PY程序\11_量化策略\data\yizhao_filtered\  — 过滤后 5.1GB (fin_int_score>=3)

关键统计:
  原始: 10,645,590 条 | 过滤后: 1,217,716 条 (fin_int_score>=3)
  覆盖: 全部 18 只 v5.1 组合标的, 每分片 3,388~5,363 命中

来源: https://modelscope.cn/datasets/CMB_AILab/YiZhao-FinDataSet
"""
import sys
if sys.version_info < (3, 9):
    try:
        from backports import zoneinfo
        sys.modules['zoneinfo'] = zoneinfo
    except ImportError:
        pass

import os
import json
import hashlib
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import warnings

warnings.filterwarnings('ignore')

# ============================================================
# 路径常量
# ============================================================
_FILTERED_DATA_DIR = r"E:\各种PY程序\11_量化策略\data\yizhao_filtered"

# ============================================================
# 配置
# ============================================================
@dataclass
class YiZhaoConfig:
    """数据集配置"""
    # 本地存储路径 — v2.0 默认指向 E 盘过滤数据
    data_dir: str = _FILTERED_DATA_DIR

    # 检索配置
    max_results: int = 150
    min_fin_score: int = 3
    default_days_back: int = 60

    # v5.1 组合: 14标的4板块 (与 portfolio.yaml 同步)
    portfolio_keywords: Dict[str, List[str]] = field(default_factory=lambda: {
        # 高端制造(含算力) — 45%
        "300308": ["中际旭创", "光模块", "800G", "1.6T", "算力光模块"],
        "688041": ["海光信息", "海光", "国产CPU", "DCU", "算力芯片"],
        "002371": ["北方华创", "半导体设备", "刻蚀", "薄膜沉积", "芯片制造"],
        "688981": ["中芯国际", "SMIC", "晶圆代工", "成熟制程", "半导体制造"],
        "300750": ["宁德时代", "宁德", "CATL", "锂电池", "动力电池", "储能电池"],
        "000425": ["徐工机械", "工程机械", "挖掘机", "基建", "装备制造"],
        # 顺周期 — 20%
        "601088": ["中国神华", "神华", "煤炭", "能源安全", "煤电一体化"],
        "600219": ["南山铝业", "铝业", "电解铝", "铝加工", "汽车板"],
        "600019": ["宝钢股份", "宝钢", "钢铁", "板材", "汽车钢"],
        # 资源 — 20%
        "518880": ["华安黄金ETF", "黄金ETF", "黄金", "贵金属", "金价"],
        "000408": ["藏格矿业", "藏格", "钾肥", "锂矿", "盐湖提锂"],
        # 防御 — 15%
        "600276": ["恒瑞医药", "恒瑞", "创新药", "PD-1", "医药研发"],
        "603259": ["药明康德", "药明", "CXO", "医药外包", "药物发现"],
        "002422": ["科伦药业", "科伦", "大输液", "仿制药", "抗生素"],
    })

    # 金融领域关键词 (用于预筛选)
    fin_domains: List[str] = field(default_factory=lambda: [
        "股票", "A股", "大盘", "指数", "行业", "板块", "涨跌", "行情",
        "政策", "监管", "央行", "利率", "降息", "加息", "货币",
        "业绩", "财报", "营收", "利润", "分红", "ROE", "PE", "估值",
        "风险", "回撤", "波动", "杠杆", "做空", "爆仓", "熔断",
        "并购", "重组", "IPO", "上市", "退市", "定增",
        "新能源", "半导体", "医药", "消费", "科技", "制造", "金融"
    ])


# ============================================================
# 数据模型
# ============================================================
@dataclass
class YiZhaoDocument:
    """单条金融文档"""
    doc_id: str
    url: str
    title: str
    source_domain: str
    text: str
    fin_int_score: int
    risk_score: float
    language: str
    dump: str = ""

    @property
    def text_length(self) -> int:
        return len(self.text)

    @classmethod
    def from_item(cls, item: Dict) -> Optional["YiZhaoDocument"]:
        """从 JSONL 行解析文档"""
        try:
            meta = item.get('meta', item)
            return cls(
                doc_id=meta.get('id', hashlib.md5(
                    item.get('text', '').encode('utf-8')
                ).hexdigest()[:16]),
                url=meta.get('url', ''),
                title=meta.get('title', ''),
                source_domain=meta.get('source_domain', ''),
                text=item.get('text', ''),
                fin_int_score=int(meta.get('fin_int_score', 0)),
                risk_score=float(meta.get('risk_score', 0.0)),
                language=meta.get('language', 'zh'),
                dump=meta.get('dump', '')
            )
        except Exception:
            return None


@dataclass
class SearchResult:
    """检索结果"""
    doc: YiZhaoDocument
    score: float
    matched_keywords: List[str] = field(default_factory=list)


# ============================================================
# v2.0 流式加载器 — 不将全部文档加载到内存
# ============================================================
class YiZhaoDataLoader:
    """
    YiZhao v2.0 流式加载器

    设计原则:
      - 数据已在 E 盘预先过滤 (fin_int_score >= 3)
      - 索引通过扫描所有分片 JSONL 文件实时构建
      - 检索时流式匹配，不将 120 万条文档同时加载到内存
    """

    def __init__(self, config: YiZhaoConfig = None):
        self.config = config or YiZhaoConfig()
        self._shard_files: List[str] = []
        self._documents: Dict[str, YiZhaoDocument] = {}  # 仅缓存热门文档
        self._keyword_index: Dict[str, List[str]] = defaultdict(list)
        self._loaded = False
        self._stats = {}
        self._total_records = 0
        self._indexed_keywords = 0

        self._discover_shards()
        if self._shard_files:
            self._build_streaming_index()

    # ---- 分片发现 ----
    def _discover_shards(self):
        """扫描 data_dir 下的所有 JSONL 分片"""
        d = self.config.data_dir
        if not os.path.isdir(d):
            print(f"[YiZhao] 数据目录不存在: {d}")
            return
        self._shard_files = sorted([
            os.path.join(d, f) for f in os.listdir(d)
            if f.endswith('.jsonl') and not f.startswith('ticker_')
        ])
        if self._shard_files:
            total_mb = sum(os.path.getsize(f) for f in self._shard_files) / 1024**2
            print(f"[YiZhao] 发现 {len(self._shard_files)} 个分片 ({total_mb:.0f}MB)")

    # ---- 流式索引构建 ----
    def _build_streaming_index(self):
        """
        流式扫描所有分片，构建关键词→doc_id 的倒排索引
        每个分片只过一遍，不将全文加载到内存
        """
        print("[YiZhao] 构建流式倒排索引...")
        start = time.time()
        self._keyword_index.clear()
        all_keywords = set()
        for kws in self.config.portfolio_keywords.values():
            all_keywords.update(kws)
        all_keywords.update(self.config.fin_domains)

        total = 0
        for shard_path in self._shard_files:
            with open(shard_path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    try:
                        item = json.loads(line.strip())
                        meta = item.get('meta', {})
                        title = meta.get('title', '')
                        text = item.get('text', '')
                        combined = title + ' ' + text[:800]
                        doc_id = hashlib.md5(
                            (title + text[:200]).encode('utf-8')
                        ).hexdigest()[:16]
                        total += 1
                        for kw in all_keywords:
                            if kw in combined:
                                self._keyword_index[kw].append(doc_id)
                    except Exception:
                        continue

        elapsed = time.time() - start
        self._total_records = total
        self._indexed_keywords = len(self._keyword_index)
        print(f"[YiZhao] 索引完成 ({elapsed:.1f}s): {total:,} 条记录, "
              f"{self._indexed_keywords} 个关键词命中")

        self._stats = {
            'total_records': total,
            'shards': len(self._shard_files),
            'keywords_indexed': self._indexed_keywords,
            'ticker_keywords': len(all_keywords),
        }
        self._loaded = True

    # ---- 检索 ----
    def search_by_code(self, code: str, top_k: int = 10) -> List[SearchResult]:
        """按标的代码流式检索: 在所有分片中实时匹配文档"""
        keywords = self.config.portfolio_keywords.get(code, [])
        if not keywords:
            return []

        results = []
        seen_titles = set()

        for shard_path in self._shard_files:
            if len(results) >= top_k:
                break
            with open(shard_path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    if len(results) >= top_k * 3:  # 多取一些用于排序
                        break
                    try:
                        item = json.loads(line.strip())
                        meta = item.get('meta', {})
                        title = meta.get('title', '')
                        text = item.get('text', '')
                        combined = title + ' ' + text[:2000]
                        matched = []
                        for kw in keywords:
                            if kw in combined:
                                matched.append(kw)
                        if matched:
                            if title in seen_titles:
                                continue
                            seen_titles.add(title)
                            doc = YiZhaoDocument.from_item(item)
                            if doc:
                                score = self._compute_relevance(doc, keywords)
                                results.append(SearchResult(
                                    doc=doc,
                                    score=score,
                                    matched_keywords=matched
                                ))
                    except Exception:
                        continue

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def search_by_keywords(self, keywords: List[str], top_k: int = 20,
                           min_fin_score: int = 0) -> List[SearchResult]:
        """流式关键词检索"""
        results = []
        seen_titles = set()

        for shard_path in self._shard_files:
            if len(results) >= top_k * 3:
                break
            with open(shard_path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    if len(results) >= top_k * 3:
                        break
                    try:
                        item = json.loads(line.strip())
                        meta = item.get('meta', {})
                        fin_score = int(meta.get('fin_int_score', 0))
                        if min_fin_score > 0 and fin_score < min_fin_score:
                            continue
                        title = meta.get('title', '')
                        text = item.get('text', '')
                        combined = title + ' ' + text[:2000]
                        matched = [kw for kw in keywords if kw in combined]
                        if matched:
                            if title in seen_titles:
                                continue
                            seen_titles.add(title)
                            doc = YiZhaoDocument.from_item(item)
                            if doc:
                                results.append(SearchResult(
                                    doc=doc,
                                    score=self._compute_relevance(doc, keywords),
                                    matched_keywords=matched
                                ))
                    except Exception:
                        continue

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def search_by_domain(self, domain: str, top_k: int = 20) -> List[SearchResult]:
        """按来源域名流式检索"""
        results = []
        for shard_path in self._shard_files:
            if len(results) >= top_k:
                break
            with open(shard_path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    if len(results) >= top_k:
                        break
                    try:
                        item = json.loads(line.strip())
                        if item.get('meta', {}).get('source_domain', '') == domain:
                            doc = YiZhaoDocument.from_item(item)
                            if doc:
                                results.append(SearchResult(doc=doc, score=1.0))
                    except Exception:
                        continue
        return results[:top_k]

    def _compute_relevance(self, doc: YiZhaoDocument, keywords: List[str]) -> float:
        """计算文档相关性得分"""
        score = 0.0
        text_lower = doc.text[:3000].lower()
        title_lower = doc.title.lower()
        for kw in keywords:
            kw_lower = kw.lower()
            score += title_lower.count(kw_lower) * 3.0
            score += text_lower.count(kw_lower) * 1.0
        return score * (doc.fin_int_score / 5.0)

    # ---- 情绪分析 ----
    def get_market_sentiment(self, code: str = None,
                             keywords: List[str] = None) -> Dict:
        """计算市场情绪指标 (流式)"""
        if code:
            search_kws = self.config.portfolio_keywords.get(code, [])
            results = self.search_by_keywords(search_kws, top_k=50)
        elif keywords:
            results = self.search_by_keywords(keywords, top_k=50)
        else:
            return {'error': '请指定 code 或 keywords'}

        if not results:
            return {'sentiment_score': 0.5, 'positive_ratio': 0.0,
                    'negative_ratio': 0.0, 'article_count': 0}

        positive_words = ['上涨', '增长', '利好', '突破', '盈利', '分红', '创新',
                          '政策支持', '补贴', '扩产', '中标', '获批', '升级', '领涨']
        negative_words = ['下跌', '下滑', '亏损', '风险', '暴雷', '退市', '处罚',
                          '监管', '减持', '爆仓', '违约', '诉讼', '停工', '跌停']

        pos_count = neg_count = 0
        for r in results:
            text_short = r.doc.text[:2000]
            p = sum(1 for w in positive_words if w in text_short)
            n = sum(1 for w in negative_words if w in text_short)
            if p > n:
                pos_count += 1
            elif n > p:
                neg_count += 1

        total = len(results)
        sentiment = (pos_count + 1) / (pos_count + neg_count + 2) if total > 0 else 0.5
        return {
            'sentiment_score': round(sentiment, 4),
            'positive_ratio': round(pos_count / total, 4) if total > 0 else 0,
            'negative_ratio': round(neg_count / total, 4) if total > 0 else 0,
            'article_count': total
        }

    def get_event_summary(self, code: str, top_k: int = 10) -> List[Dict]:
        """获取标的关键事件摘要"""
        results = self.search_by_code(code, top_k=top_k)
        return [{
            'title': r.doc.title,
            'source': r.doc.source_domain,
            'relevance': round(r.score, 2),
            'fin_score': r.doc.fin_int_score,
            'snippet': (r.doc.text[:200] + '...') if len(r.doc.text) > 200 else r.doc.text,
            'keywords': r.matched_keywords
        } for r in results]

    # ---- 工具 ----
    @property
    def is_loaded(self) -> bool:
        return self._loaded and self._total_records > 0

    @property
    def stats(self) -> Dict:
        return self._stats.copy()

    def get_doc_count(self) -> int:
        return self._total_records

    def print_stats(self):
        """打印统计信息"""
        if not self._loaded:
            print("[YiZhao] 数据未加载")
            return
        print(f"\n{'='*50}")
        print(f"  YiZhao v2.0 数据集统计")
        print(f"{'='*50}")
        print(f"  总记录数 (fin>=3): {self._total_records:,}")
        print(f"  分片数: {len(self._shard_files)}")
        print(f"  已索引关键词: {self._indexed_keywords}")
        print(f"  数据目录: {self.config.data_dir}")
        print(f"  覆盖标的: {len(self.config.portfolio_keywords)} 只")
        ticker_list = list(self.config.portfolio_keywords.keys())
        print(f"  标的代码: {', '.join(ticker_list[:7])}... ({len(ticker_list)} 只)")


# ============================================================
# 便捷函数
# ============================================================
_global_loader: Optional[YiZhaoDataLoader] = None


def get_yizhao_loader(data_dir: str = None, force_reload: bool = False) -> YiZhaoDataLoader:
    """获取全局 YiZhao 数据加载器 (单例)"""
    global _global_loader
    if _global_loader is None or force_reload:
        config = YiZhaoConfig()
        if data_dir:
            config.data_dir = data_dir
        _global_loader = YiZhaoDataLoader(config)
    return _global_loader


# ============================================================
# 命令行入口
# ============================================================
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='YiZhao v2.0 金融数据集加载器')
    parser.add_argument('--stats', action='store_true', help='显示统计')
    parser.add_argument('--search', type=str, help='按代码检索')
    parser.add_argument('--sentiment', type=str, help='分析情绪')
    parser.add_argument('--events', type=str, help='查看事件')
    parser.add_argument('--top-k', type=int, default=10, help='返回条数')

    args = parser.parse_args()
    loader = get_yizhao_loader()

    if args.stats or not any([args.search, args.sentiment, args.events]):
        loader.print_stats()
    elif args.search:
        results = loader.search_by_code(args.search, top_k=args.top_k)
        for i, r in enumerate(results, 1):
            print(f"\n{i}. [{r.score:.1f}] {r.doc.title}")
            print(f"   来源: {r.doc.source_domain} | 金融分: {r.doc.fin_int_score}")
            print(f"   关键词: {', '.join(r.matched_keywords)}")
            print(f"   摘要: {r.doc.text[:150]}...")
    elif args.sentiment:
        s = loader.get_market_sentiment(code=args.sentiment)
        print(f"\n{args.sentiment} 情绪分析:")
        print(f"  情绪得分: {s['sentiment_score']:.3f} (0=悲观, 1=乐观)")
        print(f"  正面比例: {s['positive_ratio']:.1%}")
        print(f"  负面比例: {s['negative_ratio']:.1%}")
        print(f"  文章数量: {s['article_count']}")
    elif args.events:
        events = loader.get_event_summary(args.events, top_k=args.top_k)
        for i, e in enumerate(events, 1):
            print(f"\n{i}. {e['title']}")
            print(f"   来源: {e['source']} | 相关性: {e['relevance']}")
            print(f"   {e['snippet']}")
