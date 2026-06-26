# -*- coding: utf-8 -*-
"""检查 YiZhao 数据集样本结构"""
import sys
if sys.version_info < (3, 9):
    try:
        from backports import zoneinfo
        sys.modules['zoneinfo'] = zoneinfo
    except ImportError:
        pass

from modelscope.msdatasets import MsDataset

ds = MsDataset.load(
    'CMB_AILab/YiZhao-FinDataSet',
    subset_name='en',
    split='train'
)

print(f"总记录数: {len(ds)}")
print("\n第一条记录:")
sample = ds[0]
for key, value in sample.items():
    if isinstance(value, str):
        print(f"  {key}: {value[:100]}...")
    else:
        print(f"  {key}: {value}")

print("\n\n前3条记录的meta信息:")
for i in range(min(3, len(ds))):
    meta = ds[i].get('meta', ds[i])
    print(f"\n记录 {i+1}:")
    if isinstance(meta, dict):
        for k, v in meta.items():
            print(f"  {k}: {v}")
    else:
        print(f"  meta: {meta}")
