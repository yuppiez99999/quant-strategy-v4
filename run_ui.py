# -*- coding: utf-8 -*-
"""量化策略系统 v5.2 — Streamlit UI 启动脚本"""
import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_ENTRY = os.path.join(BASE_DIR, "ui", "app.py")

print("=" * 60)
print("  量化策略系统 v5.2 — Streamlit 可视化面板")
print("=" * 60)
print(f"  入口: {UI_ENTRY}")
print(f"  地址: http://localhost:8501")
print("=" * 60)

# 优先使用安装了 streamlit 的 Python
python_exe = os.environ.get("STREAMLIT_PYTHON", sys.executable)
streamlit_paths = [
    r"C:\Program Files\Python38\python.exe",
    r"C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe",
]
for sp in streamlit_paths:
    if os.path.exists(sp):
        python_exe = sp
        break

result = subprocess.run(
    [python_exe, "-m", "streamlit", "run", UI_ENTRY, "--server.port", "8501"],
    cwd=BASE_DIR,
)
