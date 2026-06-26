"""
调试Kronos模型加载
"""
import sys
import os

sys.path.insert(0, r'e:\各种PY程序\11_量化策略\Kronos')

print("=" * 60)
print("Kronos模型加载调试")
print("=" * 60)

# 1. 检查文件
print("\n[1] 检查模型文件...")
model_path = r'e:\各种PY程序\11_量化策略\models\AI-ModelScope\Kronos-small'
print(f"  模型路径: {model_path}")
print(f"  存在: {os.path.exists(model_path)}")

if os.path.exists(model_path):
    files = os.listdir(model_path)
    print(f"  文件列表: {files}")
    for f in files:
        fp = os.path.join(model_path, f)
        if os.path.isfile(fp):
            size_mb = os.path.getsize(fp) / (1024*1024)
            print(f"    - {f}: {size_mb:.2f} MB")

# 2. 检查Tokenizer
print("\n[2] 检查Tokenizer...")
tokenizer_path = r'e:\各种PY程序\11_量化策略\Kronos\kronos\tokenizer'
print(f"  Tokenizer路径: {tokenizer_path}")
print(f"  存在: {os.path.exists(tokenizer_path)}")

if os.path.exists(tokenizer_path):
    files = os.listdir(tokenizer_path)
    print(f"  文件列表: {files}")

# 3. 尝试导入
print("\n[3] 导入Kronos模块...")
try:
    from model import Kronos, KronosTokenizer, KronosPredictor as KP
    print("  [OK] 导入成功")
except Exception as e:
    print(f"  [ERROR] 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. 尝试加载Tokenizer
print("\n[4] 加载Tokenizer...")
try:
    tokenizer = KronosTokenizer.from_pretrained(tokenizer_path)
    print(f"  [OK] Tokenizer加载成功")
    print(f"  vocab_size: {len(tokenizer.tokenizer)}")
except Exception as e:
    print(f"  [ERROR] Tokenizer加载失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 尝试加载模型
print("\n[5] 加载Kronos模型...")
try:
    model = Kronos.from_pretrained(model_path)
    print(f"  [OK] 模型加载成功")
except Exception as e:
    print(f"  [ERROR] 模型加载失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("调试完成")
print("=" * 60)
