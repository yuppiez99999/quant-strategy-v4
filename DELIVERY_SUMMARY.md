# 职业投资训练模型系统 - 交付总结

> 创建日期: 2026-06-17  
> 需求编号: 1770371634132965  
> 项目路径: `E:\各种PY程序\11_量化策略\`

---

## 📦 已创建的文件

| 文件 | 说明 | 用途 |
|------|------|------|
| **career_investor_lite.py** | 精简版训练模型（可运行） | 演示和日常使用 |
| **career_investor_model.py** | 完整版训练模型（需依赖） | 生产环境使用 |
| **quick_start.py** | 交互式启动脚本 | 菜单选择模式 |
| **run_analysis.py** | 一键运行脚本 | 直接生成报告 |
| **CAREER_INVESTOR_GUIDE.md** | 详细使用指南 | 学习文档 |
| **investment_report.json** | 分析报告（自动生成） | 结果保存 |

---

## 🚀 快速使用

### 方式一：一键生成报告（推荐）

```bash
cd "E:\各种PY程序\11_量化策略"
python run_analysis.py
```

### 方式二：交互式选择

```bash
python quick_start.py
```

### 方式三：命令行模式

```bash
# 完整分析
python career_investor_model.py --mode full

# 仅持仓分析
python career_investor_model.py --mode portfolio

# 风险评估
python career_investor_model.py --mode risk

# 策略回测
python career_investor_model.py --mode backtest

# 收益预测
python career_investor_model.py --mode predict
```

---

## 📊 系统功能

### 1. 持仓组合分析
- ✅ 支持20只标的（12只股票 + 6只ETF + 黄金ETF + 现金）
- ✅ 实时获取行情（Wind MCP / iFinD / AKShare）
- ✅ 权重分布统计
- ✅ 涨跌情况监控

### 2. 风险评估
- ✅ VaR (95%) 计算
- ✅ 最大回撤监控
- ✅ 波动率分析
- ✅ 风险等级判断（LOW/MEDIUM/HIGH）
- ✅ 自动建议操作

### 3. 交易信号生成
- ✅ 多因子信号（技术面 + 资金流 + 事件驱动）
- ✅ 买卖建议（BUY/SELL/HOLD）
- ✅ 信号强度评分（0-1）
- ✅ 信号统计汇总

### 4. 策略回测
- ✅ 5-10年历史数据回测
- ✅ 年化收益率计算
- ✅ 夏普比率评估
- ✅ 胜率统计
- ✅ 交易次数统计

### 5. 收益预测（蒙特卡洛）
- ✅ 10,000次模拟
- ✅ 5-10年期预测
- ✅ 概率分布分析
- ✅ 悲观/中位数/乐观情景

---

## 📈 当前持仓配置

| 类别 | 标的 | 代码 | 权重 |
|------|------|------|------|
| **宽基ETF** | 沪深300ETF | 510300 | 6.21% |
| | 中证500ETF | 510500 | 4.59% |
| | 中证1000ETF | 512100 | 3.24% |
| | 科创50ETF | 588000 | 4.23% |
| | 创业板ETF | 159915 | 5.31% |
| | 黄金ETF | 518880 | 5.40% |
| **数字经济** | 中际旭创 | 300308 | 4.23% |
| | 海光信息 | 688041 | 4.68% |
| | 阳光电源 | 300274 | 8.19% |
| | 北方华创 | 002371 | 1.62% |
| **防御红利** | 中国神华 | 601088 | 5.13% |
| | 恒瑞医药 | 600276 | 4.41% |
| | 中国中免 | 601888 | 6.12% |
| **康波周期** | 宝丰能源 | 600989 | 1.26% |
| | 东方电气 | 600875 | 3.96% |
| | 特变电工 | 600089 | 8.19% |
| | 南网储能 | 600995 | 1.26% |
| | 徐工机械 | 000425 | 3.06% |
| | 绿的谐波 | 688017 | 3.96% |
| **电网核心** | 国电南瑞 | 600406 | 4.95% |
| **现金储备** | 现金 | CASH | 10.00% |

**配置逻辑：**
- 29.97% 宽基ETF + 黄金（风险缓冲）
- 22.72% 数字经济/AI/半导体（成长引擎）
- 15.66% 防御红利（稳定收益）
- 22.05% 康波周期能源/基建（周期博弈）
- 4.95% 电网核心（确定性高）
- 10.00% 现金（机动仓位）

---

## 🎯 使用场景

### 每日晨间检查（9:00）

```bash
python run_analysis.py
```

**查看内容：**
- 持仓标的实时行情
- 涨跌情况
- 权重变化

### 周度策略回测（周五收盘后）

```bash
python career_investor_model.py --mode backtest
```

**查看内容：**
- 本周策略表现
- 夏普比率
- 胜率

### 月度风险评估（月初）

```bash
python career_investor_model.py --mode risk
```

**查看内容：**
- VaR计算
- 最大回撤
- 风险控制建议

### 年度收益预测（年初）

```bash
python career_investor_model.py --mode predict
```

**查看内容：**
- 5-10年期收益预测
- 概率分布
- 悲观/乐观情景

---

## 📚 数据源配置

### Wind MCP（推荐，数据最准）

**无需配置**，系统自动检测并使用

### iFinD（备选）

```bash
export IFIND_TOKEN="your_token"
```

### AKShare（免费兜底）

```bash
pip install akshare
```

### 新浪财经（实时兜底）

**自动检测**，无需配置

---

## 🔧 进阶使用

### 自定义持仓权重

编辑 `config/portfolio.yaml`：

```yaml
assets:
  - code: "510300"
    name: 沪深300ETF
    target_weight: 0.08  # 调整为8%
```

### 添加新标的

```yaml
- code: "600519"
  name: 贵州茅台
  target_weight: 0.05  # 5%权重
```

### 自动化定时任务

**Windows任务计划程序：**

```powershell
schtasks /create /tn "CareerInvestor_Morning" /tr "python E:\各种PY程序\11_量化策略\run_analysis.py" /sc daily /st 09:00
```

**Linux cron：**

```bash
0 9 * * * cd /path/to/11_量化策略 && python run_analysis.py >> logs/morning.log 2>&1
```

---

## 📖 详细文档

完整使用指南请查看：  
`E:\各种PY程序\11_量化策略\CAREER_INVESTOR_GUIDE.md`

---

## ✅ 系统已验证

- ✅ 精简版可在Windows Python 3.x直接运行
- ✅ 无需外部数据源（使用模拟数据演示）
- ✅ 支持Wind MCP获取真实数据
- ✅ 支持AKShare免费数据兜底
- ✅ 完整分析流程已测试通过

---

## 🎓 学习路径

1. **入门**：运行 `run_analysis.py` 查看完整报告
2. **理解**：阅读 `CAREER_INVESTOR_GUIDE.md` 了解各模块功能
3. **实践**：修改 `config/portfolio.yaml` 调整持仓配置
4. **进阶**：研究 `career_investor_model.py` 源码，自定义策略
5. **精通**：结合Wind MCP获取真实数据，进行实盘分析

---

## 💡 核心价值

这套系统整合了你项目中**所有成熟的金融工具和策略**：

- ✅ 11_量化策略/ - 核心量化策略系统
- ✅ 14.quantitative_trading_system/ - 结构化量化交易
- ✅ 10_第三方项目/auto_trading_system/ - 全自动交易系统
- ✅ Wind MCP - 专业金融数据源
- ✅ 康波周期理论 - 宏观择时
- ✅ 十五五规划 - 政策导向投资

**为你打造一个机构级的个人投资分析平台！**
