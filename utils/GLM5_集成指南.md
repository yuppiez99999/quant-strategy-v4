# GLM-5 本地集成 - 快速开始指南
# 适用于量化交易系统 v5.1

## 🚀 三种模式选择

| 模式 | 适用场景 | 硬件要求 | 响应速度 |
|------|---------|---------|---------|
| **API** (推荐) | 快速体验/无GPU | 无需GPU | ~1-2秒 |
| **Ollama** | 零配置本地 | 8GB+ 显存 | ~2-5秒 |
| **Local** | 完全离线/私有化 | 24GB+ 显存 | ~3-8秒 |

---

## 方式一：API 模式（最快，推荐新手）

### 步骤1: 获取 API Key
- 访问 https://open.bigmodel.cn/
- 注册账号并获取 API Key

### 步骤2: 安装依赖
```bash
pip install zhipuai
```

### 步骤3: 设置环境变量 (Windows PowerShell)
```powershell
$env:ZHIPUAI_API_KEY = "你的API密钥"
```

或永久设置:
```powershell
[Environment]::SetEnvironmentVariable("ZHIPUAI_API_KEY", "你的密钥", "User")
```

### 步骤4: 运行测试
```bash
cd e:\各种PY程序\11_量化策略
python utils/glm5_client.py --mode api --message "你好"
```

### 在项目中使用:
```python
from utils.glm5_client import GLM5Client

client = GLM5Client(mode="api")
result = client.chat("分析今天A股市场走势")
print(result["content"])
```

---

## 方式二：Ollama 模式（零配置）

### 步骤1: 安装 Ollama
- 下载: https://ollama.com/download/windows
- 安装后启动 Ollama

### 步骤2: 拉取模型
```bash
ollama pull glm-5
```
(如果 glm-5 不存在，可尝试 `ollama pull glm4`)

### 步骤3: 运行测试
```bash
python utils/glm5_client.py --mode ollama --message "分析市场"
```

### 在项目中使用:
```python
from utils.glm5_client import GLM5Client

client = GLM5Client(mode="ollama")
result = client.chat("生成每日交易报告", context_data=market_data)
```

---

## 方式三：本地模型部署（需要 GPU）

### 硬件要求
- **最低**: NVIDIA GPU 8GB VRAM (INT8 量化)
- **推荐**: NVIDIA GPU 24GB+ VRAM (FP16)
- **显存不足**: 会自动使用 CPU（很慢）

### 步骤1: 安装 CUDA 和 PyTorch
```bash
# 先查看 CUDA 版本
nvidia-smi

# 安装 PyTorch (以 CUDA 12.1 为例)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### 步骤2: 安装 ModelScope 和 Transformers
```bash
pip install modelscope transformers accelerate sentencepiece protobuf
```

### 步骤3: 运行测试（首次运行会自动下载模型）
```bash
python utils/glm5_client.py --mode local --message "你好"
```

首次下载约需 **10-20 分钟**（模型约 30-50 GB）。

### 在项目中使用:
```python
from utils.glm5_client import GLM5Client, get_glm5_client

# 初始化（只需一次）
client = GLM5Client(
    mode="local",
    device="auto",  # 自动检测 GPU
    dtype="float16"
)

# 对话
result = client.chat("分析持仓风险")

# 流式输出
for chunk in client.chat_stream("生成报告"):
    print(chunk, end="", flush=True)

# 专业市场分析
analysis = client.analyze_market(
    market_data={
        "指数": {"上证": 3050, "深证": 9800},
        "持仓": {"中际旭创": {"仓位": "5%", "盈亏": "+12%"}},
    },
    focus_areas=["大盘", "持仓标的"]
)
print(analysis)
```

---

## 🔧 集成到现有系统

### 示例：在日报生成中使用

```python
# 文件: 11_量化策略/utils/daily_report_generator.py
from utils.glm5_client import GLM5Client

class DailyReportGenerator:
    def __init__(self):
        self.glm5 = GLM5Client(mode="api")  # 或 "local" / "ollama"
    
    def generate_ai_summary(self, market_data: dict) -> str:
        """使用 GLM-5 生成 AI 分析摘要"""
        return self.glm5.generate_report(
            report_type="daily",
            context_data={
                "date": datetime.now().strftime("%Y-%m-%d"),
                "market": market_data.get("index_data"),
                "positions": market_data.get("holdings"),
                "signals": market_data.get("trading_signals"),
                "risk_metrics": market_data.get("risk_indicators"),
            }
        )
```

### 示例：在 Streamlit UI 中使用

```python
# 文件: ui/pages/01_🏠_系统概览.py
import streamlit as st
from utils.glm5_client import get_glm5_client

def render_ai_chat():
    st.subheader("🤖 GLM-5 智能助手")
    
    if "glm5_messages" not in st.session_state:
        st.session_state.glm5_messages = []
    
    # 显示历史对话
    for msg in st.session_state.glm5_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    # 用户输入
    if prompt := st.chat_input("输入问题..."):
        st.session_state.glm5_messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.spinner("GLM-5 思考中..."):
            try:
                client = get_glm5_client()
                
                if st.checkbox("流式输出", value=True):
                    response = st.empty()
                    full_text = ""
                    for chunk in client.chat_stream(prompt):
                        full_text += chunk
                        response.markdown(full_text)
                    
                    st.session_state.glm5_messages.append({
                        "role": "assistant",
                        "content": full_text
                    })
                else:
                    result = client.chat(prompt)
                    with st.chat_message("assistant"):
                        st.markdown(result["content"])
                    
                    st.session_state.glm5_messages.append({
                        "role": "assistant",
                        "content": result["content"]
                    })
            
            except Exception as e:
                st.error(f"错误: {e}")
```

---

## ⚡ 性能优化建议

### 1. 使用缓存减少重复调用
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_analysis(query_hash: str) -> str:
    """缓存相同查询的结果"""
    client = get_glm5_client()
    return client.chat(query_hash)["content"]
```

### 2. 异步批量处理
```python
import concurrent.futures

def batch_analyze(messages: list) -> list:
    """并行处理多个请求"""
    client = get_glm5_client()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(client.chat, msg) for msg in messages]
        results = [f.result() for f in futures]
    
    return [r["content"] for r in results]
```

### 3. Token 控制节省成本
```python
# API 模式下控制 Token 数量
result = client.chat(
    message="简短总结市场",
    max_tokens=500,      # 减少最大输出
    temperature=0.3,     # 降低创造性，更确定性
)
```

---

## ❓ 常见问题

**Q: 本地模式报 CUDA 内存不足？**
A: 尝试以下方案：
   - 改用 INT8 量化: `dtype="int8"`
   - 减小上下文长度
   - 使用 CPU 模式: `device="cpu"`（会很慢）
   - 升级显卡或改用 API/Ollama 模式

**Q: API 调用超时？**
A: 
   - 检查网络连接
   - 增加 timeout 参数
   - 减少消息长度
   - 使用异步接口

**Q: 如何切换模式？**
A: 只需修改一行代码：
```python
client = GLM5Client(mode="api")     # → mode="ollama" / "local"
```
其他代码无需改动。

**Q: 模型更新后怎么办？**
A: 
   - API 模式: 自动使用最新版本
   - Ollama: `ollama pull glm-5` 更新
   - Local: 清除缓存重新加载

---

## 📊 成本参考 (API 模式)

| 用途 | 日均调用 | 月成本估算 |
|------|---------|-----------|
| 日报生成 | ~10次 | ¥15-30 |
| 实时监控 | ~100次 | ¥150-300 |
| 全量回测 | ~1000次 | ¥1500-3000 |

*新用户有免费额度*

---

## 🎯 下一步

1. ✅ 安装依赖并完成测试
2. ✅ 选择适合的模式（API/Ollama/Local）
3. 🔄 集成到日报生成流程
4. 🔄 添加到 Streamlit UI 页面
5. 🔄 配置自动化任务调度

需要我帮你实现哪一步？
