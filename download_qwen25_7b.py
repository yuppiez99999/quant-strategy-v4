# -*- coding: utf-8 -*-
"""
下载Qwen2.5-7B-Instruct GGUF模型
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
print("  下载Qwen2.5-7B-Instruct GGUF模型")
print("="*70)

repo_id = "Qwen/Qwen2.5-7B-Instruct-GGUF"
filename = "qwen2.5-7b-instruct-q5_k_m.gguf"
local_dir = r"D:\models\Qwen\Qwen2.5-7B-Instruct"

# 确保目录存在
os.makedirs(local_dir, exist_ok=True)

print(f"\n[INFO] 仓库: {repo_id}")
print(f"[INFO] 文件: {filename}")
print(f"[INFO] 保存路径: {local_dir}")
print(f"\n[WAIT] 开始下载...")
print(f"[NOTE] 文件大小约 5.5 GB, 请耐心等待\n")

try:
    # 下载文件
    downloaded_path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=local_dir,
        local_dir_use_symlinks=False  # 实际复制文件而非符号链接
    )
    
    # 获取文件大小
    file_size_mb = os.path.getsize(downloaded_path) / 1024 / 1024
    
    print("\n" + "="*70)
    print("  [SUCCESS] 下载完成!")
    print("="*70)
    print(f"\n[PATH] 文件路径: {downloaded_path}")
    print(f"[SIZE] 文件大小: {file_size_mb:.0f} MB ({file_size_mb/1024:.2f} GB)")
    print(f"\n[NEXT] 下一步:")
    print(f"   1. 更新 utils/local_llm.py 中的模型路径")
    print(f"   2. 运行测试脚本验证模型")
    print(f"   3. 在量化策略系统中使用本地LLM")
    print("="*70)
    
except Exception as e:
    print(f"\n[ERROR] 下载失败: {e}")
    print("\n[HINT] 可能的原因:")
    print("   1. 网络连接问题")
    print("   2. HuggingFace服务器问题")
    print("   3. 磁盘空间不足")
    print("\n[SOLUTION] 解决方案:")
    print("   - 使用国内镜像: https://hf-mirror.com/")
    print("   - 手动下载: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF")
    print("   - 文件: qwen2.5-7b-instruct-q5_k_m.gguf")
