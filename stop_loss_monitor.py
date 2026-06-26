# -*- coding: utf-8 -*-
"""
止损止盈监控模块 — 核心持仓风险控制

功能:
  - 实时监控标的距止损/止盈位的距离
  - 多级预警机制 (接近/触及/突破)
  - 支持动态基准价更新 (移动止盈)
  - 集成到每日报告系统

使用方式:
  from stop_loss_monitor import StopLossMonitor, generate_risk_alert_report

  monitor = StopLossMonitor('config/stop_loss_rules.yaml')
  alerts = monitor.check_all(quotes)  # quotes: {code: {'price': float, ...}}
  report = generate_risk_alert_report(alerts)
"""

import os
import yaml
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

if __name__ != '__main__':
    try:
        from wind_data_provider import get_quotes_batch
        _WIND_OK = True
    except ImportError:
        _WIND_OK = False


class AlertLevel(Enum):
    """预警级别"""
    NORMAL = "normal"         # 正常 (距触发位>5%)
    WARNING = "warning"       # 预警 (距触发位2%-5%)
    CRITICAL = "critical"     # 危险 (距触发位0%-2%)
    TRIGGERED = "triggered"   # 已触发 (突破止损/止盈位)


class RiskType(Enum):
    """风险类型"""
    STOP_LOSS = "stop_loss"       # 止损
    TAKE_PROFIT = "take_profit"   # 止盈



# 默认止损止盈规则 - 从 config/stop_loss_rules_token_20260621.yaml 加载
DEFAULT_RULES = {
    "version": "2.0-auto",
    "updated": "2026-06-04 08:30",
    "notes": "由RebalancingEngine从Excel自动生成的规则(覆盖基准仓)",
    "assets": [
        {
            "code": "600989",
            "name": "宝丰能源",
            "base_price": 26.54,
            "base_date": "2026-06-04",
            "stop_loss_pct": -12.8,
            "stop_loss_price": 23.14,
            "take_profit_pct": 40.2,
            "take_profit_price": 37.2,
            "monitoring_indicators": ["油价", "煤价", "烯烃价差"],
            "position_weight": 0.12,
            "risk_level": "medium",
            "trailing_stop": False,
            "notes": "煤化工龙头，关注油价波动"
        },
        {
            "code": "600276",
            "name": "恒瑞医药",
            "base_price": 50.47,
            "base_date": "2026-06-04",
            "stop_loss_pct": -17.3,
            "stop_loss_price": 41.74,
            "take_profit_pct": 20.1,
            "take_profit_price": 60.6,
            "monitoring_indicators": ["创新药审批进展", "出海订单"],
            "position_weight": 0.08,
            "risk_level": "low",
            "trailing_stop": False,
            "notes": "创新药龙头，关注FDA审批"
        },
        {
            "code": "300274",
            "name": "阳光电源",
            "base_price": 164.51,
            "base_date": "2026-06-04",
            "stop_loss_pct": -17.3,
            "stop_loss_price": 136.05,
            "take_profit_pct": 25.4,
            "take_profit_price": 206.3,
            "monitoring_indicators": ["储能订单", "毛利率变化"],
            "position_weight": 0.1,
            "risk_level": "high",
            "trailing_stop": False,
            "notes": "光伏+储能双龙头"
        },
        {
            "code": "601088",
            "name": "中国神华",
            "base_price": 44.98,
            "base_date": "2026-06-04",
            "stop_loss_pct": -8.7,
            "stop_loss_price": 41.07,
            "take_profit_pct": 20.1,
            "take_profit_price": 54.0,
            "monitoring_indicators": ["煤价", "分红政策"],
            "position_weight": 0.15,
            "risk_level": "low",
            "trailing_stop": False,
            "notes": "煤电一体化，高股息防守标的"
        },
        {
            "code": "002371",
            "name": "北方华创",
            "base_price": 669.0,
            "base_date": "2026-06-04",
            "stop_loss_pct": -21.6,
            "stop_loss_price": 524.5,
            "take_profit_pct": 20.0,
            "take_profit_price": 803.0,
            "monitoring_indicators": ["半导体周期", "地缘政治"],
            "position_weight": 0.03,
            "risk_level": "high",
            "trailing_stop": True,
            "notes": "国产半导体设备龙头"
        },
        {
            "code": "600995",
            "name": "南网储能",
            "base_price": 14.25,
            "base_date": "2026-06-04",
            "stop_loss_pct": -13.1,
            "stop_loss_price": 12.38,
            "take_profit_pct": 20.0,
            "take_profit_price": 17.1,
            "monitoring_indicators": [],
            "position_weight": 0.1,
            "risk_level": "medium",
            "trailing_stop": True,
            "notes": "来自再平衡计划 (减持)"
        },
        {
            "code": "600875",
            "name": "东方电气",
            "base_price": 36.05,
            "base_date": "2026-06-04",
            "stop_loss_pct": -8.5,
            "stop_loss_price": 32.99,
            "take_profit_pct": 30.1,
            "take_profit_price": 46.9,
            "monitoring_indicators": [],
            "position_weight": 0.1,
            "risk_level": "low",
            "trailing_stop": False,
            "notes": "来自再平衡计划 (维持)"
        },
        {
            "code": "600406",
            "name": "国电南瑞",
            "base_price": 25.83,
            "base_date": "2026-06-04",
            "stop_loss_pct": -8.7,
            "stop_loss_price": 23.58,
            "take_profit_pct": 20.0,
            "take_profit_price": 31.0,
            "monitoring_indicators": [],
            "position_weight": 0.1,
            "risk_level": "low",
            "trailing_stop": False,
            "notes": "来自再平衡计划 (维持)"
        },
        {
            "code": "000425",
            "name": "徐工机械",
            "base_price": 9.65,
            "base_date": "2026-06-04",
            "stop_loss_pct": -8.5,
            "stop_loss_price": 8.83,
            "take_profit_pct": 20.2,
            "take_profit_price": 11.6,
            "monitoring_indicators": [],
            "position_weight": 0.1,
            "risk_level": "low",
            "trailing_stop": False,
            "notes": "来自再平衡计划 (维持)"
        },
        {
            "code": "600089",
            "name": "特变电工",
            "base_price": 26.02,
            "base_date": "2026-06-04",
            "stop_loss_pct": -8.4,
            "stop_loss_price": 23.83,
            "take_profit_pct": 19.9,
            "take_profit_price": 31.2,
            "monitoring_indicators": [],
            "position_weight": 0.07,
            "risk_level": "low",
            "trailing_stop": False,
            "notes": "来自再平衡计划 (增持)"
        },
        {
            "code": "688017",
            "name": "绿的谐波",
            "base_price": 342.0,
            "base_date": "2026-06-04",
            "stop_loss_pct": 0.0,
            "stop_loss_price": 342.0,
            "take_profit_pct": 0,
            "take_profit_price": 0.0,
            "monitoring_indicators": [],
            "position_weight": 0.0,
            "risk_level": "low",
            "trailing_stop": True,
            "notes": "来自再平衡计划 (清仓)"
        },
        {
            "code": "518880",
            "name": "黄金ETF",
            "base_price": 9.46,
            "base_date": "2026-06-04",
            "stop_loss_pct": -8.7,
            "stop_loss_price": 8.64,
            "take_profit_pct": 9.9,
            "take_profit_price": 10.4,
            "monitoring_indicators": [],
            "position_weight": 0.05,
            "risk_level": "low",
            "trailing_stop": False,
            "notes": "来自再平衡计划 (增持)"
        },
        {
            "code": "510300",
            "name": "沪深300ETF",
            "base_price": 3.85,
            "base_date": "2026-06-04",
            "stop_loss_pct": -8.6,
            "stop_loss_price": 3.52,
            "take_profit_pct": 10.1,
            "take_profit_price": 4.24,
            "monitoring_indicators": [],
            "position_weight": 0.1,
            "risk_level": "low",
            "trailing_stop": False,
            "notes": "来自再平衡计划 (新增)"
        },
    ]
}




class StopLossMonitor:
    """止损止盈监控器"""

    def __init__(self, rules_file: Optional[str] = None):
        """
        Args:
            rules_file: 规则文件路径，默认使用内置规则
        """
        self.rules = self._load_rules(rules_file)
        self._asset_index = {a['code']: a for a in self.rules.get('assets', [])}
        self.settings = self.rules.get('global_settings', {})
        self.alerts_history: List[Dict] = []

        # 日志配置
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self._log = logging.getLogger('stop_loss')
        self._log.setLevel(logging.INFO)
        _fh = logging.FileHandler(
            os.path.join(log_dir, 'stop_loss_{:%Y%m%d}.log'.format(datetime.now())),
            encoding='utf-8'
        )
        _fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        if not self._log.handlers:
            self._log.addHandler(_fh)

    def _load_rules(self, rules_file: Optional[str]) -> Dict:
        """加载规则配置"""
        if rules_file and os.path.exists(rules_file):
            with open(rules_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)

        # 尝试从config目录加载
        default_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'config', 'stop_loss_rules.yaml'
        )
        if os.path.exists(default_path):
            with open(default_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)

        # 使用内置默认规则
        return DEFAULT_RULES

    def check_single(self, code: str, current_price: float,
                     high_price: Optional[float] = None,
                     low_price: Optional[float] = None) -> Dict:
        """
        检查单只标的的止损止盈状态。

        Args:
            code: 股票代码
            current_price: 当前价格
            high_price: 当日最高价 (用于移动止盈)
            low_price: 当日最低价

        Returns:
            {
                'code': str, 'name': str,
                'current_price': float, 'base_price': float,
                'stop_loss': {...}, 'take_profit': {...},
                'alert_level': AlertLevel,
                'pnl_pct': float, 'distance_to_sl': float, 'distance_to_tp': float,
                'action_suggestion': str, 'risk_score': float
            }
        """
        asset_rule = self._asset_index.get(code)

        if not asset_rule:
            return {
                'code': code, 'name': '未知',
                'current_price': current_price,
                'error': f'未找到 {code} 的止损止盈规则'
            }

        base_price = asset_rule['base_price']
        name = asset_rule['name']

        # 计算当前收益率
        pnl_pct = (current_price - base_price) / base_price * 100

        # 解析规则
        sl_pct = asset_rule['stop_loss_pct']
        sl_price = asset_rule['stop_loss_price']
        tp_pct = asset_rule['take_profit_pct']
        tp_price = asset_rule['take_profit_price']

        # 移动止盈调整 (如果启用)
        trailing_active = asset_rule.get('trailing_stop', False)
        effective_tp_price = tp_price
        effective_tp_pct = tp_pct

        if trailing_active and high_price and high_price > base_price:
            trailing_threshold = self.settings.get('enable_trailing_stop_pct', 10.0)
            peak_pct = (high_price - base_price) / base_price * 100

            # 如果从最高点回落超过阈值，更新止盈位
            if peak_pct >= trailing_threshold:
                drawdown_from_peak = (high_price - current_price) / high_price * 100
                if drawdown_from_peak >= trailing_threshold * 0.3:  # 回撤30%即提醒
                    effective_tp_price = high_price * (1 - trailing_threshold * 0.01)
                    effective_tp_pct = (effective_tp_price - base_price) / base_price * 100

        # 计算距离止损/止盈位的距离
        # 增加除零保护：如果止损/止盈价格为0，说明该规则不适用
        if sl_price and sl_price > 0:
            dist_to_sl = (current_price - sl_price) / sl_price * 100
        else:
            dist_to_sl = float('inf')  # 无止损规则，视为无限远
        
        if tp_price and tp_price > 0:
            dist_to_tp = (tp_price - current_price) / tp_price * 100 if current_price < tp_price else -(current_price - tp_price) / tp_price * 100
        else:
            dist_to_tp = float('inf')  # 无止盈规则，视为无限远

        # 确定预警级别
        alert_level = self._determine_alert_level(dist_to_sl, dist_to_tp)

        # 构建止损状态
        stop_loss_status = self._build_status(
            risk_type=RiskType.STOP_LOSS,
            trigger_price=sl_price,
            trigger_pct=sl_pct,
            current_price=current_price,
            distance=dist_to_sl,
            is_triggered=current_price <= sl_price
        )

        # 构建止盈状态
        take_profit_status = self._build_status(
            risk_type=RiskType.TAKE_PROFIT,
            trigger_price=effective_tp_price if trailing_active else tp_price,
            trigger_pct=effective_tp_pct if trailing_active else tp_pct,
            current_price=current_price,
            distance=dist_to_tp,
            is_triggered=current_price >= tp_price
        )

        # 操作建议
        action = self._generate_action(
            alert_level, pnl_pct, dist_to_sl, dist_to_tp,
            asset_rule, stop_loss_status, take_profit_status
        )

        # 风险评分 (0-100, 越高越危险)
        risk_score = self._calculate_risk_score(
            pnl_pct, dist_to_sl, asset_rule.get('risk_level', 'medium')
        )

        result = {
            'code': code,
            'name': name,
            'current_price': current_price,
            'base_price': base_price,
            'pnl_pct': pnl_pct,
            'stop_loss': stop_loss_status,
            'take_profit': take_profit_status,
            'alert_level': alert_level.value,
            'distance_to_sl_pct': round(dist_to_sl, 2),
            'distance_to_tp_pct': round(dist_to_tp, 2),
            'action_suggestion': action,
            'risk_score': risk_score,
            'monitoring_indicators': asset_rule.get('monitoring_indicators', []),
            'position_weight': asset_rule.get('position_weight', 0),
            'trailing_active': trailing_active,
        }

        # 记录到历史
        self.alerts_history.append({
            **result,
            'timestamp': datetime.now().isoformat()
        })

        # 写日志
        if alert_level in (AlertLevel.CRITICAL, AlertLevel.TRIGGERED):
            self._log.warning("[%s] %s %s 价格=%.2f PnL=%.2f%% 建议=%s",
                              alert_level.value.upper(), code, name, current_price, pnl_pct, action)
        else:
            self._log.info("[OK] %s %s 价格=%.2f PnL=%.2f%% 距止损=%.2f%% 距止盈=%.2f%%",
                           code, name, current_price, pnl_pct, dist_to_sl, dist_to_tp)

        return result

    def check_all(self, quotes: Dict[str, Dict]) -> List[Dict]:
        """
        批量检查所有标的的止损止盈状态。

        Args:
            quotes: 行情数据 {code: {'price': float, 'high': float|None, 'low': float|None}}

        Returns:
            各标的状态列表
        """
        results = []
        for asset in self.rules.get('assets', []):
            code = asset['code']
            if code not in quotes:
                results.append({
                    'code': code, 'name': asset['name'],
                    'error': '无行情数据',
                    'alert_level': 'unknown'
                })
                continue

            q = quotes[code]
            price = q.get('price', 0)
            if price <= 0:
                results.append({
                    'code': code, 'name': asset['name'],
                    'error': f'价格无效 ({price})',
                    'alert_level': 'unknown'
                })
                continue

            result = self.check_single(
                code=code,
                current_price=price,
                high_price=q.get('high'),
                low_price=q.get('low')
            )
            results.append(result)

        # 按风险评分排序 (高危在前)
        results.sort(key=lambda x: x.get('risk_score', 0), reverse=True)
        return results

    def _determine_alert_level(self, dist_to_sl: float, dist_to_tp: float) -> AlertLevel:
        """确定预警级别"""
        warning_th = abs(self.settings.get('warning_threshold_pct', 5.0))
        critical_th = abs(self.settings.get('critical_threshold_pct', 2.0))

        # 止损触发
        if dist_to_sl <= 0:
            return AlertLevel.TRIGGERED
        # 接近止损
        if dist_to_sl <= critical_th:
            return AlertLevel.CRITICAL
        if dist_to_sl <= warning_th:
            return AlertLevel.WARNING

        # 止盈触发 (反向)
        if dist_to_tp <= 0:
            return AlertLevel.TRIGGERED

        return AlertLevel.NORMAL

    def _build_status(self, risk_type: RiskType, trigger_price: float,
                      trigger_pct: float, current_price: float,
                      distance: float, is_triggered: bool) -> Dict:
        """构建止损/止盈状态详情"""
        label = '止损' if risk_type == RiskType.STOP_LOSS else '止盈'
        return {
            'type': risk_type.value,
            'label': label,
            'trigger_price': trigger_price,
            'trigger_pct': trigger_pct,
            'distance_pct': round(distance, 2),
            'is_triggered': is_triggered,
            'status_text': (
                f"已触发! 当前{label}位 ¥{trigger_price:.2f} ({trigger_pct:+.0f}%)"
                if is_triggered else
                f"距{label}位 {distance:+.2f}% (¥{trigger_price:.2f})"
            )
        }

    def _generate_action(self, alert_level: AlertLevel, pnl_pct: float,
                         dist_to_sl: float, dist_to_tp: float,
                         asset_rule: Dict, sl_status: Dict, tp_status: Dict) -> str:
        """生成操作建议"""
        if alert_level == AlertLevel.TRIGGERED:
            if sl_status['is_triggered']:
                return "立即执行止损! 价格已跌破止损位"
            if tp_status['is_triggered']:
                return "考虑分批止盈，可继续持有观察趋势"

        if alert_level == AlertLevel.CRITICAL:
            if dist_to_sl > 0 and dist_to_sl <= 2:
                return "危险! 非常接近止损位，准备减仓或设置条件单"

        if alert_level == AlertLevel.WARNING:
            if dist_to_sl > 0 and dist_to_sl <= 5:
                return f"预警: 距止损仅{dist_to_sl:.1f}%，关注走势准备应对"

        # 正常状态的建议
        if pnl_pct > 20:
            return "盈利良好，可考虑移动止盈锁定利润"
        if pnl_pct < -5:
            return "小幅浮亏，持续关注基本面变化"
        if pnl_pct > 0:
            return "持有观望，按计划执行策略"
        return "正常持有，定期监控"

    def _calculate_risk_score(self, pnl_pct: float, dist_to_sl: float,
                              risk_level: str) -> float:
        """计算综合风险评分 (0-100)"""
        score = 0.0

        # 基于PnL (亏损越多分数越高)
        if pnl_pct < -20:
            score += 40
        elif pnl_pct < -10:
            score += 25
        elif pnl_pct < -5:
            score += 15
        elif pnl_pct < 0:
            score += 5

        # 基于距止损位距离 (越近分数越高)
        if dist_to_sl <= 0:
            score += 40  # 已触发
        elif dist_to_sl <= 2:
            score += 30
        elif dist_to_sl <= 5:
            score += 15
        elif dist_to_sl <= 10:
            score += 5

        # 基于资产固有风险等级
        risk_multipliers = {'low': 0.8, 'medium': 1.0, 'high': 1.2}
        multiplier = risk_multipliers.get(risk_level, 1.0)
        score *= multiplier

        return min(100, max(0, score))


def generate_risk_alert_report(alerts: List[Dict], include_header: bool = True) -> str:
    """
    生成格式化的止损止盈预警报告。

    Args:
        alerts: check_all() 返回的结果列表
        include_header: 是否包含报告头

    Returns:
        格式化报告文本
    """
    lines = []

    if include_header:
        lines.append("=" * 80)
        lines.append("⚠️ 止损止盈风险监控报告")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        lines.append("")

    # 统计概览
    triggered_count = sum(1 for a in alerts if a.get('alert_level') == 'triggered')
    critical_count = sum(1 for a in alerts if a.get('alert_level') == 'critical')
    warning_count = sum(1 for a in alerts if a.get('alert_level') == 'warning')
    normal_count = sum(1 for a in alerts if a.get('alert_level') == 'normal')
    error_count = sum(1 for a in alerts if a.get('alert_level') == 'unknown')

    lines.append("📊 风险概览")
    lines.append("-" * 60)
    lines.append(f"  监控标的总数: {len(alerts)}")
    lines.append(f"  🔴 已触发: {triggered_count}")
    lines.append(f"  🟠 危险: {critical_count}")
    lines.append(f"  🟡 预警: {warning_count}")
    lines.append(f"  🟢 正常: {normal_count}")
    if error_count > 0:
        lines.append(f"  ⚪ 数据异常: {error_count}")
    lines.append("")

    # 详细状态表
    lines.append("📋 各标的状态详情")
    lines.append("-" * 80)

    level_icons = {
        'normal': '🟢',
        'warning': '🟡',
        'critical': '🟠',
        'triggered': '🔴',
        'unknown': '⚪'
    }

    # 表头
    lines.append(
        f"{'状态':<6} {'名称':<10} {'代码':<8} {'现价':>8} "
        f"{'PnL':>7} {'止损位':>8} {'距止损':>8} {'止盈位':>8} {'距止盈':>8}"
    )
    lines.append("-" * 80)

    for a in alerts:
        icon = level_icons.get(a.get('alert_level', 'unknown'), '?')
        name = a.get('name', '?')[:8]
        code = a.get('code', '?')
        price = a.get('current_price', 0)
        pnl = a.get('pnl_pct', 0)
        sl_price = a.get('stop_loss', {}).get('trigger_price', 0)
        dist_sl = a.get('distance_to_sl_pct', 0)
        tp_price = a.get('take_profit', {}).get('trigger_price', 0)
        dist_tp = a.get('distance_to_tp_pct', 0)

        lines.append(
            f"{icon:<6} {name:<10} {code:<8} ¥{price:>7.2f} "
            f"{pnl:>+6.2f}% ¥{sl_price:>7.2f} {dist_sl:>+7.2f}% "
            f"¥{tp_price:>7.2f} {dist_tp:>+7.2f}%"
        )

    lines.append("")

    # 操作建议
    lines.append("🎯 操作建议")
    lines.append("-" * 60)

    triggered_alerts = [a for a in alerts if a.get('alert_level') == 'triggered']
    critical_alerts = [a for a in alerts if a.get('alert_level') == 'critical']
    warning_alerts = [a for a in alerts if a.get('alert_level') == 'warning']

    if triggered_alerts:
        lines.append("  🔴 需立即操作:")
        for a in triggered_alerts:
            lines.append(f"    • {a['name']}({a['code']}): {a.get('action_suggestion', '')}")

    if critical_alerts:
        lines.append("  🟠 高度警惕:")
        for a in critical_alerts:
            lines.append(f"    • {a['name']}({a['code']}): {a.get('action_suggestion', '')}")

    if warning_alerts:
        lines.append("  🟡 关注:")
        for a in warning_alerts:
            lines.append(f"    • {a['name']}({a['code']}): {a.get('action_suggestion', '')}")

    if not (triggered_alerts or critical_alerts or warning_alerts):
        lines.append("  ✅ 所有标的运行正常，无需紧急操作")

    lines.append("")

    # 监控指标提示
    lines.append("📌 重点监控指标")
    lines.append("-" * 60)
    indicators_shown = set()
    for a in alerts:
        for ind in a.get('monitoring_indicators', []):
            if ind not in indicators_shown:
                indicators_shown.add(ind)
    if indicators_shown:
        lines.append(f"  • {', '.join(sorted(indicators_shown))}")
    else:
        lines.append("  • 无特殊监控指标")
    lines.append("")

    # 综合风险评估
    lines.append("💎 综合风险评估")
    lines.append("-" * 60)
    valid_scores = [a.get('risk_score', 0) for a in alerts if 'risk_score' in a]
    if valid_scores:
        avg_risk = sum(valid_scores) / len(valid_scores)
        max_risk = max(valid_scores)

        if avg_risk >= 60:
            risk_overall = "🔴 高风险 — 组合整体面临较大回撤压力"
        elif avg_risk >= 30:
            risk_overall = "🟠 中等风险 — 部分标的需密切关注"
        else:
            risk_overall = "🟢 低风险 — 组合运行在安全范围内"

        lines.append(f"  平均风险评分: {avg_risk:.1f}/100")
        lines.append(f"  最高风险评分: {max_risk:.1f}/100 ({[a['name'] for a in alerts if a.get('risk_score', 0) == max_risk][0]})")
        lines.append(f"  总体评估: {risk_overall}")
    lines.append("")

    if include_header:
        lines.append("=" * 80)
        lines.append("提示: 本报告仅供参考，不构成投资建议")
        lines.append("     请结合市场环境和个人风险承受能力做出决策")
        lines.append("=" * 80)

    return '\n'.join(lines)


def save_default_rules(output_path: Optional[str] = None):
    """
    保存默认规则到YAML文件。

    Args:
        output_path: 输出路径，默认保存到 config/stop_loss_rules.yaml
    """
    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'config', 'stop_loss_rules.yaml'
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(DEFAULT_RULES, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"✅ 默认规则已保存至: {output_path}")
    return output_path


# ============================================================
# 快速测试入口
# ============================================================

if __name__ == '__main__':
    import sys
    import io

    # Windows控制台UTF-8编码修复
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("=" * 70)
    print("止损止盈监控模块 — 测试")
    print("=" * 70)

    monitor = StopLossMonitor()

    # 使用模拟数据测试 (覆盖权益组合+低风险理财)
    test_quotes = {
        # 核心宽基ETF
        '510300': {'price': 4.40},     # 沪深300ETF -4.3%
        '510500': {'price': 6.40},     # 中证500ETF -5.9%
        '512100': {'price': 3.00},     # 中证1000ETF -6.25%
        '588000': {'price': 1.10},     # 科创50ETF -8.3%
        '159915': {'price': 1.95},     # 创业板ETF -7.1%
        # 科技成长个股
        '688041': {'price': 175.00},   # 海光信息 -7.0%
        '300308': {'price': 1200.00},  # 中际旭创 -10.2% (接近止损)
        '300274': {'price': 148.00},   # 阳光电源 -6.5%
        '002371': {'price': 520.00},    # 北方华创 -11.7% (接近止损)
        '688017': {'price': 390.00},   # 绿的谐波 -9.2%
        '600276': {'price': 43.50},    # 恒瑞医药 -6.1%
        # 高端制造/基建
        '600089': {'price': 24.50},    # 特变电工 -5.9%
        '600875': {'price': 29.50},    # 东方电气 -6.2%
        '000425': {'price': 9.30},     # 徐工机械 -6.3%
        '600406': {'price': 23.80},    # 国电南瑞 -6.6%
        '600989': {'price': 20.50},    # 宝丰能源 -7.6%
        # 防御/红利
        '515180': {'price': 1.15},     # 中证红利ETF -4.2%
        '600036': {'price': 31.50},    # 招商银行 -6.0%
        '600900': {'price': 23.80},    # 长江电力 -4.8%
        '601088': {'price': 47.80},    # 中国神华 -5.8%
        # 商品/避险
        '518880': {'price': 8.50},     # 黄金ETF -5.1%
        # 低风险理财 - 短债基金
        '000105': {'price': 1.015},    # 易方达短债A -0.5%
        '000084': {'price': 1.018},    # 博时安盈短债A -0.2%
        # 低风险理财 - 信用债基金
        '000236': {'price': 1.065},    # 易方达信用债A -1.4%
        '000267': {'price': 1.055},    # 广发信用债A -2.3% (接近止损)
        # 低风险理财 - 可转债基金
        '340001': {'price': 1.26},     # 兴全可转债 -3.1%
        '001816': {'price': 1.20},     # 中欧可转债A -4.0%
        '040022': {'price': 1.22},     # 华安可转债A -2.4%
        # 低风险理财 - 红利/价值ETF
        '515080': {'price': 1.05},     # 中证红利ETF -4.5%
        '512890': {'price': 1.01},     # 红利低波ETF -3.8%
        '510030': {'price': 1.03},     # 沪深300价值ETF -4.6%
        # 低风险理财 - 增强型指数基金
        '000311': {'price': 1.72},     # 易方达沪深300增强 -4.4%
        '163407': {'price': 1.68},     # 兴全沪深300增强 -4.0%
    }

    print("\n测试数据 (模拟行情):")
    for code, q in test_quotes.items():
        print(f"  {code}: ¥{q['price']:.2f}")

    print("\n执行检查...")
    alerts = monitor.check_all(test_quotes)
    report = generate_risk_alert_report(alerts)

    print("\n" + report)

    # 保存规则文件
    print("\n是否保存默认规则到 config/stop_loss_rules.yaml? (y/n)")
    if len(sys.argv) > 1 and sys.argv[1] == '--save':
        save_default_rules()
