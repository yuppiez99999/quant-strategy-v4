# -*- coding: utf-8 -*-
"""报告归档工具。"""

import os
from datetime import date, datetime
from typing import Optional, Union

DateLike = Union[date, datetime]


def _format_date(value: Optional[DateLike], fmt: str) -> str:
    current = value or datetime.now()
    return current.strftime(fmt)


def get_archive_dir(base_dir: str, date_value: Optional[DateLike] = None) -> str:
    archive_dir = os.path.join(base_dir, '..', '每日报告归档', _format_date(date_value, '%Y-%m-%d'))
    os.makedirs(archive_dir, exist_ok=True)
    return archive_dir


def archive_report(base_dir: str, filename: str, content: str, date_value: Optional[DateLike] = None) -> str:
    archive_path = os.path.join(get_archive_dir(base_dir, date_value), filename)
    with open(archive_path, 'w', encoding='utf-8') as f:
        f.write(content)
    return archive_path
