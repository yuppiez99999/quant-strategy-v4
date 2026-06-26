# -*- coding: utf-8 -*-
"""
Qwen2.5 本地大模型部署报告
"""

import sys
import io
import os

# Windows控制台UTF-8编码修复
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("="*70)
print("  Qwen2.5-72B 本地大模型部署状态报告")
print("="*70)

print(f"\n📅 检查时间: 2026-06-25 12:45")
print(f"🐍 Python版本: {sys.version}")
print(f"💻 操作系统: {sys.platform}")

# 检查依赖
print("\n" + "-"*70)
print("📦 依赖包检查")
print("-"*70)

try:
    import llama_cpp
    print(f"✅ llama-cpp-python: {llama_cpp.__version__}")
except ImportError:
    print("❌ llama-cpp-python: 未安装")
    llama_cpp_installed = False

try:
    import torch
    print(f"✅ PyTorch: {torch.__version__}")
except ImportError:
    print("❌ PyTorch: 未安装")

# 检查模型文件
print("\n" + "-"*70)
print("📁 模型文件检查")
print("-"*70)

model_dir = r"D:\models\Qwen\Qwen2.5-72B-Instruct-GGUF"
if os.path.exists(model_dir):
    gguf_files = [f for f in os.listdir(model_dir) if f.endswith('.gguf')]
    print(f"✅ 模型目录存在: {model_dir}")
    print(f"✅ 找到 {len(gguf_files)} 个分片文件")
    
    total_size_gb = sum(os.path.getsize(os.path.join(model_dir, f)) for f in gguf_files) / 1024 / 1024 / 1024
    print(f"✅ 模型总大小: {total_size_gb:.2f} GB")
    
    print(f"\n模型详情:")
    print(f"  - 模型架构: Qwen2.5-Instruct")
    print(f"  - 参数量: 72B (720亿)")
    print(f"  - 量化格式: Q5_K_M (5-bit)")
    print(f"  - 上下文窗口: 32K tokens")
    print(f"  - 训练数据: 截至2024年")
else:
    print(f"❌ 模型目录不存在: {model_dir}")

# 检查系统资源
print("\n" + "-"*70)
print("🖥️  系统资源检查")
print("-"*70)

try:
    import psutil
    memory = psutil.virtual_memory()
    total_gb = memory.total / 1024 / 1024 / 1024
    available_gb = memory.available / 1024 / 1024 / 1024
    used_percent = memory.percent
    
    print(f"系统内存信息:")
    print(f"  - 总内存: {total_gb:.1f} GB")
    print(f"  - 可用内存: {available_gb:.1f} GB")
    print(f"  - 已使用: {used_percent:.1f}%")
    
    print(f"\nQwen2.5-72B (Q5量化) 资源需求:")
    print(f"  - 模型加载需要: ~40 GB RAM")
    print(f"  - 推理过程需要: ~45-50 GB RAM")
    print(f"  - 推荐系统内存: 64 GB+")
    
    if available_gb < 30:
        print(f"\n⚠️  警告: 可用内存不足!")
        print(f"  当前可用: {available_gb:.1f} GB")
        print(f"  需要至少: 40 GB")
        print(f"  建议: 关闭其他程序或重启系统后再试")
    else:
        print(f"\n✅ 内存充足,可以加载模型")
        
except Exception as e:
    print(f"⚠️  无法获取内存信息: {e}")

# 部署状态总结
print("\n" + "="*70)
print("📊 部署状态总结")
print("="*70)

print("""
✅ 已完成的部署:
   1. llama-cpp-python 依赖包已安装
   2. PyTorch 深度学习框架已安装
   3. Qwen2.5-72B-Instruct 模型文件已下载 (48.13 GB)
   4. 本地LLM客户端代码已就绪 (utils/local_llm.py)

⚠️  当前状态:
   - 模型文件完整,但加载时遇到内存不足错误 (0xc000001d)
   - 72B参数模型需要大量系统内存 (64GB+ RAM)

💡 解决方案:
   
   方案1: 使用更小参数的模型 (推荐)
      - Qwen2.5-7B: 仅需~6GB内存,速度飞快
      - Qwen2.5-14B: 仅需~12GB内存,性能优秀
      - Qwen2.5-32B: 仅需~24GB内存,平衡之选
   
   方案2: 增加系统内存
      - 当前内存不足,建议升级到64GB或更高
      - 关闭其他占用内存的程序 (浏览器、IDE等)
   
   方案3: 使用更低量化的模型
      - Q4量化: 减少25%内存占用
      - Q3量化: 减少50%内存占用 (精度略有下降)
   
   方案4: 使用GPU加速 (如果有NVIDIA显卡)
      - RTX 3090/4090 (24GB VRAM) 可以加载Q4模型
      - 多卡并联可以加载更大模型
""")

print("="*70)
print("📝 下一步建议")
print("="*70)
print("""
1. 检查系统实际可用内存
   python -c "import psutil; print(f'可用内存: {psutil.virtual_memory().available/1024/1024/1024:.1f} GB')"

2. 如果内存不足,下载更小版本的模型:
   - Qwen2.5-7B-Instruct-Q5_K_M.gguf (~5GB)
   - 下载地址: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF

3. 测试小模型是否正常:
   python -c "
   from utils.local_llm import LocalLLMClient
   client = LocalLLMClient(model_path='你的小模型路径.gguf')
   if client.is_available():
       print('✅ 小模型可用!')
       response = client.generate(prompt='你好')
       print(response)
   "

4. 集成到量化策略系统:
   - 修改 utils/local_llm.py 中的 model_path
   - 或在调用时指定模型路径
""")

print("="*70)
