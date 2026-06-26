# -*- coding: utf-8 -*-
"""
C盘空间清理脚本
目标: 释放至少10GB空间
"""

import os
import shutil
import subprocess
from datetime import datetime

def get_folder_size(path):
    """获取文件夹大小(GB)"""
    try:
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    try:
                        total += os.path.getsize(fp)
                    except:
                        pass
        return total / (1024**3)
    except:
        return 0

def check_admin():
    """检查管理员权限"""
    try:
        return os.getuid() == 0 or subprocess.check_call(['net', 'session'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    except:
        return False

print('='*70)
print('C盘空间清理工具')
print('='*70)
print(f'执行时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print()

# 检查当前C盘空间
print('[1/4] 检查当前C盘空间...')
try:
    result = subprocess.run(['powershell', '-Command', 
        'Get-PSDrive C | Select-Object Used,Free'], 
        capture_output=True, text=True)
    print(result.stdout)
except:
    pass

print('\n' + '-'*70)
print('可清理项目列表:')
print('-'*70)

cleanup_items = [
    {
        'name': 'Python pip缓存',
        'path': os.path.expanduser('~/.cache/pip'),
        'estimated': 0.5,
        'safe': True
    },
    {
        'name': 'Node.js npm缓存',
        'path': os.path.expanduser('~/.npm'),
        'estimated': 1.0,
        'safe': True
    },
    {
        'name': 'Docker镜像(如果不需要)',
        'path': 'C:\\ProgramData\\docker',
        'estimated': 2.0,
        'safe': False
    },
    {
        'name': 'Windows临时文件',
        'path': 'C:\\Windows\\Temp',
        'estimated': 1.0,
        'safe': True
    },
    {
        'name': '用户临时文件',
        'path': os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp'),
        'estimated': 0.5,
        'safe': True
    },
]

print()
for i, item in enumerate(cleanup_items, 1):
    safe_tag = '✅ 安全' if item['safe'] else '⚠️ 谨慎'
    print(f'{i}. {item["name"]:<25} ~{item["estimated"]:.1f}GB  {safe_tag}')

print('-'*70)
print(f'预计可释放: ~{sum(i["estimated"] for i in cleanup_items):.1f}GB')
print()

# 执行清理
print('[2/4] 执行清理...')
print()

total_freed = 0

# 1. 清理pip缓存
pip_cache = os.path.expanduser('~/.cache/pip')
if os.path.exists(pip_cache):
    size = get_folder_size(pip_cache)
    try:
        shutil.rmtree(pip_cache)
        total_freed += size
        print(f'[OK] pip缓存: 释放{size:.2f}GB')
    except Exception as e:
        print(f'[SKIP] pip缓存: {e}')

# 2. 清理npm缓存
npm_cache = os.path.expanduser('~/.npm')
if os.path.exists(npm_cache):
    size = get_folder_size(npm_cache)
    try:
        shutil.rmtree(npm_cache)
        total_freed += size
        print(f'[OK] npm缓存: 释放{size:.2f}GB')
    except Exception as e:
        print(f'[SKIP] npm缓存: {e}')

# 3. 清理Windows临时文件
temp_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Temp')
if os.path.exists(temp_dir):
    size = get_folder_size(temp_dir)
    try:
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            if os.path.isfile(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        total_freed += size
        print(f'[OK] 临时文件: 释放{size:.2f}GB')
    except Exception as e:
        print(f'[PARTIAL] 临时文件: 部分清理({e})')

# 4. 运行磁盘清理工具
print()
print('[3/4] 运行Windows磁盘清理...')
try:
    subprocess.run(['cleanmgr', '/d', 'C'], check=True, timeout=30)
    print('[OK] 磁盘清理工具已启动(请手动点击"确定")')
except subprocess.TimeoutExpired:
    print('[SKIP] 磁盘清理超时')
except Exception as e:
    print(f'[WARN] 磁盘清理: {e}')

print()
print('[4/4] 清理完成统计')
print('='*70)
print(f'已释放空间: {total_freed:.2f} GB')
print()

# 显示建议
print('进一步清理建议:')
print('  1. 卸载不常用的软件(控制面板 → 程序和功能)')
print('  2. 清理浏览器缓存(Chrome/Firefox/Edge)')
print('  3. 转移大型文件到其他磁盘')
print('  4. 禁用Hibernate: powercfg -h off (释放内存大小)')
print('  5. 清理旧的系统还原点: vssadmin delete shadows /all')
print()
print('='*70)
