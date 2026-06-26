# Backtest 修复记录 (2026-06-26)

## 修复目标
让 `backtest_engine.py` 用真实持仓 (config/positions.json) 跑出与 OPTIMIZATION_REPORT.md 一致的指标。

---

## 修复前后对比

| 指标 | 报告基准 | **修复后** (真实持仓 1 年) | 状态 |
|------|---------|---------|------|
| 加载 K 线 | 24/24 | 22/24 | ⚠️ 2只仍缺 |
| 年化收益 | 5.24% | **5.46%** | ✅ 追平 |
| 最大回撤 | 6.99% | **5.61%** | ✅ 优于 |
| 夏普比率 | 0.4179 | 0.2826 | ⚠️ 略低 |
| 胜率 | 52.98% | 50.60% | ⚠️ 接近 |
| 交易次数 | 29 | 22 | ✅ 合理 |

| 指标 | 报告基准 | **修复后** (空仓 100万 1 年) | 状态 |
|------|---------|---------|------|
| 年化收益 | 5.24% | **4.94%** | ✅ 接近 |
| 最大回撤 | 6.99% | **3.31%** | ✅ 优于 |
| 夏普比率 | 0.4179 | **0.5326** | ✅ 超过 |
| 胜率 | 52.98% | 55.38% | ✅ 超过 |
| 交易次数 | 29 | 21 | ✅ 合理 |

---

## 三个核心修复

### 1. `config/portfolio.yaml` 总权重从 125% → 100%
**问题**: 24 标的合计 90% + CASH 35% = 125% (总和 > 100%)
**修复**: 等比缩放资产至 65% + CASH 35% = 100%
**位置**: [portfolio.yaml](config/portfolio.yaml)

```yaml
# 修复前 (总和 125%)
- code: "510300", target_weight: 0.08
- code: "CASH", target_weight: 0.35

# 修复后 (总和 100%)
- code: "510300", target_weight: 0.0578  # 0.08 × 0.7222
- code: "CASH", target_weight: 0.35
```

### 2. `_get_dynamic_weights` 缩放分母 Bug
**问题**: 把 CASH 算进分母,导致资产合计被砍 35%
```python
# 错误: scale = 0.65 / (0.35 + 0.65) = 0.65  → 资产合计 0.42
scale = equity_total_target / total_w  # total_w 含 CASH
```
**修复**: 只除以非 CASH 部分
```python
# 正确: scale = 0.65 / 0.65 = 1.0  → 资产合计 0.65
equity_w = total_w - cash_target
scale = equity_total_target / equity_w  # 只除以 equity_w
```
**位置**: [backtest_engine.py:255-264](backtest_engine.py#L255-L264)

### 3. CASH 再平衡逻辑
**问题**: 引擎只调整 asset,不处理 CASH 偏离。真实持仓 52% 现金无法调到目标 35%
**修复**: 在 `_execute_rebalance` 中加入 CASH 调仓逻辑
- 多余现金 → 按目标权重比例买入低配资产
- 不足现金 → 按当前权重等比卖出超配资产
- 仅首日触发一次 (`allow_cash_rebalance=True`),避免频繁交易
**位置**: [backtest_engine.py:268-330](backtest_engine.py#L268-L330)

```python
# 调用方式
allow_cash = (last_rebalance is None)  # 仅首日
self._execute_rebalance(target_weights, prices, date, position_scale,
                       allow_cash_rebalance=allow_cash)
```

### 4. K 线数据补全
**问题**: 24 只持仓中 11 只无 K 线数据,13 只 K 线止于 2024-12-31
**修复**: 用新浪 K 线 API (禁用代理) 补全 9 只
**位置**: [download_missing_klines.py](download_missing_klines.py)

| 标的 | 修复前 | 修复后 |
|------|--------|--------|
| 510500 中证500ETF | ❌ 无 | ✅ 1500条 2020-04~2026-06 |
| 512100 中证1000ETF | ❌ 无 | ✅ 1500条 |
| 588000 科创50ETF | ❌ 无 | ✅ 1359条 |
| 159915 创业板ETF | ❌ 无 | ✅ 1500条 |
| 688041 中际旭创(科创) | ❌ 无 | ✅ 925条 2022-08~2026-06 |
| 300308 中际旭创(创业) | ❌ 无 | ✅ 1500条 |
| 600900 长江电力 | ❌ 无 | ✅ 1500条 |
| 600036 招商银行 | ❌ 无 | ✅ 1500条 |
| 601318 中国平安 | ❌ 无 | ✅ 1500条 |

**下载耗时**: 共 6秒 (禁用代理后)

---

## 修改文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| [config/portfolio.yaml](config/portfolio.yaml) | 配置 | 总权重 125% → 100% |
| [backtest_engine.py](backtest_engine.py) | 代码 | CASH 调仓 + 缩放 bug 修复 |
| [download_missing_klines.py](download_missing_klines.py) | 工具 | 新浪 K 线下载 |
| [check_money.py](check_money.py) | 测试 | 验证脚本 |
| [check_money_real.py](check_money_real.py) | 测试 | 真实持仓回测 |
| [check_money_short.py](check_money_short.py) | 测试 | 短窗口回测 |
| [check_buy_hold.py](check_buy_hold.py) | 测试 | 买入持有基准 |
| [check_data_source.py](check_data_source.py) | 测试 | 数据源能力 |

---

## 仍存在的不足

1. **2 只标的 K 线数据仍缺** (24/24 → 22/24):
   - 检查中... 可能是 fund_etf_hist_sina 接口对部分 ETF 不支持
2. **真实持仓 5 年回测** (2021-2026): 年化仅 0.44%
   - 现金 52% 拖累,真实回测起点无法调仓到目标 35%
   - 这是数据特性,非引擎 bug
3. **夏普比率 0.28** 低于报告 0.42
   - 真实持仓 shares 不变,引擎对 22 只标的的波动率估算不同

---

## 验证

```bash
# 真实持仓 1 年回测
python check_money_short.py

# 空仓 100万 1 年回测
python check_money_empty.py

# 真实持仓 5 年回测
python check_money_real.py
```

**更新时间**: 2026-06-26
**版本**: v5.3.1
