#!/usr/bin/env python3
"""A股交易日判断脚本。根据2026年休市安排判断指定日期是否为交易日。"""
import sys
from datetime import date, timedelta

# 2026年A股节假日休市安排
HOLIDAYS_2026 = [
    # 元旦
    (date(2026, 1, 1), date(2026, 1, 3)),
    # 春节
    (date(2026, 2, 15), date(2026, 2, 23)),
    # 清明节
    (date(2026, 4, 4), date(2026, 4, 6)),
    # 劳动节
    (date(2026, 5, 1), date(2026, 5, 5)),
    # 端午节
    (date(2026, 6, 19), date(2026, 6, 21)),
    # 中秋节
    (date(2026, 9, 25), date(2026, 9, 27)),
    # 国庆节
    (date(2026, 10, 1), date(2026, 10, 7)),
]

# 调休补班日（这些周末上班，是交易日）
WORKDAYS_2026 = [
    date(2026, 1, 4),   # 元旦后补班（周日）
    date(2026, 2, 14),  # 春节前补班（周六）
    date(2026, 2, 28),  # 春节后补班（周六）
    date(2026, 5, 9),   # 劳动节后补班（周六）
    date(2026, 9, 20),  # 中秋节前补班（周日）
    date(2026, 10, 10), # 国庆节后补班（周六）
]

def is_trading_day(d=None):
    """判断某天是不是A股交易日"""
    if d is None:
        d = date.today()
    
    # 周末不交易
    if d.weekday() >= 5:  # 5=周六, 6=周日
        # 检查是否是调休补班
        for wd in WORKDAYS_2026:
            if wd == d:
                return True
        return False
    
    # 检查是否在节假日休市范围内
    for start, end in HOLIDAYS_2026:
        if start <= d <= end:
            return False
    
    return True

def next_trading_day(d=None):
    """获取下一个交易日"""
    if d is None:
        d = date.today()
    d += timedelta(days=1)
    while not is_trading_day(d):
        d += timedelta(days=1)
    return d

if __name__ == '__main__':
    today = date.today()
    if is_trading_day(today):
        print(f"✅ {today} 是交易日")
        sys.exit(0)
    else:
        next_day = next_trading_day(today)
        print(f"⚠️ {today} 非交易日（周末或节假日）")
        print(f"📅 下一个交易日: {next_day}")
        sys.exit(0)  # 非交易日也返回0，由调用方决定是否继续执行
