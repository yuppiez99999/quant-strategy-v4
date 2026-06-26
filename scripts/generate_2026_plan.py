# -*- coding: utf-8 -*-
"""2026年度交易计划汇总报告生成器
整合: 康波周期 + 十五五规划 + 社保基金ETF追踪 + ETF资金流信号
"""
import sys, os, json
from datetime import datetime

sys.path.insert(0, '.')

try:
    import yaml
except ImportError:
    yaml = None

from bootstrap import logger, BASE_DIR
from engine.etf_flow import ETFRealTimeTracker, NATIONAL_TEAM_ETFS, YEARLY_STOCK_POOL
from engine.social_security import (
    SocialSecurityStyleTracker, STYLE_DEFINITIONS, run_tracking_summary,
)

today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
PLAN_START_DATE = '2026-06-15'
PLAN_END_DATE = '2026-12-31'
PLAN_TOTAL_CAPITAL = 2_000_000.0
PLAN_CASH_WEIGHT = 0.10
PLAN_INVESTABLE_CAPITAL = PLAN_TOTAL_CAPITAL * (1 - PLAN_CASH_WEIGHT)
print(f"生成时间: {today}")
print(f"工作目录: {BASE_DIR}")

# ========== 1. 读取配置 ==========
portfolio_path = os.path.join(BASE_DIR, 'config', 'portfolio.yaml')
positions_path = os.path.join(BASE_DIR, 'config', 'positions.json')
sl_path = os.path.join(BASE_DIR, 'config', 'stop_loss_rules_auto.yaml')

portfolio = {}
positions = {}
sl_rules = {}

if os.path.exists(portfolio_path) and yaml:
    with open(portfolio_path, 'r', encoding='utf-8') as f:
        portfolio = yaml.safe_load(f) or {}
    print(f"✅ 已加载 portfolio.yaml")

if os.path.exists(positions_path):
    with open(positions_path, 'r', encoding='utf-8') as f:
        positions = json.load(f)
    print(f"✅ 已加载 positions.json")

if os.path.exists(sl_path) and yaml:
    with open(sl_path, 'r', encoding='utf-8') as f:
        sl_rules = yaml.safe_load(f) or {}
    print(f"✅ 已加载 stop_loss_rules_auto.yaml")

# ========== 2. 运行 ETF 资金流分析 ==========
print("\n[步骤 1/3] 运行 ETF 资金流分析 ...")
etf_tracker = ETFRealTimeTracker()
flows = etf_tracker.analyze_fund_flow()
signals = etf_tracker.detect_signals(flows)

# ========== 3. 运行社保风格追踪 ==========
print("\n[步骤 2/3] 运行社保基金风格追踪 ...")
ss_tracker = SocialSecurityStyleTracker()
ss_tracker.analyze_styles()
ss_tracker.fetch_etf_flows(flows)
ss_tracker.run_signal_detection()

# ========== 4. 组装持仓/风格数据 ==========
# 年度计划按用户确认的 200 万总资金生成，positions.json 仅作为当前持仓参考。
current_cash = float(positions.get('cash', 0) or 0)
cash = PLAN_TOTAL_CAPITAL
holding_values = {
    "核心资产": cash * 0.25,
    "周期/顺周期": cash * 0.20,
    "防御/红利": cash * 0.25,
    "成长科技": cash * 0.15,
    "金融/银行": cash * 0.15,
}

# ========== 5. 生成 Markdown 报告 ==========
print("\n[步骤 3/3] 生成交易计划报告 ...")
R = []

def _h(text, level=1):
    R.append("")
    R.append(("#" * level) + " " + text)
    R.append("")

def _p(text):
    R.append(text)
    R.append("")

def _ul(items):
    for it in items:
        R.append(f"- {it}")
    R.append("")

# ---------- 封面 ----------
_h("2026年度交易计划 — 量化策略系统 v5.2", 1)
_p(f"**生成时间**: {today}  ")
_p(f"**计划周期**: {PLAN_START_DATE} 至 {PLAN_END_DATE}，年底前完成建仓  ")
_p(f"**计划总资金**: ¥ {cash:,.0f}（其中建仓资金 ¥{PLAN_INVESTABLE_CAPITAL:,.0f}，现金储备 ¥{cash*PLAN_CASH_WEIGHT:,.0f}）  ")
_p(f"**当前配置现金参考**: ¥ {current_cash:,.0f}（来自 positions.json，仅作当前状态参考）  ")
_p(f"**策略框架**: 康波周期 + 十五五规划 + 社保基金ETF追踪 + 实时ETF资金流  ")
_p("**文件结构**: `bootstrap.py` | `engine/data.py` | `engine/rebalance.py` | `engine/etf_flow.py` | `engine/social_security.py` | `modes/operations.py`")

# ---------- 执行摘要 ----------
_h("一、执行摘要", 2)
_p("本报告基于 v5.2 最新模块架构，整合三大信号系统：")
_ul([
    f"ETF资金流: 监控 {len(NATIONAL_TEAM_ETFS)} 只国家队ETF，生成 {len(signals) if isinstance(signals, dict) else 0}+ 条信号",
    f"社保风格: {len(list(STYLE_DEFINITIONS.keys()))} 种风格分类，买入信号 {len(ss_tracker.buy_signals)} 条，卖出信号 {len(ss_tracker.sell_signals)} 条",
    f"再平衡引擎: Excel驱动 + portfolio.yaml 后备，支持多策略投资组合优化",
])
_p("**当前风险评级**: 中等 — 自 2026-06-15 起采用分批建仓，单月最大新增仓位不超过 25%，年底保留 10% 现金缓冲")

# ---------- 目标仓位 ----------
_h("二、2026 目标仓位配置", 2)
_p(f"**总资金规模**: ¥ {cash:,.0f}；建仓资金 ¥{PLAN_INVESTABLE_CAPITAL:,.0f}，现金储备 {PLAN_CASH_WEIGHT*100:.0f}%（¥{cash*PLAN_CASH_WEIGHT:,.0f}）")

R.append("| 风格 | 目标权重 | 目标金额 | 说明 |")
R.append("|------|---------|---------|------|")
for style, target in [("核心资产", 0.25), ("周期/顺周期", 0.20),
                      ("防御/红利", 0.25), ("成长科技", 0.15), ("金融/银行", 0.15)]:
    desc = STYLE_DEFINITIONS.get(style, {}).get('desc', '')
    R.append(f"| {style} | {target*100:.0f}% | ¥{cash*target:,.0f} | {desc} |")
R.append("")

# 标的级目标仓位（20只候选标的）
_h("标的级目标分配（20只候选）", 3)
target_assets = [
    # 宽基ETF (6)
    ("510300.SH", "沪深300ETF华泰柏瑞", 0.12, "宽基核心"),
    ("510500.SH", "中证500ETF南方",      0.08, "中盘成长"),
    ("512100.SH", "中证1000ETF南方",      0.06, "小盘风格"),
    ("588000.SH", "科创50ETF华夏",        0.08, "科创/数字经济"),
    ("159915.SZ", "创业板ETF易方达",        0.06, "成长科技"),
    ("518880.SH", "黄金ETF华安",           0.10, "防御/避险"),
    # 成长科技 (4)
    ("300308.SZ", "中际旭创",              0.05, "AI/算力/十五五"),
    ("688041.SH", "海光信息",              0.03, "芯片/国产替代"),
    ("300274.SZ", "阳光电源",              0.03, "储能/新能源"),
    ("002371.SZ", "北方华创",              0.03, "半导体设备"),
    # 防御/红利 (3)
    ("601088.SH", "中国神华",              0.05, "能源安全/高股息"),
    ("600276.SH", "恒瑞医药",              0.03, "医药创新/内需"),
    ("601888.SH", "中国中免",              0.02, "消费复苏/免税"),
    # 周期/顺周期 (6)
    ("600989.SH", "宝丰能源",              0.02, "煤化工/周期复苏"),
    ("600875.SH", "东方电气",              0.02, "电力装备/核电"),
    ("600089.SH", "特变电工",              0.02, "特高压/新能源装备"),
    ("600995.SH", "南网储能",              0.02, "抽水蓄能/电力系统"),
    ("000425.SZ", "徐工机械",               0.02, "工程机械/一带一路"),
    ("688017.SH", "绿的谐波",              0.02, "人形机器人/精密制造"),
    # 核心资产 (1)
    ("600406.SH", "国电南瑞",              0.04, "电网/数字能源"),
    # 现金
    ("CASH",       "现金储备",              0.10, "灵活流动性"),
]
R.append("| 代码 | 名称 | 目标权重 | 目标金额 | 角色 |")
R.append("|------|------|---------|---------|------|")
for code, name, w, role in target_assets:
    R.append(f"| {code} | {name} | {w*100:.0f}% | ¥{cash*w:,.0f} | {role} |")
R.append("")

# ---------- 分批建仓计划 ----------
_h("三、2026-06-15 至年底 200万分批建仓计划", 2)
_p("**执行原则**: Wind MCP 数据优先；若 Wind 不可用，才按系统回退链使用 tushare / yfinance / 新浪 / 参数模型。每批建仓前必须重新检查 ETF 资金流、社保风格信号、组合回撤与单标的止损位。")
_p(f"**建仓目标**: 年底前形成 90% 目标仓位（¥{PLAN_INVESTABLE_CAPITAL:,.0f}），保留 10% 现金（¥{cash*PLAN_CASH_WEIGHT:,.0f}）。")

build_schedule = [
    ("第1批", "2026-06-15 ~ 2026-06-30", 0.20, "先建防御底仓与宽基核心，避免一次性追高"),
    ("第2批", "2026-07-01 ~ 2026-07-31", 0.20, "补齐宽基 ETF、黄金与高股息能源"),
    ("第3批", "2026-08-01 ~ 2026-08-31", 0.15, "根据 Wind 资金流加仓科创/创业板与成长科技"),
    ("第4批", "2026-09-01 ~ 2026-09-30", 0.15, "布局顺周期、设备制造和电力系统方向"),
    ("第5批", "2026-10-01 ~ 2026-10-31", 0.10, "只在回撤或资金流确认时加仓个股，避免节后高波动"),
    ("第6批", "2026-11-01 ~ 2026-11-30", 0.10, "按偏离度补齐低配风格，控制单标的集中度"),
    ("第7批", "2026-12-01 ~ 2026-12-31", 0.10, "年底完成目标仓位，保留现金缓冲并复核五年目标约束"),
]
R.append("| 批次 | 时间窗口 | 本批建仓比例 | 本批金额 | 累计建仓 | 执行重点 |")
R.append("|------|----------|-------------|---------|---------|----------|")
cum_build = 0.0
for batch, window, pct, focus in build_schedule:
    cum_build += pct
    R.append(f"| {batch} | {window} | {pct*100:.0f}% | ¥{PLAN_INVESTABLE_CAPITAL*pct:,.0f} | {cum_build*100:.0f}% | {focus} |")
R.append("")
_p("**风控硬约束**: 组合五年目标年化收益率 ≥ 8%；组合最大回撤 ≤ 15%；任一单标的未成交不得计入真实持仓；若组合回撤达到 10%，暂停新增个股仓位，仅允许宽基/黄金/现金调整。")

_h("建仓资金落点（按 90% 建仓资金拆分）", 3)
R.append("| 代码 | 名称 | 年底目标权重 | 年底目标金额 | 建仓资金内占比 | 建仓金额 |")
R.append("|------|------|-------------|-------------|---------------|---------|")
for code, name, w, role in target_assets:
    if code == "CASH":
        continue
    build_ratio = w / (1 - PLAN_CASH_WEIGHT)
    R.append(f"| {code} | {name} | {w*100:.0f}% | ¥{cash*w:,.0f} | {build_ratio*100:.1f}% | ¥{PLAN_INVESTABLE_CAPITAL*build_ratio:,.0f} |")
R.append("")

# ---------- ETF资金流 TOP ----------
_h("四、实时ETF资金流 TOP 信号", 2)
_p(f"数据源: Wind MCP (实时) / tushare / yfinance / 模拟数据（优雅降级）")
_p(f"监控标的: {len(NATIONAL_TEAM_ETFS)} 只 ETF  ")

if flows:
    sorted_flows = sorted(
        flows.values(),
        key=lambda x: float(x.get('net_flow_yi', 0)),
        reverse=True,
    )
    R.append("| 代码 | 名称 | 净流入(亿) | 涨跌幅 | 趋势 | 国家队 |")
    R.append("|------|------|-----------|-------|------|-------|")
    for item in sorted_flows[:10]:
        nat_flag = "✅" if item.get('is_national_team') else "—"
        R.append(
            f"| {item.get('code','')} | {item.get('name','')} | "
            f"{float(item.get('net_flow_yi',0)):+.2f} | "
            f"{float(item.get('change_pct',0)):+.2f}% | "
            f"{item.get('trend','—')} | {nat_flag} |"
        )
    R.append("")

    _h("买入信号（净流入强度高 + 国家队）", 3)
    buy_list = signals.get('buy', []) if isinstance(signals, dict) else []
    if buy_list:
        for s in buy_list[:8]:
            R.append(f"- **{s['code']} {s['name']}**: 净流入 {s.get('net_flow','N/A')}亿, 强度 {s.get('strength','N/A')} — {s.get('rationale','')}")
    else:
        _p("当前无明确买入信号，建议观望/持有核心资产。")

    _h("卖出信号（净流出强度高）", 3)
    sell_list = signals.get('sell', []) if isinstance(signals, dict) else []
    if sell_list:
        for s in sell_list[:8]:
            R.append(f"- **{s['code']} {s['name']}**: 净流入 {s.get('net_flow','N/A')}亿, 强度 {s.get('strength','N/A')} — {s.get('rationale','')}")
    else:
        _p("当前无明确卖出信号。")

# ---------- 社保风格 ----------
_h("四、社保基金风格追踪（2026年度信号）", 2)
if getattr(ss_tracker, 'style_weights', None):
    R.append("| 风格 | 当前仓位 | 目标仓位 | 偏离 | 信号 |")
    R.append("|------|---------|---------|------|------|")
    # style_weights 是当前权重，目标从 STYLE_DEFINITIONS fallback
    buy_map = {s.get('style'): s for s in ss_tracker.buy_signals}
    sell_map = {s.get('style'): s for s in ss_tracker.sell_signals}
    for style, cur in ss_tracker.style_weights.items():
        cur_pct = float(cur) * 100
        # 从买入信号中提取目标
        sig_obj = buy_map.get(style) or sell_map.get(style)
        if sig_obj:
            tgt_pct = float(sig_obj.get('target_weight_pct', cur_pct))
            dev = cur_pct - tgt_pct
            sig = sig_obj.get('signal_type', '—')
        else:
            tgt_pct = float(STYLE_DEFINITIONS.get(style, {}).get('weight', cur)) * 100
            dev = cur_pct - tgt_pct
            sig = "持平"
        R.append(f"| {style} | {cur_pct:.1f}% | {tgt_pct:.1f}% | {dev:+.1f}% | {sig} |")
    R.append("")

    _h("买入信号 (风格低估/资金流入)", 3)
    if ss_tracker.buy_signals:
        for s in ss_tracker.buy_signals:
            reason = "; ".join(s.get('reasons', [])[:2]) or s.get('rationale', '')
            adj = float(s.get('suggested_adjust_pct', 0))
            amt = cash * adj / 100
            related = ",".join(s.get('related_etfs', [])[:3])
            R.append(
                f"- **{s.get('style','')}** (置信度 {s.get('confidence','中')}, 十五五对齐 {s.get('alignment_15th_5','-')}): "
                f"建议加仓 {adj:.1f}% (约 ¥{amt:,.0f}) — 相关标的 {related}"
            )
    else:
        _p("暂未触发。")

    _h("卖出信号 (风格高估/资金流出)", 3)
    if ss_tracker.sell_signals:
        for s in ss_tracker.sell_signals:
            reason = "; ".join(s.get('reasons', [])[:2]) or s.get('rationale', '')
            R.append(f"- **{s.get('style','')}**: {reason}")
    else:
        _p("暂未触发。")

# ---------- 季度交易日历 ----------
_h("六、2026 年内交易日历", 2)
R.append("| 阶段 | 时间 | 核心策略 | 重点检查日 | 风控阈值 |")
R.append("|------|------|---------|-----------|---------|")
R.append("| 起始建仓 | 6/15-6/30 | 防御底仓 + 宽基核心 | 6/15, 6/24, 6/30 | 单日新增仓位 ≤ 总资金 8% |")
R.append("| Q3建仓 | 7/1-9/30 | 宽基、成长科技、顺周期分批补齐 | 每周一 + 月末 | 组合回撤 > 10% 暂停个股加仓 |")
R.append("| Q4补仓 | 10/1-11/30 | 按低配风格与 Wind 资金流补齐 | 每周一 + 月末 | 单标的最大权重 ≤ 12% |")
R.append("| 年底验收 | 12/1-12/31 | 完成 90% 建仓并保留 10% 现金 | 12/1, 12/15, 12/31 | 最大回撤硬约束 ≤ 15% |")
R.append("")
_p("**强制再平衡触发条件**: 任一风格仓位偏离目标 ≥ 10%，或任一ETF净流入/流出连续3日超 2 亿元。")

# ---------- 十五五规划 ----------
_h("七、十五五规划重点板块 (2026 持仓建议)", 2)
_ul([
    "**先进制造 / 半导体设备**: 北方华创(002371)、中际旭创(300308)、海光信息(688041) + 半导体ETF(512760) — 目标权重 ~14%",
    "**新能源 / 储能**: 阳光电源(300274)、东方电气(600875)、特变电工(600089)、南网储能(600995) — 目标权重 ~10%",
    "**数字经济 / AI 算力**: 科创50ETF(588000) + 创业板ETF(159915) + 中际旭创/海光信息/绿的谐波 — 目标权重 ~15%",
    "**消费复苏 / 内需**: 恒瑞医药(600276)、中国中免(601888) — 目标权重 ~5%",
    "**央企估值 / 高股息 / 能源安全**: 中国神华(601088) + 沪深300ETF(510300) + 黄金ETF(518880) — 目标权重 ~27%",
    "**基建 / 一带一路 / 工程机械**: 徐工机械(000425) + 中证500ETF(510500) — 目标权重 ~6%",
    "**电网 / 数字能源**: 国电南瑞(600406) + 特变电工(600089) — 目标权重 ~6%",
    "**宽基分散**: 中证1000ETF(512100) 平滑小盘波动 — 目标权重 ~6%",
    "**周期顺周期 / 煤化工**: 宝丰能源(600989) — 目标权重 ~2%",
    "**现金储备**（灵活流动性/调仓缓冲）: 10%",
])

# ---------- 止损止盈 ----------
_h("八、止损止盈规则 (自动执行)", 2)
_default_sl = [
    # 宽基ETF (6)
    ("510300.SH", "沪深300ETF", 4.884, 10.0, 20.0),
    ("510500.SH", "中证500ETF", 8.439, 10.0, 25.0),
    ("512100.SH", "中证1000ETF", 2.600, 12.0, 30.0),
    ("588000.SH", "科创50ETF", 1.813, 12.0, 30.0),
    ("159915.SZ", "创业板ETF", 2.280, 12.0, 30.0),
    ("518880.SH", "黄金ETF",  8.948, 5.0, 15.0),
    # 成长科技个股 (4)
    ("300308.SZ", "中际旭创", 150.0, 15.0, 40.0),
    ("688041.SH", "海光信息", 40.0, 15.0, 40.0),
    ("300274.SZ", "阳光电源", 90.0, 15.0, 35.0),
    ("002371.SZ", "北方华创", 280.0, 15.0, 40.0),
    # 防御/红利个股 (3)
    ("601088.SH", "中国神华", 45.0, 8.0, 25.0),
    ("600276.SH", "恒瑞医药", 48.5, 10.0, 20.0),
    ("601888.SH", "中国中免", 75.0, 12.0, 30.0),
    # 周期/顺周期个股 (6)
    ("600989.SH", "宝丰能源", 16.5, 10.0, 25.0),
    ("600875.SH", "东方电气", 22.0, 12.0, 25.0),
    ("600089.SH", "特变电工", 18.0, 12.0, 25.0),
    ("600995.SH", "南网储能", 18.0, 10.0, 25.0),
    ("000425.SZ", "徐工机械", 6.80, 10.0, 20.0),
    ("688017.SH", "绿的谐波", 130.0, 15.0, 40.0),
    # 核心资产个股 (1)
    ("600406.SH", "国电南瑞", 25.0, 8.0, 20.0),
]
has_custom = (sl_rules and 'stop_loss_rules' in sl_rules
              and isinstance(sl_rules['stop_loss_rules'], dict))

R.append("| 代码 | 名称 | 基准价 | 止损位 | 止盈位 |")
R.append("|------|------|-------|-------|-------|")
if has_custom:
    for code, r in sl_rules['stop_loss_rules'].items():
        base = float(r.get('base_price', 0))
        sl = float(r.get('stop_loss_pct', 0)) * 100
        tp = float(r.get('take_profit_pct', 0)) * 100
        name = r.get('name', code)
        R.append(f"| {code} | {name} | ¥{base:.3f} | -{sl:.1f}% | +{tp:.1f}% |")
else:
    for code, name, base, sl, tp in _default_sl:
        R.append(f"| {code} | {name} | ¥{base:.3f} | -{sl:.1f}% | +{tp:.1f}% |")
R.append("")

# ---------- 运行命令速查 ----------
_h("八、系统运行命令速查", 2)
R.append("```bash")
R.append("# 实时ETF资金流监控 (新引擎 v5.2)")
R.append("python modes/operations.py --etf-flow-v2")
R.append("")
R.append("# 社保基金风格追踪 (新引擎 v5.2)")
R.append("python modes/operations.py --social-security-v2")
R.append("")
R.append("# 日常三阶段交易工作流")
R.append("python modes/operations.py --daily")
R.append("")
R.append("# 周一调仓自动执行")
R.append("python modes/operations.py --monday-rebalance")
R.append("")
R.append("# 宏观综合分析 (康波+十五五+社保)")
R.append("python modes/operations.py --macro-analysis")
R.append("```")
R.append("")

# ---------- 风险声明 ----------
_h("十、风险声明", 2)
_p("- 本报告仅供策略参考，不构成任何投资建议。")
_p("- 市场存在系统性风险，历史信号不代表未来表现。")
_p("- 请结合个人风险偏好与流动性需求，自行决策。")

# ========== 6. 写入文件 ==========
report_text = "\n".join(R)
out_dir = os.path.join(BASE_DIR, 'reports')
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, f"2026年度交易计划_{datetime.now().strftime('%Y%m%d')}.md")
with open(out_file, 'w', encoding='utf-8') as f:
    f.write(report_text)

print(f"\n✅ 报告已保存: {out_file}")
print(f"   报告大小: {len(report_text)} 字符, {report_text.count(chr(10))} 行")
