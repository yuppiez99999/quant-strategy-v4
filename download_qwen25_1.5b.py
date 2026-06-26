#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Qwen2.5-1.5B模型下载脚本
"""

import os
import sys
import io

# 修复编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print('='*70)
print('Qwen2.5-1.5B 模型下载工具')
print('='*70)

# 创建目录
model_dir = r'D:\models\Qwen\Qwen2.5-1.5B'
os.makedirs(model_dir, exist_ok=True)
print(f'\n[DIR] 模型目录: {model_dir}')

# 下载模型
print('\n[DOWNLOAD] 正在从HuggingFace下载...')
print('[INFO] 文件大小: ~1.3GB')
print('[INFO] 预计时间: 5-15分钟 (取决于网络速度)')
print()

try:
    from huggingface_hub import hf_hub_download
    
    model_file = 'qwen2.5-1.5b-instruct-q5_k_m.gguf'
    
    print(f'[FILE] 下载: {model_file}')
    
    downloaded_path = hf_hub_download(
        repo_id='Qwen/Qwen2.5-1.5B-Instruct-GGUF',
        filename=model_file,
        local_dir=model_dir,
        local_dir_use_symlinks=False
    )
    
    print(f'\n✅ 下载完成!')
    print(f'📁 模型路径: {downloaded_path}')
    
    # 检查文件大小
    file_size = os.path.getsize(downloaded_path)
    file_size_mb = file_size / (1024 * 1024)
    print(f'📊 文件大小: {file_size_mb:.0f} MB')
    
except Exception as e:
    print(f'\n❌ 下载失败: {e}')
    print('\n[INFO] 请尝试以下备选方案:')
    print('  1. 检查网络连接')
    print('  2. 使用镜像: https://hf-mirror.com')
    print('  3. 手动下载: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF')
    sys.exit(1)

print('\n' + '='*70)
print('下一步: 更新配置并测试模型')
print('='*70)
