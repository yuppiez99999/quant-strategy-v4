# -*- coding: utf-8 -*-
"""
11_量化策略 每日持仓报告 (新口径)
=====================================

新口径（用户指定）:
  - 初始资金: 3,000,000 元
  - 现金 = 3,000,000 - 持仓成本合计
  - 账户总值 = 持仓最新市值 + 现金
  - 总盈亏 = 账户总值 - 3,000,000 (= 持仓浮动盈亏)

产出:
  - Markdown 日报: 每日报告归档/YYYY-MM-DD/持仓日报_YYYYMMDD.md
  - PDF 日报:      每日报告归档/YYYY-MM-DD/持仓日报_YYYYMMDD.pdf
  - JSON 快照:     11_量化策略/data/pnl_snapshot_YYYYMMDD_HHMMSS.json

数据源:
  - 本地持仓配置: 11_量化策略/config/positions.json
  - 最新行情:     Wind MCP / stock_data.get_stock_kline
                               / fund_data.get_fund_kline
                               (取最近交易日的 MATCH 收盘价)
"""

import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta

# reportlab 重库，模块级导入（一次性成本，避免每次build_pdf都import）
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WIND_CLI_DIR = os.path.expandvars(r"%USERPROFILE%\.agents\skills\wind-mcp-skill")
NODE = os.environ.get("NODE_PATH", "node")
POSITIONS = os.path.join(HERE, "config", "positions.json")

INITIAL_CAPITAL = 3_000_000

STOCK_NAMES = {
    "601088": "中国神华",
    "600276": "恒瑞医药",
    "510300": "沪深300ETF",
    "512100": "中证1000ETF",
    "588000": "科创50ETF",
    "159915": "创业板ETF",
    "518880": "黄金ETF",
    "512760": "半导体ETF",
    "512880": "证券ETF",
    "000425": "徐工机械",
    "000858": "五粮液",
    "300274": "阳光电源",
    "510500": "中证500ETF",
    "688041": "海光信息",
    "601888": "中国中免",
    "600875": "东方电气",
    "600089": "特变电工",
    "688017": "绿的谐波",
    "600406": "国电南瑞",
}


# ---------------------------------------------------------------------------
# 1. Wind MCP 行情查询
# ---------------------------------------------------------------------------

def to_wind(code: str) -> str:
    if code.startswith("6") or code.startswith("5"):
        return f"{code}.SH"
    if code.startswith("0") or code.startswith("3"):
        return f"{code}.SZ"
    return f"{code}.SH"


def is_etf(code: str) -> bool:
    return code.startswith(("5", "15", "16", "18"))


def parse_wind_output(stdout: str):
    """解析 cli.mjs 的 JSON 输出, 返回 rows=[dict, ...]。"""
    try:
        outer = json.loads(stdout)
    except json.JSONDecodeError:
        i = stdout.rfind("{")
        j = stdout.rfind("}")
        if 0 <= i < j:
            outer = json.loads(stdout[i: j + 1])
        else:
            return None
    if isinstance(outer, dict) and outer.get("ok") is False:
        return None
    texts = [c.get("text") for c in outer.get("content", []) if c.get("type") == "text"]
    if not texts:
        return None
    inner = json.loads(texts[0])
    data = inner.get("data")
    if not data:
        return None
    cols = [c["name"] for c in data.get("columns", [])]
    rows = data.get("rows") or []
    return [dict(zip(cols, r)) for r in rows]


def fetch_kline_close(code: str, start_date: str, end_date: str):
    """返回 (close_price, trade_date_str)。"""
    wc = to_wind(code)
    server_type = "fund_data" if is_etf(code) else "stock_data"
    tool_name = "get_fund_kline" if is_etf(code) else "get_stock_kline"
    payload = json.dumps(
        {"windcode": wc, "begin_date": start_date, "end_date": end_date},
        ensure_ascii=False,
    )
    tmp = os.path.join(tempfile.gettempdir(), f"wind_{os.getpid()}_{code}.json")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(payload)
    try:
        with open(tmp, "r", encoding="utf-8") as f:
            payload_read = f.read()
        r = subprocess.run(
            [NODE, "scripts/cli.mjs", "call", server_type, tool_name, payload_read],
            cwd=WIND_CLI_DIR,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=40,
        )
        rows = parse_wind_output(r.stdout)
        if not rows:
            return None, None
        latest = rows[-1]
        price_s = latest.get("MATCH") or latest.get("CLOSE") or latest.get("close")
        date_s = latest.get("_DATE") or latest.get("TIME")
        try:
            price = float(price_s)
        except (TypeError, ValueError):
            price = None
        return price, date_s
    except Exception as e:
        print(f"  [err] {code}: {e}")
        return None, None
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# 2. 计算汇总 (新口径)
# ---------------------------------------------------------------------------

def compute_positions():
    with open(POSITIONS, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    positions = cfg.get("positions", {})

    today = datetime.now()
    start_date = (today - timedelta(days=14)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")

    rows = []
    total_cost = 0.0
    total_market = 0.0

    for code, pos in positions.items():
        shares = int(pos["shares"])
        avg_cost = float(pos["avg_cost"])
        price, date_s = fetch_kline_close(code, start_date, end_date)
        if price is None or price <= 0:
            price = avg_cost
        cost_amt = shares * avg_cost
        mkt_amt = shares * price
        pnl = mkt_amt - cost_amt
        if avg_cost > 0:
            pct_pos = (price - avg_cost) / avg_cost * 100
        else:
            pct_pos = 0.0
        weight_pct = (mkt_amt / INITIAL_CAPITAL) * 100

        total_cost += cost_amt
        total_market += mkt_amt

        rows.append({
            "code": code,
            "name": STOCK_NAMES.get(code, code),
            "shares": shares,
            "avg_cost": round(avg_cost, 4),
            "price": round(price, 4),
            "market_value": round(mkt_amt, 2),
            "cost_amount": round(cost_amt, 2),
            "pnl": round(pnl, 2),
            "return_on_cost_pct": round(pct_pos, 3),
            "weight_pct": round(weight_pct, 3),
            "as_of_date": (date_s or "")[:10] if date_s else "",
        })

    # 新口径
    cash = INITIAL_CAPITAL - total_cost
    account_value = total_market + cash
    total_pnl = account_value - INITIAL_CAPITAL  # 等于 mkt - cost
    total_ret = total_pnl / INITIAL_CAPITAL * 100
    ret_on_cost = (total_market - total_cost) / total_cost * 100 if total_cost else 0

    # 按收益率排序（从高到低）
    rows.sort(key=lambda r: r["return_on_cost_pct"], reverse=True)

    summary = {
        "initial_capital": INITIAL_CAPITAL,
        "total_cost": round(total_cost, 2),
        "cash": round(cash, 2),
        "total_market_value": round(total_market, 2),
        "account_value": round(account_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_return_pct": round(total_ret, 3),
        "return_on_cost_pct": round(ret_on_cost, 3),
        "date_range": f"{start_date} - {end_date}",
    }

    return rows, summary, today


# ---------------------------------------------------------------------------
# 3. Markdown 日报
# ---------------------------------------------------------------------------

def fmt_yuan(v: float) -> str:
    return f"￥{v:,.2f}"


def fmt_sign(v: float) -> str:
    return f"+{v:,.2f}" if v >= 0 else f"{v:,.2f}"


def fmt_sign_pct(v: float) -> str:
    return f"+{v:.2f}%" if v >= 0 else f"{v:.2f}%"


def build_markdown(rows, summary, now: datetime) -> str:
    lines: list[str] = []
    lines.append(f"# 11_量化策略 · 持仓日报")
    lines.append("")
    lines.append(f"> 报告日期: **{now:%Y-%m-%d %H:%M:%S}**  |  数据源: Wind MCP kline 最近交易日收盘价")
    lines.append("")
    lines.append("## 一、账户概览（新口径：现金 = 300 万 − 持仓成本）")
    lines.append("")
    lines.append("| 项目 | 金额 |")
    lines.append("| --- | ---: |")
    lines.append(f"| 初始资金 | {fmt_yuan(summary['initial_capital'])} |")
    lines.append(f"| 持仓成本合计 | {fmt_yuan(summary['total_cost'])} |")
    lines.append(f"| **现金（300 万 − 成本）** | **{fmt_yuan(summary['cash'])}** |")
    lines.append(f"| 持仓最新市值 | {fmt_yuan(summary['total_market_value'])} |")
    lines.append(f"| **账户总值 = 市值 + 现金** | **{fmt_yuan(summary['account_value'])}** |")
    lines.append(f"| 持仓浮动盈亏（成本口径） | ￥{fmt_sign(summary['total_pnl'])}（{fmt_sign_pct(summary['return_on_cost_pct'])}） |")
    lines.append(f"| 总盈亏（300 万口径） | ￥{fmt_sign(summary['total_pnl'])}（{fmt_sign_pct(summary['total_return_pct'])}） |")
    lines.append("")
    lines.append("```")
    lines.append(f"  现金         = 3,000,000 - {summary['total_cost']:,.2f} = {summary['cash']:,.2f}")
    lines.append(f"  账户总值     = {summary['total_market_value']:,.2f} + {summary['cash']:,.2f} = {summary['account_value']:,.2f}")
    lines.append(f"  总盈亏       = 账户总值 - 3,000,000 = {summary['total_pnl']:,.2f}  ({summary['total_return_pct']:.2f}%)")
    lines.append(f"  持仓收益率   = ({summary['total_market_value']:,.2f} - {summary['total_cost']:,.2f}) / {summary['total_cost']:,.2f} = {summary['return_on_cost_pct']:.2f}%")
    lines.append("```")
    lines.append("")
    lines.append("## 二、逐只持仓（按收益率排序）")
    lines.append("")
    lines.append("| 代码 | 名称 | 数量 | 成本价 | 最新价 | 成本金额 | 市值 | 浮动盈亏 | 收益率 | 权重 | 行情日期 |")
    lines.append("| ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")

    best_pct = max(r["return_on_cost_pct"] for r in rows)
    worst_pct = min(r["return_on_cost_pct"] for r in rows)

    for r in rows:
        tag = ""
        if r["return_on_cost_pct"] == best_pct and best_pct > 0:
            tag = " ⭐"
        elif r["return_on_cost_pct"] == worst_pct and worst_pct < 0:
            tag = " 🔴"
        lines.append(
            f"| {r['code']} | {r['name']}{tag} | {r['shares']:,} | "
            f"{r['avg_cost']:.3f} | {r['price']:.3f} | "
            f"{r['cost_amount']:,.2f} | {r['market_value']:,.2f} | "
            f"{fmt_sign(r['pnl'])} | {fmt_sign_pct(r['return_on_cost_pct'])} | "
            f"{r['weight_pct']:.2f}% | {r['as_of_date']} |"
        )

    lines.append("")
    lines.append("## 三、结构观察")
    lines.append("")

    # 分组收益：ETF vs 个股
    etf_rows = [r for r in rows if is_etf(r["code"])]
    stock_rows = [r for r in rows if not is_etf(r["code"])]

    def group_stats(rs):
        mv = sum(r["market_value"] for r in rs)
        pnl = sum(r["pnl"] for r in rs)
        cost = sum(r["cost_amount"] for r in rs)
        ret = (pnl / cost * 100) if cost else 0
        return mv, pnl, ret, cost

    etf_mv, etf_pnl, etf_ret, etf_cost = group_stats(etf_rows)
    stk_mv, stk_pnl, stk_ret, stk_cost = group_stats(stock_rows)

    lines.append(
        f"- **ETF 组**：成本 {fmt_yuan(etf_cost)}，市值 {fmt_yuan(etf_mv)}，浮动盈亏 ￥{fmt_sign(etf_pnl)}（{fmt_sign_pct(etf_ret)}）"
    )
    lines.append(
        f"- **个股组**：成本 {fmt_yuan(stk_cost)}，市值 {fmt_yuan(stk_mv)}，浮动盈亏 ￥{fmt_sign(stk_pnl)}（{fmt_sign_pct(stk_ret)}）"
    )

    top_by_pnl = sorted(rows, key=lambda r: r["pnl"], reverse=True)[:3]
    bot_by_pnl = sorted(rows, key=lambda r: r["pnl"])[:3]

    lines.append("")
    lines.append("### 盈利贡献 Top 3")
    for r in top_by_pnl:
        lines.append(f"- {r['name']}（{r['code']}）：￥{fmt_sign(r['pnl'])}  |  {fmt_sign_pct(r['return_on_cost_pct'])}")
    lines.append("")
    lines.append("### 亏损贡献 Top 3")
    for r in bot_by_pnl:
        lines.append(f"- {r['name']}（{r['code']}）：￥{fmt_sign(r['pnl'])}  |  {fmt_sign_pct(r['return_on_cost_pct'])}")

    lines.append("")
    lines.append(f"> 报告生成时间: {now:%Y-%m-%d %H:%M:%S}")
    lines.append("> 脚本: 11_quant_daily_report.py  |  数据源: Wind MCP (stock_data / fund_data)")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. PDF 输出 (reportlab + 系统中文字体)
# ---------------------------------------------------------------------------

def pick_cn_font() -> tuple[str, str]:
    """返回 (注册名, ttf 路径)。按优先级搜索常见中文字体。"""
    candidates = [
        ("MSYH",   r"C:\Windows\Fonts\msyh.ttc"),
        ("MSYH",   r"C:\Windows\Fonts\msyh.ttf"),
        ("SIMHEI", r"C:\Windows\Fonts\simhei.ttf"),
        ("SIMSUN", r"C:\Windows\Fonts\simsun.ttc"),
    ]
    for name, path in candidates:
        if os.path.exists(path):
            return name, path
    # fallback: reportlab 自带的 cid 中文字体（无物理文件也能用）
    return ("STSong-Light", "")


def build_pdf(md_text: str, pdf_path: str):
    font_name, font_path = pick_cn_font()
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        except Exception:
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
            font_name = "STSong-Light"
    else:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName=font_name, fontSize=18, leading=24, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName=font_name, fontSize=14, leading=20, spaceAfter=6)
    h3 = ParagraphStyle("h3", parent=styles["Heading3"], fontName=font_name, fontSize=12, leading=18, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName=font_name, fontSize=10, leading=15, spaceAfter=2)
    code = ParagraphStyle("code", parent=styles["Code"], fontName=font_name, fontSize=9, leading=13, textColor=colors.HexColor("#333333"), backColor=colors.HexColor("#F5F5F5"), borderPadding=6, spaceAfter=6)

    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="11_量化策略持仓日报",
    )

    story = []

    for raw_line in md_text.split("\n"):
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 4))
            continue
        if line.startswith("# "):
            story.append(Paragraph(line[2:], h1))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], h2))
        elif line.startswith("### "):
            story.append(Paragraph(line[4:], h3))
        elif line.startswith("> "):
            story.append(Paragraph(line[2:].replace("*", ""), body))
        elif line.startswith("| "):
            # 表格: 聚齐一整块 table 后再渲染
            tbl_lines = [line]
            continue
        elif raw_line.startswith("```"):
            continue
        else:
            if not line:
                continue
            # 处理 bullet list
            if line.startswith("- ") or line.startswith("* "):
                story.append(Paragraph("• " + line[2:], body))
            # 粗体 **xxx** → 转成 <b>xxx</b>
            elif "**" in line:
                import re
                html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
                story.append(Paragraph(html, body))
            else:
                story.append(Paragraph(line, body))

    # 延迟处理的表格：再次从纯文本解析
    # 由于上面的处理中 "| " 开头的被跳过，这里用简单的做法：把所有表格重跑一次
    # 为简化，重新从 md_text 中解析表格。

    # 重建 story（更稳健的做法）
    story.clear()
    in_table = False
    in_code = False
    code_buf: list[str] = []
    table_buf: list[str] = []

    def flush_table():
        nonlocal table_buf
        if not table_buf:
            return
        rows = [r for r in table_buf if "---" not in r]  # 去掉分隔行
        cells = [[c.strip() for c in row.strip("|").split("|")] for row in rows]
        if not cells:
            return
        tbl = Table(cells, colWidths=None, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 1), (1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#999999")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 6))
        table_buf = []

    def flush_code():
        nonlocal code_buf
        if not code_buf:
            return
        story.append(Paragraph("<br/>".join(code_buf), code))
        code_buf = []

    import re

    for raw_line in md_text.split("\n"):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            if not in_code:
                flush_code()
            continue
        if in_code:
            code_buf.append(raw_line.replace(" ", "&nbsp;"))
            continue
        if stripped.startswith("|"):
            table_buf.append(stripped)
            continue
        if table_buf:
            flush_table()

        if not stripped:
            story.append(Spacer(1, 4))
        elif stripped.startswith("# "):
            story.append(Paragraph(stripped[2:], h1))
        elif stripped.startswith("## "):
            story.append(Paragraph(stripped[3:], h2))
        elif stripped.startswith("### "):
            story.append(Paragraph(stripped[4:], h3))
        elif stripped.startswith("> "):
            story.append(Paragraph(stripped[2:], body))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            text = stripped[2:]
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
            story.append(Paragraph("• " + text, body))
        else:
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped)
            # 把 '*' 当成普通字符避免与 italic 冲突
            story.append(Paragraph(text, body))

    flush_table()
    flush_code()
    doc.build(story)


# ---------------------------------------------------------------------------
# 5. 入口
# ---------------------------------------------------------------------------

def main():
    print("==> 读取持仓 & 查询 Wind MCP 行情 ...")
    rows, summary, now = compute_positions()

    md_dir = os.path.join(ROOT, "每日报告归档", now.strftime("%Y-%m-%d"))
    os.makedirs(md_dir, exist_ok=True)
    base = f"持仓日报_{now.strftime('%Y%m%d')}"
    md_path = os.path.join(md_dir, base + ".md")
    pdf_path = os.path.join(md_dir, base + ".pdf")

    md_text = build_markdown(rows, summary, now)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    print(f"[OK] Markdown: {md_path}")

    try:
        build_pdf(md_text, pdf_path)
        print(f"[OK] PDF:      {pdf_path}")
    except Exception as e:
        print(f"[WARN] PDF 生成失败 ({e})，仅产出 Markdown 版。")

    # JSON 快照
    snap_dir = os.path.join(HERE, "data")
    os.makedirs(snap_dir, exist_ok=True)
    snap_path = os.path.join(snap_dir, f"pnl_snapshot_{now:%Y%m%d_%H%M%S}.json")
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump({"timestamp": now.isoformat(timespec="seconds"),
                   "summary": summary, "positions": rows},
                  f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON:     {snap_path}")

    print("")
    print("=== 汇总 (新口径: 现金 = 300万 - 持仓成本) ===")
    print(f"  初始资金       : ￥{summary['initial_capital']:,.2f}")
    print(f"  持仓成本合计   : ￥{summary['total_cost']:,.2f}")
    print(f"  现金           : ￥{summary['cash']:,.2f}")
    print(f"  持仓最新市值   : ￥{summary['total_market_value']:,.2f}")
    print(f"  账户总值       : ￥{summary['account_value']:,.2f}")
    print(f"  总盈亏         : ￥{summary['total_pnl']:+,.2f}  ({summary['total_return_pct']:+.2f}%)")
    print(f"  持仓收益率(成本): {summary['return_on_cost_pct']:+.2f}%")


if __name__ == "__main__":
    main()
