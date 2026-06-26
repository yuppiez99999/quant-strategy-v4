# -*- coding: utf-8 -*-
"""
列出Qwen2.5-7B-Instruct-GGUF仓库中的所有可用文件
"""

import sys
import io
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from huggingface_hub import list_repo_files

repo_id = "Qwen/Qwen2.5-7B-Instruct-GGUF"

print("="*70)
print(f"  列出仓库文件: {repo_id}")
print("="*70)
print("\n[INFO] 正在获取文件列表...\n")

try:
    files = list_repo_files(repo_id)
    gguf_files = [f for f in files if f.endswith('.gguf')]
    
    print(f"[RESULT] 找到 {len(gguf_files)} 个GGUF模型文件:\n")
    
    for i, f in enumerate(sorted(gguf_files), 1):
        print(f"  {i:2d}. {f}")
    
    print(f"\n{'='*70}")
    print("  推荐下载的文件 (Q5量化,平衡性能和大小):")
    print("="*70)
    
    # 查找Q5量化的7B模型
    target_files = [f for f in gguf_files if '7b' in f.lower() and 'q5' in f.lower()]
    if target_files:
        for f in sorted(target_files):
            print(f"  -> {f}")
    else:
        print("  未找到7B Q5量化文件,显示所有7B文件:")
        seven_b_files = [f for f in gguf_files if '7b' in f.lower()]
        for f in sorted(seven_b_files)[:5]:
            print(f"  -> {f}")
    
    print(f"\n[NOTE] 使用以下命令下载:")
    if target_files:
        print(f'  hf download {repo_id} {target_files[0]} --local-dir D:\\models\\Qwen\\Qwen2.5-7B-Instruct')
    
except Exception as e:
    print(f"[ERROR] {e}")
