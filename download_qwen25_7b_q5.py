# -*- coding: utf-8 -*-
"""
下载Qwen2.5-7B-Instruct Q5量化模型 (2个分片文件)
"""

import os
import sys
import io
from huggingface_hub import hf_hub_download

# Windows控制台UTF-8编码修复
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("="*70)
print("  下载Qwen2.5-7B-Instruct Q5量化模型")
print("="*70)

repo_id = "Qwen/Qwen2.5-7B-Instruct-GGUF"
local_dir = r"D:\models\Qwen\Qwen2.5-7B-Instruct"

# 确保目录存在
os.makedirs(local_dir, exist_ok=True)

# Q5量化模型的两个分片文件
files_to_download = [
    "qwen2.5-7b-instruct-q5_k_m-00001-of-00002.gguf",
    "qwen2.5-7b-instruct-q5_k_m-00002-of-00002.gguf"
]

print(f"\n[INFO] 仓库: {repo_id}")
print(f"[INFO] 保存路径: {local_dir}")
print(f"[INFO] 文件数量: {len(files_to_download)}")
print(f"\n[WAIT] 开始下载...\n")

downloaded_files = []
total_size_mb = 0

for i, filename in enumerate(files_to_download, 1):
    print(f"[{i}/{len(files_to_download)}] 下载: {filename}")
    try:
        downloaded_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=local_dir,
            local_dir_use_symlinks=False
        )
        
        file_size_mb = os.path.getsize(downloaded_path) / 1024 / 1024
        total_size_mb += file_size_mb
        downloaded_files.append(downloaded_path)
        
        print(f"  [OK] 下载完成: {file_size_mb:.0f} MB")
        
    except Exception as e:
        print(f"  [ERROR] 下载失败: {e}")

# 汇总结果
print("\n" + "="*70)
print("  下载结果汇总")
print("="*70)

if downloaded_files:
    print(f"\n[SUCCESS] 成功下载 {len(downloaded_files)} 个文件")
    print(f"[SIZE] 总大小: {total_size_mb:.0f} MB ({total_size_mb/1024:.2f} GB)")
    print(f"\n[FILES] 已保存至:")
    for f in downloaded_files:
        print(f"  - {f}")
    
    print(f"\n[NEXT] 下一步:")
    print(f"  1. 更新 utils/local_llm.py 中的模型路径")
    print(f"  2. 运行测试脚本验证模型")
    print(f"  3. 在量化策略系统中使用本地LLM")
else:
    print(f"\n[ERROR] 下载失败,请检查网络连接")
    print(f"\n[MANUAL] 手动下载:")
    print(f"  访问: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF")
    print(f"  下载: qwen2.5-7b-instruct-q5_k_m-00001-of-00002.gguf")
    print(f"  下载: qwen2.5-7b-instruct-q5_k_m-00002-of-00002.gguf")
    print(f"  保存到: {local_dir}")

print("="*70)
