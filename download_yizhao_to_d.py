# -*- coding: utf-8 -*-
"""
YiZhao-FinDataSet 下载脚本 — 保存到 D 盘
目标: D:\YiZhao-FinDataSet\

数据集: 哈工大(深圳) + 招商银行AI实验室 — 2TB金融语料库
  - 936GB 中文金融文本
  - 100GB 英文金融文本
  - 1TB 多模态数据

本脚本下载高质量中文金融文本子集 (5-10GB)
"""

import sys
import os
import json
import time
import ssl
import hashlib
import urllib.request
from pathlib import Path
from datetime import datetime

# ============================================================
# 配置
# ============================================================
D_DRIVE_ROOT = r"D:\YiZhao-FinDataSet"
DATA_DIR = os.path.join(D_DRIVE_ROOT, "data")
CACHE_DIR = os.path.join(D_DRIVE_ROOT, "cache")
INDEX_DIR = os.path.join(D_DRIVE_ROOT, "index")
OUTPUT_FILE = os.path.join(DATA_DIR, "yizhao_subset.jsonl")

# 下载限制
MAX_DOWNLOAD_GB = 10.0  # 最多下载10GB
MIN_FIN_SCORE = 3        # 最低金融相关性得分 (1-5)
MAX_FILES = 10           # 最多处理文件数

# 标的映射关键词 (用于索引构建)
PORTFOLIO_KEYWORDS = {
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
    "518880": ["黄金ETF", "黄金", "避险", "贵金属", "金价"],
    # 扩展标的
    "300308": ["中际旭创", "光模块", "光通信", "算力", "800G"],
    "688041": ["海光信息", "CPU", "DCU", "信创", "服务器"],
    "688981": ["中芯国际", "晶圆", "代工", "先进制程", "芯片制造"],
    "300750": ["宁德时代", "锂电池", "动力电池", "储能", "钠离子"],
    "600019": ["宝钢股份", "钢铁", "板材", "汽车板", "硅钢"],
    "600219": ["南山铝业", "铝", "电解铝", "航空板", "汽车铝"],
    "000408": ["藏格矿业", "钾肥", "锂矿", "盐湖", "矿产资源"],
    "603259": ["药明康德", "CXO", "医药外包", "新药研发", "临床"],
    "002422": ["科伦药业", "输液", "抗生素", "仿制药", "创新药"],
    "600900": ["长江电力", "水电", "电力", "三峡", "清洁能源"],
    "601899": ["紫金矿业", "金矿", "铜矿", "有色金属", "矿业"],
    "300059": ["东方财富", "券商", "基金", "互联网券商", "天天基金"],
    "600036": ["招商银行", "银行", "零售银行", "理财", "财富管理"],
    "688256": ["寒武纪", "AI芯片", "GPU", "人工智能", "算力"],
}

# 金融领域关键词
FIN_KEYWORDS = [
    "股票", "A股", "大盘", "指数", "行业", "板块", "涨跌", "行情",
    "政策", "监管", "央行", "利率", "降息", "加息", "货币",
    "业绩", "财报", "营收", "利润", "分红", "ROE", "PE", "估值",
    "风险", "回撤", "波动", "杠杆", "做空", "爆仓", "熔断",
    "并购", "重组", "IPO", "上市", "退市", "定增",
    "新能源", "半导体", "医药", "消费", "科技", "制造", "金融",
    "基金", "ETF", "量化", "策略", "投资", "投机",
]


# ============================================================
# 核心下载逻辑
# ============================================================

def create_dirs():
    """创建目标目录"""
    for d in [DATA_DIR, CACHE_DIR, INDEX_DIR]:
        os.makedirs(d, exist_ok=True)
    print(f"[目录] 就绪: {D_DRIVE_ROOT}")
    print(f"  data  : {DATA_DIR}")
    print(f"  cache : {CACHE_DIR}")
    print(f"  index : {INDEX_DIR}")


def fetch_file_list():
    """从 ModelScope API 获取文件列表"""
    api_url = ("https://www.modelscope.cn/api/v1/datasets/"
               "CMB_AILab/YiZhao-FinDataSet/repo/files?Source=SDK")

    ctx = ssl.create_default_context()
    req = urllib.request.Request(api_url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    print(f"[API] 获取文件列表: {api_url}")
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    files = data.get('Data', {}).get('Files', [])
    print(f"[API] 发现 {len(files)} 个远程文件")

    # 打印前20个文件名
    for f in files[:20]:
        name = f.get('Name', '?')
        size = f.get('Size', 0) / 1024**2
        print(f"  {name} ({size:.1f}MB)")

    if len(files) > 20:
        print(f"  ... 还有 {len(files)-20} 个文件")

    return files


def select_target_files(files):
    """选择要下载的文件: 优先中文高金融相关性"""
    zh_files = []
    en_files = []
    other_files = []

    for f in files:
        name = f.get('Name', '')
        if not name.endswith('.jsonl'):
            continue
        name_lower = name.lower()
        if 'zh' in name_lower or 'chinese' in name_lower:
            zh_files.append(f)
        elif 'en' in name_lower or 'english' in name_lower:
            en_files.append(f)
        else:
            other_files.append(f)

    # 中文优先，然后英文，最后其他
    target = zh_files + en_files + other_files

    print(f"\n[选择] 中文文件: {len(zh_files)}, 英文文件: {len(en_files)}, 其他: {len(other_files)}")
    print(f"[选择] 将处理最多 {MAX_FILES} 个文件")

    return target[:MAX_FILES]


def download_and_process_file(file_info, ctx, max_bytes, processed_bytes,
                               total_downloaded, all_docs, keyword_index):
    """下载单个文件并解析"""
    fname = file_info.get('Name', 'unknown.jsonl')
    furl = file_info.get('Url') or file_info.get('DownloadUrl')
    if not furl:
        print(f"  [SKIP] {fname}: 无下载URL")
        return processed_bytes, total_downloaded, False

    file_size = file_info.get('Size', 0) / 1024**2
    print(f"\n  [下载] {fname} ({file_size:.1f}MB)...", end=" ", flush=True)

    try:
        req = urllib.request.Request(furl, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, context=ctx, timeout=120) as fresp:
            content = fresp.read()

        file_mb = len(content) / 1024**2
        print(f"{file_mb:.1f}MB 下载完成, 解析中...", end=" ", flush=True)

        lines = content.decode('utf-8').strip().split('\n')
        file_downloaded = 0
        file_bytes = 0

        for line in lines:
            if processed_bytes + file_bytes >= max_bytes:
                break
            try:
                item = json.loads(line)
                meta = item.get('meta', item)
                fin_score = int(meta.get('fin_int_score', 0))
                if fin_score < MIN_FIN_SCORE:
                    continue
                language = meta.get('language', 'zh')
                if language not in ('zh', 'en'):
                    continue

                doc_id = meta.get('id', hashlib.md5(
                    item.get('text', '').encode()
                ).hexdigest()[:16])
                text = item.get('text', '')
                title = meta.get('title', '')
                source = meta.get('source_domain', '')
                qa = item.get('qa', [])

                doc = {
                    'id': doc_id,
                    'url': meta.get('url', ''),
                    'title': title,
                    'source_domain': source,
                    'text': text,
                    'fin_int_score': fin_score,
                    'risk_score': float(meta.get('risk_score', 0.0)),
                    'language': language,
                    'qa_pairs': qa,
                }
                all_docs.append(doc)

                text_bytes = len(text.encode('utf-8'))
                file_bytes += text_bytes
                file_downloaded += 1

                # 构建关键词索引
                for kw_set in PORTFOLIO_KEYWORDS.values():
                    for kw in kw_set:
                        if kw in title or kw in text[:2000]:
                            if kw not in keyword_index:
                                keyword_index[kw] = []
                            keyword_index[kw].append(doc_id)
                            break

            except Exception:
                continue

        processed_bytes += file_bytes
        total_downloaded += file_downloaded
        print(f"→ 提取 {file_downloaded} 篇 (累计 {total_downloaded} 篇, "
              f"{processed_bytes/1024**2:.1f}MB/{max_bytes/1024**3:.1f}GB)")

        return processed_bytes, total_downloaded, processed_bytes >= max_bytes

    except Exception as e:
        print(f"失败: {e}")
        return processed_bytes, total_downloaded, False


def save_results(all_docs, keyword_index, total_downloaded):
    """保存下载结果和索引"""
    # 1. 保存 jsonl
    print(f"\n[保存] 写入 {len(all_docs)} 条记录到 {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for doc in all_docs:
            f.write(json.dumps(doc, ensure_ascii=False) + '\n')

    file_mb = os.path.getsize(OUTPUT_FILE) / 1024**2
    print(f"[保存] 文件大小: {file_mb:.1f}MB")

    # 2. 保存关键词索引
    index_file = os.path.join(INDEX_DIR, 'keyword_index.json')
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(keyword_index, f, ensure_ascii=False, indent=2)
    print(f"[保存] 关键词索引: {len(keyword_index)} 个关键词")

    # 3. 统计
    score_dist = {}
    domain_dist = {}
    total_len = 0
    for doc in all_docs:
        score = doc['fin_int_score']
        score_dist[str(score)] = score_dist.get(str(score), 0) + 1
        domain = doc['source_domain'] or 'unknown'
        domain_dist[domain] = domain_dist.get(domain, 0) + 1
        total_len += len(doc['text'])

    stats = {
        'total_docs': len(all_docs),
        'total_keywords_indexed': len(keyword_index),
        'score_distribution': score_dist,
        'avg_text_length': round(total_len / max(len(all_docs), 1), 1),
        'top_domains': sorted(domain_dist.items(), key=lambda x: x[1], reverse=True)[:20],
        'download_time': datetime.now().isoformat(),
        'keywords_per_stock': {k: sum(1 for kw in v if kw in keyword_index)
                               for k, v in PORTFOLIO_KEYWORDS.items() if k in [
                                   '601088','000425','002371','300274','300308',
                                   '688041','688981','300750','600276','600019'
                               ]}
    }

    stats_file = os.path.join(DATA_DIR, 'stats.json')
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"[保存] 统计信息 → {stats_file}")

    return stats


def update_config():
    """更新 yizhao_data_loader.py 的默认路径"""
    loader_file = os.path.join(os.path.dirname(__file__), 'yizhao_data_loader.py')

    if not os.path.exists(loader_file):
        print("[警告] 未找到 yizhao_data_loader.py")
        return

    with open(loader_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 更新默认路径配置
    old_dir = 'data_dir: str = "data/yizhao"'
    new_dir = f'data_dir: str = r"{DATA_DIR}"'
    if old_dir in content:
        content = content.replace(old_dir, new_dir)
        print(f"[配置] 已更新默认 data_dir → {DATA_DIR}")

    old_cache = 'cache_dir: str = "data/yizhao/cache"'
    new_cache = f'cache_dir: str = r"{CACHE_DIR}"'
    if old_cache in content:
        content = content.replace(old_cache, new_cache)
        print(f"[配置] 已更新默认 cache_dir → {CACHE_DIR}")

    old_index = 'index_dir: str = "data/yizhao/index"'
    new_index = f'index_dir: str = r"{INDEX_DIR}"'
    if old_index in content:
        content = content.replace(old_index, new_index)
        print(f"[配置] 已更新默认 index_dir → {INDEX_DIR}")

    with open(loader_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("[配置] yizhao_data_loader.py 已更新")


def verify_download():
    """验证下载结果"""
    print("\n" + "=" * 60)
    print("  验证下载结果")
    print("=" * 60)

    if not os.path.exists(OUTPUT_FILE):
        print("[失败] jsonl 文件不存在!")
        return False

    size_mb = os.path.getsize(OUTPUT_FILE) / 1024**2
    print(f"  文件大小: {size_mb:.1f}MB")

    if size_mb < 1:
        print("[警告] 文件太小, 可能下载失败")
        return False

    # 统计行数
    count = 0
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        for _ in f:
            count += 1
    print(f"  文档数量: {count:,}")

    if count < 1000:
        print("[警告] 文档数量较少, 推荐至少 10,000+ 篇用于因子分析")
        return False

    print(f"\n  ✓ 下载验证通过: {count:,} 篇金融文档")
    return True


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("  YiZhao-FinDataSet 下载工具")
    print("  目标: D:\\YiZhao-FinDataSet\\")
    print(f"  上限: {MAX_DOWNLOAD_GB}GB | 最低金融分: {MIN_FIN_SCORE}")
    print("=" * 60)

    create_dirs()

    # 检查是否已下载
    if os.path.exists(OUTPUT_FILE):
        size_mb = os.path.getsize(OUTPUT_FILE) / 1024**2
        count = 0
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            for _ in f:
                count += 1
        print(f"\n[发现] 已有缓存: {size_mb:.1f}MB, {count:,} 篇")
        resp = input("是否重新下载? (y/N): ").strip().lower()
        if resp != 'y':
            print("[跳过] 使用已有缓存")
            update_config()
            return

    # 获取文件列表
    try:
        files = fetch_file_list()
    except Exception as e:
        print(f"\n[错误] 获取文件列表失败: {e}")
        print("[方案2] 尝试 modelscope SDK...")
        return try_modelscope_sdk()

    if not files:
        print("[错误] 文件列表为空")
        return

    # 选择目标文件
    target_files = select_target_files(files)

    # 下载处理
    ctx = ssl.create_default_context()
    max_bytes = int(MAX_DOWNLOAD_GB * 1024**3)
    processed_bytes = 0
    total_downloaded = 0
    all_docs = []
    keyword_index = {}

    start_time = time.time()

    for file_info in target_files:
        processed_bytes, total_downloaded, should_stop = download_and_process_file(
            file_info, ctx, max_bytes, processed_bytes,
            total_downloaded, all_docs, keyword_index
        )
        if should_stop:
            print(f"\n[完成] 已达到 {MAX_DOWNLOAD_GB}GB 上限")
            break

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"  下载完成!")
    print(f"  耗时: {elapsed/60:.1f} 分钟")
    print(f"  文档: {total_downloaded:,} 篇")
    print(f"  数据: {processed_bytes/1024**3:.2f}GB")
    print(f"{'='*60}")

    if total_downloaded == 0:
        print("\n[错误] 未能下载任何文档，请检查网络连接")
        return

    # 保存
    stats = save_results(all_docs, keyword_index, total_downloaded)

    # 更新配置
    update_config()

    # 验证
    verify_download()

    # 打印统计
    print(f"\n{'='*60}")
    print(f"  数据集统计")
    print(f"{'='*60}")
    print(f"  总文档: {stats['total_docs']:,}")
    print(f"  关键词索引: {stats['total_keywords_indexed']} 个")
    print(f"  平均文本长度: {stats['avg_text_length']:.0f} 字符")
    print(f"\n  金融得分分布:")
    for score, count in sorted(stats['score_distribution'].items()):
        bar = '█' * min(int(count / max(stats['total_docs'], 1) * 40), 40)
        print(f"    得分{score}: {bar} {count:,}")
    print(f"\n  主要来源 (TOP 10):")
    for domain, count in stats['top_domains'][:10]:
        print(f"    {domain}: {count:,}")
    print(f"\n  各标的关键词覆盖率:")
    for code, count in stats.get('keywords_per_stock', {}).items():
        name = list(PORTFOLIO_KEYWORDS.get(code, ['?']))[0]
        total_kw = len(PORTFOLIO_KEYWORDS.get(code, []))
        print(f"    {name} ({code}): {count}/{total_kw} 关键词命中")


def try_modelscope_sdk():
    """备用方案: 使用 modelscope SDK"""
    try:
        from modelscope.msdatasets import MsDataset

        print("[SDK] 尝试加载 YiZhao-FinDataSet ...")
        ds = None
        for subset in ['zh', 'en', 'default', None]:
            try:
                ds = MsDataset.load(
                    'CMB_AILab/YiZhao-FinDataSet',
                    subset_name=subset,
                    split='train',
                    cache_dir=CACHE_DIR
                )
                print(f"[SDK] 子集 '{subset}': {len(ds)} 条记录")
                break
            except Exception as e:
                print(f"[SDK] 子集 '{subset}' 失败: {e}")
                continue

        if ds is None:
            print("[SDK] 无法加载任何子集")
            return

        max_bytes = int(MAX_DOWNLOAD_GB * 1024**3)
        total_bytes = 0
        all_docs = []
        keyword_index = {}

        for item in ds:
            try:
                meta = item.get('meta', item)
                fin_score = meta.get('fin_int_score', 0)
                if isinstance(fin_score, (int, float)) and fin_score < MIN_FIN_SCORE:
                    continue
                language = meta.get('language', '')
                if language not in ('zh', 'en'):
                    continue

                doc_id = meta.get('id', hashlib.md5(
                    item.get('text', '').encode()
                ).hexdigest()[:16])
                text = item.get('text', '')
                title = meta.get('title', '')

                doc = {
                    'id': doc_id,
                    'url': meta.get('url', ''),
                    'title': title,
                    'source_domain': meta.get('source_domain', ''),
                    'text': text,
                    'fin_int_score': int(fin_score),
                    'risk_score': float(meta.get('risk_score', 0.0)),
                    'language': language,
                    'qa_pairs': item.get('qa', []),
                }
                all_docs.append(doc)
                total_bytes += len(text.encode('utf-8'))

                for kw_set in PORTFOLIO_KEYWORDS.values():
                    for kw in kw_set:
                        if kw in title or kw in text[:2000]:
                            if kw not in keyword_index:
                                keyword_index[kw] = []
                            keyword_index[kw].append(doc_id)

                if total_bytes >= max_bytes:
                    break
            except Exception:
                continue

        print(f"[SDK] 下载完成: {len(all_docs):,} 篇, {total_bytes/1024**3:.2f}GB")
        save_results(all_docs, keyword_index, len(all_docs))
        update_config()
        verify_download()

    except Exception as e:
        print(f"[SDK] 失败: {e}")
        print("\n请手动下载:")
        print("  1. 访问 https://modelscope.cn/datasets/CMB_AILab/YiZhao-FinDataSet")
        print("  2. 下载中文子集 jsonl 文件")
        print(f"  3. 保存到: {OUTPUT_FILE}")
        print("  4. 重新运行本脚本")


if __name__ == '__main__':
    main()
