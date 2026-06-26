# 研究计划: 基于 YiZhao-FinDataSet 优化量化策略系统

## 一、YiZhao 数据集能力分析

YiZhao-FinDataSet 是哈工大(深圳)与招商银行AI实验室联合发布的 2TB 金融语料库：
- 936GB 中文金融文本 (jsonl格式，单文件≤7GB)
- 100GB 英文金融文本
- 1TB 多模态数据

数据覆盖: 金融事件、市场动态、金融产品、交易模式、信用评分、风险管理、欺诈检测、投资组合优化

每条数据包含:
- meta: id/url/title/source_domain/fin_int_score(金融相关性1-5)/risk_score/language/images
- text: 文本正文
- qa: 基于文本生成的QA对列表

## 二、当前系统问题诊断

1. **AI分析模块(daily_report.py)** 使用硬编码模拟新闻(_get_mock_news)，未接真实金融语料
2. **估值分析器** 使用 hash(code) 生成伪历史均价，无实际基本面数据
3. **策略信号** 仅依赖双均线+固定权重，缺乏情绪/事件驱动因子
4. **回测引擎** 无多因子模型，无法验证新因子有效性
5. **风控模块** 仅依赖价格回撤，缺乏舆情/事件预警
6. **宏观分析** 康波周期硬编码，十五五规划关键词过于粗粒度

## 三、优化方案

### 模块1: YiZhao 数据下载与预处理 (yizhao_data_loader.py)
- 安装 modelscope SDK
- 下载中文金融文本子集(精选5-10GB高质量样本)
- 建立本地索引(按fin_int_score筛选、按source_domain分类)
- 构建金融词典和情感词典

### 模块2: 金融文本语义分析引擎 (fin_sentiment_analyzer.py)
- 基于YiZhao文本构建金融情感分析模块
- 提取实体(公司/行业/政策)与情感极性
- 生成日度市场情绪指标

### 模块3: 事件驱动因子 (event_driven_factor.py)
- 从YiZhao提取: 政策事件、公司公告、行业动态、风险事件
- 构建事件冲击量化模型
- 集成到回测引擎做因子验证

### 模块4: 增强AI分析 (ai_analysis_enhanced.py)
- 替换 _get_mock_news 为真实YiZhao语料检索
- 使用QA对数据增强政策/估值分析
- 增加行业对比分析维度

### 模块5: 多因子信号生成器 (multi_factor_signal.py) ✅ 已实现
- 新增因子: 舆情情绪因子、事件冲击因子、文本热度因子
- 与现有双均线因子融合 (dual_ma + MACD + RSI)
- 因子权重通过回测优化 (网格搜索 + IC最大化)
- 综合信号: strong_buy/buy/hold/sell/strong_sell
- 实现文件: `multi_factor_signal.py` (2026-06-26)

### 模块6: 增强风控 (risk_early_warning.py) ✅ 已实现
- 舆情预警: 负面新闻密度检测 (时间加权)
- 事件预警: 重大风险事件识别 (3级严重度: critical/high/medium)
- 行业联动预警: 跨标的负面情绪传导 + 行业传染系数
- 综合风险评估: 融合多维度评分 + 行动建议
- 实现文件: `risk_early_warning.py` (2026-06-26)
- 向后兼容: `ai_analysis_enhanced.py` 中的 `PortfolioRiskEarlyWarning` 自动升级

## 四、实施优先级

P0: yizhao_data_loader.py ✅ (数据基础)
P1: fin_sentiment_analyzer.py ✅ (核心分析能力)
P2: ai_analysis_enhanced.py ✅ (替换硬编码)
P3: multi_factor_signal.py ✅ (策略增强)
P4: event_driven_factor.py ✅ + risk_early_warning.py ✅ (风控增强)
