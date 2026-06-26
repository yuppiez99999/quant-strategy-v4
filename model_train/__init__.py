# -*- coding: utf-8 -*-
"""model_train — 量化策略模型训练与增强信号模块

三个核心模块:
  - xgboost_direction: AKShare数据拉取 + XGBoost 5日涨跌分类器
  - risk_parity_backtest: 风险平价模型 vs 现有组合回测对比
  - finbert_sentiment: FinBERT中文情感标注 → 信号合成

用法:
  python -m model_train.xgboost_direction   # 训练+输出信号
  python -m model_train.risk_parity_backtest # 回测+对比报告
  python -m model_train.finbert_sentiment    # 批量情感标注
"""
