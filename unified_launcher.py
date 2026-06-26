# -*- coding: utf-8 -*-
"""
量化交易系统 - 统一启动脚本 v1.0
Author: yuppiez

功能：一次性启动所有交易模块
- 股票实时监控
- 期货期权扫描
- 逆回购管理
- 风险评估

使用方法：
    python unified_launcher.py
"""

import os
import sys
import time
import threading
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# 设置控制台编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ---- 日志配置 ----
LOG_DIR = Path(__file__).parent / "trade_logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(
            LOG_DIR / f'unified_launcher_{datetime.now():%Y%m%d}.log',
            encoding='utf-8'
        ),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('unified_launcher')


class ModuleLauncher:
    """模块启动器"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.modules = {}
        self.threads = []
    
    def register_module(self, name, script, args="", interval=60):
        """注册交易模块"""
        self.modules[name] = {
            "script": script,
            "args": args,
            "interval": interval,
            "running": False,
            "process": None
        }
        logger.info(f"✅ 已注册模块: {name}")
    
    def run_module(self, name):
        """运行单个模块（循环执行）"""
        module = self.modules[name]
        script_path = self.base_dir / module["script"]
        
        if not script_path.exists():
            logger.warning(f"⚠️  脚本不存在: {script_path}")
            return
        
        logger.info(f"🚀 启动模块: {name}")
        
        while True:
            try:
                logger.info(f"▶️  执行模块: {name}")
                
                cmd = [sys.executable, str(script_path)]
                if module["args"]:
                    cmd.extend(module["args"].split())
                
                process = subprocess.run(
                    cmd,
                    cwd=self.base_dir,
                    timeout=module["interval"] * 0.8  # 预留20%时间缓冲
                )
                
                logger.info(f"✓ 模块 {name} 执行完成 (退出码: {process.returncode})")
                
            except subprocess.TimeoutExpired:
                logger.warning(f"⏱️  模块 {name} 执行超时，重新启动")
            except KeyboardInterrupt:
                logger.info(f"⏹️  用户中断模块: {name}")
                break
            except Exception as e:
                logger.error(f"❌ 模块 {name} 执行出错: {e}")
            
            # 等待下一个周期
            logger.info(f"⏳ {module['interval']}秒后再次执行 {name}...")
            time.sleep(module["interval"])
    
    def start_all(self):
        """启动所有模块"""
        print("=" * 80)
        print("🎯 量化交易系统 - 统一启动器 v1.0")
        print("=" * 80)
        print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📂 工作目录: {self.base_dir}")
        print("-" * 80)
        print("\n📋 已注册模块列表:")
        print("=" * 80)
        for name, info in self.modules.items():
            print(f"  - {name}: {info['script']} (每 {info['interval']}秒)")
        
        print("\n" + "=" * 80)
        print("🔥 开始并行启动所有模块...")
        print("=" * 80)
        
        # 启动线程
        for name in self.modules.keys():
            thread = threading.Thread(
                target=self.run_module,
                args=(name,),
                daemon=True,
                name=name
            )
            self.threads.append(thread)
            thread.start()
            time.sleep(1)  # 错开启动时间
        
        print("\n✅ 所有模块已启动！")
        print("💡 按 Ctrl+C 停止所有模块")
        print("=" * 80)
        
        try:
            # 保持主线程运行
            while True:
                time.sleep(1)
                # 检查模块状态
                for thread in self.threads:
                    if not thread.is_alive():
                        logger.warning(f"⚠️  模块 {thread.name} 已退出，尝试重启")
                        new_thread = threading.Thread(
                            target=self.run_module,
                            args=(thread.name,),
                            daemon=True,
                            name=thread.name
                        )
                        new_thread.start()
                        self.threads.remove(thread)
                        self.threads.append(new_thread)
        
        except KeyboardInterrupt:
            print("\n\n" + "=" * 80)
            print("⏹️  收到停止信号，正在关闭所有模块...")
            print("=" * 80)
            logger.info("所有模块已停止")


def main():
    """主函数"""
    launcher = ModuleLauncher()
    launcher.start_all()


if __name__ == "__main__":
    main()
