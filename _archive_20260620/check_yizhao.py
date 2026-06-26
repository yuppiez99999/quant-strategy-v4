# -*- coding: utf-8 -*-
"""检查 YiZhao 数据集结构"""
import sys
if sys.version_info < (3, 9):
    try:
        from backports import zoneinfo
        sys.modules['zoneinfo'] = zoneinfo
    except ImportError:
        pass

from modelscope.msdatasets import MsDataset

# 尝试不同的子集名称
subset_names = ['default', 'train', 'zh', 'en', 'financial', None]

for subset in subset_names:
    try:
        print(f"\n尝试子集: {subset}")
        ds = MsDataset.load(
            'CMB_AILab/YiZhao-FinDataSet',
            subset_name=subset,
            split='train'
        )
        print(f"成功! 子集: {subset}, 记录数: {len(ds)}")
        # 打印第一条记录的结构
        sample = ds[0]
        print(f"样本键: {list(sample.keys())[:5]}")
        break
    except Exception as e:
        print(f"失败: {e}")
        continue
