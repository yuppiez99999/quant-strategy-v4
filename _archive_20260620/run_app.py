import subprocess
import sys

result = subprocess.run([
    "C:\\Program Files\\Python38\\python.exe", "-m", "streamlit", "run", "量化监控面板.py"
], capture_output=True, text=True, cwd="e:\\各种PY程序\\11_量化策略", timeout=30)

print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)