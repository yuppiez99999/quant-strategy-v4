# -*- coding: utf-8 -*-
"""
YiZhao-FinDataSet 数据加载与预处理模块
功能: 从 ModelScope 下载金融语料子集, 建立本地索引, 提供高效检索接口

YiZhao 数据集:
  936GB 中文金融文本 + 100GB 英文金融文本 + 1TB 多模态数据
  覆盖: 金融事件/市场动态/金融产品/交易模式/信用评分/风险管理/欺诈检测/投资组合优化

来源: https://modelscope.cn/datasets/CMB_AILab/YiZhao-FinDataSet
"""
import sys
# Python 3.8 兼容性: 提前注入 zoneinfo
if sys.version_info < (3, 9):
    try:
        from backports import zoneinfo
        sys.modules['zoneinfo'] = zoneinfo
    except ImportError:
        pass

import os
import json
import gzip
import pickle
import hashlib
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Iterator
from dataclasses import dataclass, field
from collections import defaultdict
import warnings

warnings.filterwarnings('ignore')


# ============================================================
# 配置
# ============================================================
@dataclass
class YiZhaoConfig:
    """数据集配置"""
    # 本地存储路径
    data_dir: str = "data/yizhao"
    cache_dir: str = "data/yizhao/cache"
    index_dir: str = "data/yizhao/index"

    # 下载配置
    max_download_gb: float = 10.0  # 最多下载10GB (精选子集)
    min_fin_score: int = 3          # 最低金融相关性得分 (1-5)

    # 检索配置
    max_results: int = 100
    default_days_back: int = 30

    # 12只标的相关关键词
    portfolio_keywords: Dict[str, List[str]] = field(default_factory=lambda: {
        "601088": ["中国神华", "神华", "煤炭", "能源安全", "煤电"],
        "600995": ["南网储能", "储能", "抽水蓄能", "南方电网", "新型电力系统"],
        "600989": ["宝丰能源", "煤化工", "氢能", "甲醇", "宁东"],
        "600875": ["东方电气", "风电", "核电", "汽轮机", "发电设备"],
        "600406": ["国电南瑞", "电网", "电力自动化", "特高压", "智能电网"],
        "300274": ["阳光电源", "逆变器", "光伏", "储能系统", "新能源"],
        "000425": ["徐工机械", "工程机械", "挖掘机", "基建", "一带一路"],
        "002371": ["北方华创", "半导体设备", "刻蚀", "薄膜沉积", "芯片"],
        "600276": ["恒瑞医药", "创新药", "PD-1", "仿制药", "医药研发"],
        "600089": ["特变电工", "变压器", "特高压", "输变电", "新能源"],
        "688017": ["绿的谐波", "谐波减速器", "机器人", "精密传动", "工业母机"],
        "518880": ["黄金ETF", "黄金", "避险", "贵金属", "金价"]
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
    fin_int_score: int       # 金融相关性 1-5
    risk_score: float        # 安全风险得分
    language: str            # zh / en
    qa_pairs: List[Dict] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    dump: str = ""

    @property
    def text_length(self) -> int:
        return len(self.text)

    @property
    def has_qa(self) -> bool:
        return len(self.qa_pairs) > 0


@dataclass
class SearchResult:
    """检索结果"""
    doc: YiZhaoDocument
    score: float
    matched_keywords: List[str] = field(default_factory=list)


# ============================================================
# 数据加载器
# ============================================================
class YiZhaoDataLoader:
    """YiZhao 金融数据集加载器"""

    def __init__(self, config: YiZhaoConfig = None):
        self.config = config or YiZhaoConfig()
        self._documents: Dict[str, YiZhaoDocument] = {}
        self._keyword_index: Dict[str, List[str]] = defaultdict(list)
        self._domain_index: Dict[str, List[str]] = defaultdict(list)
        self._date_index: Dict[str, List[str]] = defaultdict(list)
        self._score_index: Dict[int, List[str]] = defaultdict(list)
        self._loaded = False
        self._stats = {}

        os.makedirs(self.config.data_dir, exist_ok=True)
        os.makedirs(self.config.cache_dir, exist_ok=True)
        os.makedirs(self.config.index_dir, exist_ok=True)

    # ---- 下载 ----
    def download_subset(self, max_size_gb: float = None) -> bool:
        """
        从 ModelScope 下载精选子集
        优先下载中文高金融相关性文本

        策略:
          1. 优先使用 modelscope SDK (Python 3.10-3.12)
          2. 回退到直接下载 jsonl 文件 (适用于 Python 3.14+)
        """
        max_size = max_size_gb or self.config.max_download_gb
        print(f"[YiZhao] 开始下载数据子集 (上限 {max_size}GB)...")

        # 方案1: 直接下载 jsonl 文件 (最可靠)
        if self._download_jsonl_direct(max_size):
            return True

        # 方案2: modelscope SDK
        try:
            from modelscope.msdatasets import MsDataset
            # 尝试多个子集名称
            ds = None
            for subset in ['zh', 'en', 'default', None]:
                try:
                    ds = MsDataset.load(
                        'CMB_AILab/YiZhao-FinDataSet',
                        subset_name=subset,
                        split='train',
                        cache_dir=self.config.cache_dir
                    )
                    print(f"[YiZhao] 使用子集: {subset}")
                    break
                except Exception:
                    continue
            if ds is None:
                raise ValueError("无法加载任何子集")
            print(f"[YiZhao] 数据集加载成功, 共 {len(ds)} 条记录")

            downloaded = 0
            total_bytes = 0
            max_bytes = int(max_size * 1024**3)

            for item in ds:
                try:
                    meta = item.get('meta', item)
                    fin_score = meta.get('fin_int_score', 0)
                    if isinstance(fin_score, (int, float)) and fin_score < self.config.min_fin_score:
                        continue
                    # 接受中文和英文数据
                    language = meta.get('language', '')
                    if language not in ('zh', 'en'):
                        continue
                    doc = self._parse_document(item)
                    if doc is None:
                        continue
                    self._documents[doc.doc_id] = doc
                    total_bytes += len(doc.text.encode('utf-8'))
                    downloaded += 1
                    if total_bytes >= max_bytes:
                        break
                except Exception:
                    continue

            print(f"[YiZhao] 下载完成: {downloaded} 篇文档, {total_bytes / 1024**3:.2f}GB")
            self._save_to_disk()
            self._build_index()
            self._loaded = True
            return True

        except Exception as e:
            print(f"[YiZhao] SDK加载失败: {e}")

        print("[YiZhao] 尝试从本地缓存加载...")
        return self.load_from_cache()

    def _download_jsonl_direct(self, max_size_gb: float) -> bool:
        """
        直接从 ModelScope API 下载 jsonl 文件
        绕过 MsDataset, 适用于 Python 3.14
        """
        import urllib.request
        import ssl

        # ModelScope 数据集文件列表 API
        api_url = ("https://www.modelscope.cn/api/v1/datasets/"
                   "CMB_AILab/YiZhao-FinDataSet/repo/files?Source=SDK")

        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(api_url, headers={
                'User-Agent': 'Mozilla/5.0'
            })

            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                data = json.loads(resp.read().decode())

            files = data.get('Data', {}).get('Files', [])
            print(f"[YiZhao] 发现 {len(files)} 个文件")

            # 优先下载中文样本文件
            zh_files = [f for f in files if 'zh' in f.get('Name', '').lower()
                       and f['Name'].endswith('.jsonl')]
            en_files = [f for f in files if 'en' in f.get('Name', '').lower()
                       and f['Name'].endswith('.jsonl')]

            target_files = (zh_files or en_files or
                           [f for f in files if f['Name'].endswith('.jsonl')])

            total_bytes = 0
            max_bytes = int(max_size_gb * 1024**3)
            downloaded = 0

            for file_info in target_files[:5]:  # 最多5个文件
                if total_bytes >= max_bytes:
                    break

                fname = file_info['Name']
                furl = file_info.get('Url') or file_info.get('DownloadUrl')
                if not furl:
                    continue

                print(f"[YiZhao] 下载: {fname} ({file_info.get('Size', 0)/1024**2:.1f}MB)...")

                try:
                    req2 = urllib.request.Request(furl, headers={
                        'User-Agent': 'Mozilla/5.0'
                    })
                    with urllib.request.urlopen(req2, context=ctx, timeout=120) as fresp:
                        content = fresp.read()

                    # 解析 jsonl
                    for line in content.decode('utf-8').strip().split('\n'):
                        if total_bytes >= max_bytes:
                            break
                        try:
                            item = json.loads(line)
                            doc = self._parse_document(item)
                            if doc and doc.fin_int_score >= self.config.min_fin_score:
                                self._documents[doc.doc_id] = doc
                                total_bytes += len(doc.text.encode('utf-8'))
                                downloaded += 1
                        except Exception:
                            continue

                    print(f"  -> 已处理 {downloaded} 篇 ({total_bytes/1024**2:.1f}MB)")

                except Exception as e:
                    print(f"  -> 下载失败: {e}")
                    continue

            if downloaded > 0:
                print(f"[YiZhao] 直接下载完成: {downloaded} 篇, {total_bytes/1024**3:.2f}GB")
                self._save_to_disk()
                self._build_index()
                self._loaded = True
                return True

        except Exception as e:
            print(f"[YiZhao] 直接下载失败: {e}")

        return False

    # ---- 本地存储 ----
    def _save_to_disk(self):
        """保存到本地 Parquet/JSONL 文件"""
        output_file = os.path.join(self.config.data_dir, 'yizhao_subset.jsonl')
        with open(output_file, 'w', encoding='utf-8') as f:
            for doc in self._documents.values():
                record = {
                    'id': doc.doc_id,
                    'url': doc.url,
                    'title': doc.title,
                    'source_domain': doc.source_domain,
                    'text': doc.text,
                    'fin_int_score': doc.fin_int_score,
                    'risk_score': doc.risk_score,
                    'language': doc.language,
                    'qa_pairs': doc.qa_pairs,
                    'images': doc.images,
                    'dump': doc.dump
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

        # 保存统计信息
        stats_file = os.path.join(self.config.data_dir, 'stats.json')
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self._stats, f, ensure_ascii=False, indent=2)

        print(f"[YiZhao] 已保存 {len(self._documents)} 条记录到 {output_file}")

    def load_from_cache(self) -> bool:
        """从本地缓存加载"""
        input_file = os.path.join(self.config.data_dir, 'yizhao_subset.jsonl')
        if not os.path.exists(input_file):
            print(f"[YiZhao] 缓存文件不存在: {input_file}")
            return False

        print(f"[YiZhao] 从本地缓存加载: {input_file}")
        count = 0
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    doc = self._parse_document(item)
                    if doc:
                        self._documents[doc.doc_id] = doc
                        count += 1
                except Exception:
                    continue

        print(f"[YiZhao] 加载完成: {count} 篇文档")
        self._build_index()
        self._loaded = True
        return count > 0

    # ---- 索引构建 ----
    def _build_index(self):
        """构建多维度索引"""
        print("[YiZhao] 构建索引...")
        start = time.time()

        self._keyword_index.clear()
        self._domain_index.clear()
        self._score_index.clear()

        for doc_id, doc in self._documents.items():
            # 按域名索引
            self._domain_index[doc.source_domain].append(doc_id)

            # 按金融得分索引
            self._score_index[doc.fin_int_score].append(doc_id)

            # 按关键词索引
            all_keywords = set()
            for keywords in self.config.portfolio_keywords.values():
                all_keywords.update(keywords)

            for kw in all_keywords:
                if kw in doc.title or kw in doc.text[:2000]:
                    self._keyword_index[kw].append(doc_id)

        # 统计
        self._stats = {
            'total_docs': len(self._documents),
            'domains': len(self._domain_index),
            'keywords_indexed': len(self._keyword_index),
            'score_distribution': {str(k): len(v) for k, v in self._score_index.items()},
            'avg_text_length': sum(d.text_length for d in self._documents.values()) / max(len(self._documents), 1),
            'top_domains': sorted(
                [(d, len(ids)) for d, ids in self._domain_index.items()],
                key=lambda x: x[1], reverse=True
            )[:10]
        }

        elapsed = time.time() - start
        print(f"[YiZhao] 索引构建完成 ({elapsed:.1f}s), 统计: {self._stats}")

    # ---- 文档解析 ----
    def _parse_document(self, item: Dict) -> Optional[YiZhaoDocument]:
        """解析单条记录为 YiZhaoDocument"""
        try:
            meta = item.get('meta', item)
            return YiZhaoDocument(
                doc_id=meta.get('id', hashlib.md5(
                    item.get('text', '').encode()
                ).hexdigest()[:16]),
                url=meta.get('url', ''),
                title=meta.get('title', ''),
                source_domain=meta.get('source_domain', ''),
                text=item.get('text', ''),
                fin_int_score=int(meta.get('fin_int_score', 0)),
                risk_score=float(meta.get('risk_score', 0.0)),
                language=meta.get('language', 'zh'),
                qa_pairs=item.get('qa', []),
                images=meta.get('images', []),
                dump=meta.get('dump', '')
            )
        except Exception as e:
            return None

    # ---- 检索接口 ----
    def search_by_code(self, code: str, top_k: int = 10) -> List[SearchResult]:
        """按标的代码检索相关金融文本"""
        keywords = self.config.portfolio_keywords.get(code, [])
        if not keywords:
            return []

        results = []
        seen_ids = set()

        for kw in keywords:
            doc_ids = self._keyword_index.get(kw, [])
            for doc_id in doc_ids[:20]:
                if doc_id in seen_ids:
                    continue
                seen_ids.add(doc_id)
                doc = self._documents.get(doc_id)
                if doc:
                    score = self._compute_relevance(doc, keywords)
                    results.append(SearchResult(
                        doc=doc,
                        score=score,
                        matched_keywords=[kw]
                    ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def search_by_keywords(self, keywords: List[str], top_k: int = 20,
                           min_fin_score: int = 3) -> List[SearchResult]:
        """按关键词检索"""
        results = []
        seen_ids = set()

        for kw in keywords:
            doc_ids = self._keyword_index.get(kw, [])
            for doc_id in doc_ids[:20]:
                if doc_id in seen_ids:
                    continue
                seen_ids.add(doc_id)
                doc = self._documents.get(doc_id)
                if doc and doc.fin_int_score >= min_fin_score:
                    results.append(SearchResult(
                        doc=doc,
                        score=self._compute_relevance(doc, keywords),
                        matched_keywords=[kw]
                    ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def search_by_domain(self, domain: str, top_k: int = 20) -> List[SearchResult]:
        """按来源域名检索"""
        doc_ids = self._domain_index.get(domain, [])
        return [SearchResult(doc=self._documents[did], score=1.0)
                for did in doc_ids[:top_k] if did in self._documents]

    def _compute_relevance(self, doc: YiZhaoDocument, keywords: List[str]) -> float:
        """计算文档与关键词的相关性得分"""
        score = 0.0
        text_lower = doc.text[:3000].lower()
        title_lower = doc.title.lower()

        for kw in keywords:
            kw_lower = kw.lower()
            # 标题命中权重更高
            title_count = title_lower.count(kw_lower)
            score += title_count * 3.0
            # 正文命中
            text_count = text_lower.count(kw_lower)
            score += text_count * 1.0

        # 金融相关性加成
        score *= (doc.fin_int_score / 5.0)

        return score

    # ---- 统计分析 ----
    def get_market_sentiment(self, code: str = None,
                             keywords: List[str] = None) -> Dict:
        """
        计算市场情绪指标
        返回: {'sentiment_score': float, 'positive_ratio': float,
                'negative_ratio': float, 'article_count': int}
        """
        if code:
            results = self.search_by_code(code, top_k=50)
        elif keywords:
            results = self.search_by_keywords(keywords, top_k=50)
        else:
            return {'error': '请指定 code 或 keywords'}

        if not results:
            return {'sentiment_score': 0.5, 'positive_ratio': 0.0,
                    'negative_ratio': 0.0, 'article_count': 0}

        # 简单情感分析 (基于正负面关键词)
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
        """获取标的相关的关键事件摘要"""
        results = self.search_by_code(code, top_k=top_k)
        events = []
        for r in results:
            events.append({
                'title': r.doc.title,
                'source': r.doc.source_domain,
                'relevance': round(r.score, 2),
                'fin_score': r.doc.fin_int_score,
                'snippet': r.doc.text[:200] + '...' if len(r.doc.text) > 200 else r.doc.text,
                'keywords': r.matched_keywords
            })
        return events

    # ---- 工具方法 ----
    @property
    def is_loaded(self) -> bool:
        return self._loaded and len(self._documents) > 0

    @property
    def stats(self) -> Dict:
        return self._stats.copy()

    def get_doc_count(self) -> int:
        return len(self._documents)

    def print_stats(self):
        """打印数据集统计信息"""
        if not self._loaded:
            print("[YiZhao] 数据未加载")
            return
        print(f"\n{'='*50}")
        print(f"  YiZhao 数据集统计")
        print(f"{'='*50}")
        print(f"  总文档数: {self._stats.get('total_docs', 0):,}")
        print(f"  域名数: {self._stats.get('domains', 0)}")
        print(f"  已索引关键词: {self._stats.get('keywords_indexed', 0)}")
        print(f"  平均文本长度: {self._stats.get('avg_text_length', 0):.0f} 字符")
        print(f"\n  金融得分分布:")
        for score, count in sorted(self._stats.get('score_distribution', {}).items()):
            bar = '█' * min(int(int(count) / max(1, self.get_doc_count()) * 30), 30)
            print(f"    得分{score}: {bar} {count}")
        print(f"\n  主要来源域名:")
        for domain, count in self._stats.get('top_domains', [])[:5]:
            print(f"    {domain}: {count}")


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
            config.cache_dir = os.path.join(data_dir, 'cache')
            config.index_dir = os.path.join(data_dir, 'index')
        _global_loader = YiZhaoDataLoader(config)

        if not _global_loader.load_from_cache():
            print("[YiZhao] 本地无缓存, 尝试从 ModelScope 下载...")
            _global_loader.download_subset(max_size_gb=5.0)

    return _global_loader


# ============================================================
# 命令行入口
# ============================================================
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='YiZhao 金融数据集加载器')
    parser.add_argument('--download', action='store_true', help='下载数据集')
    parser.add_argument('--stats', action='store_true', help='显示统计')
    parser.add_argument('--search', type=str, help='按代码检索')
    parser.add_argument('--sentiment', type=str, help='分析情绪')
    parser.add_argument('--events', type=str, help='查看事件')
    parser.add_argument('--top-k', type=int, default=10, help='返回条数')

    args = parser.parse_args()
    loader = get_yizhao_loader()

    if args.download:
        loader.download_subset()
        loader.print_stats()
    elif args.stats:
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
    else:
        loader.print_stats()
