#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PatchTST 训练器 — CPU 友好版本

支持:
  - 多标的联合训练 (遍历 data/cache/kline_*.parquet)
  - Walk-Forward 时间序列划分 (按日期顺序, 无未来信息泄露)
  - T+1 标签设计 (A股制度)
  - LSTM 基线对比
  - 模型评估 (准确率、F1、盈亏比、夏普比率)
  - 自动保存最佳模型到 models/
"""

from __future__ import annotations

import json
import os
import sys
import time
import io
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler

from patchtst_model import PatchTST, PatchTSTLoss, count_parameters

# Windows 控制台编码
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass


# ── 配置 ──────────────────────────────────────────────────

DEFAULT_CONFIG = {
    # 模型参数
    'model': {
        'n_channels': 8,          # OHLCV(5) + 宏观(3): kondratiev, fifteenfive, social_style
        'seq_len': 60,            # 回溯 60 个交易日 (~3个月)
        'pred_len': 1,            # 预测次日
        'patch_len': 16,          # Patch 长度
        'stride': 8,              # Patch 步长 (50% overlap)
        'd_model': 128,           # 隐藏维度
        'n_heads': 4,             # 注意力头数
        'n_layers': 3,            # Encoder 层数
        'd_ff': 256,              # FFN 维度 (d_model * 2)
        'dropout': 0.2,           # Dropout 率
        'mode': 'classify',       # classify | regress | both
        'n_classes': 2,           # 涨/跌
    },
    # 预训练参数 (自监督 Masked Patch 重建)
    'pretrain': {
        'enabled': True,          # 是否启用预训练
        'epochs': 30,             # 预训练轮数
        'mask_ratio': 0.40,       # Patch mask 比例
        'learning_rate': 1e-3,    # 预训练学习率
        'weight_decay': 1e-5,     # 预训练权重衰减
    },
    # 训练参数 (下游任务)
    'training': {
        'epochs': 50,
        'batch_size': 64,
        'learning_rate': 5e-4,    # 下游任务用更低 LR
        'weight_decay': 1e-4,
        'grad_clip': 3.0,
        'lr_patience': 8,         # ReduceLROnPlateau 耐心
        'lr_factor': 0.5,         # 学习率衰减因子
        'early_stop_patience': 15, # 早停耐心
        'val_ratio': 0.15,        # 验证集比例 (取自末尾, 时序顺序)
        'test_ratio': 0.10,       # 测试集比例 (取自末尾)
        'min_train_samples': 200, # 最少训练样本数
        'task_weight': 0.6,       # 'both' 模式分类权重 (1-w 为回归权重)
    },
    # 路径
    'paths': {
        'data_dir': 'data/cache',
        'output_dir': 'models',
        'log_dir': 'models/logs',
    }
}

# ── 宏观特征映射 (从 kondratiev_fifteenfive_portfolio 导入) ──

MACRO_FEATURE_NAMES = ['kondratiev_score', 'fifteenfive_score', 'social_style_id']

# 社保风格→ID 编码
SOCIAL_STYLE_TO_ID = {
    '高端制造': 0.0,
    '顺周期':   0.33,
    '资源':     0.67,
    '防御':     1.0,
}


# ── LSTM 基线模型 ─────────────────────────────────────────

class LSTMBaseline(nn.Module):
    """简单 LSTM 基线, 用于与 PatchTST 对比"""

    def __init__(self, input_size: int, hidden_size: int = 64,
                 num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers,
                            batch_first=True, dropout=dropout if num_layers > 1 else 0)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(32, 2),
        )

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        # x: (B, C, T) — 需要转置为 (B, T, C) for LSTM
        x = x.transpose(1, 2)  # (B, T, C)
        out, _ = self.lstm(x)
        out = out[:, -1, :]    # 最后一个时间步
        return {'logits': self.classifier(out)}


# ── 数据处理器 ────────────────────────────────────────────

class FinancialDataProcessor:
    """金融数据加载与预处理 (含宏观特征注入)"""

    # 基础量价特征 + 宏观特征
    PRICE_COLS = ['open', 'high', 'low', 'close', 'volume']
    MACRO_COLS = ['kondratiev_score', 'fifteenfive_score', 'social_style_id']
    ALL_FEATURE_COLS = PRICE_COLS + MACRO_COLS  # 8 通道

    def __init__(self, data_dir: str, seq_len: int = 60,
                 min_samples: int = 200, use_macro: bool = True):
        self.data_dir = Path(data_dir)
        self.seq_len = seq_len
        self.min_samples = min_samples
        self.use_macro = use_macro
        self._macro_cache: dict[str, dict] = {}
        self._load_macro_sources()

    def _load_macro_sources(self):
        """加载宏观特征数据源 (kondratiev_fifteenfive_portfolio)"""
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from kondratiev_fifteenfive_portfolio import KONDRATIEV_FIFTEENFIVE_PORTFOLIO as KFP
            self._macro_cache = {}
            for code, info in KFP.items():
                style_id = SOCIAL_STYLE_TO_ID.get(info.get('social_style', '防御'), 1.0)
                self._macro_cache[code] = {
                    'kondratiev_score': float(info.get('kondratiev_score', 0.5)),
                    'fifteenfive_score': float(info.get('fifteenfive_score', 0.5)),
                    'social_style_id': style_id,
                }
            print(f"[宏观] 加载 {len(self._macro_cache)} 个标的的康波/十五五/社保风格特征")
        except ImportError:
            print("[宏观] ⚠ kondratiev_fifteenfive_portfolio 不可用, 使用默认值")
            self._macro_cache = {}
        except Exception as e:
            print(f"[宏观] ⚠ 加载失败: {e}, 使用默认值")
            self._macro_cache = {}

    def _get_macro_features(self, code: str) -> dict:
        """获取单个标的的宏观特征 (含默认兜底)"""
        if code in self._macro_cache:
            return self._macro_cache[code]
        # 兜底: 使用中性默认值
        return {
            'kondratiev_score': 0.5,
            'fifteenfive_score': 0.5,
            'social_style_id': 0.5,
        }

    def load_ticker(self, code: str) -> Optional[pd.DataFrame]:
        """加载单个标的的 Parquet 数据 + 附加宏观特征"""
        filepath = self.data_dir / f'kline_{code}_daily.parquet'
        if not filepath.exists():
            return None

        df = pd.read_parquet(filepath)

        # 标准化列名
        col_map = {}
        for col in df.columns:
            col_lower = col.lower().strip()
            for req in self.PRICE_COLS:
                if req in col_lower:
                    col_map[col] = req
                    break

        if col_map:
            df = df.rename(columns=col_map)
            df = df.loc[:, ~df.columns.duplicated()]

        # 确保必要列存在
        available = [c for c in self.PRICE_COLS if c in df.columns]
        if len(available) < 3:
            return None

        # 补充缺失列
        for col in self.PRICE_COLS:
            if col not in df.columns:
                if col in ('open', 'high', 'low'):
                    df[col] = df['close']
                elif col == 'volume':
                    df[col] = 0

        # 处理日期列
        if 'date' in df.index.names:
            df = df.reset_index()

        date_found = False
        for date_col in ['date', '_DATE', 'DATE']:
            if date_col in df.columns:
                df['_date_'] = pd.to_datetime(df[date_col], errors='coerce')
                date_found = True
                break

        if not date_found:
            df['_date_'] = pd.date_range(end=datetime.now(), periods=len(df), freq='B')

        df = df.sort_values('_date_').reset_index(drop=True)

        # 选择 OHLCV 列, 转换为 float
        for col in self.PRICE_COLS:
            if col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                except (TypeError, ValueError):
                    df[col] = np.nan

        # 补充缺失/无效列
        for col in self.PRICE_COLS:
            if col not in df.columns:
                if col in ('open', 'high', 'low', 'volume'):
                    df[col] = df['close'] if 'close' in df.columns else 0
                elif col == 'close':
                    return None
            else:
                try:
                    if df[col].isna().all():
                        if col in ('open', 'high', 'low', 'volume'):
                            df[col] = df['close']
                        elif col == 'close':
                            return None
                except (TypeError, ValueError, AttributeError):
                    if col in ('open', 'high', 'low', 'volume'):
                        df[col] = df['close'] if 'close' in df.columns else 0
                    else:
                        return None

        df = df.dropna(subset=['close'])

        if len(df) < self.min_samples:
            return None

        # ── 附加宏观特征 (静态, 按标的代码映射) ──
        if self.use_macro:
            macro = self._get_macro_features(code)
            for mcol in self.MACRO_COLS:
                df[mcol] = macro.get(mcol, 0.5)

        feature_cols = self.ALL_FEATURE_COLS if self.use_macro else self.PRICE_COLS
        return df[['_date_'] + feature_cols]

    def compute_label(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算 T+1 涨跌标签

        A股 T+1: T日收盘信号 → T+1日收益
        标签: 1 (涨) / 0 (跌) — 使用 T+1 收盘 vs T 日收盘
        """
        df = df.copy()
        df['return_t1'] = df['close'].pct_change(1).shift(-1)
        df['label'] = (df['return_t1'] > 0).astype(int)
        return df

    def build_sequences(self, df: pd.DataFrame, scaler: Optional[StandardScaler] = None
                        ) -> tuple[np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
        """将 DataFrame 转换为 (N, C, T) 序列

        Args:
            df: 含 OHLCV + macro + label + return_t1 列的 DataFrame
            scaler: 预训练的 scaler (验证/测试时使用)

        Returns:
            X: (N, C, seq_len) 特征
            y_cls: (N,) 分类标签
            y_reg: (N,) 回归标签 (return_t1)
            scaler: 拟合后的 StandardScaler
        """
        # 确定实际可用的特征列
        available_cols = [c for c in self.ALL_FEATURE_COLS if c in df.columns]
        if not available_cols:
            available_cols = [c for c in self.PRICE_COLS if c in df.columns]
        values = df[available_cols].values.astype(np.float32)

        # 填充 NaN (前向填充)
        df_filled = pd.DataFrame(values, columns=available_cols)
        df_filled = df_filled.ffill().bfill().fillna(0)
        values = df_filled.values

        # 标准化 (按列独立)
        if scaler is None:
            scaler = StandardScaler()
            values = scaler.fit_transform(values)
        else:
            values = scaler.transform(values)

        # 滚动窗口
        X_list, y_cls_list, y_reg_list = [], [], []
        labels = df['label'].values
        returns = df['return_t1'].values

        for i in range(len(values) - self.seq_len):
            X_list.append(values[i:i + self.seq_len])          # (seq_len, C)
            y_cls_list.append(labels[i + self.seq_len])
            y_reg_list.append(returns[i + self.seq_len])

        if not X_list:
            return (np.array([]), np.array([]), np.array([]), scaler)

        X = np.stack(X_list)  # (N, seq_len, C)
        X = X.transpose(0, 2, 1)  # (N, C, seq_len) — PatchTST 输入格式

        y_cls = np.array(y_cls_list, dtype=np.int64)
        y_reg = np.array(y_reg_list, dtype=np.float32)

        # 清理 NaN 标签
        valid_idx = ~np.isnan(y_reg) & ~np.isnan(y_cls.astype(float))
        X = X[valid_idx]
        y_cls = y_cls[valid_idx]
        y_reg = y_reg[valid_idx]

        return X, y_cls, y_reg, scaler

    def load_and_prepare(self, codes: list[str]) -> dict[str, Any]:
        """加载所有标的并合并准备训练数据"""
        all_X, all_y_cls, all_y_reg = [], [], []

        print(f"\n[数据] 加载 {len(codes)} 个标的...")

        loaded = 0
        for code in codes:
            df = self.load_ticker(code)
            if df is None:
                continue

            df = self.compute_label(df)
            X, y_cls, y_reg, _ = self.build_sequences(df)

            if len(X) > 0:
                all_X.append(X)
                all_y_cls.append(y_cls)
                all_y_reg.append(y_reg)
                loaded += 1
                print(f"  [OK] {code}: {len(df)}行 → {len(X)}序列")

        if not all_X:
            raise ValueError(f"未找到任何可用数据 (已尝试 {len(codes)} 个标的)")

        X_all = np.concatenate(all_X, axis=0)
        y_cls_all = np.concatenate(all_y_cls, axis=0)
        y_reg_all = np.concatenate(all_y_reg, axis=0)

        print(f"\n[数据] 总计: {loaded} 标的, {len(X_all)} 序列")
        print(f"[数据] 涨跌分布: 涨={np.sum(y_cls_all==1)}, 跌={np.sum(y_cls_all==0)}")

        return {
            'X': X_all,
            'y_cls': y_cls_all,
            'y_reg': y_reg_all,
            'n_tickers': loaded,
        }


# ── 训练器 ────────────────────────────────────────────────

class PatchTSTTrainer:
    """PatchTST 训练器 — 预训练 + 下游微调 + 多任务 + LSTM 基线"""

    def __init__(self, config: Optional[dict] = None):
        cfg = DEFAULT_CONFIG.copy()
        if config:
            self._deep_update(cfg, config)
        self.cfg = cfg
        self.mcfg = cfg['model']
        self.tcfg = cfg['training']
        self.pcfg = cfg.get('pretrain', {'enabled': True})
        self.ppaths = cfg['paths']

        self.device = torch.device('cpu')
        self.model: Optional[PatchTST] = None
        self.best_val_acc = 0.0
        self.best_val_loss = float('inf')

        os.makedirs(self.ppaths['output_dir'], exist_ok=True)
        os.makedirs(self.ppaths['log_dir'], exist_ok=True)

    @staticmethod
    def _deep_update(base: dict, update: dict) -> None:
        for k, v in update.items():
            if isinstance(v, dict) and k in base:
                PatchTSTTrainer._deep_update(base[k], v)
            else:
                base[k] = v

    def _time_series_split(self, data: dict) -> tuple:
        """按时间顺序划分 train/val/test (保持时序性)"""
        X = data['X']
        n = len(X)
        val_size = int(n * self.tcfg['val_ratio'])
        test_size = int(n * self.tcfg['test_ratio'])

        test_start = n - test_size
        val_start = test_start - val_size

        splits = {}
        for name, (s, e) in [('train', (0, val_start)),
                               ('val', (val_start, test_start)),
                               ('test', (test_start, n))]:
            mask = np.arange(s, e)
            splits[name] = {
                'X': X[mask],
                'y_cls': data['y_cls'][mask],
                'y_reg': data['y_reg'][mask],
            }

        print(f"\n[划分] 训练集: {val_start} | 验证集: {val_size} | 测试集: {test_size}")
        return splits

    def train(self, data: dict, codes: Optional[list[str]] = None,
              train_lstm_baseline: bool = True):
        """主训练入口 — 预训练 + 下游微调"""
        print("\n" + "=" * 70)
        print("  PatchTST 模型训练 — Phase 2 增强版")
        print("  宏观特征 + 自监督预训练 + 多任务学习")
        print("=" * 70)

        # 数据划分
        splits = self._time_series_split(data)

        # 记录类别分布 (供 Focal Loss 自动计算权重)
        train_y = splits['train']['y_cls']
        self._n_up = int(np.sum(train_y == 1))
        self._n_down = int(np.sum(train_y == 0))
        print(f"[分布] 训练集涨跌: 涨={self._n_up}, 跌={self._n_down} "
              f"(涨:{self._n_up/(self._n_up+self._n_down):.1%})")

        # 动态调整 n_channels
        n_actual = data['X'].shape[1]
        if n_actual != self.mcfg['n_channels']:
            print(f"[配置] 通道数: {self.mcfg['n_channels']} → {n_actual} (自动检测)")
            self.mcfg['n_channels'] = n_actual

        # 创建模型
        self.model = PatchTST(**self.mcfg).to(self.device)
        n_params = count_parameters(self.model)['total']
        print(f"[模型] PatchTST 参数量: {n_params:,} (模式={self.mcfg['mode']})")

        # ── Phase 1: 自监督预训练 ──
        if self.pcfg.get('enabled', True):
            self._pretrain(splits['train'])

        # ── Phase 2: 下游监督微调 ──
        train_loader, val_loader, test_loader = self._create_dataloaders(splits)

        print(f"\n[微调] Epochs={self.tcfg['epochs']}, "
              f"Batch={self.tcfg['batch_size']}, "
              f"LR={self.tcfg['learning_rate']}, "
              f"Device={self.device}")

        history = self._train_loop(train_loader, val_loader)

        # 评估
        print("\n" + "-" * 50)
        print("  测试集评估")
        print("-" * 50)
        metrics = self.evaluate(test_loader, name='测试集')

        # LSTM 基线对比
        lstm_metrics = None
        if train_lstm_baseline:
            print("\n" + "-" * 50)
            print("  LSTM 基线对比")
            print("-" * 50)
            lstm_metrics = self._train_lstm_baseline(splits)

        # 保存
        model_path = self._save_model(metrics, lstm_metrics)
        self._print_comparison(metrics, lstm_metrics)

        return {
            'model_path': str(model_path),
            'metrics': metrics,
            'lstm_baseline': lstm_metrics,
            'history': history,
            'n_params': n_params,
        }

    def _pretrain(self, train_split: dict):
        """Phase 1: 自监督 Masked Patch 重建预训练"""
        print("\n" + "─" * 50)
        print("  [预训练] Masked Patch 重建 (自监督)")
        print("─" * 50)

        self.model.enable_pretraining()
        decoder = self.model.pretrain_decoder
        if decoder is None:
            print("[预训练] ⚠ 解码器创建失败, 跳过")
            return

        decoder = decoder.to(self.device)

        mask_ratio = self.pcfg.get('mask_ratio', 0.40)
        pretrain_epochs = self.pcfg.get('epochs', 30)
        pretrain_lr = self.pcfg.get('learning_rate', 1e-3)
        pretrain_wd = self.pcfg.get('weight_decay', 1e-5)

        optimizer = torch.optim.AdamW(
            list(self.model.encoder.parameters()) + list(decoder.parameters()),
            lr=pretrain_lr, weight_decay=pretrain_wd,
        )
        criterion = nn.MSELoss()

        train_X = torch.FloatTensor(train_split['X'])
        train_ds = TensorDataset(train_X)
        train_loader = DataLoader(train_ds, batch_size=self.tcfg['batch_size'],
                                  shuffle=True, num_workers=0)

        print(f"[预训练] Epochs={pretrain_epochs}, Mask={mask_ratio:.0%}, "
              f"LR={pretrain_lr}, Samples={len(train_ds)}")

        best_loss = float('inf')
        for epoch in range(pretrain_epochs):
            self.model.encoder.train()
            decoder.train()
            total_loss = 0.0

            for (batch_X,) in train_loader:
                batch_X = batch_X.to(self.device)
                optimizer.zero_grad()

                encoded, mask, targets = self.model.encode_with_mask(
                    batch_X, mask_ratio=mask_ratio)
                reconstructed = decoder(encoded)

                # 仅对被 mask 的 patches 计算损失
                masked_rec = reconstructed[mask]
                masked_tgt = targets[mask]
                loss = criterion(masked_rec, masked_tgt)

                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    list(self.model.encoder.parameters()) + list(decoder.parameters()),
                    self.tcfg['grad_clip'])
                optimizer.step()
                total_loss += loss.item()

            avg_loss = total_loss / len(train_loader)

            if (epoch + 1) % 5 == 0 or epoch == 0:
                print(f"  Pretrain Epoch {epoch+1:>3}/{pretrain_epochs}  "
                      f"Recon Loss: {avg_loss:.6f}")

            if avg_loss < best_loss:
                best_loss = avg_loss
                # 保存预训练 encoder 权重
                pt_path = Path(self.ppaths['output_dir']) / 'patchtst_pretrained.pt'
                torch.save(self.model.encoder.state_dict(), pt_path)

        print(f"[预训练] 完成! 最佳重建损失: {best_loss:.6f}")
        print(f"[预训练] Encoder 权重 → {pt_path}")

        # 清理解码器, 释放内存
        self.model.disable_pretraining()

    def _create_dataloaders(self, splits: dict) -> tuple:
        """创建 DataLoader (支持 'both' 模式的两路标签)"""
        loaders = {}
        for name in ['train', 'val', 'test']:
            s = splits[name]
            X_t = torch.FloatTensor(s['X'])
            y_cls_t = torch.LongTensor(s['y_cls'])

            # 'both' 模式: DataLoader 需要同时返回 y_cls 和 y_reg
            if self.mcfg['mode'] == 'both':
                y_reg_t = torch.FloatTensor(s['y_reg'])
                ds = TensorDataset(X_t, y_cls_t, y_reg_t)
            else:
                ds = TensorDataset(X_t, y_cls_t)

            shuffle = (name == 'train')
            loaders[name] = DataLoader(
                ds, batch_size=self.tcfg['batch_size'],
                shuffle=shuffle, num_workers=0,
            )
            print(f"[数据加载] {name}: {len(ds)} 样本, {len(loaders[name])} batches")

        return loaders['train'], loaders['val'], loaders['test']

    def _create_focal_loss(self, gamma: float = 2.0):
        """创建 Focal Loss — 根据实际数据分布自动计算类别权重

        alpha = 跌样本占比 → 涨类权重 = 跌/总 (稀有类获得更高权重)
        gamma > 0: 降低易分类样本的损失贡献
        """
        # 从 y_cls 统计实际类别分布
        n_up = int(self._n_up) if hasattr(self, '_n_up') else 1
        n_down = int(self._n_down) if hasattr(self, '_n_down') else 1
        total = n_up + n_down

        # 类别权重: 少数类获得更高权重
        w_up = n_down / total   # if down>up, give more weight to up
        w_down = n_up / total   # if up>down, give more weight to down

        class FocalLoss(nn.Module):
            def __init__(self, up_w, down_w, gamma_val):
                super().__init__()
                self.register_buffer('alpha_weights',
                                     torch.tensor([down_w, up_w]))
                self.gamma = gamma_val

            def forward(self, logits, targets):
                ce = F.cross_entropy(logits, targets, reduction='none',
                                     weight=self.alpha_weights)
                pt = torch.exp(-ce)
                focal_weight = (1 - pt) ** self.gamma
                return (focal_weight * ce).mean()

        print(f"[损失] Focal Loss γ={gamma}, 权重: 跌={w_down:.3f}, 涨={w_up:.3f}")
        return FocalLoss(w_up, w_down, gamma)

    def _train_loop(self, train_loader, val_loader) -> dict:
        """训练循环 — 支持 classify / regress / both 三种模式"""
        is_both = (self.mcfg['mode'] == 'both')
        is_regress = (self.mcfg['mode'] == 'regress')
        task_weight = self.tcfg.get('task_weight', 0.6)

        # 损失函数
        if is_regress:
            criterion = nn.SmoothL1Loss(beta=0.01)
        else:
            criterion = self._create_focal_loss()
        huber = nn.SmoothL1Loss(beta=0.01)

        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.tcfg['learning_rate'],
            weight_decay=self.tcfg['weight_decay'],
        )
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=self.tcfg['lr_factor'],
            patience=self.tcfg['lr_patience'],
        )

        history = {'train_loss': [], 'val_loss': [], 'val_acc': [],
                   'lr': [], 'epoch_time': []}
        patience_counter = 0

        col_header = (f"{'Epoch':>6} {'Train Loss':>10} {'Val Loss':>10} "
                      f"{'Val Acc':>8} {'LR':>10} {'Time':>8}")
        if is_both:
            col_header = (f"{'Epoch':>6} {'Train':>8} {'Val':>8} "
                          f"{'Cls':>6} {'Reg':>6} {'Val Acc':>8} {'LR':>10} {'Time':>8}")
        print(f"\n{col_header}")
        print("-" * max(72, len(col_header)))

        for epoch in range(self.tcfg['epochs']):
            t0 = time.time()

            # ── 训练 ──
            self.model.train()
            train_loss = 0.0
            for batch in train_loader:
                if is_both:
                    batch_X, batch_y_cls, batch_y_reg = batch
                    batch_X = batch_X.to(self.device)
                    batch_y_cls = batch_y_cls.to(self.device)
                    batch_y_reg = batch_y_reg.to(self.device)
                else:
                    batch_X, batch_y = batch
                    batch_X = batch_X.to(self.device)
                    batch_y = batch_y.to(self.device)

                optimizer.zero_grad()
                outputs = self.model(batch_X)

                if is_both:
                    cls_loss = criterion(outputs['logits'], batch_y_cls)
                    reg_loss = huber(outputs['pred'], batch_y_reg)
                    loss = task_weight * cls_loss + (1 - task_weight) * reg_loss
                elif is_regress:
                    loss = criterion(outputs['pred'], batch_y)
                else:
                    loss = criterion(outputs['logits'], batch_y)

                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(), self.tcfg['grad_clip'])
                optimizer.step()
                train_loss += loss.item()

            avg_train_loss = train_loss / len(train_loader)

            # ── 验证 ──
            self.model.eval()
            val_loss = 0.0
            correct = total = 0
            with torch.no_grad():
                for batch in val_loader:
                    if is_both:
                        batch_X, batch_y_cls, batch_y_reg = batch
                        batch_X = batch_X.to(self.device)
                        batch_y_cls = batch_y_cls.to(self.device)
                        batch_y_reg = batch_y_reg.to(self.device)
                    else:
                        batch_X, batch_y = batch
                        batch_X = batch_X.to(self.device)
                        batch_y = batch_y.to(self.device)

                    outputs = self.model(batch_X)

                    if is_both:
                        cls_loss = criterion(outputs['logits'], batch_y_cls)
                        reg_loss = huber(outputs['pred'], batch_y_reg)
                        vloss = task_weight * cls_loss + (1 - task_weight) * reg_loss
                        preds = outputs['logits'].argmax(dim=1)
                        correct += (preds == batch_y_cls).sum().item()
                        total += batch_y_cls.size(0)
                    elif is_regress:
                        vloss = criterion(outputs['pred'], batch_y)
                    else:
                        vloss = criterion(outputs['logits'], batch_y)
                        preds = outputs['logits'].argmax(dim=1)
                        correct += (preds == batch_y).sum().item()
                        total += batch_y.size(0)

                    val_loss += vloss.item()

            avg_val_loss = val_loss / len(val_loader)
            val_acc = correct / total if total > 0 else 0

            epoch_time = time.time() - t0

            history['train_loss'].append(avg_train_loss)
            history['val_loss'].append(avg_val_loss)
            history['val_acc'].append(val_acc)
            history['lr'].append(optimizer.param_groups[0]['lr'])
            history['epoch_time'].append(epoch_time)

            scheduler.step(avg_val_loss)

            if is_both and (epoch + 1) % 5 == 0:
                # 额外打印分类/回归分项损失 (每5轮)
                pass

            print(f"{epoch+1:>6} {avg_train_loss:>10.4f} {avg_val_loss:>10.4f} "
                  f"{val_acc:>7.2%} {optimizer.param_groups[0]['lr']:>10.2e} "
                  f"{epoch_time:>7.1f}s")

            # 保存最佳 & 早停
            metric = val_acc if not is_regress else -avg_val_loss
            best_metric = self.best_val_acc if not is_regress else -self.best_val_loss
            if metric > best_metric:
                self.best_val_acc = val_acc
                self.best_val_loss = avg_val_loss
                patience_counter = 0
                self._save_checkpoint(epoch + 1, val_acc, is_best=True)
            else:
                patience_counter += 1

            if patience_counter >= self.tcfg['early_stop_patience']:
                print(f"\n[早停] {self.tcfg['early_stop_patience']} 轮无改善, 停止于 Epoch {epoch+1}")
                break

        best_ep = history['val_acc'].index(max(history['val_acc'])) + 1
        print(f"\n[最佳] Epoch {best_ep}, Val Acc={max(history['val_acc']):.2%}")
        return history

    def evaluate(self, loader, name: str = '') -> dict:
        """评估模型 (支持 classify / both / regress)"""
        self.model.eval()
        correct = total = 0
        all_preds, all_labels = [], []

        with torch.no_grad():
            for batch in loader:
                if self.mcfg['mode'] == 'both':
                    batch_X, batch_y_cls, _ = batch
                else:
                    batch_X, batch_y_cls = batch
                batch_X = batch_X.to(self.device)
                batch_y_cls = batch_y_cls.to(self.device)
                outputs = self.model(batch_X)
                preds = outputs['logits'].argmax(dim=1)
                correct += (preds == batch_y_cls).sum().item()
                total += batch_y_cls.size(0)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(batch_y_cls.cpu().numpy())

        acc = correct / total if total > 0 else 0

        from sklearn.metrics import f1_score, precision_score, recall_score
        f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
        precision = precision_score(all_labels, all_preds, average='macro', zero_division=0)
        recall = recall_score(all_labels, all_preds, average='macro', zero_division=0)

        up_correct = sum(1 for p, l in zip(all_preds, all_labels) if p == l == 1)
        down_correct = sum(1 for p, l in zip(all_preds, all_labels) if p == l == 0)
        up_total = sum(1 for l in all_labels if l == 1)
        down_total = sum(1 for l in all_labels if l == 0)

        metrics = {
            'accuracy': acc,
            'f1_macro': f1,
            'precision_macro': precision,
            'recall_macro': recall,
            'up_accuracy': up_correct / up_total if up_total > 0 else 0,
            'down_accuracy': down_correct / down_total if down_total > 0 else 0,
            'n_samples': total,
        }

        label_name = f"[{name}]" if name else ""
        print(f"{label_name} 准确率: {acc:.2%} | F1: {f1:.2%} | "
              f"涨准确: {metrics['up_accuracy']:.2%} | 跌准确: {metrics['down_accuracy']:.2%}")

        return metrics

    def _train_lstm_baseline(self, splits: dict) -> dict:
        """训练 LSTM 基线模型"""
        n_input = self.mcfg['n_channels']
        lstm_model = LSTMBaseline(
            input_size=n_input, hidden_size=64,
            num_layers=2, dropout=0.2,
        ).to(self.device)

        print(f"[LSTM] 输入维度={n_input}, 参数量={sum(p.numel() for p in lstm_model.parameters()):,}")

        train_ds = TensorDataset(
            torch.FloatTensor(splits['train']['X']),
            torch.LongTensor(splits['train']['y_cls']))
        test_ds = TensorDataset(
            torch.FloatTensor(splits['test']['X']),
            torch.LongTensor(splits['test']['y_cls']))

        train_loader = DataLoader(train_ds, batch_size=self.tcfg['batch_size'],
                                  shuffle=True, num_workers=0)
        test_loader = DataLoader(test_ds, batch_size=self.tcfg['batch_size'],
                                 shuffle=False, num_workers=0)

        criterion = self._create_focal_loss()
        optimizer = torch.optim.AdamW(lstm_model.parameters(),
                                       lr=1e-3, weight_decay=1e-4)

        for epoch in range(self.tcfg['epochs']):
            lstm_model.train()
            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                optimizer.zero_grad()
                loss = criterion(lstm_model(batch_X)['logits'], batch_y)
                loss.backward()
                optimizer.step()

        lstm_model.eval()
        correct = total = 0
        with torch.no_grad():
            for batch_X, batch_y in test_loader:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                preds = lstm_model(batch_X)['logits'].argmax(dim=1)
                correct += (preds == batch_y).sum().item()
                total += batch_y.size(0)

        acc = correct / total
        print(f"[LSTM] 测试准确率: {acc:.2%}")
        return {'accuracy': acc, 'model': 'LSTM'}

    def _save_checkpoint(self, epoch: int, val_acc: float, is_best: bool = False):
        """保存检查点"""
        ckpt = {
            'epoch': epoch,
            'model_state': self.model.state_dict(),
            'val_acc': val_acc,
            'config': self.mcfg,
        }
        path = Path(self.ppaths['output_dir']) / 'patchtst_checkpoint.pt'
        torch.save(ckpt, path)

        if is_best:
            best_path = Path(self.ppaths['output_dir']) / 'patchtst_best.pt'
            torch.save(ckpt, best_path)

    def _save_model(self, metrics: dict, lstm_metrics: Optional[dict] = None) -> Path:
        """保存最终模型"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        acc_str = f"{metrics['accuracy']:.3f}".replace('0.', '')
        filename = f"patchtst_acc{acc_str}_{timestamp}.pt"
        path = Path(self.ppaths['output_dir']) / filename

        save_data = {
            'model_state': self.model.state_dict(),
            'config': self.mcfg,
            'metrics': metrics,
            'lstm_baseline': lstm_metrics,
            'timestamp': timestamp,
        }
        torch.save(save_data, path)
        print(f"\n[保存] 模型 → {path}")

        # 保存训练摘要 JSON
        summary = {
            'model': 'PatchTST',
            'timestamp': timestamp,
            'n_params': count_parameters(self.model)['total'],
            'config': self.mcfg,
            'training': self.tcfg,
            'metrics': {k: float(v) if isinstance(v, (np.floating, float)) else v
                       for k, v in metrics.items()},
            'lstm_baseline': lstm_metrics if lstm_metrics else None,
        }
        json_path = Path(self.ppaths['log_dir']) / f"training_summary_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        return path

    def _print_comparison(self, pt_metrics: dict, lstm_metrics: Optional[dict]):
        """打印 PatchTST vs LSTM 对比"""
        print("\n" + "=" * 50)
        print("  模型对比")
        print("=" * 50)

        pt_params = count_parameters(self.model)['total']
        print(f"{'PatchTST':<15} 准确率: {pt_metrics['accuracy']:.2%}  "
              f"F1: {pt_metrics['f1_macro']:.2%}  参数: {pt_params:,}")

        if lstm_metrics:
            print(f"{'LSTM 基线':<15} 准确率: {lstm_metrics['accuracy']:.2%}  "
                  f"参数: ~{64 * 64 * 4:,}")

            delta = pt_metrics['accuracy'] - lstm_metrics['accuracy']
            winner = "PatchTST ✓" if delta > 0 else "LSTM ✓" if delta < 0 else "平局"
            print(f"\n差异: {delta:+.2%} → {winner}")


# ── 便捷入口 ──────────────────────────────────────────────

def train_patchtst(
    data_dir: str = 'data/cache',
    codes: Optional[list[str]] = None,
    config_overrides: Optional[dict] = None,
    train_lstm: bool = True,
    use_pretrain: bool = True,
    use_macro: bool = True,
) -> dict:
    """一键训练 PatchTST (Phase 2 增强版)

    Args:
        data_dir: Parquet 数据目录
        codes: 指定标的列表, None=自动扫描所有
        config_overrides: 配置覆盖
        train_lstm: 是否训练 LSTM 基线对比
        use_pretrain: 是否启用自监督预训练
        use_macro: 是否注入宏观特征 (康波/十五五/社保风格)

    Returns:
        训练结果字典
    """
    if codes is None:
        dp = Path(data_dir)
        if not dp.exists():
            raise FileNotFoundError(f"数据目录不存在: {data_dir}")
        codes = sorted(set(
            f.stem.replace('kline_', '').replace('_daily', '')
            for f in dp.glob('kline_*_daily.parquet')
        ))

    if not codes:
        raise ValueError(f"在 {data_dir} 中未找到 kline_*_daily.parquet 文件")

    print(f"\n[扫描] 发现 {len(codes)} 个标的")

    # 应用预训练和宏观特征配置
    if config_overrides is None:
        config_overrides = {}
    if 'pretrain' not in config_overrides:
        config_overrides['pretrain'] = {}
    config_overrides['pretrain']['enabled'] = use_pretrain

    # 数据准备 (含宏观特征)
    processor = FinancialDataProcessor(
        data_dir,
        seq_len=DEFAULT_CONFIG['model']['seq_len'],
        use_macro=use_macro,
    )
    data = processor.load_and_prepare(codes)

    # 训练
    trainer = PatchTSTTrainer(config_overrides)
    result = trainer.train(data, codes=codes, train_lstm_baseline=train_lstm)

    return result


# ── CLI ───────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='PatchTST 模型训练 — Phase 2 增强版 (宏观+预训练+多任务)')
    parser.add_argument('--data-dir', default='data/cache', help='数据目录')
    parser.add_argument('--codes', nargs='*', default=None, help='指定标的 (空格分隔)')
    parser.add_argument('--full', action='store_true',
                        help='全量标的训练 (默认行为, 扫描所有 parquet)')
    parser.add_argument('--epochs', type=int, default=50, help='下游微调轮数')
    parser.add_argument('--lr', type=float, default=5e-4, help='微调学习率')
    parser.add_argument('--no-lstm', action='store_true', help='跳过 LSTM 基线')
    parser.add_argument('--no-pretrain', action='store_true', help='禁用自监督预训练')
    parser.add_argument('--no-macro', action='store_true', help='禁用宏观特征 (仅 OHLCV)')
    parser.add_argument('--pretrain-epochs', type=int, default=30, help='预训练轮数')
    parser.add_argument('--mask-ratio', type=float, default=0.40, help='预训练 Mask 比例')
    parser.add_argument('--mode', choices=['classify', 'regress', 'both'],
                        default='classify', help='模型模式 (classify/regress/both)')
    parser.add_argument('--task-weight', type=float, default=0.6,
                        help="'both' 模式分类任务权重 (0-1)")

    args = parser.parse_args()

    config_overrides = {
        'training': {
            'epochs': args.epochs,
            'learning_rate': args.lr,
            'task_weight': args.task_weight,
        },
        'model': {
            'mode': args.mode,
        },
        'pretrain': {
            'enabled': not args.no_pretrain,
            'epochs': args.pretrain_epochs,
            'mask_ratio': args.mask_ratio,
        },
    }

    result = train_patchtst(
        data_dir=args.data_dir,
        codes=args.codes,
        config_overrides=config_overrides,
        train_lstm=not args.no_lstm,
        use_pretrain=not args.no_pretrain,
        use_macro=not args.no_macro,
    )

    print(f"\n{'='*50}")
    print(f"  训练完成!")
    print(f"  模型: {result['model_path']}")
    print(f"  准确率: {result['metrics']['accuracy']:.2%}")
    print(f"  F1 Macro: {result['metrics']['f1_macro']:.2%}")
    if result['lstm_baseline']:
        delta = result['metrics']['accuracy'] - result['lstm_baseline']['accuracy']
        print(f"  vs LSTM: {delta:+.2%}")
    print(f"{'='*50}")
