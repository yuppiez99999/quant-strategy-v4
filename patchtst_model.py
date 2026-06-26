#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PatchTST 模型 — CPU 友好基线版本
参考: PatchTST (Nie et al., ICLR 2023) "A Time Series is Worth 64 Words"

架构: Encoder-only, Channel-Independent, Pre-LN, 监督学习
设计目标: 可在 CPU 上训练 (2-4层, d_model=128-256, <500K参数)
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


# ── 基础组件 ──────────────────────────────────────────────

class RMSNorm(nn.Module):
    """RMS Layer Normalization (Zhang & Sennrich, 2019)"""

    def __init__(self, d_model: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(d_model))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        rms = torch.sqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
        return x / rms * self.weight


class SinusoidalPositionalEncoding(nn.Module):
    """可学习 + 正弦位置编码混合"""

    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() *
                             (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe.unsqueeze(0))  # (1, max_len, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, :x.size(1), :]


class MultiHeadAttention(nn.Module):
    """标准 Multi-Head Scaled Dot-Product Attention"""

    def __init__(self, d_model: int, n_heads: int, dropout: float = 0.1):
        super().__init__()
        assert d_model % n_heads == 0
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads

        self.W_q = nn.Linear(d_model, d_model, bias=False)
        self.W_k = nn.Linear(d_model, d_model, bias=False)
        self.W_v = nn.Linear(d_model, d_model, bias=False)
        self.W_o = nn.Linear(d_model, d_model, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, N, D = x.shape  # batch, num_patches, d_model

        # 多头投影
        Q = self.W_q(x).view(B, N, self.n_heads, self.d_k).transpose(1, 2)
        K = self.W_k(x).view(B, N, self.n_heads, self.d_k).transpose(1, 2)
        V = self.W_v(x).view(B, N, self.n_heads, self.d_k).transpose(1, 2)

        # Scaled Dot-Product Attention
        scale = math.sqrt(self.d_k)
        attn_scores = (Q @ K.transpose(-2, -1)) / scale
        attn_weights = F.softmax(attn_scores, dim=-1)
        attn_weights = self.dropout(attn_weights)

        # 加权聚合
        out = attn_weights @ V  # (B, n_heads, N, d_k)
        out = out.transpose(1, 2).contiguous().view(B, N, D)
        return self.W_o(out)


class FeedForward(nn.Module):
    """Position-wise Feed-Forward with GELU"""

    def __init__(self, d_model: int, d_ff: int, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class TransformerEncoderBlock(nn.Module):
    """Pre-LN Transformer Encoder Block"""

    def __init__(self, d_model: int, n_heads: int, d_ff: int, dropout: float = 0.1):
        super().__init__()
        self.norm1 = RMSNorm(d_model)
        self.attn = MultiHeadAttention(d_model, n_heads, dropout)
        self.norm2 = RMSNorm(d_model)
        self.ff = FeedForward(d_model, d_ff, dropout)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Pre-LN: norm → attn → residual
        x = x + self.dropout(self.attn(self.norm1(x)))
        # Pre-LN: norm → ff → residual
        x = x + self.ff(self.norm2(x))
        return x


# ── PatchTST Encoder ──────────────────────────────────────

class PatchTSTEncoder(nn.Module):
    """PatchTST Encoder (Channel-Independent)

    输入: (B, C, T) — batch, channels, time steps
    内部流程:
      1. Instance Normalization (per channel)
      2. Patching: (B, C, T) → (B*C, N, P) where N = num patches, P = patch_len
      3. Patch Embedding: Linear(P, d_model)
      4. Positional Encoding
      5. Transformer Encoder Blocks (Pre-LN)
      6. Mean Pooling over N patches → (B*C, d_model)
    """

    def __init__(
        self,
        n_channels: int,
        patch_len: int = 16,
        stride: int = 8,
        d_model: int = 128,
        n_heads: int = 4,
        n_layers: int = 3,
        d_ff: int = 256,
        dropout: float = 0.2,
        max_seq_len: int = 252,
    ):
        super().__init__()
        self.n_channels = n_channels
        self.patch_len = patch_len
        self.stride = stride

        # 计算最大 patch 数量
        self.max_patches = (max_seq_len - patch_len) // stride + 1

        # Patch Embedding
        self.patch_embed = nn.Linear(patch_len, d_model)

        # 位置编码
        self.pos_encoding = SinusoidalPositionalEncoding(d_model, self.max_patches)

        # Transformer Encoder Blocks
        self.encoder_blocks = nn.ModuleList([
            TransformerEncoderBlock(d_model, n_heads, d_ff, dropout)
            for _ in range(n_layers)
        ])

        self.norm_out = RMSNorm(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, C, T)
        B, C, T = x.shape

        # 1. Instance Normalization (per channel, across time)
        mean = x.mean(dim=-1, keepdim=True)
        std = x.std(dim=-1, keepdim=True).clamp(min=1e-5)
        x = (x - mean) / std

        # 2. Patching — unfold into (B, C, N, P)
        x = x.unfold(dimension=-1, size=self.patch_len, step=self.stride)
        # x: (B, C, N, P)

        B, C, N, P = x.shape

        # 3. Channel-Independent: reshape to (B*C, N, P)
        x = x.reshape(B * C, N, P)

        # 4. Patch Embedding
        x = self.patch_embed(x)  # (B*C, N, d_model)

        # 5. Positional Encoding
        x = self.pos_encoding(x)

        # 6. Dropout
        x = self.dropout(x)

        # 7. Transformer Encoder Blocks
        for block in self.encoder_blocks:
            x = block(x)

        # 8. Final Norm + Mean Pooling over patches
        x = self.norm_out(x)      # (B*C, N, d_model)
        x = x.mean(dim=1)         # (B*C, d_model)

        # 9. Restore channel dimension: (B, C*d_model)
        x = x.reshape(B, C * self.encoder_blocks[0].attn.d_model)

        return x


# ── 完整 PatchTST 模型 ─────────────────────────────────────

class PatchTSTDecoder(nn.Module):
    """Masked Patch 重建解码器 — 自监督预训练用

    输入: encoder 输出 (B*C, N, d_model) — 所有 patch 的表示
    任务: 重建被 mask 的原始 patch 值
    """

    def __init__(self, d_model: int, patch_len: int, n_heads: int = 4,
                 n_layers: int = 2, dropout: float = 0.1):
        super().__init__()
        self.patch_len = patch_len
        self.d_model = d_model

        # 轻量 Transformer Decoder (自注意力, 无交叉注意力因为只有 encoder 输出)
        self.decoder_blocks = nn.ModuleList([
            TransformerEncoderBlock(d_model, n_heads, d_model * 2, dropout)
            for _ in range(n_layers)
        ])

        self.norm_out = RMSNorm(d_model)
        self.head = nn.Linear(d_model, patch_len)

    def forward(self, encoded: torch.Tensor) -> torch.Tensor:
        """重建 patches

        Args:
            encoded: (B*C, N, d_model) — encoder 输出

        Returns:
            reconstructed: (B*C, N, patch_len) — 重建的 patch 值
        """
        x = encoded
        for block in self.decoder_blocks:
            x = block(x)
        x = self.norm_out(x)
        return self.head(x)  # (B*C, N, patch_len)


class PatchTST(nn.Module):
    """PatchTST 完整模型：Encoder + 分类头 / 回归头

    支持三种模式:
      - 'classify': 方向分类 (涨/跌), Focal Loss
      - 'regress':  收益率回归, Huber Loss
      - 'both':     多任务学习 (分类 + 回归), 加权联合损失
    支持自监督预训练 (Masked Patch Reconstruction)
    """

    def __init__(
        self,
        n_channels: int = 5,
        seq_len: int = 60,          # 回溯窗口 (交易日)
        pred_len: int = 1,          # 预测步长 (1=次日)
        patch_len: int = 16,
        stride: int = 8,
        d_model: int = 128,
        n_heads: int = 4,
        n_layers: int = 3,
        d_ff: int = 256,
        dropout: float = 0.2,
        mode: str = 'classify',     # 'classify', 'regress', 'both'
        n_classes: int = 2,         # 分类类别数
    ):
        super().__init__()
        self.mode = mode
        self.seq_len = seq_len
        self.pred_len = pred_len
        self.n_channels = n_channels
        self.patch_len = patch_len
        self.stride = stride
        self.d_model = d_model

        # Encoder
        self.encoder = PatchTSTEncoder(
            n_channels=n_channels,
            patch_len=patch_len,
            stride=stride,
            d_model=d_model,
            n_heads=n_heads,
            n_layers=n_layers,
            d_ff=d_ff,
            dropout=dropout,
            max_seq_len=seq_len,
        )

        # 预训练解码器 (独立于下游任务头)
        self.pretrain_decoder: Optional[PatchTSTDecoder] = None

        encoder_dim = n_channels * d_model

        # 分类头
        if mode in ('classify', 'both'):
            self.classifier = nn.Sequential(
                nn.Linear(encoder_dim, 64),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(64, n_classes),
            )

        # 回归头
        if mode in ('regress', 'both'):
            self.regressor = nn.Sequential(
                nn.Linear(encoder_dim, 64),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(64, pred_len),
            )

    def enable_pretraining(self):
        """启用自监督预训练解码器"""
        self.pretrain_decoder = PatchTSTDecoder(
            d_model=self.d_model,
            patch_len=self.patch_len,
            n_heads=4,
            n_layers=2,
            dropout=0.1,
        )
        return self.pretrain_decoder

    def disable_pretraining(self):
        """禁用预训练解码器 (释放内存, 用于下游任务)"""
        self.pretrain_decoder = None

    def encode_with_mask(self, x: torch.Tensor, mask_ratio: float = 0.4
                         ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """带 mask 的编码 — 预训练前向传播

        在 patch 级别随机 mask, 然后编码, 返回:
          - encoded: 编码后的表示 (含 mask token)
          - mask:    被 mask 的位置 (True=masked)
          - targets: 原始 patch 值 (用于重建损失)

        Args:
            x: (B, C, T) 原始输入
            mask_ratio: mask 比例 (0-1)

        Returns:
            encoded: (B*C, N, d_model)
            mask:    (B*C, N) bool
            targets: (B*C, N, patch_len)
        """
        B, C, T = x.shape

        # 1. Instance Normalization
        mean = x.mean(dim=-1, keepdim=True)
        std = x.std(dim=-1, keepdim=True).clamp(min=1e-5)
        x_norm = (x - mean) / std

        # 2. Patching
        patches = x_norm.unfold(dimension=-1, size=self.patch_len, step=self.stride)
        B, C, N, P = patches.shape
        patches_flat = patches.reshape(B * C, N, P)  # (B*C, N, P)

        # 保存原始 patch 值作为重建目标
        targets = patches_flat.clone()

        # 3. 随机 mask patches
        mask = torch.rand(B * C, N, device=x.device) < mask_ratio
        # 确保至少一个 patch 不被 mask (避免全 mask)
        for i in range(B * C):
            if mask[i].all():
                mask[i, 0] = False

        # 将被 mask 的 patch 替换为可学习的 mask token
        # (简化为零向量 — 效果已足够)
        patches_flat[mask] = 0.0

        # 4. Patch Embedding
        x_emb = self.encoder.patch_embed(patches_flat)  # (B*C, N, d_model)

        # 5. Positional Encoding
        x_emb = self.encoder.pos_encoding(x_emb)

        # 6. Dropout
        x_emb = self.encoder.dropout(x_emb)

        # 7. Transformer Encoder Blocks
        for block in self.encoder.encoder_blocks:
            x_emb = block(x_emb)

        return x_emb, mask, targets

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        """前向传播

        Args:
            x: (B, C, T) — batch, channels, time steps

        Returns:
            dict with keys depending on mode:
              - 'logits': 分类 logits (classify/both)
              - 'pred':   回归预测值 (regress/both)
        """
        encoded = self.encoder(x)  # (B, C*d_model)

        result = {}
        if self.mode in ('classify', 'both'):
            result['logits'] = self.classifier(encoded)
        if self.mode in ('regress', 'both'):
            result['pred'] = self.regressor(encoded).squeeze(-1)

        return result

    def get_num_params(self) -> int:
        """返回总参数量"""
        return sum(p.numel() for p in self.parameters())


# ── 损失函数 ──────────────────────────────────────────────

class PatchTSTLoss(nn.Module):
    """PatchTST 组合损失

    - 'classify':  Focal Loss (处理类别不均衡)
    - 'regress':   Huber Loss (对异常值鲁棒)
    - 'both':      多任务: α * Focal + (1-α) * Huber
    - 'pretrain':  Masked Patch MSE 重建损失
    """

    def __init__(self, mode: str = 'classify', task_weight: float = 0.5,
                 class_weights: Optional[torch.Tensor] = None):
        super().__init__()
        self.mode = mode
        self.task_weight = task_weight  # 分类权重 (only for 'both')
        self.class_weights = class_weights
        self.huber_loss = nn.SmoothL1Loss(beta=0.01)
        self.mse_loss = nn.MSELoss()

    def _focal_loss(self, logits: torch.Tensor, targets: torch.Tensor,
                    gamma: float = 2.0) -> torch.Tensor:
        """Focal Loss for class imbalance (支持类别权重)"""
        ce = F.cross_entropy(logits, targets, reduction='none',
                             weight=self.class_weights.to(logits.device)
                             if self.class_weights is not None else None)
        pt = torch.exp(-ce)
        focal_weight = (1 - pt) ** gamma
        return (focal_weight * ce).mean()

    def _pretrain_loss(self, reconstructed: torch.Tensor,
                       targets: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Masked Patch 重建损失 — 仅计算被 mask 位置"""
        # reconstructed: (B*C, N, patch_len)
        # targets:       (B*C, N, patch_len)
        # mask:          (B*C, N) bool — True=masked positions
        masked_rec = reconstructed[mask]      # (N_masked, patch_len)
        masked_tgt = targets[mask]            # (N_masked, patch_len)
        return self.mse_loss(masked_rec, masked_tgt)

    def forward(self, outputs: dict, targets: dict) -> torch.Tensor:
        if self.mode == 'classify':
            return self._focal_loss(outputs['logits'], targets['label'])
        elif self.mode == 'regress':
            return self.huber_loss(outputs['pred'], targets['return_'])
        elif self.mode == 'both':
            cls_loss = self._focal_loss(outputs['logits'], targets['label'])
            reg_loss = self.huber_loss(outputs['pred'], targets['return_'])
            return self.task_weight * cls_loss + (1 - self.task_weight) * reg_loss
        elif self.mode == 'pretrain':
            return self._pretrain_loss(
                outputs['reconstructed'], targets['patches'], targets['mask'])
        else:
            raise ValueError(f"Unknown mode: {self.mode}")


# ── 工具函数 ──────────────────────────────────────────────

def count_parameters(model: nn.Module) -> dict:
    """统计模型参数"""
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return {'total': total, 'trainable': trainable}


def create_patchtst(config: dict) -> PatchTST:
    """从配置字典创建 PatchTST 模型"""
    return PatchTST(
        n_channels=config.get('n_channels', 5),
        seq_len=config.get('seq_len', 60),
        pred_len=config.get('pred_len', 1),
        patch_len=config.get('patch_len', 16),
        stride=config.get('stride', 8),
        d_model=config.get('d_model', 128),
        n_heads=config.get('n_heads', 4),
        n_layers=config.get('n_layers', 3),
        d_ff=config.get('d_ff', 256),
        dropout=config.get('dropout', 0.2),
        mode=config.get('mode', 'classify'),
        n_classes=config.get('n_classes', 2),
    )


if __name__ == '__main__':
    # 快速测试
    config = {
        'n_channels': 5,
        'seq_len': 60,
        'patch_len': 16,
        'stride': 8,
        'd_model': 128,
        'n_heads': 4,
        'n_layers': 3,
        'd_ff': 256,
        'dropout': 0.2,
        'mode': 'classify',
    }

    model = create_patchtst(config)
    params = count_parameters(model)
    print(f"PatchTST 模型参数: {params}")

    # 测试前向传播
    x = torch.randn(4, 5, 60)  # (batch=4, channels=5, seq_len=60)
    out = model(x)
    print(f"输入: {x.shape}")
    print(f"输出: {out['logits'].shape}")
    print(f"前向传播成功!")
