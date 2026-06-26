# -*- coding: utf-8 -*-
"""
11_量化策略 当前持仓收益快照 v2
数据源:
  - A股: Wind MCP / stock_data.get_stock_kline
  - ETF/LOF/指数: Wind MCP / fund_data.get_fund_kline
运行: python calc_pnl_now.py
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
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


def to_wind(code: str) -> str:
    """6 / 5 开头 → 上交所; 0 / 3 开头 → 深交所; 688 科创板属上交所"""
    if code.startswith("6") or code.startswith("5"):
        return f"{code}.SH"
    if code.startswith("0") or code.startswith("3"):
        return f"{code}.SZ"
    return f"{code}.SH"


def is_etf(code: str) -> bool:
    """5 开头（上交所ETF）/ 15 开头（深交所ETF）/ 16 开头LOF"""
    return (
        code.startswith("5")
        or code.startswith("15")
        or code.startswith("16")
        or code.startswith("18")
    )


def parse_output(stdout: str):
    """
    从 wind cli.mjs 输出中提取嵌套 JSON。
    外层: {"content": [{"type": "text", "text": "<inner-json>"}]}
    """
    try:
        outer = json.loads(stdout)
    except json.JSONDecodeError:
        # 尝试截取最后一个 {...}
        i = stdout.rfind("{")
        j = stdout.rfind("}")
        if 0 <= i < j:
            outer = json.loads(stdout[i : j + 1])
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
    return [dict(zip(cols, row)) for row in rows]


def fetch_kline_close(code: str, start_date: str, end_date: str):
    """
    查最近一个交易日的收盘价。返回 (close_price, trade_date)。
    """
    wc = to_wind(code)
    server_type = "fund_data" if is_etf(code) else "stock_data"
    tool_name = "get_fund_kline" if is_etf(code) else "get_stock_kline"
    payload = json.dumps(
        {"windcode": wc, "begin_date": start_date, "end_date": end_date},
        ensure_ascii=False,
    )
    # 通过文件传 payload, 避免 Windows cmd / powershell 下的中文编码问题
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
            timeout=30,
        )
        rows = parse_output(r.stdout)
        if not rows:
            return None, None
        latest = rows[-1]
        # 字段: MATCH 或 CLOSE 都有可能
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


def main():
    with open(POSITIONS, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    positions = cfg.get("positions", {})
    cash = float(cfg.get("cash", 0))

    # 查询范围: 最近 3 个交易日（避免周末/节假日）
    today = datetime.now()
    start = today - timedelta(days=7)
    start_date = start.strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")

    total_cost = 0.0
    total_market = 0.0
    table_rows = []

    print("=" * 92)
    print(f"  11_量化策略 持仓快照 —— {today:%Y-%m-%d %H:%M:%S}")
    print(f"  初始资金: ￥{INITIAL_CAPITAL:,.2f}   可用现金: ￥{cash:,.2f}")
    print(f"  行情来源: Wind MCP kline [{start_date} → {end_date}]")
    print("=" * 92)
    print(
        f"{'代码':<8} {'名称':<12} {'数量':>9} {'成本价':>9} "
        f"{'最新价':>9} {'市值':>13} {'盈亏':>13} {'收益率':>9} {'日期':>9}"
    )
    print("-" * 92)

    for code, pos in positions.items():
        shares = int(pos["shares"])
        avg_cost = float(pos["avg_cost"])
        price, date_s = fetch_kline_close(code, start_date, end_date)
        if price is None or price <= 0:
            price = avg_cost  # 查不到就回退成本价
        cost_amt = shares * avg_cost
        mkt_amt = shares * price
        pnl = mkt_amt - cost_amt
        pct_pos = (price - avg_cost) / avg_cost * 100
        total_cost += cost_amt
        total_market += mkt_amt
        date_short = (date_s or "")[:10] if date_s else ""

        table_rows.append(
            {
                "code": code,
                "name": STOCK_NAMES.get(code, code),
                "shares": shares,
                "avg_cost": round(avg_cost, 4),
                "price": round(price, 4),
                "market_value": round(mkt_amt, 2),
                "pnl": round(pnl, 2),
                "return_on_cost_pct": round(pct_pos, 3),
                "as_of_date": date_short,
            }
        )
        name = STOCK_NAMES.get(code, code)
        print(
            f"{code:<8} {name:<12} {shares:>9,} {avg_cost:>9.3f} "
            f"{price:>9.3f} {mkt_amt:>13,.2f} {pnl:>+13,.2f} {pct_pos:>+8.2f}% {date_short:>9}"
        )

    total_value = total_market + cash
    total_pnl = total_value - INITIAL_CAPITAL
    total_ret = total_pnl / INITIAL_CAPITAL * 100
    cost_pnl = total_market - total_cost
    cost_ret = cost_pnl / total_cost * 100 if total_cost else 0

    print("-" * 92)
    print(f"{'合计持仓成本':>43} ￥{total_cost:>15,.2f}")
    print(
        f"{'合计持仓市值':>43} ￥{total_market:>15,.2f}   持仓盈亏 ￥{cost_pnl:>+12,.2f} ({cost_ret:+.2f}%)"
    )
    print(f"{'账户总值(含现金)':>43} ￥{total_value:>15,.2f}")
    print(f"{'相对初始资金 300 万 总盈亏':>43} ￥{total_pnl:>+15,.2f} ({total_ret:+.2f}%)")
    print("=" * 92)
    print(f"时间戳: {today:%Y-%m-%d %H:%M:%S}")

    # 快照文件
    snap = {
        "timestamp": today.isoformat(timespec="seconds"),
        "initial_capital": INITIAL_CAPITAL,
        "cash": round(cash, 2),
        "positions": table_rows,
        "summary": {
            "total_cost": round(total_cost, 2),
            "total_market_value": round(total_market, 2),
            "total_account_value": round(total_value, 2),
            "pnl_on_cost": round(cost_pnl, 2),
            "return_on_cost_pct": round(cost_ret, 3),
            "pnl_on_initial": round(total_pnl, 2),
            "return_on_initial_pct": round(total_ret, 3),
        },
    }
    out_path = os.path.join(
        HERE, "data", f"pnl_snapshot_{today:%Y%m%d_%H%M%S}.json"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    print(f"快照已保存: {out_path}")


if __name__ == "__main__":
    main()
