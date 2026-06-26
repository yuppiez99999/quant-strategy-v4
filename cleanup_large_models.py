# -*- coding: utf-8 -*-
"""
清理大模型文件,释放磁盘空间
保留: Qwen2.5-1.5B (约400MB)
删除: Qwen2.5-72B (约48GB)
"""

import os
import shutil
import sys

def get_folder_size(path):
    """获取文件夹大小(GB)"""
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total += os.path.getsize(fp)
    return total / (1024**3)

def count_files(path):
    """统计文件数量"""
    count = 0
    for dirpath, dirnames, filenames in os.walk(path):
        count += len(filenames)
    return count

# 模型目录
models_dir = r'D:\models\Qwen'

if not os.path.exists(models_dir):
    print('[ERROR] 目录不存在:', models_dir)
    sys.exit(1)

# 列出所有模型
print('='*70)
print('当前模型列表')
print('='*70)

models = {}
for item in os.listdir(models_dir):
    item_path = os.path.join(models_dir, item)
    if os.path.isdir(item_path):
        size_gb = get_folder_size(item_path)
        file_count = count_files(item_path)
        models[item] = {'size': size_gb, 'files': file_count, 'path': item_path}
        print(f'{item:<35} {size_gb:>8.2f} GB  {file_count:>4} 个文件')

print('='*70)

# 确认要删除的模型
print('\n建议保留的模型 (小模型,适合16GB内存):')
print('  - Qwen2.5-1.5B-Instruct (~0.24 GB)')
print('  - Qwen2.5-7B-Instruct (~0.45 GB)')

print('\n建议删除的模型 (太大,需要48GB+内存):')
print('  - Qwen2.5-72B-Instruct-GGUF (48.13 GB) ← 将释放48GB空间')

# 自动删除72B模型
print('\n' + '='*70)
print('正在删除 Qwen2.5-72B-Instruct-GGUF...')
print('='*70)

target_dir = os.path.join(models_dir, 'Qwen2.5-72B-Instruct-GGUF')

if os.path.exists(target_dir):
    try:
        size_before = get_folder_size(target_dir)
        shutil.rmtree(target_dir)
        print(f'\n[OK] 已删除: {target_dir}')
        print(f'[OK] 释放空间: {size_before:.2f} GB')
    except Exception as e:
        print(f'\n[ERROR] 删除失败: {e}')
        print('[TIP] 请手动删除: D:\\models\\Qwen\\Qwen2.5-72B-Instruct-GGUF')
else:
    print('\n[SKIP] 目录不存在,无需删除')

# 显示清理后状态
print('\n' + '='*70)
print('清理后的模型列表')
print('='*70)

total_remaining = 0
for item in sorted(models.keys()):
    if item == 'Qwen2.5-72B-Instruct-GGUF':
        print(f'{item:<35} [已删除]')
    else:
        print(f'{item:<35} {models[item]["size"]:>8.2f} GB')
        total_remaining += models[item]['size']

print('-'*70)
print(f'剩余模型总计: {total_remaining:.2f} GB')
print('='*70)

print('\n[SUCCESS] 清理完成!')
print(f'[TIP] 已释放约 {size_before:.2f} GB 空间')
print('[NEXT] 现在可以下载并使用 Qwen2.5-1.5B 模型了')
