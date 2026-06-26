"""
下载 Kronos-small 金融K线预测模型和Tokenizer
"""
import os
import sys
if sys.platform == 'win32':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

from modelscope import snapshot_download

# 创建模型目录
model_dir = r'e:\各种PY程序\11_量化策略\models'
os.makedirs(model_dir, exist_ok=True)

print("=" * 60)
print("开始下载 Kronos-small 金融K线预测模型")
print("=" * 60)

# 下载主模型
print("\n[1/2] 下载 Kronos-small 模型...")
kronos_path = snapshot_download('AI-ModelScope/Kronos-small', cache_dir=model_dir)
print("[OK] 模型已保存到:", kronos_path)

# 下载Tokenizer
print("\n[2/2] 下载 Kronos-Tokenizer-base...")
tokenizer_path = snapshot_download('NeoQuasar/Kronos-Tokenizer-base', cache_dir=model_dir)
print("[OK] Tokenizer已保存到:", tokenizer_path)

print("\n" + "=" * 60)
print("下载完成！")
print("=" * 60)
print("\n模型目录:", model_dir)
print("\n下一步:")
print("1. 验证模型文件完整性")
print("2. 运行测试脚本验证预测功能")
print("3. 集成到量化交易系统")
