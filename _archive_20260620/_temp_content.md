# 能源贸易·矿产投融资 — GitHub 职业助力项目清单

> 整理时间：2026-06-07 | 按职业需求分类

---

## 一、量化交易框架

| 项目 | 链接 | 说明 |
|------|------|------|
| **vnpy** | https://github.com/vnpy/vnpy | 国内最主流的开源量化交易平台，支持CTP期货接口、CTA策略、套利策略、期权交易，Python开发，全中文文档 |
| **backtrader** | https://github.com/mementum/backtrader | 轻量级回测框架，适合CTA趋势策略、跨期套利策略的快速验证 |
| **zipline-reloaded** | https://github.com/stefan-jansen/zipline-reloaded | Quantopian开源回测引擎续作，适合美股/商品策略研究 |
| **qlib** | https://github.com/microsoft/qlib | 微软AI量化研究平台，因子挖掘+机器学习选股/择时，适合量化投研 |
| **rqalpha** | https://github.com/ricequant/rqalpha | 米筐科技开源回测框架，支持A股/期货，Python |

## 二、金融数据获取（Wind替代）

| 项目 | 链接 | 说明 |
|------|------|------|
| **akshare** | https://github.com/akfamily/akshare | 🥇 免费、最全面的中文金融数据接口，覆盖期货/商品/宏观/外汇/碳交易等2000+接口，无需注册 |
| **tushare** | https://github.com/waditu/tushare | 🥈 经典A股/期货数据接口（Pro版需积分），适合股票+期货数据获取 |
| **baostock** | https://github.com/baostock/baostock | 免费A股/指数数据，稳定可靠，适合历史数据批量下载 |
| **efinance** | https://github.com/Micro-sheep/efinance | 轻量级东方财富数据接口，实时行情+历史数据，无需注册 |
| **yahoo-finance2** | https://github.com/gsheni/yahoo-finance2 | 雅虎财经数据接口，适合LME铜/WTI/布伦特/美元指数等国际品种 |
| **pandas-datareader** | https://github.com/pydata/pandas-datareader | 统一数据读取接口，支持FRED/World Bank/Yahoo等宏观数据源 |

## 三、风控/尽调/法律NLP

| 项目 | 链接 | 说明 |
|------|------|------|
| **ChatLaw** | https://github.com/PKU-YuanGroup/ChatLaw | 北大法律大模型，中文合同审查+法律咨询 |
| **LaWGPT** | https://github.com/pengxiao-song/LaWGPT | 中文法律增强大模型，裁判文书理解+法律问答 |
| **LawGPT** | https://github.com/LiuHC0428/LAW-GPT | 中文法律NLP工具包+大模型，合同条款提取+风险识别 |
| **LegalNLP** | https://github.com/LiuHC0428/LegalNLP | 中文法律NLP工具包，适合合同条款提取+风险识别 |

## 四、数据加密/备份

| 项目 | 链接 | 说明 |
|------|------|------|
| **age** | https://github.com/FiloSottile/age | 现代化文件加密工具，替代GPG，简单高效 |
| **rclone** | https://github.com/rclone/rclone | 云存储同步工具，支持多云端，适合3-2-1备份策略 |
| **restic** | https://github.com/restic/restic | 加密增量备份工具，适合本地+云端双重备份 |
| **duplicacy** | https://github.com/gilbertchen/duplicacy | 跨平台加密备份，去重效率高 |

## 五、数据分析/可视化

| 项目 | 链接 | 说明 |
|------|------|------|
| **plotly** | https://github.com/plotly/plotly.py | 交互式图表库，期货K线+技术指标可视化 |
| **streamlit** | https://github.com/streamlit/streamlit | 快速搭建数据看板，投研简报+行情监控面板 |
| **dash** | https://github.com/plotly/dash | 企业级数据仪表盘，实时行情+风控监控 |
| **great_tables** | https://github.com/posit-dev/great-tables | 高质量表格输出，投研简报格式化 |

## 六、爬虫/自动化

| 项目 | 链接 | 说明 |
|------|------|------|
| **scrapy** | https://github.com/scrapy/scrapy | 工业级爬虫框架，大宗商品价格/矿权信息批量采集 |
| **playwright** | https://github.com/microsoft/playwright | 浏览器自动化，动态网站数据抓取（天眼查/裁判文书网） |
| **httpx** | https://github.com/encode/httpx | 异步HTTP客户端，高频行情数据请求 |
| **celery** | https://github.com/celery/celery | 分布式任务队列，定时爬虫+行情监控调度 |

---

## 💡 一人制公司 TOP 5 必装

1. **akshare** — 免费2000+金融数据接口，直接替代Wind
2. **vnpy** — 量化交易+CTP接口，期货CTA/套利策略直接上
3. **ChatLaw/LaWGPT** — 中文合同审查，辅助能源贸易合同风险识别
4. **restic + age** — 加密备份+文件加密，业务数据安全底线
5. **streamlit** — 零前端开发投研看板，一人搞定数据可视化

---

*注：部分小众项目链接可能随时间失效，建议在GitHub直接搜索项目名确认最新地址。akshare内置碳交易数据接口，可覆盖CCER行情获取需求。*
