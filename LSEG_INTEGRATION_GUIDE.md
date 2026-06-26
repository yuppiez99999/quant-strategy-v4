# LSEG MCP 连接器集成指南

## 📋 概述

本指南说明如何将 **LSEG Financial Analytics** 集成到量化策略系统 v5.0 中，作为第三级数据源。

### 数据源优先级架构

```
Wind MCP (优先级1) 
    ↓ 失败
iFinD MCP (优先级2) 
    ↓ 失败
LSEG MCP (优先级3) ⭐ 新增
    ↓ 失败
免费数据源 (优先级4-6)
```

---

## 🚀 快速开始

### 1. 安装 Claude Code 插件

```bash
cd "e:\各种PY程序\financial-services"

# 添加市场（已完成）
claude plugin marketplace add anthropics/financial-services

# 安装核心技能（已完成）
claude plugin install financial-analysis@claude-for-financial-services
```

### 2. 配置 LSEG API Key

#### 方式A: 环境变量（推荐）

在 Windows PowerShell 中：
```powershell
$env:LSEG_API_KEY = "your-lseg-api-key-here"
```

或在系统环境变量中永久设置：
1. 右键"此电脑" → 属性 → 高级系统设置
2. 环境变量 → 新建系统变量
   - 变量名: `LSEG_API_KEY`
   - 变量值: `your-api-key`

#### 方式B: 代码中直接设置

```python
import os
os.environ['LSEG_API_KEY'] = 'your-api-key-here'
```

### 3. 测试连接

```bash
cd "e:\各种PY程序\11_量化策略"
python lseg_integration.py
```

预期输出：
```
============================================================
Testing LSEG MCP Integration
============================================================

🔍 Testing LSEG MCP Server connection...
✅ Connection successful!

📊 Testing equity research (AAPL)...
✓ Retrieved AAPL data
  Price: $XXX.XX

🌍 Testing macro dashboard (US)...
✓ Retrieved US macro data

✅ All tests passed!
```

---

## 📊 功能列表

### 1. 股票研究 (Equity Research)

```python
from lseg_mcp_connector import create_lseg_connector

connector = create_lseg_connector()

# 获取股票研究报告
equity_data = connector.get_equity_research("AAPL", exchange="US")
# 返回: 共识预测、基本面数据、价格表现、估值指标

# 获取公司基本面
fundamentals = connector.get_company_fundamentals("MSFT")
# 返回: 营收、利润、现金流、资产负债表

# 获取分析师共识
consensus = connector.get_consensus_estimates("GOOGL")
# 返回: EPS预测、收入预测、推荐趋势
```

### 2. 债券分析 (Bond Analysis)

```python
# 获取债券定价
bond_data = connector.get_bond_pricing("US912828ZT09")
# 返回: 价格、收益率、久期、利差

# 获取收益率曲线
yield_curve = connector.get_yield_curve(currency="USD", tenor="10Y")
# 返回: 国债收益率、互换利率、利差曲线
```

### 3. FX 汇率分析

```python
# 获取汇率
fx_rates = connector.get_fx_rates("EURUSD")
# 返回: 即期汇率、远期点数、掉期利率

# FX 套利分析
carry_analysis = connector.get_fx_carry_analysis("GBPJPY")
# 返回: 套利波动比、历史背景、交易信号
```

### 4. 期权波动率

```python
# 获取期权波动率曲面
vol_data = connector.get_option_volatility("SPY", expiry="2026-12-18")
# 返回: 隐含波动率曲面、希腊字母、SABR参数
```

### 5. 宏观指标

```python
# 获取宏观仪表板
macro_dashboard = connector.get_macro_dashboard(country="US")
# 返回: GDP、通胀、失业、政策利率、收益率曲线

# 获取特定经济指标
gdp_data = connector.get_economic_indicators("GDP", country="CN")
# 返回: 历史时间序列数据
```

### 6. 历史价格

```python
# 获取历史价格
historical_prices = connector.get_historical_prices(
    ticker="AAPL",
    start_date="2026-01-01",
    end_date="2026-06-07",
    frequency="daily"
)
# 返回: OHLCV 时间序列
```

---

## 🔧 集成到量化策略系统

### 自动注册（推荐）

在主程序中调用：

```python
from lseg_integration import register_lseg_connector

# 在 connector_manager 初始化后
connector_manager = DataConnectorManager()

# 注册 LSEG 连接器
register_lseg_connector(connector_manager)
```

### 手动注册

```python
from lseg_mcp_connector import create_lseg_connector
from 量化策略系统_v5_0 import DataConnector

class LSEGDataConnector(DataConnector):
    def __init__(self, lseg_connector):
        super().__init__(name="LSEG MCP", priority=3)
        self.lseg = lseg_connector
    
    def connect(self):
        return self.lseg.test_connection()
    
    def get_quote(self, code):
        result = self.lseg.get_equity_research(code)
        if result:
            return {
                'price': result.get('price', 0),
                'change_pct': result.get('change_pct', 0),
            }
        return None

# 创建并注册
lseg_conn = create_lseg_connector()
lseg_data_connector = LSEGDataConnector(lseg_conn)
connector_manager.register_connector(lseg_data_connector)
```

---

## 📁 文件结构

```
11_量化策略/
├── lseg_mcp_connector.py      # LSEG MCP 连接器核心实现
├── lseg_integration.py         # 集成辅助模块
├── LSEG_INTEGRATION_GUIDE.md   # 本指南
└── 量化策略系统 v5.0.py        # 主程序（可选集成）
```

---

## ⚙️ 配置选项

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LSEG_API_KEY` | LSEG API 认证密钥 | 无 |
| `LSEG_BASE_URL` | LSEG MCP Server URL | `https://api.analytics.lseg.com/lfa/mcp` |

### 连接器参数

```python
connector = LSEGMCPConnector(
    base_url="https://api.analytics.lseg.com/lfa/mcp",
    api_key="your-api-key"
)
```

---

## 🐛 故障排除

### 问题1: 连接失败

**症状**: `Connection failed` 或 `Timeout`

**解决方案**:
1. 检查网络连接
2. 验证 API Key 是否正确
3. 确认 LSEG MCP Server 可访问
4. 检查防火墙设置

```python
# 测试连接
connector = create_lseg_connector()
if connector.test_connection():
    print("✅ Connected")
else:
    print("❌ Connection failed")
```

### 问题2: API 返回空数据

**症状**: `get_equity_research()` 返回 `None`

**解决方案**:
1. 检查股票代码格式（如 "AAPL" vs "AAPL.US"）
2. 确认有该数据的产品权限
3. 查看日志中的详细错误信息

### 问题3: 导入错误

**症状**: `ModuleNotFoundError: No module named 'lseg_mcp_connector'`

**解决方案**:
```bash
# 确保在正确的目录
cd "e:\各种PY程序\11_量化策略"

# 检查文件是否存在
dir lseg_mcp_connector.py
```

---

## 📈 使用示例

### 示例1: 康波周期监控增强

```python
from lseg_mcp_connector import create_lseg_connector

connector = create_lseg_connector()

# 获取黄金价格（替代 yfinance）
gold_data = connector.get_historical_prices("GC=F", days=30)

# 获取铜价格
copper_data = connector.get_historical_prices("HG=F", days=30)

# 获取宏观指标
us_macro = connector.get_macro_dashboard("US")
cn_macro = connector.get_macro_dashboard("CN")
```

### 示例2: 投资组合优化增强

```python
# 获取多只股票的基本面数据
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN"]

fundamentals = {}
for ticker in tickers:
    data = connector.get_company_fundamentals(ticker)
    if data:
        fundamentals[ticker] = {
            'pe_ratio': data.get('pe_ratio'),
            'pb_ratio': data.get('pb_ratio'),
            'roe': data.get('roe'),
            'debt_to_equity': data.get('debt_to_equity'),
        }

# 用于因子配比优化
print(fundamentals)
```

### 示例3: 大宗商品基本面分析

```python
# 获取债券收益率曲线（用于利率敏感性分析）
us_yield = connector.get_yield_curve("USD", "10Y")
cn_yield = connector.get_yield_curve("CNY", "10Y")

# 获取 FX 汇率（用于进口成本分析）
usdcny = connector.get_fx_rates("USDCNY")

print(f"USD/CNY: {usdcny}")
```

---

## 🔐 安全注意事项

1. **API Key 保护**
   - 不要将 API Key 硬编码在代码中
   - 使用环境变量或密钥管理服务
   - 不要将包含 API Key 的文件提交到 Git

2. **速率限制**
   - LSEG API 可能有请求频率限制
   - 实施缓存机制避免重复请求
   - 监控 API 使用情况

3. **数据权限**
   - 确保您的订阅包含所需的数据产品
   - 某些高级功能可能需要额外授权

---

## 📞 支持

- **LSEG 官方文档**: https://developers.lseg.com
- **Claude Financial Services**: https://github.com/anthropics/financial-services
- **项目问题**: 在 GitHub 仓库提交 Issue

---

## 📝 更新日志

### v1.0 (2026-06-07)
- ✅ 初始版本发布
- ✅ 支持股票研究、债券、FX、期权、宏观指标
- ✅ 自动回退机制集成
- ✅ 完整文档和示例

---

**最后更新**: 2026-06-07  
**版本**: 1.0
