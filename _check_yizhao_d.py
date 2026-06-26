# 检查下载结果
import json, os, glob

data_dir = r'D:\YiZhao-FinDataSet\data\sample'
files = glob.glob(os.path.join(data_dir, '*.jsonl'))
print(f"JSONL files: {files}")

for fp in files:
    print(f"\n=== {os.path.basename(fp)} ===")
    count = 0
    total_text_len = 0
    scores = {}
    langs = {}
    domains = {}
    
    with open(fp, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                item = json.loads(line.strip())
                count += 1
                meta = item.get('meta', item)
                score = meta.get('fin_int_score', 0)
                scores[str(score)] = scores.get(str(score), 0) + 1
                lang = meta.get('language', '?')
                langs[lang] = langs.get(lang, 0) + 1
                dom = meta.get('source_domain', 'unknown')
                domains[dom] = domains.get(dom, 0) + 1
                total_text_len += len(item.get('text', ''))
            except:
                pass
    
    print(f"  记录数: {count}")
    print(f"  平均文本长度: {total_text_len/max(count,1):.0f} 字符")
    print(f"  金融得分分布: {scores}")
    print(f"  语言分布: {langs}")
    top5 = sorted(domains.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"  来源TOP5: {top5}")
