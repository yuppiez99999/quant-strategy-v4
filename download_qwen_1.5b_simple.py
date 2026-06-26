# -*- coding: utf-8 -*-
"""
下载Qwen2.5-1.5B-Instruct模型
"""

import os
import sys
import io

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from huggingface_hub import hf_hub_download

# 使用国内镜像
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

print("="*70)
print("  下载Qwen2.5-1.5B-Instruct模型")
print("="*70)

repo_id = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
filename = "qwen2.5-1.5b-instruct-q5_k_m.gguf"
local_dir = r"D:\models\Qwen\Qwen2.5-1.5B-Instruct"

os.makedirs(local_dir, exist_ok=True)

print(f"\n[INFO] 仓库: {repo_id}")
print(f"[INFO] 文件: {filename}")
print(f"[INFO] 保存: {local_dir}")
print(f"[INFO] 镜像: https://hf-mirror.com")
print(f"\n[WAIT] 开始下载 (约1.3GB)...\n")

try:
    path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=local_dir,
        local_dir_use_symlinks=False
    )
    
    size_mb = os.path.getsize(path) / 1024 / 1024
    
    print("\n" + "="*70)
    print("  [SUCCESS] 下载完成!")
    print("="*70)
    print(f"\n[PATH] {path}")
    print(f"[SIZE] {size_mb:.0f} MB ({size_mb/1024:.2f} GB)")
    print(f"\n[NEXT] 下一步:")
    print(f"  1. 更新 utils/local_llm.py 配置")
    print(f"  2. 测试模型加载")
    print("="*70)
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    print(f"\n[MANUAL] 手动下载:")
    print(f"  https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF")
