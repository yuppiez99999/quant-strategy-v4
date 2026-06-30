"""
统一配置中心 (ConfigHub) v1.0

合并 portfolio.yaml + settings.yaml + positions.json 为统一配置访问层。
支持运行时热重载、动态阈值、标的级别完整交易参数查询。

用法:
    hub = ConfigHub()
    portfolio = hub.get_portfolio()
    params = hub.get_trading_params('688041.SH')
    hub.hot_reload()  # 运行时重载配置
"""

import os
import json
import yaml
import copy
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AssetParams:
    """单个标的的完整交易参数"""
    code: str
    name: str
    category: str
    category_name: str
    target_weight: float
    risk_weight: float
    shares: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    current_value: float = 0.0
    stop_loss_pct: float = -0.08      # 默认 -8%
    take_profit_pct: float = 0.20     # 默认 +20%
    ml_signal_threshold: float = 0.55  # ML信号阈值
    max_position_pct: float = 0.15     # 最大仓位上限
    enabled: bool = True


@dataclass
class PortfolioConfig:
    """统一投资组合配置"""
    total_capital: float = 0.0
    cash: float = 0.0
    total_value: float = 0.0
    annual_target_return: float = 0.15
    max_drawdown: float = 0.15
    categories: Dict[str, Dict] = field(default_factory=dict)
    assets: Dict[str, AssetParams] = field(default_factory=dict)
    data_source_priority: List[str] = field(default_factory=list)
    report_config: Dict = field(default_factory=dict)
    trading_config: Dict = field(default_factory=dict)
    monitoring_config: Dict = field(default_factory=dict)


class ConfigHub:
    """统一配置中心

    合并加载 portfolio.yaml、settings.yaml、positions.json，
    提供统一的标的级别完整交易参数查询接口。
    """

    def __init__(self, config_dir: str = None, base_dir: str = None):
        """
        Args:
            config_dir: 配置文件目录，默认自动推断
            base_dir: 项目根目录
        """
        if config_dir is None:
            if base_dir is None:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_dir = os.path.join(base_dir, 'config')
        self.config_dir = config_dir
        self.base_dir = base_dir or os.path.dirname(config_dir)
        self._portfolio: PortfolioConfig = PortfolioConfig()
        self._load_timestamp: Optional[datetime] = None
        self._file_mtimes: Dict[str, float] = {}
        self._signal_auditor = None  # 延迟注入 SignalAuditor
        self._loaded = False
        self._load_all()

    # ── 加载逻辑 ──────────────────────────────────────────

    def _load_all(self) -> None:
        """加载所有配置文件并合并"""
        portfolio_raw = self._load_yaml('portfolio.yaml')
        settings_raw = self._load_yaml('settings.yaml')
        positions_raw = self._load_json('positions.json')

        self._portfolio = PortfolioConfig()

        # 1. 加载全局参数 (portfolio.yaml)
        if portfolio_raw:
            global_cfg = portfolio_raw.get('global', {})
            capital = global_cfg.get('capital', {})
            self._portfolio.total_capital = capital.get('total', 0)
            targets = global_cfg.get('targets', {})
            self._portfolio.annual_target_return = targets.get('annual_return', 0.15)
            self._portfolio.max_drawdown = targets.get('max_drawdown', 0.15)

            self._portfolio.categories = portfolio_raw.get('categories', {})
            assets_raw = portfolio_raw.get('assets', [])

            # 构建资产映射
            for a in assets_raw:
                code = a.get('code', '')
                cat = a.get('category', '')
                cat_info = self._portfolio.categories.get(cat, {})
                self._portfolio.assets[code] = AssetParams(
                    code=code,
                    name=a.get('name', code),
                    category=cat,
                    category_name=cat_info.get('name', cat),
                    target_weight=a.get('target_weight', 0.0),
                    risk_weight=a.get('risk_weight', 0.0),
                )

        # 2. 加载数据源优先级 (settings.yaml)
        if settings_raw:
            ds = settings_raw.get('data_sources', {})
            fallback = ds.get('fallback_order', [])
            if fallback:
                self._portfolio.data_source_priority = list(fallback)

            self._portfolio.report_config = settings_raw.get('report', {})
            self._portfolio.trading_config = settings_raw.get('trading', {})
            self._portfolio.monitoring_config = settings_raw.get('monitoring', {})

        # 3. 合并 positions.json（实际持仓/现金）
        if positions_raw:
            self._portfolio.cash = positions_raw.get('cash', 0)
            self._portfolio.total_value = positions_raw.get('total_value', 0)
            positions = positions_raw.get('positions', {})

            for code, pos in positions.items():
                if code in self._portfolio.assets:
                    self._portfolio.assets[code].shares = pos.get('shares', 0)
                    self._portfolio.assets[code].avg_cost = pos.get('avg_cost', 0.0)
                else:
                    # 新建条目（仅 positions.json 中有而 portfolio.yaml 中无）
                    self._portfolio.assets[code] = AssetParams(
                        code=code,
                        name=pos.get('name', code),
                        category=pos.get('category', 'unknown'),
                        category_name='未知',
                        target_weight=pos.get('target_weight', 0.0),
                        shares=pos.get('shares', 0),
                        avg_cost=pos.get('avg_cost', 0.0),
                    )

            # 更新价格
            prices = positions_raw.get('prices', {})
            for code, price in prices.items():
                if code in self._portfolio.assets:
                    asset = self._portfolio.assets[code]
                    asset.current_price = float(price)
                    if asset.shares > 0:
                        asset.current_value = asset.shares * asset.current_price

        # 4. 加载可选的止损止盈配置
        sl_config = self._load_yaml('stop_loss_rules_auto.yaml')
        if sl_config:
            rules = sl_config.get('rules', sl_config) if isinstance(sl_config, dict) else {}
            for code, rule in (rules.items() if isinstance(rules, dict) else []):
                if code in self._portfolio.assets:
                    if isinstance(rule, dict):
                        self._portfolio.assets[code].stop_loss_pct = float(
                            rule.get('stop_loss', rule.get('止损位', -0.08))
                        )
                        self._portfolio.assets[code].take_profit_pct = float(
                            rule.get('take_profit', rule.get('止盈位', 0.20))
                        )

        # 记录文件修改时间用于热重载检测
        self._update_file_mtimes()
        self._load_timestamp = datetime.now()
        self._loaded = True

        asset_count = len(self._portfolio.assets)
        logger.info(
            f"[ConfigHub] 已加载 {asset_count} 个标的, "
            f"总资金: {self._portfolio.total_capital:,.0f}, "
            f"数据源层级: {' > '.join(self._portfolio.data_source_priority[:3])}"
        )

    def _load_yaml(self, filename: str) -> Optional[Dict]:
        """安全加载 YAML 文件"""
        path = os.path.join(self.config_dir, filename)
        if not os.path.exists(path):
            logger.debug(f"[ConfigHub] {filename} 不存在，跳过")
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"[ConfigHub] 加载 {filename} 失败: {e}")
            return None

    def _load_json(self, filename: str) -> Optional[Dict]:
        """安全加载 JSON 文件"""
        path = os.path.join(self.config_dir, filename)
        if not os.path.exists(path):
            logger.debug(f"[ConfigHub] {filename} 不存在，跳过")
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[ConfigHub] 加载 {filename} 失败: {e}")
            return None

    def _update_file_mtimes(self) -> None:
        """更新所有配置文件的修改时间戳"""
        for fname in ['portfolio.yaml', 'settings.yaml', 'positions.json',
                       'stop_loss_rules_auto.yaml']:
            path = os.path.join(self.config_dir, fname)
            if os.path.exists(path):
                self._file_mtimes[path] = os.path.getmtime(path)

    # ── 查询接口 ──────────────────────────────────────────

    def get_portfolio(self) -> PortfolioConfig:
        """获取统一投资组合配置（只读副本）"""
        return copy.deepcopy(self._portfolio)

    def get_asset(self, code: str) -> Optional[AssetParams]:
        """获取单个标的的完整参数"""
        return self._portfolio.assets.get(code)

    def get_trading_params(self, code: str) -> Optional[Dict[str, Any]]:
        """获取单个标的的完整交易参数字典"""
        asset = self._portfolio.assets.get(code)
        if not asset:
            return None

        # 动态阈值：如果 SignalAuditor 可用，使用其推荐阈值
        ml_threshold = asset.ml_signal_threshold
        if self._signal_auditor:
            try:
                dynamic_threshold = self._signal_auditor.get_optimal_threshold(code)
                if dynamic_threshold is not None:
                    ml_threshold = dynamic_threshold
            except Exception:
                pass

        return {
            'code': asset.code,
            'name': asset.name,
            'category': asset.category,
            'category_name': asset.category_name,
            'target_weight': asset.target_weight,
            'risk_weight': asset.risk_weight,
            'shares': asset.shares,
            'avg_cost': asset.avg_cost,
            'current_price': asset.current_price,
            'current_value': asset.current_value,
            'stop_loss_pct': asset.stop_loss_pct,
            'take_profit_pct': asset.take_profit_pct,
            'ml_signal_threshold': ml_threshold,
            'max_position_pct': asset.max_position_pct,
            'enabled': asset.enabled,
            # 衍生数据
            'position_pct': (asset.current_value / self._portfolio.total_value
                             if self._portfolio.total_value > 0 else 0),
            'unrealized_pnl': ((asset.current_price - asset.avg_cost) * asset.shares
                               if asset.shares > 0 and asset.current_price > 0 else 0),
            'unrealized_pnl_pct': ((asset.current_price - asset.avg_cost) / asset.avg_cost
                                    if asset.avg_cost > 0 else 0),
        }

    def get_assets_by_category(self, category: str) -> List[AssetParams]:
        """按板块获取标的列表"""
        return [a for a in self._portfolio.assets.values() if a.category == category]

    def get_all_asset_codes(self) -> List[str]:
        """获取所有标的代码列表"""
        return list(self._portfolio.assets.keys())

    def get_category_weights(self) -> Dict[str, Dict[str, Any]]:
        """获取各板块的配置权重和实际权重"""
        result = {}
        for cat, info in self._portfolio.categories.items():
            assets = self.get_assets_by_category(cat)
            target_w = info.get('weight', 0)
            actual_w = sum(
                a.current_value / self._portfolio.total_value
                for a in assets
                if self._portfolio.total_value > 0 and a.current_value > 0
            )
            result[cat] = {
                'name': info.get('name', cat),
                'target_weight': target_w,
                'actual_weight': actual_w,
                'deviation': actual_w - target_w,
                'asset_count': len(assets),
            }
        return result

    def get_data_source_label(self) -> str:
        """获取数据源层级标签（用于报告中显示）"""
        priorities = {
            0: '🟢', 1: '🟡', 2: '🟠', 3: '🔴', 4: '⚫', 5: '⚪'
        }
        labels = [f"{priorities.get(i, '➖')} {ds}" for i, ds in
                  enumerate(self._portfolio.data_source_priority[:5])]
        return ' > '.join(labels) if labels else '未配置'

    def get_summary(self) -> Dict[str, Any]:
        """获取配置摘要（用于UI展示）"""
        return {
            'total_capital': self._portfolio.total_capital,
            'cash': self._portfolio.cash,
            'total_value': self._portfolio.total_value,
            'asset_count': len(self._portfolio.assets),
            'category_count': len(self._portfolio.categories),
            'annual_target_return': self._portfolio.annual_target_return,
            'max_drawdown': self._portfolio.max_drawdown,
            'data_source_depth': len(self._portfolio.data_source_priority),
            'primary_source': (self._portfolio.data_source_priority[0]
                               if self._portfolio.data_source_priority else 'unknown'),
            'last_loaded': self._load_timestamp.isoformat() if self._load_timestamp else None,
        }

    # ── 写入接口 ──────────────────────────────────────────

    def update_positions(self, positions: Dict[str, Dict]) -> bool:
        """更新持仓信息（同时更新内存和 positions.json）

        Args:
            positions: {code: {shares: int, avg_cost: float, price: float, ...}, ...}
        """
        # 更新内存
        prices = {}
        for code, pos in positions.items():
            if code in self._portfolio.assets:
                asset = self._portfolio.assets[code]
                asset.shares = pos.get('shares', asset.shares)
                asset.avg_cost = pos.get('avg_cost', asset.avg_cost)
                price = pos.get('price', pos.get('current_price', 0))
                asset.current_price = float(price) if price else 0
                if asset.shares > 0 and asset.current_price > 0:
                    asset.current_value = asset.shares * asset.current_price
                prices[code] = asset.current_price

        # 重新计算总价值
        total_value = self._portfolio.cash + sum(
            a.current_value for a in self._portfolio.assets.values() if a.current_value > 0
        )
        self._portfolio.total_value = total_value

        # 写入 JSON
        positions_json = {
            'positions': {
                code: {
                    'shares': self._portfolio.assets[code].shares,
                    'avg_cost': self._portfolio.assets[code].avg_cost,
                    'category': self._portfolio.assets[code].category,
                    'target_weight': self._portfolio.assets[code].target_weight,
                    'name': self._portfolio.assets[code].name,
                }
                for code in self._portfolio.assets
            },
            'cash': self._portfolio.cash,
            'total_value': self._portfolio.total_value,
            'prices': prices,
            'last_updated': datetime.now().strftime('%Y-%m-%d'),
        }
        try:
            path = os.path.join(self.config_dir, 'positions.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(positions_json, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"[ConfigHub] 写入 positions.json 失败: {e}")
            return False

    # ── 热重载 ────────────────────────────────────────────

    def hot_reload(self) -> bool:
        """检测配置文件变更，有变更时自动重载。

        Returns:
            True 如果触发了重载，False 如果没有变更。
        """
        changed = False
        for fname in ['portfolio.yaml', 'settings.yaml', 'positions.json']:
            path = os.path.join(self.config_dir, fname)
            if not os.path.exists(path):
                continue
            current_mtime = os.path.getmtime(path)
            if current_mtime != self._file_mtimes.get(path, 0):
                changed = True
                break

        if changed:
            logger.info("[ConfigHub] 检测到配置文件变更，执行热重载...")
            self._load_all()
            return True

        return False

    def check_and_reload(self) -> bool:
        """热重载的别名，供外部统一调用"""
        return self.hot_reload()

    def force_reload(self) -> None:
        """强制重新加载所有配置"""
        self._load_all()
        logger.info("[ConfigHub] 强制重载完成")

    # ── SignalAuditor 集成 ────────────────────────────────

    def set_signal_auditor(self, auditor) -> None:
        """注入 SignalAuditor 用于动态阈值"""
        self._signal_auditor = auditor

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def load_timestamp(self) -> Optional[datetime]:
        return self._load_timestamp


# ── 全局单例 ──────────────────────────────────────────

_global_config_hub: Optional[ConfigHub] = None


def get_config_hub(config_dir: str = None, base_dir: str = None,
                   force_new: bool = False) -> ConfigHub:
    """获取全局 ConfigHub 单例"""
    global _global_config_hub
    if _global_config_hub is None or force_new:
        _global_config_hub = ConfigHub(config_dir=config_dir, base_dir=base_dir)
    return _global_config_hub


def reset_config_hub() -> None:
    """重置全局 ConfigHub 单例"""
    global _global_config_hub
    _global_config_hub = None
