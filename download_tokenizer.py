"""
从HuggingFace下载Kronos Tokenizer
"""
import os
from huggingface_hub import snapshot_download

model_dir = r'e:\各种PY程序\11_量化策略\models'
os.makedirs(model_dir, exist_ok=True)

print("开始下载 Kronos Tokenizer...")
tokenizer_path = snapshot_download(
    repo_id="NeoQuasar/Kronos-Tokenizer-base",
    local_dir=os.path.join(model_dir, "NeoQuasar/Kronos-Tokenizer-base"),
    local_dir_use_symlinks=False
)
print("[OK] Tokenizer已保存到:", tokenizer_path)
