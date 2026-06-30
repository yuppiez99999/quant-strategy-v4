#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
交易时段全模块自启动主调度器 v1.0
=====================================
在交易时段自动启动所有量化策略模块，按时间线编排。

时间线:
  08:40  启动预热 — 系统健康检查 + 数据源连接验证
  08:45  盘前分析 — 晨间行情摘要 + 宏观综合分析(康波+十五五+社保ETF) + 盘前计划
  09:20  开盘前   — ETF资金流向 + 大宗商品监控 + 康波周期分析
  09:25  盘中启动 — 实时监控 + 统一监控 + AI决策引擎(子进程)
  09:30  开盘首触 — AI盘中决策#1 + 风险监控
  10:30  上午盘中 — AI盘中决策#2 + 再平衡检查
  11:25  午盘前   — AI盘中决策#3 + 对冲风险快照
  13:05  午后开盘 — AI盘中决策#4 + 风险监控
  14:05  下午盘中 — AI盘中决策#5 + 再平衡检查
  14:50  收盘前   — AI盘中决策#6 + ML信号预测
  15:05  收盘后   — 收盘报告 + 综合日报
  15:10  盘后联动 — 对冲再平衡联动分析
  15:20  归档整理 — 报告归档 + 持仓快照

运行方式:
  python trading_hours_master.py              # 完整调度（持续运行直到15:30）
  python trading_hours_master.py --once       # 只执行当前时间点任务一次
  python trading_hours_master.py --status     # 查看调度状态
  python trading_hours_master.py --dry-run    # 试运行(不实际执行)
"""

import os
import sys
import json
import time
import signal
import logging
import threading
import subprocess
from pathlib import Path
from datetime import datetime, time as dtime
from typing import Dict, List, Optional, Callable, Any

# ── 编码设置 ──
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── 路径 ──
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR.parent))

REPORT_ROOT = BASE_DIR.parent / '每日报告归档'
LOG_DIR = REPORT_ROOT / datetime.now().strftime('%Y-%m-%d')
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── 日志 ──
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            LOG_DIR / f'trading_master_{datetime.now().strftime("%Y%m%d")}.log',
            encoding='utf-8'
        ),
    ]
)
log = logging.getLogger("TradingMaster")

# ── 主系统入口 ──
MAIN_SCRIPT = BASE_DIR / '量化策略系统 v5.9.py'
PYTHON_EXE = sys.executable


def _make_cmd(*parts: str) -> str:
    """安全构造命令行字符串，自动加引号"""
    return ' '.join(f'"{p}"' for p in parts)


# ── 交易时段配置 ──
_MAIN = str(MAIN_SCRIPT)

TRADING_SCHEDULE = [
    # (时间, 标签, 命令列表, 超时秒)
    ("08:40", "启动预热", [
        _make_cmd(PYTHON_EXE, _MAIN) + " --check",
    ], 60),

    ("08:45", "盘前分析", [
        _make_cmd(PYTHON_EXE, _MAIN) + " --report",
        _make_cmd(PYTHON_EXE, _MAIN) + " --macro-analysis",
    ], 300),

    ("09:20", "开盘前检查", [
        _make_cmd(PYTHON_EXE, _MAIN) + " --etf-flow",
        _make_cmd(PYTHON_EXE, _MAIN) + " --kondratiev",
    ], 180),

    ("09:25", "盘中引擎启动", [], 10),  # 子进程方式启动(见START_MODULES)

    ("09:30", "开盘首触", [
        _make_cmd(PYTHON_EXE, _MAIN) + " --ai-decision",
        _make_cmd(PYTHON_EXE, _MAIN) + " --risk",
    ], 120),

    ("10:30", "上午盘中", [
        _make_cmd(PYTHON_EXE, _MAIN) + " --ai-decision",
        _make_cmd(PYTHON_EXE, _MAIN) + " --rebalance --sync-sl",
    ], 120),

    ("11:25", "午盘前", [
        _make_cmd(PYTHON_EXE, _MAIN) + " --ai-decision",
        _make_cmd(PYTHON_EXE, _MAIN) + " --hedge --no-ai",
    ], 120),

    ("13:05", "午后开盘", [
        _make_cmd(PYTHON_EXE, _MAIN) + " --ai-decision",
        _make_cmd(PYTHON_EXE, _MAIN) + " --risk",
    ], 120),

    ("14:05", "下午盘中", [
        _make_cmd(PYTHON_EXE, _MAIN) + " --ai-decision",
        _make_cmd(PYTHON_EXE, _MAIN) + " --rebalance --sync-sl",
    ], 120),

    ("14:50", "收盘前", [
        _make_cmd(PYTHON_EXE, _MAIN) + " --ai-decision",
        _make_cmd(PYTHON_EXE, _MAIN) + " --ml-signal",
    ], 120),

    ("15:05", "收盘报告", [
        _make_cmd(PYTHON_EXE, _MAIN) + " --report",
        _make_cmd(PYTHON_EXE, _MAIN) + " --daily --phase postmarket",
    ], 300),

    ("15:10", "盘后联动", [
        _make_cmd(PYTHON_EXE, _MAIN) + " --hedge-rebalance --mode=tail_only",
    ], 180),

    ("15:20", "归档整理", [
        _make_cmd(PYTHON_EXE, _MAIN) + " --check",
    ], 60),
]

# ── 需要作为子进程持续运行的模块 ──
_STREAMLIT_APP = str(BASE_DIR / "ui" / "app.py")

START_MODULES = {
    "live_monitor": {
        "cmd": _make_cmd(PYTHON_EXE, str(MAIN_SCRIPT)) + " --live",
        "label": "实时监控(live)",
        "start_at": "09:25",
    },
    "unified_monitor": {
        "cmd": _make_cmd(PYTHON_EXE, str(MAIN_SCRIPT)) + " --unified-monitor",
        "label": "统一监控(unified)",
        "start_at": "09:25",
    },
    "streamlit_ui": {
        "cmd": _make_cmd(PYTHON_EXE) + f" -m streamlit run \"{_STREAMLIT_APP}\" --server.port 8501 --server.headless true",
        "label": "Streamlit UI (8501)",
        "start_at": "08:40",
    },
}

# ── 节假日简易判断(仅排除周末，完整版需接入交易日历) ──
def is_trading_day() -> bool:
    today = datetime.now()
    return today.weekday() < 5


def is_in_time_window(start: str, end: str) -> bool:
    now = datetime.now().strftime('%H:%M')
    return start <= now <= end


def is_past_time(t: str) -> bool:
    return datetime.now().strftime('%H:%M') >= t


def time_diff_seconds(target: str) -> float:
    """计算距离目标时间的秒数"""
    now = datetime.now()
    th, tm = map(int, target.split(':'))
    target_dt = now.replace(hour=th, minute=tm, second=0, microsecond=0)
    if target_dt < now:
        target_dt = target_dt.replace(day=now.day + 1)
    return (target_dt - now).total_seconds()


# ════════════════════════════════════════════════════════════════
# 子进程管理
# ════════════════════════════════════════════════════════════════
class ProcessManager:
    def __init__(self):
        self._processes: Dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def start(self, name: str, cmd: str) -> bool:
        with self._lock:
            if name in self._processes and self._processes[name].poll() is None:
                log.info(f"  [跳过] {name} 已在运行中")
                return False
            try:
                proc = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=str(BASE_DIR),
                )
                self._processes[name] = proc
                log.info(f"  [启动] {name} (PID={proc.pid})")
                return True
            except Exception as e:
                log.error(f"  [失败] {name}: {e}")
                return False

    def stop(self, name: str):
        with self._lock:
            proc = self._processes.pop(name, None)
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                log.info(f"  [停止] {name}")

    def stop_all(self):
        with self._lock:
            for name in list(self._processes.keys()):
                self.stop(name)

    def check_alive(self) -> List[str]:
        alive = []
        with self._lock:
            for name, proc in list(self._processes.items()):
                if proc.poll() is None:
                    alive.append(name)
                else:
                    self._processes.pop(name, None)
        return alive


# ════════════════════════════════════════════════════════════════
# 命令执行器
# ════════════════════════════════════════════════════════════════
def run_command(cmd: str, timeout: int = 120, dry_run: bool = False) -> int:
    if dry_run:
        log.info(f"  [DRY-RUN] {cmd[:120]}...")
        return 0

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(BASE_DIR),
        )
        # 只输出关键行
        for line in result.stdout.splitlines()[-10:]:
            if any(k in line for k in ['✅', '❌', '完成', '错误', 'ERROR', 'OK', '耗时']):
                log.info(f"    {line.strip()}")
        if result.returncode != 0:
            log.warning(f"    退出码={result.returncode}")
            if result.stderr:
                err_lines = result.stderr.strip().splitlines()
                for l in err_lines[-3:]:
                    log.warning(f"    stderr: {l}")
        return result.returncode
    except subprocess.TimeoutExpired:
        log.warning(f"  [超时] {cmd[:100]}... ({timeout}s)")
        return -1
    except Exception as e:
        log.error(f"  [异常] {e}")
        return -1


# ════════════════════════════════════════════════════════════════
# 主调度器
# ════════════════════════════════════════════════════════════════
class TradingHoursMaster:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.pm = ProcessManager()
        self.executed_slots: set = set()
        self._running = True

    def _slot_key(self, at_time: str) -> str:
        return f"{datetime.now().strftime('%Y%m%d')}_{at_time}"

    def execute_slot(self, at_time: str, label: str, commands: List[str], timeout: int):
        """执行一个时间窗口的任务"""
        slot = self._slot_key(at_time)
        if slot in self.executed_slots:
            return
        self.executed_slots.add(slot)

        log.info(f"\n{'═'*60}")
        log.info(f"  ⏰ {at_time} — {label}")
        log.info(f"{'═'*60}")

        for i, cmd in enumerate(commands, 1):
            log.info(f"  [{i}/{len(commands)}] {cmd.split(' --')[0].split('python')[-1].strip() if 'python' in cmd else cmd[:80]}")
            run_command(cmd, timeout=timeout, dry_run=self.dry_run)
            if i < len(commands):
                time.sleep(2)  # 命令间短暂间隔

        # 09:25 额外启动持续运行的子进程
        if at_time == "09:25":
            self._start_persistent_modules()

        log.info(f"  ✅ {label} 完成")

    def _start_persistent_modules(self):
        """启动需要持续运行的模块(子进程)"""
        log.info(f"\n  ── 启动持续运行模块 ──")
        for name, cfg in START_MODULES.items():
            # 只在对应时间点启动
            if is_past_time(cfg["start_at"]) or is_in_time_window("09:25", "09:30"):
                self.pm.start(name, cfg["cmd"])
                time.sleep(3)

    def _catchup_missed_slots(self, now_time: str):
        """迟到启动时，一次性补执行 08:40-当前时间 之间已过但未执行的窗口"""
        for at_time, label, commands, timeout in TRADING_SCHEDULE:
            if at_time >= now_time:
                break  # 后面的还没到，不执行
            slot = self._slot_key(at_time)
            if slot not in self.executed_slots:
                self.execute_slot(at_time, label, commands, timeout)

    def check_time_and_execute(self):
        """检查当前时间并执行对应任务"""
        now_time = datetime.now().strftime('%H:%M')

        for at_time, label, commands, timeout in TRADING_SCHEDULE:
            if at_time == "09:25":
                # 09:25 特殊处理:如果已过 09:25 但未执行过,在下一个检查点执行
                slot = self._slot_key(at_time)
                if slot not in self.executed_slots and now_time >= at_time:
                    self.execute_slot(at_time, label, commands, timeout)
            elif abs(_minutes_between(now_time, at_time)) <= 1:
                self.execute_slot(at_time, label, commands, timeout)

    def run_full_cycle(self):
        """完整的交易时段循环(从当前时间到15:30)"""
        log.info("=" * 60)
        log.info("  交易时段全模块自启动主调度器 v1.0")
        log.info(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log.info(f"  Python:   {PYTHON_EXE}")
        log.info(f"  主系统:   {MAIN_SCRIPT}")
        log.info("=" * 60)

        if not is_trading_day():
            log.info("\n  ⚠️ 今日非交易日(周末)，退出调度")
            return

        # 迟到启动补执行: 一次性补齐所有已过但未执行的窗口
        now_time = datetime.now().strftime('%H:%M')
        self._catchup_missed_slots(now_time)

        end_time = dtime(15, 30)
        shutdown_requested = False

        def _signal_handler(sig, frame):
            nonlocal shutdown_requested
            log.info("\n  收到终止信号，正在优雅关闭...")
            shutdown_requested = True

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        # 主循环
        last_check_minute = -1
        while self._running and not shutdown_requested:
            now = datetime.now()
            now_minute = now.minute

            # 超过15:30自动退出
            if now.time() > end_time:
                log.info(f"\n  ⏰ 已超过 15:30，调度器自动退出")
                break

            # 每分钟检查一次
            if now_minute != last_check_minute:
                last_check_minute = now_minute

                # 健康检查:确认子进程存活
                alive = self.pm.check_alive()
                if alive and now_minute % 5 == 0:  # 每5分钟报告一次
                    log.info(f"  [心跳] 活跃子进程: {', '.join(alive)}")

                self.check_time_and_execute()

            time.sleep(30)  # 30秒检查间隔

        # 清理
        log.info("\n  正在关闭所有子进程...")
        self.pm.stop_all()
        log.info("  调度器已退出")

    def run_once(self):
        """只执行当前时间点对应的任务一次"""
        log.info(f"  单次执行模式 — {datetime.now().strftime('%H:%M')}")

        if not is_trading_day():
            log.info("  非交易日，仅执行系统检查")
            run_command(_make_cmd(PYTHON_EXE, _MAIN) + " --check", dry_run=self.dry_run)
            return

        executed = False
        now_time = datetime.now().strftime('%H:%M')

        for at_time, label, commands, timeout in TRADING_SCHEDULE:
            if now_time >= at_time and self._slot_key(at_time) not in self.executed_slots:
                self.execute_slot(at_time, label, commands, timeout)
                executed = True
                break

        if not executed:
            log.info("  当前无匹配的时间窗口任务。")
            log.info("  执行基础健康检查...")
            run_command(_make_cmd(PYTHON_EXE, _MAIN) + " --check", dry_run=self.dry_run)


def _minutes_between(a: str, b: str) -> int:
    """两个 HH:MM 时间的分钟差"""
    ah, am = map(int, a.split(':'))
    bh, bm = map(int, b.split(':'))
    return (ah * 60 + am) - (bh * 60 + bm)


# ════════════════════════════════════════════════════════════════
# 入口
# ════════════════════════════════════════════════════════════════
def main():
    import argparse
    parser = argparse.ArgumentParser(description='交易时段全模块自启动主调度器')
    parser.add_argument('--once', action='store_true', help='只执行当前时间点的任务一次')
    parser.add_argument('--dry-run', action='store_true', help='试运行(不实际执行命令)')
    parser.add_argument('--status', action='store_true', help='显示调度状态')
    args = parser.parse_args()

    if args.status:
        print("\n  交易时段调度器状态")
        print("  " + "=" * 40)
        print(f"  当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  是否交易日: {'是' if is_trading_day() else '否(周末)'}")
        print(f"  主系统: {MAIN_SCRIPT}")
        print(f"  Python: {PYTHON_EXE}")
        print(f"  报告目录: {LOG_DIR}")
        print(f"\n  已注册时间窗口:")
        for at_time, label, commands, timeout in TRADING_SCHEDULE:
            n_cmds = len(commands)
            status = "✅ 已过" if datetime.now().strftime('%H:%M') >= at_time else "⏳ 待执行"
            print(f"    {at_time}  {label:12s} ({n_cmds}条命令) {status}")
        print(f"\n  持续运行模块:")
        for name, cfg in START_MODULES.items():
            print(f"    {cfg['start_at']}  {cfg['label']}")
        return

    master = TradingHoursMaster(dry_run=args.dry_run)

    if args.once:
        master.run_once()
    else:
        master.run_full_cycle()


if __name__ == '__main__':
    main()
