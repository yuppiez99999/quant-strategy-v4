# -*- coding: utf-8 -*-
"""
为 v5.1 组合的每只标的预建专属 JSONL 文件
扫描所有过滤分片一次，将匹配的文档写入对应标的分片
"""
import json
import os
import time

FILTERED_DIR = r"E:\各种PY程序\11_量化策略\data\yizhao_filtered"

STOCKS = {
    "300308": ["中际旭创", "光模块", "800G", "1.6T", "算力光模块"],
    "688041": ["海光信息", "海光", "国产CPU", "DCU", "算力芯片"],
    "002371": ["北方华创", "半导体设备", "刻蚀", "薄膜沉积", "芯片制造"],
    "688981": ["中芯国际", "SMIC", "晶圆代工", "成熟制程", "半导体制造"],
    "300750": ["宁德时代", "宁德", "CATL", "锂电池", "动力电池", "储能电池"],
    "000425": ["徐工机械", "工程机械", "挖掘机", "基建", "装备制造"],
    "601088": ["中国神华", "神华", "煤炭", "能源安全", "煤电一体化"],
    "600219": ["南山铝业", "铝业", "电解铝", "铝加工", "汽车板"],
    "600019": ["宝钢股份", "宝钢", "钢铁", "板材", "汽车钢"],
    "518880": ["华安黄金ETF", "黄金ETF", "黄金", "贵金属", "金价"],
    "000408": ["藏格矿业", "藏格", "钾肥", "锂矿", "盐湖提锂"],
    "600276": ["恒瑞医药", "恒瑞", "创新药", "PD-1", "医药研发"],
    "603259": ["药明康德", "药明", "CXO", "医药外包", "药物发现"],
    "002422": ["科伦药业", "科伦", "大输液", "仿制药", "抗生素"],
}

print("=== 构建标的专属索引文件 ===")
start = time.time()

# 初始化输出文件
ticker_files = {}
ticker_counts = {code: 0 for code in STOCKS}
for code in STOCKS:
    path = os.path.join(FILTERED_DIR, f"ticker_{code}.jsonl")
    ticker_files[code] = open(path, 'w', encoding='utf-8')

# 扫描所有分片
shards = sorted([f for f in os.listdir(FILTERED_DIR) if f.endswith('.jsonl') and f != 'ticker_index.json'])
print(f"分片数: {len(shards)}")

total_processed = 0
total_matched = 0
for shard_name in shards:
    shard_path = os.path.join(FILTERED_DIR, shard_name)
    shard_matched = 0
    with open(shard_path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            total_processed += 1
            try:
                item = json.loads(line.strip())
                title = item.get('meta', {}).get('title', '')
                text = item.get('text', '')
                combined = title + ' ' + text[:1000]

                for code, keywords in STOCKS.items():
                    for kw in keywords:
                        if kw in combined:
                            ticker_files[code].write(line)
                            ticker_counts[code] += 1
                            shard_matched += 1
                            break  # 一个文档只分配一次给同一标的

            except Exception:
                pass

    total_matched += shard_matched
    elapsed = time.time() - start
    print(f"  {shard_name}: {shard_matched} matches (累计 {total_matched}/{total_processed}, {elapsed:.0f}s)")

# 关闭所有文件
for code, f in ticker_files.items():
    f.close()
    path = os.path.join(FILTERED_DIR, f"ticker_{code}.jsonl")
    size = os.path.getsize(path) / 1024**2
    print(f"  {code}: {ticker_counts[code]} docs, {size:.1f}MB")

elapsed = time.time() - start
print(f"\n完成: {total_matched} 匹配 / {total_processed} 扫描 ({elapsed:.1f}s)")

# 保存统计
stats_path = os.path.join(FILTERED_DIR, 'ticker_index.json')
with open(stats_path, 'w', encoding='utf-8') as f:
    json.dump({
        'total_records': total_processed,
        'total_matched': total_matched,
        'ticker_counts': ticker_counts,
        'build_time': time.strftime('%Y-%m-%d %H:%M:%S'),
    }, f, ensure_ascii=False, indent=2)
print(f"统计已保存: {stats_path}")
