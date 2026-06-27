# -*- coding: utf-8 -*-
"""
快速构建 YiZhao 关键词位置索引 (pickle格式)
构建时间 ~60s | 索引大小 ~50MB | 加载时间 ~2s | 检索时间 <100ms
"""
import json
import os
import pickle
import time
import gzip

FILTERED_DIR = r"E:\各种PY程序\11_量化策略\data\yizhao_filtered"
INDEX_PATH = os.path.join(FILTERED_DIR, "keyword_index.pkl.gz")

STOCKS = {
    "300308": ["中际旭创", "光模块"],
    "688041": ["海光信息", "海光", "国产CPU", "DCU"],
    "002371": ["北方华创", "半导体设备", "刻蚀"],
    "688981": ["中芯国际", "SMIC", "晶圆代工"],
    "300750": ["宁德时代", "宁德", "CATL"],
    "000425": ["徐工机械", "工程机械", "挖掘机"],
    "601088": ["中国神华", "神华", "煤炭"],
    "600219": ["南山铝业", "铝业", "电解铝"],
    "600019": ["宝钢股份", "宝钢", "钢铁"],
    "518880": ["华安黄金ETF", "黄金ETF", "黄金", "贵金属"],
    "000408": ["藏格矿业", "藏格", "钾肥", "锂矿"],
    "600276": ["恒瑞医药", "恒瑞", "创新药", "PD-1"],
    "603259": ["药明康德", "药明", "CXO"],
    "002422": ["科伦药业", "科伦", "大输液"],
}

FIN_DOMAINS = [
    "股票", "A股", "大盘", "指数", "行业", "板块", "涨跌", "行情",
    "政策", "监管", "央行", "利率", "货币政策",
    "业绩", "财报", "营收", "利润", "分红", "估值",
    "风险", "回撤", "波动", "做空",
    "并购", "重组", "IPO", "定增",
    "新能源", "半导体", "医药", "消费", "科技", "制造", "金融"
]

all_keywords = set()
for kws in STOCKS.values():
    all_keywords.update(kws)
all_keywords.update(FIN_DOMAINS)

print(f"=== 构建 YiZhao 关键词位置索引 ({len(all_keywords)} 关键词) ===")
start = time.time()

index = {}  # keyword -> [(shard_name, byte_offset, fin_score)]
shards = sorted([f for f in os.listdir(FILTERED_DIR) if f.endswith('.jsonl')])

total = 0
total_matches = 0

for shard_name in shards:
    shard_path = os.path.join(FILTERED_DIR, shard_name)
    shard_matches = 0
    with open(shard_path, 'r', encoding='utf-8', errors='replace') as f:
        while True:
            pos = f.tell()
            line = f.readline()
            if not line:
                break
            total += 1
            try:
                item = json.loads(line.strip())
                meta = item.get('meta', {})
                title = meta.get('title', '')
                text = item.get('text', '')
                combined = title + ' ' + text[:800]
                fin_score = int(meta.get('fin_int_score', 3))
                for kw in all_keywords:
                    if kw in combined:
                        if kw not in index:
                            index[kw] = []
                        index[kw].append((shard_name, pos, fin_score))
                        shard_matches += 1
            except Exception:
                pass
    total_matches += shard_matches
    elapsed = time.time() - start
    print(f"  {shard_name}: {shard_matches} hits / {total} scanned ({elapsed:.0f}s)")

# 压缩保存
with gzip.open(INDEX_PATH, 'wb') as f:
    pickle.dump(index, f, protocol=pickle.HIGHEST_PROTOCOL)

elapsed = time.time() - start
db_size = os.path.getsize(INDEX_PATH) / 1024**2
print(f"\n索引构建完成:")
print(f"  扫描记录: {total:,}")
print(f"  索引命中: {total_matches:,}")
print(f"  唯一关键词: {len(index)}")
print(f"  索引文件: {db_size:.1f}MB (gzip)")
print(f"  总耗时: {elapsed:.1f}s")
print(f"  路径: {INDEX_PATH}")
